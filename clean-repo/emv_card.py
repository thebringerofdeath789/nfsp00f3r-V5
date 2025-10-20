#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: emv_card.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: EMV card data structure and methods

Classes:
- EMVCard: Main EMV card data container with parsing and export capabilities
- EMVApplication: Individual application data within a card
- EMVRecord: SFI record data structure

Functions:
- parse_track_data(): Parse magnetic stripe track data
- validate_pan(): Validate Primary Account Number using Luhn algorithm
- decode_service_code(): Decode magnetic stripe service code

This module represents an EMV card with all its data including applications,
records, TLV data, transaction logs, and cryptographic material. Provides
methods for parsing APDU responses and exporting/importing card profiles.

Based on code from:
- danmichaelo/emv (TLV parsing and field extraction)
- dimalinux/EMV-Tools (card data structure)
- LucaBongiorni/EMV-NFC-Paycard-Reader (track data parsing)
- Yagoor/EMV (application browsing)
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict

from tlv import TLVParser
from tag_dictionary import TagDictionary

@dataclass
class EMVRecord:
    """
    Represents a single SFI record from an EMV application.
    Contains the raw data and parsed TLV structure.
    """
    sfi: int
    record_number: int
    raw_data: bytes
    tlv_data: Dict[str, Any]
    parsed_data: Dict[str, str]
    
    def __post_init__(self):
        """Parse TLV data after initialization."""
        if not self.tlv_data and self.raw_data:
            parser = TLVParser()
            self.tlv_data = parser.parse(self.raw_data)
            self.parsed_data = parser.get_parsed_data()

@dataclass
class EMVApplication:
    """
    Represents an EMV application (AID) with its associated data.
    Contains PDOL, CDOL, records, and cryptographic information.
    """
    aid: str
    application_label: str = ""
    preferred_name: str = ""
    priority_indicator: int = 0
    pdol: bytes = b""
    cdol1: bytes = b""
    cdol2: bytes = b""
    aip: bytes = b""  # Application Interchange Profile
    afl: bytes = b""  # Application File Locator
    records: Dict[int, List[EMVRecord]] = None
    cryptograms: List[Dict[str, Any]] = None
    issuer_scripts: List[Dict[str, Any]] = None
    sda_data: Dict[str, Any] = None  # Static Data Authentication
    dda_data: Dict[str, Any] = None  # Dynamic Data Authentication
    cda_data: Dict[str, Any] = None  # Combined Data Authentication
    
    def __post_init__(self):
        """Initialize collections after creation."""
        if self.records is None:
            self.records = {}
        if self.cryptograms is None:
            self.cryptograms = []
        if self.issuer_scripts is None:
            self.issuer_scripts = []
        if self.sda_data is None:
            self.sda_data = {}
        if self.dda_data is None:
            self.dda_data = {}
        if self.cda_data is None:
            self.cda_data = {}

