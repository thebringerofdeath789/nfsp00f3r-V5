#!/usr/bin/env python3
"""
EMV Terminal Emulator - Full Transaction Flow
Emulates a proper EMV terminal to extract cryptograms, ARQC/TC, and all transaction data
"""

import logging
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from smartcard.System import readers as pcsc_readers
from smartcard.util import toHexString
from datetime import datetime


class EMVTerminalEmulator:
    """EMV Terminal Emulator for complete transaction processing"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Terminal capabilities and configuration
        self.terminal_capabilities = {
            'terminal_type': 0x22,  # Attended, online capable
            'transaction_capabilities': 0xE0A8C8,  # CVM, SDA, DDA, CDA, etc.
            'additional_capabilities': 0xFF8000,  # Full capabilities
        }
        
        # Transaction parameters
        self.transaction_data = {
            'amount': 100,  # $1.00 in cents
            'currency_code': 0x0840,  # USD
            'transaction_date': datetime.now().strftime('%y%m%d'),
            'transaction_time': datetime.now().strftime('%H%M%S'),
            'unpredictable_number': random.randint(0x10000000, 0xFFFFFFFF),
        }
    
    def emulate_full_transaction(self, connection=None) -> Dict[str, Any]:
        """
        Emulate a complete EMV transaction to extract all possible data
        including cryptograms, ARQC/TC, and comprehensive EMV data
        """
        transaction_data = {
            'applications': {},
            'all_cryptograms': [],
            'terminal_data': {},
            'apdu_log': [],
            'transaction_results': {}
        }
        
        try:
            # Create connection if not provided
            if connection is None:
                connection = self._create_connection()
                if not connection:
                    self.logger.error("Failed to create card connection for terminal emulation")
                    return transaction_data
            # Step 1: Build Candidate List (discover all applications)
            applications = self._build_candidate_list(connection, transaction_data['apdu_log'])
            
            # Step 2: Process each application with full terminal emulation
            for aid_hex, app_info in applications.items():
                self.logger.info(f"Processing application: {app_info['name']} ({aid_hex})")
                
                app_data = self._process_application_full(
                    connection, aid_hex, app_info, transaction_data['apdu_log']
                )
                
                if app_data:
                    transaction_data['applications'][aid_hex] = app_data
                    
                    # Collect cryptograms from this application
                    if 'cryptograms' in app_data:
                        transaction_data['all_cryptograms'].extend(app_data['cryptograms'])
            
            # Step 3: Terminal risk management and final processing
            transaction_data['terminal_data'] = self._get_terminal_data()
            transaction_data['transaction_results'] = self._finalize_transaction_results(transaction_data)
            
            return transaction_data
            
        except Exception as e:
            self.logger.error(f"Terminal emulation failed: {e}")
            return transaction_data
    
    def _build_candidate_list(self, connection, apdu_log: List[Dict]) -> Dict[str, Dict]:
        """Build complete candidate list of all applications on card"""
        applications = {}
        
        # Try PPSE first
        ppse_apps = self._discover_ppse_applications(connection, apdu_log)
        applications.update(ppse_apps)
        
        # Try all known AIDs regardless of PPSE results
        known_aids = [
            # Visa variants
            ("A0000000031010", "Visa Credit/Debit"),
            ("A0000000032010", "Visa Credit/Debit International"),
            ("A0000000033010", "Visa Interlink"),
            ("A0000000041010", "Visa Credit/Debit"),
            ("A0000000043060", "Visa Electron"),
            ("A00000000980", "Visa Common Debit"),
            
            # Mastercard variants  
            ("A0000000041010", "Mastercard Credit/Debit"),
            ("A0000000042010", "Mastercard Credit"),
            ("A0000000043010", "Mastercard Debit"),
            ("A0000000044010", "Mastercard Enhanced"),
            ("A0000000050001", "Mastercard Maestro"),
            
            # American Express
            ("A000000025010701", "American Express"),
            ("A000000025010801", "American Express Blue"),
            ("A0000000250105", "American Express Corporate"),
            
            # Discover
            ("A0000001523010", "Discover Card"),
            ("A0000003241010", "Discover Card"),
            
            # Other major brands
            ("A0000001544442", "Bancontact/Mister Cash"),
            ("A0000000651010", "JCB Credit"),
            ("A0000000980840", "Visa Common Debit AID"),
        ]
        
        for aid_hex, name in known_aids:
            if aid_hex not in applications:
                if self._test_aid_selection(connection, aid_hex, apdu_log):
                    applications[aid_hex] = {
                        'name': name,
                        'priority': 1,
                        'source': 'direct_test'
                    }
        
        return applications
    
    def _discover_ppse_applications(self, connection, apdu_log: List[Dict]) -> Dict[str, Dict]:
        """Discover applications via PPSE"""
        applications = {}
        
        # Try PPSE selection
        ppse_names = ["2PAY.SYS.DDF01", "1PAY.SYS.DDF01"]
        
        for ppse_name in ppse_names:
            try:
                ppse_bytes = ppse_name.encode('ascii')
                select_ppse = [0x00, 0xA4, 0x04, 0x00, len(ppse_bytes)] + list(ppse_bytes)
                
                response, sw1, sw2 = connection.transmit(select_ppse)
                
                apdu_log.append({
                    'command': f"SELECT PPSE ({ppse_name})",
                    'command_hex': ' '.join(f'{b:02X}' for b in select_ppse),
                    'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                    'status': f'{sw1:02X}{sw2:02X}',
                    'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                    'timestamp': datetime.now().isoformat(),
                    'description': f'Select Payment System Environment ({ppse_name})'
                })
                
                if sw1 == 0x90 and sw2 == 0x00 and response:
                    # Parse PPSE response for application entries
                    parsed_apps = self._parse_ppse_response(response)
                    applications.update(parsed_apps)
                    break
                    
            except Exception as e:
                self.logger.debug(f"PPSE {ppse_name} failed: {e}")
        
        return applications
    
    def _test_aid_selection(self, connection, aid_hex: str, apdu_log: List[Dict]) -> bool:
        """Test if AID can be selected"""
        try:
            aid_bytes = bytes.fromhex(aid_hex)
            select_aid = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            
            response, sw1, sw2 = connection.transmit(select_aid)
            
            apdu_log.append({
                'command': f"TEST AID {aid_hex}",
                'command_hex': ' '.join(f'{b:02X}' for b in select_aid),
                'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                'status': f'{sw1:02X}{sw2:02X}',
                'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                'timestamp': datetime.now().isoformat(),
                'description': f'Test AID selection: {aid_hex}'
            })
            
            return sw1 == 0x90 and sw2 == 0x00
            
        except Exception as e:
            self.logger.debug(f"AID test {aid_hex} failed: {e}")
            return False
    
    def _process_application_full(self, connection, aid_hex: str, app_info: Dict, apdu_log: List[Dict]) -> Optional[Dict]:
        """Process application with full EMV terminal emulation"""
        try:
            # Select the application
            if not self._select_application_for_processing(connection, aid_hex, apdu_log):
                return None
            
            app_data = {
                'aid': aid_hex,
                'name': app_info['name'],
                'tlv_data': {},
                'cryptograms': [],
                'transaction_data': {},
                'processing_options': {},
                'records': {},
                'authentication_results': {}
            }
            
            # Step 1: Get Processing Options (GPO) with proper terminal emulation
            gpo_result = self._perform_gpo_with_terminal_emulation(connection, app_data, apdu_log)
            
            if gpo_result:
                app_data['processing_options'] = gpo_result
                
                # Step 2: Read Application Data (all available records)
                self._read_all_application_records(connection, app_data, apdu_log)
                
                # Step 3: Offline Data Authentication
                self._perform_offline_data_authentication(connection, app_data, apdu_log)
                
                # Step 4: Processing Restrictions
                self._check_processing_restrictions(connection, app_data, apdu_log)
                
                # Step 5: Cardholder Verification
                self._perform_cardholder_verification(connection, app_data, apdu_log)
                
                # Step 6: Terminal Risk Management
                self._perform_terminal_risk_management(connection, app_data, apdu_log)
                
                # Step 7: Terminal Action Analysis
                self._perform_terminal_action_analysis(connection, app_data, apdu_log)
                
                # Step 8: Card Action Analysis (Generate ARQC/TC/AAC)
                self._perform_card_action_analysis(connection, app_data, apdu_log)
                
                # Step 9: Online Processing (if ARQC generated)
                self._perform_online_processing(connection, app_data, apdu_log)
                
                # Step 10: Completion (Generate TC/AAC)
                self._perform_completion_processing(connection, app_data, apdu_log)
            
            return app_data
            
        except Exception as e:
            self.logger.error(f"Application processing failed for {aid_hex}: {e}")
            return None
    
    def _select_application_for_processing(self, connection, aid_hex: str, apdu_log: List[Dict]) -> bool:
        """Select application for processing"""
        try:
            aid_bytes = bytes.fromhex(aid_hex)
            select_aid = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            
            response, sw1, sw2 = connection.transmit(select_aid)
            
            apdu_log.append({
                'command': f"SELECT AID {aid_hex}",
                'command_hex': ' '.join(f'{b:02X}' for b in select_aid),
                'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                'status': f'{sw1:02X}{sw2:02X}',
                'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                'timestamp': datetime.now().isoformat(),
                'description': f'Select application for processing: {aid_hex}'
            })
            
            return sw1 == 0x90 and sw2 == 0x00
            
        except Exception as e:
            self.logger.debug(f"Application selection failed: {e}")
            return False
    
    def _perform_gpo_with_terminal_emulation(self, connection, app_data: Dict, apdu_log: List[Dict]) -> Optional[Dict]:
        """Perform GPO (Get Processing Options) with proper terminal data"""
        
        # Build comprehensive PDOL data
        pdol_data = self._build_comprehensive_pdol_data()
        
        # Try different GPO variants with increasing complexity
        gpo_variants = [
            # Empty PDOL
            bytes([0x83, 0x00]),
            
            # Basic transaction data
            bytes([0x83, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x01, 0x56]),
            
            # Full terminal data
            pdol_data,
        ]
        
        for i, pdol in enumerate(gpo_variants):
            try:
                gpo_command = [0x80, 0xA8, 0x00, 0x00, len(pdol)] + list(pdol)
                response, sw1, sw2 = connection.transmit(gpo_command)
                
                apdu_log.append({
                    'command': f"GPO (variant {i+1})",
                    'command_hex': ' '.join(f'{b:02X}' for b in gpo_command),
                    'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                    'status': f'{sw1:02X}{sw2:02X}',
                    'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                    'timestamp': datetime.now().isoformat(),
                    'description': f'Get Processing Options (variant {i+1})'
                })
                
                if sw1 == 0x90 and sw2 == 0x00:
                    return self._parse_gpo_response(response)
                    
            except Exception as e:
                self.logger.debug(f"GPO variant {i+1} failed: {e}")
        
        return None
    
    def _build_comprehensive_pdol_data(self) -> bytes:
        """Build comprehensive PDOL data for terminal emulation"""
        pdol_data = bytearray([0x83])  # PDOL tag
        
        # Terminal data for PDOL
        terminal_data = bytearray()
        
        # Amount, Authorized (9F02)
        terminal_data.extend(self.transaction_data['amount'].to_bytes(6, 'big'))
        
        # Amount, Other (9F03) 
        terminal_data.extend(b'\x00\x00\x00\x00\x00\x00')
        
        # Terminal Country Code (9F1A)
        terminal_data.extend(b'\x08\x40')  # USA
        
        # Transaction Currency Code (5F2A)
        terminal_data.extend(self.transaction_data['currency_code'].to_bytes(2, 'big'))
        
        # Transaction Date (9A)
        terminal_data.extend(bytes.fromhex(self.transaction_data['transaction_date']))
        
        # Transaction Type (9C)
        terminal_data.extend(b'\x00')  # Purchase
        
        # Unpredictable Number (9F37)
        terminal_data.extend(self.transaction_data['unpredictable_number'].to_bytes(4, 'big'))
        
        # Terminal Capabilities (9F33)
        terminal_data.extend(self.terminal_capabilities['transaction_capabilities'].to_bytes(3, 'big'))
        
        # Additional Terminal Capabilities (9F40)
        terminal_data.extend(self.terminal_capabilities['additional_capabilities'].to_bytes(5, 'big'))
        
        # Terminal Type (9F35)
        terminal_data.extend(bytes([self.terminal_capabilities['terminal_type']]))
        
        # Transaction Time (9F21)
        terminal_data.extend(bytes.fromhex(self.transaction_data['transaction_time']))
        
        pdol_data.append(len(terminal_data))
        pdol_data.extend(terminal_data)
        
        return bytes(pdol_data)
    
    def _perform_card_action_analysis(self, connection, app_data: Dict, apdu_log: List[Dict]):
        """Perform Card Action Analysis to generate ARQC/TC"""
        
        # Generate Application Cryptogram (GENERATE AC)
        # Try different P1 values: AAC (00), TC (40), ARQC (80)
        
        for ac_type, ac_name in [(0x80, "ARQC"), (0x40, "TC"), (0x00, "AAC")]:
            try:
                # Build CDOL1 data for Generate AC
                cdol1_data = self._build_cdol1_data()
                
                gen_ac_command = [0x80, 0xAE, ac_type, 0x00, len(cdol1_data)] + list(cdol1_data)
                response, sw1, sw2 = connection.transmit(gen_ac_command)
                
                apdu_log.append({
                    'command': f"GENERATE AC ({ac_name})",
                    'command_hex': ' '.join(f'{b:02X}' for b in gen_ac_command),
                    'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                    'status': f'{sw1:02X}{sw2:02X}',
                    'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                    'timestamp': datetime.now().isoformat(),
                    'description': f'Generate {ac_name} - Card Action Analysis'
                })
                
                if sw1 == 0x90 and sw2 == 0x00 and response:
                    # Parse cryptogram response
                    cryptogram_data = self._parse_cryptogram_response(response, ac_name)
                    if cryptogram_data:
                        app_data['cryptograms'].append(cryptogram_data)
                        self.logger.info(f"Generated {ac_name}: {cryptogram_data.get('cryptogram', 'N/A')}")
                
            except Exception as e:
                self.logger.debug(f"Generate AC {ac_name} failed: {e}")
    
    def _build_cdol1_data(self) -> bytes:
        """Build CDOL1 data for Generate AC command"""
        cdol1_data = bytearray()
        
        # Amount, Authorized (9F02)
        cdol1_data.extend(self.transaction_data['amount'].to_bytes(6, 'big'))
        
        # Amount, Other (9F03)
        cdol1_data.extend(b'\x00\x00\x00\x00\x00\x00')
        
        # Terminal Country Code (9F1A)
        cdol1_data.extend(b'\x08\x40')  # USA
        
        # Terminal Verification Results (95)
        cdol1_data.extend(b'\x80\x00\x00\x00\x00')  # Default TVR
        
        # Transaction Currency Code (5F2A)
        cdol1_data.extend(self.transaction_data['currency_code'].to_bytes(2, 'big'))
        
        # Transaction Date (9A)
        cdol1_data.extend(bytes.fromhex(self.transaction_data['transaction_date']))
        
        # Transaction Type (9C)
        cdol1_data.extend(b'\x00')  # Purchase
        
        # Unpredictable Number (9F37)
        cdol1_data.extend(self.transaction_data['unpredictable_number'].to_bytes(4, 'big'))
        
        return bytes(cdol1_data)
    
    def _parse_cryptogram_response(self, response: List[int], ac_type: str) -> Optional[Dict]:
        """Parse Generate AC response for cryptogram data"""
        try:
            response_hex = ''.join(f'{b:02X}' for b in response)
            
            # Look for Format 1 or Format 2 response
            if len(response) >= 8:
                # Extract Application Cryptogram (usually first 8 bytes)
                cryptogram = response_hex[:16]  # First 8 bytes
                
                # Extract CID (Cryptogram Information Data) if available
                cid = None
                if len(response) > 8:
                    cid = f"{response[8]:02X}"
                
                # Extract ATC (Application Transaction Counter) if available  
                atc = None
                if len(response) > 10:
                    atc = ''.join(f'{response[i]:02X}' for i in range(9, 11))
                
                return {
                    'type': ac_type,
                    'cryptogram': cryptogram,
                    'cid': cid,
                    'atc': atc,
                    'raw_response': response_hex,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.debug(f"Cryptogram parsing failed: {e}")
        
        return None
    
    def _read_all_application_records(self, connection, app_data: Dict, apdu_log: List[Dict]):
        """Read all available application records"""
        
        # Try reading from common SFI/record combinations
        record_locations = []
        
        # Add AFL-based records if available from GPO
        if 'afl' in app_data.get('processing_options', {}):
            afl_records = self._parse_afl_records(app_data['processing_options']['afl'])
            record_locations.extend(afl_records)
        
        # Add common record locations for fallback
        common_locations = [
            (1, 1), (1, 2), (1, 3), (1, 4),
            (2, 1), (2, 2), (2, 3), (2, 4), (2, 5),
            (3, 1), (3, 2), (3, 3), (3, 4),
            (4, 1), (4, 2), (4, 3), (4, 4),
            (8, 1), (8, 2), (8, 3), (8, 4),
        ]
        
        for sfi, record in common_locations:
            if (sfi, record) not in record_locations:
                record_locations.append((sfi, record))
        
        # Read all records
        for sfi, record_num in record_locations:
            try:
                p2 = (sfi << 3) | 0x04
                read_record = [0x00, 0xB2, record_num, p2, 0x00]
                
                response, sw1, sw2 = connection.transmit(read_record)
                
                apdu_log.append({
                    'command': f"READ RECORD SFI{sfi}.{record_num}",
                    'command_hex': ' '.join(f'{b:02X}' for b in read_record),
                    'response_hex': ' '.join(f'{b:02X}' for b in response) if response else '',
                    'status': f'{sw1:02X}{sw2:02X}',
                    'sw1_sw2': f'{sw1:02X} {sw2:02X}',
                    'timestamp': datetime.now().isoformat(),
                    'description': f'Read record {record_num} from SFI {sfi}'
                })
                
                if sw1 == 0x90 and sw2 == 0x00 and response:
                    # Parse TLV data from record
                    record_tlv = self._parse_tlv_simple(''.join(f'{b:02X}' for b in response))
                    app_data['tlv_data'].update(record_tlv)
                    app_data['records'][f"SFI{sfi}_REC{record_num}"] = response
                    
            except Exception as e:
                self.logger.debug(f"Failed to read SFI{sfi}.{record_num}: {e}")
    
    def _parse_tlv_simple(self, hex_data: str) -> Dict[str, bytes]:
        """Simple TLV parser for EMV data"""
        tlv_data = {}
        i = 0
        
        while i < len(hex_data) - 2:
            try:
                # Get tag
                tag = hex_data[i:i+2]
                i += 2
                
                # Check for multi-byte tag
                if int(tag, 16) & 0x1F == 0x1F:
                    tag += hex_data[i:i+2]
                    i += 2
                
                # Get length
                if i >= len(hex_data):
                    break
                    
                length_byte = int(hex_data[i:i+2], 16)
                i += 2
                
                if length_byte & 0x80:
                    # Long form length
                    length_bytes = length_byte & 0x7F
                    if i + length_bytes * 2 > len(hex_data):
                        break
                    length = int(hex_data[i:i+length_bytes*2], 16)
                    i += length_bytes * 2
                else:
                    length = length_byte
                
                # Get value
                if i + length * 2 > len(hex_data):
                    break
                    
                value_hex = hex_data[i:i+length*2]
                value_bytes = bytes.fromhex(value_hex)
                tlv_data[tag] = value_bytes
                i += length * 2
                
            except Exception as e:
                self.logger.debug(f"TLV parsing error: {e}")
                break
                
        return tlv_data
    
    # Placeholder methods for other EMV processing steps
    def _parse_ppse_response(self, response): return {}
    def _parse_gpo_response(self, response): return {}
    def _parse_afl_records(self, afl): return []
    def _perform_offline_data_authentication(self, connection, app_data, apdu_log): pass
    def _check_processing_restrictions(self, connection, app_data, apdu_log): pass
    def _perform_cardholder_verification(self, connection, app_data, apdu_log): pass
    def _perform_terminal_risk_management(self, connection, app_data, apdu_log): pass
    def _perform_terminal_action_analysis(self, connection, app_data, apdu_log): pass
    def _perform_online_processing(self, connection, app_data, apdu_log): pass
    def _perform_completion_processing(self, connection, app_data, apdu_log): pass
    def _get_terminal_data(self): return {'terminal_type': 'EMV_EMULATOR'}
    def _finalize_transaction_results(self, data): return {'status': 'COMPLETE'}
    
    def _create_connection(self):
        """Create a new smartcard connection"""
        try:
            readers_list = pcsc_readers()
            if not readers_list:
                self.logger.error("No smartcard readers found")
                return None
            
            # Use first available reader
            reader = readers_list[0]
            connection = reader.createConnection()
            connection.connect()
            
            self.logger.info(f"Connected to card via reader: {reader}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create connection: {e}")
            return None


def create_emv_terminal_emulator():
    """Factory function to create EMV terminal emulator"""
    return EMVTerminalEmulator()
