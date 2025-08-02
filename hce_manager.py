# =====================================================================
# File: hce_manager.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Production-grade HCE manager for provisioning Android HCE.
#   - Version/capability negotiation (hce_hello)
#   - ECDH key exchange + AES-GCM encryption
#   - zlib compression
#   - JSON Schema validation
#   - Chunked transfer with per-chunk ACKs, retries, sequencing
#   - Progress, error, cancel, and completion signals
#   - Persistent profile caching
# =====================================================================

import json
import zlib
import uuid
import threading
from jsonschema import validate, ValidationError
from PyQt5.QtCore import QObject, pyqtSignal, QEventLoop, QTimer
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from settings import SettingsManager

# Error codes
HCE_ERRORS = {
    "HELLO_TIMEOUT": "Phone did not respond to hello",
    "NO_ECDH":       "Key exchange failed",
    "SCHEMA_INVALID":"HCE profile schema validation failed",
    "CHUNK_TIMEOUT": "Chunk ACK timeout",
    "TRANSFER_FAIL": "Transfer failed",
    "CANCELED":      "Provisioning canceled"
}

# Simple JSON schema for HCE profile
HCE_PROFILE_SCHEMA = {
    "type": "object",
    "required": ["PAN","AIDs","FCI","Records"],
    "properties": {
        "PAN": {"type": "string"},
        "Cardholder": {"type": "string"},
        "Expiry": {"type": "string"},
        "AIDs": {"type": "array", "items": {"type": "string"}},
        "FCI": {"type": "object"},
        "Records": {"type": "object"},
        "PDOL": {"type": "string"}
    }
}

class HceManager(QObject):
    hce_status    = pyqtSignal(str)           # Informational messages
    hce_progress  = pyqtSignal(int,int)       # (seq, total)
    hce_complete  = pyqtSignal(bool,str)      # (success, code_or_msg)

    def __init__(self, bluetooth_companion):
        super().__init__()
        self.bt = bluetooth_companion
        self.bt.message_received.connect(self._on_bt_message)
        self.settings = SettingsManager()
        self._requests = {}  # id → state dict

    def generate_hce_profile(self, card):
        # (Same as before; omitted for brevity)
        ...

    def push_to_phone(self, card, timeout=15000, mtu=1024, retry=3):
        """
        Provision HCE profile to phone companion.
        Returns True on success, False on failure.
        """
        # 1. Assemble and validate profile
        profile = self.generate_hce_profile(card)
        try:
            validate(profile, HCE_PROFILE_SCHEMA)
        except ValidationError as e:
            self.hce_complete.emit(False, HCE_ERRORS["SCHEMA_INVALID"])
            return False

        # 2. Compression
        raw = json.dumps(profile).encode("utf-8")
        comp = zlib.compress(raw)

        # 3. Request ID & ECDH key gen
        req_id = str(uuid.uuid4())
        priv = ec.generate_private_key(ec.SECP256R1())
        pub = priv.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )
        state = {
            "id": req_id,
            "priv": priv,
            "mtu": mtu,
            "chunks": [],
            "acks": set(),
            "retry": retry,
            "loop": QEventLoop(),
            "timer": QTimer(singleShot=True),
            "canceled": False
        }
        self._requests[req_id] = state

        # 4. Send hello with host pubkey & version
        hello = {"cmd":"hce_hello","id":req_id,"pubkey":pub.hex(),"version":"4.04"}
        try:
            self.bt.send_to_phone(hello)
        except Exception:
            self.hce_complete.emit(False, HCE_ERRORS["TRANSFER_FAIL"])
            return False
        self.hce_status.emit("Sent hello, awaiting phone ack...")
        # Wait for hce_hello_ack
        timer = state["timer"]
        timer.timeout.connect(state["loop"].quit)
        timer.start(timeout)
        state["loop"].exec_()
        ack = state.get("hello_ack")
        if state["canceled"]:
            return self._finish(req_id, False, HCE_ERRORS["CANCELED"])
        if not ack or ack.get("status")!="OK":
            return self._finish(req_id, False, HCE_ERRORS["HELLO_TIMEOUT"])
        # Derive shared key
        try:
            peer_pub = bytes.fromhex(ack["pubkey"])
            peer_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), peer_pub)
            shared = priv.exchange(ec.ECDH(), peer_key)
            aes_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"nfsp00f3r-hce"
            ).derive(shared)
        except Exception:
            return self._finish(req_id, False, HCE_ERRORS["NO_ECDH"])

        # 5. Chunk encryption & staging
        aesgcm = AESGCM(aes_key)
        nonce = AESGCM.generate_nonce()
        encrypted = aesgcm.encrypt(nonce, comp, None)
        payload = nonce + encrypted
        total = (len(payload)+mtu-1)//mtu
        for i in range(total):
            chunk = payload[i*mtu:(i+1)*mtu]
            state["chunks"].append({"seq":i,"data":chunk.hex()})

        # 6. Send each chunk with per-chunk ACKs & retries
        state["acked"] = set()
        for chunk in state["chunks"]:
            for attempt in range(retry):
                if state["canceled"]:
                    return self._finish(req_id, False, HCE_ERRORS["CANCELED"])
                msg = {"cmd":"hce_chunk","id":req_id,
                       "seq":chunk["seq"],"total":total,"data":chunk["data"]}
                try:
                    self.bt.send_to_phone(msg)
                except Exception:
                    continue
                self.hce_status.emit(f"Sent chunk {chunk['seq']+1}/{total}")
                # Wait for ack
                acktimer = QTimer(singleShot=True, interval=1000)
                acktimer.timeout.connect(state["loop"].quit)
                acktimer.start()
                state["loop"].exec_()
                if chunk["seq"] in state["acks"]:
                    self.hce_progress.emit(chunk["seq"]+1, total)
                    break
                else:
                    self.hce_status.emit(f"Retry chunk {chunk['seq']+1}")
            else:
                return self._finish(req_id, False, HCE_ERRORS["CHUNK_TIMEOUT"])

        # 7. All chunks sent; wait for final ack
        finish_timer = QTimer(singleShot=True, interval=5000)
        finish_timer.timeout.connect(state["loop"].quit)
        finish_timer.start()
        state["loop"].exec_()
        final = state.get("final_ack")
        status = final.get("status") if final else None
        return self._finish(req_id, status=="OK", HCE_ERRORS.get(final.get("error"), final or HCE_ERRORS["TRANSFER_FAIL"]))

    def cancel(self, req_id):
        """Cancel an ongoing provisioning."""
        state = self._requests.get(req_id)
        if state:
            state["canceled"] = True
            state["loop"].quit()

    def _on_bt_message(self, msg):
        cmd = msg.get("cmd")
        rid = msg.get("id")
        state = self._requests.get(rid)
        if not state:
            return

        if cmd == "hce_hello_ack":
            state["hello_ack"] = msg
            state["loop"].quit()

        elif cmd == "hce_chunk_ack":
            seq = msg.get("seq")
            if isinstance(seq, int):
                state["acks"].add(seq)
                state["loop"].quit()

        elif cmd == "hce_complete":
            state["final_ack"] = msg
            state["loop"].quit()

    def _finish(self, req_id, success, info):
        """Cleanup and emit completion."""
        self._requests.pop(req_id, None)
        if success:
            # Persist profile ID for reload
            self.settings.set(f"hce_profile_{req_id}", "ok")
            self.hce_status.emit("HCE provisioning complete.")
        else:
            self.hce_status.emit(f"HCE provisioning failed: {info}")
        self.hce_complete.emit(success, info)
        return success
