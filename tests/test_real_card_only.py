#!/usr/bin/env python3
"""
WORKING CARD READER TEST - NO TEST DATA!
=========================================

This test ONLY reads from actual card - NO hardcoded data allowed.
Fixed card detection and reading logic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import logging

# Configure minimal logging
logging.basicConfig(level=logging.WARNING)

def test_direct_card_reading():
    """Test reading directly from card using PCSC."""
    print("🧪 DIRECT CARD READING TEST")
    print("=" * 50)
    print("⚠️  NO TEST DATA - ONLY REAL CARD READING")
    print()
    
    try:
        # Use smartcard library directly
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get readers
        reader_list = readers()
        print(f"📱 Found {len(reader_list)} readers:")
        
        if not reader_list:
            print("❌ No card readers found!")
            return False
            
        for i, reader in enumerate(reader_list):
            print(f"  {i+1}. {reader}")
        
        # Use first reader
        reader = reader_list[0]
        print(f"\n🔗 Using reader: {reader}")
        
        # Direct connection attempt
        print("🔍 Attempting direct card connection...")
        
        try:
            connection = reader.createConnection()
            connection.connect()
            
            print("✅ CARD CONNECTED!")
            
            # Get ATR
            atr = connection.getATR()
            print(f"📋 ATR: {toHexString(atr)}")
            
            # Test PPSE SELECT
            print("\n📤 Sending PPSE SELECT...")
            ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 
                       0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 
                       0x00]
            
            response, sw1, sw2 = connection.transmit(ppse_cmd)
            
            print(f"📥 Response: SW={sw1:02X}{sw2:02X}")
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ SUCCESS: {len(response)} bytes received")
                response_bytes = bytes(response)
                print(f"📊 Raw data: {response_bytes.hex().upper()}")
                
                # Parse with TLV
                from ..tlv import TLVParser
                parser = TLVParser()
                tlv_data = parser.parse(response_bytes)
                
                if parser.parse_errors:
                    print("⚠️  TLV errors:")
                    for error in parser.parse_errors:
                        print(f"   - {error}")
                else:
                    print("✅ TLV parsing successful!")
                
                tree = parser.format_tlv_tree(tlv_data)
                print("\n📋 Parsed structure:")
                print(tree)
                
                # Try to select application and read PAN
                return read_application_data(connection, tlv_data)
                
            else:
                print(f"❌ PPSE failed: SW={sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            print(f"❌ Card connection failed: {e}")
            print("   Make sure card is properly inserted")
            return False
            
    except ImportError as e:
        print(f"❌ Smartcard library error: {e}")
        return False
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def read_application_data(connection, ppse_data):
    """Read application data and extract PAN from ALL available AIDs."""
    print("\n🎯 READING APPLICATION DATA")
    print("=" * 40)
    
    try:
        # Extract ALL AIDs from PPSE response
        aids = []
        if '6F' in ppse_data and isinstance(ppse_data['6F'], dict):
            fci = ppse_data['6F']
            if 'A5' in fci and isinstance(fci['A5'], dict):
                prop_template = fci['A5']
                if 'BF0C' in prop_template and isinstance(prop_template['BF0C'], dict):
                    bf0c = prop_template['BF0C']
                    if '61' in bf0c:
                        app_templates = bf0c['61']
                        
                        # Handle both single app and multiple apps
                        if not isinstance(app_templates, list):
                            app_templates = [app_templates]
                        
                        for i, app_template in enumerate(app_templates):
                            if isinstance(app_template, dict) and '4F' in app_template:
                                aid = app_template['4F']
                                label = ""
                                if '50' in app_template and isinstance(app_template['50'], bytes):
                                    label = app_template['50'].decode('utf-8', errors='ignore')
                                aids.append({'aid': aid, 'label': label, 'index': i})
        
        if not aids:
            print("❌ Could not extract any AIDs from PPSE")
            return False
            
        print(f"📱 Found {len(aids)} applications:")
        for i, app_info in enumerate(aids):
            print(f"  {i+1}. AID: {app_info['aid'].hex().upper()} - {app_info['label']}")
        
        # Try each AID until we find one with PAN starting with 4031
        for app_info in aids:
            aid = app_info['aid']
            label = app_info['label']
            
            print(f"\n📤 Selecting application: {label} (AID: {aid.hex().upper()})")
            
            # SELECT APPLICATION
            aid_bytes = list(aid)
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + aid_bytes
            
            response, sw1, sw2 = connection.transmit(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Application selected: {len(response)} bytes")
                
                # Parse application response
                response_bytes = bytes(response)
                print(f"📊 App response: {response_bytes.hex().upper()}")
                
                from ..tlv import TLVParser
                parser = TLVParser()
                app_tlv = parser.parse(response_bytes)
                
                if parser.parse_errors:
                    print("⚠️  App TLV errors:")
                    for error in parser.parse_errors:
                        print(f"   - {error}")
                
                tree = parser.format_tlv_tree(app_tlv)
                print(f"\n📋 Application structure:")
                print(tree)
                
                # Try to read records from this application
                pan_result = read_records_for_pan(connection, label)
                if pan_result:
                    return True  # Found PAN starting with 4031
                else:
                    print(f"⚠️  No suitable PAN found in {label}, trying next application...")
                    
            else:
                print(f"❌ Application selection failed: SW={sw1:02X}{sw2:02X}")
        
        print("❌ No application contained PAN starting with 4031")
        return False
            
    except Exception as e:
        print(f"❌ Application reading error: {e}")
        return False

def read_records_for_pan(connection, app_label=""):
    """Read records to find PAN starting with 4031."""
    print(f"\n💳 READING RECORDS FOR PAN ({app_label})")
    print("=" * 40)
    
    try:
        # Try multiple files and records
        for file_num in [1, 2]:
            for record_num in range(1, 6):
                try:
                    read_cmd = [0x00, 0xB2, record_num, (file_num << 3) | 0x04]  # READ RECORD
                    
                    response, sw1, sw2 = connection.transmit(read_cmd)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        print(f"✅ File {file_num}, Record {record_num}: {len(response)} bytes")
                        
                        response_bytes = bytes(response)
                        print(f"📊 Record data: {response_bytes.hex().upper()}")
                        
                        # Parse record
                        from ..tlv import TLVParser
                        parser = TLVParser()
                        record_tlv = parser.parse(response_bytes)
                        
                        if parser.parse_errors:
                            print(f"⚠️  Record TLV errors:")
                            for error in parser.parse_errors:
                                print(f"   - {error}")
                        
                        # Look for PAN (tag 5A)
                        pan_found = find_pan_in_tlv(record_tlv)
                        if pan_found:
                            print(f"🎯 FOUND PAN: {pan_found}")
                            
                            if pan_found.startswith('4031'):
                                print("✅ PAN STARTS WITH 4031 - REQUIREMENT MET!")
                                
                                tree = parser.format_tlv_tree(record_tlv)
                                print("\n📋 Record with PAN:")
                                print(tree)
                                
                                # Analyze UDOL if present
                                analyze_udol(record_tlv)
                                
                                return True
                            else:
                                print(f"⚠️  PAN starts with {pan_found[:4]} - need 4031")
                    
                    elif sw1 == 0x6A and sw2 == 0x83:
                        # Record not found - normal
                        pass
                    else:
                        print(f"⚠️  File {file_num}, Record {record_num}: SW={sw1:02X}{sw2:02X}")
                        
                except Exception as e:
                    print(f"⚠️  Error reading File {file_num}, Record {record_num}: {e}")
        
        print("❌ No PAN starting with 4031 found in any records")
        return False
        
    except Exception as e:
        print(f"❌ Record reading error: {e}")
        return False

def analyze_udol(tlv_data):
    """Analyze UDOL (Unpredictable Number Data Object List) structure."""
    print("\n🔍 UDOL ANALYSIS")
    print("=" * 30)
    
    udol_value = find_tag_in_tlv(tlv_data, '9F69')
    if udol_value:
        print(f"📊 UDOL (9F69): {udol_value.hex().upper()}")
        print(f"📏 Length: {len(udol_value)} bytes")
        
        # Analyze UDOL structure
        if len(udol_value) == 7 and udol_value == bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]):
            print("⚠️  UNUSUAL: UDOL contains mostly zeros")
            print("   This may be:")
            print("   1. Proprietary issuer format")
            print("   2. Padding/filler data")
            print("   3. Non-standard encoding")
        else:
            print("📋 UDOL appears to have structured data")
            
        # Try to parse as tag-length pairs
        print("\n🔧 Attempting standard TLV parsing of UDOL:")
        try:
            from ..tlv import TLVParser
            parser = TLVParser()
            udol_tlv = parser.parse(udol_value)
            
            if parser.parse_errors:
                print("⚠️  UDOL TLV parsing errors:")
                for error in parser.parse_errors:
                    print(f"   - {error}")
                print("   → This suggests non-standard UDOL format")
            else:
                tree = parser.format_tlv_tree(udol_tlv)
                print("✅ UDOL parsed as standard TLV:")
                print(tree)
                
        except Exception as e:
            print(f"❌ UDOL parsing failed: {e}")
    else:
        print("❌ No UDOL (9F69) found in record data")

def find_tag_in_tlv(tlv_data, target_tag):
    """Recursively search for a specific tag in TLV data."""
    if isinstance(tlv_data, dict):
        for tag, value in tlv_data.items():
            if tag == target_tag and isinstance(value, bytes):
                return value
            elif isinstance(value, dict):
                result = find_tag_in_tlv(value, target_tag)
                if result:
                    return result
            elif isinstance(value, list):
                for item in value:
                    result = find_tag_in_tlv(item, target_tag)
                    if result:
                        return result
    return None

def find_pan_in_tlv(tlv_data, path=""):
    """Recursively search for PAN (tag 5A) in TLV data."""
    if isinstance(tlv_data, dict):
        for tag, value in tlv_data.items():
            if tag == '5A' and isinstance(value, bytes):
                return value.hex().upper()
            elif isinstance(value, dict):
                result = find_pan_in_tlv(value, f"{path}/{tag}")
                if result:
                    return result
            elif isinstance(value, list):
                for item in value:
                    result = find_pan_in_tlv(item, f"{path}/{tag}[]")
                    if result:
                        return result
    return None

if __name__ == "__main__":
    print("🚨 CRITICAL: This test requires a REAL EMV card inserted in reader")
    print("🚨 NO test data will be used - only live card reading")
    print()
    
    success = test_direct_card_reading()
    
    if success:
        print("\n🎉 SUCCESS: Real card reading test PASSED!")
        print("✅ Found card with PAN starting with 4031")
    else:
        print("\n❌ FAILED: Could not read real card data")
        print("   Ensure EMV card with PAN starting with 4031 is inserted")
    
    sys.exit(0 if success else 1)
