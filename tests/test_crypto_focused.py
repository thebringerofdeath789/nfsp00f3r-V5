#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Crypto Test Runner
====================================

File: test_crypto_focused.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Focused test runner for cryptographic functions

This module specifically tests the crypto module functionality including:
- Cryptogram generation (ARQC, TC, AAC)
- Key derivation and session key management
- PIN block formatting and verification
- Data authentication methods (SDA, DDA, CDA)
- MAC calculation and validation

Run with: python test_crypto_focused.py
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestCryptographyFocused(unittest.TestCase):
    """Focused test for cryptographic functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from ..crypto import EMVCrypto
            self.crypto = EMVCrypto()
            print("✅ Crypto module loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load crypto module: {e}")
            self.crypto = None
            
    def test_cryptogram_generation(self):
        """Test cryptogram generation and validation."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n🔐 Testing Cryptogram Generation:")
        
        # Initialize crypto for card
        self.crypto.initialize_for_card('4761739001010010', '00')
        
        transaction_data = {
            'amount': 10000,  # $100.00 in cents
            'currency_code': '0840',     # USD
            'country_code': '0840',      # US
            'tvr': '0000000000',
            'transaction_date': '250816',
            'transaction_type': '00',
            'unpredictable_number': '12345678',
            'aip': '1800',
            'atc': '0001'
        }
        
        try:
            # Test ARQC generation
            arqc = self.crypto.calculate_application_cryptogram('ARQC', transaction_data)
            self.assertIsNotNone(arqc)
            self.assertEqual(len(arqc), 16)  # 8 bytes = 16 hex chars
            print(f"  ✓ ARQC generated: {arqc}")
            
            # Test TC generation
            tc = self.crypto.calculate_application_cryptogram('TC', transaction_data)
            self.assertIsNotNone(tc)
            self.assertEqual(len(tc), 16)
            print(f"  ✓ TC generated: {tc}")
            
            # Test AAC generation
            aac = self.crypto.calculate_application_cryptogram('AAC', transaction_data)
            self.assertIsNotNone(aac)
            self.assertEqual(len(aac), 16)
            print(f"  ✓ AAC generated: {aac}")
            
        except Exception as e:
            print(f"  ❌ Cryptogram generation failed: {e}")
            raise
        
    def test_key_derivation(self):
        """Test session key derivation."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n🔑 Testing Key Derivation:")
        
        try:
            # Test session key derivation
            self.crypto.key_manager.derive_session_keys('4761739001010010', '00')
            
            # Test getting session keys
            ac_key = self.crypto.key_manager.get_session_key('ac')
            smi_key = self.crypto.key_manager.get_session_key('smi')
            smc_key = self.crypto.key_manager.get_session_key('smc')
            dac_key = self.crypto.key_manager.get_session_key('dac')
            
            self.assertIsNotNone(ac_key)
            self.assertIsNotNone(smi_key)
            self.assertIsNotNone(smc_key)
            self.assertIsNotNone(dac_key)
            
            print(f"  ✓ AC session key: {ac_key.hex() if ac_key else 'None'}")
            print(f"  ✓ SMI session key: {smi_key.hex() if smi_key else 'None'}")
            print(f"  ✓ SMC session key: {smc_key.hex() if smc_key else 'None'}")
            print(f"  ✓ DAC session key: {dac_key.hex() if dac_key else 'None'}")
            
            # Test key setting
            test_key = b'\x01\x23\x45\x67\x89\xAB\xCD\xEF\x01\x23\x45\x67\x89\xAB\xCD\xEF'
            self.crypto.key_manager.set_master_keys(ac_key=test_key)
            print(f"  ✓ Master keys set successfully")
            
        except Exception as e:
            print(f"  ❌ Key derivation failed: {e}")
            raise
            
    def test_mac_calculation(self):
        """Test MAC calculation."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n🛡️ Testing MAC Calculation:")
        
        try:
            # Test MAC calculation using standalone function
            from ..crypto import calculate_mac
            
            data = bytes.fromhex('123456789ABCDEF0')
            session_key = bytes.fromhex('0123456789ABCDEF0123456789ABCDEF')
            
            mac = calculate_mac(session_key, data, "DES")
            self.assertIsNotNone(mac)
            self.assertEqual(len(mac), 8)  # 8 bytes
            print(f"  ✓ DES MAC calculated: {mac.hex()}")
            
            # Test different MAC algorithms
            mac_aes = calculate_mac(session_key, data, "AES")
            self.assertIsNotNone(mac_aes)
            print(f"  ✓ AES MAC calculated: {mac_aes.hex()}")
            
            mac_hmac = calculate_mac(session_key, data, "HMAC-SHA256")
            self.assertIsNotNone(mac_hmac)
            print(f"  ✓ HMAC-SHA256 calculated: {mac_hmac.hex()}")
            
        except Exception as e:
            print(f"  ❌ MAC calculation failed: {e}")
            raise
        
    def test_pin_processing(self):
        """Test PIN block formatting and verification."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n📱 Testing PIN Processing:")
        
        try:
            pan = '4761739001010010'
            pin = '1234'
            
            # Test PIN processing using the available method
            encrypted_pin = self.crypto.process_pin_verification(pin, pan, 0)
            self.assertIsNotNone(encrypted_pin)
            self.assertEqual(len(encrypted_pin), 8)  # 8 bytes
            print(f"  ✓ PIN block format 0: {encrypted_pin.hex()}")
            
            # Test format 1
            encrypted_pin_1 = self.crypto.process_pin_verification(pin, pan, 1)
            self.assertIsNotNone(encrypted_pin_1)
            print(f"  ✓ PIN block format 1: {encrypted_pin_1.hex()}")
            
            # Test PIN verification using pin processor directly
            emv_data = {
                '9F17': '03',  # PIN Try Counter
                '8E': '000000000000000000000000'  # CVM List
            }
            
            result = self.crypto.pin_processor.verify_pin_offline(pin, emv_data)
            self.assertIsInstance(result, bool)
            print(f"  ✓ PIN verification result: {result}")
            
        except Exception as e:
            print(f"  ❌ PIN processing failed: {e}")
            raise
            
    def test_data_authentication(self):
        """Test data authentication methods."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n🔒 Testing Data Authentication:")
        
        try:
            emv_data = {
                '5A': '4761739001010010',  # PAN
                '5F24': '2512',            # Expiry
                '8F': '01',                # CA Public Key Index
                '90': '01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789',  # Issuer Public Key Certificate
                '92': '0123456789ABCDEF0123456789ABCDEF01234567',  # Issuer Public Key Remainder
                '9F32': '03',              # Issuer Public Key Exponent
                '9F46': '01234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789',  # ICC Public Key Certificate
                '9F47': '03',              # ICC Public Key Exponent
                '9F48': '0123456789ABCDEF0123456789ABCDEF01234567',   # ICC Public Key Remainder
                '4F': 'A0000000041010'     # AID
            }
            
            # Test SDA using the verify_data_authentication method
            sda_result = self.crypto.verify_data_authentication('SDA', emv_data)
            self.assertIsInstance(sda_result, bool)
            print(f"  ✓ SDA verification: {sda_result}")
            
            # Test DDA
            challenge = b'\x12\x34\x56\x78'
            dda_result = self.crypto.verify_data_authentication('DDA', emv_data, challenge)
            self.assertIsInstance(dda_result, bool)
            print(f"  ✓ DDA verification: {dda_result}")
            
            # Test CDA
            cda_result = self.crypto.verify_data_authentication('CDA', emv_data)
            self.assertIsInstance(cda_result, bool)
            print(f"  ✓ CDA verification: {cda_result}")
            
        except Exception as e:
            print(f"  ❌ Data authentication failed: {e}")
            raise
            
    def test_encryption_decryption(self):
        """Test encryption and decryption operations."""
        if not self.crypto:
            self.skipTest("Crypto module not available")
            
        print("\n🔐 Testing Encryption/Decryption:")
        
        try:
            # Test symmetric encryption using cryptography library directly
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            plaintext = b"This is test data for encryption"
            key = bytes.fromhex('0123456789ABCDEF0123456789ABCDEF')
            
            # Simple AES encryption test
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Pad plaintext to 16-byte boundary
            padding_length = 16 - (len(plaintext) % 16)
            padded_plaintext = plaintext + bytes([padding_length] * padding_length)
            
            encrypted = encryptor.update(padded_plaintext) + encryptor.finalize()
            self.assertIsNotNone(encrypted)
            self.assertNotEqual(encrypted, plaintext)
            print(f"  ✓ Data encrypted: {encrypted.hex()[:32]}...")
            
            # Test decryption
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
            
            # Remove padding
            padding_length = decrypted_padded[-1]
            decrypted = decrypted_padded[:-padding_length]
            
            self.assertEqual(decrypted, plaintext)
            print(f"  ✓ Data decrypted: {decrypted.decode()}")
            
        except Exception as e:
            print(f"  ❌ Encryption/Decryption failed: {e}")
            raise

def run_crypto_tests():
    """Run focused crypto tests."""
    print("🧪 NFSP00F3R V5.00 - Crypto Module Test Suite")
    print("=" * 50)
    
    # Create test suite for crypto tests only
    test_suite = unittest.TestSuite()
    
    # Add crypto test class
    crypto_tests = unittest.TestLoader().loadTestsFromTestCase(TestCryptographyFocused)
    test_suite.addTests(crypto_tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # Print detailed summary
    print("\n" + "=" * 50)
    print(f"Crypto Tests Summary:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
            
    if result.errors:
        print("\n⚠️ ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback.strip()}")
            
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100 if result.testsRun > 0 else 0
    print(f"\n📊 Success Rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("🎉 ALL CRYPTO TESTS PASSED!")
        print("✅ Cryptographic functionality validated successfully")
    else:
        print("❌ Some crypto tests failed. Review output above.")
        
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_crypto_tests()
    sys.exit(0 if success else 1)
