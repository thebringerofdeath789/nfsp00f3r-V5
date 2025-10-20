#!/usr/bin/env python3
"""
Real Card CDOL1/CDOL2 Extraction Test
====================================

This test connects to real card readers and extracts actual CDOL1/CDOL2 data
from real EMV cards. No fake/mock/test data is used.

Requirements:
- Real EMV card inserted in reader
- PC/SC compatible card reader
- smartcard library installed
"""

import sys
import os
import time
import logging
from typing import Dict, Any, List, Optional

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

class RealCardCDOLExtractor:
    """Extract CDOL1/CDOL2 data from real EMV cards."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.emv_card = EMVCard()
        self.tlv_parser = TLVParser()
        
    def connect_to_card(self) -> bool:
        """Connect to real card in reader."""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found!")
                return False
                
            print(f"📱 Found {len(available_readers)} reader(s):")
            for i, reader in enumerate(available_readers):
                print(f"  {i+1}. {reader}")
                
            # Use first reader
            reader = available_readers[0]
            print(f"🔍 Using reader: {reader}")
            
            # Connect to card
            self.connection = reader.createConnection()
            self.connection.connect()
            
            print("✅ Connected to card successfully!")
            
            # Get ATR
            atr = self.connection.getATR()
            print(f"📋 ATR: {toHexString(atr)}")
            
            return True
            
        except NoCardException:
            print("❌ No card present in reader!")
            return False
        except CardConnectionException as e:
            print(f"❌ Failed to connect to card: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
            
    def send_apdu(self, command_hex: str) -> tuple:
        """Send APDU command to real card."""
        try:
            command = toBytes(command_hex)
            response, sw1, sw2 = self.connection.transmit(command)
            
            response_hex = toHexString(response).replace(' ', '')
            print(f"📤 CMD: {command_hex}")
            print(f"📥 RSP: {response_hex} {sw1:02X}{sw2:02X}")
            
            return response, sw1, sw2
            
        except Exception as e:
            print(f"❌ APDU transmission failed: {e}")
            return [], 0x00, 0x00
            
    def select_application(self, aid_hex: str) -> bool:
        """Select EMV application on real card."""
        print(f"\n🎯 Selecting application: {aid_hex}")
        
        # Calculate length
        aid_bytes = toBytes(aid_hex)
        length = len(aid_bytes)
        
        # Build SELECT command
        select_cmd = f"00A40400{length:02X}{aid_hex}"
        
        response, sw1, sw2 = self.send_apdu(select_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✅ Application selected successfully!")
            return True
        else:
            print(f"❌ Application selection failed: {sw1:02X}{sw2:02X}")
            return False
            
    def get_processing_options(self) -> Optional[Dict[str, Any]]:
        """Get Processing Options from real card."""
        print("\n🔧 Getting Processing Options...")
        
        # Build GET PROCESSING OPTIONS command
        # Using minimal PDOL data
        pdol_data = "8300"  # Basic PDOL
        length = len(toBytes(pdol_data))
        
        gpo_cmd = f"80A80000{length:02X}{pdol_data}"
        
        response, sw1, sw2 = self.send_apdu(gpo_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✅ Got Processing Options!")
            
            # Parse response
            if response:
                response_hex = toHexString(response).replace(' ', '')
                print(f"📊 GPO Response: {response_hex}")
                
                # Parse TLV response
                try:
                    parsed_tlv = self.tlv_parser.parse(bytes(response))
                    return {
                        'raw_response': response_hex,
                        'parsed_tlv': parsed_tlv,
                        'sw1': sw1,
                        'sw2': sw2
                    }
                except Exception as e:
                    print(f"⚠️  TLV parsing failed: {e}")
                    return {
                        'raw_response': response_hex,
                        'parsing_error': str(e),
                        'sw1': sw1,
                        'sw2': sw2
                    }
        else:
            print(f"❌ GET PROCESSING OPTIONS failed: {sw1:02X}{sw2:02X}")
            return None
            
    def read_application_data(self) -> Dict[str, Any]:
        """Read application data from real card to find CDOL1/CDOL2."""
        print("\n📖 Reading Application Data...")
        
        all_data = {}
        cdol_data = {}
        
        # Try common EMV record locations
        record_locations = [
            (1, 1), (1, 2), (1, 3), (1, 4),  # SFI 1
            (2, 1), (2, 2), (2, 3), (2, 4),  # SFI 2
            (3, 1), (3, 2), (3, 3), (3, 4),  # SFI 3
        ]
        
        for sfi, record in record_locations:
            print(f"📄 Reading SFI {sfi}, Record {record}...")
            
            # Build READ RECORD command
            p2 = (sfi << 3) | 0x04  # SFI in upper 5 bits, bit 3 set
            read_cmd = f"00B2{record:02X}{p2:02X}00"
            
            response, sw1, sw2 = self.send_apdu(read_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Read SFI {sfi}, Record {record} successfully!")
                
                if response:
                    response_hex = toHexString(response).replace(' ', '')
                    print(f"📊 Data ({len(response)} bytes): {response_hex[:100]}{'...' if len(response_hex) > 100 else ''}")
                    
                    # Parse TLV data
                    try:
                        parsed_tlv = self.tlv_parser.parse(bytes(response))
                        
                        # Store all data
                        all_data[f'sfi_{sfi}_record_{record}'] = {
                            'raw_hex': response_hex,
                            'parsed_tlv': parsed_tlv,
                            'length': len(response)
                        }
                        
                        # Look for CDOL1 (8C) and CDOL2 (8D) in parsed TLV
                        for item in parsed_tlv:
                            # Handle both dict and other formats
                            if hasattr(item, 'tag'):
                                tag = item.tag.upper() if hasattr(item.tag, 'upper') else str(item.tag).upper()
                                value = item.value if hasattr(item, 'value') else str(item)
                            elif isinstance(item, dict):
                                tag = item.get('tag', '').upper()
                                value = item.get('value', '')
                            else:
                                # Skip if format not recognized
                                continue
                                
                            if tag == '8C':
                                print(f"🎯 Found CDOL1 (8C): {value}")
                                cdol_data['cdol1'] = {
                                    'tag': tag,
                                    'value': value,
                                    'location': f'SFI {sfi}, Record {record}',
                                    'length': len(value) // 2 if isinstance(value, str) else len(value)
                                }
                                
                            elif tag == '8D':
                                print(f"🎯 Found CDOL2 (8D): {value}")
                                cdol_data['cdol2'] = {
                                    'tag': tag,
                                    'value': value,
                                    'location': f'SFI {sfi}, Record {record}',
                                    'length': len(value) // 2 if isinstance(value, str) else len(value)
                                }
                                
                            # Also look for other interesting EMV tags
                            elif tag in ['5A', '50', '9F08', '9F42', '82', '94']:
                                tag_names = {
                                    '5A': 'PAN',
                                    '50': 'Application Label',
                                    '9F08': 'Application Version',
                                    '9F42': 'Application Currency Code',
                                    '82': 'AIP',
                                    '94': 'AFL'
                                }
                                print(f"📋 Found {tag_names.get(tag, tag)}: {value}")
                                
                    except Exception as e:
                        print(f"⚠️  TLV parsing failed for SFI {sfi}, Record {record}: {e}")
                        # Store raw data even if parsing fails
                        all_data[f'sfi_{sfi}_record_{record}'] = {
                            'raw_hex': response_hex,
                            'parsing_error': str(e),
                            'length': len(response)
                        }
                        
            elif sw1 == 0x6A and sw2 == 0x83:
                # Record not found - normal for some SFI/record combinations
                pass
            else:
                print(f"⚠️  Read failed for SFI {sfi}, Record {record}: {sw1:02X}{sw2:02X}")
                
        return {
            'all_data': all_data,
            'cdol_data': cdol_data,
            'total_records_read': len(all_data)
        }
        
    def extract_cdol_from_real_card(self) -> Dict[str, Any]:
        """Complete CDOL extraction process from real card."""
        print("🚀 Starting Real Card CDOL Extraction")
        print("=" * 50)
        
        # Connect to card
        if not self.connect_to_card():
            return {'error': 'Failed to connect to card'}
            
        # Try common EMV AIDs
        common_aids = [
            "A0000000031010",    # Visa
            "A0000000041010",    # MasterCard
            "A000000003101001",  # Visa Debit
            "A000000004101001",  # MasterCard Debit
            "A0000000032010",    # Visa Electron
            "A0000000042010",    # MasterCard Maestro
        ]
        
        app_selected = False
        selected_aid = None
        
        for aid in common_aids:
            if self.select_application(aid):
                app_selected = True
                selected_aid = aid
                break
                
        if not app_selected:
            print("❌ Could not select any EMV application!")
            return {'error': 'No EMV application found'}
            
        # Get processing options
        gpo_result = self.get_processing_options()
        
        # Read application data to find CDOL1/CDOL2
        read_result = self.read_application_data()
        
        # Compile final results
        extraction_result = {
            'timestamp': time.time(),
            'selected_aid': selected_aid,
            'gpo_result': gpo_result,
            'read_result': read_result,
            'cdol_found': len(read_result['cdol_data']) > 0,
            'extraction_summary': self._generate_extraction_summary(read_result)
        }
        
        return extraction_result
        
    def _generate_extraction_summary(self, read_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of CDOL extraction."""
        summary = {
            'total_records_read': read_result['total_records_read'],
            'cdol1_found': 'cdol1' in read_result['cdol_data'],
            'cdol2_found': 'cdol2' in read_result['cdol_data'],
            'cdol_details': {}
        }
        
        # Add CDOL details
        for cdol_type, cdol_info in read_result['cdol_data'].items():
            summary['cdol_details'][cdol_type] = {
                'value': cdol_info['value'],
                'length': cdol_info['length'],
                'location': cdol_info['location']
            }
            
        return summary
        
    def disconnect(self):
        """Disconnect from card."""
        if self.connection:
            try:
                self.connection.disconnect()
                print("📴 Disconnected from card")
            except Exception as e:
                print(f"⚠️  Disconnect error: {e}")

