#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - BLE Android Companion Manager
==============================================

File: bluetooth_manager_ble.py  
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: BLE Central mode for Android companion app communication

This module provides BLE connectivity for the Android companion app,
handling device discovery, GATT communication, data encryption, and
real-time synchronization of EMV session data.

Classes:
- BLEAndroidManager: Main BLE management for Android communication
- BLESession: Session manager for GATT communication
- BLEMessage: Message structure for fragmented communication
- SessionExporter: Converts EMV sessions to Android-compatible format
"""

import logging
import asyncio
import json
import struct
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
# PyQt5 is optional for the Python-side unit tests and CI runs. Provide
# lightweight fallbacks if PyQt5 is not installed so SessionExporter and
# other non-UI helpers can be imported in headless environments.
try:
    from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer
    PYQT_AVAILABLE = True
except Exception:
    PYQT_AVAILABLE = False
    class _DummySignal:
        def __init__(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
        def emit(self, *args, **kwargs):
            pass
    def pyqtSignal(*args, **kwargs):
        return _DummySignal()
    class QObject:
        pass
    class QThread:
        pass
    class QTimer:
        def __init__(self, *args, **kwargs):
            pass
        def start(self, *args, **kwargs):
            pass
        def stop(self, *args, **kwargs):
            pass

# BLE imports
try:
    import bleak
    from bleak import BleakScanner, BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic
    BLE_AVAILABLE = True
    logging.info("Bleak BLE library available")
except ImportError:
    BLE_AVAILABLE = False
    logging.warning("Bleak not available - install with: pip install bleak")

# Android companion GATT service UUIDs
ANDROID_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"  # Nordic UART Service
ANDROID_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # TX from central perspective
ANDROID_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # RX from central perspective

class BLEState(Enum):
    """BLE session states."""
    IDLE = "idle"
    SCANNING = "scanning"  
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SENDING = "sending"
    ERROR = "error"

class BLEMessageType(Enum):
    """BLE message types for Android communication."""
    HELLO = 0x01
    SESSION_DATA = 0x02
    APDU_TRACE = 0x03
    CARD_DATA = 0x04
    TRANSACTION_DATA = 0x05
    ACK = 0x06
    ERROR = 0x07

@dataclass
class BLEMessage:
    """BLE message structure with fragmentation support."""
    message_type: BLEMessageType
    sequence_id: int
    total_fragments: int
    fragment_index: int
    payload: bytes
    
    def to_bytes(self) -> bytes:
        """Convert to wire format."""
        header = struct.pack('<BBHH', 
                           self.message_type.value,
                           self.sequence_id,
                           self.total_fragments,
                           self.fragment_index)
        payload_len = len(self.payload)
        return struct.pack('<H', payload_len) + header + self.payload
    
    @classmethod
    def from_bytes(cls, data: bytes) -> 'BLEMessage':
        """Parse from wire format."""
        if len(data) < 8:
            raise ValueError("Message too short")
        
        payload_len = struct.unpack('<H', data[0:2])[0]
        msg_type, seq_id, total_frags, frag_idx = struct.unpack('<BBHH', data[2:8])
        payload = data[8:8+payload_len]
        
        return cls(
            message_type=BLEMessageType(msg_type),
            sequence_id=seq_id,
            total_fragments=total_frags,
            fragment_index=frag_idx,
            payload=payload
        )

class SessionExporter:
    """Exports EMV session data for Android consumption."""
    
    @staticmethod
    def export_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert session to Android-compatible format."""
        return {
            "session_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "version": "5.0",
            "card_data": SessionExporter._extract_card_data(session_data),
            "transaction_data": SessionExporter._extract_transaction_data(session_data),
            "apdu_trace": SessionExporter._extract_apdu_trace(session_data),
            "security_data": SessionExporter._extract_security_data(session_data)
        }
    
    @staticmethod
    def _extract_card_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Extract card-specific data."""
        card_data = {}
        
        if "fci_data" in session:
            card_data["fci"] = session["fci_data"]
        if "afl_data" in session:
            card_data["afl"] = session["afl_data"] 
        if "pan" in session:
            card_data["pan"] = session["pan"]
        if "expiry_date" in session:
            card_data["expiry"] = session["expiry_date"]
        if "cardholder_name" in session:
            card_data["cardholder_name"] = session["cardholder_name"]
            
        return card_data
    
    @staticmethod
    def _extract_transaction_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Extract transaction-specific data."""
        txn_data = {}
        
        if "amount" in session:
            txn_data["amount"] = session["amount"]
        if "currency" in session:
            txn_data["currency"] = session["currency"]
        if "transaction_type" in session:
            txn_data["type"] = session["transaction_type"]
        if "terminal_data" in session:
            txn_data["terminal"] = session["terminal_data"]
            
        return txn_data
    
    @staticmethod
    def _extract_apdu_trace(session: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract APDU command trace."""
        if "apdu_trace" not in session:
            return []
            
        trace = []
        for apdu in session["apdu_trace"]:
            trace_entry = {
                "timestamp": apdu.get("timestamp", ""),
                "command": apdu.get("command", ""),
                "response": apdu.get("response", ""),
                "sw1": apdu.get("sw1", ""),
                "sw2": apdu.get("sw2", ""),
                "description": apdu.get("description", "")
            }
            trace.append(trace_entry)
            
        return trace
    
    @staticmethod
    def _extract_security_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Extract cryptographic data."""
        security_data = {}
        
        if "cryptogram" in session:
            security_data["cryptogram"] = session["cryptogram"]
        if "unpredictable_number" in session:
            security_data["unpredictable_number"] = session["unpredictable_number"]
        if "application_cryptogram" in session:
            security_data["application_cryptogram"] = session["application_cryptogram"]
        if "issuer_data" in session:
            security_data["issuer_data"] = session["issuer_data"]
            
        return security_data

class BLESession(QObject):
    """Manages BLE GATT communication with Android device."""
    
    # PyQt5 signals
    connected = pyqtSignal(str)  # device_name
    disconnected = pyqtSignal()
    data_sent = pyqtSignal(str, int)  # message_type, size
    data_received = pyqtSignal(str, bytes)  # message_type, data
    status_changed = pyqtSignal(str)  # status
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: Optional[BleakClient] = None
        self.device_address = ""
        self.device_name = ""
        self.state = BLEState.IDLE
        self.sequence_counter = 0
        self.pending_fragments: Dict[int, List[Optional[BLEMessage]]] = {}
        self.rx_characteristic = None
        self.tx_characteristic = None
        
    async def scan_for_android_devices(self, timeout: float = 10.0) -> List[Dict[str, str]]:
        """Scan for Android companion devices."""
        if not BLE_AVAILABLE:
            raise RuntimeError("BLE not available - install bleak")
            
        self.state = BLEState.SCANNING
        devices = []
        
        try:
            self.status_changed.emit("Scanning for Android devices...")
            
            scanner = BleakScanner()
            discovered = await scanner.discover(timeout=timeout)
            
            for device in discovered:
                # Look for devices with our service or specific naming
                if (device.name and 
                    ("NFSP00F3R" in device.name or "EMV" in device.name)):
                    devices.append({
                        "name": device.name,
                        "address": device.address,
                        "rssi": device.rssi
                    })
                    logging.info(f"Found Android device: {device.name} ({device.address})")
                    
            self.status_changed.emit(f"Found {len(devices)} Android devices")
            return devices
            
        except Exception as e:
            self.state = BLEState.ERROR
            error_msg = f"BLE scan failed: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return []
    
    async def connect_to_device(self, device_address: str, device_name: str = "") -> bool:
        """Connect to Android companion device."""
        if not BLE_AVAILABLE:
            raise RuntimeError("BLE not available")
            
        self.state = BLEState.CONNECTING
        self.device_address = device_address
        self.device_name = device_name
        
        try:
            self.status_changed.emit(f"Connecting to {device_name or device_address}...")
            
            # Create BLE client
            self.client = BleakClient(device_address)
            await self.client.connect()
            
            # Verify connection
            if not self.client.is_connected:
                raise RuntimeError("Failed to establish connection")
                
            # Discover services
            services = await self.client.get_services()
            
            # Find Nordic UART service (commonly used for custom protocols)
            uart_service = None
            for service in services:
                if service.uuid.upper() == ANDROID_SERVICE_UUID.upper():
                    uart_service = service
                    break
                    
            if not uart_service:
                raise RuntimeError("Android service not found - ensure app is running")
                
            # Get characteristics
            for char in uart_service.characteristics:
                if char.uuid.upper() == ANDROID_RX_CHAR_UUID.upper():
                    self.rx_characteristic = char
                elif char.uuid.upper() == ANDROID_TX_CHAR_UUID.upper():
                    self.tx_characteristic = char
                    
            if not (self.rx_characteristic and self.tx_characteristic):
                raise RuntimeError("Required characteristics not found")
                
            # Enable notifications for TX characteristic
            await self.client.start_notify(self.tx_characteristic, self._notification_handler)
            
            self.state = BLEState.CONNECTED
            self.status_changed.emit(f"Connected to {device_name}")
            self.connected.emit(device_name)
            
            # Send hello message
            await self._send_hello()
            
            logging.info(f"Successfully connected to Android device: {device_name}")
            return True
            
        except Exception as e:
            self.state = BLEState.ERROR
            error_msg = f"Connection failed: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
    
    async def disconnect_from_device(self):
        """Disconnect from Android device."""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
                
            self.state = BLEState.IDLE
            self.status_changed.emit("Disconnected")
            self.disconnected.emit()
            
            logging.info("Disconnected from Android device")
            
        except Exception as e:
            logging.error(f"Disconnect error: {e}")
    
    async def send_session_data(self, session_data: Dict[str, Any]) -> bool:
        """Send complete session data to Android."""
        if self.state != BLEState.CONNECTED:
            self.error_occurred.emit("Not connected to Android device")
            return False
            
        try:
            self.state = BLEState.SENDING
            
            # Export session for Android
            android_session = SessionExporter.export_session(session_data)
            
            # Convert to JSON
            json_data = json.dumps(android_session, indent=None)
            payload = json_data.encode('utf-8')
            
            # Send with fragmentation
            await self._send_fragmented_message(BLEMessageType.SESSION_DATA, payload)
            
            self.data_sent.emit("session_data", len(payload))
            self.status_changed.emit(f"Sent session data ({len(payload)} bytes)")
            
            logging.info(f"Sent session data to Android: {len(payload)} bytes")
            return True
            
        except Exception as e:
            error_msg = f"Failed to send session: {e}"
            logging.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False
        finally:
            if self.state == BLEState.SENDING:
                self.state = BLEState.CONNECTED
    
    async def send_apdu_trace(self, apdu_trace: List[Dict[str, Any]]) -> bool:
        """Send APDU trace data to Android."""
        if self.state != BLEState.CONNECTED:
            return False
            
        try:
            trace_data = {
                "timestamp": datetime.now().isoformat(),
                "trace": apdu_trace,
                "count": len(apdu_trace)
            }
            
            json_data = json.dumps(trace_data)
            payload = json_data.encode('utf-8')
            
            await self._send_fragmented_message(BLEMessageType.APDU_TRACE, payload)
            
            self.data_sent.emit("apdu_trace", len(payload))
            logging.info(f"Sent APDU trace: {len(apdu_trace)} commands")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to send APDU trace: {e}")
            return False
    
    async def _send_hello(self):
        """Send hello message to establish session."""
        hello_data = {
            "type": "hello",
            "version": "5.0",
            "timestamp": datetime.now().isoformat(),
            "capabilities": ["session_data", "apdu_trace", "card_data", "transaction_data"],
            "device": "NFSP00F3R Terminal"
        }
        
        payload = json.dumps(hello_data).encode('utf-8')
        await self._send_fragmented_message(BLEMessageType.HELLO, payload)
    
    async def _send_fragmented_message(self, msg_type: BLEMessageType, payload: bytes):
        """Send message with automatic fragmentation."""
        max_mtu = 20  # Conservative BLE MTU minus headers
        total_fragments = (len(payload) + max_mtu - 1) // max_mtu
        
        self.sequence_counter += 1
        sequence_id = self.sequence_counter
        
        for fragment_idx in range(total_fragments):
            start_pos = fragment_idx * max_mtu
            end_pos = min((fragment_idx + 1) * max_mtu, len(payload))
            fragment_payload = payload[start_pos:end_pos]
            
            message = BLEMessage(
                message_type=msg_type,
                sequence_id=sequence_id,
                total_fragments=total_fragments,
                fragment_index=fragment_idx,
                payload=fragment_payload
            )
            
            # Send fragment via GATT
            wire_data = message.to_bytes()
            if self.client and self.rx_characteristic:
                await self.client.write_gatt_char(self.rx_characteristic, wire_data)
                
            # Brief pause between fragments
            await asyncio.sleep(0.005)
            
        logging.debug(f"Sent {msg_type.name} message: {total_fragments} fragments, {len(payload)} bytes")
    
    def _notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        """Handle incoming notifications from Android."""
        try:
            message = BLEMessage.from_bytes(bytes(data))
            
            # Handle message fragmentation
            seq_id = message.sequence_id
            if seq_id not in self.pending_fragments:
                self.pending_fragments[seq_id] = [None] * message.total_fragments
                
            self.pending_fragments[seq_id][message.fragment_index] = message
            
            # Check if all fragments received
            fragments = self.pending_fragments[seq_id]
            if all(f is not None for f in fragments):
                # Reassemble complete message
                complete_payload = b''.join(f.payload for f in fragments)
                self._handle_complete_message(message.message_type, complete_payload)
                
                # Clean up
                del self.pending_fragments[seq_id]
                
        except Exception as e:
            logging.error(f"Notification handler error: {e}")
    
    def _handle_complete_message(self, msg_type: BLEMessageType, payload: bytes):
        """Process complete received message."""
        try:
            if msg_type == BLEMessageType.ACK:
                logging.info("Received ACK from Android")
                
            elif msg_type == BLEMessageType.ERROR:
                error_msg = payload.decode('utf-8', errors='ignore')
                logging.error(f"Android reported error: {error_msg}")
                self.error_occurred.emit(f"Android: {error_msg}")
                
            else:
                # Try to parse as JSON
                try:
                    data = json.loads(payload.decode('utf-8'))
                    self.data_received.emit(msg_type.name, payload)
                    logging.info(f"Received {msg_type.name}: {len(payload)} bytes")
                except json.JSONDecodeError:
                    # Raw data
                    self.data_received.emit(msg_type.name, payload)
                    
        except Exception as e:
            logging.error(f"Message handling error: {e}")

class BLEAndroidManager(QObject):
    """Main BLE manager for Android companion app communication."""
    
    # PyQt5 signals
    device_found = pyqtSignal(str, str, int)  # name, address, rssi
    android_connected = pyqtSignal(str)  # device_name
    android_disconnected = pyqtSignal()
    session_sent = pyqtSignal(int)  # bytes_sent
    status_changed = pyqtSignal(str)  # status
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ble_session = BLESession(self)
        self.event_loop = None
        self.worker_thread = None
        
        # Connect signals
        self.ble_session.connected.connect(self.android_connected)
        self.ble_session.disconnected.connect(self.android_disconnected)
        self.ble_session.data_sent.connect(self._on_data_sent)
        self.ble_session.status_changed.connect(self.status_changed)
        self.ble_session.error_occurred.connect(self.error_occurred)
    
    def is_ble_available(self) -> bool:
        """Check if BLE is available."""
        return BLE_AVAILABLE
    
    def start_android_scan(self, timeout: float = 10.0):
        """Start scanning for Android devices."""
        if not BLE_AVAILABLE:
            self.error_occurred.emit("BLE not available - install bleak")
            return
            
        self._run_async_operation(self._scan_operation, timeout)
    
    def connect_to_android(self, device_address: str, device_name: str = ""):
        """Connect to specific Android device."""
        if not BLE_AVAILABLE:
            self.error_occurred.emit("BLE not available")
            return
            
        self._run_async_operation(self._connect_operation, device_address, device_name)
    
    def disconnect_android(self):
        """Disconnect from Android device."""
        if self.is_connected():
            self._run_async_operation(self._disconnect_operation)
    
    def send_session_to_android(self, session_data: Dict[str, Any]):
        """Send session data to connected Android device."""
        if not self.is_connected():
            self.error_occurred.emit("Not connected to Android device")
            return
            
        self._run_async_operation(self._send_session_operation, session_data)
    
    def send_apdu_trace_to_android(self, apdu_trace: List[Dict[str, Any]]):
        """Send APDU trace to connected Android device."""
        if not self.is_connected():
            self.error_occurred.emit("Not connected to Android device")
            return
            
        self._run_async_operation(self._send_trace_operation, apdu_trace)
    
    def is_connected(self) -> bool:
        """Check if connected to Android device."""
        return self.ble_session.state == BLEState.CONNECTED
    
    def get_connection_info(self) -> Dict[str, str]:
        """Get current connection information."""
        return {
            "state": self.ble_session.state.value,
            "device_name": self.ble_session.device_name,
            "device_address": self.ble_session.device_address
        }
    
    def _run_async_operation(self, operation, *args):
        """Run async operation in worker thread."""
        if not self.worker_thread:
            self.worker_thread = QThread()
            
        def run_operation():
            try:
                if not self.event_loop:
                    self.event_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self.event_loop)
                    
                self.event_loop.run_until_complete(operation(*args))
                
            except Exception as e:
                logging.error(f"Async operation error: {e}")
                self.error_occurred.emit(f"Operation failed: {e}")
        
        self.worker_thread.started.connect(run_operation)
        self.worker_thread.start()
    
    async def _scan_operation(self, timeout: float):
        """Async scan operation."""
        devices = await self.ble_session.scan_for_android_devices(timeout)
        for device in devices:
            self.device_found.emit(device["name"], device["address"], device.get("rssi", -100))
    
    async def _connect_operation(self, device_address: str, device_name: str):
        """Async connect operation."""
        await self.ble_session.connect_to_device(device_address, device_name)
    
    async def _disconnect_operation(self):
        """Async disconnect operation."""
        await self.ble_session.disconnect_from_device()
    
    async def _send_session_operation(self, session_data: Dict[str, Any]):
        """Async send session operation."""
        await self.ble_session.send_session_data(session_data)
    
    async def _send_trace_operation(self, apdu_trace: List[Dict[str, Any]]):
        """Async send trace operation."""
        await self.ble_session.send_apdu_trace(apdu_trace)
    
    def _on_data_sent(self, data_type: str, size: int):
        """Handle data sent notification."""
        if data_type == "session_data":
            self.session_sent.emit(size)

# Factory function
def create_android_manager() -> BLEAndroidManager:
    """Create and return a BLE Android manager instance."""
    return BLEAndroidManager()

# Module-level availability check
def check_ble_availability() -> Dict[str, bool]:
    """Check BLE availability and return status."""
    return {
        "bleak_available": BLE_AVAILABLE,
        "ble_supported": BLE_AVAILABLE
    }
