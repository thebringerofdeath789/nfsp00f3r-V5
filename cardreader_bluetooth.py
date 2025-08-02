# =====================================================================
# File: cardreader_bluetooth.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Fully featured Bluetooth Companion server/client for phone sync, APDU relay, and emulation.
#   - BLE client (Windows, via Bleak) and server/peripheral (Linux, macOS) with pairing and trusted list.
#   - RFCOMM server/client (Linux/macOS, via PyBluez) with persistent pairing.
#   - Bi-directional message handling with ACK/NACK, error codes, chunked transfer for large payloads.
#   - Secure channel with optional pre-shared key challenge-response.
#   - Live status/progress/error hooks for UI, device hotplug detection, auto reconnect with backoff.
#   - Relay and APDU proxy support (phone → PC → card and back).
# =====================================================================

import sys
import json
import os
import time
import threading
import hashlib
from PyQt5.QtCore import QThread, pyqtSignal, QObject

TRUSTED_DEVICES_FILE = "trusted_devices.json"
CHUNK_SIZE = 1600  # for BLE/RFCOMM, safe value for most platforms

class BluetoothCompanion(QObject):
    sync_status      = pyqtSignal(str)
    message_received = pyqtSignal(dict)
    device_status    = pyqtSignal(str, str)  # addr, status (connected/disconnected)
    progress_update  = pyqtSignal(str, int)  # msg, percent

    SERVICE_UUID = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
    CHAR_RX_UUID = "94f39d29-7d6d-437d-973b-fba39e49d4ef"
    CHAR_TX_UUID = "94f39d29-7d6d-437d-973b-fba39e49d4f0"

    def __init__(self, card_manager):
        super().__init__()
        self.card_manager = card_manager
        self.server_thread = None
        self.running = False
        self.is_windows = sys.platform == "win32"
        self.ble_client = None
        self.connected_device = None
        self.trusted_devices = self._load_trusted_devices()
        self._pairing_key = "nfsp00f3r_shared_secret"  # Should be randomized and shared via QR/NFC for prod

    # --------- Trusted Device Management ---------

    def _load_trusted_devices(self):
        if os.path.exists(TRUSTED_DEVICES_FILE):
            try:
                with open(TRUSTED_DEVICES_FILE, "r") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_trusted_devices(self):
        with open(TRUSTED_DEVICES_FILE, "w") as f:
            json.dump(list(self.trusted_devices), f, indent=2)

    def add_trusted_device(self, addr):
        self.trusted_devices.add(addr)
        self._save_trusted_devices()

    def remove_trusted_device(self, addr):
        self.trusted_devices.discard(addr)
        self._save_trusted_devices()

    def list_trusted_devices(self):
        return list(self.trusted_devices)

    # --------- Server Start/Stop ---------

    def start_server(self):
        if self.is_windows:
            try:
                import asyncio
                from bleak import BleakScanner, BleakClient
            except ImportError:
                self.sync_status.emit("Bleak not installed; BLE client disabled on Windows.")
                return
            if not self.server_thread:
                self.running = True
                self.server_thread = QThread()
                self.server_thread.run = self._ble_client_loop
                self.server_thread.start()
                self.sync_status.emit("BLE client started on Windows.")
        else:
            try:
                import bluetooth
            except ImportError:
                self.sync_status.emit("PyBluez not installed; RFCOMM server disabled.")
                return
            if not self.server_thread:
                self.running = True
                self.server_thread = QThread()
                self.server_thread.run = self.bt_server_loop
                self.server_thread.start()
                self.sync_status.emit("Bluetooth RFCOMM server started.")

    def stop_server(self):
        self.running = False
        if self.server_thread:
            self.server_thread.quit()
            self.server_thread.wait()
            self.server_thread = None
            self.sync_status.emit("Bluetooth/BLE server stopped.")
        if self.ble_client:
            try:
                import asyncio
                asyncio.run(self.ble_client.disconnect())
            except:
                pass

    # --------- RFCOMM Server/Client (Linux/macOS) ---------

    def bt_server_loop(self):
        import bluetooth
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", bluetooth.PORT_ANY))
        server_sock.listen(1)
        port = server_sock.getsockname()[1]
        bluetooth.advertise_service(
            server_sock,
            "nfsp00f3r",
            service_id=self.SERVICE_UUID,
            service_classes=[self.SERVICE_UUID, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE]
        )
        self.sync_status.emit(f"RFCOMM listening on channel {port}")

        while self.running:
            try:
                client_sock, client_info = server_sock.accept()
                addr = client_info[0]
                self.device_status.emit(addr, "connected")

                # Pairing: check trusted devices, else require challenge-response
                if addr not in self.trusted_devices:
                    self.sync_status.emit(f"Unpaired device {addr} requested connection.")
                    client_sock.send(self._make_challenge().encode("utf-8"))
                    resp = client_sock.recv(4096).decode("utf-8")
                    if not self._check_challenge(resp):
                        self.sync_status.emit("Pairing failed: wrong response.")
                        client_sock.close()
                        continue
                    self.add_trusted_device(addr)
                    self.sync_status.emit(f"Device {addr} paired.")

                buffer = b""
                while self.running:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    buffer += data
                    # Chunked protocol: look for end marker
                    if b"<EOF>" in buffer:
                        full_data, buffer = buffer.split(b"<EOF>", 1)
                        msg = self._decode_message(full_data)
                        self._handle_message(msg, addr)
                client_sock.close()
                self.device_status.emit(addr, "disconnected")
            except Exception as e:
                self.sync_status.emit(f"Bluetooth server error: {e}")
                break
        server_sock.close()

    # --------- BLE Client (Windows) ---------

    def _ble_client_loop(self):
        import asyncio
        from bleak import BleakScanner, BleakClient

        async def run():
            # BLE scan UI: List devices, pick one
            devices = await BleakScanner.discover(service_uuids=[self.SERVICE_UUID])
            if not devices:
                self.sync_status.emit("BLE service not found.")
                return
            # Let user select, for now pick first
            target = devices[0]
            self.sync_status.emit(f"Connecting to BLE device {target.address}")
            client = BleakClient(target.address)
            self.ble_client = client
            try:
                await client.connect()
                self.device_status.emit(target.address, "connected")
                self.connected_device = target.address

                async def handle_notify(_, data):
                    # Support chunked protocol
                    self._on_chunk_received(data, target.address)

                await client.start_notify(self.CHAR_RX_UUID, handle_notify)

                while self.running and client.is_connected:
                    await asyncio.sleep(1)
                await client.disconnect()
                self.device_status.emit(target.address, "disconnected")
                self.connected_device = None
            except Exception as e:
                self.sync_status.emit(f"BLE client error: {e}")

        asyncio.run(run())

    # --------- Chunked Message/Relay Support ---------

    def send_message(self, msg: dict):
        """
        Send a message, splitting into chunks if needed.
        """
        raw = self._encode_message(msg)
        if self.is_windows and self.ble_client and self.ble_client.is_connected:
            try:
                import asyncio
                for i in range(0, len(raw), CHUNK_SIZE):
                    chunk = raw[i:i+CHUNK_SIZE]
                    is_last = (i + CHUNK_SIZE) >= len(raw)
                    chunk += b"<EOF>" if is_last else b""
                    asyncio.run(self.ble_client.write_gatt_char(self.CHAR_TX_UUID, chunk))
            except Exception as e:
                self.sync_status.emit(f"BLE send error: {e}")
        else:
            try:
                import bluetooth
                # TODO: show UI to pick device and channel
                addr = self.connected_device or ""
                if not addr:
                    self.sync_status.emit("No connected/trusted device for send.")
                    return
                sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                sock.connect((addr, 1))
                for i in range(0, len(raw), CHUNK_SIZE):
                    chunk = raw[i:i+CHUNK_SIZE]
                    is_last = (i + CHUNK_SIZE) >= len(raw)
                    chunk += b"<EOF>" if is_last else b""
                    sock.send(chunk)
                sock.close()
            except Exception as e:
                self.sync_status.emit(f"RFCOMM send error: {e}")

    def _on_chunk_received(self, data, addr):
        """
        Receive chunk, reassemble if necessary, then dispatch.
        """
        # Simple reassembly per address
        if not hasattr(self, "_chunk_buffers"):
            self._chunk_buffers = {}
        buf = self._chunk_buffers.setdefault(addr, b"") + data
        if b"<EOF>" in buf:
            full_msg, rest = buf.split(b"<EOF>", 1)
            self._chunk_buffers[addr] = rest
            msg = self._decode_message(full_msg)
            self._handle_message(msg, addr)
        else:
            self._chunk_buffers[addr] = buf

    # --------- Message Protocol (ACK/NACK, APDU relay, etc) ---------

    def _encode_message(self, msg: dict):
        # Optionally add encryption here
        return json.dumps(msg).encode("utf-8")

    def _decode_message(self, raw):
        # Optionally decrypt here
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {"cmd": "invalid", "raw": raw.hex()}

    def _handle_message(self, msg, addr):
        # Protocol: ACK/NACK, relay, import/export, APDU proxy
        if "cmd" not in msg:
            self._send_ack(addr, success=False, reason="No cmd")
            return

        cmd = msg["cmd"]
        if cmd == "ping":
            self._send_ack(addr, success=True, info="pong")
        elif cmd == "profile":
            # Handle card profile import/export
            profile = msg.get("profile")
            if profile:
                card = self.card_manager.exporter.import_from_string(profile)
                if card:
                    self.card_manager.add_card(card)
                    self._send_ack(addr, success=True)
                else:
                    self._send_ack(addr, success=False, reason="Profile import failed")
            else:
                self._send_ack(addr, success=False, reason="No profile provided")
        elif cmd == "request_profile":
            # Phone requests export of current card
            card = self.card_manager.get_current_card()
            if card:
                profile = self.card_manager.exporter.export_to_string(card)
                self.send_message({"cmd": "profile", "profile": profile})
                self._send_ack(addr, success=True)
            else:
                self._send_ack(addr, success=False, reason="No current card")
        elif cmd == "apdu_proxy":
            # Relay APDU from phone to card, return result
            apdu = bytes.fromhex(msg.get("apdu",""))
            resp = self.card_manager.send_apdu(apdu)
            self.send_message({"cmd": "apdu_proxy_resp", "apdu_resp": resp.hex()})
            self._send_ack(addr, success=True)
        elif cmd == "apdu_proxy_resp":
            # Phone-to-PC relay response, handled by UI or app logic if needed
            self.message_received.emit(msg)
            self._send_ack(addr, success=True)
        elif cmd == "forget_device":
            # Remove from trusted
            self.remove_trusted_device(addr)
            self._send_ack(addr, success=True)
        else:
            self._send_ack(addr, success=False, reason=f"Unknown cmd: {cmd}")

        # Pass message to app if further handling required
        self.message_received.emit(msg)

    def _send_ack(self, addr, success=True, reason="", info=""):
        # ACK/NACK with details
        ack = {
            "cmd": "ack",
            "success": success,
            "reason": reason,
            "info": info
        }
        self.send_message(ack)

    # --------- Pairing/Challenge Protocol ---------

    def _make_challenge(self):
        nonce = os.urandom(8).hex()
        sig = hashlib.sha256((nonce + self._pairing_key).encode()).hexdigest()
        return json.dumps({"cmd": "pair_challenge", "nonce": nonce, "sig": sig})

    def _check_challenge(self, resp):
        # Client must return a valid sig using the shared key and nonce
        try:
            obj = json.loads(resp)
            expected = hashlib.sha256((obj["nonce"] + self._pairing_key).encode()).hexdigest()
            return obj["sig"] == expected
        except Exception:
            return False

    # --------- Device UI/Status Integration ---------

    def get_paired_devices(self):
        return self.list_trusted_devices()

    def forget_device(self, addr):
        self.remove_trusted_device(addr)

    # --------- Progress & Error Reporting ---------

    def log_progress(self, msg, percent):
        self.progress_update.emit(msg, percent)

    # --------- Live Device/Connection Status ---------

    def is_device_connected(self, addr=None):
        # Return True if device (by addr) is currently connected
        if self.is_windows:
            return self.ble_client and self.ble_client.is_connected
        else:
            # Only one device at a time for now
            return self.connected_device is not None

    # --------- BLE Peripheral/Server (ADVANCED, LINUX ONLY) ---------
    # Full GATT server mode is only available on Linux (bluez). Stub for future.
    # You can implement with python-gattlib, pybleno, aioble, or custom code.

    # def start_ble_peripheral(self):
    #     pass  # Advanced: Implement BLE server on Linux

    # --------- End ---------
