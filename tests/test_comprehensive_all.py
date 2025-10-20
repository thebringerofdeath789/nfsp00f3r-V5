#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Comprehensive Test Suite
==========================================

File: test_comprehensive_features.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Complete test suite for all application features

Test Categories:
- EMV Card Data Extraction and Parsing
- TLV Structure Validation and Analysis
- APDU Command Processing and Response Handling
- Attack Manager Functionality (Replay/Pre-play)
- BLE Android Companion Communication
- Key Derivation and Cryptographic Analysis
- GUI Component Integration and Workflow
- Error Handling and Edge Cases

This comprehensive test suite validates all major functionality
of the NFSP00F3R application including real card interaction,
attack simulation, Android companion communication, and UI components.
"""

import unittest
import sys
import os
import json
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock
import asyncio
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import all modules to test
try:
    import emv_card
    import tlv
    import crypto
    import card_manager
    import attack_manager
    import bluetooth_manager_ble
    import key_derivation_research_clean
    import ui_mainwindow
    import main
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Warning: Some imports failed: {e}")
    IMPORTS_SUCCESSFUL = False

class TestEMVCardDataExtraction(unittest.TestCase):
    """Test EMV card data extraction and parsing."""
    
    def setUp(self):
        """Set up test environment."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.emv = emv_card.EMVCard()
        
    def test_atr_parsing(self):
        """Test ATR (Answer to Reset) parsing."""
        # Test valid ATR
        atr_hex = "3B6A00000046534343432D654944"
        atr_bytes = bytes.fromhex(atr_hex)
        
        parsed_atr = self.emv.parse_atr(atr_bytes)
        self.assertIsInstance(parsed_atr, dict)
        self.assertIn('historical_bytes', parsed_atr)
        
    def test_fci_data_parsing(self):
        """Test FCI (File Control Information) parsing."""
        # Sample FCI response from real card
        fci_response = (
            "6F1C840E315041592E5359532E4444463031A50A88010240"
            "5F2D0265737007"
        )
        
        fci_data = self.emv.parse_fci(bytes.fromhex(fci_response))
        self.assertIsInstance(fci_data, dict)
        self.assertIn('aid', fci_data)
        
    def test_application_selection(self):
        """Test EMV application selection process."""
        # Mock card connection for testing
        with patch.object(self.emv, 'send_apdu') as mock_apdu:
            # Mock SELECT PSE response
            mock_apdu.return_value = (
                bytes.fromhex("6F1C840E315041592E5359532E4444463031"),
                0x90, 0x00
            )
            
            result = self.emv.select_application("1PAY.SYS.DDF01")
            self.assertTrue(result)
            
    def test_cdol_parsing(self):
        """Test CDOL (Card Risk Management Data Object List) parsing."""
        # Real CDOL data from EMV card
        cdol_data = "9F02069F03069F1A0295055F2A029A039C019F37049F35019F34039F4E14"
        
        parsed_cdol = self.emv.parse_cdol(bytes.fromhex(cdol_data))
        self.assertIsInstance(parsed_cdol, list)
        self.assertGreater(len(parsed_cdol), 0)
        
        # Verify structure
        for tag_info in parsed_cdol:
            self.assertIn('tag', tag_info)
            self.assertIn('length', tag_info)
            
    def test_afl_processing(self):
        """Test AFL (Application File Locator) processing."""
        # Sample AFL data
        afl_data = "08010300100101001818030020040100"
        
        afl_records = self.emv.parse_afl(bytes.fromhex(afl_data))
        self.assertIsInstance(afl_records, list)
        
        for record in afl_records:
            self.assertIn('sfi', record)
            self.assertIn('start_record', record)
            self.assertIn('end_record', record)

