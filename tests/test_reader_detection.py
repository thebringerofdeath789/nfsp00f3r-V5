#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card Reader Detection Test Script
Tests the reader detection functionality to identify issues.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pcsc_availability():
    """Test PC/SC availability."""
    print("\n=== Testing PC/SC Availability ===")
    try:
        import smartcard
        from smartcard.System import readers
        print("✓ PC/SC library (pyscard) is available")
        
        # Test reader enumeration
        reader_list = readers()
        print(f"✓ Found {len(reader_list)} PC/SC readers:")
        for i, reader in enumerate(reader_list):
            print(f"  {i+1}. {reader}")
        
        if not reader_list:
            print("⚠️  No PC/SC readers detected")
            print("   - Make sure your card reader is connected")
            print("   - Check Windows Device Manager for driver issues")
            print("   - Try installing PC/SC Lite or Windows Smart Card service")
        
        return len(reader_list) > 0
        
    except ImportError as e:
        print(f"✗ PC/SC not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing PC/SC: {e}")
        return False

def test_serial_devices():
    """Test serial device detection."""
    print("\n=== Testing Serial Device Detection ===")
    try:
        import serial
        import serial.tools.list_ports
        print("✓ PySerial library is available")
        
        ports = serial.tools.list_ports.comports()
        print(f"✓ Found {len(ports)} serial ports:")
        
        for port in ports:
            print(f"  - {port.device}: {port.description}")
            if port.manufacturer:
                print(f"    Manufacturer: {port.manufacturer}")
            if port.product:
                print(f"    Product: {port.product}")
        
        if not ports:
            print("⚠️  No serial devices detected")
        
        return len(ports) > 0
        
    except ImportError as e:
        print(f"✗ PySerial not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing serial devices: {e}")
        return False

def test_nfc_library():
    """Test NFCPy availability."""
    print("\n=== Testing NFCPy Library ===")
    try:
        import nfc
        print("✓ NFCPy library is available")
        
        # Try to create a contactless interface
        try:
            clf = nfc.ContactlessFrontend()
            print("✓ NFCPy contactless frontend created successfully")
            clf.close()
        except Exception as e:
            print(f"⚠️  Could not create NFCPy frontend: {e}")
        
        return True
        
    except ImportError as e:
        print(f"✗ NFCPy not available: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing NFCPy: {e}")
        return False

def test_reader_manager():
    """Test the ReaderManager class."""
    print("\n=== Testing ReaderManager ===")
    try:
        from readers import ReaderManager
        print("✓ ReaderManager import successful")
        
        # Create reader manager
        reader_manager = ReaderManager()
        print("✓ ReaderManager instance created")
        
        # Test reader detection
        detected_readers = reader_manager.detect_readers()
        print(f"✓ Reader detection completed: {len(detected_readers)} readers found")
        
        if detected_readers:
            print("   Detected readers:")
            for i, reader in enumerate(detected_readers):
                print(f"     {i+1}. {reader['name']} ({reader['type']})")
                print(f"        Description: {reader['description']}")
        else:
            print("⚠️  No readers detected by ReaderManager")
        
        return len(detected_readers) > 0
        
    except Exception as e:
        print(f"✗ Error testing ReaderManager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_card_reader_connection():
    """Test connecting to a card reader."""
    print("\n=== Testing Card Reader Connection ===")
    try:
        from readers import ReaderManager
        
        reader_manager = ReaderManager()
        detected_readers = reader_manager.detect_readers()
        
        if not detected_readers:
            print("⚠️  No readers to test connection")
            return False
        
        # Try to connect to the first reader
        reader_info = detected_readers[0]
        print(f"Attempting to connect to: {reader_info['name']}")
        
        success = reader_manager.connect_reader(reader_info)
        if success:
            print("✓ Successfully connected to reader")
            
            # Test basic operations if possible
            connected_readers = reader_manager.get_connected_readers()
            print(f"✓ Connected readers: {connected_readers}")
            
            # Disconnect
            reader_manager.disconnect_reader(reader_info['name'])
            print("✓ Successfully disconnected from reader")
            
            return True
        else:
            print("✗ Failed to connect to reader")
            return False
            
    except Exception as e:
        print(f"✗ Error testing reader connection: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all reader tests."""
    print("Card Reader Detection and Testing Script")
    print("=" * 50)
    
    results = {
        'pcsc': test_pcsc_availability(),
        'serial': test_serial_devices(),
        'nfc': test_nfc_library(),
        'reader_manager': test_reader_manager(),
        'connection': test_card_reader_connection()
    }
    
    print("\n=== Test Results Summary ===")
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name.upper()}: {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if not any(results.values()):
        print("\n⚠️  All tests failed - possible issues:")
        print("   1. No card readers connected")
        print("   2. Missing drivers")
        print("   3. PC/SC service not running")
        print("   4. USB permissions (on Linux)")
    
    elif not results['connection']:
        print("\n⚠️  Readers detected but connection failed - possible issues:")
        print("   1. Reader in use by another application")
        print("   2. Driver issues")
        print("   3. Hardware malfunction")

if __name__ == "__main__":
    main()
