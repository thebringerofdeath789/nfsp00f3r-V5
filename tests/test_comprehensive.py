#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Comprehensive Test Suite
==========================================

File: test_comprehensive.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Complete test suite for all NFSP00F3R components

This module provides comprehensive testing for:
- EMV card processing and TLV parsing
- Cryptographic functions and key management
- Transaction engine and replay functionality
- Hardware interfaces and emulation
- Attack modules and security research features
- User interface components and integration

Run with: python -m pytest test_comprehensive.py -v
"""

import unittest
import sys
import os
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestEMVCard(unittest.TestCase):
    """Test EMV card data structures and processing with REAL card data."""
    
    def setUp(self):
        """Set up test fixtures with real card connection."""
        from ..emv_card import EMVCard
        self.card = EMVCard()
        
        # Connect to real card - NO test data allowed
        self.real_card_data = self._read_real_card_data()
        
    def _read_real_card_data(self):
        """Read actual data from inserted EMV card."""
        try:
            from smartcard.System import readers
            
            reader_list = readers()
            if not reader_list:
                self.skipTest("No card readers found")
                
            reader = reader_list[0]
            connection = reader.createConnection()
            connection.connect()
            
            # Read PPSE
            ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 
                       0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 
                       0x00]
            
            response, sw1, sw2 = connection.transmit(ppse_cmd)
            
            if sw1 != 0x90 or sw2 != 0x00:
                self.skipTest("Cannot read card data - ensure EMV card is inserted")
                
            return bytes(response)
            
        except Exception as e:
            self.skipTest(f"Card reading failed: {e}")
        
    def test_card_initialization(self):
        """Test EMV card initialization with real data."""
        self.assertIsNotNone(self.card)
        self.assertEqual(self.card.pan, '')
        self.assertEqual(self.card.expiry_date, '')
        self.assertIsInstance(self.card.applications, list)
        self.assertIsInstance(self.card.tlv_data, dict)
        
        # Test with real card data
        self.assertIsNotNone(self.real_card_data)
        self.assertGreater(len(self.real_card_data), 0)
        
    def test_tlv_parsing(self):
        """Test TLV data parsing."""
        # Test basic TLV parsing
        tlv_data = "5A084761739001010010"  # PAN tag
        self.card.parse_tlv_data(tlv_data)
        
        self.assertIn('5A', self.card.tlv_data)
        self.assertEqual(self.card.tlv_data['5A']['value'], '4761739001010010')
        
    def test_track_data_parsing(self):
        """Test magnetic stripe track data parsing."""
        track2_data = "4761739001010010D25121010000000000"
        self.card.track_data['track2'] = track2_data
        
        # Parse track 2 data
        self.card._parse_track2_string(track2_data)
        
        self.assertEqual(self.card.pan, '4761739001010010')
        self.assertEqual(self.card.expiry_date, '2512')
        
    def test_application_management(self):
        """Test EMV application management."""
        app_data = {
            'aid': 'A0000000041010',
            'label': 'Mastercard',
            'priority': 1
        }
        
        self.card.add_application(app_data)
        self.assertEqual(len(self.card.applications), 1)
        self.assertEqual(self.card.applications[0]['aid'], 'A0000000041010')
        
    def test_data_export_import(self):
        """Test card data export and import."""
        # Set up card data
        self.card.pan = '4761739001010010'
        self.card.expiry_date = '2512'
        self.card.cardholder_name = 'TEST CARD'
        
        # Export to dict
        exported_data = self.card.to_dict()
        
        self.assertIn('pan', exported_data)
        self.assertIn('expiry_date', exported_data)
        self.assertIn('cardholder_name', exported_data)
        
        # Import from dict
        new_card = EMVCard()
        new_card.from_dict(exported_data)
        
        self.assertEqual(new_card.pan, '4761739001010010')
        self.assertEqual(new_card.expiry_date, '2512')
        self.assertEqual(new_card.cardholder_name, 'TEST CARD')

class TestTLVParser(unittest.TestCase):
    """Test TLV parser functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..tlv import TLVParser
        self.parser = TLVParser()
        
    def test_basic_tlv_parsing(self):
        """Test basic TLV parsing."""
        tlv_data = "5A084761739001010010"  # PAN
        parsed = self.parser.parse(tlv_data)
        
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['tag'], '5A')
        self.assertEqual(parsed[0]['length'], 8)
        self.assertEqual(parsed[0]['value'], '4761739001010010')
        
    def test_constructed_tlv_parsing(self):
        """Test constructed TLV parsing."""
        # FCI template with nested data
        tlv_data = "6F1C840E315041592E5359532E4444463031A50A880102500550415920"
        parsed = self.parser.parse(tlv_data)
        
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['tag'], '6F')
        self.assertIn('children', parsed[0])
        
    def test_long_form_length(self):
        """Test long form length encoding."""
        # Create TLV with length > 127
        tag = "9F10"
        length = 200  # Long form length
        value = "01" * 200
        tlv_data = f"{tag}81{length:02X}{value}"
        
        parsed = self.parser.parse(tlv_data)
        
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['tag'], tag)
        self.assertEqual(parsed[0]['length'], length)
        
    def test_validation(self):
        """Test TLV validation."""
        # Valid TLV
        valid_tlv = "5A084761739001010010"
        is_valid, issues = self.parser.validate(valid_tlv)
        self.assertTrue(is_valid)
        self.assertEqual(len(issues), 0)
        
        # Invalid TLV (incomplete)
        invalid_tlv = "5A08476173"
        is_valid, issues = self.parser.validate(invalid_tlv)
        self.assertFalse(is_valid)
        self.assertGreater(len(issues), 0)