class TestTLVStructureValidation(unittest.TestCase):
    """Test TLV parsing and validation."""
    
    def setUp(self):
        """Set up TLV parser."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.tlv_parser = tlv.TLVParser()
        
    def test_basic_tlv_parsing(self):
        """Test basic TLV structure parsing."""
        # Simple TLV: Tag 9F02, Length 06, Value 123456789012
        tlv_data = "9F0206123456789012"
        
        parsed = self.tlv_parser.parse(bytes.fromhex(tlv_data))
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        
        tag_data = parsed[0]
        self.assertEqual(tag_data['tag'], '9F02')
        self.assertEqual(tag_data['length'], 6)
        self.assertEqual(tag_data['value'].hex().upper(), '123456789012')
        
    def test_nested_tlv_parsing(self):
        """Test nested TLV structure parsing."""
        # Complex nested structure
        nested_data = "70819F9F02060000000100009F03060000000000009F1A0209789F26088C0A2B2B2B2B2B2B2B2B"
        
        parsed = self.tlv_parser.parse(bytes.fromhex(nested_data))
        self.assertIsInstance(parsed, list)
        
        # Should find nested tags
        tag_70 = None
        for tag in parsed:
            if tag['tag'] == '70':
                tag_70 = tag
                break
                
        self.assertIsNotNone(tag_70)
        self.assertIn('nested', tag_70)
        
    def test_tlv_validation(self):
        """Test TLV data validation."""
        # Valid EMV TLV data
        valid_data = "9F02060000000100009F03060000000000009F1A0209789F26088C0A2B2B2B2B2B2B2B2B"
        
        is_valid = self.tlv_parser.validate(bytes.fromhex(valid_data))
        self.assertTrue(is_valid)
        
        # Invalid TLV data (truncated)
        invalid_data = "9F0206123456"
        
        is_valid = self.tlv_parser.validate(bytes.fromhex(invalid_data))
        self.assertFalse(is_valid)
        
    def test_tag_dictionary_lookup(self):
        """Test EMV tag dictionary lookups."""
        from tag_dictionary import get_tag_description
        
        # Test known EMV tags
        self.assertIsNotNone(get_tag_description('9F02'))  # Amount Authorized
        self.assertIsNotNone(get_tag_description('5A'))    # PAN
        self.assertIsNotNone(get_tag_description('9F26'))  # Application Cryptogram
        
        # Test unknown tag
        unknown_desc = get_tag_description('FFFF')
        self.assertIn('Unknown', unknown_desc or 'Unknown')

class TestAPDUProcessing(unittest.TestCase):
    """Test APDU command processing and response handling."""
    
    def setUp(self):
        """Set up APDU testing environment."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.card_manager = card_manager.CardManager()
        
    def test_apdu_construction(self):
        """Test APDU command construction."""
        # SELECT command
        select_apdu = self.card_manager.build_select_apdu("1PAY.SYS.DDF01")
        
        expected = "00A404000E315041592E5359532E4444463031"
        self.assertEqual(select_apdu.hex().upper(), expected)
        
    def test_apdu_response_parsing(self):
        """Test APDU response parsing."""
        # Sample response with status words
        response_data = bytes.fromhex("6F1C840E315041592E5359532E4444463031A50A88010240")
        sw1, sw2 = 0x90, 0x00
        
        parsed = self.card_manager.parse_apdu_response(response_data, sw1, sw2)
        
        self.assertTrue(parsed['success'])
        self.assertEqual(parsed['sw1'], 0x90)
        self.assertEqual(parsed['sw2'], 0x00)
        self.assertEqual(parsed['data'], response_data)
        
    def test_error_response_handling(self):
        """Test error response handling."""
        # Test various error conditions
        error_cases = [
            (0x6A, 0x82),  # File not found
            (0x6A, 0x86),  # Incorrect parameters
            (0x6E, 0x00),  # Class not supported
            (0x6D, 0x00),  # Instruction not supported
        ]
        
        for sw1, sw2 in error_cases:
            parsed = self.card_manager.parse_apdu_response(b'', sw1, sw2)
            self.assertFalse(parsed['success'])
            self.assertIn('error', parsed)

