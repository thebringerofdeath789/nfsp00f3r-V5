#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Proxmark USB Relay
====================================

File: proxmark_usb.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: USB relay module for Proxmark3 devices

Classes:
- ProxmarkUSBRelay: USB communication with Proxmark3
- ProxmarkCommand: Command wrapper for Proxmark operations
"""

import asyncio
import logging
import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, List, Callable, Dict, Any
from PyQt5.QtCore import QObject, pyqtSignal
import struct

class ProxmarkCommand:
    """Proxmark3 command wrapper."""
    
    # standard proxmark commands
    CMD_HF_14A_READER = 0x0385
    CMD_HF_14A_SIMULATE = 0x0386
    CMD_HF_14A_SNOOP = 0x0387
    CMD_HF_14A_RAW = 0x0388
    
    def __init__(self, cmd: int, data: bytes = b''):
        self.cmd = cmd
        self.data = data
        self.timestamp = time.time()
        
    def to_bytes(self) -> bytes:
        """Convert command to wire format."""
        # proxmark protocol: length + cmd + data
        length = len(self.data)
        header = struct.pack('<HH', length, self.cmd)
        return header + self.data

class ProxmarkUSBRelay(QObject):
    """
    USB relay for Proxmark3 devices.
    Handles HF 14A communication and integrates with AttackManager.
    """
    
    # signals for gui integration
    device_connected = pyqtSignal(str)  # device_path
    device_disconnected = pyqtSignal()
    apdu_received = pyqtSignal(bytes)
    apdu_sent = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, attack_manager=None):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.attack_manager = attack_manager
        
        # device state
        self.device_path = None
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False
        
        # communication state
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False
        self.command_queue = asyncio.Queue()
        
        # proxmark state
        self.field_active = False
        self.card_present = False
        self.current_uid = None
        
        self.logger.info("proxmark usb relay initialized")
        
    def scan_devices(self) -> List[str]:
        """Scan for connected Proxmark devices."""
        devices = []
        
        try:
            # scan usb serial ports
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                # check for proxmark identifiers
                if (port.vid == 0x2d2d and port.pid == 0x504d) or \
                   'proxmark' in (port.description or '').lower() or \
                   'pm3' in (port.description or '').lower():
                    devices.append(port.device)
                    
            self.logger.info(f"found {len(devices)} proxmark devices")
            return devices
            
        except Exception as e:
            self.logger.error(f"device scan failed: {e}")
            return []
            
    def connect(self, device_path: str = None) -> bool:
        """Connect to Proxmark device."""
        try:
            if not device_path:
                devices = self.scan_devices()
                if not devices:
                    raise Exception("no proxmark devices found")
                device_path = devices[0]
                
            # open serial connection
            self.serial_conn = serial.Serial(
                port=device_path,
                baudrate=115200,  # default proxmark baudrate
                timeout=2.0,
                write_timeout=2.0
            )
            
            # verify connection
            if not self._verify_connection():
                raise Exception("device verification failed")
                
            self.device_path = device_path
            self.connected = True
            
            # start communication thread
            self.running = True
            self.reader_thread = threading.Thread(target=self._reader_loop)
            self.reader_thread.daemon = True
            self.reader_thread.start()
            
            self.logger.info(f"connected to proxmark: {device_path}")
            self.device_connected.emit(device_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"connection failed: {e}")
            self.error_occurred.emit(f"connection failed: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Disconnect from Proxmark device."""
        try:
            self.running = False
            
            # stop hf field
            if self.field_active:
                self._send_command(ProxmarkCommand(0x0303))  # hf field off
                
            # close serial connection
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
                
            # wait for reader thread
            if self.reader_thread and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=2.0)
                
            self.connected = False
            self.device_path = None
            
            self.logger.info("disconnected from proxmark")
            self.device_disconnected.emit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"disconnect failed: {e}")
            return False
            
    def _verify_connection(self) -> bool:
        """Verify Proxmark connection and capabilities."""
        try:
            # send version command
            version_cmd = ProxmarkCommand(0x0001)  # cmd_version
            response = self._send_command_sync(version_cmd)
            
            if not response:
                return False
                
            self.logger.debug("proxmark version verified")
            return True
            
        except Exception as e:
            self.logger.error(f"verification failed: {e}")
            return False
            
    def start_hf_reader(self) -> bool:
        """Start HF 14A reader mode."""
        try:
            # activate hf field
            field_cmd = ProxmarkCommand(0x0302)  # hf field on
            self._send_command(field_cmd)
            self.field_active = True
            
            # start 14a reader
            reader_cmd = ProxmarkCommand(ProxmarkCommand.CMD_HF_14A_READER)
            self._send_command(reader_cmd)
            
            self.logger.info("hf reader started")
            return True
            
        except Exception as e:
            self.logger.error(f"hf reader start failed: {e}")
            return False
            
    def stop_hf_reader(self) -> bool:
        """Stop HF 14A reader mode."""
        try:
            # deactivate hf field
            field_cmd = ProxmarkCommand(0x0303)  # hf field off
            self._send_command(field_cmd)
            self.field_active = False
            
            self.logger.info("hf reader stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"hf reader stop failed: {e}")
            return False
            
    def send_apdu(self, apdu_bytes: bytes) -> Optional[bytes]:
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
            raw_cmd = ProxmarkCommand(
                ProxmarkCommand.CMD_HF_14A_RAW,
                self._format_apdu_data(apdu_bytes)
            )
            
            response = self._send_command_sync(raw_cmd)
            if response:
                apdu_response = self._parse_apdu_response(response)
                if apdu_response:
                    self.apdu_received.emit(apdu_response)
                    return apdu_response
                    
            return None
            
        except Exception as e:
            self.logger.error(f"apdu send failed: {e}")
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
            self.logger.error(f"response parsing failed: {e}")
            return None
            
    def _send_command(self, command: ProxmarkCommand) -> None:
        """Send command to Proxmark (async)."""
        if self.serial_conn:
            try:
                data = command.to_bytes()
                self.serial_conn.write(data)
                self.serial_conn.flush()
            except Exception as e:
                self.logger.error(f"command send failed: {e}")
                
    def _send_command_sync(self, command: ProxmarkCommand, timeout: float = 2.0) -> Optional[bytes]:
        """Send command and wait for response."""
        if not self.serial_conn:
            return None
            
        try:
            # send command
            data = command.to_bytes()
            self.serial_conn.write(data)
            self.serial_conn.flush()
            
            # wait for response
            start_time = time.time()
            response_data = bytearray()
            
            while time.time() - start_time < timeout:
                if self.serial_conn.in_waiting > 0:
                    chunk = self.serial_conn.read(self.serial_conn.in_waiting)
                    response_data.extend(chunk)
                    
                    # check if we have complete response
                    if len(response_data) >= 4:
                        length = struct.unpack('<H', response_data[:2])[0]
                        if len(response_data) >= length + 4:
                            return bytes(response_data)
                            
                time.sleep(0.01)
                
            return None
            
        except Exception as e:
            self.logger.error(f"sync command failed: {e}")
            return None
            
    def _reader_loop(self) -> None:
        """Main reader thread for incoming data."""
        self.logger.info("reader thread started")
        
        buffer = bytearray()
        
        while self.running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting > 0:
                    data = self.serial_conn.read(self.serial_conn.in_waiting)
                    buffer.extend(data)
                    
                    # process complete messages
                    while len(buffer) >= 4:
                        length = struct.unpack('<H', buffer[:2])[0]
                        msg_size = length + 4
                        
                        if len(buffer) >= msg_size:
                            message = bytes(buffer[:msg_size])
                            buffer = buffer[msg_size:]
                            
                            self._process_message(message)
                        else:
                            break
                            
                time.sleep(0.01)
                
            except Exception as e:
                if self.running:
                    self.logger.error(f"reader loop error: {e}")
                break
                
        self.logger.info("reader thread stopped")
        
    def _process_message(self, message: bytes) -> None:
        """Process incoming message from Proxmark."""
        try:
            if len(message) < 4:
                return
                
            length, cmd = struct.unpack('<HH', message[:4])
            data = message[4:]
            
            # handle different message types
            if cmd == ProxmarkCommand.CMD_HF_14A_READER:
                self._handle_reader_response(data)
            elif cmd == ProxmarkCommand.CMD_HF_14A_RAW:
                self._handle_raw_response(data)
                
        except Exception as e:
            self.logger.error(f"message processing failed: {e}")
            
    def _handle_reader_response(self, data: bytes) -> None:
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
                        self.logger.info(f"card detected: uid={self.current_uid}")
                        
        except Exception as e:
            self.logger.error(f"reader response handling failed: {e}")
            
    def _handle_raw_response(self, data: bytes) -> None:
        """Handle raw APDU response."""
        try:
            if len(data) >= 2:
                # extract apdu response
                apdu_response = self._parse_apdu_response(data)
                if apdu_response:
                    self.apdu_received.emit(apdu_response)
                    
        except Exception as e:
            self.logger.error(f"raw response handling failed: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Get current relay status."""
        return {
            'connected': self.connected,
            'device_path': self.device_path,
            'field_active': self.field_active,
            'card_present': self.card_present,
            'current_uid': self.current_uid
        }
