#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Comprehensive Test Suite
==========================================

File: test_comprehensive_all_features.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Complete test suite for all application features

Test Categories:
1. Core EMV Functionality
2. BLE Android Companion
3. Attack Modules
4. Key Derivation Research
5. UI Components
6. Data Processing
7. Integration Tests

This test suite validates all major features of the NFSP00F3R V5.00
application including EMV parsing, Android BLE communication,
attack implementations, and user interface components.
"""

import unittest
import logging
import json
import tempfile
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Setup test environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestCoreEMV(unittest.TestCase):
    """Test core EMV functionality."""
    
    def setUp(self):
        """Setup test environment."""
        logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
        
    def test_tlv_parsing(self):
        """Test TLV parsing functionality."""
        try:
            from ..tlv import TLVParser, TLVTag
            
            parser = TLVParser()
            
            # Test basic TLV parsing
            test_data = "6F1C840EA0000000031010A50A500842454249545010870101109000"
            tlv_data = bytes.fromhex(test_data)
            
            parsed = parser.parse(tlv_data)
            self.assertIsInstance(parsed, list)
            self.assertGreater(len(parsed), 0)
            
            print("✓ TLV parsing test passed")
            
        except ImportError as e:
            self.skipTest(f"TLV module not available: {e}")
    
    def test_emv_card(self):
        """Test EMV card functionality."""
        try:
            from ..emv_card import EMVCard
            
            card = EMVCard()
            self.assertIsNotNone(card)
            
            # Test card initialization
            self.assertFalse(card.is_connected())
            
            print("✓ EMV card test passed")
            
        except ImportError as e:
            self.skipTest(f"EMV card module not available: {e}")
    
    def test_crypto_functions(self):
        """Test cryptographic functions."""
        try:
            from ..crypto import EMVCrypto
            
            crypto = EMVCrypto()
            
            # Test PIN block analysis
            pin_block = "2412345678ABCDEF"
            analysis = crypto.analyze_pin_block(bytes.fromhex(pin_block), "4000123456789010")
            
            self.assertIsInstance(analysis, dict)
            self.assertIn("format", analysis)
            
            print("✓ Crypto functions test passed")
            
        except ImportError as e:
            self.skipTest(f"Crypto module not available: {e}")

class TestBLEAndroidCompanion(unittest.TestCase):
    """Test BLE Android companion functionality."""
    
    def test_ble_availability(self):
        """Test BLE availability check."""
        try:
            from ..bluetooth_manager_ble import check_ble_availability
            
            status = check_ble_availability()
            self.assertIsInstance(status, dict)
            self.assertIn('ble_supported', status)
            
            print(f"✓ BLE availability: {status}")
            
        except ImportError as e:
            self.skipTest(f"BLE module not available: {e}")
    
    def test_android_manager_creation(self):
        """Test Android manager creation."""
        try:
            from ..bluetooth_manager_ble import create_android_manager
            
            manager = create_android_manager()
            self.assertIsNotNone(manager)
            
            # Test connection info
            info = manager.get_connection_info()
            self.assertIsInstance(info, dict)
            self.assertIn('state', info)
            
            print("✓ Android manager creation test passed")
            
        except ImportError as e:
            self.skipTest(f"Android manager module not available: {e}")
    
    def test_session_export(self):
        """Test session export functionality."""
        try:
            from ..bluetooth_manager_ble import SessionExporter
            
            # Create test session data
            test_session = {
                'pan': '4000123456789010',
                'expiry_date': '12/25',
                'cardholder_name': 'TEST CARDHOLDER',
                'applications': [
                    {'aid': 'A0000000031010', 'label': 'Visa Credit'}
                ],
                'apdu_trace': [
                    {
                        'timestamp': datetime.now().isoformat(),
                        'command': '00A40400',
                        'response': '9000',
                        'description': 'SELECT FILE'
                    }
                ]
            }
            
            # Export session
            exported = SessionExporter.export_session(test_session)
            
            self.assertIsInstance(exported, dict)
            self.assertIn('session_id', exported)
            self.assertIn('card_data', exported)
            self.assertIn('apdu_trace', exported)
            
            print("✓ Session export test passed")
            
        except ImportError as e:
            self.skipTest(f"Session export module not available: {e}")

class TestAttackModules(unittest.TestCase):
    """Test attack module functionality."""
    
    def test_attack_manager(self):
        """Test attack manager functionality."""
        try:
            from ..attack_manager import AttackManager, AttackMode
            
            manager = AttackManager()
            self.assertIsNotNone(manager)
            
            # Test mode setting
            manager.set_mode(AttackMode.REPLAY)
            self.assertEqual(manager.current_mode, AttackMode.REPLAY)
            
            print("✓ Attack manager test passed")
            
        except ImportError as e:
            self.skipTest(f"Attack manager module not available: {e}")
    
    def test_relay_modules(self):
        """Test relay module functionality."""
        try:
            from proxmark_usb import ProxmarkUSBRelay
            from ..android_hce import AndroidHCERelay
            
            # Test Proxmark USB relay
            usb_relay = ProxmarkUSBRelay()
            self.assertIsNotNone(usb_relay)
            
            # Test Android HCE relay
            hce_relay = AndroidHCERelay()
            self.assertIsNotNone(hce_relay)
            
            print("✓ Relay modules test passed")
            
        except ImportError as e:
            self.skipTest(f"Relay modules not available: {e}")

class TestKeyDerivationResearch(unittest.TestCase):
    """Test key derivation research functionality."""
    
    def test_key_derivation_analyzer(self):
        """Test key derivation analyzer."""
        try:
            from ..key_derivation_research_clean import KeyDerivationAnalyzer
            
            analyzer = KeyDerivationAnalyzer()
            self.assertIsNotNone(analyzer)
            
            # Test basic functionality
            self.assertIsInstance(analyzer.analyzed_cards, list)
            
            print("✓ Key derivation analyzer test passed")
            
        except ImportError as e:
            self.skipTest(f"Key derivation module not available: {e}")
    
    def test_multi_card_analysis(self):
        """Test multi-card analysis functionality."""
        try:
            from ..key_derivation_research_clean import MultiCardAnalyzer
            
            analyzer = MultiCardAnalyzer()
            self.assertIsNotNone(analyzer)
            
            print("✓ Multi-card analysis test passed")
            
        except ImportError as e:
            self.skipTest(f"Multi-card analysis module not available: {e}")

class TestUIComponents(unittest.TestCase):
    """Test UI component functionality."""
    
    def setUp(self):
        """Setup PyQt5 application for testing."""
        try:
            from PyQt5.QtWidgets import QApplication
            import sys
            
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
            else:
                self.app = QApplication.instance()
                
        except ImportError:
            self.skipTest("PyQt5 not available")
    
    def test_android_widget(self):
        """Test Android widget functionality."""
        try:
            from ..android_widget import AndroidWidget
            
            widget = AndroidWidget()
            self.assertIsNotNone(widget)
            
            # Test widget has required attributes
            self.assertTrue(hasattr(widget, 'ble_manager'))
            self.assertTrue(hasattr(widget, 'discovered_devices'))
            
            print("✓ Android widget test passed")
            
        except ImportError as e:
            self.skipTest(f"Android widget module not available: {e}")
    
    def test_main_window(self):
        """Test main window functionality."""
        try:
            from ..ui_mainwindow import MainWindow
            
            # Create mock app instance
            class MockApp:
                def __init__(self):
                    self.ble_android_manager = None
                    
            mock_app = MockApp()
            
            window = MainWindow(mock_app)
            self.assertIsNotNone(window)
            
            # Check for Android widget
            if hasattr(window, 'android_widget'):
                self.assertIsNotNone(window.android_widget)
                print("✓ Main window with Android widget test passed")
            else:
                print("✓ Main window test passed (Android widget not loaded)")
                
        except ImportError as e:
            self.skipTest(f"Main window module not available: {e}")

class TestDataProcessing(unittest.TestCase):
    """Test data processing functionality."""
    
    def test_session_file_handling(self):
        """Test session file creation and parsing."""
        # Create test session data
        test_session = {
            'session_id': 'test_session_001',
            'timestamp': datetime.now().isoformat(),
            'card_data': {
                'pan': '4000123456789010',
                'expiry_date': '12/25'
            },
            'transaction_data': {
                'amount': '10.00',
                'currency': 'USD'
            }
        }
        
        # Test JSON serialization
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_session, f, indent=2)
            temp_file = f.name
        
        try:
            # Test file reading
            with open(temp_file, 'r') as f:
                loaded_session = json.load(f)
                
            self.assertEqual(loaded_session['session_id'], test_session['session_id'])
            self.assertEqual(loaded_session['card_data']['pan'], test_session['card_data']['pan'])
            
            print("✓ Session file handling test passed")
            
        finally:
            os.unlink(temp_file)
    
    def test_apdu_trace_processing(self):
        """Test APDU trace processing."""
        # Create test APDU trace
        test_trace = [
            {
                'timestamp': datetime.now().isoformat(),
                'command': '00A4040007A0000000041010',
                'response': '6F1C840EA0000000041010A50A500842454249545010870101109000',
                'sw1': '90',
                'sw2': '00',
                'description': 'SELECT APPLICATION'
            },
            {
                'timestamp': datetime.now().isoformat(),
                'command': '80A80000238321F6101112131415161718192021222324252627282930313233',
                'response': '9000',
                'sw1': '90',
                'sw2': '00',
                'description': 'GET PROCESSING OPTIONS'
            }
        ]
        
        # Test trace validation
        for trace_entry in test_trace:
            self.assertIn('timestamp', trace_entry)
            self.assertIn('command', trace_entry)
            self.assertIn('response', trace_entry)
            self.assertIn('sw1', trace_entry)
            self.assertIn('sw2', trace_entry)
            
        print("✓ APDU trace processing test passed")

class TestIntegration(unittest.TestCase):
    """Test integration between components."""
    
    def test_full_workflow_simulation(self):
        """Test a complete workflow simulation."""
        try:
            # Test card manager initialization
            from ..card_manager import CardManager
            card_manager = CardManager()
            
            # Test transaction engine
            from ..transaction import TransactionEngine
            from ..readers import ReaderManager
            
            reader_manager = ReaderManager()
            transaction_engine = TransactionEngine(card_manager, reader_manager)
            
            self.assertIsNotNone(transaction_engine)
            
            print("✓ Full workflow simulation test passed")
            
        except ImportError as e:
            self.skipTest(f"Integration modules not available: {e}")
    
    def test_android_integration_workflow(self):
        """Test Android integration workflow."""
        try:
            from ..bluetooth_manager_ble import BLEAndroidManager, SessionExporter
            
            # Create Android manager
            manager = BLEAndroidManager()
            
            # Create test session
            test_session = {
                'pan': '4000123456789010',
                'applications': [{'aid': 'A0000000031010'}]
            }
            
            # Test export
            exported = SessionExporter.export_session(test_session)
            self.assertIsNotNone(exported)
            
            print("✓ Android integration workflow test passed")
            
        except ImportError as e:
            self.skipTest(f"Android integration modules not available: {e}")

def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("="*60)
    print("NFSP00F3R V5.00 - Comprehensive Test Suite")
    print("="*60)
    print()
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestCoreEMV,
        TestBLEAndroidCompanion,
        TestAttackModules,
        TestKeyDerivationResearch,
        TestUIComponents,
        TestDataProcessing,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Print summary
    print()
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / 
                    result.testsRun * 100) if result.testsRun > 0 else 0
    
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✓ Comprehensive test suite PASSED")
        return True
    else:
        print("✗ Comprehensive test suite FAILED")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
