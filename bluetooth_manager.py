#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: bluetooth_manager.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Cross-platform Bluetooth management with BLE for Android companion apps

Classes:
- BluetoothManager: Main Bluetooth management class
- BLERelaySession: BLE session manager for Android communication
- BluetoothDevice: Represents a connected device
- BluetoothServer: Server for Android connections
- AndroidCompanion: Android app interface

Functions:
- detect_bluetooth_stack(): Detect available Bluetooth libraries
- encrypt_data(): Encrypt data for transmission
- decrypt_data(): Decrypt received data

This module provides cross-platform Bluetooth connectivity for the Android
companion app, handling device discovery, pairing, data encryption, and
real-time synchronization of card data and transaction information.

Enhanced with BLE Central mode for GATT server communication with Android devices.
"""

import logging
import asyncio
import json
import base64
import uuid
import struct
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread

# BLE imports
try:
    import bleak
    from bleak import BleakScanner, BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic
    BLEAK_AVAILABLE = True
    logging.info("Bleak BLE library available")
except ImportError:
    BLEAK_AVAILABLE = False
    logging.warning("Bleak not available - install bleak for BLE support")

# Legacy Bluetooth imports
try:
    import bluetooth
    PYBLUEZ_AVAILABLE = True
    logging.info("PyBluez classic Bluetooth available")
except ImportError:
    PYBLUEZ_AVAILABLE = False
    logging.warning("PyBluez not available - install pybluez for classic Bluetooth")

# Android companion GATT service UUIDs
ANDROID_SERVICE_UUID = "12345678-1234-5678-9abc-123456789abc"
ANDROID_RX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abd"  # Write to Android
ANDROID_TX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abe"  # Notifications from Android

class BLESessionState(Enum):
    """BLE session states."""
    IDLE = "idle"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SENDING = "sending"
    COMPLETED = "completed"
    ERROR = "error"

class BLEMessageType(Enum):
    """BLE message types for Android communication."""
    HELLO = 0x01
    SESSION_START = 0x02
    APDU_TRACE = 0x03
    CRYPTOGRAM_DATA = 0x04
    SESSION_END = 0x05
    ACK = 0x06
    ERROR = 0x07

@dataclass
class BLEMessage:
    """BLE message structure for Android communication."""
    message_type: BLEMessageType
    sequence_number: int
    total_fragments: int
    fragment_index: int
    payload: bytes
    
    def to_bytes(self) -> bytes:
        """Convert message to wire format."""
        header = struct.pack('<BBHH', 
                           self.message_type.value,
                           self.sequence_number,
                           self.total_fragments,
                           self.fragment_index)
        length = len(self.payload)
        return struct.pack('<H', length) + header + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BLEMessage':
        """Parse message from wire format."""
        if len(data) < 8:
            raise ValueError("Message too short")
        
        length = struct.unpack('<H', data[0:2])[0]
        msg_type, seq_num, total_frags, frag_idx = struct.unpack('<BBHH', data[2:8])
        payload = data[8:8+length]
        
        return cls(
            message_type=BLEMessageType(msg_type),
            sequence_number=seq_num,
            total_fragments=total_frags,
            fragment_index=frag_idx,
            payload=payload
        )

class BLERelaySession(QObject):
    """Manages BLE session for Android companion app communication."""
    
    # Signals for status updates
    session_started = pyqtSignal(str)  # device_name
    session_ended = pyqtSignal()
    message_sent = pyqtSignal(str, int)  # message_type, size
    message_received = pyqtSignal(str, bytes)  # message_type, data
    connection_status = pyqtSignal(str)  # status
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: Optional[BleakClient] = None
        self.device_address: Optional[str] = None
        self.state = BLESessionState.IDLE
        self.sequence_number = 0
        self.message_fragments: Dict[int, List[BLEMessage]] = {}
        self.tx_characteristic: Optional[BleakGATTCharacteristic] = None
        self.rx_characteristic: Optional[BleakGATTCharacteristic] = None
        self.session_data = {}
        
    async def scan_for_devices(self, timeout: float = 10.0) -> List[str]:
        """Scan for Android companion devices."""
        if not BLEAK_AVAILABLE:
            raise RuntimeError("BLE not available - install bleak")
            
        self.state = BLESessionState.SCANNING
        devices = []
        
        try:
            scanner = BleakScanner()
            discovered = await scanner.discover(timeout=timeout)
            
            for device in discovered:
                # Look for devices advertising our service
                if device.name and "NFSP00F3R" in device.name:
                    devices.append(f"{device.name} ({device.address})")
                    logging.info(f"Found Android companion: {device.name} - {device.address}")
                    
        except Exception as e:
            logging.error(f"BLE scan error: {e}")
            self.state = BLESessionState.ERROR
            self.error_occurred.emit(f"Scan failed: {e}")
            
        return devices
        
    async def connect_to_device(self, device_address: str) -> bool:
        """Connect to Android companion device."""
        if not BLEAK_AVAILABLE:
            raise RuntimeError("BLE not available")
            
        self.state = BLESessionState.CONNECTING
        self.device_address = device_address
        
        try:
            self.client = BleakClient(device_address)
            await self.client.connect()
            
            # Discover services
            services = await self.client.get_services()
            service = services.get_service(ANDROID_SERVICE_UUID)
            
            if not service:
                raise RuntimeError("Android service not found")
                
            # Get characteristics
            self.rx_characteristic = service.get_characteristic(ANDROID_RX_CHAR_UUID)
            self.tx_characteristic = service.get_characteristic(ANDROID_TX_CHAR_UUID)
            
            if not (self.rx_characteristic and self.tx_characteristic):
                raise RuntimeError("Required characteristics not found")
                
            # Enable notifications
            await self.client.start_notify(self.tx_characteristic, self._notification_handler)
            
            self.state = BLESessionState.CONNECTED
            self.connection_status.emit("Connected to Android device")
            
            # Send hello message
            await self._send_hello()
            
            return True
            
        except Exception as e:
            logging.error(f"BLE connection error: {e}")
            self.state = BLESessionState.ERROR
            self.error_occurred.emit(f"Connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Android device."""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.state = BLESessionState.IDLE
            self.session_ended.emit()
            logging.info("Disconnected from Android device")
        except Exception as e:
            logging.error(f"Disconnect error: {e}")
            
    async def send_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Send complete session data to Android."""
        if self.state != BLESessionState.CONNECTED:
            return False
            
        try:
            self.state = BLESessionState.SENDING
            
            # Convert session to JSON
            json_data = json.dumps(session_data, indent=2)
            payload = json_data.encode('utf-8')
            
            # Send in fragments if needed
            await self._send_fragmented_message(BLEMessageType.SESSION_START, payload)
            
            self.message_sent.emit("session_data", len(payload))
            logging.info(f"Sent session data: {len(payload)} bytes")
            
            return True
            
        except Exception as e:
            logging.error(f"Send session error: {e}")
            self.error_occurred.emit(f"Send failed: {e}")
            return False
            
    async def send_apdu_trace(self, apdu_data: List[Dict[str, Any]]) -> bool:
        """Send APDU trace data to Android."""
        if self.state != BLESessionState.CONNECTED:
            return False
            
        try:
            # Convert APDU trace to compact format
            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "apdus": apdu_data
            }
            
            json_data = json.dumps(trace_data)
            payload = json_data.encode('utf-8')
            
            await self._send_fragmented_message(BLEMessageType.APDU_TRACE, payload)
            
            self.message_sent.emit("apdu_trace", len(payload))
            logging.info(f"Sent APDU trace: {len(apdu_data)} commands")
            
            return True
            
        except Exception as e:
            logging.error(f"Send APDU trace error: {e}")
            return False
            
    async def _send_hello(self):
        """Send hello message to establish session."""
        hello_data = {
            "version": "5.0",
            "timestamp": datetime.now().isoformat(),
            "capabilities": ["session_data", "apdu_trace", "cryptogram_data"]
        }
        
        payload = json.dumps(hello_data).encode('utf-8')
        await self._send_fragmented_message(BLEMessageType.HELLO, payload)
        
    async def _send_fragmented_message(self, msg_type: BLEMessageType, payload: bytes):
        """Send message with fragmentation support."""
        max_fragment_size = 20  # BLE MTU limitation
        total_fragments = (len(payload) + max_fragment_size - 1) // max_fragment_size
        
        self.sequence_number += 1
        
        for i in range(total_fragments):
            start_idx = i * max_fragment_size
            end_idx = min((i + 1) * max_fragment_size, len(payload))
            fragment_payload = payload[start_idx:end_idx]
            
            message = BLEMessage(
                message_type=msg_type,
                sequence_number=self.sequence_number,
                total_fragments=total_fragments,
                fragment_index=i,
                payload=fragment_payload
            )
            
            # Send fragment
            data = message.to_bytes()
            await self.client.write_gatt_char(self.rx_characteristic, data)
            
            # Small delay between fragments
            await asyncio.sleep(0.01)
            
    def _notification_handler(self, sender: int, data: bytes):
        """Handle notifications from Android device."""
        try:
            message = BLEMessage.from_bytes(data)
            
            # Handle fragmented messages
            seq_num = message.sequence_number
            if seq_num not in self.message_fragments:
                self.message_fragments[seq_num] = [None] * message.total_fragments
                
            self.message_fragments[seq_num][message.fragment_index] = message
            
            # Check if all fragments received
            fragments = self.message_fragments[seq_num]
            if all(f is not None for f in fragments):
                # Reassemble message
                complete_payload = b''.join(f.payload for f in fragments)
                self._handle_complete_message(message.message_type, complete_payload)
                del self.message_fragments[seq_num]
                
        except Exception as e:
            logging.error(f"Notification handler error: {e}")
            
    def _handle_complete_message(self, msg_type: BLEMessageType, payload: bytes):
        """Handle complete received message."""
        try:
            if msg_type == BLEMessageType.ACK:
                logging.info("Received ACK from Android")
            elif msg_type == BLEMessageType.ERROR:
                error_msg = payload.decode('utf-8')
                logging.error(f"Android error: {error_msg}")
                self.error_occurred.emit(f"Android: {error_msg}")
            else:
                # Parse JSON payload
                data = json.loads(payload.decode('utf-8'))
                self.message_received.emit(msg_type.name, payload)
                logging.info(f"Received {msg_type.name}: {len(payload)} bytes")
                
        except Exception as e:
            logging.error(f"Message handling error: {e}")
import threading
import time
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Try to import Bluetooth libraries
try:
    import bluetooth
    PYBLUEZ_AVAILABLE = True
except ImportError:
    PYBLUEZ_AVAILABLE = False
    logging.warning("PyBluez not available - install pybluez for legacy Bluetooth support")

try:
    import asyncio
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    logging.warning("Bleak not available - install bleak for BLE support")

@dataclass
class BluetoothDevice:
    """Represents a Bluetooth device."""
    address: str
    name: str
    device_type: str  # 'classic' or 'ble'
    rssi: int = 0
    paired: bool = False
    connected: bool = False
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now()

@dataclass
class AndroidMessage:
    """Message structure for Android communication."""
    msg_type: str
    timestamp: float
    data: Dict[str, Any]
    message_id: str = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = secrets.token_hex(8)

class BluetoothSecurityManager:
    """Handles encryption and security for Bluetooth communications."""
    
    def __init__(self, passphrase: str = None):
        self.logger = logging.getLogger(__name__)
        self.passphrase = passphrase or "NFSP00F3R_V5_DEFAULT_KEY"
        self.cipher_suite = None
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Setup Fernet encryption with PBKDF2."""
        try:
            password = self.passphrase.encode()
            salt = b'nfsp00f3r_salt_v5'  # In production, use random salt per session
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.cipher_suite = Fernet(key)
            
            self.logger.info("Bluetooth encryption initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to setup encryption: {e}")
            self.cipher_suite = None
    
    def encrypt_message(self, data: dict) -> bytes:
        """Encrypt a message for transmission."""
        try:
            if not self.cipher_suite:
                self.logger.warning("No encryption available, sending plaintext")
                return json.dumps(data).encode('utf-8')
            
            json_data = json.dumps(data)
            encrypted = self.cipher_suite.encrypt(json_data.encode('utf-8'))
            return encrypted
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            return json.dumps(data).encode('utf-8')
    
    def decrypt_message(self, encrypted_data: bytes) -> dict:
        """Decrypt a received message."""
        try:
            if not self.cipher_suite:
                self.logger.warning("No decryption available, assuming plaintext")
                return json.loads(encrypted_data.decode('utf-8'))
            
            decrypted = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            # Try as plaintext fallback
            try:
                return json.loads(encrypted_data.decode('utf-8'))
            except:
                return {"error": "Failed to decrypt message"}