class EMVCard:
    def decode_emv_certificate(self, cert_bytes: bytes) -> dict[str, object]:
        """Decode EMV-format public key certificate (Issuer/ICC/DA). Returns dict with field breakdown (per EMV Book 2)."""
        # See EMV Book 2 Annex A1 for structure
        result = {}
        if not cert_bytes or len(cert_bytes) < 42:
            result['error'] = 'Certificate too short'
            return result
        try:
            idx = 0
            result['header'] = cert_bytes[idx]
            idx += 1
            result['format'] = cert_bytes[idx]
            idx += 1
            result['pan'] = cert_bytes[idx:idx+10].hex().upper()
            idx += 10
            result['expiration_date'] = cert_bytes[idx:idx+2].hex().upper()
            idx += 2
            result['serial_number'] = cert_bytes[idx:idx+3].hex().upper()
            idx += 3
            result['public_key_algorithm'] = cert_bytes[idx]
            idx += 1
            # Public key length and exponent length
            result['public_key_length'] = cert_bytes[idx]
            idx += 1
            result['exponent_length'] = cert_bytes[idx]
            idx += 1
            # Public key (variable length)
            pk_len = result['public_key_length']
            result['public_key'] = cert_bytes[idx:idx+pk_len].hex().upper()
            idx += pk_len
            # Remainder (if any)
            result['remainder'] = cert_bytes[idx:idx+20].hex().upper()
            idx += 20
            # Hash
            result['hash'] = cert_bytes[idx:idx+20].hex().upper()
            idx += 20
            # Trailer
            result['trailer'] = cert_bytes[-1]
        except Exception as e:
            result['error'] = f'Parse error: {e}'
        return result

    def decode_emv_signature(self, sig_bytes: bytes) -> dict[str, object]:
        """Decode EMV-format signature field (SDA/DDA/CDA). Returns dict with field breakdown (per EMV Book 2)."""
        # See EMV Book 2 Annex A2 for structure
        result = {}
        if not sig_bytes or len(sig_bytes) < 42:
            result['error'] = 'Signature too short'
            return result
        try:
            idx = 0
            result['header'] = sig_bytes[idx]
            idx += 1
            result['format'] = sig_bytes[idx]
            idx += 1
            # Signed data (variable, depends on type)
            signed_data_len = len(sig_bytes) - 22
            result['signed_data'] = sig_bytes[idx:idx+signed_data_len].hex().upper()
            idx += signed_data_len
            # Hash
            result['hash'] = sig_bytes[idx:idx+20].hex().upper()
            idx += 20
            # Trailer
            result['trailer'] = sig_bytes[-1]
        except Exception as e:
            result['error'] = f'Parse error: {e}'
        return result

    def analyze_pin_block(self, pin_block: bytes, pan: str) -> dict[str, object]:
        """Analyze PIN block format and structure for research purposes."""
        result = {}
        if not pin_block or len(pin_block) != 8:
            result['error'] = 'PIN block must be 8 bytes'
            return result
        
        pin_block_hex = pin_block.hex().upper()
        result['raw_hex'] = pin_block_hex
        
        # Detect PIN block format
        first_nibble = pin_block[0] >> 4
        if first_nibble == 0:
            result['format'] = 'ISO-0 (Format 0)'
            # PIN length in lower nibble of first byte
            pin_length = pin_block[0] & 0x0F
            result['pin_length'] = pin_length
            
            # Extract PIN digits - PIN block format: 0L + PIN digits + padding
            # Example: 041234FFFFFFFFFF = Format 0, Length 4, PIN 1234, Padding FFF...
            if pin_length > 0 and pin_length <= 12:
                # PIN digits start from the second nibble of first byte
                pin_digits = ""
                
                # First PIN digit is in the lower nibble of byte 1
                remaining_length = pin_length
                byte_index = 1
                
                while remaining_length > 0 and byte_index < len(pin_block):
                    if remaining_length >= 2:
                        # Full byte - two digits
                        pin_digits += f"{pin_block[byte_index]:02X}"
                        remaining_length -= 2
                    else:
                        # Partial byte - one digit (upper nibble)
                        pin_digits += f"{pin_block[byte_index] >> 4:X}"
                        remaining_length -= 1
                    byte_index += 1
                
                result['pin_digits'] = pin_digits[:pin_length]
                
                # Calculate padding start position
                padding_start_byte = 1 + (pin_length + 1) // 2
                if padding_start_byte < len(pin_block):
                    padding_bytes = pin_block[padding_start_byte:]
                    result['padding'] = ''.join(f"{b:02X}" for b in padding_bytes)
                    result['padding_valid'] = all(b == 0xFF for b in padding_bytes)
        
        elif first_nibble == 1:
            result['format'] = 'ISO-1 (Format 1)'
            # PAN-based format
            if pan and len(pan) >= 12:
                # Extract last 12 digits of PAN (excluding check digit)
                pan_part = pan[-13:-1]  # Last 12 digits
                result['pan_part'] = pan_part
                
        elif first_nibble == 2:
            result['format'] = 'ISO-2 (Format 2)'
            result['note'] = 'Intermediate format'
            
        elif first_nibble == 3:
            result['format'] = 'ISO-3 (Format 3)'
            result['note'] = 'Intermediate format'
            
        else:
            result['format'] = f'Unknown format (first nibble: {first_nibble})'
        
        return result

    def get_pin_block_statistics(self, cards_data: list) -> dict[str, object]:
        """Analyze PIN block patterns across multiple cards for research."""
        stats = {
            'total_cards': len(cards_data),
            'format_distribution': {},
            'pin_length_distribution': {},
            'padding_patterns': {},
            'first_byte_distribution': {},
            'common_patterns': []
        }
        
        pin_blocks = []
        for card in cards_data:
            if hasattr(card, 'pin_block') and card.pin_block:
                analysis = self.analyze_pin_block(card.pin_block, card.pan)
                pin_blocks.append(analysis)
                
                # Count formats
                fmt = analysis.get('format', 'Unknown')
                stats['format_distribution'][fmt] = stats['format_distribution'].get(fmt, 0) + 1
                
                # Count PIN lengths
                pin_len = analysis.get('pin_length')
                if pin_len:
                    stats['pin_length_distribution'][str(pin_len)] = stats['pin_length_distribution'].get(str(pin_len), 0) + 1
                
                # Count first bytes
                raw_hex = analysis.get('raw_hex', '')
                if raw_hex:
                    first_byte = raw_hex[:2]
                    stats['first_byte_distribution'][first_byte] = stats['first_byte_distribution'].get(first_byte, 0) + 1
        
        stats['analyzed_blocks'] = len(pin_blocks)
        return stats
    def parse_oda_structures(self, tlv_data: Dict[str, Any], app: EMVApplication):
        """Parse and extract ODA (SDA, DDA, CDA) structures from TLV data (adapted from atzedevs/emv-crypto, dimalinux/EMV-Tools)."""
        # SDA: Static Data Authentication
        if '93' in tlv_data:  # Signed Static Application Data
            app.sda_data['signed_static_data'] = tlv_data['93']
        if '9F46' in tlv_data:  # ICC Public Key Certificate
            app.sda_data['icc_public_key_certificate'] = tlv_data['9F46']
        if '9F47' in tlv_data:  # ICC Public Key Exponent
            app.sda_data['icc_public_key_exponent'] = tlv_data['9F47']
        if '9F48' in tlv_data:  # ICC Public Key Remainder
            app.sda_data['icc_public_key_remainder'] = tlv_data['9F48']
        if '90' in tlv_data:  # Issuer Public Key Certificate
            app.sda_data['issuer_public_key_certificate'] = tlv_data['90']
        if '92' in tlv_data:  # Issuer Public Key Remainder
            app.sda_data['issuer_public_key_remainder'] = tlv_data['92']
        if '9F32' in tlv_data:  # Issuer Public Key Exponent
            app.sda_data['issuer_public_key_exponent'] = tlv_data['9F32']
        # DDA: Dynamic Data Authentication
        if '9F4B' in tlv_data:  # Signed Dynamic Application Data
            app.dda_data['signed_dynamic_data'] = tlv_data['9F4B']
        if '9F49' in tlv_data:  # DDA Public Key Certificate
            app.dda_data['dda_public_key_certificate'] = tlv_data['9F49']
        if '9F4A' in tlv_data:  # DDA Public Key Exponent
            app.dda_data['dda_public_key_exponent'] = tlv_data['9F4A']
        if '9F2D' in tlv_data:  # DDA Public Key Remainder
            app.dda_data['dda_public_key_remainder'] = tlv_data['9F2D']
        # CDA: Combined Data Authentication (CDA signature is in GENERATE AC response, tag 9F4B)
        if '9F4B' in tlv_data:
            app.cda_data['cda_signature'] = tlv_data['9F4B']
    """
    Complete EMV card representation with all data and functionality.
    Handles parsing of APDU responses, TLV data extraction, and provides
    methods for transaction processing and data export/import.
    """
    
    def __init__(self):
        """Initialize EMV card with empty data structures."""
        self.logger = logging.getLogger(__name__)
        
        # Card identification
        self.card_id: Optional[str] = None
        self.reader_name: str = "Unknown"
        self.insertion_time: Optional[datetime] = None
        self.atr: Optional[str] = None  # Answer To Reset
        
        # Cardholder data
        self.pan: Optional[str] = None
        self.pan_sequence_number: Optional[str] = None
        self.cardholder_name: Optional[str] = None
        self.expiry_date: Optional[str] = None  # YYMMDD format
        self.effective_date: Optional[str] = None
        self.service_code: Optional[str] = None
        
        # Track data
        self.track1_data: Optional[str] = None
        self.track2_data: Optional[str] = None
        self.track3_data: Optional[str] = None
        self.track2_equivalent: Optional[bytes] = None
        
        # Discretionary data
        self.discretionary_data: Optional[str] = None
        self.cvv: Optional[str] = None
        self.cvv2: Optional[str] = None
        self.cvc3: Optional[str] = None
        self.pin: Optional[str] = None
        self.pin_try_counter: int = 3
        
        # Applications and data
        self.applications: Dict[str, EMVApplication] = {}
        self.current_application: Optional[str] = None
        
        # Complete TLV data from all interactions
        self.tlv_data: Dict[str, Any] = {}
        
        # APDU logs
        self.apdu_log: List[Dict[str, Any]] = []
        
        # Transaction data
        self.transaction_counter: int = 0
        self.last_online_atc: int = 0
        self.transaction_history: List[Dict[str, Any]] = []
        
        # Cryptographic data
        self.issuer_public_key: Optional[bytes] = None
        self.icc_public_key: Optional[bytes] = None
        self.issuer_certificates: List[bytes] = []
        self.icc_certificates: List[bytes] = []
        self.derived_keys: Dict[str, bytes] = {}
        
        # Processing options
        self.processing_options: Dict[str, Any] = {}
        
        # Card capabilities
        self.card_capabilities: Dict[str, bool] = {
            'contact': False,
            'contactless': False,
            'magstripe': False,
            'chip_auth': False,
            'pin_online': False,
            'pin_offline': False
        }
        
        # Initialize parsers
        self.tlv_parser = TLVParser()
        self.tag_dict = TagDictionary()
        
        # Card type - will be determined during reading
        self.card_type: str = "Unknown"
        self.uid: Optional[str] = None  # For contactless cards
        
        self.logger.debug("EMV card initialized")
    
    def _determine_card_type(self) -> str:
        """Determine card type based on available data."""
        # Check if this is an EMV card based on applications or ATR patterns
        if self.applications:
            # Has EMV applications - this is a payment card
            if self.uid and len(self.uid) == 8:
                return "EMV Contactless Card"
            else:
                return "EMV Contact Card"
        elif self.uid and len(self.uid) == 8:
            # Has UID but no EMV apps - could be EMV with protected data
            if self.atr and "534C4A" in self.atr.upper():  # "SLJ" identifier
                return "EMV Contactless Card"  # EMV card with Java Card OS
            else:
                return "Contactless Smart Card"
        elif self.track2_data or self.track1_data:
            return "Payment Card (Magnetic Stripe)"
        elif self.atr and "534C4A" in self.atr.upper():
            return "Smart Card (Java Card)"
        elif self.atr:
            return "Contact Smart Card"
        else:
            return "Unknown Card"
    
    def parse_response(self, command: bytes, response: bytes, sw1: int, sw2: int) -> Dict[str, Any]:
        """
        Parse an APDU response and extract relevant data.
        
        Args:
            command: APDU command that was sent
            response: Response data received
            sw1: Status word 1
            sw2: Status word 2
            
        Returns:
            Dictionary containing parsed data
        """
        try:
            # Log the APDU exchange
            apdu_entry = {
                'timestamp': datetime.now(),
                'command': command.hex().upper(),
                'response': response.hex().upper() if response else "",
                'sw1': sw1,
                'sw2': sw2,
                'status': 'Success' if sw1 == 0x90 and sw2 == 0x00 else f'Error {sw1:02X}{sw2:02X}',
                'parsed_data': {}
            }
            
            # Parse response if successful
            parsed_data = {}
            if sw1 == 0x90 and sw2 == 0x00 and response:
                parsed_data = self._parse_response_data(command, response)
                apdu_entry['parsed_data'] = parsed_data
            
            self.apdu_log.append(apdu_entry)
            
            # Search for track2 equivalent data in all responses
            self._search_track2_data(response)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing APDU response: {e}")
            return {}
    
    def _parse_response_data(self, command: bytes, response: bytes) -> Dict[str, Any]:
        """
        Parse response data based on command type and extract relevant information.
        
        Args:
            command: APDU command
            response: Response data
            
        Returns:
            Parsed data dictionary
        """
        parsed_data = {}
        
        try:
            # Determine command type
            if len(command) >= 4:
                cla, ins, p1, p2 = command[:4]
                
                # SELECT command (00 A4)
                if ins == 0xA4:
                    parsed_data = self._parse_select_response(response)
                
                # GET PROCESSING OPTIONS (80 A8)
                elif ins == 0xA8:
                    parsed_data = self._parse_gpo_response(response)
                
                # READ RECORD (00 B2)
                elif ins == 0xB2:
                    sfi = (p2 >> 3) & 0x1F
                    record_num = p1
                    parsed_data = self._parse_read_record_response(response, sfi, record_num)
                
                # GENERATE AC (80 AE)
                elif ins == 0xAE:
                    parsed_data = self._parse_generate_ac_response(response, p1)
                
                # VERIFY PIN (00 20)
                elif ins == 0x20:
                    parsed_data = self._parse_verify_pin_response(p2)
                
                # GET DATA (80 CA)
                elif ins == 0xCA:
                    tag = (p1 << 8) | p2
                    parsed_data = self._parse_get_data_response(response, tag)
            
            # Always parse TLV data if present
            if response:
                tlv_data = self.tlv_parser.parse(response)
                parsed_data['tlv'] = tlv_data
                
                # Merge into main TLV data
                self._merge_tlv_data(tlv_data)
                
                # Extract specific fields
                self._extract_fields_from_tlv(tlv_data)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing response data: {e}")
            return {}
    
    def _parse_select_response(self, response: bytes) -> Dict[str, Any]:
        """Parse SELECT command response (FCI template)."""
        parsed_data = {'command_type': 'SELECT'}
        
        try:
            tlv_data = self.tlv_parser.parse(response)
            
            # Extract FCI data
            if '6F' in tlv_data:  # FCI Template
                fci = tlv_data['6F']
                
                if 'A5' in fci:  # FCI Proprietary Template
                    proprietary = fci['A5']
                    
                    # Application label
                    if '50' in proprietary:
                        parsed_data['application_label'] = proprietary['50'].decode('utf-8', errors='ignore')
                    
                    # Preferred name
                    if '9F12' in proprietary:
                        parsed_data['preferred_name'] = proprietary['9F12'].decode('utf-8', errors='ignore')
                    
                    # PDOL
                    if '9F38' in proprietary:
                        parsed_data['pdol'] = proprietary['9F38']
                    
                    # Application priority
                    if '87' in proprietary:
                        parsed_data['priority'] = int.from_bytes(proprietary['87'], 'big')
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing SELECT response: {e}")
            return parsed_data
    
    def _parse_gpo_response(self, response: bytes) -> Dict[str, Any]:
        """Parse GET PROCESSING OPTIONS response (adapted from danmichaelo/emv, dimalinux/EMV-Tools)."""
        parsed_data: Dict[str, Any] = {'command_type': 'GPO'}
        try:
            # Format 1: tag 80 (AIP + AFL)
            if response and response[0] == 0x80:
                length = response[1]
                data = response[2:2+length]
                if len(data) >= 2:
                    parsed_data['aip'] = bytes(data[:2])
                    parsed_data['afl'] = bytes(data[2:])
                    parsed_data['afl_entries'] = self._parse_afl(bytes(data[2:]))
            # Format 2: tag 77 (TLV)
            elif response and response[0] == 0x77:
                tlv_data = self.tlv_parser.parse(response)
                if '82' in tlv_data:
                    parsed_data['aip'] = tlv_data['82']
                if '94' in tlv_data:
                    parsed_data['afl'] = tlv_data['94']
                    parsed_data['afl_entries'] = self._parse_afl(tlv_data['94'])
            # Store in current application
            if self.current_application and self.current_application in self.applications:
                app = self.applications[self.current_application]
                if 'aip' in parsed_data:
                    app.aip = parsed_data['aip']
                if 'afl' in parsed_data:
                    app.afl = parsed_data['afl']
            self.processing_options.update(parsed_data)
            return parsed_data
        except Exception as e:
            self.logger.error(f"Error parsing GPO response: {e}")
            return parsed_data

    def _parse_afl(self, afl_bytes: bytes) -> list[dict[str, int]]:
        """Parse AFL bytes into list of dicts (SFI, first rec, last rec, num recs)."""
        entries: list[dict[str, int]] = []
        if not afl_bytes or len(afl_bytes) % 4 != 0:
            return entries
        for i in range(0, len(afl_bytes), 4):
            sfi = (afl_bytes[i] >> 3) & 0x1F
            first_rec = afl_bytes[i+1]
            last_rec = afl_bytes[i+2]
            num_rec = afl_bytes[i+3]
            entries.append({'sfi': sfi, 'first_record': first_rec, 'last_record': last_rec, 'num_records': num_rec})
        return entries
    
    def _parse_read_record_response(self, response: bytes, sfi: int, record_num: int) -> Dict[str, Any]:
        """Parse READ RECORD response."""
        parsed_data = {
            'command_type': 'READ_RECORD',
            'sfi': sfi,
            'record_number': record_num
        }
        
        try:
            # Parse TLV data in record
            tlv_data = self.tlv_parser.parse(response)
            
            # Create record object
            record = EMVRecord(
                sfi=sfi,
                record_number=record_num,
                raw_data=response,
                tlv_data=tlv_data,
                parsed_data={}
            )
            
            # Store in current application
            if self.current_application and self.current_application in self.applications:
                app = self.applications[self.current_application]
                if sfi not in app.records:
                    app.records[sfi] = []
                app.records[sfi].append(record)
            
            parsed_data['record_data'] = tlv_data
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing READ RECORD response: {e}")
            return parsed_data
    
    def _parse_generate_ac_response(self, response: bytes, p1: int) -> Dict[str, Any]:
        """Parse GENERATE AC response."""
        parsed_data = {
            'command_type': 'GENERATE_AC',
            'ac_type': (p1 >> 6) & 0x03  # AC type from P1
        }
        
        try:
            tlv_data = self.tlv_parser.parse(response)
            
            # Extract cryptogram
            if '9F26' in tlv_data:
                parsed_data['application_cryptogram'] = tlv_data['9F26']
            
            # Extract ATC
            if '9F36' in tlv_data:
                parsed_data['atc'] = tlv_data['9F36']
            
            # Extract CID
            if '9F27' in tlv_data:
                parsed_data['cid'] = tlv_data['9F27']
            
            # Store cryptogram in current application
            if self.current_application and self.current_application in self.applications:
                app = self.applications[self.current_application]
                cryptogram_data = {
                    'timestamp': datetime.now(),
                    'type': parsed_data['ac_type'],
                    'cryptogram': parsed_data.get('application_cryptogram'),
                    'atc': parsed_data.get('atc'),
                    'cid': parsed_data.get('cid'),
                    'full_response': tlv_data
                }
                app.cryptograms.append(cryptogram_data)
            
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Error parsing GENERATE AC response: {e}")
            return parsed_data
    
    def _parse_verify_pin_response(self, p2: int) -> Dict[str, Any]:
        """Parse VERIFY PIN response."""
        return {
            'command_type': 'VERIFY_PIN',
            'reference': p2,
            'verification_method': 'online' if p2 == 0x00 else 'offline'
        }
    
    def _parse_get_data_response(self, response: bytes, tag: int) -> Dict[str, Any]:
        """Parse GET DATA response."""
        parsed_data = {
            'command_type': 'GET_DATA',
            'tag': f'{tag:04X}',
            'data': response
        }
        
        # Parse specific data objects
        tag_hex = f'{tag:04X}'
        
        if tag_hex == '9F13':  # Last Online ATC
            if len(response) >= 2:
                parsed_data['last_online_atc'] = int.from_bytes(response, 'big')
                self.last_online_atc = parsed_data['last_online_atc']
        
        elif tag_hex == '9F17':  # PIN Try Counter
            if len(response) >= 1:
                parsed_data['pin_try_counter'] = response[0]
                self.pin_try_counter = parsed_data['pin_try_counter']
        
        elif tag_hex == '9F36':  # Application Transaction Counter
            if len(response) >= 2:
                parsed_data['atc'] = int.from_bytes(response, 'big')
                self.transaction_counter = parsed_data['atc']
        
        return parsed_data
    
    def _search_track2_data(self, response: bytes):
        """Search for track2 equivalent data in APDU response."""
        try:
            if not response:
                return
            
            # Look for track2 equivalent tag (57)
            tlv_data = self.tlv_parser.parse(response)
            
            if '57' in tlv_data:
                track2_data = tlv_data['57']
                self.track2_equivalent = track2_data
                
                # Parse track2 data
                track2_str = track2_data.hex().upper()
                self._parse_track2_string(track2_str)
                
                self.logger.info("Found track2 equivalent data")
        
        except Exception as e:
            self.logger.debug(f"No track2 data found in response: {e}")
    
    def _parse_track2_string(self, track2_str: str):
        """Parse track2 data string and extract PAN, expiry, service code, discretionary, and derive PIN and 101 SVC track2 with simulated CVV."""
        try:
            # Remove padding (F)
            track2_str = track2_str.rstrip('F')
            # Find separator (D)
            if 'D' not in track2_str:
                return
            parts = track2_str.split('D')
            if len(parts) < 2:
                return
            # Extract PAN
            pan = parts[0]
            if self._validate_pan(pan):
                self.pan = pan
            # Extract expiry and service code
            exp, svc, disc = '', '', ''
            if len(parts[1]) >= 4:
                exp = parts[1][:4]
                self.expiry_date = exp
                if len(parts[1]) >= 7:
                    svc = parts[1][4:7]
                    self.service_code = svc
                    if len(parts[1]) > 7:
                        disc = parts[1][7:]
                        self.discretionary_data = disc
            # Derive PIN (demo: last 4 of PAN or fallback)
            derived_pin = pan[-4:] if pan and len(pan) >= 4 else '1234'
            self.derived_pin = derived_pin
            # Generate Track2 with 101 SVC and simulated CVV/disc
            if pan and exp and disc:
                import hashlib
                new_svc = '101'
                cvv_input = (pan + exp + new_svc).encode()
                cvv_hash = hashlib.sha1(cvv_input).hexdigest()
                cvv_digits = ''.join([c for c in cvv_hash if c.isdigit()])
                new_cvv = (cvv_digits + '000')[:3]
                new_disc = new_cvv + disc[3:] if len(disc) >= 3 else disc
                self.track2_101 = f"{pan}D{exp}{new_svc}{new_disc}"
            pan_str = self.pan if isinstance(self.pan, str) and self.pan else ''
            self.logger.info(f"Parsed track2 data - PAN: {self._mask_pan(pan_str)} PIN: {derived_pin} 101SVC: {getattr(self, 'track2_101', '')}")
        except Exception as e:
            self.logger.error(f"Error parsing track2 string: {e}")
    
    def _validate_pan(self, pan: str) -> bool:
        """Validate PAN using Luhn algorithm."""
        try:
            if not pan or not pan.isdigit() or len(pan) < 13 or len(pan) > 19:
                return False
            
            # Luhn algorithm
            total = 0
            reverse_digits = pan[::-1]
            
            for i, digit in enumerate(reverse_digits):
                n = int(digit)
                if i % 2 == 1:
                    n *= 2
                    if n > 9:
                        n = n // 10 + n % 10
                total += n
            
            return total % 10 == 0
            
        except Exception:
            return False
    
    def _mask_pan(self, pan: str) -> str:
        """Mask PAN for logging purposes."""
        if not pan or len(pan) < 8:
            return "****"
        return f"{pan[:4]}{'*' * (len(pan) - 8)}{pan[-4:]}"
    
    def _extract_fields_from_tlv(self, tlv_data):
        """Extract all relevant card fields and CDOL1/CDOL2 from TLV data.
        Handles both list format (from TLV parser) and dict format (legacy).
        """
        try:
            # Convert list format to dict format for processing
            if isinstance(tlv_data, list):
                tlv_dict = {}
                for item in tlv_data:
                    if isinstance(item, dict) and 'tag' in item and 'value' in item:
                        tag = item['tag'].upper()
                        value = item['value']
                        # Convert hex string to bytes if needed
                        if isinstance(value, str):
                            try:
                                tlv_dict[tag] = bytes.fromhex(value)
                            except ValueError:
                                # Keep as string if not valid hex
                                tlv_dict[tag] = value.encode('utf-8') if isinstance(value, str) else value
                        else:
                            tlv_dict[tag] = value
                tlv_data = tlv_dict
            
            # Initialize extracted fields
            extracted_fields = {}
            
            # Cardholder name
            if '5F20' in tlv_data:
                name_data = tlv_data['5F20']
                if isinstance(name_data, bytes):
                    extracted_fields['cardholder_name'] = name_data.decode('utf-8', errors='ignore').strip()
                else:
                    extracted_fields['cardholder_name'] = str(name_data)
                    
            # PAN
            if '5A' in tlv_data:
                pan_data = tlv_data['5A']
                if isinstance(pan_data, bytes):
                    pan_str = pan_data.hex().upper().rstrip('F')
                elif isinstance(pan_data, str):
                    pan_str = pan_data.rstrip('F')
                else:
                    pan_str = str(pan_data)
                    
                if self._validate_pan(pan_str):
                    extracted_fields['pan'] = pan_str
                    self.pan = pan_str
                    
            # Application expiry date
            if '5F24' in tlv_data:
                expiry_data = tlv_data['5F24']
                if isinstance(expiry_data, bytes):
                    extracted_fields['expiry_date'] = expiry_data.hex().upper()
                else:
                    extracted_fields['expiry_date'] = str(expiry_data)
                    
            # *** CDOL1 and CDOL2 EXTRACTION - CRITICAL FOR REAL CARDS ***
            if '8C' in tlv_data:  # CDOL1
                cdol1_data = tlv_data['8C']
                if isinstance(cdol1_data, bytes):
                    cdol1_hex = cdol1_data.hex().upper()
                else:
                    cdol1_hex = str(cdol1_data)
                    
                extracted_fields['cdol1'] = cdol1_hex
                self.logger.info(f"✅ EXTRACTED REAL CDOL1: {cdol1_hex}")
                
                # Store in current application if available
                if self.current_application and self.current_application in self.applications:
                    self.applications[self.current_application].cdol1 = cdol1_data
                    
            if '8D' in tlv_data:  # CDOL2
                cdol2_data = tlv_data['8D']
                if isinstance(cdol2_data, bytes):
                    cdol2_hex = cdol2_data.hex().upper()
                else:
                    cdol2_hex = str(cdol2_data)
                    
                extracted_fields['cdol2'] = cdol2_hex
                self.logger.info(f"✅ EXTRACTED REAL CDOL2: {cdol2_hex}")
                
                # Store in current application if available
                if self.current_application and self.current_application in self.applications:
                    self.applications[self.current_application].cdol2 = cdol2_data
                    
            # Application Interchange Profile
            if '82' in tlv_data:
                aip_data = tlv_data['82']
                if isinstance(aip_data, bytes):
                    extracted_fields['aip'] = aip_data.hex().upper()
                else:
                    extracted_fields['aip'] = str(aip_data)
                    
            # Application File Locator
            if '94' in tlv_data:
                afl_data = tlv_data['94']
                if isinstance(afl_data, bytes):
                    extracted_fields['afl'] = afl_data.hex().upper()
                else:
                    extracted_fields['afl'] = str(afl_data)
                    
            # Application label
            if '50' in tlv_data:
                label_data = tlv_data['50']
                if isinstance(label_data, bytes):
                    extracted_fields['application_label'] = label_data.decode('utf-8', errors='ignore').strip()
                else:
                    extracted_fields['application_label'] = str(label_data)
                    
            # Extract discretionary/optional tags
            discretionary_tags = ['9F10', '9F26', '9F27', '9F36', '9F37', '9F1A', '9F35', '9F33', '9F34', '9F21', '9F02', '9F03']
            for tag in discretionary_tags:
                if tag in tlv_data:
                    tag_data = tlv_data[tag]
                    if isinstance(tag_data, bytes):
                        extracted_fields[f'tag_{tag}'] = tag_data.hex().upper()
                    else:
                        extracted_fields[f'tag_{tag}'] = str(tag_data)
                        
            return extracted_fields
            
        except Exception as e:
            self.logger.error(f"Error extracting fields from TLV: {e}")
            return {}
    
    def _merge_tlv_data(self, new_tlv_data: Dict[str, Any]):
        """Merge new TLV data into the main TLV collection."""
        try:
            def merge_dict(target: Dict[str, Any], source: Dict[str, Any]):
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        merge_dict(target[key], value)
                    else:
                        target[key] = value
            
            merge_dict(self.tlv_data, new_tlv_data)
            
        except Exception as e:
            self.logger.error(f"Error merging TLV data: {e}")
    
    def add_application(self, aid: str, app_data: Dict[str, Any] = None) -> EMVApplication:
        """
        Add an application to the card.
        
        Args:
            aid: Application Identifier
            app_data: Optional application data
            
        Returns:
            Created EMV application
        """
        try:
            if aid not in self.applications:
                self.applications[aid] = EMVApplication(aid=aid)
            
            app = self.applications[aid]
            
            # Update application data if provided
            if app_data:
                if 'application_label' in app_data:
                    app.application_label = app_data['application_label']
                if 'preferred_name' in app_data:
                    app.preferred_name = app_data['preferred_name']
                if 'priority' in app_data:
                    app.priority_indicator = app_data['priority']
                if 'pdol' in app_data:
                    app.pdol = app_data['pdol']
            
            self.logger.info(f"Added application {aid}")
            return app
            
        except Exception as e:
            self.logger.error(f"Error adding application {aid}: {e}")
            return self.applications.get(aid)
    
    def set_current_application(self, aid: str):
        """Set the currently active application."""
        if aid in self.applications:
            self.current_application = aid
            self.logger.debug(f"Set current application to {aid}")
        else:
            self.logger.warning(f"Attempted to set non-existent application {aid}")
    
    def get_applications(self) -> List[Tuple[str, str]]:
        """Get list of applications as (AID, label) tuples."""
        apps = []
        for aid, app in self.applications.items():
            label = app.application_label or app.preferred_name or aid[:16] + "..."
            apps.append((aid, label))
        return apps
    
    def extract_track_data(self) -> Dict[str, str]:
        """Extract and return all track data."""
        tracks = {}
        
        if self.track1_data:
            tracks['track1'] = self.track1_data
        
        if self.track2_data:
            tracks['track2'] = self.track2_data
        elif self.track2_equivalent:
            tracks['track2_equivalent'] = self.track2_equivalent.hex().upper()
        
        if self.track3_data:
            tracks['track3'] = self.track3_data
        
        return tracks
    
    def to_json(self) -> Dict[str, Any]:
        """Export card data to JSON-serializable dictionary."""
        try:
            # Convert applications to dictionaries
            apps_data = {}
            for aid, app in self.applications.items():
                apps_data[aid] = {
                    'aid': app.aid,
                    'application_label': app.application_label,
                    'preferred_name': app.preferred_name,
                    'priority_indicator': app.priority_indicator,
                    'pdol': app.pdol.hex() if app.pdol else "",
                    'cdol1': app.cdol1.hex() if app.cdol1 else "",
                    'cdol2': app.cdol2.hex() if app.cdol2 else "",
                    'aip': app.aip.hex() if app.aip else "",
                    'afl': app.afl.hex() if app.afl else "",
                    'records': {},
                    'cryptograms': app.cryptograms,
                    'issuer_scripts': app.issuer_scripts,
                    'sda_data': app.sda_data,
                    'dda_data': app.dda_data
                }
                
                # Convert records
                for sfi, records in app.records.items():
                    apps_data[aid]['records'][str(sfi)] = []
                    for record in records:
                        record_data = {
                            'sfi': record.sfi,
                            'record_number': record.record_number,
                            'raw_data': record.raw_data.hex(),
                            'tlv_data': self._serialize_tlv_for_json(record.tlv_data),
                            'parsed_data': record.parsed_data
                        }
                        apps_data[aid]['records'][str(sfi)].append(record_data)
            
            # Main card data
            card_data = {
                'card_id': self.card_id,
                'reader_name': self.reader_name,
                'insertion_time': self.insertion_time.isoformat() if self.insertion_time else None,
                'pan': self.pan,
                'pan_sequence_number': self.pan_sequence_number,
                'cardholder_name': self.cardholder_name,
                'expiry_date': self.expiry_date,
                'effective_date': self.effective_date,
                'service_code': self.service_code,
                'track1_data': self.track1_data,
                'track2_data': self.track2_data,
                'track3_data': self.track3_data,
                'track2_equivalent': self.track2_equivalent.hex() if self.track2_equivalent else None,
                'discretionary_data': self.discretionary_data,
                'cvv': self.cvv,
                'cvv2': self.cvv2,
                'cvc3': self.cvc3,
                'pin': self.pin,
                'pin_try_counter': self.pin_try_counter,
                'applications': apps_data,
                'current_application': self.current_application,
                'tlv_data': self._serialize_tlv_for_json(self.tlv_data),
                'apdu_log': self._serialize_apdu_log(),
                'transaction_counter': self.transaction_counter,
                'last_online_atc': self.last_online_atc,
                'transaction_history': self.transaction_history,
                'processing_options': self.processing_options,
                'card_capabilities': self.card_capabilities,
                'derived_keys': {k: v.hex() for k, v in self.derived_keys.items()},
                'export_timestamp': datetime.now().isoformat()
            }
            
            return card_data
            
        except Exception as e:
            self.logger.error(f"Error exporting card to JSON: {e}")
            raise
    
    def from_json(self, card_data: Dict[str, Any]):
        """Import card data from JSON dictionary."""
        try:
            # Basic card data
            self.card_id = card_data.get('card_id')
            self.reader_name = card_data.get('reader_name', 'Unknown')
            
            insertion_time_str = card_data.get('insertion_time')
            if insertion_time_str:
                self.insertion_time = datetime.fromisoformat(insertion_time_str)
            
            self.pan = card_data.get('pan')
            self.pan_sequence_number = card_data.get('pan_sequence_number')
            self.cardholder_name = card_data.get('cardholder_name')
            self.expiry_date = card_data.get('expiry_date')
            self.effective_date = card_data.get('effective_date')
            self.service_code = card_data.get('service_code')
            
            # Track data
            self.track1_data = card_data.get('track1_data')
            self.track2_data = card_data.get('track2_data')
            self.track3_data = card_data.get('track3_data')
            
            track2_equiv = card_data.get('track2_equivalent')
            if track2_equiv:
                self.track2_equivalent = bytes.fromhex(track2_equiv)
            
            self.discretionary_data = card_data.get('discretionary_data')
            self.cvv = card_data.get('cvv')
            self.cvv2 = card_data.get('cvv2')
            self.cvc3 = card_data.get('cvc3')
            self.pin = card_data.get('pin')
            self.pin_try_counter = card_data.get('pin_try_counter', 3)
            
            # Applications
            apps_data = card_data.get('applications', {})
            self.applications = {}
            
            for aid, app_data in apps_data.items():
                app = EMVApplication(aid=aid)
                app.application_label = app_data.get('application_label', '')
                app.preferred_name = app_data.get('preferred_name', '')
                app.priority_indicator = app_data.get('priority_indicator', 0)
                
                # Convert hex strings back to bytes
                if app_data.get('pdol'):
                    app.pdol = bytes.fromhex(app_data['pdol'])
                if app_data.get('cdol1'):
                    app.cdol1 = bytes.fromhex(app_data['cdol1'])
                if app_data.get('cdol2'):
                    app.cdol2 = bytes.fromhex(app_data['cdol2'])
                if app_data.get('aip'):
                    app.aip = bytes.fromhex(app_data['aip'])
                if app_data.get('afl'):
                    app.afl = bytes.fromhex(app_data['afl'])
                
                # Records
                records_data = app_data.get('records', {})
                for sfi_str, sfi_records in records_data.items():
                    sfi = int(sfi_str)
                    app.records[sfi] = []
                    
                    for record_data in sfi_records:
                        record = EMVRecord(
                            sfi=record_data['sfi'],
                            record_number=record_data['record_number'],
                            raw_data=bytes.fromhex(record_data['raw_data']),
                            tlv_data=record_data['tlv_data'],
                            parsed_data=record_data.get('parsed_data', {})
                        )
                        app.records[sfi].append(record)
                
                # Other application data
                app.cryptograms = app_data.get('cryptograms', [])
                app.issuer_scripts = app_data.get('issuer_scripts', [])
                app.sda_data = app_data.get('sda_data', {})
                app.dda_data = app_data.get('dda_data', {})
                
                self.applications[aid] = app
            
            self.current_application = card_data.get('current_application')
            
            # Other data
            self.tlv_data = card_data.get('tlv_data', {})
            self.transaction_counter = card_data.get('transaction_counter', 0)
            self.last_online_atc = card_data.get('last_online_atc', 0)
            self.transaction_history = card_data.get('transaction_history', [])
            self.processing_options = card_data.get('processing_options', {})
            self.card_capabilities = card_data.get('card_capabilities', {})
            
            # Derived keys
            derived_keys_data = card_data.get('derived_keys', {})
            self.derived_keys = {k: bytes.fromhex(v) for k, v in derived_keys_data.items()}
            
            pan_str = self.pan if isinstance(self.pan, str) and self.pan else ''
            self.logger.info(f"Imported card data for {self._mask_pan(pan_str)}")
            
        except Exception as e:
            self.logger.error(f"Error importing card from JSON: {e}")
            raise
    
    def _serialize_tlv_for_json(self, tlv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TLV data to JSON-serializable format."""
        try:
            def convert_value(value):
                if isinstance(value, bytes):
                    return value.hex().upper()
                elif isinstance(value, dict):
                    return {k: convert_value(v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [convert_value(item) for item in value]
                else:
                    return value
            
            return convert_value(tlv_data)
            
        except Exception as e:
            self.logger.error(f"Error serializing TLV data: {e}")
            return {}
    
    def _serialize_apdu_log(self) -> List[Dict[str, Any]]:
        """Serialize APDU log for JSON export."""
        try:
            serialized_log = []
            
            for entry in self.apdu_log:
                serialized_entry = entry.copy()
                
                # Convert datetime to string
                if 'timestamp' in serialized_entry:
                    serialized_entry['timestamp'] = serialized_entry['timestamp'].isoformat()
                
                serialized_log.append(serialized_entry)
            
            return serialized_log
            
        except Exception as e:
            self.logger.error(f"Error serializing APDU log: {e}")
            return []
    
    def get_card_summary(self) -> Dict[str, str]:
        """Get a summary of card information for display."""
        summary = {}
        
        if self.pan:
            summary['PAN'] = self._mask_pan(self.pan)
        
        if self.cardholder_name:
            summary['Cardholder'] = self.cardholder_name
        
        if self.expiry_date:
            # Convert YYMMDD to MM/YY
            if len(self.expiry_date) == 6:
                year = self.expiry_date[:2]
                month = self.expiry_date[2:4]
                summary['Expiry'] = f"{month}/{year}"
            else:
                summary['Expiry'] = self.expiry_date
        
        if self.applications:
            app_names = []
            for app in self.applications.values():
                name = app.application_label or app.preferred_name
                if name:
                    app_names.append(name)
            if app_names:
                summary['Applications'] = ', '.join(app_names[:3])  # Limit to 3
        
        summary['Records'] = str(sum(len(app.records) for app in self.applications.values()))
        summary['Cryptograms'] = str(sum(len(app.cryptograms) for app in self.applications.values()))
        
        return summary

    def to_ui_dict(self) -> Dict[str, Any]:
        """
        Convert EMVCard to dictionary format expected by UI.
        
        Returns:
            Dictionary with UI-compatible card data
        """
        from datetime import datetime
        
        card_type = self._determine_card_type()
        
        # Determine appropriate PAN display based on card type
        pan_display = 'N/A'
        if self.pan:
            # Actual PAN was extracted - show it
            pan_display = self.pan
        elif 'EMV' in card_type:
            # EMV card but PAN not accessible - this can happen
            pan_display = 'Protected (EMV Security)'
        elif self.uid:
            # Non-payment card - show UID as identifier
            pan_display = f'Card ID: {self.uid}'
        
        # Basic card information
        ui_data = {
            'atr': self.atr or 'N/A',
            'card_type': card_type,
            'pan': pan_display,
            'uid': self.uid or 'N/A',
            'expiry_date': self.expiry_date or 'N/A',
            'cardholder_name': self.cardholder_name or 'N/A',
            'aid': '',
            'application_label': '',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Get first application data if available
        if self.applications:
            first_app = next(iter(self.applications.values()))
            ui_data['aid'] = first_app.aid or 'N/A'
            ui_data['application_label'] = first_app.application_label or first_app.preferred_name or 'N/A'
        
        # Applications list for UI
        ui_data['applications'] = []
        for app_id, app in self.applications.items():
            app_data = {
                'aid': app.aid,
                'label': app.application_label or app.preferred_name,
                'priority': app.priority_indicator,
                'records': len(app.records) if app.records else 0
            }
            ui_data['applications'].append(app_data)
        
        # Track data - format for display
        ui_data['track_data'] = {}
        if self.track1_data:
            ui_data['track_data']['Track 1'] = self.track1_data
        if self.track2_data:
            ui_data['track_data']['Track 2'] = self.track2_data
        if self.track3_data:
            ui_data['track_data']['Track 3'] = self.track3_data
        
        # Add track_data from track_data dict if available (from universal parser)
        if hasattr(self, 'track_data') and isinstance(self.track_data, dict):
            for track_key, track_value in self.track_data.items():
                if track_key == 'track2' and track_value:
                    ui_data['track_data']['Track 2 (Raw)'] = track_value
        
        # TLV data - format with tag descriptions for display
        ui_data['tlv_data'] = {}
        if self.tlv_data:
            for tag, value in self.tlv_data.items():
                try:
                    # Convert bytes to hex string for display
                    if isinstance(value, bytes):
                        hex_value = value.hex().upper()
                        # Add spaces for readability if longer than 16 chars
                        if len(hex_value) > 16:
                            hex_value = ' '.join(hex_value[i:i+2] for i in range(0, len(hex_value), 2))
                    else:
                        hex_value = str(value)
                    
                    # Get tag description
                    tag_name = self.tag_dict.get_tag_name(tag)
                    tag_desc = self.tag_dict.get_tag_description(tag)
                    
                    # Create display entry
                    if tag_name and tag_name != tag:
                        display_key = f"{tag} ({tag_name})"
                    else:
                        display_key = tag
                    
                    ui_data['tlv_data'][display_key] = {
                        'value': hex_value,
                        'description': tag_desc or 'Unknown tag',
                        'length': len(value) if isinstance(value, bytes) else len(str(value))
                    }
                    
                except Exception as e:
                    # Fallback for problematic values
                    ui_data['tlv_data'][tag] = {
                        'value': str(value),
                        'description': 'Parse error',
                        'length': 0
                    }
        
        # ODA/Certificate data
        ui_data['oda_data'] = {}
        for app_id, app in self.applications.items():
            app_oda = {}
            
            # Static Data Authentication (SDA)
            if app.sda_data:
                sda_fields = {}
                if 'issuer_public_key_certificate' in app.sda_data:
                    sda_fields['Issuer Public Key Certificate'] = app.sda_data['issuer_public_key_certificate']
                if 'issuer_public_key_exponent' in app.sda_data:
                    sda_fields['Issuer Public Key Exponent'] = app.sda_data['issuer_public_key_exponent']
                if 'icc_public_key_certificate' in app.sda_data:
                    sda_fields['ICC Public Key Certificate'] = app.sda_data['icc_public_key_certificate']
                if 'icc_public_key_exponent' in app.sda_data:
                    sda_fields['ICC Public Key Exponent'] = app.sda_data['icc_public_key_exponent']
                if 'signed_static_data' in app.sda_data:
                    sda_fields['Signed Static Data'] = app.sda_data['signed_static_data']
                if sda_fields:
                    app_oda['Static Data Authentication (SDA)'] = sda_fields
            
            # Dynamic Data Authentication (DDA)
            if app.dda_data:
                dda_fields = {}
                if 'dda_public_key_certificate' in app.dda_data:
                    dda_fields['DDA Public Key Certificate'] = app.dda_data['dda_public_key_certificate']
                if 'dda_public_key_exponent' in app.dda_data:
                    dda_fields['DDA Public Key Exponent'] = app.dda_data['dda_public_key_exponent']
                if 'signed_dynamic_data' in app.dda_data:
                    dda_fields['Signed Dynamic Data'] = app.dda_data['signed_dynamic_data']
                if dda_fields:
                    app_oda['Dynamic Data Authentication (DDA)'] = dda_fields
            
            # Combined Data Authentication (CDA)
            if app.cda_data:
                cda_fields = {}
                if 'cda_signature' in app.cda_data:
                    cda_fields['CDA Signature'] = app.cda_data['cda_signature']
                if cda_fields:
                    app_oda['Combined Data Authentication (CDA)'] = cda_fields
            
            if app_oda:
                ui_data['oda_data'][f"{app.application_label or app.preferred_name} ({app.aid})"] = app_oda
        
        # Comprehensive Cryptographic Data Display
        ui_data['cryptographic_data'] = {}
        
        # Check if we have comprehensive cryptographic data from universal parser
        if hasattr(self, 'cryptographic_data') and self.cryptographic_data:
            for aid, crypto_info in self.cryptographic_data.items():
                crypto_display = {}
                
                if 'application_cryptogram' in crypto_info:
                    crypto_display['Application Cryptogram (9F26)'] = crypto_info['application_cryptogram']
                    
                if 'cid' in crypto_info:
                    crypto_display['Cryptogram Information Data (9F27)'] = crypto_info['cid']
                    
                if 'atc' in crypto_info:
                    crypto_display['Application Transaction Counter (9F36)'] = crypto_info['atc']
                    
                if 'cryptogram_type' in crypto_info:
                    crypto_display['Cryptogram Type'] = crypto_info['cryptogram_type']
                    
                if 'arqc_data' in crypto_info and crypto_info['arqc_data']:
                    arqc_display = {}
                    for tag, value in crypto_info['arqc_data'].items():
                        tag_desc = self.tag_dict.get_tag_description(tag)
                        hex_value = value.hex().upper() if isinstance(value, bytes) else str(value)
                        arqc_display[f"{tag} ({tag_desc})"] = hex_value
                    if arqc_display:
                        crypto_display['ARQC Data'] = arqc_display
                        
                if 'tc_data' in crypto_info and crypto_info['tc_data']:
                    tc_display = {}
                    for tag, value in crypto_info['tc_data'].items():
                        tag_desc = self.tag_dict.get_tag_description(tag)
                        hex_value = value.hex().upper() if isinstance(value, bytes) else str(value)
                        tc_display[f"{tag} ({tag_desc})"] = hex_value
                    if tc_display:
                        crypto_display['TC Data'] = tc_display
                
                if crypto_display:
                    ui_data['cryptographic_data'][aid] = crypto_display
        
        # Also extract cryptographic data from TLV if available
        crypto_tlv_data = {}
        if self.tlv_data:
            crypto_tags = {
                '9F26': 'Application Cryptogram',
                '9F27': 'Cryptogram Information Data (CID)',
                '9F36': 'Application Transaction Counter (ATC)', 
                '9F13': 'Last Online ATC Register',
                '82': 'Application Interchange Profile (AIP)',
                '94': 'Application File Locator (AFL)',
                '9F10': 'Issuer Application Data',
                '90': 'Issuer Public Key Certificate',
                '92': 'Issuer Public Key Remainder',
                '93': 'Signed Static Application Data',
                '9F46': 'ICC Public Key Certificate',
                '9F47': 'ICC Public Key Exponent',
                '9F48': 'ICC Public Key Remainder'
            }
            
            for tag, description in crypto_tags.items():
                if tag in self.tlv_data:
                    value = self.tlv_data[tag]
                    if isinstance(value, bytes):
                        hex_value = ' '.join(f'{b:02X}' for b in value)
                    else:
                        hex_value = str(value)
                    crypto_tlv_data[f"{tag} ({description})"] = hex_value
                    
        if crypto_tlv_data:
            ui_data['cryptographic_tlv'] = crypto_tlv_data
        
        # Extract all applications data if available
        if hasattr(self, 'all_applications') and self.all_applications:
            ui_data['all_applications'] = {}
            for aid, app_data in self.all_applications.items():
                app_display = {
                    'AID': aid,
                    'Label': app_data.get('application_label', 'N/A'),
                    'PAN': app_data.get('pan', 'N/A'),
                    'Expiry': app_data.get('expiry_date', 'N/A'),
                    'Card Type': app_data.get('card_type', 'N/A')
                }
                
                # Add cryptographic info for this application
                crypto_info = {}
                if app_data.get('application_cryptogram'):
                    crypto_info['Cryptogram'] = app_data['application_cryptogram']
                if app_data.get('cid'):
                    crypto_info['CID'] = app_data['cid']
                if app_data.get('atc'):
                    crypto_info['ATC'] = app_data['atc']
                if app_data.get('cryptogram_type'):
                    crypto_info['Type'] = app_data['cryptogram_type']
                    
                if crypto_info:
                    app_display['Cryptographic Data'] = crypto_info
                    
                ui_data['all_applications'][aid] = app_display
        
        # APDU responses for raw display - format for readability
        ui_data['raw_responses'] = []
        for apdu_entry in self.apdu_log:
            try:
                formatted_entry = {
                    'command': apdu_entry.get('command', 'Unknown'),
                    'response': apdu_entry.get('response', 'No response'),
                    'status': apdu_entry.get('sw1_sw2', 'Unknown'),
                    'timestamp': apdu_entry.get('timestamp', 'Unknown'),
                    'description': apdu_entry.get('description', 'APDU transaction')
                }
                
                # Format hex data with spaces for readability
                if 'command_hex' in apdu_entry:
                    hex_cmd = apdu_entry['command_hex'].replace(' ', '').upper()
                    formatted_entry['command_hex'] = ' '.join(hex_cmd[i:i+2] for i in range(0, len(hex_cmd), 2))
                
                if 'response_hex' in apdu_entry:
                    hex_resp = apdu_entry['response_hex'].replace(' ', '').upper()
                    formatted_entry['response_hex'] = ' '.join(hex_resp[i:i+2] for i in range(0, len(hex_resp), 2))
                
                ui_data['raw_responses'].append(formatted_entry)
            except Exception as e:
                # Fallback for malformed entries
                ui_data['raw_responses'].append({
                    'command': str(apdu_entry),
                    'response': 'Format error',
                    'status': 'N/A',
                    'timestamp': 'N/A',
                    'description': 'Malformed APDU entry'
                })
        
        # Add comprehensive cryptographic data from all applications
        ui_data['comprehensive_crypto'] = {}
        
        # Check for all_cryptograms from comprehensive parsing
        if hasattr(self, 'all_cryptograms') and self.all_cryptograms:
            crypto_summary = {}
            for i, cryptogram in enumerate(self.all_cryptograms):
                crypto_key = f"Cryptogram_{i+1}"
                crypto_summary[crypto_key] = {
                    'Type': cryptogram.get('type', 'Unknown'),
                    'Value': cryptogram.get('cryptogram', 'N/A'),
                    'CID': cryptogram.get('cid', 'N/A'),
                    'ATC': cryptogram.get('atc', 'N/A'),
                    'Timestamp': cryptogram.get('timestamp', 'N/A')
                }
            ui_data['comprehensive_crypto']['All_Cryptograms'] = crypto_summary
        
        # Check for all_applications data from comprehensive parsing
        if hasattr(self, 'all_applications') and self.all_applications:
            apps_summary = {}
            for aid, app_data in self.all_applications.items():
                app_crypto = {}
                
                # Extract cryptographic data for this application
                if 'cryptograms' in app_data:
                    for j, crypto in enumerate(app_data['cryptograms']):
                        app_crypto[f'Crypto_{j+1}'] = {
                            'Type': crypto.get('type', 'Unknown'),
                            'Value': crypto.get('cryptogram', 'N/A'),
                            'CID': crypto.get('cid', 'N/A'),
                            'ATC': crypto.get('atc', 'N/A')
                        }
                
                # Extract key EMV tags for this application
                app_emv_data = {}
                if 'tlv_data' in app_data:
                    for tag, value in app_data['tlv_data'].items():
                        if tag in ['9F26', '9F27', '9F36', '9F34', '95', '9F37']:  # Important crypto tags
                            try:
                                if isinstance(value, bytes):
                                    hex_val = value.hex().upper()
                                    hex_val = ' '.join(hex_val[i:i+2] for i in range(0, len(hex_val), 2))
                                    app_emv_data[tag] = hex_val
                                else:
                                    app_emv_data[tag] = str(value)
                            except:
                                app_emv_data[tag] = 'Parse Error'
                
                apps_summary[aid] = {
                    'Name': app_data.get('name', 'Unknown'),
                    'Cryptograms': app_crypto,
                    'Key_EMV_Tags': app_emv_data
                }
            
            ui_data['comprehensive_crypto']['All_Applications'] = apps_summary
        
        # Add terminal emulation results if available
        if hasattr(self, 'terminal_data') and self.terminal_data:
            ui_data['terminal_emulation'] = self.terminal_data
            
        if hasattr(self, 'transaction_results') and self.transaction_results:
            ui_data['transaction_results'] = self.transaction_results
        
        return ui_data
