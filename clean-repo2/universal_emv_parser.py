#!/usr/bin/env python3
"""
Universal EMV Parser for all major US card types
Supports: Visa, Mastercard, American Express, Discover, and other major brands
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from smartcard.System import readers as pcsc_readers
from smartcard.util import toHexString
from emv_terminal_emulator import EMVTerminalEmulator

class UniversalEMVParser:
    """Universal EMV parser for all major card types used in the USA"""
    
    # Comprehensive list of US card AIDs
    US_CARD_AIDS = [
        # Visa
        ("A0000000031010", "Visa Credit/Debit"),
        ("A0000000032010", "Visa Credit/Debit"),  
        ("A0000000033010", "Visa Interlink"),
        ("A0000000034010", "Visa Credit/Debit"),
        ("A0000000035010", "Visa Credit/Debit"),
        ("A0000000036010", "Visa Credit/Debit"),
        ("A0000000038010", "Visa Plus"),
        ("A0000000041010", "Visa Credit/Debit"),
        ("A0000000043060", "Visa Electron"),
        ("A00000000980", "Visa Common Debit"),
        ("A0000000980840", "Visa Common Debit"),
        
        # Mastercard
        ("A0000000041010", "Mastercard Credit/Debit"),
        ("A0000000042010", "Mastercard Credit/Debit"),
        ("A0000000043010", "Mastercard Credit/Debit"),
        ("A0000000044010", "Mastercard Credit/Debit"),
        ("A0000000045010", "Mastercard Credit/Debit"),
        ("A0000000046000", "Mastercard Credit/Debit"),
        ("A0000000050001", "Mastercard Credit/Debit"),
        ("A0000000050002", "Mastercard World/World Elite"),
        ("A00000000401", "Mastercard Credit/Debit"),
        ("A000000004", "Mastercard"),
        ("A0000000980840", "Mastercard Common Debit"),
        
        # American Express
        ("A000000025", "American Express"),
        ("A0000000250000", "American Express"),
        ("A000000025010104", "American Express"),
        ("A000000025010701", "American Express"),
        ("A000000025010801", "American Express"),
        
        # Discover
        ("A0000001523010", "Discover"),
        ("A0000001524010", "Discover"),
        ("A00000015290", "Discover"),
        ("A0000000651010", "Discover/Diners"),
        
        # Other US cards
        ("A0000000651010", "Diners Club"),
        ("A0000001544442", "Bancontact"),
        ("A0000000980848", "Common US Debit"),
        
        # Generic/Fallback
        ("A000000003", "Visa Generic"),
        ("A000000004", "Mastercard Generic"),
        ("A000000025", "Amex Generic"),
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize EMV Terminal Emulator for complete transaction processing
        self.terminal_emulator = EMVTerminalEmulator()
        
    def parse_card_comprehensive(self, connection=None) -> Optional[Dict[str, Any]]:
        """
        Parse ALL EMV card data using full terminal emulation
        Extracts cryptograms, ARQC/TC, and data from every AID
        
        Args:
            connection: Optional existing smartcard connection
            
        Returns:
            Dictionary with comprehensive card data from all applications
        """
        try:
            # Use provided connection or create new one
            if connection is None:
                connection = self._create_connection()
                if not connection:
                    return None
            
            # Use terminal emulator for complete transaction processing
            try:
                self.logger.info("Starting comprehensive terminal emulation...")
                comprehensive_data = self.terminal_emulator.emulate_full_transaction(connection)
                self.logger.info(f"Terminal emulation completed, got data: {type(comprehensive_data)}")
                
                if comprehensive_data:
                    self.logger.info(f"Terminal emulation keys: {list(comprehensive_data.keys())}")
                else:
                    self.logger.warning("Terminal emulation returned None or empty data")
                    
            except Exception as e:
                self.logger.error(f"Terminal emulation failed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
            
            if comprehensive_data and comprehensive_data.get('applications'):
                self.logger.info(f"Comprehensive parsing successful: {len(comprehensive_data['applications'])} applications processed")
                
                # Convert to format compatible with existing code
                consolidated_data = self._consolidate_comprehensive_data(comprehensive_data)
                return consolidated_data
            
            self.logger.warning("No applications found with comprehensive parsing")
            return None
            
        except Exception as e:
            self.logger.error(f"Comprehensive card parsing failed: {e}")
            return None
    
    def _consolidate_comprehensive_data(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert comprehensive data to format compatible with existing EMVCard"""
        
        # Find the application with the most data
        best_app = None
        best_app_data = None
        
        for aid, app_data in comprehensive_data.get('applications', {}).items():
            if not best_app or len(app_data.get('tlv_data', {})) > len(best_app_data.get('tlv_data', {})):
                best_app = aid
                best_app_data = app_data
        
        if not best_app_data:
            return None
        
        # Build consolidated card data
        card_data = {
            'aid': best_app,
            'application_label': best_app_data.get('name', 'Unknown'),
            'pan': None,
            'expiry_date': None,
            'cardholder_name': None,
            'track_data': {},
            'tlv_data': {},
            'card_type': self._determine_card_type(best_app, best_app_data.get('name', '')),
            'uid': None,
            'apdu_log': comprehensive_data.get('apdu_log', []),
            'all_applications': comprehensive_data.get('applications', {}),
            'all_cryptograms': comprehensive_data.get('all_cryptograms', []),
            'terminal_data': comprehensive_data.get('terminal_data', {}),
            'transaction_results': comprehensive_data.get('transaction_results', {})
        }
        
        # Consolidate TLV data from all applications
        for aid, app_data in comprehensive_data.get('applications', {}).items():
            card_data['tlv_data'].update(app_data.get('tlv_data', {}))
        
        # Extract key data from TLV
        for tag, value in card_data['tlv_data'].items():
            try:
                if tag == '5A':  # PAN
                    pan = self._bcd_decode(value)
                    if pan and len(pan) >= 13:
                        card_data['pan'] = pan
                        
                elif tag == '5F24':  # Expiry date
                    expiry = self._bcd_decode(value)
                    if expiry and len(expiry) == 6:
                        card_data['expiry_date'] = f"{expiry[4:6]}/{expiry[0:2]}"
                        
                elif tag == '5F20':  # Cardholder name
                    try:
                        name = value.decode('ascii').strip()
                        if name:
                            card_data['cardholder_name'] = name
                    except:
                        pass
                        
                elif tag == '57':  # Track 2 equivalent
                    track2_hex = value.hex().upper()
                    card_data['track_data']['track2'] = track2_hex
                    
            except Exception as e:
                self.logger.debug(f"Error processing tag {tag}: {e}")
        
        return card_data
    
    def parse_card(self, connection=None) -> Optional[Dict[str, Any]]:
        """
        Parse EMV card data from ALL applications on card (modified to extract everything)
        
        Args:
            connection: Optional existing smartcard connection
            
        Returns:
            Dictionary with comprehensive card data from all AIDs or None if failed
        """
        try:
            # Initialize APDU log and comprehensive data storage
            apdu_log = []
            all_applications = {}  # Store data from all AIDs
            
            # Use provided connection or create new one
            if connection is None:
                connection = self._create_connection()
                if not connection:
                    return None
            
            # Try to select PPSE first
            ppse_success = self._select_ppse(connection, apdu_log)
            if not ppse_success:
                self.logger.warning("PPSE selection failed, trying direct AID selection")
            
            # Try ALL known AIDs (don't stop at first success like before)
            successful_extractions = 0
            
            for aid_hex, description in self.US_CARD_AIDS:
                try:
                    if self._select_application(connection, aid_hex, apdu_log):
                        self.logger.info(f"Successfully selected: {description} ({aid_hex})")
                        
                        # Extract card data from this AID
                        app_data = self._extract_card_data(connection, aid_hex, description, apdu_log)
                        if app_data and (app_data.get('pan') or app_data.get('uid') or app_data.get('tlv_data')):
                            all_applications[aid_hex] = app_data
                            successful_extractions += 1
                            self.logger.info(f"Extracted data from {description}: "
                                           f"PAN={'***' if app_data.get('pan') else 'N/A'}, "
                                           f"TLV tags={len(app_data.get('tlv_data', {}))}")
                            
                            # Try to extract cryptograms for this application
                            self._try_extract_cryptograms(connection, app_data, apdu_log)
                            
                except Exception as e:
                    self.logger.debug(f"Failed to process {description}: {e}")
                    continue
            
            if not all_applications:
                self.logger.warning("No supported applications found on card")
                return None
                
            self.logger.info(f"Successfully extracted data from {successful_extractions} applications")
            
            # Create comprehensive card data from all applications
            consolidated_data = self._consolidate_all_applications(all_applications, apdu_log)
            consolidated_data['apdu_log'] = apdu_log
            consolidated_data['all_applications'] = all_applications
            
            return consolidated_data
            
        except Exception as e:
            self.logger.error(f"Comprehensive card parsing failed: {e}")
            return None
    
    def _try_extract_cryptograms(self, connection, app_data: Dict, apdu_log: List[Dict]):
        """Try to extract cryptograms from current application"""
        try:
            # Try to generate ARQC/TC using Generate AC command
            for ac_type, ac_name in [(0x80, "ARQC"), (0x40, "TC"), (0x00, "AAC")]:
                try:
                    # Simple CDOL data for Generate AC
                    cdol_data = bytes([
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x01,  # Amount
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Amount Other
                        0x08, 0x40,                           # Country Code (USA)
                        0x80, 0x00, 0x00, 0x00, 0x00,       # TVR
                        0x08, 0x40,                           # Currency Code
                    ])
                    
                    gen_ac_command = [0x80, 0xAE, ac_type, 0x00, len(cdol_data)] + list(cdol_data)
                    response, sw1, sw2 = connection.transmit(gen_ac_command)
                    
                    apdu_log.append({
                        'command': f"GENERATE AC ({ac_name})",
                        'command_hex': ' '.join(f'{b:02X}' for b in gen_ac_command),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Generate {ac_name} - Cryptogram Generation'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00 and response:
                        # Extract cryptogram from response
                        if len(response) >= 8:
                            cryptogram = ''.join(f'{b:02X}' for b in response[:8])
                            app_data[f'{ac_name.lower()}_cryptogram'] = cryptogram
                            app_data['application_cryptogram'] = cryptogram
                            app_data['cryptogram_type'] = ac_name
                            
                            if len(response) > 8:
                                app_data['cid'] = f"{response[8]:02X}"  # CID
                            if len(response) > 10:
                                app_data['atc'] = ''.join(f'{response[i]:02X}' for i in range(9, 11))  # ATC
                            
                            self.logger.info(f"Generated {ac_name}: {cryptogram}")
                            break  # Stop after first successful cryptogram
                        
                except Exception as e:
                    self.logger.debug(f"Generate AC {ac_name} failed: {e}")
                    
        except Exception as e:
            self.logger.debug(f"Cryptogram extraction failed: {e}")
    
    def _consolidate_all_applications(self, all_applications: Dict, apdu_log: List[Dict]) -> Dict[str, Any]:
        """Consolidate data from all applications into a single card data structure"""
        
        # Find the application with the best data (most complete)
        best_app = None
        best_app_data = None
        best_score = 0
        
        for aid, app_data in all_applications.items():
            score = 0
            if app_data.get('pan'): score += 10
            if app_data.get('expiry_date'): score += 5
            if app_data.get('cardholder_name'): score += 5
            if app_data.get('tlv_data'): score += len(app_data['tlv_data'])
            if app_data.get('application_cryptogram'): score += 20
            
            if score > best_score:
                best_score = score
                best_app = aid
                best_app_data = app_data
        
        if not best_app_data:
            # Fallback - use first application
            best_app = list(all_applications.keys())[0]
            best_app_data = all_applications[best_app]
        
        # Create consolidated card data
        consolidated_data = {
            'aid': best_app,
            'application_label': best_app_data.get('application_label', 'Unknown'),
            'pan': best_app_data.get('pan'),
            'expiry_date': best_app_data.get('expiry_date'),
            'cardholder_name': best_app_data.get('cardholder_name'),
            'track_data': best_app_data.get('track_data', {}),
            'tlv_data': {},
            'card_type': best_app_data.get('card_type', 'EMV Card'),
            'uid': best_app_data.get('uid'),
            'all_applications': all_applications,  # Store ALL application data
            'cryptographic_summary': {}
        }
        
        # Consolidate TLV data from all applications
        for aid, app_data in all_applications.items():
            if app_data.get('tlv_data'):
                consolidated_data['tlv_data'].update(app_data['tlv_data'])
        
        # Create cryptographic summary
        for aid, app_data in all_applications.items():
            if any(key in app_data for key in ['application_cryptogram', 'arqc_cryptogram', 'tc_cryptogram', 'aac_cryptogram']):
                consolidated_data['cryptographic_summary'][aid] = {
                    'application_name': app_data.get('application_label', 'Unknown'),
                    'cryptogram': app_data.get('application_cryptogram', 'N/A'),
                    'cryptogram_type': app_data.get('cryptogram_type', 'N/A'),
                    'cid': app_data.get('cid', 'N/A'),
                    'atc': app_data.get('atc', 'N/A')
                }
        
        return consolidated_data
    
    def _create_connection(self):
        """Create a new smartcard connection"""
        try:
            reader_list = pcsc_readers()
            if not reader_list:
                self.logger.error("No card readers found")
                return None
                
            reader = reader_list[0]
            connection = reader.createConnection()
            connection.connect()
            
            self.logger.info(f"Connected to reader: {reader}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            return None
    
    def _select_ppse(self, connection, apdu_log: List[Dict]) -> bool:
        """Select Payment System Environment"""
        try:
            # Try 2PAY.SYS.DDF01 first (contactless)
            ppse_aids = [
                ("325041592E5359532E4444463031", "2PAY.SYS.DDF01 (contactless)"),
                ("315041592E5359532E4444463031", "1PAY.SYS.DDF01 (contact)"),
            ]
            
            for ppse_hex, ppse_desc in ppse_aids:
                try:
                    ppse_aid = bytes.fromhex(ppse_hex)
                    select_ppse = [0x00, 0xA4, 0x04, 0x00, len(ppse_aid)] + list(ppse_aid)
                    
                    response, sw1, sw2 = connection.transmit(select_ppse)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"SELECT {ppse_desc}",
                        'command_hex': ' '.join(f'{b:02X}' for b in select_ppse),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',  # Could add real timestamp if needed
                        'description': f'Select PPSE: {ppse_desc}'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        self.logger.info("PPSE selected successfully")
                        return True
                        
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"PPSE selection failed: {e}")
            return False
    
    def _select_ppse_with_discovery(self, connection, apdu_log: List[Dict]) -> Tuple[bool, List[Tuple[str, str]]]:
        """Select PPSE and discover all available AIDs on the card"""
        try:
            discovered_aids = []
            
            # Try 2PAY.SYS.DDF01 first (contactless) with discovery
            ppse_aids = [
                ("325041592E5359532E4444463031", "2PAY.SYS.DDF01 (contactless)"),
                ("315041592E5359532E4444463031", "1PAY.SYS.DDF01 (contact)"),
            ]
            
            for ppse_hex, ppse_desc in ppse_aids:
                try:
                    ppse_aid = bytes.fromhex(ppse_hex)
                    select_ppse = [0x00, 0xA4, 0x04, 0x00, len(ppse_aid)] + list(ppse_aid)
                    
                    response, sw1, sw2 = connection.transmit(select_ppse)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"SELECT {ppse_desc} (with discovery)",
                        'command_hex': ' '.join(f'{b:02X}' for b in select_ppse),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Select PPSE with AID discovery: {ppse_desc}'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00 and response:
                        # Parse response to find AIDs
                        discovered_aids = self._parse_ppse_response(response)
                        self.logger.info(f"PPSE discovered {len(discovered_aids)} AIDs")
                        return True, discovered_aids
                        
                except Exception:
                    continue
            
            return False, []
            
        except Exception as e:
            self.logger.debug(f"PPSE selection with discovery failed: {e}")
            return False, []
    
    def _parse_ppse_response(self, response: List[int]) -> List[Tuple[str, str]]:
        """Parse PPSE response to extract all available AIDs"""
        aids = []
        try:
            response_hex = ''.join(f'{b:02X}' for b in response)
            
            # Look for FCI template (6F) and ADF names (4F)
            i = 0
            while i < len(response_hex) - 4:
                if response_hex[i:i+2] == '4F':  # ADF Name tag
                    length = int(response_hex[i+2:i+4], 16)
                    aid_start = i + 4
                    aid_end = aid_start + (length * 2)
                    
                    if aid_end <= len(response_hex):
                        aid_hex = response_hex[aid_start:aid_end]
                        # Find matching description
                        aid_desc = 'Discovered Application'
                        for known_aid, desc in self.US_CARD_AIDS:
                            if aid_hex.upper() == known_aid.upper():
                                aid_desc = desc
                                break
                        aids.append((aid_hex, aid_desc))
                        self.logger.debug(f"Found AID in PPSE: {aid_hex}")
                
                i += 2
                
        except Exception as e:
            self.logger.debug(f"Error parsing PPSE response: {e}")
            
        return aids
    
    def _select_application(self, connection, aid_hex: str, apdu_log: List[Dict]) -> bool:
        """Select specific EMV application"""
        try:
            aid_bytes = bytes.fromhex(aid_hex)
            select_aid = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            
            response, sw1, sw2 = connection.transmit(select_aid)
            
            # Log APDU
            apdu_log.append({
                'command': f"SELECT AID {aid_hex}",
                'command_hex': ' '.join(f'{b:02X}' for b in select_aid),
                'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                'status': f'{sw1:02X}{sw2:02X}',
                'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                'timestamp': 'N/A',
                'description': f'Select application AID: {aid_hex}'
            })
            
            return sw1 == 0x90 and sw2 == 0x00
            
        except Exception as e:
            self.logger.debug(f"AID {aid_hex} selection failed: {e}")
            return False
    
    def _extract_card_data(self, connection, aid_hex: str, description: str, apdu_log: List[Dict]) -> Dict[str, Any]:
        """Extract EMV data from selected application"""
        card_data = {
            'aid': aid_hex,
            'application_label': description,
            'pan': None,
            'expiry_date': None,
            'cardholder_name': None,
            'track_data': {},
            'tlv_data': {},
            'card_type': self._determine_card_type(aid_hex, description),
            'uid': None,
            'apdu_log': apdu_log
        }
        
        # Try direct record reading (works for most contactless cards)
        self._read_records_direct(connection, card_data)
        
        # If no PAN found, try other methods
        if not card_data.get('pan'):
            self._try_get_data_commands(connection, card_data)
        
        # If still no PAN, try GPO + record reading
        if not card_data.get('pan'):
            self._try_gpo_method(connection, card_data)
        
        return card_data
    
    def _read_records_direct(self, connection, card_data: Dict[str, Any]):
        """Try direct record reading without GPO"""
        try:
            apdu_log = card_data.get('apdu_log', [])
            
            # Common record locations for different card types
            record_locations = [
                # Visa typical locations
                (1, 1, "Track2/Payment data"),
                (2, 1, "Application data"),
                (2, 2, "Application data"),
                (2, 3, "Application data"),
                (2, 4, "Application data"),
                (2, 5, "PAN data"),
                (2, 6, "Additional data"),
                
                # Mastercard typical locations
                (1, 2, "Track2 data"),
                (3, 1, "Payment data"),
                (3, 2, "Payment data"),
                
                # Amex typical locations
                (1, 3, "Payment data"),
                (4, 1, "Payment data"),
                (4, 2, "Payment data"),
            ]
            
            for sfi, record, description in record_locations:
                try:
                    p2 = (sfi << 3) | 0x04  # SFI in upper 4 bits
                    read_record = [0x00, 0xB2, record, p2, 0x00]
                    
                    response, sw1, sw2 = connection.transmit(read_record)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"READ RECORD SFI{sfi}.{record}",
                        'command_hex': ' '.join(f'{b:02X}' for b in read_record),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Read record {record} from SFI {sfi} - {description}'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        self.logger.debug(f"Read SFI{sfi}.{record}: {len(response)} bytes")
                        self._parse_record_response(response, card_data)
                        
                except Exception as e:
                    self.logger.debug(f"Failed to read SFI{sfi}.{record}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Direct record reading failed: {e}")
    
    def _try_get_data_commands(self, connection, card_data: Dict[str, Any]):
        """Try GET DATA commands for card information"""
        apdu_log = card_data.get('apdu_log', [])
        
        get_data_commands = [
            ([0x00, 0xCA, 0x5A, 0x00, 0x00], "PAN"),
            ([0x00, 0xCA, 0x57, 0x00, 0x00], "Track 2 Equivalent"),
            ([0x00, 0xCA, 0x5F, 0x20, 0x00], "Cardholder Name"),
            ([0x00, 0xCA, 0x5F, 0x24, 0x00], "Expiry Date"),
            ([0x00, 0xCA, 0x5F, 0x30, 0x00], "Service Code"),
        ]
        
        for command, name in get_data_commands:
            try:
                response, sw1, sw2 = connection.transmit(command)
                
                # Log APDU
                apdu_log.append({
                    'command': f"GET DATA {name}",
                    'command_hex': ' '.join(f'{b:02X}' for b in command),
                    'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                    'status': f'{sw1:02X}{sw2:02X}',
                    'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                    'timestamp': 'N/A',
                    'description': f'Get data for {name}'
                })
                
                if sw1 == 0x90 and sw2 == 0x00:
                    self.logger.debug(f"GET DATA {name} successful: {len(response)} bytes")
                    self._parse_record_response(response, card_data)
                    
            except Exception as e:
                self.logger.debug(f"GET DATA {name} failed: {e}")
    
    def _try_gpo_method(self, connection, card_data: Dict[str, Any]):
        """Try GPO (Generate Processing Options) method"""
        try:
            apdu_log = card_data.get('apdu_log', [])
            
            # Try different PDOL parameters
            pdol_variants = [
                bytes([0x83, 0x00]),  # Empty PDOL
                bytes([0x83, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x56]),  # Basic transaction
            ]
            
            for i, pdol in enumerate(pdol_variants):
                try:
                    gpo_command = [0x80, 0xA8, 0x00, 0x00, len(pdol)] + list(pdol)
                    response, sw1, sw2 = connection.transmit(gpo_command)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"GPO (variant {i+1})",
                        'command_hex': ' '.join(f'{b:02X}' for b in gpo_command),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Generate Processing Options (variant {i+1})'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        self.logger.debug("GPO successful, trying record reading")
                        self._read_records_direct(connection, card_data)
                        break
                        
                except Exception as e:
                    self.logger.debug(f"GPO variant failed: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"GPO method failed: {e}")
    
    def _parse_record_response(self, response: List[int], card_data: Dict[str, Any]):
        """Parse EMV record response for TLV data"""
        try:
            # Convert response to hex string
            response_hex = ''.join(f'{b:02X}' for b in response)
            
            # Parse TLV tags
            tlv_data = self._parse_tlv_simple(response_hex)
            card_data['tlv_data'].update(tlv_data)
            
            # Extract specific data
            for tag, value_bytes in tlv_data.items():
                if tag == '5A':  # PAN
                    pan = self._bcd_decode(value_bytes)
                    # Only set PAN if we don't have one, or this one looks more valid
                    if pan and 13 <= len(pan) <= 19:  # Valid PAN length range
                        current_pan = card_data.get('pan', '')
                        # Prefer shorter, valid PAN (usually more accurate)
                        if not current_pan or (len(pan) < len(current_pan) and len(pan) >= 13):
                            card_data['pan'] = pan
                            self.logger.info(f"Extracted PAN: {pan}")
                        elif len(pan) == 16 and len(current_pan) != 16:  # Prefer standard 16-digit PAN
                            card_data['pan'] = pan
                            self.logger.info(f"Updated to standard PAN: {pan}")
                
                elif tag == '57':  # Track 2 Equivalent Data
                    track2_hex = ''.join(f'{b:02X}' for b in value_bytes)
                    card_data['track_data']['track2'] = track2_hex
                    
                    # Parse Track2 for PAN and expiry (only if not already set or current is invalid)
                    if 'D' in track2_hex:
                        parts = track2_hex.split('D')
                        if len(parts) >= 2:
                            track2_pan = parts[0]
                            current_pan = card_data.get('pan', '')
                            
                            # Prefer Track2 PAN if it's 16 digits and current isn't, or if we have no PAN
                            if track2_pan and 13 <= len(track2_pan) <= 19:
                                if not current_pan or (len(track2_pan) == 16 and len(current_pan) != 16):
                                    card_data['pan'] = track2_pan
                                    self.logger.info(f"Extracted PAN from Track2: {track2_pan}")
                            
                            # Extract expiry (YYMM format) only if not already set or current looks invalid
                            if len(parts[1]) >= 4:
                                expiry_yymm = parts[1][:4]
                                if len(expiry_yymm) == 4:
                                    try:
                                        yy_int = int(expiry_yymm[:2])
                                        mm_int = int(expiry_yymm[2:4])
                                        # Only use if it looks like a valid date
                                        if 1 <= mm_int <= 12 and 20 <= yy_int <= 40:
                                            yy, mm = expiry_yymm[:2], expiry_yymm[2:4]
                                            expiry = f"{mm}/{yy}"
                                            current_expiry = card_data.get('expiry_date', '')
                                            if not current_expiry:
                                                card_data['expiry_date'] = expiry
                                                self.logger.info(f"Extracted expiry: {expiry}")
                                    except:
                                        pass
                
                elif tag == '5F20':  # Cardholder Name
                    if not card_data.get('cardholder_name'):  # Only if not already set
                        try:
                            name = value_bytes.decode('utf-8', errors='ignore').strip()
                            if name and len(name) > 3:  # Reasonable name length
                                card_data['cardholder_name'] = name
                                self.logger.info(f"Extracted name: {name}")
                        except:
                            pass
                
                elif tag == '5F24':  # Application Expiry Date
                    if len(value_bytes) >= 3:
                        yy = f"{value_bytes[0]:02d}"
                        mm = f"{value_bytes[1]:02d}"
                        expiry = f"{mm}/{yy}"
                        card_data['expiry_date'] = expiry
                        self.logger.info(f"Extracted expiry from 5F24: {expiry}")
                
                elif tag == '50':  # Application Label
                    if not card_data.get('application_label') or card_data['application_label'] in ['EMV Application', 'Visa Credit/Debit']:
                        try:
                            label = value_bytes.decode('utf-8', errors='ignore').strip()
                            if label and len(label) > 2 and label.replace(' ', '').isalnum():  # Valid looking label
                                card_data['application_label'] = label
                                self.logger.info(f"Updated application label: {label}")
                        except:
                            pass
                        
        except Exception as e:
            self.logger.debug(f"Record parsing failed: {e}")
    
    def _parse_tlv_simple(self, data_hex: str) -> Dict[str, bytes]:
        """Simple TLV parser for EMV data"""
        parsed = {}
        
        # Common EMV tags to look for
        tags_to_find = ['5A', '57', '5F20', '5F24', '50', '84', '9F6E']
        
        for tag in tags_to_find:
            pos = data_hex.find(tag)
            if pos >= 0 and pos + 4 < len(data_hex):
                try:
                    length_hex = data_hex[pos+2:pos+4]
                    length = int(length_hex, 16)
                    
                    value_start = pos + 4
                    value_end = value_start + (length * 2)
                    
                    if value_end <= len(data_hex):
                        value_hex = data_hex[value_start:value_end]
                        value_bytes = bytes.fromhex(value_hex)
                        parsed[tag] = value_bytes
                        
                except Exception:
                    continue
        
        return parsed
    
    def _bcd_decode(self, data: bytes) -> str:
        """Decode BCD (Binary Coded Decimal) data"""
        result = ""
        for byte in data:
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            
            if high <= 9:
                result += str(high)
            if low <= 9:
                result += str(low)
            elif low == 0x0F:  # Padding
                break
                
        return result
    
    def _determine_card_type(self, aid_hex: str, description: str) -> str:
        """Determine card type from AID and description"""
        aid_upper = aid_hex.upper()
        desc_upper = description.upper()
        
        if 'VISA' in desc_upper or aid_upper.startswith('A000000003'):
            return "Visa EMV Card"
        elif 'MASTERCARD' in desc_upper or 'MASTER' in desc_upper or aid_upper.startswith('A000000004'):
            return "Mastercard EMV Card"
        elif 'AMERICAN EXPRESS' in desc_upper or 'AMEX' in desc_upper or aid_upper.startswith('A000000025'):
            return "American Express EMV Card"
        elif 'DISCOVER' in desc_upper or aid_upper.startswith('A0000001523') or aid_upper.startswith('A000000651'):
            return "Discover EMV Card"
        elif 'DINERS' in desc_upper:
            return "Diners Club EMV Card"
        else:
            return "EMV Contactless Card"

    def _extract_complete_application_data(self, connection, aid_hex: str, description: str, apdu_log: List[Dict]) -> Dict[str, Any]:
        """Extract comprehensive data from a single application including cryptograms"""
        app_data = {
            'aid': aid_hex,
            'application_label': description,
            'pan': None,
            'expiry_date': None,
            'cardholder_name': None,
            'track_data': {},
            'tlv_data': {},
            'card_type': self._determine_card_type(aid_hex, description),
            'uid': None,
            'application_cryptogram': None,
            'cid': None,  # Cryptogram Information Data
            'atc': None,  # Application Transaction Counter
            'arqc_data': {},  # ARQC related data
            'tc_data': {},    # TC related data
            'oda_data': {}    # Offline Data Authentication
        }
        
        # Try direct record reading first
        self._read_records_direct(connection, app_data)
        
        # Try GET DATA commands for more info
        self._try_get_data_commands(connection, app_data)
        
        # Try GPO to generate cryptograms (ARQC/TC)
        self._try_comprehensive_gpo(connection, app_data, apdu_log)
        
        # Extract cryptogram-related data from TLV
        self._extract_cryptogram_data(app_data)
        
        return app_data
    
    def _try_comprehensive_gpo(self, connection, card_data: Dict[str, Any], apdu_log: List[Dict]):
        """Try GPO with different PDOL parameters to generate cryptograms"""
        try:
            # Multiple PDOL variants to try different transaction types
            pdol_variants = [
                # Empty PDOL
                (bytes([0x83, 0x00]), "Empty PDOL"),
                
                # Basic transaction amount
                (bytes([0x83, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x56]), "Basic transaction"),
                
                # Transaction with amount 1.00 USD
                (bytes([0x83, 0x1B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x08, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x56, 0x42, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]), "Transaction $1.00"),
                
                # CDOL1 related data for ARQC generation
                (bytes([0x83, 0x25, 0x9F, 0x02, 0x06, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x9F, 0x03, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x9F, 0x1A, 0x02, 0x08, 0x40, 0x95, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5F, 0x2A, 0x02, 0x08, 0x40, 0x9A, 0x03, 0x20, 0x01, 0x01]), "CDOL1 ARQC"),
            ]
            
            for pdol, description in pdol_variants:
                try:
                    gpo_command = [0x80, 0xA8, 0x00, 0x00, len(pdol)] + list(pdol)
                    response, sw1, sw2 = connection.transmit(gpo_command)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"GPO ({description})",
                        'command_hex': ' '.join(f'{b:02X}' for b in gpo_command),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Generate Processing Options: {description}'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        self.logger.debug(f"GPO successful ({description}), parsing response")
                        
                        # Parse GPO response for AIP and AFL
                        if response:
                            self._parse_gpo_response(response, card_data)
                            
                        # Read records from AFL if available
                        self._read_afl_records(connection, card_data, apdu_log)
                        
                        # Try to generate ARQC
                        self._try_generate_arqc(connection, card_data, apdu_log)
                        
                        break  # Stop on first successful GPO
                        
                except Exception as e:
                    self.logger.debug(f"GPO variant ({description}) failed: {e}")
                    continue
                    
        except Exception as e:
            self.logger.debug(f"Comprehensive GPO failed: {e}")
    
    def _parse_gpo_response(self, response: List[int], card_data: Dict[str, Any]):
        """Parse GPO response for AIP and AFL"""
        try:
            if len(response) >= 2:
                # Check if response is in format 1 or 2
                if response[0] == 0x77:  # Format 2 - TLV encoded
                    response_hex = ''.join(f'{b:02X}' for b in response)
                    tlv_data = self._parse_tlv_simple(response_hex)
                    card_data['tlv_data'].update(tlv_data)
                    
                elif response[0] == 0x80:  # Format 1 - primitive data
                    if len(response) >= 4:
                        # AIP (first 2 bytes after tag and length)
                        aip = response[2:4]
                        card_data['tlv_data']['82'] = bytes(aip)  # AIP tag
                        
                        # AFL (remaining bytes)
                        if len(response) > 4:
                            afl = response[4:]
                            card_data['afl_data'] = afl
                            
        except Exception as e:
            self.logger.debug(f"GPO response parsing failed: {e}")
    
    def _read_afl_records(self, connection, card_data: Dict[str, Any], apdu_log: List[Dict]):
        """Read records from Application File Locator (AFL)"""
        try:
            afl_data = card_data.get('afl_data', [])
            if not afl_data:
                return
                
            # Parse AFL entries (4 bytes each)
            for i in range(0, len(afl_data), 4):
                if i + 3 < len(afl_data):
                    sfi = (afl_data[i] >> 3) & 0x1F
                    start_record = afl_data[i + 1]
                    end_record = afl_data[i + 2]
                    offline_auth_records = afl_data[i + 3]
                    
                    # Read each record in the range
                    for record_num in range(start_record, end_record + 1):
                        try:
                            p2 = (sfi << 3) | 0x04
                            read_record = [0x00, 0xB2, record_num, p2, 0x00]
                            
                            response, sw1, sw2 = connection.transmit(read_record)
                            
                            # Log APDU
                            apdu_log.append({
                                'command': f"READ RECORD AFL SFI{sfi}.{record_num}",
                                'command_hex': ' '.join(f'{b:02X}' for b in read_record),
                                'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                                'status': f'{sw1:02X}{sw2:02X}',
                                'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                                'timestamp': 'N/A',
                                'description': f'Read AFL record SFI {sfi}, record {record_num}'
                            })
                            
                            if sw1 == 0x90 and sw2 == 0x00:
                                self._parse_record_response(response, card_data)
                                
                        except Exception as e:
                            self.logger.debug(f"Failed to read AFL record SFI{sfi}.{record_num}: {e}")
                            
        except Exception as e:
            self.logger.debug(f"AFL record reading failed: {e}")
    
    def _try_generate_arqc(self, connection, card_data: Dict[str, Any], apdu_log: List[Dict]):
        """Try to generate ARQC (Authorization Request Cryptogram)"""
        try:
            # GENERATE AC command to request ARQC
            # P1=80 for ARQC, P1=40 for TC
            for p1, crypto_type in [(0x80, "ARQC"), (0x40, "TC")]:
                try:
                    # Basic CDOL data for GENERATE AC
                    cdol_data = bytes([
                        0x9F, 0x02, 0x06, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00,  # Amount
                        0x9F, 0x03, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Other Amount
                        0x9F, 0x1A, 0x02, 0x08, 0x40,  # Terminal Country Code
                        0x95, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00,  # TVR
                        0x5F, 0x2A, 0x02, 0x08, 0x40,  # Currency Code
                        0x9A, 0x03, 0x25, 0x08, 0x21,  # Transaction Date
                        0x9C, 0x01, 0x00  # Transaction Type
                    ])
                    
                    generate_ac = [0x80, 0xAE, p1, 0x00, len(cdol_data)] + list(cdol_data)
                    response, sw1, sw2 = connection.transmit(generate_ac)
                    
                    # Log APDU
                    apdu_log.append({
                        'command': f"GENERATE AC ({crypto_type})",
                        'command_hex': ' '.join(f'{b:02X}' for b in generate_ac),
                        'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                        'status': f'{sw1:02X}{sw2:02X}',
                        'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                        'timestamp': 'N/A',
                        'description': f'Generate Application Cryptogram: {crypto_type}'
                    })
                    
                    if sw1 == 0x90 and sw2 == 0x00 and response:
                        # Parse response for cryptogram
                        response_hex = ''.join(f'{b:02X}' for b in response)
                        tlv_data = self._parse_tlv_simple(response_hex)
                        card_data['tlv_data'].update(tlv_data)
                        
                        # Store cryptogram type specific data
                        if crypto_type == "ARQC":
                            card_data['arqc_data'].update(tlv_data)
                        else:
                            card_data['tc_data'].update(tlv_data)
                            
                        self.logger.info(f"Successfully generated {crypto_type}")
                        
                except Exception as e:
                    self.logger.debug(f"GENERATE AC ({crypto_type}) failed: {e}")
                    
        except Exception as e:
            self.logger.debug(f"ARQC generation failed: {e}")
    
    def _extract_cryptogram_data(self, card_data: Dict[str, Any]):
        """Extract and organize cryptogram-related data"""
        try:
            tlv_data = card_data.get('tlv_data', {})
            
            # Application Cryptogram (9F26)
            if '9F26' in tlv_data:
                cryptogram = tlv_data['9F26']
                card_data['application_cryptogram'] = cryptogram.hex().upper() if isinstance(cryptogram, bytes) else str(cryptogram)
                
            # Cryptogram Information Data (9F27)
            if '9F27' in tlv_data:
                cid = tlv_data['9F27']
                card_data['cid'] = cid.hex().upper() if isinstance(cid, bytes) else str(cid)
                
                # Parse CID to determine cryptogram type
                if isinstance(cid, bytes) and len(cid) > 0:
                    cid_byte = cid[0]
                    crypto_type = "Unknown"
                    if (cid_byte & 0xC0) == 0x80:
                        crypto_type = "ARQC"
                    elif (cid_byte & 0xC0) == 0x40:
                        crypto_type = "TC"
                    elif (cid_byte & 0xC0) == 0x00:
                        crypto_type = "AAC"
                    card_data['cryptogram_type'] = crypto_type
                
            # Application Transaction Counter (9F36)
            if '9F36' in tlv_data:
                atc = tlv_data['9F36']
                card_data['atc'] = atc.hex().upper() if isinstance(atc, bytes) else str(atc)
                
            # Last Online ATC Register (9F13)
            if '9F13' in tlv_data:
                last_online_atc = tlv_data['9F13']
                card_data['last_online_atc'] = last_online_atc.hex().upper() if isinstance(last_online_atc, bytes) else str(last_online_atc)
                
        except Exception as e:
            self.logger.debug(f"Cryptogram data extraction failed: {e}")
    
    def _merge_all_applications(self, all_applications: Dict[str, Dict], apdu_log: List[Dict]) -> Dict[str, Any]:
        """Merge data from all applications into comprehensive card data"""
        try:
            merged_data = {
                'applications': all_applications,
                'apdu_log': apdu_log,
                'tlv_data': {},
                'track_data': {},
                'cryptographic_data': {},
                'all_pans': [],
                'all_expiry_dates': [],
                'all_cardholder_names': []
            }
            
            # Find the best PAN, expiry, and cardholder name from all applications
            best_pan = None
            best_expiry = None
            best_name = None
            
            for aid, app_data in all_applications.items():
                # Collect all TLV data
                if 'tlv_data' in app_data:
                    merged_data['tlv_data'].update(app_data['tlv_data'])
                    
                # Collect track data
                if 'track_data' in app_data:
                    merged_data['track_data'].update(app_data['track_data'])
                
                # Collect cryptographic data
                crypto_info = {}
                for key in ['application_cryptogram', 'cid', 'atc', 'cryptogram_type', 'arqc_data', 'tc_data']:
                    if key in app_data and app_data[key]:
                        crypto_info[key] = app_data[key]
                        
                if crypto_info:
                    merged_data['cryptographic_data'][aid] = crypto_info
                
                # Collect unique values
                if app_data.get('pan'):
                    if app_data['pan'] not in merged_data['all_pans']:
                        merged_data['all_pans'].append(app_data['pan'])
                    if not best_pan or len(app_data['pan']) == 16:  # Prefer 16-digit PANs
                        best_pan = app_data['pan']
                        
                if app_data.get('expiry_date'):
                    if app_data['expiry_date'] not in merged_data['all_expiry_dates']:
                        merged_data['all_expiry_dates'].append(app_data['expiry_date'])
                    if not best_expiry:
                        best_expiry = app_data['expiry_date']
                        
                if app_data.get('cardholder_name'):
                    if app_data['cardholder_name'] not in merged_data['all_cardholder_names']:
                        merged_data['all_cardholder_names'].append(app_data['cardholder_name'])
                    if not best_name:
                        best_name = app_data['cardholder_name']
            
            # Set primary values
            merged_data['pan'] = best_pan
            merged_data['expiry_date'] = best_expiry
            merged_data['cardholder_name'] = best_name
            
            # Determine overall card type
            if all_applications:
                first_app = next(iter(all_applications.values()))
                merged_data['card_type'] = first_app.get('card_type', 'Unknown')
                merged_data['aid'] = first_app.get('aid', 'N/A')
                merged_data['application_label'] = first_app.get('application_label', 'N/A')
            
            self.logger.info(f"Merged data from {len(all_applications)} applications")
            self.logger.info(f"Found {len(merged_data['all_pans'])} unique PANs")
            self.logger.info(f"Cryptographic data available for {len(merged_data['cryptographic_data'])} applications")
            
            return merged_data
            
        except Exception as e:
            self.logger.error(f"Application data merging failed: {e}")
            return {}

# Factory function for easy use
def parse_emv_card(connection=None) -> Optional[Dict[str, Any]]:
    """
    Parse EMV card data using the universal parser
    
    Args:
        connection: Optional existing smartcard connection
        
    Returns:
        Dictionary with card data or None if failed
    """
    parser = UniversalEMVParser()
    return parser.parse_card(connection)

if __name__ == "__main__":
    # Test the parser
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Universal EMV Parser")
    print("=" * 40)
    
    card_data = parse_emv_card()
    if card_data:
        print("🎉 Card data extracted successfully!")
        for key, value in card_data.items():
            print(f"{key}: {value}")
    else:
        print("❌ Failed to extract card data")
