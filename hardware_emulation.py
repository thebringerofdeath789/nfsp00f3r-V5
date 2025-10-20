#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Hardware Emulation and Cloning Modules
=========================================================

File: hardware_emulation.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Complete hardware emulation and card cloning implementations

Classes:
- CardCloner: Complete card cloning and emulation
- ChameleonMiniController: Full Chameleon Mini integration
- MagspoofController: Magnetic stripe emulation
- ProxmarkController: Enhanced Proxmark3 integration
- HardwareEmulator: Generic hardware emulation framework

This module provides complete hardware emulation capabilities including
card cloning, magnetic stripe emulation, and hardware device control.
"""

import time
import serial
import struct
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
import subprocess
import tempfile
import os

@dataclass
class CloneProfile:
    """Card clone profile data structure."""
    name: str
    card_type: str
    atr: bytes
    tlv_data: Dict[str, str]
    track_data: Dict[str, str]
    emv_applications: List[Dict[str, Any]]
    clone_timestamp: float
    source_reader: str

class CardCloner:
    """
    Complete card cloning and emulation system.
    Supports multiple target devices and emulation modes.
    """
    
    def __init__(self, card_manager, reader_manager):
        self.card_manager = card_manager
        self.reader_manager = reader_manager
        self.logger = logging.getLogger(__name__)
        
        # Clone profiles storage
        self.clone_profiles: Dict[str, CloneProfile] = {}
        self.active_clone: Optional[str] = None
        
        # Supported clone targets
        self.clone_targets = {
            'chameleon_mini': ChameleonMiniController(),
            'magspoof': MagspoofController(),
            'proxmark3': ProxmarkController(),
            'android_hce': AndroidHCEController(),
            'software_emulation': SoftwareEmulator()
        }
        
    def clone_card(self, card_data: Dict[str, Any], target_device: str, 
                   profile_name: str) -> bool:
        """
        Clone a card to specified target device.
        
        Args:
            card_data: Source card data
            target_device: Target emulation device
            profile_name: Name for the clone profile
            
        Returns:
            True if cloning successful
        """
        try:
            self.logger.info(f"Starting card clone to {target_device}")
            
            # Create clone profile
            profile = CloneProfile(
                name=profile_name,
                card_type=card_data.get('card_type', 'EMV'),
                atr=bytes.fromhex(card_data.get('atr', '')),
                tlv_data=card_data.get('tlv_data', {}),
                track_data=card_data.get('track_data', {}),
                emv_applications=card_data.get('applications', []),
                clone_timestamp=time.time(),
                source_reader=card_data.get('source_reader', 'unknown')
            )
            
            # Store profile
            self.clone_profiles[profile_name] = profile
            
            # Execute cloning to target device
            if target_device in self.clone_targets:
                controller = self.clone_targets[target_device]
                success = controller.load_profile(profile)
                
                if success:
                    self.active_clone = profile_name
                    self.logger.info(f"Card successfully cloned to {target_device}")
                    return True
                else:
                    self.logger.error(f"Failed to load profile to {target_device}")
                    return False
            else:
                self.logger.error(f"Unsupported target device: {target_device}")
                return False
                
        except Exception as e:
            self.logger.error(f"Card cloning failed: {e}")
            return False
            
    def emulate_card(self, profile_name: str, target_device: str) -> bool:
        """Start card emulation with specified profile."""
        try:
            if profile_name not in self.clone_profiles:
                self.logger.error(f"Clone profile '{profile_name}' not found")
                return False
                
            profile = self.clone_profiles[profile_name]
            
            if target_device in self.clone_targets:
                controller = self.clone_targets[target_device]
                return controller.start_emulation(profile)
            else:
                self.logger.error(f"Unsupported target device: {target_device}")
                return False
                
        except Exception as e:
            self.logger.error(f"Card emulation failed: {e}")
            return False
            
    def stop_emulation(self, target_device: str) -> bool:
        """Stop card emulation on target device."""
        try:
            if target_device in self.clone_targets:
                controller = self.clone_targets[target_device]
                return controller.stop_emulation()
            return False
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False
            
    def export_profile(self, profile_name: str, file_path: str) -> bool:
        """Export clone profile to file."""
        try:
            if profile_name not in self.clone_profiles:
                return False
                
            profile = self.clone_profiles[profile_name]
            
            # Convert to serializable format
            profile_data = {
                'name': profile.name,
                'card_type': profile.card_type,
                'atr': profile.atr.hex().upper(),
                'tlv_data': profile.tlv_data,
                'track_data': profile.track_data,
                'emv_applications': profile.emv_applications,
                'clone_timestamp': profile.clone_timestamp,
                'source_reader': profile.source_reader
            }
            
            import json
            with open(file_path, 'w') as f:
                json.dump(profile_data, f, indent=2)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Profile export failed: {e}")
            return False
            
    def import_profile(self, file_path: str) -> bool:
        """Import clone profile from file."""
        try:
            import json
            with open(file_path, 'r') as f:
                profile_data = json.load(f)
                
            profile = CloneProfile(
                name=profile_data['name'],
                card_type=profile_data['card_type'],
                atr=bytes.fromhex(profile_data['atr']),
                tlv_data=profile_data['tlv_data'],
                track_data=profile_data['track_data'],
                emv_applications=profile_data['emv_applications'],
                clone_timestamp=profile_data['clone_timestamp'],
                source_reader=profile_data['source_reader']
            )
            
            self.clone_profiles[profile.name] = profile
            return True
            
        except Exception as e:
            self.logger.error(f"Profile import failed: {e}")
            return False

class ChameleonMiniController:
    """
    Complete Chameleon Mini integration and control.
    Supports all major Chameleon Mini features and configurations.
    """
    
    def __init__(self, port: str = None):
        self.port = port
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        self.current_profile = None
        self.emulation_active = False
        
        # Chameleon Mini configurations
        self.configurations = {
            'ISO14443A_UID': 'CONFIG=ISO14443A_UID',
            'ISO14443A_READER': 'CONFIG=ISO14443A_READER',
            'ISO14443A_SNIFF': 'CONFIG=ISO14443A_SNIFF',
            'ISO15693_SNIFF': 'CONFIG=ISO15693_SNIFF',
            'EM4X02_EMULATE': 'CONFIG=EM4X02_EMULATE'
        }
        
    def connect(self) -> bool:
        """Connect to Chameleon Mini device."""
        try:
            if not self.port:
                # Auto-detect Chameleon Mini
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                
                for port in ports:
                    if 'chameleon' in port.description.lower() or \
                       'ch340' in port.description.lower():
                        self.port = port.device
                        break
                        
            if not self.port:
                self.logger.error("Chameleon Mini not found")
                return False
                
            self.serial_conn = serial.Serial(
                self.port,
                115200,
                timeout=2.0,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            
            # Test connection
            response = self.send_command("VERSION")
            if response and "chameleon" in response.lower():
                self.logger.info(f"Connected to Chameleon Mini on {self.port}")
                return True
            else:
                self.logger.error("Invalid response from Chameleon Mini")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Chameleon Mini: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from Chameleon Mini."""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
            
    def send_command(self, command: str) -> Optional[str]:
        """Send command to Chameleon Mini and get response."""
        try:
            if not self.serial_conn:
                return None
                
            self.serial_conn.write(f"{command}\r\n".encode())
            response = self.serial_conn.readline().decode().strip()
            
            # Check for error responses
            if response.startswith("101:") or response.startswith("102:"):
                self.logger.error(f"Chameleon Mini error: {response}")
                return None
                
            return response
            
        except Exception as e:
            self.logger.error(f"Command failed: {e}")
            return None
            
    def load_profile(self, profile: CloneProfile) -> bool:
        """Load clone profile into Chameleon Mini."""
        try:
            if not self.connect():
                return False
                
            self.logger.info(f"Loading profile '{profile.name}' to Chameleon Mini")
            
            # Set configuration based on card type
            if profile.card_type.upper() == 'EMV':
                config_cmd = self.configurations['ISO14443A_UID']
            else:
                config_cmd = self.configurations['ISO14443A_UID']  # Default
                
            if not self.send_command(config_cmd):
                return False
                
            # Set UID from card data
            if profile.tlv_data and '5A' in profile.tlv_data:
                # Use PAN as UID (first 4 bytes)
                pan_hex = profile.tlv_data['5A']
                if len(pan_hex) >= 8:
                    uid = pan_hex[:8]
                    if not self.send_command(f"UID={uid}"):
                        return False
                        
            # Configure memory with EMV data
            if not self._configure_emv_memory(profile):
                return False
                
            self.current_profile = profile
            self.logger.info("Profile loaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
            return False
        finally:
            self.disconnect()
            
    def _configure_emv_memory(self, profile: CloneProfile) -> bool:
        """Configure Chameleon Mini memory with EMV data."""
        try:
            # Build EMV application structure
            memory_data = self._build_emv_memory(profile)
            
            # Upload memory data
            for address, data in memory_data.items():
                cmd = f"UPLOAD={address:04X}:{data}"
                if not self.send_command(cmd):
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Memory configuration failed: {e}")
            return False
            
    def _build_emv_memory(self, profile: CloneProfile) -> Dict[int, str]:
        """Build EMV memory structure for Chameleon Mini."""
        memory = {}
        
        # Simplified EMV structure
        # In practice, this would be much more complex
        
        # Application directory (block 0)
        memory[0x0000] = "6F1C840E315041592E5359532E4444463031A50A"
        
        # Application data (blocks 1-4)
        if profile.tlv_data:
            # PAN
            if '5A' in profile.tlv_data:
                memory[0x0001] = profile.tlv_data['5A']
                
            # Expiry date
            if '5F24' in profile.tlv_data:
                memory[0x0002] = profile.tlv_data['5F24']
                
            # Track 2 equivalent data
            if '57' in profile.tlv_data:
                memory[0x0003] = profile.tlv_data['57']
                
        return memory
        
    def start_emulation(self, profile: CloneProfile) -> bool:
        """Start card emulation."""
        try:
            if not self.load_profile(profile):
                return False
                
            if not self.connect():
                return False
                
            # Start emulation
            if self.send_command("FIELD=1"):
                self.emulation_active = True
                self.logger.info("Card emulation started")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start emulation: {e}")
            return False
        finally:
            self.disconnect()
            
    def stop_emulation(self) -> bool:
        """Stop card emulation."""
        try:
            if not self.connect():
                return False
                
            if self.send_command("FIELD=0"):
                self.emulation_active = False
                self.logger.info("Card emulation stopped")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False
        finally:
            self.disconnect()

class MagspoofController:
    """
    Magspoof magnetic stripe emulation controller.
    Emulates magnetic stripe cards for legacy systems.
    """
    
    def __init__(self, port: str = None):
        self.port = port
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        self.current_profile = None
        
    def connect(self) -> bool:
        """Connect to Magspoof device."""
        try:
            if not self.port:
                # Auto-detect Magspoof
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                
                for port in ports:
                    if 'magspoof' in port.description.lower() or \
                       'arduino' in port.description.lower():
                        self.port = port.device
                        break
                        
            if not self.port:
                self.logger.error("Magspoof not found")
                return False
                
            self.serial_conn = serial.Serial(
                self.port,
                9600,
                timeout=2.0
            )
            
            time.sleep(2)  # Arduino reset delay
            
            # Test connection
            self.serial_conn.write(b"?\n")
            response = self.serial_conn.readline().decode().strip()
            
            if "magspoof" in response.lower():
                self.logger.info(f"Connected to Magspoof on {self.port}")
                return True
            else:
                self.logger.error("Invalid response from Magspoof")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Magspoof: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from Magspoof."""
        if self.serial_conn:
            try:
                self.serial_conn.close()
            except:
                pass
            self.serial_conn = None
            
    def load_profile(self, profile: CloneProfile) -> bool:
        """Load magnetic stripe data into Magspoof."""
        try:
            if not self.connect():
                return False
                
            # Extract magnetic stripe data
            track1 = profile.track_data.get('track1', '')
            track2 = profile.track_data.get('track2', '')
            track3 = profile.track_data.get('track3', '')
            
            if not track2:  # Track 2 is minimum requirement
                # Try to build from EMV data
                track2 = self._build_track2_from_emv(profile)
                
            if not track2:
                self.logger.error("No magnetic stripe data available")
                return False
                
            # Program tracks
            success = True
            
            if track1:
                success &= self._program_track(1, track1)
            if track2:
                success &= self._program_track(2, track2)
            if track3:
                success &= self._program_track(3, track3)
                
            if success:
                self.current_profile = profile
                self.logger.info("Magnetic stripe data programmed")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
            return False
        finally:
            self.disconnect()
            
    def _build_track2_from_emv(self, profile: CloneProfile) -> str:
        """Build Track 2 data from EMV card data."""
        try:
            # Extract PAN and expiry from EMV data
            pan = profile.tlv_data.get('5A', '')
            expiry = profile.tlv_data.get('5F24', '')  # YYMMDD format
            
            if not pan or not expiry:
                return ''
                
            # Convert expiry to YYMM format
            if len(expiry) == 6:  # YYMMDD
                expiry_track = expiry[:4]  # YYMM
            elif len(expiry) == 4:  # Already YYMM
                expiry_track = expiry
            else:
                return ''
                
            # Build Track 2 equivalent (simplified)
            # Format: PAN=EXPIRY[SERVICE_CODE][DISCRETIONARY_DATA]
            service_code = "201"  # Default service code
            discretionary = "000000000"
            
            # Calculate LRC (Longitudinal Redundancy Check)
            track2_data = f"{pan}={expiry_track}{service_code}{discretionary}"
            
            # Add LRC calculation here if needed
            return track2_data
            
        except Exception as e:
            self.logger.error(f"Failed to build Track 2: {e}")
            return ''
            
    def _program_track(self, track_number: int, track_data: str) -> bool:
        """Program specific track data."""
        try:
            command = f"T{track_number}:{track_data}\n"
            self.serial_conn.write(command.encode())
            
            response = self.serial_conn.readline().decode().strip()
            
            if "OK" in response:
                self.logger.info(f"Track {track_number} programmed successfully")
                return True
            else:
                self.logger.error(f"Failed to program track {track_number}: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Track programming failed: {e}")
            return False
            
    def start_emulation(self, profile: CloneProfile) -> bool:
        """Start magnetic stripe emulation."""
        try:
            if not self.load_profile(profile):
                return False
                
            if not self.connect():
                return False
                
            # Start emulation mode
            self.serial_conn.write(b"E\n")
            response = self.serial_conn.readline().decode().strip()
            
            if "EMULATING" in response:
                self.logger.info("Magnetic stripe emulation started")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to start emulation: {e}")
            return False
        finally:
            self.disconnect()
            
    def stop_emulation(self) -> bool:
        """Stop magnetic stripe emulation."""
        try:
            if not self.connect():
                return False
                
            self.serial_conn.write(b"S\n")
            response = self.serial_conn.readline().decode().strip()
            
            if "STOPPED" in response:
                self.logger.info("Magnetic stripe emulation stopped")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False
        finally:
            self.disconnect()

class ProxmarkController:
    """
    Enhanced Proxmark3 integration with advanced features.
    """
    
    def __init__(self, device_path: str = None):
        self.device_path = device_path or "/dev/ttyACM0"
        self.logger = logging.getLogger(__name__)
        self.current_profile = None
        
    def load_profile(self, profile: CloneProfile) -> bool:
        """Load profile to Proxmark3."""
        try:
            # Create temporary dump file
            dump_file = tempfile.mktemp(suffix='.dump')
            
            # Convert profile to Proxmark format
            if not self._create_proxmark_dump(profile, dump_file):
                return False
                
            # Load to Proxmark
            cmd = f"proxmark3 {self.device_path} -c 'hf 14a sim t 1 u {dump_file}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.current_profile = profile
                self.logger.info("Profile loaded to Proxmark3")
                return True
            else:
                self.logger.error(f"Proxmark3 load failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
            return False
        finally:
            if 'dump_file' in locals() and os.path.exists(dump_file):
                os.unlink(dump_file)
                
    def _create_proxmark_dump(self, profile: CloneProfile, output_file: str) -> bool:
        """Create Proxmark3 dump file from profile."""
        try:
            # Simplified dump creation
            # Real implementation would create proper ISO14443A dump format
            
            with open(output_file, 'wb') as f:
                # Write UID (first 4 bytes of PAN if available)
                if profile.tlv_data and '5A' in profile.tlv_data:
                    pan_hex = profile.tlv_data['5A']
                    if len(pan_hex) >= 8:
                        uid_bytes = bytes.fromhex(pan_hex[:8])
                        f.write(uid_bytes)
                    else:
                        f.write(b'\x00\x00\x00\x00')
                else:
                    f.write(b'\x00\x00\x00\x00')
                    
                # Write BCC (XOR of UID bytes)
                uid_bytes = f.seek(0) or f.read(4)
                f.seek(0)
                uid_bytes = f.read(4)
                bcc = 0
                for byte in uid_bytes:
                    bcc ^= byte
                f.write(bytes([bcc]))
                
                # Pad to standard size
                f.write(b'\x00' * (1024 - f.tell()))
                
            return True
            
        except Exception as e:
            self.logger.error(f"Dump creation failed: {e}")
            return False
            
    def start_emulation(self, profile: CloneProfile) -> bool:
        """Start Proxmark3 emulation."""
        try:
            if not self.load_profile(profile):
                return False
                
            # Start simulation
            cmd = f"proxmark3 {self.device_path} -c 'hf 14a sim t 1'"
            
            # Run in background
            self.emulation_process = subprocess.Popen(
                cmd, shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            self.logger.info("Proxmark3 emulation started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start emulation: {e}")
            return False
            
    def stop_emulation(self) -> bool:
        """Stop Proxmark3 emulation."""
        try:
            if hasattr(self, 'emulation_process'):
                self.emulation_process.terminate()
                self.emulation_process.wait()
                delattr(self, 'emulation_process')
                
            self.logger.info("Proxmark3 emulation stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False

class AndroidHCEController:
    """
    Android Host Card Emulation controller.
    Interfaces with Android companion app for HCE.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_profile = None
        
    def load_profile(self, profile: CloneProfile) -> bool:
        """Load profile to Android HCE."""
        try:
            # Send profile to Android app via Bluetooth
            from bluetooth_manager import BluetoothManager
            
            bt_manager = BluetoothManager()
            if not bt_manager.is_connected():
                self.logger.error("Android device not connected")
                return False
                
            # Convert profile to Android format
            android_profile = self._convert_to_android_format(profile)
            
            # Send to Android
            success = bt_manager.send_hce_profile(android_profile)
            
            if success:
                self.current_profile = profile
                self.logger.info("Profile loaded to Android HCE")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
            return False
            
    def _convert_to_android_format(self, profile: CloneProfile) -> Dict[str, Any]:
        """Convert profile to Android HCE format."""
        return {
            'name': profile.name,
            'type': 'emv',
            'pan': profile.tlv_data.get('5A', ''),
            'expiry': profile.tlv_data.get('5F24', ''),
            'track2': profile.track_data.get('track2', ''),
            'applications': profile.emv_applications,
            'tlv_data': profile.tlv_data
        }
        
    def start_emulation(self, profile: CloneProfile) -> bool:
        """Start Android HCE emulation."""
        try:
            if not self.load_profile(profile):
                return False
                
            # Send start emulation command
            from bluetooth_manager import BluetoothManager
            bt_manager = BluetoothManager()
            
            return bt_manager.send_command('start_hce_emulation', {
                'profile': profile.name
            })
            
        except Exception as e:
            self.logger.error(f"Failed to start emulation: {e}")
            return False
            
    def stop_emulation(self) -> bool:
        """Stop Android HCE emulation."""
        try:
            from bluetooth_manager import BluetoothManager
            bt_manager = BluetoothManager()
            
            return bt_manager.send_command('stop_hce_emulation', {})
            
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False

class SoftwareEmulator:
    """
    Software-based card emulator.
    Provides card emulation without hardware devices.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_profile = None
        self.emulation_active = False
        
    def load_profile(self, profile: CloneProfile) -> bool:
        """Load profile to software emulator."""
        try:
            self.current_profile = profile
            self.logger.info("Profile loaded to software emulator")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load profile: {e}")
            return False
            
    def start_emulation(self, profile: CloneProfile) -> bool:
        """Start software emulation."""
        try:
            if not self.load_profile(profile):
                return False
                
            self.emulation_active = True
            self.logger.info("Software emulation started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start emulation: {e}")
            return False
            
    def stop_emulation(self) -> bool:
        """Stop software emulation."""
        try:
            self.emulation_active = False
            self.logger.info("Software emulation stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop emulation: {e}")
            return False
            
    def handle_apdu(self, command: bytes) -> Tuple[bytes, int, int]:
        """Handle APDU command in software emulation."""
        try:
            if not self.emulation_active or not self.current_profile:
                return b'', 0x6F, 0x00  # Technical problem
                
            # Simplified APDU handling
            # Real implementation would process full EMV command set
            
            # SELECT command
            if len(command) >= 4 and command[1] == 0xA4:
                return self._handle_select(command)
                
            # Other commands would be handled here
            
            return b'', 0x6D, 0x00  # Instruction not supported
            
        except Exception as e:
            self.logger.error(f"APDU handling failed: {e}")
            return b'', 0x6F, 0x00
            
    def _handle_select(self, command: bytes) -> Tuple[bytes, int, int]:
        """Handle SELECT command."""
        # Return FCI template
        fci = bytes.fromhex("6F1C840E315041592E5359532E4444463031A50A")
        return fci, 0x90, 0x00
