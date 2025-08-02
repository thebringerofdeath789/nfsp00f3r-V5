# =====================================================================
# File: bluetooth_api.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Bluetooth API for phone companion synchronization and relay.
#   - Sets up an RFCOMM server using PyBluez.
#   - Accepts JSON commands from the Android app and emits signals.
#   - Sends JSON responses back over the socket.
#
# Functions:
#   - BluetoothAPI(service_uuid=None, port=None)
#       - start()
#       - stop()
#       - send_message(msg: dict)
#       - connection_made(sender_address)
#       - connection_lost()
#       - message_received(dict)
# =====================================================================

import threading
import json
try:
    import bluetooth
except ImportError:
    bluetooth = None

from PyQt5.QtCore import QObject, pyqtSignal

class BluetoothAPI(QObject):
    connection_made = pyqtSignal(str)
    connection_lost = pyqtSignal()
    message_received = pyqtSignal(dict)

    def __init__(self, service_uuid="94f39d29-7d6d-437d-973b-fba39e49d4ee", port=3):
        super().__init__()
        self.service_uuid = service_uuid
        self.port = port
        self.server_sock = None
        self.client_sock = None
        self.client_info = None
        self._running = False
        self._thread = None

    def start(self):
        """Start the RFCOMM server thread."""
        if bluetooth is None:
            raise RuntimeError("PyBluez not installed")
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the server and close sockets."""
        self._running = False
        if self.client_sock:
            try:
                self.client_sock.close()
            except Exception:
                pass
            self.client_sock = None
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None
        self.connection_lost.emit()

    def send_message(self, msg: dict):
        """
        Send a JSON-encoded message to the connected client.
        Raises if no client is connected.
        """
        if not self.client_sock:
            raise RuntimeError("No Bluetooth client connected")
        try:
            payload = json.dumps(msg).encode("utf-8")
            # Prepend length header (4 bytes big-endian)
            length = len(payload).to_bytes(4, "big")
            self.client_sock.send(length + payload)
        except Exception as e:
            self.connection_lost.emit()
            self.client_sock = None
            raise

    def _server_loop(self):
        """Main server loop: wait for connection, receive JSON messages."""
        self.server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.server_sock.bind(("", self.port))
        self.server_sock.listen(1)
        bluetooth.advertise_service(
            self.server_sock,
            "nfsp00f3rService",
            service_id=self.service_uuid,
            service_classes=[self.service_uuid, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE]
        )
        try:
            while self._running:
                # Accept client
                client, info = self.server_sock.accept()
                self.client_sock = client
                self.client_info = info
                self.connection_made.emit(f"{info[0]}:{info[1]}")
                # Receive loop
                try:
                    while self._running:
                        # Read 4-byte length
                        header = self.client_sock.recv(4)
                        if not header:
                            break
                        length = int.from_bytes(header, "big")
                        data = b""
                        while len(data) < length:
                            chunk = self.client_sock.recv(length - len(data))
                            if not chunk:
                                break
                            data += chunk
                        if not data:
                            break
                        try:
                            msg = json.loads(data.decode("utf-8"))
                            self.message_received.emit(msg)
                        except json.JSONDecodeError:
                            # Malformed JSON, ignore or log
                            continue
                finally:
                    # Client disconnected
                    self.client_sock.close()
                    self.client_sock = None
                    self.connection_lost.emit()
        finally:
            if self.server_sock:
                self.server_sock.close()
                self.server_sock = None
            self._running = False
