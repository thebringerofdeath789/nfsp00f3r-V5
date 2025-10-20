#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Test Script
Tests the UI functionality and reader detection integration.
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

def test_ui_initialization():
    """Test UI initialization and reader detection."""
    print("\n=== Testing UI Initialization ===")
    
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Import main modules
        from main import Application
        from ui_mainwindow import MainWindow
        from readers import ReaderManager
        
        # Create Application instance (which initializes all managers)
        main_app = Application(sys.argv)
        
        # Check if reader_manager is available
        if hasattr(main_app, 'reader_manager'):
            print("✓ ReaderManager is available in Application")
            
            # Test reader detection through the app
            readers = main_app.reader_manager.detect_readers()
            print(f"✓ Detected {len(readers)} readers through Application")
            
            # Check MainWindow initialization
            if hasattr(main_app, 'main_window'):
                main_window = main_app.main_window
                print("✓ MainWindow is available")
                
                # Check if reader widget is initialized
                if hasattr(main_window, 'reader_widget') and main_window.reader_widget:
                    print("✓ ReaderControlWidget is initialized")
                    
                    # Try to trigger reader refresh through UI
                    print("Triggering refresh_readers through UI...")
                    main_window.refresh_readers()
                    print("✓ refresh_readers method called successfully")
                    
                    # Check if readers were updated in UI
                    if hasattr(main_window, '_detected_readers'):
                        ui_readers = main_window._detected_readers
                        print(f"✓ UI has {len(ui_readers)} readers in _detected_readers")
                        
                        # Check if reader widget shows readers
                        widget_readers = main_window.reader_widget._readers
                        print(f"✓ ReaderWidget has {len(widget_readers)} readers")
                        
                        # Check reader list widget
                        list_count = main_window.reader_widget.reader_list.count()
                        print(f"✓ Reader list widget shows {list_count} items")
                        
                        if list_count > 0:
                            # Get first item text
                            first_item = main_window.reader_widget.reader_list.item(0)
                            if first_item:
                                print(f"✓ First reader in list: {first_item.text()}")
                        
                    else:
                        print("⚠️  MainWindow._detected_readers not found")
                else:
                    print("✗ ReaderControlWidget not initialized")
            else:
                print("✗ MainWindow not available in Application")
        else:
            print("✗ ReaderManager not available in Application")
        
        # Don't start event loop, just test initialization
        return True
        
    except Exception as e:
        print(f"✗ Error testing UI: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_with_actual_display():
    """Test UI with actual display for manual verification."""
    print("\n=== Testing UI with Display ===")
    
    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Import main modules
        from main import Application
        
        # Create Application instance
        main_app = Application(sys.argv)
        
        # The application should show the window automatically
        # unless --no-gui was specified
        
        # Set up a timer to automatically refresh readers after startup
        def auto_refresh():
            print("Auto-refreshing readers...")
            if hasattr(main_app, 'main_window') and main_app.main_window:
                main_app.main_window.refresh_readers()
        
        # Trigger auto-refresh after 2 seconds
        timer = QTimer()
        timer.singleShot(2000, auto_refresh)
        
        print("UI should be displayed now. Check for:")
        print("1. Main window with tabs")
        print("2. 'Readers' tab with available readers")
        print("3. ACS ACR122 0 reader should be listed")
        print("4. Card status should show card detected")
        print("\nPress Ctrl+C to exit or close the window")
        
        # Start event loop for manual testing
        return app.exec_()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 0
    except Exception as e:
        print(f"✗ Error in UI display test: {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Run UI tests."""
    print("UI Testing Script for NFSP00F3R")
    print("=" * 40)
    
    # Test 1: Initialization without display
    init_success = test_ui_initialization()
    
    if init_success:
        print("\n" + "="*50)
        choice = input("\nDo you want to test the UI with actual display? (y/n): ")
        if choice.lower() in ['y', 'yes']:
            return test_ui_with_actual_display()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
