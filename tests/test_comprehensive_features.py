#!/usr/bin/env python3
"""
Comprehensive test suite for all advanced EMV parsing, ODA, PIN block analysis,
and UI features. Tests real card data parsing without test/demo keys.
"""

import unittest
import logging
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..emv_card import EMVCard
from ..tlv import TLVParser
from ..ui_mainwindow import CardDataWidget

class TestAdvancedTLVParsing(unittest.TestCase):
    """Test advanced TLV parsing with EMV validation."""
    
    def setUp(self):
        self.parser = TLVParser()
        self.emv_card = EMVCard()
        
    def test_luhn_algorithm(self):
        """Test Luhn algorithm implementation."""
        # Valid test PANs (using Luhn-valid test numbers)
        valid_pans = [
            "4111111111111111",  # Visa test
            "5555555555554444",  # MasterCard test
            "378282246310005",   # Amex test
        ]
        
        for pan in valid_pans:
            self.assertTrue(self.parser._luhn_check(pan), f"PAN {pan} should be valid")
            
        # Invalid PANs
        invalid_pans = [
            "4111111111111112",  # Wrong check digit
            "1234567890123456",  # Invalid sequence
        ]
        
        for pan in invalid_pans:
            self.assertFalse(self.parser._luhn_check(pan), f"PAN {pan} should be invalid")
    
    def test_emv_structure_validation(self):
        """Test EMV structure validation."""
        # Test CDOL validation
        test_data = {
            "8C": "9F0206",  # CDOL1
            "8D": "9F0206",  # CDOL2
            "94": "18011A03",  # AFL
        }
        
        # Should not raise exception for valid EMV data
        try:
            self.parser._validate_emv_structure(test_data)
        except Exception as e:
            self.fail(f"EMV validation failed unexpectedly: {e}")
    
    def test_cdol_parsing(self):
        """Test CDOL1/CDOL2 parsing and extraction."""
        # Test CDOL data parsing
        cdol_data = "9F02069F03069F1A0295055F2A029A039C019F37049F35019F45029F4C089F34039F21039F7C14"
        
        try:
            parsed = self.parser.parse_tlv(bytes.fromhex(cdol_data))
            self.assertIsInstance(parsed, list)
            self.assertGreater(len(parsed), 0)
        except Exception as e:
            self.fail(f"CDOL parsing failed: {e}")

class TestODAParsing(unittest.TestCase):
    """Test Offline Data Authentication parsing."""
    
    def setUp(self):
        self.emv_card = EMVCard()
        
    def test_oda_structure_parsing(self):
        """Test ODA structure parsing for SDA/DDA/CDA."""
        # Mock ODA data
        mock_oda_data = {
            "82": "1980",  # AIP - SDA supported
            "8F": "01",    # Certification Authority Public Key Index
            "90": "1234567890ABCDEF" * 16,  # Issuer Public Key Certificate (mock)
            "92": "FEDCBA0987654321" * 8,   # Issuer Public Key Remainder (mock)
            "93": "ABCDEF1234567890" * 32,  # Signed Static Application Data (mock)
        }
        
        try:
            oda_result = self.emv_card.parse_oda_structures(mock_oda_data)
            self.assertIsInstance(oda_result, dict)
            self.assertIn('authentication_method', oda_result)
        except Exception as e:
            self.fail(f"ODA parsing failed: {e}")
    
    def test_certificate_decoding(self):
        """Test EMV certificate decoding."""
        # Mock certificate data (proper length)
        mock_cert = bytes([0x6A] + [0x01] * 142 + [0xBC])  # 144 bytes total
        
        try:
            decoded = self.emv_card.decode_emv_certificate(mock_cert)
            self.assertIsInstance(decoded, dict)
            self.assertIn('header', decoded)
            self.assertIn('format', decoded)
        except Exception as e:
            self.fail(f"Certificate decoding failed: {e}")
    
    def test_signature_decoding(self):
        """Test EMV signature decoding."""
        # Mock signature data (proper length)
        mock_sig = bytes([0x6A] + [0x01] * 40 + [0xBC])  # 42 bytes minimum
        
        try:
            decoded = self.emv_card.decode_emv_signature(mock_sig)
            self.assertIsInstance(decoded, dict)
            self.assertIn('header', decoded)
            self.assertIn('format', decoded)
        except Exception as e:
            self.fail(f"Signature decoding failed: {e}")