class BluetoothServer(QThread):
    """Bluetooth server thread for accepting Android connections."""
    
    client_connected = pyqtSignal(str, str)  # address, name
    client_disconnected = pyqtSignal(str)    # address
    message_received = pyqtSignal(str, dict) # address, message
    error_occurred = pyqtSignal(str)         # error message
    
    def __init__(self, bluetooth_manager):
        super().__init__()
        self.bluetooth_manager = bluetooth_manager
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.server_socket = None
        self.client_sockets = {}
        self.security_manager = BluetoothSecurityManager()
        
    def run(self):
        """Main server loop."""
        if PYBLUEZ_AVAILABLE:
            self._run_classic_server()
        else:
            self.logger.error("No Bluetooth stack available for server")
            self.error_occurred.emit("No Bluetooth stack available")
    
    def _run_classic_server(self):
        """Run classic Bluetooth server."""
        try:
            self.server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            port = bluetooth.PORT_ANY
            
            self.server_socket.bind(("", port))
            self.server_socket.listen(1)
            
            # Advertise service
            bluetooth.advertise_service(
                self.server_socket,
                "NFSP00F3R EMV Terminal",
                service_id="1e0ca4ea-299d-4335-93eb-27fcfe7fa848",
                service_classes=[bluetooth.SERIAL_PORT_CLASS],
                profiles=[bluetooth.SERIAL_PORT_PROFILE]
            )
            
            port = self.server_socket.getsockname()[1]
            self.logger.info(f"Bluetooth server listening on port {port}")
            
            self.running = True
            
            while self.running:
                try:
                    client_socket, client_info = self.server_socket.accept()
                    client_address = client_info[0]
                    
                    self.logger.info(f"Client connected: {client_address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except bluetooth.BluetoothError as e:
                    if self.running:
                        self.logger.error(f"Bluetooth server error: {e}")
                        time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Failed to start Bluetooth server: {e}")
            self.error_occurred.emit(f"Server failed: {e}")
        finally:
            self._cleanup_server()
    
    def _handle_client(self, client_socket, client_address):
        """Handle individual client connection."""
        try:
            self.client_sockets[client_address] = client_socket
            
            # Get client name
            try:
                client_name = bluetooth.lookup_name(client_address) or "Unknown"
            except:
                client_name = "Unknown"
            
            self.client_connected.emit(client_address, client_name)
            
            while self.running:
                try:
                    # Receive data
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    # Decrypt and parse message
                    try:
                        message = self.security_manager.decrypt_message(data)
                        self.message_received.emit(client_address, message)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to parse message from {client_address}: {e}")
                    
                except bluetooth.BluetoothError:
                    break
                except Exception as e:
                    self.logger.error(f"Error handling client {client_address}: {e}")
                    break
            
        except Exception as e:
            self.logger.error(f"Client handler error for {client_address}: {e}")
        finally:
            self._cleanup_client(client_address)
    
    def _cleanup_client(self, client_address):
        """Clean up client connection."""
        try:
            if client_address in self.client_sockets:
                self.client_sockets[client_address].close()
                del self.client_sockets[client_address]
            
            self.client_disconnected.emit(client_address)
            self.logger.info(f"Client disconnected: {client_address}")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up client {client_address}: {e}")
    
    def _cleanup_server(self):
        """Clean up server resources."""
        try:
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            
            # Close all client connections
            for address, socket in list(self.client_sockets.items()):
                try:
                    socket.close()
                except:
                    pass
            
            self.client_sockets.clear()
            
        except Exception as e:
            self.logger.error(f"Error cleaning up server: {e}")
    
    def send_to_client(self, client_address: str, message: dict) -> bool:
        """Send message to specific client."""
        try:
            if client_address not in self.client_sockets:
                return False
            
            encrypted_data = self.security_manager.encrypt_message(message)
            self.client_sockets[client_address].send(encrypted_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send to client {client_address}: {e}")
            return False
    
    def broadcast_to_clients(self, message: dict):
        """Broadcast message to all connected clients."""
        for address in list(self.client_sockets.keys()):
            self.send_to_client(address, message)
    
    def stop_server(self):
        """Stop the Bluetooth server."""
        self.running = False
        self._cleanup_server()

class AndroidCompanion:
    """Interface for communicating with Android companion app."""
    
    def __init__(self, bluetooth_manager):
        self.bluetooth_manager = bluetooth_manager
        self.logger = logging.getLogger(__name__)
        self.connected_devices = {}
        
    def send_card_data(self, device_address: str, card_data: dict) -> bool:
        """Send card data to Android device."""
        message = AndroidMessage(
            msg_type="card_data",
            timestamp=time.time(),
            data=card_data
        )
        
        return self.bluetooth_manager.send_message(device_address, asdict(message))
    
    def send_transaction_data(self, device_address: str, transaction_data: dict) -> bool:
        """Send transaction data to Android device."""
        message = AndroidMessage(
            msg_type="transaction_data",
            timestamp=time.time(),
            data=transaction_data
        )
        
        return self.bluetooth_manager.send_message(device_address, asdict(message))
    
    def send_reader_status(self, device_address: str, readers_status: dict) -> bool:
        """Send reader status to Android device."""
        message = AndroidMessage(
            msg_type="reader_status",
            timestamp=time.time(),
            data=readers_status
        )
        
        return self.bluetooth_manager.send_message(device_address, asdict(message))
    
    def send_settings(self, device_address: str, settings: dict) -> bool:
        """Send application settings to Android device."""
        message = AndroidMessage(
            msg_type="settings",
            timestamp=time.time(),
            data=settings
        )
        
        return self.bluetooth_manager.send_message(device_address, asdict(message))
    
    def request_remote_operation(self, device_address: str, operation: str, parameters: dict = None) -> bool:
        """Request Android device to perform an operation."""
        message = AndroidMessage(
            msg_type="remote_operation",
            timestamp=time.time(),
            data={
                "operation": operation,
                "parameters": parameters or {}
            }
        )
        
        return self.bluetooth_manager.send_message(device_address, asdict(message))
    
    def handle_android_message(self, device_address: str, message: dict):
        """Handle incoming message from Android device."""
        try:
            msg_type = message.get("msg_type", "unknown")
            data = message.get("data", {})
            
            if msg_type == "ping":
                self._handle_ping(device_address, data)
            elif msg_type == "remote_command":
                self._handle_remote_command(device_address, data)
            elif msg_type == "settings_update":
                self._handle_settings_update(device_address, data)
            elif msg_type == "file_request":
                self._handle_file_request(device_address, data)
            else:
                self.logger.warning(f"Unknown message type from {device_address}: {msg_type}")
            
        except Exception as e:
            self.logger.error(f"Error handling Android message: {e}")
    
    def _handle_ping(self, device_address: str, data: dict):
        """Handle ping from Android device."""
        response = AndroidMessage(
            msg_type="pong",
            timestamp=time.time(),
            data={"server_time": time.time()}
        )
        
        self.bluetooth_manager.send_message(device_address, asdict(response))
    
    def _handle_remote_command(self, device_address: str, data: dict):
        """Handle remote command from Android device."""
        command = data.get("command", "")
        
        if command == "read_card":
            # Trigger card read on specified reader
            reader_name = data.get("reader", "")
            self.bluetooth_manager.request_card_read.emit(reader_name)
        
        elif command == "stop_reading":
            # Stop card reading
            self.bluetooth_manager.request_stop_reading.emit()
        
        elif command == "get_readers":
            # Send current reader list
            readers_info = self.bluetooth_manager.get_readers_info()
            self.send_reader_status(device_address, readers_info)
        
        elif command == "export_card":
            # Export card data
            card_id = data.get("card_id", "")
            self.bluetooth_manager.request_card_export.emit(card_id)
    
    def _handle_settings_update(self, device_address: str, data: dict):
        """Handle settings update from Android device."""
        settings = data.get("settings", {})
        self.bluetooth_manager.settings_update_received.emit(settings)
    
    def _handle_file_request(self, device_address: str, data: dict):
        """Handle file request from Android device."""
        file_type = data.get("file_type", "")
        file_id = data.get("file_id", "")
        
        # Emit signal for main application to handle
        self.bluetooth_manager.file_request_received.emit(device_address, file_type, file_id)

class BluetoothManager(QObject):
    """
    Main Bluetooth manager class.
    Handles device discovery, connections, and communication with Android app.
    """
    
    # Signals
    device_discovered = pyqtSignal(dict)     # device info
    device_connected = pyqtSignal(str, str)  # address, name
    device_disconnected = pyqtSignal(str)    # address
    message_received = pyqtSignal(str, dict) # address, message
    error_occurred = pyqtSignal(str)         # error message
    
    # Android companion signals
    request_card_read = pyqtSignal(str)      # reader name
    request_stop_reading = pyqtSignal()
    request_card_export = pyqtSignal(str)    # card id
    settings_update_received = pyqtSignal(dict)
    file_request_received = pyqtSignal(str, str, str)  # address, file_type, file_id
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Available Bluetooth stacks
        self.capabilities = {
            'pybluez': PYBLUEZ_AVAILABLE,
            'bleak': BLEAK_AVAILABLE
        }
        
        # Connected devices
        self.devices: Dict[str, BluetoothDevice] = {}
        
        # Server
        self.server = None
        
        # Android companion interface
        self.android_companion = AndroidCompanion(self)
        
        # Discovery thread
        self.discovery_thread = None
        self.discovering = False
        
        self.logger.info(f"Bluetooth manager initialized with capabilities: {self.capabilities}")
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get available Bluetooth capabilities."""
        return self.capabilities.copy()
    
    def start_server(self) -> bool:
        """Start Bluetooth server for Android connections."""
        try:
            if self.server and self.server.isRunning():
                self.logger.warning("Bluetooth server already running")
                return True
            
            if not PYBLUEZ_AVAILABLE:
                self.error_occurred.emit("No Bluetooth stack available for server")
                return False
            
            self.server = BluetoothServer(self)
            
            # Connect signals
            self.server.client_connected.connect(self.device_connected)
            self.server.client_disconnected.connect(self.device_disconnected)
            self.server.message_received.connect(self._on_message_received)
            self.server.error_occurred.connect(self.error_occurred)
            
            self.server.start()
            
            self.logger.info("Bluetooth server started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Bluetooth server: {e}")
            self.error_occurred.emit(f"Server start failed: {e}")
            return False
    
    def stop_server(self):
        """Stop Bluetooth server."""
        try:
            if self.server:
                self.server.stop_server()
                self.server.wait()
                self.server = None
            
            self.logger.info("Bluetooth server stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Bluetooth server: {e}")
    
    def start_discovery(self, duration: int = 10):
        """Start device discovery."""
        try:
            if self.discovering:
                self.logger.warning("Discovery already in progress")
                return
            
            if not any(self.capabilities.values()):
                self.error_occurred.emit("No Bluetooth stack available for discovery")
                return
            
            self.discovering = True
            
            # Use classic Bluetooth discovery if available
            if PYBLUEZ_AVAILABLE:
                self.discovery_thread = threading.Thread(
                    target=self._classic_discovery,
                    args=(duration,),
                    daemon=True
                )
                self.discovery_thread.start()
            elif BLEAK_AVAILABLE:
                # BLE discovery
                self.discovery_thread = threading.Thread(
                    target=self._ble_discovery,
                    args=(duration,),
                    daemon=True
                )
                self.discovery_thread.start()
            
            self.logger.info(f"Started device discovery for {duration} seconds")
            
        except Exception as e:
            self.logger.error(f"Failed to start discovery: {e}")
            self.discovering = False
    
    def stop_discovery(self):
        """Stop device discovery."""
        self.discovering = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=2)
        self.logger.info("Stopped device discovery")
    
    def _classic_discovery(self, duration: int):
        """Classic Bluetooth device discovery."""
        try:
            nearby_devices = bluetooth.discover_devices(
                duration=duration,
                lookup_names=True,
                flush_cache=True
            )
            
            for address, name in nearby_devices:
                if not self.discovering:
                    break
                
                device = BluetoothDevice(
                    address=address,
                    name=name or "Unknown",
                    device_type="classic"
                )
                
                self.devices[address] = device
                self.device_discovered.emit(asdict(device))
            
        except Exception as e:
            self.logger.error(f"Classic discovery error: {e}")
        finally:
            self.discovering = False
    
    def _ble_discovery(self, duration: int):
        """BLE device discovery."""
        try:
            async def scan():
                devices = await BleakScanner.discover(timeout=duration)
                for device in devices:
                    if not self.discovering:
                        break
                    
                    ble_device = BluetoothDevice(
                        address=device.address,
                        name=device.name or "Unknown",
                        device_type="ble",
                        rssi=device.rssi
                    )
                    
                    self.devices[device.address] = ble_device
                    self.device_discovered.emit(asdict(ble_device))
            
            # Run in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(scan())
            loop.close()
            
        except Exception as e:
            self.logger.error(f"BLE discovery error: {e}")
        finally:
            self.discovering = False
    
    def send_message(self, device_address: str, message: dict) -> bool:
        """Send message to specific device."""
        try:
            if not self.server:
                return False
            
            return self.server.send_to_client(device_address, message)
            
        except Exception as e:
            self.logger.error(f"Failed to send message to {device_address}: {e}")
            return False
    
    def broadcast_message(self, message: dict):
        """Broadcast message to all connected devices."""
        try:
            if self.server:
                self.server.broadcast_to_clients(message)
        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
    
    def get_connected_devices(self) -> List[BluetoothDevice]:
        """Get list of connected devices."""
        connected = []
        for device in self.devices.values():
            if device.connected:
                connected.append(device)
        return connected
    
    def get_discovered_devices(self) -> List[BluetoothDevice]:
        """Get list of all discovered devices."""
        return list(self.devices.values())
    
    def get_readers_info(self) -> dict:
        """Get current readers information for Android."""
        # This would be implemented by the main application
        return {
            "readers": [],
            "timestamp": time.time()
        }
    
    def _on_message_received(self, device_address: str, message: dict):
        """Handle incoming message from device."""
        try:
            # Update device connection status
            if device_address in self.devices:
                self.devices[device_address].connected = True
                self.devices[device_address].last_seen = datetime.now()
            
            # Handle Android-specific messages
            self.android_companion.handle_android_message(device_address, message)
            
            # Emit general message signal
            self.message_received.emit(device_address, message)
            
        except Exception as e:
            self.logger.error(f"Error handling message from {device_address}: {e}")
    
    def cleanup(self):
        """Clean up Bluetooth manager resources."""
        try:
            self.stop_discovery()
            self.stop_server()
            self.devices.clear()
            
            self.logger.info("Bluetooth manager cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up Bluetooth manager: {e}")

def detect_bluetooth_stack() -> Dict[str, bool]:
    """
    Detect available Bluetooth stacks.
    
    Returns:
        Dictionary of available stacks
    """
    return {
        'pybluez': PYBLUEZ_AVAILABLE,
        'bleak': BLEAK_AVAILABLE
    }

def encrypt_data(data: str, key: str) -> str:
    """
    Encrypt string data with a key.
    
    Args:
        data: Data to encrypt
        key: Encryption key
        
    Returns:
        Encrypted data as base64 string
    """
    try:
        security_manager = BluetoothSecurityManager(key)
        encrypted = security_manager.encrypt_message({"data": data})
        return base64.b64encode(encrypted).decode('utf-8')
    except Exception as e:
        logging.error(f"Encryption failed: {e}")
        return data

def decrypt_data(encrypted_data: str, key: str) -> str:
    """
    Decrypt base64 encoded data with a key.
    
    Args:
        encrypted_data: Base64 encoded encrypted data
        key: Decryption key
        
    Returns:
        Decrypted data string
    """
    try:
        security_manager = BluetoothSecurityManager(key)
        data_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted = security_manager.decrypt_message(data_bytes)
        return decrypted.get("data", "")
    except Exception as e:
        logging.error(f"Decryption failed: {e}")
        return encrypted_data