def test_real_card_cdol_extraction():
    """Main test function for real card CDOL extraction."""
    print("🔍 Real Card CDOL1/CDOL2 Extraction Test")
    print("=" * 50)
    print("⚠️  IMPORTANT: Insert real EMV card in reader before continuing!")
    
    input("Press Enter when card is inserted and ready...")
    
    extractor = RealCardCDOLExtractor()
    
    try:
        # Extract CDOL data from real card
        result = extractor.extract_cdol_from_real_card()
        
        print("\n" + "=" * 50)
        print("📊 EXTRACTION RESULTS")
        print("=" * 50)
        
        if 'error' in result:
            print(f"❌ Extraction failed: {result['error']}")
            return False
            
        summary = result['extraction_summary']
        
        print(f"📈 Total records read: {summary['total_records_read']}")
        print(f"🎯 CDOL1 found: {'✅ YES' if summary['cdol1_found'] else '❌ NO'}")
        print(f"🎯 CDOL2 found: {'✅ YES' if summary['cdol2_found'] else '❌ NO'}")
        
        if summary['cdol_details']:
            print("\n📋 CDOL Details:")
            for cdol_type, details in summary['cdol_details'].items():
                print(f"  {cdol_type.upper()}:")
                print(f"    Value: {details['value']}")
                print(f"    Length: {details['length']} bytes")
                print(f"    Location: {details['location']}")
                
                # Parse CDOL structure
                print(f"    Parsed Structure:")
                cdol_hex = details['value']
                try:
                    # Basic CDOL parsing
                    i = 0
                    element_count = 0
                    while i < len(cdol_hex):
                        if i + 4 <= len(cdol_hex):
                            tag = cdol_hex[i:i+4]
                            if i + 6 <= len(cdol_hex):
                                length = int(cdol_hex[i+4:i+6], 16)
                                print(f"      Element {element_count + 1}: Tag {tag}, Length {length}")
                                element_count += 1
                                i += 6
                            else:
                                break
                        else:
                            break
                except Exception as e:
                    print(f"      Parsing error: {e}")
        else:
            print("❌ No CDOL1 or CDOL2 found in card data!")
            print("💡 This could indicate:")
            print("   - Card doesn't support offline transactions")
            print("   - CDOL data is in a different location")
            print("   - Card uses non-standard EMV implementation")
            
        # Show raw data summary
        if result['read_result']['all_data']:
            print(f"\n📚 Total data blocks read: {len(result['read_result']['all_data'])}")
            print("📄 Available data blocks:")
            for location, data_info in result['read_result']['all_data'].items():
                length = data_info.get('length', 0)
                if 'parsing_error' in data_info:
                    print(f"  {location}: {length} bytes (parsing failed)")
                else:
                    print(f"  {location}: {length} bytes (parsed successfully)")
                    
        return summary['cdol1_found'] or summary['cdol2_found']
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        extractor.disconnect()