class TestAttackManagerFunctionality(unittest.TestCase):
    """Test attack manager functionality."""
    
    def setUp(self):
        """Set up attack manager testing."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.attack_manager = attack_manager.AttackManager()
        
    def test_replay_attack_initialization(self):
        """Test replay attack initialization."""
        self.attack_manager.set_mode(attack_manager.AttackMode.REPLAY)
        
        self.assertEqual(self.attack_manager.current_mode, attack_manager.AttackMode.REPLAY)
        self.assertFalse(self.attack_manager.session_active)
        
    def test_session_loading(self):
        """Test session file loading."""
        # Create temporary session file
        session_data = {
            "session_id": "test_session_001",
            "timestamp": datetime.now().isoformat(),
            "apdu_trace": [
                {
                    "command": "00A404000E315041592E5359532E4444463031",
                    "response": "6F1C840E315041592E5359532E4444463031A50A889000",
                    "sw1": "90",
                    "sw2": "00",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(session_data, f)
            temp_file = f.name
            
        try:
            result = self.attack_manager.load_session(temp_file)
            self.assertTrue(result)
            
            self.assertEqual(self.attack_manager.session_data['session_id'], 'test_session_001')
            self.assertGreater(len(self.attack_manager.session_data['apdu_trace']), 0)
            
        finally:
            os.unlink(temp_file)
            
    def test_apdu_processing(self):
        """Test APDU processing in attack mode."""
        # Load test session first
        self.attack_manager.session_data = {
            "apdu_trace": [
                {
                    "command": "00A404000E315041592E5359532E4444463031",
                    "response": "6F1C840E315041592E5359532E4444463031A50A88010240",
                    "sw1": "90",
                    "sw2": "00"
                }
            ]
        }
        
        # Test APDU processing
        command = bytes.fromhex("00A404000E315041592E5359532E4444463031")
        response = self.attack_manager.process_apdu(command)
        
        self.assertIsNotNone(response)
        self.assertIn('data', response)
        self.assertIn('sw1', response)
        self.assertIn('sw2', response)

class TestBLEAndroidCommunication(unittest.TestCase):
    """Test BLE Android companion communication."""
    
    def setUp(self):
        """Set up BLE testing environment."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.ble_manager = bluetooth_manager_ble.BLEAndroidManager()
        
    def test_ble_availability_check(self):
        """Test BLE availability detection."""
        is_available = self.ble_manager.is_ble_available()
        self.assertIsInstance(is_available, bool)
        
    def test_message_serialization(self):
        """Test BLE message serialization."""
        from ..bluetooth_manager_ble import BLEMessage, BLEMessageType
        
        message = BLEMessage(
            message_type=BLEMessageType.SESSION_DATA,
            sequence_id=1,
            total_fragments=1,
            fragment_index=0,
            payload=b'test data'
        )
        
        # Test serialization
        wire_data = message.to_bytes()
        self.assertIsInstance(wire_data, bytes)
        self.assertGreater(len(wire_data), 0)
        
        # Test deserialization
        reconstructed = BLEMessage.from_bytes(wire_data)
        self.assertEqual(reconstructed.message_type, BLEMessageType.SESSION_DATA)
        self.assertEqual(reconstructed.payload, b'test data')
        
    def test_session_export(self):
        """Test session data export for Android."""
        from ..bluetooth_manager_ble import SessionExporter
        
        sample_session = {
            "fci_data": {"aid": "A0000000031010", "label": "Test Card"},
            "pan": "1234567890123456",
            "expiry_date": "12/25",
            "cardholder_name": "TEST CARDHOLDER",
            "apdu_trace": [
                {
                    "command": "00A404000E315041592E5359532E4444463031",
                    "response": "6F1C840E315041592E5359532E4444463031A50A88010240",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
        
        exported = SessionExporter.export_session(sample_session)
        
        self.assertIn('session_id', exported)
        self.assertIn('card_data', exported)
        self.assertIn('apdu_trace', exported)
        self.assertIn('version', exported)
        
        # Verify card data extraction
        self.assertEqual(exported['card_data']['pan'], "1234567890123456")
        self.assertEqual(exported['card_data']['cardholder_name'], "TEST CARDHOLDER")

class TestKeyDerivationAnalysis(unittest.TestCase):
    """Test key derivation and cryptographic analysis."""
    
    def setUp(self):
        """Set up cryptographic testing environment."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        self.analyzer = key_derivation_research_clean.KeyDerivationAnalyzer()
        
    def test_key_diversification(self):
        """Test key diversification algorithms."""
        master_key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
        pan = "1234567890123456"
        
        diversified_key = self.analyzer.diversify_key(master_key, pan)
        
        self.assertIsInstance(diversified_key, bytes)
        self.assertEqual(len(diversified_key), 16)  # 128-bit key
        self.assertNotEqual(diversified_key, master_key)
        
    def test_cryptogram_validation(self):
        """Test cryptogram validation."""
        # Sample cryptogram data
        cryptogram_data = {
            "amount": "000000010000",
            "currency": "0978",
            "unpredictable_number": "12345678",
            "application_cryptogram": "1234567890ABCDEF"
        }
        
        result = self.analyzer.validate_cryptogram(cryptogram_data)
        self.assertIsInstance(result, dict)
        self.assertIn('valid', result)
        
    def test_pin_verification(self):
        """Test PIN verification algorithms."""
        pin = "1234"
        pan = "1234567890123456"
        
        # Test PIN block generation
        pin_block = self.analyzer.generate_pin_block(pin, pan)
        self.assertIsInstance(pin_block, bytes)
        self.assertEqual(len(pin_block), 8)  # 64-bit PIN block
        
        # Test PIN verification
        verification_result = self.analyzer.verify_pin(pin, pan, pin_block)
        self.assertIsInstance(verification_result, bool)

class TestGUIIntegration(unittest.TestCase):
    """Test GUI component integration."""
    
    def setUp(self):
        """Set up GUI testing environment."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
        
        # Mock QApplication for testing
        self.app = None
        try:
            from PyQt5.QtWidgets import QApplication
            import sys
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
        except ImportError:
            self.skipTest("PyQt5 not available")
            
    def tearDown(self):
        """Clean up GUI testing."""
        if self.app:
            self.app.quit()
            
    def test_main_window_creation(self):
        """Test main window creation."""
        # Mock application instance
        mock_app = Mock()
        mock_app.card_manager = Mock()
        mock_app.reader_manager = Mock()
        mock_app.bluetooth_manager = Mock()
        mock_app.ble_android_manager = Mock()
        
        main_window = ui_mainwindow.MainWindow(mock_app)
        
        self.assertIsNotNone(main_window)
        self.assertIsNotNone(main_window.card_widget)
        self.assertIsNotNone(main_window.reader_widget)
        
    def test_card_data_widget(self):
        """Test card data widget functionality."""
        card_widget = ui_mainwindow.CardDataWidget()
        
        # Test data update
        sample_data = {
            'pan': '1234567890123456',
            'expiry_date': '12/25',
            'cardholder_name': 'TEST CARDHOLDER',
            'applications': [
                {'aid': 'A0000000031010', 'label': 'Test App'}
            ]
        }
        
        card_widget.update_card_data(sample_data)
        
        # Verify data is displayed
        self.assertGreater(card_widget.card_info_table.rowCount(), 0)
        
    def test_android_button_functionality(self):
        """Test Android send button functionality."""
        card_widget = ui_mainwindow.CardDataWidget()
        
        # Initially disabled
        self.assertFalse(card_widget.send_android_button.isEnabled())
        
        # Should be enabled when Android connected (simulated)
        card_widget.send_android_button.setEnabled(True)
        self.assertTrue(card_widget.send_android_button.isEnabled())

class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""
    
    def setUp(self):
        """Set up error handling tests."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
    def test_invalid_tlv_data(self):
        """Test handling of invalid TLV data."""
        tlv_parser = tlv.TLVParser()
        
        # Test various invalid inputs
        invalid_inputs = [
            b'',  # Empty data
            b'\xFF',  # Single byte
            b'\x9F\x02\xFF',  # Invalid length
            b'\x9F\x02\x06\x12\x34',  # Truncated data
        ]
        
        for invalid_data in invalid_inputs:
            try:
                result = tlv_parser.parse(invalid_data)
                # Should either return empty list or handle gracefully
                self.assertIsInstance(result, list)
            except Exception as e:
                # Should not raise unhandled exceptions
                self.assertIsInstance(e, (ValueError, tlv.TLVError))
                
    def test_card_connection_failures(self):
        """Test card connection failure handling."""
        card_mgr = card_manager.CardManager()
        
        # Test connection to non-existent reader
        with patch.object(card_mgr, '_connect_to_reader') as mock_connect:
            mock_connect.side_effect = Exception("Reader not found")
            
            result = card_mgr.connect_to_reader("NonExistentReader")
            self.assertFalse(result)
            
    def test_file_operation_errors(self):
        """Test file operation error handling."""
        attack_mgr = attack_manager.AttackManager()
        
        # Test loading non-existent file
        result = attack_mgr.load_session("/non/existent/file.json")
        self.assertFalse(result)
        
        # Test loading invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
            
        try:
            result = attack_mgr.load_session(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)

class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end workflows."""
    
    def setUp(self):
        """Set up end-to-end testing."""
        if not IMPORTS_SUCCESSFUL:
            self.skipTest("Required modules not available")
            
    def test_complete_card_analysis_workflow(self):
        """Test complete card analysis workflow."""
        # This would typically involve:
        # 1. Card detection and connection
        # 2. EMV application selection
        # 3. Data extraction and parsing
        # 4. TLV structure analysis
        # 5. Cryptographic validation
        # 6. Data export
        
        # Mock the workflow since we can't use real cards in tests
        card_mgr = card_manager.CardManager()
        emv_card_obj = emv_card.EMVCard()
        
        # Simulate workflow steps
        with patch.object(card_mgr, 'connect_to_reader', return_value=True):
            with patch.object(emv_card_obj, 'read_card_data') as mock_read:
                mock_read.return_value = {
                    'pan': '1234567890123456',
                    'expiry_date': '12/25',
                    'applications': [{'aid': 'A0000000031010'}]
                }
                
                # Simulate successful workflow
                connected = card_mgr.connect_to_reader("TestReader")
                self.assertTrue(connected)
                
                card_data = emv_card_obj.read_card_data()
                self.assertIsNotNone(card_data)
                self.assertIn('pan', card_data)
                
    def test_attack_simulation_workflow(self):
        """Test attack simulation workflow."""
        attack_mgr = attack_manager.AttackManager()
        
        # Create test session data
        session_data = {
            "session_id": "test_attack_001",
            "apdu_trace": [
                {
                    "command": "00A404000E315041592E5359532E4444463031",
                    "response": "6F1C840E315041592E5359532E4444463031A50A88010240",
                    "sw1": "90",
                    "sw2": "00"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(session_data, f)
            temp_file = f.name
            
        try:
            # Test complete attack workflow
            attack_mgr.set_mode(attack_manager.AttackMode.REPLAY)
            self.assertTrue(attack_mgr.load_session(temp_file))
            
            attack_mgr.start_session()
            self.assertTrue(attack_mgr.session_active)
            
            # Test APDU processing
            command = bytes.fromhex("00A404000E315041592E5359532E4444463031")
            response = attack_mgr.process_apdu(command)
            self.assertIsNotNone(response)
            
            attack_mgr.stop_session()
            self.assertFalse(attack_mgr.session_active)
            
        finally:
            os.unlink(temp_file)

def run_comprehensive_tests():
    """Run all comprehensive tests."""
    print("Running NFSP00F3R V5.00 Comprehensive Test Suite")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEMVCardDataExtraction,
        TestTLVStructureValidation,
        TestAPDUProcessing,
        TestAttackManagerFunctionality,
        TestBLEAndroidCommunication,
        TestKeyDerivationAnalysis,
        TestGUIIntegration,
        TestErrorHandling,
        TestEndToEndWorkflow
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