class TestCryptography(unittest.TestCase):
    """Test cryptographic functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..crypto import EMVCrypto
        self.crypto = EMVCrypto()
        
    def test_cryptogram_generation(self):
        """Test cryptogram generation and validation."""
        transaction_data = {
            'amount': '000000010000',  # $100.00
            'currency': '0840',        # USD
            'pan': '4761739001010010',
            'pan_sequence': '00',
            'terminal_country': '0840',
            'tvr': '0000000000',
            'transaction_date': '250816',
            'transaction_type': '00',
            'unpredictable_number': '12345678'
        }
        
        # Test ARQC generation
        arqc = self.crypto.generate_arqc(transaction_data)
        self.assertIsNotNone(arqc)
        self.assertEqual(len(arqc), 16)  # 8 bytes = 16 hex chars
        
        # Test TC generation
        tc = self.crypto.generate_tc(transaction_data)
        self.assertIsNotNone(tc)
        self.assertEqual(len(tc), 16)
        
        # Test AAC generation
        aac = self.crypto.generate_aac(transaction_data)
        self.assertIsNotNone(aac)
        self.assertEqual(len(aac), 16)
        
        # Test session key derivation
        session_keys = self.crypto.key_manager.derive_session_keys('4761739001010010', '00')
        self.assertIsNotNone(session_keys)
        self.assertIn('session_key', session_keys)
        
        # Test MAC calculation
        data = bytes.fromhex('123456789ABCDEF0')
        mac = self.crypto.calculate_mac(data, session_keys['session_key'])
        self.assertIsNotNone(mac)
        self.assertEqual(len(mac), 8)  # 4 bytes = 8 hex chars
        
        # Test PIN verification
        pin_block = self.crypto.format_pin_block('1234', '4761739001010010', format_type=0)
        self.assertIsNotNone(pin_block)
        self.assertEqual(len(pin_block), 16)  # 8 bytes = 16 hex chars
        
    def test_data_authentication(self):
        """Test data authentication methods."""
        emv_data = {
            '5A': '4761739001010010',  # PAN
            '5F24': '2512',            # Expiry
            '8F': '01',                # CA Public Key Index
            '90': '01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789',  # Issuer Public Key Certificate
            '92': '0123456789ABCDEF0123456789ABCDEF01234567',  # Issuer Public Key Remainder
            '9F32': '03',              # Issuer Public Key Exponent
            '9F46': '01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789',  # ICC Public Key Certificate
            '9F47': '03',              # ICC Public Key Exponent
            '9F48': '0123456789ABCDEF0123456789ABCDEF01234567'   # ICC Public Key Remainder
        }
        
        # Test SDA
        sda_result = self.crypto.verify_sda(emv_data)
        self.assertIsInstance(sda_result, bool)
        
        # Test DDA
        challenge = b'\x12\x34\x56\x78'
        dda_result = self.crypto.verify_dda(emv_data, challenge)
        self.assertIsInstance(dda_result, bool)
        
        # Test CDA
        ac_data = bytes.fromhex('1234567890ABCDEF')
        cda_result = self.crypto.verify_cda(emv_data, ac_data)
        self.assertIsInstance(cda_result, bool)
        
    def test_pin_processing(self):
        """Test PIN block formatting and verification."""
        pan = '4761739001010010'
        pin = '1234'
        
        # Test different PIN block formats
        for format_type in [0, 1, 2, 3, 4]:
            pin_block = self.crypto.format_pin_block(pin, pan, format_type)
            self.assertIsNotNone(pin_block)
            self.assertEqual(len(pin_block), 16)  # 8 bytes = 16 hex chars
            
        # Test PIN verification
        emv_data = {
            '9F17': '03',  # PIN Try Counter
            '8E': '000000000000000000000000'  # CVM List
        }
        
        result = self.crypto.verify_pin_offline(pin, emv_data)
        self.assertIsInstance(result, bool)

class TestTransactionEngine(unittest.TestCase):
    """Test transaction processing engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('card_manager.CardManager'), \
             patch('readers.ReaderManager'):
            from ..transaction import TransactionEngine
            self.engine = TransactionEngine(Mock(), Mock())
            
    def test_transaction_creation(self):
        """Test transaction creation and management."""
        transaction_id = self.engine.create_transaction(
            'PURCHASE', 1000, '0840',
            merchant_id='123456789',
            terminal_id='12345678'
        )
        
        self.assertIsNotNone(transaction_id)
        self.assertIn(transaction_id, self.engine.active_transactions)
        
        transaction = self.engine.active_transactions[transaction_id]
        self.assertEqual(transaction.amount, 1000)
        self.assertEqual(transaction.currency_code, '0840')
        
    def test_cdol_parsing(self):
        """Test CDOL data parsing and building."""
        # Test CDOL1 parsing
        cdol1_data = "9F0206" + "9F0306" + "9F1A02" + "9502" + "5F2A02" + "9A03" + "9C01" + "9F3704"
        cdol_tags = self.engine._parse_cdol(cdol1_data)
        
        expected_tags = [
            ('9F02', 6),  # Amount Authorized
            ('9F03', 6),  # Amount Other
            ('9F1A', 2),  # Terminal Country Code
            ('95', 2),    # TVR
            ('5F2A', 2),  # Transaction Currency Code
            ('9A', 3),    # Transaction Date
            ('9C', 1),    # Transaction Type
            ('9F37', 4)   # Unpredictable Number
        ]
        
        self.assertEqual(len(cdol_tags), len(expected_tags))
        for i, (tag, length) in enumerate(expected_tags):
            self.assertEqual(cdol_tags[i], (tag, length))
            
    def test_terminal_verification_results(self):
        """Test TVR (Terminal Verification Results) management."""
        transaction_id = self.engine.create_transaction('PURCHASE', 1000)
        transaction = self.engine.active_transactions[transaction_id]
        
        # Test TVR bit setting
        transaction.set_tvr_bit(0, 7)  # Set bit 7 of byte 0
        tvr_bytes = bytes.fromhex(transaction.tvr)
        self.assertEqual(tvr_bytes[0] & 0x80, 0x80)
        
        # Test TVR bit clearing
        transaction.clear_tvr_bit(0, 7)  # Clear bit 7 of byte 0
        tvr_bytes = bytes.fromhex(transaction.tvr)
        self.assertEqual(tvr_bytes[0] & 0x80, 0x00)

