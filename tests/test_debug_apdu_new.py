#!/usr/bin/env python3
"""
Card Reader Diagnostic Test - Overwrite
=======================================

This test diagnoses card reader issues and provides detailed debugging info.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..readers import ReaderManager, PCSCCardReader
import time

def diagnose_reader():
    print("🔧 CARD READER DIAGNOSTIC TEST")
    print("=" * 50)
    
    try:
        # Step 1: Check reader detection
        print("\n1️⃣ READER DETECTION")
        reader_manager = ReaderManager()
        available_readers = reader_manager.detect_readers()
        
        print(f"📱 Found {len(available_readers)} readers:")
        for i, reader_info in enumerate(available_readers):
            print(f"  {i+1}. {reader_info['name']} ({reader_info['type']})")
        
        if not available_readers:
            print("❌ FAILED: No readers detected!")
            return False
            
        # Step 2: Test reader connection
        print("\n2️⃣ READER CONNECTION TEST")
        reader_info = available_readers[0]
        reader_name = reader_info['name']
        print(f"🔗 Testing connection to: {reader_name}")
        
        reader = PCSCCardReader(reader_name)
        
        # Step 3: Raw card presence check (multiple attempts)
        print("\n3️⃣ CARD PRESENCE DETECTION")
        print("📋 Testing card presence detection (10 attempts over 5 seconds)...")
        
        for attempt in range(10):
            present = reader.is_card_present()
            print(f"  Attempt {attempt+1}: {'✅ CARD DETECTED' if present else '❌ No card'}")
            
            if present:
                print("\n🎉 SUCCESS: Card detected!")
                
                # Get detailed info
                if reader.connect():
                    atr = reader.get_atr()
                    if atr:
                        print(f"📋 ATR: {atr.hex().upper()}")
                        print(f"📋 ATR Length: {len(atr)} bytes")
                    else:
                        print("📋 ATR: Not available")
                    
                    reader.disconnect()
                    return True
                else:
                    print("⚠️  Card detected but connection failed")
            
            time.sleep(0.5)
        
        # Step 4: Manual check instructions
        print("\n4️⃣ MANUAL VERIFICATION")
        print("❌ No card detected in 10 attempts")
        print("\n🔍 TROUBLESHOOTING CHECKLIST:")
        print("   1. Is an EMV card properly inserted in the reader?")
        print("   2. Is the card oriented correctly (chip side up)?")
        print("   3. Is the card fully inserted (you should hear/feel a click)?")
        print("   4. Try removing and reinserting the card")
        print("   5. Try a different EMV card")
        print("\n⏳ Insert a card now and press Enter to test again...")
        input()
        
        # Test again after manual insertion
        print("\n5️⃣ RETRY AFTER MANUAL INSERTION")
        for attempt in range(5):
            present = reader.is_card_present()
            print(f"  Retry {attempt+1}: {'✅ CARD DETECTED' if present else '❌ No card'}")
            
            if present:
                print("\n🎉 SUCCESS: Card detected after manual check!")
                return True
            time.sleep(1.0)
        
        print("\n❌ FAILED: Still no card detected")
        return False
        
    except Exception as e:
        print(f"\n💥 ERROR during diagnosis: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_detected_card():
    """Test actual EMV communication once card is detected."""
    print("\n" + "="*50)
    print("🏦 EMV COMMUNICATION TEST")
    print("="*50)
    
    try:
        reader_manager = ReaderManager()
        available_readers = reader_manager.detect_readers()
        
        if not available_readers:
            print("❌ No readers available")
            return False
            
        reader = PCSCCardReader(available_readers[0]['name'])
        
        if not reader.is_card_present():
            print("❌ No card present")
            return False
            
        if not reader.connect():
            print("❌ Failed to connect to card")
            return False
            
        print("✅ Connected to card")
        
        # Try basic EMV commands
        print("\n📤 Testing PPSE SELECT...")
        ppse_cmd = bytes.fromhex("00A404000E325041592E5359532E4444463031")
        
        try:
            response, sw1, sw2 = reader.transmit(ppse_cmd)
            print(f"📥 Response: SW={sw1:02X}{sw2:02X}")
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ PPSE SELECT successful: {len(response)} bytes")
                print(f"📊 Data: {response.hex().upper()}")
                
                # Parse with TLV
                from ..tlv import TLVParser
                parser = TLVParser()
                tlv_data = parser.parse(response)
                
                if parser.parse_errors:
                    print("⚠️  TLV parsing errors:")
                    for error in parser.parse_errors:
                        print(f"   - {error}")
                
                tree = parser.format_tlv_tree(tlv_data)
                print("\n📋 Parsed TLV structure:")
                print(tree)
                
                return True
            else:
                print(f"❌ PPSE SELECT failed: SW={sw1:02X}{sw2:02X}")
                
        except Exception as e:
            print(f"❌ APDU transmission failed: {e}")
            
        finally:
            reader.disconnect()
            
    except Exception as e:
        print(f"💥 EMV test error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Starting comprehensive card reader diagnostic...")
    
    if diagnose_reader():
        print("\n🎯 Reader diagnosis successful! Testing EMV communication...")
        test_with_detected_card()
    else:
        print("\n❌ Reader diagnosis failed. Please check card insertion.")
        
    print("\n✅ Diagnostic complete.")
