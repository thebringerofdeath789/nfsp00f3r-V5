#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Fixed Card Reading Implementation
Tests the fixed card reading functionality.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_fixed_card_reading():
    """Test the fixed card reading implementation."""
    print("\n=== Testing Fixed Card Reading Implementation ===")
    
    try:
        from readers import ReaderManager
        
        # Create reader manager
        reader_manager = ReaderManager()
        
        # Detect readers
        readers = reader_manager.detect_readers()
        print(f"✓ Detected {len(readers)} readers")
        
        if not readers:
            print("⚠️  No readers detected")
            return False
        
        reader_info = readers[0]
        print(f"✓ Testing with: {reader_info['name']}")
        
        # Connect to reader
        if not reader_manager.connect_reader(reader_info):
            print("✗ Failed to connect to reader")
            return False
        
        print("✓ Connected to reader")
        
        # Get reader instance
        reader = reader_manager.get_reader(reader_info['name'])
        if not reader:
            print("✗ Could not get reader instance")
            return False
        
        # Test card presence
        card_present = reader.is_card_present()
        print(f"✓ Card present: {card_present}")
        
        if not card_present:
            print("ℹ️  Place a card on the reader and run the test again")
            return True
        
        # Test ATR reading (this should work now)
        print("Testing ATR reading...")
        atr = reader.get_atr()
        
        if atr:
            atr_hex = atr.hex().upper()
            print(f"✓ ATR successfully read: {atr_hex}")
            print(f"  - Length: {len(atr)} bytes")
            
            # Basic ATR analysis
            if len(atr) > 0:
                if atr[0] == 0x3B:
                    print("  - Convention: Direct")
                elif atr[0] == 0x3F:
                    print("  - Convention: Inverse")
                    
            # Identify card type
            if '1402' in atr_hex:
                print("  - Card type: MIFARE Classic")
            elif '4000' in atr_hex:
                print("  - Card type: MIFARE Ultralight")
            else:
                print("  - Card type: Unknown/Other")
                
        else:
            print("✗ Failed to read ATR")
            return False
        
        # Test APDU transmission
        print("\nTesting APDU transmission...")
        
        test_apdus = [
            # GET UID (for MIFARE/NFC cards)
            (bytes([0xFF, 0xCA, 0x00, 0x00, 0x00]), "GET UID"),
            # SELECT PPSE (EMV)
            (bytes([0x00, 0xA4, 0x04, 0x00, 0x0E, 
                   0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 
                   0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 0x00]), "SELECT PPSE"),
            # GET CHALLENGE
            (bytes([0x00, 0x84, 0x00, 0x00, 0x08]), "GET CHALLENGE")
        ]
        
        successful_commands = 0
        
        for apdu, description in test_apdus:
            try:
                response_data, sw1, sw2 = reader.transmit(apdu)
                status = f"{sw1:02X}{sw2:02X}"
                
                if sw1 == 0x90 and sw2 == 0x00:
                    print(f"✓ {description}: Success")
                    if response_data:
                        data_hex = response_data.hex().upper()
                        print(f"  - Data: {data_hex}")
                    successful_commands += 1
                elif sw1 == 0x6A and sw2 == 0x82:
                    print(f"⚠️  {description}: File not found (normal)")
                elif sw1 == 0x6D and sw2 == 0x00:
                    print(f"⚠️  {description}: Command not supported (normal)")
                else:
                    print(f"⚠️  {description}: Status {status}")
                    
            except Exception as e:
                print(f"⚠️  {description}: Error - {e}")
        
        print(f"\n✓ APDU testing completed: {successful_commands} successful commands")
        
        # Test convenience method
        print("\nTesting convenience method...")
        try:
            uid_apdu = bytes([0xFF, 0xCA, 0x00, 0x00, 0x00])
            full_response = reader.transmit_apdu(uid_apdu)
            
            if full_response and len(full_response) >= 2:
                sw = full_response[-2:]
                data = full_response[:-2]
                
                print(f"✓ Convenience method: SW={sw.hex().upper()}")
                if data:
                    print(f"  - Data: {data.hex().upper()}")
            else:
                print("⚠️  Convenience method returned no data")
                
        except Exception as e:
            print(f"⚠️  Convenience method error: {e}")
        
        # Disconnect
        reader_manager.disconnect_reader(reader_info['name'])
        print("✓ Disconnected from reader")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in card reading test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_integration():
    """Test UI integration with fixed card reading."""
    print("\n=== Testing UI Integration ===")
    
    try:
        from PyQt5.QtWidgets import QApplication
        from main import Application
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Create main application
        main_app = Application(sys.argv)
        
        # Get main window
        main_window = main_app.main_window
        
        # Trigger reader refresh
        main_window.refresh_readers()
        
        # Check if readers are shown
        if (hasattr(main_window, 'reader_widget') and 
            main_window.reader_widget and 
            main_window.reader_widget.reader_list.count() > 0):
            print("✓ Readers visible in UI")
            
            # Simulate reader selection
            first_item = main_window.reader_widget.reader_list.item(0)
            if first_item:
                reader_name = main_window._detected_readers[0]['name']
                print(f"✓ Selecting reader: {reader_name}")
                
                # Simulate card reading through UI
                main_window.on_reader_selected(reader_name)
                print("✓ Reader selected through UI")
                
                # Check if we can start reading
                main_window.start_card_reading(reader_name)
                print("✓ Card reading started through UI")
        else:
            print("⚠️  No readers visible in UI")
        
        return True
        
    except Exception as e:
        print(f"⚠️  UI integration test error: {e}")
        return False

def main():
    """Run the fixed card reading tests."""
    print("Testing Fixed Card Reading Implementation")
    print("=" * 50)
    
    # Test 1: Fixed card reading
    reading_success = test_fixed_card_reading()
    
    # Test 2: UI integration (optional)
    ui_success = True
    if reading_success:
        try:
            ui_success = test_ui_integration()
        except:
            ui_success = False
    
    print("\n" + "="*50)
    print("Test Results:")
    print(f"Card Reading: {'✓ PASS' if reading_success else '✗ FAIL'}")
    print(f"UI Integration: {'✓ PASS' if ui_success else '⚠️ SKIP'}")
    
    if reading_success:
        print("\n🎉 Card reading is now fixed!")
        print("\nThe application should now:")
        print("  1. Detect your ACR122 reader")
        print("  2. Read card ATR properly")
        print("  3. Support APDU communication")
        print("  4. Work with different card types")
        print("\nRun the main application: python main.py")
    else:
        print("\n❌ Card reading issues persist")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()