class TestPINBlockAnalysis(unittest.TestCase):
    """Test PIN block analysis functionality."""
    
    def setUp(self):
        self.emv_card = EMVCard()
        
    def test_pin_block_format_detection(self):
        """Test PIN block format detection."""
        # ISO-0 format (0X where X is PIN length)
        iso0_block = bytes.fromhex("041234FFFFFFFFFF")
        analysis = self.emv_card.analyze_pin_block(iso0_block, "4111111111111111")
        
        self.assertEqual(analysis['format'], 'ISO-0 (Format 0)')
        self.assertEqual(analysis['pin_length'], 4)
        self.assertEqual(analysis['pin_digits'], '1234')
        self.assertTrue(analysis['padding_valid'])
        
        # ISO-1 format (1X...)
        iso1_block = bytes.fromhex("1234567890123456")
        analysis = self.emv_card.analyze_pin_block(iso1_block, "4111111111111111")
        
        self.assertEqual(analysis['format'], 'ISO-1 (Format 1)')
        self.assertIn('pan_part', analysis)
    
    def test_invalid_pin_block(self):
        """Test handling of invalid PIN blocks."""
        # Too short
        short_block = bytes.fromhex("041234")
        analysis = self.emv_card.analyze_pin_block(short_block, "4111111111111111")
        self.assertIn('error', analysis)
        
        # Empty
        empty_analysis = self.emv_card.analyze_pin_block(b'', "4111111111111111")
        self.assertIn('error', empty_analysis)
    
    def test_pin_block_statistics(self):
        """Test multi-card PIN block statistics."""
        # Mock cards with PIN blocks
        mock_cards = []
        for i in range(3):
            card = Mock()
            card.pin_block = bytes.fromhex(f"04123{i}FFFFFFFFFF")
            card.pan = f"411111111111111{i}"
            mock_cards.append(card)
        
        stats = self.emv_card.get_pin_block_statistics(mock_cards)
        
        self.assertEqual(stats['total_cards'], 3)
        self.assertEqual(stats['analyzed_blocks'], 3)
        self.assertIn('format_distribution', stats)
        self.assertIn('pin_length_distribution', stats)

class TestCDOLExtraction(unittest.TestCase):
    """Test CDOL1/CDOL2 extraction fixes."""
    
    def setUp(self):
        self.emv_card = EMVCard()
        
    def test_cdol_extraction_from_tlv(self):
        """Test CDOL1/CDOL2 extraction from TLV data."""
        # Mock TLV data with CDOL tags
        mock_tlv_data = [
            {'tag': '8C', 'length': 6, 'value': '9F0206', 'description': 'CDOL1'},
            {'tag': '8D', 'length': 6, 'value': '9F0206', 'description': 'CDOL2'},
            {'tag': '50', 'length': 4, 'value': 'VISA', 'description': 'Application Label'},
        ]
        
        fields = self.emv_card._extract_fields_from_tlv(mock_tlv_data)
        
        # Check CDOL1/CDOL2 are extracted
        self.assertIn('cdol1', fields)
        self.assertIn('cdol2', fields)
        self.assertEqual(fields['cdol1'], '9F0206')
        self.assertEqual(fields['cdol2'], '9F0206')
    
    def test_cdol_detection_logging(self):
        """Test CDOL detection logging works correctly."""
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log
            
            mock_tlv_data = [
                {'tag': '8C', 'value': '9F0206'},
                {'tag': '8D', 'value': '9F0206'},
            ]
            
            self.emv_card._extract_fields_from_tlv(mock_tlv_data)
            
            # Verify logging was called for CDOL detection
            self.assertTrue(mock_log.info.called)

