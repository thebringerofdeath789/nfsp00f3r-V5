#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Real Card APDU Reader
=======================================

File: test_real_card_apdu.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Read real card data with raw APDU output and proper TLV parsing

This script:
1. Detects available card readers
2. Connects to card on reader
3. Shows raw APDU commands and responses
4. Extracts actual PAN and card data
5. Demonstrates robust nested TLV parsing
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging for APDU debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def hex_dump(data: bytes, prefix: str = "", max_bytes: int = 256) -> str:
    """Create a formatted hex dump of binary data."""
    if not data:
        return f"{prefix}(empty)"
    
    hex_str = data[:max_bytes].hex().upper()
    formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
    
    if len(data) > max_bytes:
        formatted += f" ... ({len(data)} bytes total)"
    
    return f"{prefix}{formatted}"

def send_apdu(reader, apdu_hex: str, description: str = "") -> Optional[bytes]:
    """Send APDU command and display raw I/O."""
    try:
        apdu_bytes = bytes.fromhex(apdu_hex.replace(' ', ''))
        print(f"\n🔍 {description}")
        print(f"📤 APDU CMD: {hex_dump(apdu_bytes, '')}")
        
        # Send APDU using reader - returns tuple (response, sw1, sw2)
        result = reader.transmit(apdu_bytes)
        
        if result and len(result) == 3:
            response_bytes, sw1, sw2 = result
            status = f"{sw1:02X}{sw2:02X}"
            
            # Combine response and status for display
            full_response = response_bytes + bytes([sw1, sw2])
            print(f"📥 APDU RSP: {hex_dump(full_response, '')}")
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Status: {status} (Success)")
            elif sw1 == 0x61:
                print(f"🔄 Status: {status} (More data available: {sw2} bytes)")
                # Get additional data
                get_response_cmd = f"00 C0 00 00 {sw2:02X}"
                additional_data = send_apdu(reader, get_response_cmd, f"GET RESPONSE ({sw2} bytes)")
                if additional_data:
                    response_bytes += additional_data
            elif sw1 == 0x6C:
                print(f"⚠️  Status: {status} (Wrong length, correct length: {sw2})")
            else:
                print(f"❌ Status: {status} (Error)")
                
            return response_bytes if sw1 in [0x90, 0x61] else None
        else:
            print("❌ Invalid response format")
            return None
            
    except Exception as e:
        print(f"❌ APDU Error: {e}")
        return None

def get_response(reader, length: int) -> Optional[bytes]:
    """Get response for 61XX status."""
    get_response_apdu = f"00 C0 00 00 {length:02X}"
    return send_apdu(reader, get_response_apdu, f"GET RESPONSE ({length} bytes)")

