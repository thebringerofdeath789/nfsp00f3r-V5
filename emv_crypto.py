# =====================================================================
# File: emv_crypto.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Implements all EMV cryptographic routines, including
#   cryptogram generation (ARQC/AAC/TC), signature logic,
#   and transaction orchestration for simulation/real keys.
# =====================================================================

import hashlib
import hmac
import os
import random
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class EmvCrypto:
    def __init__(self, issuer_keys=None, master_key=None):
        self.issuer_keys = issuer_keys or {}
        self.master_key = master_key

    def run_transaction(self, card):
        # High-level transaction orchestration for simulation and testing
        output = []
        cdol_tags = [
            '9F02', '9F03', '9F1A', '95', '5F2A', '9A', '9C', '9F37'
        ]
        cdol_data = self.build_cdol_data(card, cdol_tags)
        arqc = self.generate_arqc(card, cdol_data)
        ac_apdu = self.generate_ac_apdu(card, cdol_data, mode=1)  # ARQC mode
        output.append(f"ARQC: {arqc.hex()}")
        output.append(f"GENERATE AC APDU: {ac_apdu.hex()}")
        # Simulate card-side GENERATE AC processing, return dummy AAC/TC for now
        tc = self.generate_tc(card, cdol_data)
        output.append(f"Transaction Certificate (TC): {tc.hex()}")
        # Optionally SDA/DDA/CDA if card/profile supports
        # sda_sig = self.generate_sda(card, b'')  # Add logic for pubkey as needed
        # dda_sig = self.generate_dda(card, b'')
        # Optionally process issuer scripts if present
        # scripts = []
        return "\n".join(output)

    def build_cdol_data(self, card, required_tags):
        # Returns CDOL1/2 as bytes, filling tags with plausible or random values
        tag_values = {
            '9F02': int(1e6).to_bytes(6, 'big'),   # Amount Authorized (10.00)
            '9F03': b'\x00\x00\x00\x00\x00\x00',   # Amount Other
            '9F1A': b'\x02\x50',                   # Terminal Country Code (USA)
            '95':   b'\x00\x00\x00\x00\x00',       # TVR
            '5F2A': b'\x02\x50',                   # Currency (USD)
            '9A':   datetime.now().strftime('%y%m%d').encode(), # Transaction Date YYMMDD
            '9C':   b'\x00',                       # Transaction Type
            '9F37': os.urandom(4),                 # Unpredictable Number
        }
        data = b''
        for tag in required_tags:
            val = tag_values.get(tag)
            if val is None:
                # Try from card profile if available
                try:
                    val = bytes.fromhex(card.extract_tag(tag))
                except Exception:
                    val = b'\x00'
            data += val
        return data

    def derive_key(self, pan: str, seq: int = 0) -> bytes:
        # EMV key derivation (simulated). Replace with DES/3DES if using real keys.
        data = (pan + f"{seq:02d}").encode("utf-8")
        full = hashlib.sha256(data).digest()
        return full[:16]

    def generate_arqc(self, card, cdol_data: bytes) -> bytes:
        pan = card.pan
        seq_hex = card.extract_tag('5F34') or "00"
        seq = int(seq_hex, 16) if seq_hex else 0
        key = self.derive_key(pan, seq)
        mac = hmac.new(key, cdol_data, hashlib.sha256).digest()
        return mac[:8]

    def generate_tc(self, card, cdol_data: bytes) -> bytes:
        # Transaction certificate, just simulating with different MAC (dummy).
        pan = card.pan
        seq_hex = card.extract_tag('5F34') or "00"
        seq = int(seq_hex, 16) if seq_hex else 0
        key = self.derive_key(pan, seq)
        mac = hmac.new(key[::-1], cdol_data, hashlib.sha256).digest()
        return mac[:8]

    def generate_aac(self, card, cdol_data: bytes) -> bytes:
        # Application authentication cryptogram (dummy), all zeros.
        return b'\x00' * 8

    def generate_ac_apdu(self, card, cdol_data: bytes, mode: int) -> bytes:
        # Build GENERATE AC APDU (mode: 1=ARQC, 2=TC, 0=AAC)
        p1 = {0: 0x00, 1: 0x40, 2: 0x80}.get(mode, 0x40)
        apdu = bytes([
            0x80, 0xAE, p1, 0x00, len(cdol_data)
        ]) + cdol_data + b'\x00'
        return apdu

    def generate_sda(self, card, issuer_pubkey_bytes: bytes) -> bytes:
        # Static Data Authentication logic (stub, replace with real signature check if desired)
        # If you want, use issuer_pubkey_bytes with cryptography module for RSA verify
        return b"SDA_NOT_IMPLEMENTED"

    def generate_dda(self, card, icc_pubkey_bytes: bytes) -> bytes:
        # Dynamic Data Authentication logic (stub, replace with real signature check if desired)
        return b"DDA_NOT_IMPLEMENTED"

    def verify_signature(self, signature, data, pubkey):
        # For DDA/CDA. Example skeleton, not wired up in this demo.
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.exceptions import InvalidSignature
        try:
            pubkey.verify(
                signature,
                data,
                padding.PKCS1v15(),
                hashes.SHA1()
            )
            return True
        except Exception:
            return False

    def issuer_script_process(self, card, script_apdus: list) -> list:
        # Send issuer script APDUs and collect responses (simulation).
        results = []
        for apdu in script_apdus:
            resp = card.send_apdu(bytes.fromhex(apdu))
            results.append(resp.hex())
        return results
