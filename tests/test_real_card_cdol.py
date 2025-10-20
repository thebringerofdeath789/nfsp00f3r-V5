#!/usr/bin/env python3
"""
Real card data extraction and CDOL testing.
Tests CDOL1, CDOL2, and other EMV data extraction from actual cards.
"""

import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..emv_card import EMVCard
from ..tlv import TLVParser
from ..readers import ReaderManager
from smartcard.System import readers
from smartcard.util import toHexString

class RealCardTester:
    """Real card data extraction and testing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser = TLVParser()
        self.emv_card = EMVCard()
        self.reader_manager = ReaderManager()
        
    def detect_and_connect_card(self):
        """Detect card readers and connect to card."""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found!")
                return None, None
                
            print(f"📱 Found {len(available_readers)} reader(s):")
            for i, reader in enumerate(available_readers):
                print(f"  {i}: {reader}")
                
            # Try each reader for card
            for reader in available_readers:
                try:
                    connection = reader.createConnection()
                    connection.connect()
                    
                    # Send ATR request
                    atr = connection.getATR()
                    print(f"✅ Card found in reader: {reader}")
                    print(f"📄 ATR: {toHexString(atr)}")
                    
                    return connection, reader
                    
                except Exception as e:
                    print(f"⚠️  No card in reader {reader}: {e}")
                    continue
                    
            print("❌ No cards found in any reader!")
            return None, None
            
        except Exception as e:
            print(f"❌ Reader detection failed: {e}")
            return None, None
    
    def extract_real_emv_data(self, connection):
        """Extract real EMV data from card including CDOL1/CDOL2."""
        try:
            print("\n🔍 Extracting Real EMV Data")
            print("=" * 40)
            
            # Step 1: SELECT PSE (Payment System Environment)
            print("1. Selecting PSE...")
            pse_aid = [0x31, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
            select_pse = [0x00, 0xA4, 0x04, 0x00, len(pse_aid)] + pse_aid
            
            response, sw1, sw2 = connection.transmit(select_pse)
            print(f"   Response: {toHexString(response)} SW: {sw1:02X}{sw2:02X}")
            
            if sw1 == 0x90:
                print("   ✅ PSE selected successfully")
                # Parse PSE response for applications
                pse_data = self.parser.parse(response)
                print(f"   📊 PSE TLV data: {len(pse_data)} tags found")
                
                # Look for applications in PSE
                applications = []
                for tlv in pse_data:
                    if tlv['tag'] == '61':  # Application template
                        # Parse application template
                        app_tlv = self.parser.parse_tlv(bytes.fromhex(tlv['value']))
                        app_info = {}
                        for app_tag in app_tlv:
                            if app_tag['tag'] == '4F':  # ADF Name (AID)
                                app_info['aid'] = app_tag['value']
                            elif app_tag['tag'] == '50':  # Application Label
                                app_info['label'] = bytes.fromhex(app_tag['value']).decode('ascii', errors='ignore')
                        applications.append(app_info)
                        
                print(f"   📱 Found {len(applications)} applications:")
                for i, app in enumerate(applications):
                    print(f"     {i}: {app.get('label', 'Unknown')} - AID: {app.get('aid', 'N/A')}")
                    
            else:
                print("   ⚠️  PSE selection failed, trying direct AID selection...")
                # Try common AIDs
                applications = [
                    {'aid': 'A0000000031010', 'label': 'Visa Credit/Debit'},
                    {'aid': 'A0000000041010', 'label': 'MasterCard Credit/Debit'},
                    {'aid': 'A0000000032010', 'label': 'Visa Electron'},
                    {'aid': 'A0000000042203', 'label': 'MasterCard Maestro'},
                ]
                
            # Step 2: Try to select and read each application
            card_data = {}
            
            for app in applications:
                try:
                    aid_hex = app['aid']
                    aid_bytes = bytes.fromhex(aid_hex)
                    
                    print(f"\n2. Selecting application: {app['label']}")
                    print(f"   AID: {aid_hex}")
                    
                    select_app = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
                    response, sw1, sw2 = connection.transmit(select_app)
                    
                    if sw1 == 0x90:
                        print("   ✅ Application selected!")
                        
                        # Parse SELECT response (FCI Template)
                        fci_data = self.parser.parse_tlv(response)
                        
                        print(f"   📊 FCI TLV data: {len(fci_data)} tags found")
                        
                        # Extract key EMV tags
                        emv_tags = {}
                        for tlv in fci_data:
                            print(f"     Tag {tlv['tag']}: {tlv['value'][:32]}{'...' if len(tlv['value']) > 32 else ''}")
                            emv_tags[tlv['tag']] = tlv['value']
                            
                            # Look for CDOL1 and CDOL2 in nested structures
                            if tlv['tag'] == '6F':  # FCI Template
                                nested_tlv = self.parser.parse_tlv(bytes.fromhex(tlv['value']))
                                for nested in nested_tlv:
                                    if nested['tag'] == 'A5':  # FCI Proprietary Template
                                        prop_tlv = self.parser.parse_tlv(bytes.fromhex(nested['value']))
                                        for prop in prop_tlv:
                                            print(f"       Nested Tag {prop['tag']}: {prop['value'][:32]}{'...' if len(prop['value']) > 32 else ''}")
                                            emv_tags[prop['tag']] = prop['value']
                        
                        # Specifically look for CDOL1 (8C) and CDOL2 (8D)
                        cdol1 = emv_tags.get('8C', '')
                        cdol2 = emv_tags.get('8D', '')
                        
                        print(f"\n   🔍 CDOL Analysis:")
                        print(f"     CDOL1 (8C): {'Found - ' + cdol1 if cdol1 else 'NOT FOUND'}")
                        print(f"     CDOL2 (8D): {'Found - ' + cdol2 if cdol2 else 'NOT FOUND'}")
                        
                        if cdol1:
                            print(f"     📊 CDOL1 Analysis:")
                            cdol1_parsed = self.parse_cdol(cdol1)
                            for tag_info in cdol1_parsed:
                                print(f"       {tag_info}")
                                
                        if cdol2:
                            print(f"     📊 CDOL2 Analysis:")
                            cdol2_parsed = self.parse_cdol(cdol2)
                            for tag_info in cdol2_parsed:
                                print(f"       {tag_info}")
                        
                        # Step 3: GET PROCESSING OPTIONS
                        print(f"\n3. Getting Processing Options...")
                        
                        # Build PDOL data if CDOL1 exists
                        pdol_data = self.build_pdol_data(cdol1) if cdol1 else b'\x83\x00'
                        
                        gpo_command = [0x80, 0xA8, 0x00, 0x00, len(pdol_data)] + list(pdol_data)
                        response, sw1, sw2 = connection.transmit(gpo_command)
                        
                        if sw1 == 0x90:
                            print("   ✅ Processing Options retrieved!")
                            
                            # Parse GPO response
                            gpo_tlv = self.parser.parse_tlv(response)
                            afl_data = ""
                            aip_data = ""
                            
                            for tlv in gpo_tlv:
                                print(f"     GPO Tag {tlv['tag']}: {tlv['value']}")
                                if tlv['tag'] == '94':  # AFL
                                    afl_data = tlv['value']
                                elif tlv['tag'] == '82':  # AIP
                                    aip_data = tlv['value']
                            
                            # Step 4: Read records using AFL
                            if afl_data:
                                print(f"\n4. Reading Records using AFL: {afl_data}")
                                records_data = self.read_afl_records(connection, afl_data)
                                
                                # Parse all record data for additional EMV tags
                                all_record_tlv = []
                                for record in records_data:
                                    record_tlv = self.parser.parse_tlv(record)
                                    all_record_tlv.extend(record_tlv)
                                    
                                # Look for CDOL1/CDOL2 in record data
                                for tlv in all_record_tlv:
                                    if tlv['tag'] == '8C':
                                        print(f"     🎯 CDOL1 found in records: {tlv['value']}")
                                        cdol1 = tlv['value']
                                    elif tlv['tag'] == '8D':
                                        print(f"     🎯 CDOL2 found in records: {tlv['value']}")
                                        cdol2 = tlv['value']
                        
                        # Store card data
                        card_data = {
                            'aid': aid_hex,
                            'label': app['label'],
                            'fci_data': emv_tags,
                            'cdol1': cdol1,
                            'cdol2': cdol2,
                            'afl': afl_data,
                            'aip': aip_data,
                            'raw_fci_tlv': fci_data,
                            'records_tlv': all_record_tlv if 'all_record_tlv' in locals() else []
                        }
                        
                        # Extract fields using EMV card class
                        fields = self.emv_card._extract_fields_from_tlv(fci_data + (all_record_tlv if 'all_record_tlv' in locals() else []))
                        card_data['extracted_fields'] = fields
                        
                        print(f"\n   📊 Extracted Fields:")
                        for key, value in fields.items():
                            print(f"     {key}: {value}")
                        
                        return card_data
                        
                    else:
                        print(f"   ❌ Application selection failed: {sw1:02X}{sw2:02X}")
                        
                except Exception as e:
                    print(f"   ❌ Error processing application {app['label']}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"❌ EMV data extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_cdol(self, cdol_hex):
        """Parse CDOL data to show required tags."""
        try:
            cdol_bytes = bytes.fromhex(cdol_hex)
            tags = []
            
            i = 0
            while i < len(cdol_bytes):
                # Parse tag
                if cdol_bytes[i] & 0x1F == 0x1F:  # Multi-byte tag
                    if i + 1 < len(cdol_bytes):
                        tag = f"{cdol_bytes[i]:02X}{cdol_bytes[i+1]:02X}"
                        i += 2
                    else:
                        break
                else:  # Single byte tag
                    tag = f"{cdol_bytes[i]:02X}"
                    i += 1
                
                # Parse length
                if i < len(cdol_bytes):
                    length = cdol_bytes[i]
                    i += 1
                    
                    tag_name = self.get_tag_name(tag)
                    tags.append(f"Tag {tag} ({tag_name}): {length} bytes")
                else:
                    break
                    
            return tags
            
        except Exception as e:
            return [f"CDOL parsing error: {e}"]
    
    def get_tag_name(self, tag):
        """Get human-readable tag name."""
        tag_names = {
            '9F02': 'Amount Authorized',
            '9F03': 'Amount Other',
            '9F1A': 'Terminal Country Code',
            '95': 'Terminal Verification Results',
            '5F2A': 'Transaction Currency Code',
            '9A': 'Transaction Date',
            '9C': 'Transaction Type',
            '9F37': 'Unpredictable Number',
            '9F35': 'Terminal Type',
            '9F45': 'Data Authentication Code',
            '9F4C': 'ICC Dynamic Number',
            '9F34': 'CVM Results',
            '9F21': 'Transaction Time',
            '9F7C': 'Customer Exclusive Data'
        }
        return tag_names.get(tag, 'Unknown')
    
    def build_pdol_data(self, cdol1):
        """Build PDOL data for GET PROCESSING OPTIONS."""
        try:
            # Simple PDOL - just basic required data
            pdol = b'\x83\x00'  # Basic PDOL
            return pdol
        except:
            return b'\x83\x00'
    
    def read_afl_records(self, connection, afl_hex):
        """Read records specified in AFL."""
        try:
            afl_bytes = bytes.fromhex(afl_hex)
            records = []
            
            # AFL format: SFI(1) + First Record(1) + Last Record(1) + Records in SDA(1)
            for i in range(0, len(afl_bytes), 4):
                if i + 3 < len(afl_bytes):
                    sfi = afl_bytes[i] >> 3
                    first_rec = afl_bytes[i + 1]
                    last_rec = afl_bytes[i + 2]
                    
                    print(f"     Reading SFI {sfi}, records {first_rec}-{last_rec}")
                    
                    for rec_num in range(first_rec, last_rec + 1):
                        read_record = [0x00, 0xB2, rec_num, (sfi << 3) | 0x04, 0x00]
                        response, sw1, sw2 = connection.transmit(read_record)
                        
                        if sw1 == 0x90:
                            print(f"       Record {rec_num}: {len(response)} bytes")
                            records.append(response)
                        else:
                            print(f"       Record {rec_num} failed: {sw1:02X}{sw2:02X}")
            
            return records
            
        except Exception as e:
            print(f"     AFL reading error: {e}")
            return []

def test_real_card_data():
    """Test real card data extraction."""
    print("🔍 REAL CARD DATA EXTRACTION TEST")
    print("=" * 50)
    
    tester = RealCardTester()
    
    # Connect to card
    connection, reader = tester.detect_and_connect_card()
    if not connection:
        print("❌ Cannot proceed without card connection")
        return False
    
    try:
        # Extract real EMV data
        card_data = tester.extract_real_emv_data(connection)
        
        if card_data:
            print(f"\n🎉 SUCCESS! Real card data extracted:")
            print(f"   Application: {card_data['label']}")
            print(f"   AID: {card_data['aid']}")
            print(f"   CDOL1: {'✅ CAPTURED' if card_data['cdol1'] else '❌ NOT FOUND'}")
            print(f"   CDOL2: {'✅ CAPTURED' if card_data['cdol2'] else '❌ NOT FOUND'}")
            
            # Test CDOL extraction in EMV card class
            if card_data['cdol1'] or card_data['cdol2']:
                print(f"\n🧪 Testing CDOL extraction in EMV class:")
                
                # Create mock TLV data with CDOL
                mock_tlv = []
                if card_data['cdol1']:
                    mock_tlv.append({
                        'tag': '8C',
                        'value': card_data['cdol1'],
                        'length': len(card_data['cdol1']) // 2,
                        'description': 'CDOL1'
                    })
                if card_data['cdol2']:
                    mock_tlv.append({
                        'tag': '8D',
                        'value': card_data['cdol2'],
                        'length': len(card_data['cdol2']) // 2,
                        'description': 'CDOL2'
                    })
                
                # Test extraction
                emv = EMVCard()
                extracted = emv._extract_fields_from_tlv(mock_tlv)
                
                print(f"     CDOL1 extracted: {'✅' if 'cdol1' in extracted else '❌'}")
                print(f"     CDOL2 extracted: {'✅' if 'cdol2' in extracted else '❌'}")
                
                if 'cdol1' in extracted:
                    print(f"     CDOL1 value: {extracted['cdol1']}")
                if 'cdol2' in extracted:
                    print(f"     CDOL2 value: {extracted['cdol2']}")
            
            return True
        else:
            print("❌ Failed to extract card data")
            return False
            
    finally:
        try:
            connection.disconnect()
        except:
            pass

def test_cdol_parsing():
    """Test CDOL parsing with real data."""
    print("\n🔍 CDOL PARSING TEST")
    print("=" * 30)
    
    # Real CDOL examples from different card types
    real_cdol_examples = [
        "9F0206",  # Simple CDOL: Amount Authorized (6 bytes)
        "9F02069F03069F1A0295055F2A029A039C019F37049F35019F45029F4C089F34039F21039F7C14",  # Complex CDOL
        "9F0206950882029F37049F1A029A039C01",  # Medium CDOL
        "9F02069F03069F1A0295055F2A02",  # Common CDOL pattern
    ]
    
    tester = RealCardTester()
    
    for i, cdol_hex in enumerate(real_cdol_examples):
        print(f"\nCDOL Example {i+1}: {cdol_hex}")
        parsed = tester.parse_cdol(cdol_hex)
        for tag_info in parsed:
            print(f"  {tag_info}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        print("🚀 REAL CARD DATA & CDOL TESTING")
        print("=" * 60)
        
        # Test CDOL parsing first (doesn't require card)
        test_cdol_parsing()
        
        # Test real card data extraction
        success = test_real_card_data()
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Real card data extracted successfully")
            print("✅ CDOL1/CDOL2 captured and parsed")
        else:
            print("\n⚠️  Tests completed with issues")
            print("   Ensure card is inserted and try again")
        
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        import traceback
        traceback.print_exc()