def read_emv_card():
    """Read EMV card data with full APDU tracing."""
    print("🔍 NFSP00F3R V5.00 - Real Card APDU Reader")
    print("=" * 60)
    
    try:
        # Import readers
        from ..readers import ReaderManager, PCSCCardReader
        
        # Detect readers
        reader_manager = ReaderManager()
        available_readers = reader_manager.detect_readers()
        
        print(f"📱 Available readers: {len(available_readers)}")
        for i, reader_info in enumerate(available_readers):
            print(f"  {i+1}. {reader_info['name']} ({reader_info['type']})")
        
        if not available_readers:
            print("❌ No card readers found!")
            return
        
        # Use first available reader
        reader_info = available_readers[0]
        print(f"\n🔗 Connecting to: {reader_info['name']}")
        
        # Create reader instance
        reader = PCSCCardReader(reader_info['name'])
        
        # Check for card presence first
        print("🔍 Checking for card presence...")
        if not reader.is_card_present():
            print("❌ No card detected on reader")
            print("   Please insert a card and try again")
            return
        
        # Connect to card
        if not reader.connect():
            print("❌ Failed to connect to card")
            return
        
        print("✅ Connected to card successfully")
        atr = reader.get_atr()
        if atr:
            print(f"📋 ATR: {hex_dump(atr, '')}")
        else:
            print("📋 ATR: Not available")
        
        # Start EMV application selection
        print("\n" + "="*60)
        print("🏦 EMV APPLICATION SELECTION")
        print("="*60)
        
        # Send SELECT PPSE (Proximity Payment System Environment)
        ppse_select = "00 A4 04 00 0E 32 50 41 59 2E 53 59 53 2E 44 44 46 30 31 00"
        response = send_apdu(reader, ppse_select, "SELECT PPSE")
        
        if response:
            print(f"\n📊 PPSE Response Analysis:")
            print(f"Raw data: {response.hex().upper()}")
            
            # Parse TLV response
            try:
                from ..tlv import TLVParser
                parser = TLVParser()
                parsed = parser.parse(response)
                
                print(f"\n📋 Parsed TLV Structure:")
                if isinstance(parsed, dict):
                    for tag, value in parsed.items():
                        print(f"  Tag {tag}: {type(value).__name__}")
                        if isinstance(value, bytes):
                            print(f"    Value: {value.hex().upper()}")
                elif isinstance(parsed, list):
                    for i, tlv in enumerate(parsed):
                        print(f"  TLV {i+1}: {tlv}")
                
            except Exception as e:
                print(f"❌ TLV parsing failed: {e}")
        
        # Try to select specific applications
        common_aids = [
            ("A0000000041010", "Mastercard"),
            ("A0000000031010", "Visa"),
            ("A0000000032010", "Visa Electron"),
            ("A0000000033010", "Visa Interlink"),
            ("A0000000042203", "Maestro"),
            ("A0000000043060", "Cirrus"),
        ]
        
        selected_aid = None
        for aid, name in common_aids:
            print(f"\n🎯 Trying to select {name} ({aid})")
            aid_bytes = bytes.fromhex(aid)
            select_cmd = f"00 A4 04 00 {len(aid_bytes):02X} {aid} 00"
            
            response = send_apdu(reader, select_cmd, f"SELECT {name}")
            
            if response and len(response) > 0:
                print(f"✅ Successfully selected {name}")
                selected_aid = aid
                
                # Parse application response
                try:
                    from ..tlv import TLVParser
                    parser = TLVParser()
                    parsed = parser.parse(response)
                    print(f"📋 Application Selection Response:")
                    print(f"Raw: {response.hex().upper()}")
                    
                except Exception as e:
                    print(f"❌ Failed to parse application response: {e}")
                
                break
        
        if not selected_aid:
            print("❌ No supported applications found on card")
            return
        
        # Read application data
        print("\n" + "="*60)
        print("💳 READING CARD DATA")
        print("="*60)
        
        # Try to read common EMV records
        card_data = {}
        
        # Try GET PROCESSING OPTIONS
        pdol = "83 00"  # Empty PDOL data
        gpo_cmd = f"80 A8 00 00 {len(bytes.fromhex(pdol)):02X} {pdol} 00"
        response = send_apdu(reader, gpo_cmd, "GET PROCESSING OPTIONS")
        
        if response:
            try:
                from ..tlv import TLVParser
                parser = TLVParser()
                parsed = parser.parse(response)
                
                # Look for AFL (Application File Locator)
                print(f"📊 Processing Options Response:")
                print(f"Raw: {response.hex().upper()}")
                
            except Exception as e:
                print(f"❌ Failed to parse GPO response: {e}")
        
        # Read records from typical locations
        for sfi in range(1, 5):  # Try SFI 1-4
            for record in range(1, 11):  # Try records 1-10
                read_cmd = f"00 B2 {record:02X} {(sfi << 3) | 4:02X} 00"
                response = send_apdu(reader, read_cmd, f"READ RECORD SFI={sfi} REC={record}")
                
                if response and len(response) > 0:
                    print(f"\n📄 Found data in SFI {sfi}, Record {record}")
                    print(f"Raw: {response.hex().upper()}")
                    
                    # Parse for PAN and other data
                    try:
                        from ..tlv import TLVParser
                        parser = TLVParser()
                        parsed = parser.parse(response)
                        
                        # Look for specific tags
                        if isinstance(parsed, dict):
                            for tag, value in parsed.items():
                                if tag == '5A' and isinstance(value, bytes):  # PAN
                                    pan = value.hex().upper()
                                    print(f"🎯 FOUND PAN: {pan}")
                                    card_data['pan'] = pan
                                elif tag == '5F24' and isinstance(value, bytes):  # Expiry
                                    expiry = value.hex().upper()
                                    print(f"📅 FOUND EXPIRY: {expiry}")
                                    card_data['expiry'] = expiry
                                elif tag == '5F20' and isinstance(value, bytes):  # Cardholder name
                                    try:
                                        name = value.decode('ascii').strip()
                                        print(f"👤 FOUND NAME: {name}")
                                        card_data['name'] = name
                                    except:
                                        print(f"👤 FOUND NAME (hex): {value.hex().upper()}")
                                        card_data['name'] = value.hex()
                                        
                    except Exception as e:
                        print(f"❌ Failed to parse record: {e}")
                
                # Stop if we get an error (no more records)
                elif not response:
                    break
        
        # Summary
        print("\n" + "="*60)
        print("📋 CARD DATA SUMMARY")
        print("="*60)
        
        if card_data:
            for key, value in card_data.items():
                print(f"  {key.upper()}: {value}")
        else:
            print("  No card data extracted")
        
        # Test the TLV parser with some nested data
        print("\n" + "="*60)
        print("🧪 TLV PARSER TEST")
        print("="*60)
        
        # Create test nested TLV
        test_tlv = "6F1C840E315041592E5359532E4444463031A50A880102500550415920"
        print(f"Test TLV: {test_tlv}")
        
        try:
            from ..tlv import TLVParser
            parser = TLVParser()
            test_data = bytes.fromhex(test_tlv)
            parsed = parser.parse(test_data)
            
            print(f"Parsed result type: {type(parsed)}")
            print(f"Parsed result: {parsed}")
            
        except Exception as e:
            print(f"❌ TLV parser test failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Card reading failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            reader.disconnect()
            print("\n🔌 Disconnected from card")
        except:
            pass

if __name__ == "__main__":
    read_emv_card()
