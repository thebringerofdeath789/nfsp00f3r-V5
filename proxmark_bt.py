#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Proxmark Bluetooth Relay
==========================================

File: proxmark_bt.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Bluetooth relay module for Proxmark3 devices with BT support

Classes:
- ProxmarkBluetoothRelay: Bluetooth communication with Proxmark3
- BluetoothScanner: Device discovery and pairing
"""

import asyncio
import logging
import time
import struct
from typing import Optional, List, Callable, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
import bleak
from bleak import BleakClient, BleakScanner

class BluetoothScanner:
    """Bluetooth device scanner for Proxmark discovery."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def scan_proxmark_devices(self, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Scan for Proxmark Bluetooth devices."""
        devices = []
        
        try:
            self.logger.info(f"scanning for bluetooth devices ({timeout}s)")
            
            discovered = await BleakScanner.discover(timeout=timeout)
            
            for device in discovered:
                # check device name and services for proxmark indicators
                if self._is_proxmark_device(device):
                    device_info = {
                        'address': device.address,
                        'name': device.name or 'Unknown',
                        'rssi': device.rssi,
                        'services': device.metadata.get('uuids', [])
                    }
                    devices.append(device_info)
                    
            self.logger.info(f"found {len(devices)} proxmark bluetooth devices")
            return devices
            
        except Exception as e:
            self.logger.error(f"bluetooth scan failed: {e}")
            return []
            
    def _is_proxmark_device(self, device) -> bool:
        """Check if BLE device is a Proxmark."""
        if not device.name:
            return False
            
        name_lower = device.name.lower()
        
        # check common proxmark bluetooth names
        proxmark_indicators = [
            'proxmark',
            'pm3',
            'rfid tools',
            'nfc tools'
        ]
        
        return any(indicator in name_lower for indicator in proxmark_indicators)

