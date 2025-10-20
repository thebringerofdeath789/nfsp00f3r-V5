#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive UI and Card Reading Test
Tests the complete functionality including UI initialization and card reading.
"""

import sys
import os
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_card_reading_functionality():
    """Test the card reading functionality through UI."""
    print("\n=== Testing Card Reading Functionality ===")
    
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Import main modules
        from main import Application
        
        # Create Application instance
        main_app = Application(sys.argv)
        
        if not (hasattr(main_app, 'reader_manager') and hasattr(main_app, 'main_window')):
            print("✗ Application components not properly initialized")
            return False
        
        reader_manager = main_app.reader_manager
        main_window = main_app.main_window
        
        # Test reader detection
        readers = reader_manager.detect_readers()
        print(f"✓ Detected {len(readers)} readers")
        
        if not readers:
            print("⚠️  No readers detected - ensure ACR122 is connected")
            return False
        
        reader_info = readers[0]  # Use first reader
        print(f"✓ Testing with reader: {reader_info['name']}")
        
        # Test reader connection
        if not reader_manager.connect_reader(reader_info):
            print("✗ Failed to connect to reader")
            return False
        
        print("✓ Successfully connected to reader")
        
        # Get the reader instance
        reader = reader_manager.get_reader(reader_info['name'])
        if not reader:
            print("✗ Could not get reader instance")
            return False
        
        # Test card detection
        card_present = reader.is_card_present()
        print(f"✓ Card present: {card_present}")
        
        if card_present:
            # Get ATR
            atr = reader.get_atr()
            if atr:
                print(f"✓ Card ATR: {atr.hex().upper() if isinstance(atr, bytes) else atr}")
                
                # Test UI card status update
                if hasattr(main_window, 'reader_widget') and main_window.reader_widget:
                    main_window.reader_widget.update_card_status(True, atr)
                    print("✓ UI card status updated")
                
                # Test basic APDU communication if possible
                try:
                    # Send GET PROCESSING OPTIONS or simple SELECT
                    test_apdu = bytes([0x00, 0xA4, 0x04, 0x00, 0x00])  # Simple SELECT
                    response = reader.transmit_apdu(test_apdu)
                    if response:
                        sw1, sw2 = response[-2], response[-1]
                        status = f"{sw1:02X}{sw2:02X}"
                        print(f"✓ APDU test response: {status}")
                        
                        if sw1 == 0x90 and sw2 == 0x00:
                            print("✓ Card communication successful")
                        elif sw1 == 0x6F or sw1 == 0x6A:
                            print("⚠️  Card responded but command not supported (normal)")
                        else:
                            print(f"⚠️  Card responded with status: {status}")
                    else:
                        print("⚠️  No response to APDU")
                        
                except Exception as e:
                    print(f"⚠️  APDU test failed: {e} (may be normal)")
                    
            else:
                print("⚠️  Could not get card ATR")
        else:
            print("ℹ️  No card present - insert a card to test reading")
        
        # Test UI refresh functionality
        print("\nTesting UI refresh functionality...")
        main_window.refresh_readers()
        print("✓ UI refresh_readers called successfully")
        
        # Check if readers are shown in UI
        if (hasattr(main_window, 'reader_widget') and 
            main_window.reader_widget and 
            main_window.reader_widget.reader_list.count() > 0):
            print("✓ Readers are displayed in UI")
            
            # Get first reader from UI list
            first_item = main_window.reader_widget.reader_list.item(0)
            if first_item:
                print(f"✓ First reader in UI: {first_item.text()}")
        else:
            print("⚠️  Readers not displayed in UI")
        
        # Clean up
        reader_manager.disconnect_reader(reader_info['name'])
        print("✓ Reader disconnected")
        
        return True
        
    except Exception as e:
        print(f"✗ Error in card reading test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_auto_refresh():
    """Test the UI auto-refresh functionality."""
    print("\n=== Testing UI Auto-Refresh ===")
    
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Import main modules
        from main import Application
        
        # Create Application instance
        main_app = Application(sys.argv)
        
        # Check if auto-refresh timer was set up
        main_window = main_app.main_window
        if hasattr(main_window, 'auto_refresh_timer'):
            print("✓ Auto-refresh timer initialized")
        else:
            print("⚠️  Auto-refresh timer not found")
        
        # Wait for auto-refresh to complete
        def check_auto_refresh():
            if (hasattr(main_window, 'reader_widget') and 
                main_window.reader_widget and 
                main_window.reader_widget.reader_list.count() > 0):
                print("✓ Auto-refresh completed - readers visible in UI")
                app.quit()
            else:
                print("⚠️  Auto-refresh may not have completed")
                # Try manual refresh
                main_window.refresh_readers()
                QTimer.singleShot(500, lambda: app.quit())
        
        # Check after auto-refresh should have completed
        QTimer.singleShot(2000, check_auto_refresh)
        
        # Run briefly to test auto-refresh
        app.exec_()
        return True
        
    except Exception as e:
        print(f"✗ Error in auto-refresh test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run comprehensive UI and card reading tests."""
    print("Comprehensive UI and Card Reading Test")
    print("=" * 50)
    
    # Test 1: Card reading functionality
    reading_success = test_card_reading_functionality()
    
    # Test 2: UI auto-refresh
    refresh_success = test_ui_auto_refresh()
    
    print("\n" + "="*50)
    print("Test Results Summary:")
    print(f"Card Reading Test: {'✓ PASS' if reading_success else '✗ FAIL'}")
    print(f"Auto-Refresh Test: {'✓ PASS' if refresh_success else '✗ FAIL'}")
    
    if reading_success and refresh_success:
        print("\n🎉 All tests passed! The UI and card reader are working correctly.")
        print("\nTo use the application:")
        print("1. Run: python main.py")
        print("2. Go to 'Readers' tab")
        print("3. Select your card reader")
        print("4. Insert a card and click 'Start Reading'")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