class TestAttackModules(unittest.TestCase):
    """Test security research attack modules."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..attack_modules import PINBruteForcer, CryptogramAnalyzer
        self.pin_attacker = PINBruteForcer(Mock(), Mock())
        self.crypto_analyzer = CryptogramAnalyzer()
        
    def test_pin_generation_strategies(self):
        """Test PIN generation strategies."""
        # Test date-based PIN generation
        card_data = {
            'expiry_date': '2512',  # December 2025
            'issue_date': '2301'    # January 2023
        }
        
        date_pins = self.pin_attacker.generate_date_based_pins(card_data)
        self.assertIn('2512', date_pins)  # MMYY
        self.assertIn('1225', date_pins)  # YYMM
        
        # Test sequential PIN generation
        sequential_pins = self.pin_attacker.generate_sequential_pins()
        self.assertIn('1234', sequential_pins)
        self.assertIn('0000', sequential_pins)
        self.assertIn('9876', sequential_pins)
        
    def test_cryptogram_analysis(self):
        """Test cryptogram pattern analysis."""
        # Add test cryptograms
        test_cryptograms = [
            {
                'arqc': '1234567890ABCDEF',
                'amount': 1000,
                'pan': '4761739001010010',
                'timestamp': '2025-08-16 10:00:00'
            },
            {
                'arqc': 'FEDCBA0987654321',
                'amount': 2000,
                'pan': '4761739001010010',
                'timestamp': '2025-08-16 10:01:00'
            },
            {
                'arqc': '1234567890ABCDEF',  # Duplicate
                'amount': 1000,
                'pan': '4761739001010010',
                'timestamp': '2025-08-16 10:02:00'
            }
        ]
        
        for crypto in test_cryptograms:
            self.crypto_analyzer.add_cryptogram(crypto)
            
        # Analyze patterns
        analysis = self.crypto_analyzer.analyze_patterns()
        
        self.assertEqual(analysis['total_cryptograms'], 3)
        self.assertEqual(analysis['unique_cryptograms'], 2)
        self.assertIn('Duplicate cryptograms detected', analysis['patterns_found'])

class TestHardwareEmulation(unittest.TestCase):
    """Test hardware emulation and cloning."""
    
    def setUp(self):
        """Set up test fixtures."""
        from ..hardware_emulation import CardCloner, CloneProfile
        self.cloner = CardCloner(Mock(), Mock())
        
        # Create test profile
        self.test_profile = CloneProfile(
            name='test_card',
            card_type='EMV',
            atr=bytes.fromhex('3B8F8001804F0CA000000306030001000000006A'),
            tlv_data={'5A': '4761739001010010', '5F24': '2512'},
            track_data={'track2': '4761739001010010D25121010000000000'},
            emv_applications=[],
            clone_timestamp=1692172800.0,
            source_reader='PC/SC'
        )
        
    def test_profile_creation(self):
        """Test clone profile creation and management."""
        card_data = {
            'card_type': 'EMV',
            'atr': '3B8F8001804F0CA000000306030001000000006A',
            'tlv_data': {'5A': '4761739001010010'},
            'track_data': {'track2': '4761739001010010D25121010000000000'},
            'applications': [],
            'source_reader': 'PC/SC'
        }
        
        success = self.cloner.clone_card(card_data, 'software_emulation', 'test_clone')
        self.assertTrue(success)
        self.assertIn('test_clone', self.cloner.clone_profiles)
        
    def test_profile_export_import(self):
        """Test profile export and import."""
        # Add test profile
        self.cloner.clone_profiles['test_card'] = self.test_profile
        
        # Export profile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = f.name
            
        try:
            success = self.cloner.export_profile('test_card', export_path)
            self.assertTrue(success)
            
            # Verify export file
            with open(export_path, 'r') as f:
                exported_data = json.load(f)
                
            self.assertEqual(exported_data['name'], 'test_card')
            self.assertEqual(exported_data['card_type'], 'EMV')
            
            # Clear profiles and import
            self.cloner.clone_profiles.clear()
            success = self.cloner.import_profile(export_path)
            self.assertTrue(success)
            self.assertIn('test_card', self.cloner.clone_profiles)
            
        finally:
            os.unlink(export_path)

class TestUserInterface(unittest.TestCase):
    """Test user interface components."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for UI testing."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
            
    def test_main_window_creation(self):
        """Test main window initialization."""
        from ..ui_mainwindow import MainWindow
        
        window = MainWindow()
        self.assertIsNotNone(window)
        
        # Check that all tabs are created
        central_widget = window.centralWidget()
        self.assertIsNotNone(central_widget)
        
        # Check tab count (should have at least 4 tabs)
        tab_count = central_widget.count()
        self.assertGreaterEqual(tab_count, 4)
        
    def test_card_data_widget(self):
        """Test card data display widget."""
        from ..ui_mainwindow import CardDataWidget
        
        widget = CardDataWidget()
        self.assertIsNotNone(widget)
        
        # Test card data update
        test_card_data = {
            'atr': '3B8F8001804F0CA000000306030001000000006A',
            'card_type': 'EMV',
            'pan': '4761739001010010',
            'expiry_date': '2512',
            'cardholder_name': 'TEST CARD',
            'applications': [],
            'tlv_data': {},
            'track_data': {},
            'raw_responses': []
        }
        
        widget.update_card_data(test_card_data)
        
        # Verify data is displayed
        self.assertGreater(widget.card_info_table.rowCount(), 0)
        
    def test_transaction_widget(self):
        """Test transaction control widget."""
        from ..ui_mainwindow import TransactionWidget
        
        widget = TransactionWidget()
        self.assertIsNotNone(widget)
        
        # Test transaction parameter setting
        widget.amount_edit.setText('1000')
        widget.currency_edit.setText('0840')
        widget.merchant_id_edit.setText('123456789')
        
        self.assertEqual(widget.amount_edit.text(), '1000')
        self.assertEqual(widget.currency_edit.text(), '0840')
        self.assertEqual(widget.merchant_id_edit.text(), '123456789')