class TestUIComponents(unittest.TestCase):
    """Test UI components for new features."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for UI tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        self.card_widget = CardDataWidget()
        
    def test_pin_analysis_tab_exists(self):
        """Test PIN Block Analysis tab is created."""
        # Check tab exists
        tab_count = self.card_widget.emv_tabs.count()
        tab_texts = [self.card_widget.emv_tabs.tabText(i) for i in range(tab_count)]
        
        self.assertIn("PIN Block Analysis", tab_texts)
        
    def test_pin_block_input_widget(self):
        """Test PIN block input widget exists and works."""
        self.assertTrue(hasattr(self.card_widget, 'pin_block_input'))
        self.assertTrue(hasattr(self.card_widget, 'analyze_pin_btn'))
        self.assertTrue(hasattr(self.card_widget, 'pin_analysis_text'))
        
    def test_pin_analysis_functionality(self):
        """Test PIN analysis functionality in UI."""
        # Set test input
        test_pin_block = "041234FFFFFFFFFF"
        self.card_widget.pin_block_input.setText(test_pin_block)
        
        # Trigger analysis
        try:
            self.card_widget.analyze_pin_block()
            # Check that analysis text is populated
            result_text = self.card_widget.pin_analysis_text.toPlainText()
            self.assertIn("PIN Block Analysis", result_text)
            self.assertIn("Format:", result_text)
        except Exception as e:
            self.fail(f"PIN analysis in UI failed: {e}")
    
    def test_oda_tab_exists(self):
        """Test ODA/Certificates tab exists."""
        tab_count = self.card_widget.emv_tabs.count()
        tab_texts = [self.card_widget.emv_tabs.tabText(i) for i in range(tab_count)]
        
        self.assertIn("ODA/Certificates", tab_texts)

class TestRealCardDataIntegration(unittest.TestCase):
    """Test integration with real card data (no test/demo keys)."""
    
    def setUp(self):
        self.emv_card = EMVCard()
        self.parser = TLVParser()
        
    def test_real_apdu_parsing(self):
        """Test parsing real APDU responses."""
        # This would use actual card APDU responses
        # For now, test the parsing infrastructure
        
        mock_real_apdu = "77819E9F6C0200019F62060000000000009F630600000000E0E09F64010E9F6501FF9F660204409F6B135413339000001111D2512221000000000000000F9F6701059F680E000000000000000000000000"
        
        try:
            apdu_bytes = bytes.fromhex(mock_real_apdu)
            parsed = self.parser.parse_tlv(apdu_bytes)
            self.assertIsInstance(parsed, list)
            
            # Extract fields using EMV card
            fields = self.emv_card._extract_fields_from_tlv(parsed)
            self.assertIsInstance(fields, dict)
            
        except Exception as e:
            self.fail(f"Real APDU parsing failed: {e}")
    
    def test_comprehensive_emv_parsing(self):
        """Test comprehensive EMV parsing pipeline."""
        # Mock comprehensive EMV data
        mock_emv_data = {
            "50": "56495341",  # Application Label
            "5A": "4111111111111111",  # PAN
            "5F24": "251231",  # Expiry
            "8C": "9F0206",  # CDOL1
            "8D": "9F0206",  # CDOL2
            "82": "1980",  # AIP
            "94": "18011A03",  # AFL
        }
        
        try:
            # Test ODA parsing
            oda_result = self.emv_card.parse_oda_structures(mock_emv_data)
            self.assertIsInstance(oda_result, dict)
            
            # Test field extraction
            fields = self.emv_card._extract_fields_from_tlv(
                [{'tag': k, 'value': v} for k, v in mock_emv_data.items()]
            )
            
            # Verify CDOL extraction works
            self.assertIn('cdol1', fields)
            self.assertIn('cdol2', fields)
            
        except Exception as e:
            self.fail(f"Comprehensive EMV parsing failed: {e}")

class TestKeyDerivationPrep(unittest.TestCase):
    """Test preparation for key derivation research."""
    
    def setUp(self):
        self.emv_card = EMVCard()
        
    def test_crypto_infrastructure(self):
        """Test cryptographic infrastructure is available."""
        # Test basic crypto operations needed for key derivation
        try:
            import hashlib
            import hmac
            from cryptography.hazmat.primitives.ciphers import algorithms
            
            # Basic crypto functionality test
            test_data = b"test data for crypto"
            sha1_hash = hashlib.sha1(test_data).hexdigest()
            self.assertEqual(len(sha1_hash), 40)  # SHA1 produces 160-bit hash
            
        except ImportError as e:
            self.fail(f"Required cryptographic libraries not available: {e}")
    
    def test_multi_card_data_structure(self):
        """Test data structures for multi-card analysis."""
        # Test framework for storing multiple card data
        cards_data = []
        
        for i in range(3):
            card_data = {
                'pan': f'411111111111111{i}',
                'pin': f'123{i}',
                'pin_block': bytes.fromhex(f'04123{i}FFFFFFFFFF'),
                'issuer_cert': f'cert_data_{i}',
                'transaction_data': f'tx_data_{i}'
            }
            cards_data.append(card_data)
        
        # Test statistical analysis preparation
        stats = self.emv_card.get_pin_block_statistics([
            type('Card', (), card)() for card in cards_data
        ])
        
        self.assertEqual(stats['total_cards'], 3)
        self.assertIn('format_distribution', stats)

def run_comprehensive_tests():
    """Run all comprehensive tests."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Running Comprehensive EMV Feature Tests")
    print("=" * 50)
    
    # Test suites
    test_suites = [
        TestAdvancedTLVParsing,
        TestODAParsing,
        TestPINBlockAnalysis,
        TestCDOLExtraction,
        TestUIComponents,
        TestRealCardDataIntegration,
        TestKeyDerivationPrep,
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for suite_class in test_suites:
        print(f"\n--- {suite_class.__name__} ---")
        suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        
        if result.failures:
            print(f"FAILURES in {suite_class.__name__}:")
            for test, traceback in result.failures:
                print(f"  {test}: {traceback}")
                
        if result.errors:
            print(f"ERRORS in {suite_class.__name__}:")
            for test, traceback in result.errors:
                print(f"  {test}: {traceback}")
    
    print(f"\n{'='*50}")
    print(f"COMPREHENSIVE TEST SUMMARY:")
    print(f"Total Tests: {total_tests}")
    print(f"Failures: {total_failures}")
    print(f"Errors: {total_errors}")
    print(f"Success Rate: {((total_tests - total_failures - total_errors) / total_tests * 100):.1f}%")
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 ALL TESTS PASSED! Ready for key derivation research.")
    else:
        print("⚠️  Some tests failed. Review and fix before proceeding.")
    
    return total_failures == 0 and total_errors == 0

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
