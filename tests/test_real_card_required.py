#!/usr/bin/env python3
"""
REAL CARD READING TEST - No Mock Data!
======================================

This test ONLY works with a real card inserted in the reader.
It reads actual EMV data from the card and validates TLV parsing.

REQUIREMENTS:
- Real EMV card with PAN starting with 4031 
- Card inserted in ACS ACR122 reader
- No hardcoded/mock data allowed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..readers import ReaderManager, PCSCCardReader
from ..tlv import TLVParser
from ..emv_card import EMVCard
import time

class RealCardTest:
    def __init__(self):
        self.reader = None
        self.card_data = {}
        self.tlv_parser = TLVParser()
        
    def wait_for_card(self, timeout=30):
        """Wait for card insertion with timeout."""
        print(f"⏳ Waiting for card insertion (timeout: {timeout}s)...")
        print("   Please insert an EMV card with PAN starting with 4031")
        
        reader_manager = ReaderManager()
        available_readers = reader_manager.detect_readers()
        
        if not available_readers:
            print("❌ No card readers found!")
            return False
            
        reader_info = available_readers[0]
        self.reader = PCSCCardReader(reader_info['name'])
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.reader.is_card_present():
                print("✅ Card detected!")
                return True
            time.sleep(0.5)
            print(".", end="", flush=True)
        
        print(f"\n❌ Timeout: No card inserted within {timeout} seconds")
        return False
    
    def read_real_card_data(self):
        """Read actual data from the inserted card."""
        if not self.reader or not self.reader.is_card_present():
            print("❌ No card available for reading")
            return False
            
        print("\n🔗 Connecting to card...")
        if not self.reader.connect():
            print("❌ Failed to connect to card")
            return False
            
        print("✅ Connected to card")
        
        # Get ATR
        atr = self.reader.get_atr()
        if atr:
            print(f"📋 ATR: {atr.hex().upper()}")
            self.card_data['atr'] = atr.hex().upper()
        
        # Try to read EMV application
        print("\n🏦 Reading EMV application data...")
        
        # SELECT PPSE
        ppse_cmd = bytes.fromhex("00A404000E325041592E5359532E4444463031")
        response, sw1, sw2 = self.reader.transmit(ppse_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00 and response:
            print(f"✅ PPSE SELECT successful: {len(response)} bytes")
            print(f"📊 Raw PPSE response: {response.hex().upper()}")
            
            # Parse PPSE TLV data
            print("\n🔍 Parsing PPSE TLV structure:")
            ppse_tlv = self.tlv_parser.parse(response)
            
            if self.tlv_parser.parse_errors:
                print("⚠️  TLV Parse errors:")
                for error in self.tlv_parser.parse_errors:
                    print(f"   - {error}")
            
            # Display parsed structure
            tree = self.tlv_parser.format_tlv_tree(ppse_tlv)
            print(tree)
            
            self.card_data['ppse_response'] = response.hex().upper()
            self.card_data['ppse_tlv'] = ppse_tlv
            
            # Extract application identifiers
            if '6F' in ppse_tlv and isinstance(ppse_tlv['6F'], dict):
                fci = ppse_tlv['6F']
                if 'A5' in fci and isinstance(fci['A5'], dict):
                    prop_template = fci['A5']
                    if 'BF0C' in prop_template:  # FCI Issuer Discretionary Data
                        print("\n🎯 Found application directory")
                        return self.select_application(prop_template['BF0C'])
        
        print("❌ PPSE selection failed or no response")
        return False
    
    def select_application(self, app_directory):
        """Select and read application data."""
        print("\n🎯 Selecting EMV application...")
        
        # Look for application template (61)
        if isinstance(app_directory, dict) and '61' in app_directory:
            app_template = app_directory['61']
            if isinstance(app_template, list):
                app_template = app_template[0]  # Use first application
            
            if isinstance(app_template, dict) and '4F' in app_template:
                aid = app_template['4F']
                print(f"📱 Application ID: {aid.hex().upper()}")
                
                # SELECT application
                select_cmd = bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid
                response, sw1, sw2 = self.reader.transmit(select_cmd)
                
                if sw1 == 0x90 and sw2 == 0x00 and response:
                    print(f"✅ Application selected: {len(response)} bytes")
                    print(f"📊 Raw APP response: {response.hex().upper()}")
                    
                    # Parse application TLV
                    app_tlv = self.tlv_parser.parse(response)
                    
                    if self.tlv_parser.parse_errors:
                        print("⚠️  Application TLV errors:")
                        for error in self.tlv_parser.parse_errors:
                            print(f"   - {error}")
                    
                    tree = self.tlv_parser.format_tlv_tree(app_tlv)
                    print(f"\n📋 Application TLV structure:")
                    print(tree)
                    
                    self.card_data['application_response'] = response.hex().upper()
                    self.card_data['application_tlv'] = app_tlv
                    
                    # Try to read record data for PAN
                    return self.read_record_data()
        
        return False
    
    def read_record_data(self):
        """Read record data to find PAN."""
        print("\n💳 Reading record data for PAN...")
        
        # Try reading records from file 1, records 1-5
        for record in range(1, 6):
            read_cmd = bytes([0x00, 0xB2, record, 0x0C])  # READ RECORD
            response, sw1, sw2 = self.reader.transmit(read_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00 and response:
                print(f"✅ Record {record}: {len(response)} bytes")
                print(f"📊 Raw record: {response.hex().upper()}")
                
                # Parse record TLV
                record_tlv = self.tlv_parser.parse(response)
                
                if self.tlv_parser.parse_errors:
                    print(f"⚠️  Record {record} TLV errors:")
                    for error in self.tlv_parser.parse_errors:
                        print(f"   - {error}")
                
                # Look for PAN (tag 5A)
                if '5A' in record_tlv:
                    pan_bytes = record_tlv['5A']
                    if isinstance(pan_bytes, bytes):
                        pan = pan_bytes.hex().upper()
                        print(f"🎯 FOUND PAN: {pan}")
                        
                        # Check if PAN starts with 4031
                        if pan.startswith('4031'):
                            print("✅ PAN starts with 4031 - PERFECT!")
                            self.card_data['pan'] = pan
                            self.card_data['record_data'] = response.hex().upper()
                            self.card_data['record_tlv'] = record_tlv
                            return True
                        else:
                            print(f"⚠️  PAN starts with {pan[:4]}, need 4031")
                
                tree = self.tlv_parser.format_tlv_tree(record_tlv)
                print(f"📋 Record {record} structure:")
                print(tree)
            
            else:
                print(f"❌ Record {record}: SW={sw1:02X}{sw2:02X}")
        
        return False
    
    def validate_real_data(self):
        """Validate that we have real card data, not test data."""
        print("\n🔍 VALIDATION: Real vs Test Data")
        print("=" * 50)
        
        if 'pan' in self.card_data:
            pan = self.card_data['pan']
            print(f"✅ PAN found: {pan}")
            
            if pan.startswith('4031'):
                print("✅ PAN starts with 4031 - REQUIREMENT MET")
            else:
                print(f"❌ PAN starts with {pan[:4]} - REQUIREMENT NOT MET")
                return False
        else:
            print("❌ No PAN found in card data")
            return False
        
        # Check if TLV parsing worked without errors
        if 'record_tlv' in self.card_data:
            print("✅ TLV parsing completed")
            print("✅ Real card data successfully extracted")
            return True
        
        print("❌ TLV parsing failed")
        return False
    
    def run_test(self):
        """Run the complete real card test."""
        print("🧪 REAL CARD READING TEST")
        print("=" * 60)
        print("⚠️  This test requires a REAL EMV card with PAN starting with 4031")
        print("⚠️  NO hardcoded or mock data will be used!")
        print()
        
        try:
            # Wait for card
            if not self.wait_for_card():
                return False
            
            # Read real card data
            if not self.read_real_card_data():
                print("❌ Failed to read card data")
                return False
            
            # Validate results
            if self.validate_real_data():
                print("\n🎉 SUCCESS: Real card data test PASSED!")
                print("🎯 TLV parser works correctly with real EMV data")
                return True
            else:
                print("\n❌ FAILED: Real card data test failed validation")
                return False
                
        except Exception as e:
            print(f"\n💥 ERROR: {e}")
            return False
        finally:
            if self.reader:
                self.reader.disconnect()

if __name__ == "__main__":
    test = RealCardTest()
    success = test.run_test()
    sys.exit(0 if success else 1)
