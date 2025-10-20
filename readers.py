#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: readers.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: All card reader implementations with hotplug support

Classes:
- ReaderManager: Main reader management class
- PCSCCardReader: PC/SC compatible reader (ACR122U, etc.)
- PN532Reader: Adafruit PN532 NFC reader
- ProxmarkReader: Proxmark3 device interface
- ChameleonReader: Chameleon Mini device interface
- MagspoofReader: Magspoof device interface

Functions:
- detect_readers(): Auto-detect available readers
- validate_reader_response(): Validate reader response data

This module provides unified interfaces for all supported card readers
including hotplug detection, real-time card insertion/removal events,
and proper error handling for all device types.

Based on code from:
- dlenski/python-pyscard (PC/SC implementation)
- AdamLaurie/RFIDIOt (PN532 and general NFC)
- RfidResearchGroup/proxmark3 (Proxmark3 interface)
- Various hardware-specific implementations
"""

import logging
import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QTimer

try:
    import smartcard
    from smartcard.System import readers
    from smartcard.CardMonitoring import CardMonitor, CardObserver
    from smartcard.util import toHexString
    from smartcard.Exceptions import CardConnectionException, NoCardException
    PCSC_AVAILABLE = True
except ImportError:
    PCSC_AVAILABLE = False
    logging.warning("PC/SC not available - install pyscard for PC/SC reader support")

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logging.warning("PySerial not available - install pyserial for serial device support")

try:
    import nfc
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    logging.warning("NFCPy not available - install nfcpy for advanced NFC support")

class CardReaderError(Exception):
    """Custom exception for card reader errors."""
    pass

class CardEvent:
    """Represents a card insertion or removal event."""
    INSERTED = "inserted"
    REMOVED = "removed"
    
    def __init__(self, event_type: str, reader_name: str, atr: bytes = None):
        self.event_type = event_type
        self.reader_name = reader_name
        self.atr = atr
        self.timestamp = time.time()

class BaseCardReader(ABC):
    """
    Abstract base class for all card readers.
    Defines the common interface that all readers must implement.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.connected = False
        self.card_present = False
        self.current_atr = None
        
        # Callbacks for events
        self.card_inserted_callback: Optional[Callable] = None
        self.card_removed_callback: Optional[Callable] = None
        self.reader_connected_callback: Optional[Callable] = None
        self.reader_disconnected_callback: Optional[Callable] = None
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the reader."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the reader."""
        pass
    
    @abstractmethod
    def is_card_present(self) -> bool:
        """Check if a card is present."""
        pass
    
    @abstractmethod
    def get_atr(self) -> Optional[bytes]:
        """Get the Answer to Reset (ATR) of the current card."""
        pass
    
    @abstractmethod
    def transmit(self, apdu: bytes) -> tuple:
        """
        Transmit APDU to card.
        Returns: (response_data, sw1, sw2)
        """
        pass
    
    def transmit_apdu(self, apdu: bytes) -> Optional[bytes]:
        """
        Convenience method to transmit APDU and return full response.
        Returns: response_data + sw1 + sw2 as bytes, or None on error
        """
        try:
            response_data, sw1, sw2 = self.transmit(apdu)
            return response_data + bytes([sw1, sw2])
        except Exception as e:
            self.logger.error(f"APDU transmission failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if reader connection is working."""
        try:
            # Try a simple test - checking if card is present should work
            return self.is_card_present()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def set_callbacks(self, card_inserted=None, card_removed=None, 
                     reader_connected=None, reader_disconnected=None):
        """Set callback functions for reader events."""
        self.card_inserted_callback = card_inserted
        self.card_removed_callback = card_removed
        self.reader_connected_callback = reader_connected
        self.reader_disconnected_callback = reader_disconnected

class PCSCCardReader(BaseCardReader):
    """
    PC/SC compatible card reader implementation.
    Supports all PC/SC compatible readers including ACR122U.
    """
    
    def __init__(self, reader_name: str):
        super().__init__(reader_name)
        self.reader = None
        self.connection = None
        self.protocol = None
        
        if not PCSC_AVAILABLE:
            raise CardReaderError("PC/SC not available - install pyscard")
    
    def connect(self) -> bool:
        """Connect to the PC/SC reader."""
        try:
            # Find the reader
            reader_list = readers()
            matching_readers = [r for r in reader_list if self.name in str(r)]
            
            if not matching_readers:
                self.logger.error(f"Reader {self.name} not found")
                return False
            
            self.reader = matching_readers[0]
            self.connected = True
            
            # Check for card presence immediately after connecting
            self.is_card_present()
            
            if self.reader_connected_callback:
                self.reader_connected_callback(self.name)
            
            self.logger.info(f"Connected to PC/SC reader: {self.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to reader {self.name}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the PC/SC reader."""
        try:
            if self.connection:
                self.connection.disconnect()
                self.connection = None
            
            self.connected = False
            self.card_present = False
            self.current_atr = None
            
            if self.reader_disconnected_callback:
                self.reader_disconnected_callback(self.name)
            
            self.logger.info(f"Disconnected from reader: {self.name}")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from reader: {e}")
    
    def is_card_present(self) -> bool:
        """Check if a card is present in the reader."""
        try:
            if not self.reader:
                return False
            
            # Use PCSC status to check card presence without connecting
            from smartcard.CardRequest import CardRequest
            from smartcard.CardType import AnyCardType
            from smartcard.Exceptions import CardRequestTimeoutException
            
            try:
                # Check with longer timeout for contactless cards
                cardrequest = CardRequest(timeout=2.0, cardType=AnyCardType(), readers=[self.reader])
                cardservice = cardrequest.waitforcard()
                
                # If we get here, card is present
                if not self.card_present:
                    # Card was just inserted
                    self.card_present = True
                    # Don't connect yet, just mark as present
                    self.logger.info(f"Card detected in {self.name}")
                
                return True
                
            except CardRequestTimeoutException:
                # No card present
                if self.card_present:
                    # Card was just removed
                    self.card_present = False
                    self.current_atr = None
                    
                    # Disconnect from card if connected
                    if self.connection:
                        try:
                            self.connection.disconnect()
                        except:
                            pass
                        self.connection = None
                    
                    if self.card_removed_callback:
                        self.card_removed_callback(self.name)
                    
                    self.logger.info(f"Card removed from {self.name}")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking card presence: {e}")
            return False
            self.logger.error(f"Error checking card presence: {e}")
            return False
    
    def connect_to_card(self) -> bool:
        """Establish connection to the card for APDU communication."""
        try:
            if self.connection:
                # Already connected, test if still valid
                try:
                    # Try to get ATR to test connection
                    atr = self.connection.getATR()
                    if atr:
                        self.current_atr = bytes(atr)
                        return True
                except:
                    # Connection lost, clean up
                    try:
                        self.connection.disconnect()
                    except:
                        pass
                    self.connection = None
                    
            # Create new connection
            from smartcard.CardRequest import CardRequest
            from smartcard.CardType import AnyCardType
            from smartcard.CardConnection import CardConnection
            
            self.logger.info(f"Connecting to card in {self.name}")
            cardrequest = CardRequest(timeout=5, cardType=AnyCardType(), readers=[self.reader])
            cardservice = cardrequest.waitforcard()
            
            # Get connection
            connection = cardservice.connection
            
            # Try to connect with best protocol
            protocols = [
                CardConnection.T1_protocol,  # Try T=1 first (works better with many cards)
                CardConnection.T0_protocol,
                None  # Any protocol
            ]
            
            connected = False
            protocol_used = None
            for protocol in protocols:
                try:
                    if protocol:
                        connection.connect(protocol)
                        protocol_used = "T=1" if protocol == CardConnection.T1_protocol else "T=0"
                    else:
                        connection.connect()
                        protocol_used = "Any"
                    connected = True
                    break
                except Exception as e:
                    self.logger.debug(f"Protocol {protocol} failed: {e}")
                    continue
            
            if not connected:
                self.logger.error("Failed to connect with any protocol")
                return False
                
            self.connection = connection
            self.logger.info(f"Connected using {protocol_used} protocol")
            
            # Get ATR immediately after connecting
            try:
                atr = connection.getATR()
                if atr:
                    self.current_atr = bytes(atr)
                    atr_hex = self.current_atr.hex().upper()
                    self.logger.info(f"Card connected, ATR: {atr_hex}")
                else:
                    self.logger.warning("Connected but no ATR received")
                    self.current_atr = None
            except Exception as e:
                self.logger.warning(f"Connected but ATR read failed: {e}")
                self.current_atr = None
            
            # Update status
            self.card_present = True
            
            # Trigger callback after everything is set up
            if self.card_inserted_callback and self.current_atr:
                try:
                    self.card_inserted_callback(self.name, self.current_atr)
                except Exception as e:
                    self.logger.error(f"Card inserted callback error: {e}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to card: {e}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error connecting to card: {e}")
            return False

    def get_atr(self) -> Optional[bytes]:
        """Get the ATR of the current card."""
        try:
            # If we already have a valid ATR and connection, return it
            if self.current_atr and self.connection:
                try:
                    # Verify connection is still active
                    test_atr = self.connection.getATR()
                    if test_atr:
                        return self.current_atr
                except:
                    # Connection lost, clear ATR
                    self.current_atr = None
                    self.connection = None
            
            # Try to connect and get fresh ATR
            if not self.connection:
                if not self.connect_to_card():
                    return None
            
            # Get ATR from active connection
            if self.connection:
                try:
                    atr = self.connection.getATR()
                    if atr:
                        self.current_atr = bytes(atr)
                        return self.current_atr
                except Exception as e:
                    self.logger.debug(f"ATR read failed: {e}")
                    
            return self.current_atr
            
        except Exception as e:
            self.logger.error(f"Error getting ATR: {e}")
            return None
    
    def transmit(self, apdu: bytes) -> tuple:
        """Transmit APDU to the card."""
        try:
            # Auto-connect to card if not already connected
            if not self.connection:
                if not self.connect_to_card():
                    raise CardReaderError("Failed to connect to card")
            
            # Convert bytes to list for pyscard
            apdu_list = list(apdu)
            
            self.logger.debug(f"APDU TX: {apdu.hex().upper()}")
            
            response, sw1, sw2 = self.connection.transmit(apdu_list)
            
            response_bytes = bytes(response)
            
            self.logger.debug(f"APDU RX: {response_bytes.hex().upper()}{sw1:02X}{sw2:02X}")
            
            return response_bytes, sw1, sw2
            
        except Exception as e:
            self.logger.error(f"Error transmitting APDU: {e}")
            # Try to reconnect once
            try:
                self.logger.info("Attempting to reconnect and retry APDU")
                self.connection = None
                if self.connect_to_card():
                    apdu_list = list(apdu)
                    response, sw1, sw2 = self.connection.transmit(apdu_list)
                    response_bytes = bytes(response)
                    self.logger.info("APDU retry successful")
                    return response_bytes, sw1, sw2
            except:
                pass
            raise CardReaderError(f"APDU transmission failed: {e}")

class PN532Reader(BaseCardReader):
    """
    Adafruit PN532 NFC reader implementation.
    Supports both UART and I2C interfaces.
    """
    
    def __init__(self, port: str = None, interface: str = "uart"):
        super().__init__(f"PN532-{interface}-{port or 'auto'}")
        self.port = port
        self.interface = interface
        self.serial_conn = None
        self.nfc_device = None
        
        if not SERIAL_AVAILABLE:
            raise CardReaderError("PySerial not available - install pyserial")
    
    def connect(self) -> bool:
        """Connect to the PN532 reader."""
        try:
            if self.interface == "uart":
                return self._connect_uart()
            elif self.interface == "i2c":
                return self._connect_i2c()
            else:
                raise CardReaderError(f"Unsupported interface: {self.interface}")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to PN532: {e}")
            return False
    
    def _connect_uart(self) -> bool:
        """Connect via UART interface."""
        try:
            if not self.port:
                # Auto-detect PN532
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    # Try to detect PN532 by sending version command
                    try:
                        test_conn = serial.Serial(port.device, 115200, timeout=1)
                        if self._test_pn532_connection(test_conn):
                            self.port = port.device
                            test_conn.close()
                            break
                        test_conn.close()
                    except:
                        continue
                
                if not self.port:
                    self.logger.error("No PN532 device found")
                    return False
            
            self.serial_conn = serial.Serial(self.port, 115200, timeout=1)
            
            # Initialize PN532
            if not self._initialize_pn532():
                return False
            
            self.connected = True
            
            if self.reader_connected_callback:
                self.reader_connected_callback(self.name)
            
            self.logger.info(f"Connected to PN532 on {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PN532 UART: {e}")
            return False
    
    def _connect_i2c(self) -> bool:
        """Connect via I2C interface."""
        try:
            # This would require platform-specific I2C libraries
            # Implementation depends on the specific platform (RPi, etc.)
            self.logger.warning("I2C interface not yet implemented")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PN532 I2C: {e}")
            return False
    
    def _test_pn532_connection(self, conn) -> bool:
        """Test if a serial connection is a PN532."""
        try:
            # Send GetFirmwareVersion command
            cmd = bytes([0x00, 0x00, 0xFF, 0x02, 0xFE, 0xD4, 0x02, 0x2A, 0x00])
            conn.write(cmd)
            time.sleep(0.1)
            
            response = conn.read(20)
            # Check for valid PN532 response
            return len(response) > 10 and response[0:3] == bytes([0x00, 0x00, 0xFF])
            
        except:
            return False
    
    def _initialize_pn532(self) -> bool:
        """Initialize PN532 settings."""
        try:
            # Wake up PN532
            self.serial_conn.write(bytes([0x55, 0x55, 0x00, 0x00, 0x00]))
            time.sleep(0.1)
            
            # Get firmware version
            cmd = bytes([0x00, 0x00, 0xFF, 0x02, 0xFE, 0xD4, 0x02, 0x2A, 0x00])
            self.serial_conn.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_conn.read(20)
            if len(response) < 10:
                return False
            
            # Configure PN532 for card reading
            # Set SAM configuration
            sam_cmd = bytes([0x00, 0x00, 0xFF, 0x04, 0xFC, 0xD4, 0x14, 0x01, 0x14, 0x01, 0x02, 0x00])
            self.serial_conn.write(sam_cmd)
            time.sleep(0.1)
            
            # Clear any remaining data
            self.serial_conn.read(100)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing PN532: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from PN532."""
        try:
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            self.connected = False
            self.card_present = False
            self.current_atr = None
            
            if self.reader_disconnected_callback:
                self.reader_disconnected_callback(self.name)
            
            self.logger.info(f"Disconnected from PN532")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from PN532: {e}")
    
    def is_card_present(self) -> bool:
        """Check if a card is present."""
        try:
            if not self.serial_conn:
                return False
            
            # Send InListPassiveTarget command
            cmd = bytes([0x00, 0x00, 0xFF, 0x04, 0xFC, 0xD4, 0x4A, 0x01, 0x00, 0xE1, 0x00])
            self.serial_conn.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_conn.read(50)
            
            # Check for successful response
            if len(response) > 10 and response[8] == 0xD5 and response[9] == 0x4B:
                if response[10] == 0x01:  # One card found
                    if not self.card_present:
                        self.card_present = True
                        # Extract ATR/UID
                        uid_len = response[12]
                        uid = response[13:13+uid_len]
                        self.current_atr = uid
                        
                        if self.card_inserted_callback:
                            self.card_inserted_callback(self.name, self.current_atr)
                        
                        self.logger.info(f"Card detected by PN532, UID: {uid.hex().upper()}")
                    
                    return True
                else:
                    if self.card_present:
                        self.card_present = False
                        self.current_atr = None
                        
                        if self.card_removed_callback:
                            self.card_removed_callback(self.name)
                        
                        self.logger.info("Card removed from PN532")
                    
                    return False
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking card presence on PN532: {e}")
            return False
    
    def get_atr(self) -> Optional[bytes]:
        """Get the UID/ATR of the current card."""
        return self.current_atr
    
    def transmit(self, apdu: bytes) -> tuple:
        """Transmit APDU through PN532."""
        try:
            if not self.serial_conn or not self.card_present:
                raise CardReaderError("No card present")
            
            # Construct InDataExchange command
            cmd_len = len(apdu) + 2
            checksum = (0x100 - (0xD4 + 0x40 + 0x01 + sum(apdu))) & 0xFF
            
            cmd = bytes([0x00, 0x00, 0xFF, cmd_len, 0x100-cmd_len, 0xD4, 0x40, 0x01]) + apdu + bytes([checksum, 0x00])
            
            self.serial_conn.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_conn.read(100)
            
            if len(response) < 10:
                raise CardReaderError("No response from card")
            
            # Parse response
            if response[8] == 0xD5 and response[9] == 0x41:
                if response[10] == 0x00:  # Success
                    data_len = response[3] - 3
                    response_data = response[11:11+data_len-2]
                    sw1 = response[11+data_len-2]
                    sw2 = response[11+data_len-1]
                    
                    self.logger.debug(f"PN532 APDU >> {apdu.hex().upper()}")
                    self.logger.debug(f"PN532 APDU << {response_data.hex().upper()}{sw1:02X}{sw2:02X}")
                    
                    return response_data, sw1, sw2
                else:
                    raise CardReaderError(f"Card error: {response[10]:02X}")
            else:
                raise CardReaderError("Invalid response from PN532")
                
        except Exception as e:
            self.logger.error(f"Error transmitting APDU via PN532: {e}")
            raise CardReaderError(f"PN532 APDU transmission failed: {e}")

class ProxmarkReader(BaseCardReader):
    """
    Proxmark3 device interface.
    Provides basic card reading capabilities through Proxmark3.
    """
    
    def __init__(self, port: str = None):
        super().__init__(f"Proxmark3-{port or 'auto'}")
        self.port = port
        self.serial_conn = None
        
        if not SERIAL_AVAILABLE:
            raise CardReaderError("PySerial not available")
    
    def connect(self) -> bool:
        """Connect to Proxmark3."""
        try:
            if not self.port:
                # Auto-detect Proxmark3
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    if 'proxmark' in port.description.lower() or 'pm3' in port.description.lower():
                        self.port = port.device
                        break
                
                if not self.port:
                    self.logger.error("No Proxmark3 device found")
                    return False
            
            self.serial_conn = serial.Serial(self.port, 115200, timeout=2)
            
            # Test connection
            self.serial_conn.write(b'hw version\n')
            time.sleep(0.5)
            response = self.serial_conn.read(1000).decode('utf-8', errors='ignore')
            
            if 'proxmark' not in response.lower():
                self.logger.error("Device does not appear to be a Proxmark3")
                return False
            
            self.connected = True
            
            if self.reader_connected_callback:
                self.reader_connected_callback(self.name)
            
            self.logger.info(f"Connected to Proxmark3 on {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmark3: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Proxmark3."""
        try:
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            self.connected = False
            self.card_present = False
            
            if self.reader_disconnected_callback:
                self.reader_disconnected_callback(self.name)
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from Proxmark3: {e}")
    
    def is_card_present(self) -> bool:
        """Check for card presence using Proxmark3."""
        try:
            if not self.serial_conn:
                return False
            
            # Send HF search command
            self.serial_conn.write(b'hf search\n')
            time.sleep(1)
            response = self.serial_conn.read(2000).decode('utf-8', errors='ignore')
            
            # Check for ISO14443A detection
            if 'iso14443a' in response.lower() or 'uid' in response.lower():
                if not self.card_present:
                    self.card_present = True
                    
                    # Extract UID if possible
                    uid_match = None
                    lines = response.split('\n')
                    for line in lines:
                        if 'uid' in line.lower():
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if 'uid' in part.lower() and i + 1 < len(parts):
                                    uid_str = parts[i + 1].replace(':', '')
                                    try:
                                        uid_match = bytes.fromhex(uid_str)
                                        break
                                    except:
                                        continue
                    
                    self.current_atr = uid_match or b'\x00\x00\x00\x00'
                    
                    if self.card_inserted_callback:
                        self.card_inserted_callback(self.name, self.current_atr)
                    
                    self.logger.info("Card detected by Proxmark3")
                
                return True
            else:
                if self.card_present:
                    self.card_present = False
                    self.current_atr = None
                    
                    if self.card_removed_callback:
                        self.card_removed_callback(self.name)
                    
                    self.logger.info("Card removed from Proxmark3")
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking card presence on Proxmark3: {e}")
            return False
    
    def get_atr(self) -> Optional[bytes]:
        """Get card UID/ATR."""
        return self.current_atr
    
    def transmit(self, apdu: bytes) -> tuple:
        """Transmit APDU through Proxmark3."""
        try:
            if not self.serial_conn or not self.card_present:
                raise CardReaderError("No card present")
            
            # Use hf 14a raw command
            apdu_hex = apdu.hex()
            cmd = f'hf 14a raw -s -c {apdu_hex}\n'
            
            self.serial_conn.write(cmd.encode())
            time.sleep(0.5)
            
            response = self.serial_conn.read(1000).decode('utf-8', errors='ignore')
            
            # Parse response
            lines = response.split('\n')
            for line in lines:
                if len(line.strip()) >= 4 and all(c in '0123456789ABCDEF ' for c in line.strip().upper()):
                    hex_data = line.strip().replace(' ', '')
                    if len(hex_data) >= 4:
                        try:
                            response_bytes = bytes.fromhex(hex_data)
                            if len(response_bytes) >= 2:
                                sw1 = response_bytes[-2]
                                sw2 = response_bytes[-1]
                                data = response_bytes[:-2]
                                
                                self.logger.debug(f"PM3 APDU >> {apdu.hex().upper()}")
                                self.logger.debug(f"PM3 APDU << {data.hex().upper()}{sw1:02X}{sw2:02X}")
                                
                                return data, sw1, sw2
                        except:
                            continue
            
            raise CardReaderError("No valid response from Proxmark3")
            
        except Exception as e:
            self.logger.error(f"Error transmitting APDU via Proxmark3: {e}")
            raise CardReaderError(f"Proxmark3 APDU transmission failed: {e}")

class ChameleonReader(BaseCardReader):
    """
    Chameleon Mini device interface.
    Provides card emulation and reading capabilities.
    """
    
    def __init__(self, port: str = None):
        super().__init__(f"Chameleon-{port or 'auto'}")
        self.port = port
        self.serial_conn = None
        
        if not SERIAL_AVAILABLE:
            raise CardReaderError("PySerial not available")
    
    def connect(self) -> bool:
        """Connect to Chameleon Mini."""
        try:
            if not self.port:
                # Auto-detect Chameleon
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    if 'chameleon' in port.description.lower():
                        self.port = port.device
                        break
                
                if not self.port:
                    self.logger.error("No Chameleon Mini device found")
                    return False
            
            self.serial_conn = serial.Serial(self.port, 115200, timeout=1)
            
            # Test connection
            self.serial_conn.write(b'VERSION?\r\n')
            time.sleep(0.1)
            response = self.serial_conn.read(100).decode('utf-8', errors='ignore')
            
            if 'chameleon' not in response.lower():
                self.logger.error("Device does not appear to be Chameleon Mini")
                return False
            
            self.connected = True
            
            if self.reader_connected_callback:
                self.reader_connected_callback(self.name)
            
            self.logger.info(f"Connected to Chameleon Mini on {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Chameleon Mini: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Chameleon Mini."""
        try:
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            self.connected = False
            self.card_present = False
            
            if self.reader_disconnected_callback:
                self.reader_disconnected_callback(self.name)
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from Chameleon Mini: {e}")
    
    def is_card_present(self) -> bool:
        """Chameleon Mini operates in emulation mode, always 'present'."""
        # For emulation mode, we consider the card always present
        if self.connected and not self.card_present:
            self.card_present = True
            self.current_atr = b'\x3B\x00'  # Dummy ATR
            
            if self.card_inserted_callback:
                self.card_inserted_callback(self.name, self.current_atr)
        
        return self.connected
    
    def get_atr(self) -> Optional[bytes]:
        """Get emulated card ATR."""
        return self.current_atr
    
    def transmit(self, apdu: bytes) -> tuple:
        """Handle APDU in emulation mode."""
        try:
            if not self.serial_conn:
                raise CardReaderError("Not connected to Chameleon Mini")
            
            # In emulation mode, forward APDU to the Chameleon Mini device
            hex_apdu = apdu.hex().upper()
            command = f"SEND {hex_apdu}\r\n"
            
            self.serial_conn.write(command.encode())
            time.sleep(0.1)
            response = self.serial_conn.read(1024).decode('utf-8', errors='ignore').strip()
            
            if response and response.startswith("200:"):
                # Parse response data and status words
                response_data = response[4:]  # Remove "200:" prefix
                if len(response_data) >= 4:
                    try:
                        # Extract SW1 SW2 from last 2 bytes
                        resp_bytes = bytes.fromhex(response_data)
                        if len(resp_bytes) >= 2:
                            data = resp_bytes[:-2]
                            sw1 = resp_bytes[-2]
                            sw2 = resp_bytes[-1]
                            return data, sw1, sw2
                    except ValueError:
                        pass
                
            # Default response if parsing fails
            return b'', 0x90, 0x00
            
        except Exception as e:
            self.logger.error(f"Error handling APDU on Chameleon Mini: {e}")
            raise CardReaderError(f"Chameleon Mini APDU failed: {e}")

class MagspoofReader(BaseCardReader):
    """
    Magspoof device interface for magnetic stripe emulation.
    """
    
    def __init__(self, port: str = None):
        super().__init__(f"Magspoof-{port or 'auto'}")
        self.port = port
        self.serial_conn = None
        
        if not SERIAL_AVAILABLE:
            raise CardReaderError("PySerial not available")
    
    def connect(self) -> bool:
        """Connect to Magspoof device."""
        try:
            if not self.port:
                # Auto-detect Magspoof
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    if 'magspoof' in port.description.lower():
                        self.port = port.device
                        break
                
                if not self.port:
                    self.logger.error("No Magspoof device found")
                    return False
            
            self.serial_conn = serial.Serial(self.port, 9600, timeout=1)
            
            # Test connection
            self.serial_conn.write(b'?\n')
            time.sleep(0.1)
            response = self.serial_conn.read(100)
            
            self.connected = True
            
            if self.reader_connected_callback:
                self.reader_connected_callback(self.name)
            
            self.logger.info(f"Connected to Magspoof on {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Magspoof: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Magspoof."""
        try:
            if self.serial_conn:
                self.serial_conn.close()
                self.serial_conn = None
            
            self.connected = False
            self.card_present = False
            
            if self.reader_disconnected_callback:
                self.reader_disconnected_callback(self.name)
                
        except Exception as e:
            self.logger.error(f"Error disconnecting from Magspoof: {e}")
    
    def is_card_present(self) -> bool:
        """Magspoof emulates magstripe, always 'present' when connected."""
        if self.connected and not self.card_present:
            self.card_present = True
            self.current_atr = b'\x4D\x53'  # 'MS' for MagStripe
            
            if self.card_inserted_callback:
                self.card_inserted_callback(self.name, self.current_atr)
        
        return self.connected
    
    def get_atr(self) -> Optional[bytes]:
        """Get magstripe identifier."""
        return self.current_atr
    
    def transmit(self, apdu: bytes) -> tuple:
        """Magspoof doesn't support APDU transmission."""
        raise CardReaderError("Magspoof does not support APDU transmission")
    
    def emit_track_data(self, track1: str = None, track2: str = None, track3: str = None):
        """Emit magnetic stripe track data."""
        try:
            if not self.serial_conn:
                raise CardReaderError("Not connected to Magspoof")
            
            if track2:
                cmd = f"2{track2}\n"
                self.serial_conn.write(cmd.encode())
                self.logger.info(f"Emitted track2 data via Magspoof")
            
            if track1:
                cmd = f"1{track1}\n"
                self.serial_conn.write(cmd.encode())
                self.logger.info(f"Emitted track1 data via Magspoof")
            
        except Exception as e:
            self.logger.error(f"Error emitting track data: {e}")
            raise CardReaderError(f"Failed to emit track data: {e}")

class ReaderMonitorThread(QThread):
    """Thread for monitoring reader status and card presence."""
    
    reader_connected = pyqtSignal(str)
    reader_disconnected = pyqtSignal(str)
    card_inserted = pyqtSignal(str, bytes)
    card_removed = pyqtSignal(str)
    
    def __init__(self, reader_manager):
        super().__init__()
        self.reader_manager = reader_manager
        self.running = False
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Main monitoring loop."""
        self.running = True
        
        while self.running:
            try:
                # Check all readers
                for reader in self.reader_manager.readers.values():
                    if reader.connected:
                        reader.is_card_present()
                
                time.sleep(0.5)  # Check every 500ms
                
            except Exception as e:
                self.logger.error(f"Error in reader monitoring: {e}")
                time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread."""
        self.running = False
        self.wait()

class ReaderManager(QObject):
    """
    Main reader management class that handles all types of card readers.
    Provides unified interface for reader detection, connection, and monitoring.
    """
    
    reader_connected = pyqtSignal(str)
    reader_disconnected = pyqtSignal(str)
    card_inserted = pyqtSignal(str, bytes)
    card_removed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Dictionary of active readers {name: reader_instance}
        self.readers: Dict[str, BaseCardReader] = {}
        
        # Monitoring thread
        self.monitor_thread = None
        
        # Capabilities
        self.capabilities = {
            'pcsc': PCSC_AVAILABLE,
            'serial': SERIAL_AVAILABLE,
            'nfc': NFC_AVAILABLE
        }
        
        self.logger.info(f"Reader manager initialized with capabilities: {self.capabilities}")
    
    def detect_readers(self) -> List[Dict[str, str]]:
        """
        Detect all available card readers.
        
        Returns:
            List of reader information dictionaries
        """
        detected_readers = []
        
        # Detect PC/SC readers
        if PCSC_AVAILABLE:
            try:
                pcsc_readers = readers()
                for reader in pcsc_readers:
                    detected_readers.append({
                        'name': str(reader),
                        'type': 'pcsc',
                        'description': f"PC/SC Reader: {reader}"
                    })
            except Exception as e:
                self.logger.error(f"Error detecting PC/SC readers: {e}")
        
        # Detect serial-based devices
        if SERIAL_AVAILABLE:
            try:
                ports = serial.tools.list_ports.comports()
                for port in ports:
                    desc_lower = port.description.lower()
                    
                    if 'pn532' in desc_lower or 'nfc' in desc_lower:
                        detected_readers.append({
                            'name': f"PN532-{port.device}",
                            'type': 'pn532',
                            'description': f"PN532 NFC Reader: {port.device}"
                        })
                    elif 'proxmark' in desc_lower or 'pm3' in desc_lower:
                        detected_readers.append({
                            'name': f"Proxmark3-{port.device}",
                            'type': 'proxmark3',
                            'description': f"Proxmark3: {port.device}"
                        })
                    elif 'chameleon' in desc_lower:
                        detected_readers.append({
                            'name': f"Chameleon-{port.device}",
                            'type': 'chameleon',
                            'description': f"Chameleon Mini: {port.device}"
                        })
                    elif 'magspoof' in desc_lower:
                        detected_readers.append({
                            'name': f"Magspoof-{port.device}",
                            'type': 'magspoof',
                            'description': f"Magspoof: {port.device}"
                        })
            except Exception as e:
                self.logger.error(f"Error detecting serial devices: {e}")
        
        self.logger.info(f"Detected {len(detected_readers)} readers")
        return detected_readers
    
    def connect_reader(self, reader_info: Dict[str, str]) -> bool:
        """
        Connect to a specific reader.
        
        Args:
            reader_info: Reader information dictionary
            
        Returns:
            True if connection successful
        """
        try:
            reader_type = reader_info['type']
            reader_name = reader_info['name']
            
            # Create appropriate reader instance
            if reader_type == 'pcsc':
                reader = PCSCCardReader(reader_name)
            elif reader_type == 'pn532':
                port = reader_name.split('-')[1] if '-' in reader_name else None
                reader = PN532Reader(port)
            elif reader_type == 'proxmark3':
                port = reader_name.split('-')[1] if '-' in reader_name else None
                reader = ProxmarkReader(port)
            elif reader_type == 'chameleon':
                port = reader_name.split('-')[1] if '-' in reader_name else None
                reader = ChameleonReader(port)
            elif reader_type == 'magspoof':
                port = reader_name.split('-')[1] if '-' in reader_name else None
                reader = MagspoofReader(port)
            else:
                self.logger.error(f"Unknown reader type: {reader_type}")
                return False
            
            # Set up callbacks
            reader.set_callbacks(
                card_inserted=self._on_card_inserted,
                card_removed=self._on_card_removed,
                reader_connected=self._on_reader_connected,
                reader_disconnected=self._on_reader_disconnected
            )
            
            # Connect to reader
            if reader.connect():
                self.readers[reader_name] = reader
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error connecting to reader {reader_info['name']}: {e}")
            return False
    
    def disconnect_reader(self, reader_name: str):
        """Disconnect a specific reader."""
        try:
            if reader_name in self.readers:
                self.readers[reader_name].disconnect()
                del self.readers[reader_name]
                self.logger.info(f"Disconnected reader: {reader_name}")
        except Exception as e:
            self.logger.error(f"Error disconnecting reader {reader_name}: {e}")
    
    def start_monitoring(self):
        """Start reader and card monitoring."""
        if not self.monitor_thread or not self.monitor_thread.isRunning():
            self.monitor_thread = ReaderMonitorThread(self)
            
            # Connect signals
            self.monitor_thread.reader_connected.connect(self.reader_connected)
            self.monitor_thread.reader_disconnected.connect(self.reader_disconnected)
            self.monitor_thread.card_inserted.connect(self.card_inserted)
            self.monitor_thread.card_removed.connect(self.card_removed)
            
            self.monitor_thread.start()
            self.logger.info("Started reader monitoring")
    
    def stop_monitoring(self):
        """Stop reader and card monitoring."""
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
            self.monitor_thread = None
            self.logger.info("Stopped reader monitoring")
    
    def stop_all_readers(self):
        """Disconnect all readers and stop monitoring."""
        try:
            # Stop monitoring first
            self.stop_monitoring()
            
            # Disconnect all readers
            reader_names = list(self.readers.keys())
            for reader_name in reader_names:
                self.disconnect_reader(reader_name)
            
            self.logger.info("Stopped all readers")
            
        except Exception as e:
            self.logger.error(f"Error stopping readers: {e}")
    
    def get_connected_readers(self) -> List[str]:
        """Get list of connected reader names."""
        return list(self.readers.keys())
    
    def get_reader(self, reader_name: str) -> Optional[BaseCardReader]:
        """Get a specific reader instance."""
        return self.readers.get(reader_name)
    
    def transmit_to_reader(self, reader_name: str, apdu: bytes) -> tuple:
        """
        Transmit APDU to a specific reader.
        
        Args:
            reader_name: Name of the reader
            apdu: APDU bytes to transmit
            
        Returns:
            Tuple of (response_data, sw1, sw2)
        """
        if reader_name not in self.readers:
            raise CardReaderError(f"Reader {reader_name} not connected")
        
        return self.readers[reader_name].transmit(apdu)
    
    def _on_card_inserted(self, reader_name: str, atr: bytes):
        """Handle card insertion event."""
        self.logger.info(f"Card inserted in {reader_name}")
        self.card_inserted.emit(reader_name, atr)
    
    def _on_card_removed(self, reader_name: str):
        """Handle card removal event."""
        self.logger.info(f"Card removed from {reader_name}")
        self.card_removed.emit(reader_name)
    
    def _on_reader_connected(self, reader_name: str):
        """Handle reader connection event."""
        self.logger.info(f"Reader connected: {reader_name}")
        self.reader_connected.emit(reader_name)
    
    def _on_reader_disconnected(self, reader_name: str):
        """Handle reader disconnection event."""
        self.logger.info(f"Reader disconnected: {reader_name}")
        self.reader_disconnected.emit(reader_name)

def detect_readers() -> List[Dict[str, str]]:
    """
    Standalone function to detect available readers.
    
    Returns:
        List of reader information dictionaries
    """
    manager = ReaderManager()
    return manager.detect_readers()

def validate_reader_response(response: bytes, expected_length: int = None) -> bool:
    """
    Validate a reader response.
    
    Args:
        response: Response bytes
        expected_length: Expected response length
        
    Returns:
        True if response is valid
    """
    if not response:
        return False
    
    if expected_length and len(response) != expected_length:
        return False
    
    return True