class TestIntegration(unittest.TestCase):
    """Test component integration."""
    
    def test_card_manager_integration(self):
        """Test card manager with EMV card integration."""
        with patch('readers.ReaderManager'):
            from ..card_manager import CardManager
            from ..emv_card import EMVCard
            
            manager = CardManager(Mock())
            
            # Create test card
            card = EMVCard()
            card.pan = '4761739001010010'
            card.expiry_date = '2512'
            card.cardholder_name = 'TEST CARD'
            
            # Add card to manager
            card_id = manager.add_card(card)
            self.assertIsNotNone(card_id)
            
            # Retrieve card
            retrieved_card = manager.get_card(card_id)
            self.assertIsNotNone(retrieved_card)
            self.assertEqual(retrieved_card.pan, '4761739001010010')
            
    def test_transaction_crypto_integration(self):
        """Test transaction engine with crypto integration."""
        with patch('card_manager.CardManager'), \
             patch('readers.ReaderManager'):
            from ..transaction import TransactionEngine
            from ..crypto import EMVCrypto
            
            engine = TransactionEngine(Mock(), Mock())
            crypto = EMVCrypto()
            
            # Create transaction
            transaction_id = engine.create_transaction('PURCHASE', 1000)
            transaction = engine.active_transactions[transaction_id]
            
            # Generate cryptogram data
            transaction_data = {
                'amount': f'{transaction.amount:012d}',
                'currency': transaction.currency_code,
                'pan': '4761739001010010',
                'pan_sequence': '00',
                'terminal_country': '0840',
                'tvr': transaction.tvr,
                'transaction_date': transaction.transaction_date,
                'transaction_type': transaction.transaction_type.value,
                'unpredictable_number': transaction.unpredictable_number
            }
            
            # Test cryptogram generation
            arqc = crypto.generate_arqc(transaction_data)
            self.assertIsNotNone(arqc)
            self.assertEqual(len(arqc), 16)

def run_all_tests():
    """Run all test suites."""
    print("🧪 Running NFSP00F3R V5.00 Comprehensive Test Suite")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestEMVCard,
        TestTLVParser,
        TestCryptography,
        TestTransactionEngine,
        TestAttackModules,
        TestHardwareEmulation,
        TestUserInterface,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
            
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
            
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed. Please review the output above.")
        
    return result.wasSuccessful()

if __name__ == '__main__':
    # Run tests when executed directly
    run_all_tests()
