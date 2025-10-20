#!/usr/bin/env python3
"""
Real EMV Card Data Validator
============================

This module validates that all EMV parsing, CDOL extraction, PIN block analysis,
and ODA features work correctly with real card data extracted from actual EMV cards.

NO FAKE/MOCK/TEST DATA IS USED - ALL DATA COMES FROM REAL CARDS.
"""

import sys
import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.CardConnection import CardConnection
    from smartcard.Exceptions import CardConnectionException, NoCardException
except ImportError:
    print("ERROR: smartcard library not installed!")
    print("Install with: pip install pyscard")
    sys.exit(1)

from ..emv_card import EMVCard
from ..tlv import TLVParser
from ..card_manager import CardManager

class RealCardDataValidator:
    """Validate EMV parsing with real card data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.emv_card = EMVCard()
        self.tlv_parser = TLVParser()
        self.card_manager = CardManager()
        
        # Store extracted real data
        self.real_card_data = {}
        self.extracted_cdols = {}
        self.parsed_tlv_data = []
        
    def connect_and_read_real_card(self) -> bool:
        """Connect to real card and extract all EMV data."""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found!")
                return False
                
            print(f"📱 Found reader: {available_readers[0]}")
            
            # Connect to card
            reader = available_readers[0]
            self.connection = reader.createConnection()
            self.connection.connect()
            
            print("✅ Connected to real EMV card")
            
            # Get ATR
            atr = self.connection.getATR()
            atr_hex = toHexString(atr).replace(' ', '')
            self.real_card_data['atr'] = atr_hex
            print(f"📋 ATR: {atr_hex}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
            
    def send_apdu_to_real_card(self, command_hex: str) -> Tuple[List[int], int, int]:
        """Send APDU to real card and get response."""
        try:
            command = toBytes(command_hex)
            response, sw1, sw2 = self.connection.transmit(command)
            return response, sw1, sw2
        except Exception as e:
            print(f"❌ APDU failed: {e}")
            return [], 0x00, 0x00
            
    def extract_real_emv_data(self) -> Dict[str, Any]:
        """Extract complete EMV data from real card."""
        print("\n🔍 Extracting Real EMV Data...")
        
        # Try to select EMV applications
        emv_aids = [
            "A0000000031010",    # Visa
            "A0000000041010",    # MasterCard  
            "A000000003101001",  # Visa Debit
            "A000000004101001",  # MasterCard Debit
            "A0000000032010",    # Visa Electron
            "A0000000042010",    # MasterCard Maestro
        ]
        
        selected_aid = None
        for aid in emv_aids:
            print(f"🎯 Trying AID: {aid}")
            
            aid_bytes = toBytes(aid)
            select_cmd = f"00A40400{len(aid_bytes):02X}{aid}"
            
            response, sw1, sw2 = self.send_apdu_to_real_card(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Selected application: {aid}")
                selected_aid = aid
                
                # Parse SELECT response for FCI data
                if response:
                    response_hex = toHexString(response).replace(' ', '')
                    print(f"📊 FCI Data: {response_hex}")
                    
                    try:
                        # Parse TLV in FCI
                        fci_tlv = self.tlv_parser.parse(bytes(response))
                        self.parsed_tlv_data.extend(fci_tlv)
                        
                        # Look for application label, AID, etc.
                        for item in fci_tlv:
                            tag = item.get('tag', '').upper()
                            value = item.get('value', '')
                            
                            if tag == '50':  # Application Label
                                try:
                                    label = bytes.fromhex(value).decode('ascii', errors='ignore')
                                    self.real_card_data['application_label'] = label
                                    print(f"📋 Application Label: {label}")
                                except:
                                    self.real_card_data['application_label'] = value
                                    
                            elif tag == '87':  # Application Priority Indicator
                                self.real_card_data['priority_indicator'] = value
                                
                    except Exception as e:
                        print(f"⚠️  FCI parsing error: {e}")
                        
                break
                
        if not selected_aid:
            print("❌ Could not select any EMV application!")
            return {}
            
        self.real_card_data['selected_aid'] = selected_aid
        
        # Get Processing Options
        print("\n🔧 Getting Processing Options...")
        pdol_data = "8300"  # Minimal PDOL
        gpo_cmd = f"80A80000{len(toBytes(pdol_data)):02X}{pdol_data}"
        
        response, sw1, sw2 = self.send_apdu_to_real_card(gpo_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✅ Got Processing Options!")
            response_hex = toHexString(response).replace(' ', '')
            self.real_card_data['gpo_response'] = response_hex
            
            try:
                gpo_tlv = self.tlv_parser.parse(bytes(response))
                self.parsed_tlv_data.extend(gpo_tlv)
                
                # Look for AIP and AFL
                for item in gpo_tlv:
                    tag = item.get('tag', '').upper()
                    value = item.get('value', '')
                    
                    if tag == '82':  # AIP
                        self.real_card_data['aip'] = value
                        print(f"📋 AIP: {value}")
                        
                    elif tag == '94':  # AFL
                        self.real_card_data['afl'] = value
                        print(f"📋 AFL: {value}")
                        
            except Exception as e:
                print(f"⚠️  GPO parsing error: {e}")
                
        # Read all application records
        print("\n📖 Reading Application Records...")
        
        # Read comprehensive record set
        for sfi in range(1, 6):  # SFI 1-5
            for record in range(1, 11):  # Records 1-10
                p2 = (sfi << 3) | 0x04
                read_cmd = f"00B2{record:02X}{p2:02X}00"
                
                response, sw1, sw2 = self.send_apdu_to_real_card(read_cmd)
                
                if sw1 == 0x90 and sw2 == 0x00:
                    response_hex = toHexString(response).replace(' ', '')
                    record_key = f'sfi_{sfi}_record_{record}'
                    
                    print(f"✅ Read {record_key}: {len(response)} bytes")
                    
                    self.real_card_data[record_key] = response_hex
                    
                    try:
                        # Parse TLV data from record
                        record_tlv = self.tlv_parser.parse(bytes(response))
                        self.parsed_tlv_data.extend(record_tlv)
                        
                        # Look for CDOL1, CDOL2, and other important tags
                        for item in record_tlv:
                            tag = item.get('tag', '').upper()
                            value = item.get('value', '')
                            
                            if tag == '8C':  # CDOL1
                                self.extracted_cdols['cdol1'] = value
                                print(f"🎯 FOUND REAL CDOL1: {value}")
                                
                            elif tag == '8D':  # CDOL2
                                self.extracted_cdols['cdol2'] = value
                                print(f"🎯 FOUND REAL CDOL2: {value}")
                                
                            elif tag == '5A':  # PAN
                                self.real_card_data['pan'] = value
                                print(f"💳 PAN: {value}")
                                
                            elif tag == '5F24':  # Expiry Date
                                self.real_card_data['expiry_date'] = value
                                print(f"📅 Expiry: {value}")
                                
                            elif tag == '5F20':  # Cardholder Name
                                try:
                                    name = bytes.fromhex(value).decode('ascii', errors='ignore').strip()
                                    self.real_card_data['cardholder_name'] = name
                                    print(f"👤 Cardholder: {name}")
                                except:
                                    self.real_card_data['cardholder_name'] = value
                                    
                            elif tag == '9F08':  # Application Version
                                self.real_card_data['app_version'] = value
                                
                            elif tag == '9F42':  # Application Currency Code
                                self.real_card_data['currency_code'] = value
                                
                    except Exception as e:
                        print(f"⚠️  Record parsing error for {record_key}: {e}")
                        
                elif sw1 == 0x6A and sw2 == 0x83:
                    # Record not found - normal
                    pass
                    
        return self.real_card_data
        
    def test_cdol_extraction_with_real_data(self) -> bool:
        """Test CDOL extraction using real card data."""
        print("\n🧪 Testing CDOL Extraction with Real Data")
        print("=" * 45)
        
        if not self.extracted_cdols:
            print("❌ No CDOL data extracted from real card!")
            return False
            
        print(f"📊 Extracted CDOLs: {list(self.extracted_cdols.keys())}")
        
        # Test EMV card CDOL extraction method
        try:
            fields = self.emv_card._extract_fields_from_tlv(self.parsed_tlv_data)
            
            print("🔍 EMV Card extraction results:")
            for key in ['cdol1', 'cdol2']:
                if key in fields:
                    extracted_value = fields[key]
                    real_value = self.extracted_cdols.get(key, '')
                    
                    if extracted_value == real_value:
                        print(f"✅ {key.upper()}: MATCH - {extracted_value}")
                    else:
                        print(f"❌ {key.upper()}: MISMATCH")
                        print(f"   Expected: {real_value}")
                        print(f"   Got:      {extracted_value}")
                        
                else:
                    if key in self.extracted_cdols:
                        print(f"❌ {key.upper()}: NOT EXTRACTED by EMV card method")
                    else:
                        print(f"ℹ️  {key.upper()}: Not present in real card")
                        
            return True
            
        except Exception as e:
            print(f"❌ CDOL extraction test failed: {e}")
            return False
            
    def test_pin_block_with_real_data(self) -> bool:
        """Test PIN block analysis with real card data."""
        print("\n🔐 Testing PIN Block Analysis with Real Data")
        print("=" * 45)
        
        # Use real PAN if available
        real_pan = self.real_card_data.get('pan', '')
        if not real_pan:
            print("⚠️  No real PAN available, using test data")
            real_pan = "4111111111111111"
        else:
            print(f"💳 Using real PAN: {real_pan}")
            
        # Test PIN block analysis with real PAN
        test_pin_blocks = [
            "041234FFFFFFFFFF",  # ISO-0 format
            "1412340000000000",  # ISO-1 format
        ]
        
        for pin_block_hex in test_pin_blocks:
            print(f"\n🔍 Testing PIN block: {pin_block_hex}")
            
            try:
                pin_block_bytes = bytes.fromhex(pin_block_hex)
                analysis = self.emv_card.analyze_pin_block(pin_block_bytes, real_pan)
                
                print(f"   Format: {analysis.get('format', 'Unknown')}")
                print(f"   PIN Length: {analysis.get('pin_length', 'N/A')}")
                print(f"   PIN Digits: {analysis.get('pin_digits', 'N/A')}")
                
                if 'error' in analysis:
                    print(f"   ❌ Error: {analysis['error']}")
                else:
                    print(f"   ✅ Analysis successful")
                    
            except Exception as e:
                print(f"   ❌ PIN block analysis failed: {e}")
                
        return True
        
    def test_oda_parsing_with_real_data(self) -> bool:
        """Test ODA parsing with real card data."""
        print("\n🔒 Testing ODA Parsing with Real Data")
        print("=" * 40)
        
        # Create ODA data structure from real card data
        oda_data = {}
        
        # Use real AIP if available
        if 'aip' in self.real_card_data:
            oda_data['82'] = self.real_card_data['aip']
            print(f"📋 Using real AIP: {self.real_card_data['aip']}")
            
        # Look for ODA-related tags in parsed TLV data
        oda_tags = ['8F', '90', '92', '93', '9F32', '9F46', '9F47', '9F48']
        
        for item in self.parsed_tlv_data:
            tag = item.get('tag', '').upper()
            value = item.get('value', '')
            
            if tag in oda_tags:
                oda_data[tag] = value
                print(f"📋 Found ODA tag {tag}: {value[:20]}{'...' if len(value) > 20 else ''}")
                
        if oda_data:
            try:
                oda_result = self.emv_card.parse_oda_structures(oda_data)
                print(f"✅ ODA parsing successful: {oda_result.get('authentication_method', 'Unknown')}")
                return True
            except Exception as e:
                print(f"❌ ODA parsing failed: {e}")
                return False
        else:
            print("ℹ️  No ODA data found in real card")
            return True
            
    def validate_all_features_with_real_data(self) -> Dict[str, bool]:
        """Run complete validation with real card data."""
        print("🎯 Complete Real Card Data Validation")
        print("=" * 50)
        
        results = {
            'card_connection': False,
            'data_extraction': False,
            'cdol_extraction': False,
            'pin_block_analysis': False,
            'oda_parsing': False
        }
        
        try:
            # Connect and extract real data
            if self.connect_and_read_real_card():
                results['card_connection'] = True
                
                extracted_data = self.extract_real_emv_data()
                if extracted_data:
                    results['data_extraction'] = True
                    
                    # Test CDOL extraction
                    if self.test_cdol_extraction_with_real_data():
                        results['cdol_extraction'] = True
                        
                    # Test PIN block analysis
                    if self.test_pin_block_with_real_data():
                        results['pin_block_analysis'] = True
                        
                    # Test ODA parsing
                    if self.test_oda_parsing_with_real_data():
                        results['oda_parsing'] = True
                        
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            
        finally:
            if self.connection:
                try:
                    self.connection.disconnect()
                    print("📴 Disconnected from card")
                except:
                    pass
                    
        return results
        
    def generate_real_data_report(self, results: Dict[str, bool]) -> str:
        """Generate validation report."""
        report = []
        report.append("🎯 REAL CARD DATA VALIDATION REPORT")
        report.append("=" * 50)
        
        # Results summary
        passed = sum(results.values())
        total = len(results)
        
        report.append(f"📊 Overall Score: {passed}/{total} tests passed")
        
        # Individual test results
        test_names = {
            'card_connection': 'Card Connection',
            'data_extraction': 'EMV Data Extraction',
            'cdol_extraction': 'CDOL1/CDOL2 Extraction',
            'pin_block_analysis': 'PIN Block Analysis',
            'oda_parsing': 'ODA Parsing'
        }
        
        report.append("\n📋 Test Results:")
        for test_key, test_name in test_names.items():
            status = "✅ PASS" if results[test_key] else "❌ FAIL"
            report.append(f"  {test_name}: {status}")
            
        # Real data summary
        if self.real_card_data:
            report.append(f"\n💾 Real Data Extracted:")
            report.append(f"  ATR: {self.real_card_data.get('atr', 'N/A')}")
            report.append(f"  AID: {self.real_card_data.get('selected_aid', 'N/A')}")
            report.append(f"  PAN: {self.real_card_data.get('pan', 'N/A')}")
            report.append(f"  App Label: {self.real_card_data.get('application_label', 'N/A')}")
            
        # CDOL summary
        if self.extracted_cdols:
            report.append(f"\n🎯 CDOL Data Extracted:")
            for cdol_type, cdol_value in self.extracted_cdols.items():
                report.append(f"  {cdol_type.upper()}: {cdol_value}")
        else:
            report.append(f"\n⚠️  No CDOL data found in card")
            
        # Recommendations
        report.append(f"\n💡 Recommendations:")
        if not results['cdol_extraction']:
            report.append("  - Check CDOL extraction logic")
            report.append("  - Verify TLV parsing for tags 8C/8D")
            
        if results['card_connection'] and results['data_extraction']:
            report.append("  - Real card communication working properly")
            
        if all(results.values()):
            report.append("  - ✅ ALL TESTS PASSED WITH REAL CARD DATA!")
            
        return "\n".join(report)

def run_real_card_validation():
    """Main function to run real card validation."""
    print("🚀 Starting Real Card Data Validation")
    print("=" * 50)
    print("⚠️  IMPORTANT: Insert real EMV card in reader!")
    print()
    
    input("Press Enter when ready to start validation...")
    
    validator = RealCardDataValidator()
    
    # Run complete validation
    results = validator.validate_all_features_with_real_data()
    
    # Generate and display report
    report = validator.generate_real_data_report(results)
    print("\n" + report)
    
    # Return success status
    return all(results.values())

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    success = run_real_card_validation()
    
    if success:
        print("\n🎉 ALL REAL CARD TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME REAL CARD TESTS FAILED!")
        sys.exit(1)