class ProxmarkBluetoothRelay(QObject):
    """
    Bluetooth relay for Proxmark3 devices with BT support.
    Provides same interface as USB relay but over Bluetooth.
    """
    
    # bluetooth service uuids for proxmark
    PROXMARK_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
    PROXMARK_TX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    PROXMARK_RX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    
    # signals for gui integration
    device_connected = pyqtSignal(str)  # device_address
    device_disconnected = pyqtSignal()
    apdu_received = pyqtSignal(bytes)
    apdu_sent = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, attack_manager=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.attack_manager = attack_manager
        
        # bluetooth state
        self.device_address = None
        self.client: Optional[BleakClient] = None
        self.connected = False
        
        # communication state
        self.scanner = BluetoothScanner()
        self.command_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        
        # proxmark state
        self.field_active = False
        self.card_present = False
        self.current_uid = None
        
        self.logger.info("proxmark bluetooth relay initialized")
        
    async def scan_devices(self) -> List[Dict[str, Any]]:
        """Scan for Proxmark Bluetooth devices."""
        return await self.scanner.scan_proxmark_devices()
        
    async def connect(self, device_address: str = None) -> bool:
        """Connect to Proxmark via Bluetooth."""
        try:
            if not device_address:
                devices = await self.scan_devices()
                if not devices:
                    raise Exception("no proxmark bluetooth devices found")
                device_address = devices[0]['address']
                
            self.logger.info(f"connecting to {device_address}")
            
            # create bleak client
            self.client = BleakClient(device_address)
            
            # connect and verify services
            await self.client.connect()
            
            if not await self._verify_services():
                raise Exception("proxmark services not found")
                
            # setup notification handlers
            await self._setup_notifications()
            
            self.device_address = device_address
            self.connected = True
            
            self.logger.info(f"connected to proxmark: {device_address}")
            self.device_connected.emit(device_address)
            
            return True
            
        except Exception as e:
            self.logger.error(f"bluetooth connection failed: {e}")
            self.error_occurred.emit(f"connection failed: {e}")
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from Proxmark device."""
        try:
            # stop hf field
            if self.field_active:
                await self._send_field_command(False)
                
            # disconnect bluetooth
            if self.client and self.connected:
                await self.client.disconnect()
                
            self.connected = False
            self.device_address = None
            self.client = None
            
            self.logger.info("disconnected from proxmark")
            self.device_disconnected.emit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"bluetooth disconnect failed: {e}")
            return False
            
    async def _verify_services(self) -> bool:
        """Verify Proxmark Bluetooth services."""
        try:
            services = self.client.services
            
            # check for proxmark service
            service = services.get_service(self.PROXMARK_SERVICE_UUID)
            if not service:
                return False
                
            # check for required characteristics
            tx_char = service.get_characteristic(self.PROXMARK_TX_CHAR_UUID)
            rx_char = service.get_characteristic(self.PROXMARK_RX_CHAR_UUID)
            
            if not tx_char or not rx_char:
                return False
                
            self.logger.debug("proxmark bluetooth services verified")
            return True
            
        except Exception as e:
            self.logger.error(f"service verification failed: {e}")
            return False
            
    async def _setup_notifications(self) -> None:
        """Setup Bluetooth notification handlers."""
        try:
            await self.client.start_notify(
                self.PROXMARK_RX_CHAR_UUID,
                self._notification_handler
            )
            
            self.logger.debug("bluetooth notifications enabled")
            
        except Exception as e:
            self.logger.error(f"notification setup failed: {e}")
            
    def _notification_handler(self, sender, data: bytearray) -> None:
        """Handle incoming Bluetooth notifications."""
        try:
            message = bytes(data)
            asyncio.create_task(self._process_bt_message(message))
            
        except Exception as e:
            self.logger.error(f"notification handling failed: {e}")
            
    async def _process_bt_message(self, message: bytes) -> None:
        """Process incoming Bluetooth message."""
        try:
            if len(message) < 4:
                return
                
            # parse proxmark message format
            length, cmd = struct.unpack('<HH', message[:4])
            data = message[4:]
            
            # handle different message types
            if cmd == 0x0385:  # hf 14a reader response
                await self._handle_reader_response(data)
            elif cmd == 0x0388:  # raw apdu response
                await self._handle_raw_response(data)
                
        except Exception as e:
            self.logger.error(f"bt message processing failed: {e}")
            
    async def start_hf_reader(self) -> bool:
        """Start HF 14A reader mode."""
        try:
            # activate hf field
            await self._send_field_command(True)
            self.field_active = True
            
            # start 14a reader
            await self._send_bt_command(0x0385, b'')  # cmd_hf_14a_reader
            
            self.logger.info("hf reader started")
            return True
            
        except Exception as e:
            self.logger.error(f"hf reader start failed: {e}")
            return False
            
    async def stop_hf_reader(self) -> bool:
        """Stop HF 14A reader mode."""
        try:
            # deactivate hf field
            await self._send_field_command(False)
            self.field_active = False
            
            self.logger.info("hf reader stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"hf reader stop failed: {e}")
            return False
            
    async def send_apdu(self, apdu_bytes: bytes) -> Optional[bytes]:
        """Send APDU to card and get response."""
        try:
            if not self.connected or not self.field_active:
                return None
                
            # check for attack response first
            if self.attack_manager:
                attack_response = self.attack_manager.process_apdu(apdu_bytes)
                if attack_response:
                    self.logger.info("attack response substituted")
                    self.apdu_sent.emit(attack_response)
                    return attack_response
                    
            # send raw apdu command
            apdu_data = self._format_apdu_data(apdu_bytes)
            response = await self._send_bt_command_sync(0x0388, apdu_data)
            
            if response:
                apdu_response = self._parse_apdu_response(response)
                if apdu_response:
                    self.apdu_received.emit(apdu_response)
                    return apdu_response
                    
            return None
            
        except Exception as e:
            self.logger.error(f"bluetooth apdu send failed: {e}")
            return None
            
    async def _send_field_command(self, enable: bool) -> None:
        """Send HF field on/off command."""
        cmd = 0x0302 if enable else 0x0303
        await self._send_bt_command(cmd, b'')
        
    async def _send_bt_command(self, cmd: int, data: bytes) -> None:
        """Send command via Bluetooth."""
        if not self.client or not self.connected:
            return
            
        try:
            # format command
            length = len(data)
            header = struct.pack('<HH', length, cmd)
            message = header + data
            
            # send via bluetooth
            await self.client.write_gatt_char(
                self.PROXMARK_TX_CHAR_UUID,
                message
            )
            
        except Exception as e:
            self.logger.error(f"bt command send failed: {e}")
            
    async def _send_bt_command_sync(self, cmd: int, data: bytes, timeout: float = 3.0) -> Optional[bytes]:
        """Send command and wait for response."""
        try:
            # clear response queue
            while not self.response_queue.empty():
                await self.response_queue.get()
                
            # send command
            await self._send_bt_command(cmd, data)
            
            # wait for response
            response = await asyncio.wait_for(
                self.response_queue.get(),
                timeout=timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            self.logger.warning(f"bt command timeout: {cmd:04x}")
            return None
        except Exception as e:
            self.logger.error(f"bt sync command failed: {e}")
            return None
            
    def _format_apdu_data(self, apdu_bytes: bytes) -> bytes:
        """Format APDU for Proxmark raw command."""
        # proxmark raw format: flags + data
        flags = struct.pack('<H', 0x0000)  # basic flags
        return flags + apdu_bytes
        
    def _parse_apdu_response(self, response_data: bytes) -> Optional[bytes]:
        """Parse APDU response from Proxmark data."""
        try:
            if len(response_data) < 4:
                return None
                
            # skip response header
            apdu_data = response_data[4:]
            
            if len(apdu_data) >= 2:
                return apdu_data
                
            return None
            
        except Exception as e:
            self.logger.error(f"bt response parsing failed: {e}")
            return None
            
    async def _handle_reader_response(self, data: bytes) -> None:
        """Handle HF 14A reader response."""
        try:
            if len(data) >= 4:
                # check card presence
                self.card_present = True
                
                # extract uid if available
                if len(data) >= 8:
                    uid_len = data[0]
                    if uid_len > 0 and len(data) >= 1 + uid_len:
                        self.current_uid = data[1:1+uid_len].hex().upper()
                        self.logger.info(f"bt card detected: uid={self.current_uid}")
                        
            # queue response for sync commands
            await self.response_queue.put(data)
            
        except Exception as e:
            self.logger.error(f"bt reader response handling failed: {e}")
            
    async def _handle_raw_response(self, data: bytes) -> None:
        """Handle raw APDU response."""
        try:
            if len(data) >= 2:
                # extract apdu response
                apdu_response = self._parse_apdu_response(data)
                if apdu_response:
                    self.apdu_received.emit(apdu_response)
                    
            # queue response for sync commands
            await self.response_queue.put(data)
            
        except Exception as e:
            self.logger.error(f"bt raw response handling failed: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current relay status."""
        return {
            'connected': self.connected,
            'device_address': self.device_address,
            'field_active': self.field_active,
            'card_present': self.card_present,
            'current_uid': self.current_uid
        }
