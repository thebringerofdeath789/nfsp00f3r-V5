#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Android HCE Relay
===================================

File: android_hce.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Android HCE (Host Card Emulation) relay module via Bluetooth

Classes:
- AndroidHCERelay: Bluetooth communication with Android HCE app
- HCEProtocol: Protocol handler for HCE communication
"""

import asyncio
import logging
import time
import json
import struct
from typing import Optional, List, Callable, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
import bleak
from bleak import BleakClient, BleakScanner

class HCEProtocol:
    """Protocol handler for Android HCE communication."""
    
    # message types
    MSG_APDU_COMMAND = 0x01
    MSG_APDU_RESPONSE = 0x02
    MSG_STATUS_UPDATE = 0x03
    MSG_ERROR = 0x04
    MSG_HELLO = 0x05
    
    @staticmethod
    def pack_message(msg_type: int, data: bytes) -> bytes:
        """Pack message for transmission."""
        length = len(data)
        header = struct.pack('<HB', length, msg_type)
        return header + data
        
    @staticmethod
    def unpack_message(message: bytes) -> tuple:
        """Unpack received message."""
        if len(message) < 3:
            return None, None
            
        length, msg_type = struct.unpack('<HB', message[:3])
        data = message[3:]
        
        if len(data) != length:
            return None, None
            
        return msg_type, data

class AndroidHCERelay(QObject):
    """
    Android HCE relay for card emulation via smartphone.
    Communicates with companion Android app over Bluetooth.
    """
    
    # bluetooth service uuids for android hce app
    HCE_SERVICE_UUID = "12345678-1234-5678-9abc-123456789abc"
    HCE_TX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abd"
    HCE_RX_CHAR_UUID = "12345678-1234-5678-9abc-123456789abe"
    
    # signals for gui integration
    device_connected = pyqtSignal(str)  # device_address
    device_disconnected = pyqtSignal()
    apdu_received = pyqtSignal(bytes)
    apdu_sent = pyqtSignal(bytes)
    status_updated = pyqtSignal(str, dict)
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
        self.response_queue = asyncio.Queue()
        self.message_buffer = bytearray()
        
        # hce state
        self.emulation_active = False
        self.card_present = False
        self.current_aid = None
        
        self.logger.info("android hce relay initialized")
        
    async def scan_devices(self) -> List[Dict[str, Any]]:
        """Scan for Android HCE devices."""
        devices = []
        
        try:
            self.logger.info("scanning for android hce devices")
            
            discovered = await BleakScanner.discover(timeout=10.0)
            
            for device in discovered:
                if self._is_hce_device(device):
                    device_info = {
                        'address': device.address,
                        'name': device.name or 'Unknown',
                        'rssi': device.rssi,
                        'services': device.metadata.get('uuids', [])
                    }
                    devices.append(device_info)
                    
            self.logger.info(f"found {len(devices)} hce devices")
            return devices
            
        except Exception as e:
            self.logger.error(f"hce scan failed: {e}")
            return []
            
    def _is_hce_device(self, device) -> bool:
        """Check if BLE device is Android HCE app."""
        if not device.name:
            return False
            
        name_lower = device.name.lower()
        
        # check for hce app identifiers
        hce_indicators = [
            'nfsp00f3r',
            'hce emulator',
            'card emulator',
            'nfc relay'
        ]
        
        # also check service uuids
        if hasattr(device, 'metadata') and 'uuids' in device.metadata:
            service_uuids = [uuid.lower() for uuid in device.metadata['uuids']]
            if self.HCE_SERVICE_UUID.lower() in service_uuids:
                return True
                
        return any(indicator in name_lower for indicator in hce_indicators)
        
    async def connect(self, device_address: str = None) -> bool:
        """Connect to Android HCE device."""
        try:
            if not device_address:
                devices = await self.scan_devices()
                if not devices:
                    raise Exception("no android hce devices found")
                device_address = devices[0]['address']
                
            self.logger.info(f"connecting to hce device: {device_address}")
            
            # create bleak client
            self.client = BleakClient(device_address)
            
            # connect and verify services
            await self.client.connect()
            
            if not await self._verify_services():
                raise Exception("hce services not found")
                
            # setup notification handlers
            await self._setup_notifications()
            
            # send hello message
            await self._send_hello()
            
            self.device_address = device_address
            self.connected = True
            
            self.logger.info(f"connected to hce device: {device_address}")
            self.device_connected.emit(device_address)
            
            return True
            
        except Exception as e:
            self.logger.error(f"hce connection failed: {e}")
            self.error_occurred.emit(f"connection failed: {e}")
            return False
            
    async def disconnect(self) -> bool:
        """Disconnect from Android HCE device."""
        try:
            # stop emulation
            if self.emulation_active:
                await self.stop_emulation()
                
            # disconnect bluetooth
            if self.client and self.connected:
                await self.client.disconnect()
                
            self.connected = False
            self.device_address = None
            self.client = None
            
            self.logger.info("disconnected from hce device")
            self.device_disconnected.emit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"hce disconnect failed: {e}")
            return False
            
    async def _verify_services(self) -> bool:
        """Verify Android HCE services."""
        try:
            services = self.client.services
            
            # check for hce service
            service = services.get_service(self.HCE_SERVICE_UUID)
            if not service:
                return False
                
            # check for required characteristics
            tx_char = service.get_characteristic(self.HCE_TX_CHAR_UUID)
            rx_char = service.get_characteristic(self.HCE_RX_CHAR_UUID)
            
            if not tx_char or not rx_char:
                return False
                
            self.logger.debug("hce bluetooth services verified")
            return True
            
        except Exception as e:
            self.logger.error(f"hce service verification failed: {e}")
            return False
            
    async def _setup_notifications(self) -> None:
        """Setup Bluetooth notification handlers."""
        try:
            await self.client.start_notify(
                self.HCE_RX_CHAR_UUID,
                self._notification_handler
            )
            
            self.logger.debug("hce notifications enabled")
            
        except Exception as e:
            self.logger.error(f"hce notification setup failed: {e}")
            
    def _notification_handler(self, sender, data: bytearray) -> None:
        """Handle incoming Bluetooth notifications."""
        try:
            self.message_buffer.extend(data)
            
            # process complete messages
            while len(self.message_buffer) >= 3:
                length, msg_type = struct.unpack('<HB', self.message_buffer[:3])
                msg_size = length + 3
                
                if len(self.message_buffer) >= msg_size:
                    message = bytes(self.message_buffer[:msg_size])
                    self.message_buffer = self.message_buffer[msg_size:]
                    
                    asyncio.create_task(self._process_hce_message(message))
                else:
                    break
                    
        except Exception as e:
            self.logger.error(f"hce notification handling failed: {e}")
            
    async def _process_hce_message(self, message: bytes) -> None:
        """Process incoming HCE message."""
        try:
            msg_type, data = HCEProtocol.unpack_message(message)
            
            if msg_type == HCEProtocol.MSG_APDU_COMMAND:
                await self._handle_apdu_command(data)
            elif msg_type == HCEProtocol.MSG_STATUS_UPDATE:
                await self._handle_status_update(data)
            elif msg_type == HCEProtocol.MSG_ERROR:
                await self._handle_error(data)
                
        except Exception as e:
            self.logger.error(f"hce message processing failed: {e}")
            
    async def _handle_apdu_command(self, apdu_data: bytes) -> None:
        """Handle incoming APDU command from terminal."""
        try:
            self.logger.debug(f"hce apdu received: {apdu_data.hex()}")
            self.apdu_received.emit(apdu_data)
            
            # check for attack response
            response = None
            if self.attack_manager:
                response = self.attack_manager.process_apdu(apdu_data)
                
            if response:
                self.logger.info("attack response substituted")
                await self._send_apdu_response(response)
                self.apdu_sent.emit(response)
            else:
                # forward to real card or default response
                default_response = b'\x6F\x00'  # unknown error
                await self._send_apdu_response(default_response)
                
        except Exception as e:
            self.logger.error(f"hce apdu handling failed: {e}")
            
    async def _handle_status_update(self, status_data: bytes) -> None:
        """Handle status update from HCE app."""
        try:
            status = json.loads(status_data.decode('utf-8'))
            
            if 'emulation_active' in status:
                self.emulation_active = status['emulation_active']
                
            if 'card_present' in status:
                self.card_present = status['card_present']
                
            if 'current_aid' in status:
                self.current_aid = status['current_aid']
                
            self.logger.debug(f"hce status update: {status}")
            self.status_updated.emit("status_update", status)
            
        except Exception as e:
            self.logger.error(f"hce status handling failed: {e}")
            
    async def _handle_error(self, error_data: bytes) -> None:
        """Handle error from HCE app."""
        try:
            error_msg = error_data.decode('utf-8')
            self.logger.error(f"hce error: {error_msg}")
            self.error_occurred.emit(f"hce error: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"hce error handling failed: {e}")
            
    async def _send_hello(self) -> None:
        """Send hello message to establish connection."""
        try:
            hello_data = json.dumps({
                'version': '5.0',
                'client': 'nfsp00f3r',
                'timestamp': time.time()
            }).encode('utf-8')
            
            await self._send_hce_message(HCEProtocol.MSG_HELLO, hello_data)
            
        except Exception as e:
            self.logger.error(f"hce hello failed: {e}")
            
    async def _send_apdu_response(self, response_data: bytes) -> None:
        """Send APDU response to terminal via HCE."""
        try:
            await self._send_hce_message(HCEProtocol.MSG_APDU_RESPONSE, response_data)
            
        except Exception as e:
            self.logger.error(f"hce apdu response failed: {e}")
            
    async def _send_hce_message(self, msg_type: int, data: bytes) -> None:
        """Send message to HCE app."""
        if not self.client or not self.connected:
            return
            
        try:
            message = HCEProtocol.pack_message(msg_type, data)
            
            # send via bluetooth
            await self.client.write_gatt_char(
                self.HCE_TX_CHAR_UUID,
                message
            )
            
        except Exception as e:
            self.logger.error(f"hce message send failed: {e}")
            
    async def start_emulation(self, aid: str = None) -> bool:
        """Start card emulation on Android device."""
        try:
            if not self.connected:
                return False
                
            start_data = json.dumps({
                'action': 'start_emulation',
                'aid': aid or 'A0000000031010'  # default visa aid
            }).encode('utf-8')
            
            await self._send_hce_message(HCEProtocol.MSG_STATUS_UPDATE, start_data)
            
            # wait for confirmation
            await asyncio.sleep(1.0)
            
            self.logger.info("hce emulation started")
            return True
            
        except Exception as e:
            self.logger.error(f"hce emulation start failed: {e}")
            return False
            
    async def stop_emulation(self) -> bool:
        """Stop card emulation on Android device."""
        try:
            if not self.connected:
                return False
                
            stop_data = json.dumps({
                'action': 'stop_emulation'
            }).encode('utf-8')
            
            await self._send_hce_message(HCEProtocol.MSG_STATUS_UPDATE, stop_data)
            
            self.emulation_active = False
            self.card_present = False
            
            self.logger.info("hce emulation stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"hce emulation stop failed: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Get current relay status."""
        return {
            'connected': self.connected,
            'device_address': self.device_address,
            'emulation_active': self.emulation_active,
            'card_present': self.card_present,
            'current_aid': self.current_aid
        }