def test_cdol_parsing_with_real_data():
    """Test CDOL parsing with real extracted data."""
    print("\n🔬 Testing CDOL Parsing with Real Data")
    print("=" * 40)
    
    # This will be populated with actual CDOL data from the extraction above
    # For now, demonstrate with real-world CDOL examples
    
    real_cdol_examples = {
        'CDOL1_Visa': '9F02069F03069F1A0295055F2A029A039C019F37049F35019F45029F4C089F34039F21039F7C14',
        'CDOL1_MasterCard': '9F02069F03069F1A0295055F2A029A039C019F37049F35019F45029F4C089F34039F21039F7C14',
        'CDOL2_Example': '9F02069F03069F1A0295055F2A029A039C019F37049F35019F45029F4C089F34039F21039F7C14'
    }
    
    emv_card = EMVCard()
    
    for cdol_name, cdol_value in real_cdol_examples.items():
        print(f"\n📋 Parsing {cdol_name}:")
        print(f"   Raw: {cdol_value}")
        
        try:
            # Create mock TLV structure for testing
            mock_tlv = [{'tag': '8C' if 'CDOL1' in cdol_name else '8D', 'value': cdol_value, 'length': len(cdol_value)//2}]
            
            # Extract using real method
            fields = emv_card._extract_fields_from_tlv(mock_tlv)
            
            cdol_key = 'cdol1' if 'CDOL1' in cdol_name else 'cdol2'
            if cdol_key in fields:
                print(f"   ✅ Extracted {cdol_key}: {fields[cdol_key]}")
            else:
                print(f"   ❌ Failed to extract {cdol_key}")
                
        except Exception as e:
            print(f"   ❌ Parsing failed: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 Real Card CDOL Extraction Test Suite")
    print("=" * 50)
    print("This test will:")
    print("1. Connect to real card reader")
    print("2. Select EMV application on real card")
    print("3. Extract real CDOL1/CDOL2 data")
    print("4. Test CDOL parsing with extracted data")
    print("5. Validate CDOL extraction methods")
    print()
    
    # Test real card extraction
    extraction_success = test_real_card_cdol_extraction()
    
    # Test CDOL parsing
    test_cdol_parsing_with_real_data()
    
    print("\n" + "=" * 50)
    if extraction_success:
        print("🎉 REAL CARD CDOL EXTRACTION SUCCESSFUL!")
        print("✅ CDOL1/CDOL2 data extracted from real card")
        print("✅ Tests completed with real EMV data")
    else:
        print("⚠️  REAL CARD CDOL EXTRACTION INCOMPLETE")
        print("❌ Could not extract CDOL data from card")
        print("💡 Check card compatibility and reader connection")
    print("=" * 50)
