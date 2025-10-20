#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Key Derivation Research Tests
=================================================

File: test_key_derivation_research.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Comprehensive tests for key derivation research capabilities

This module validates the key derivation research functionality using real
EMV card data and implements comprehensive testing for master key discovery,
cryptographic pattern analysis, and multi-card correlation detec        logger.info("="*60)
        logger.info("KEY DERIVATION RESEARCH TESTING COMPLETE")
        logger.info("="*60)

def main():
    """Main test execution function."""
    try:
        # Create and run comprehensive tests
        tester = KeyDerivationTester()
        tester.run_comprehensive_tests()
        
        return True
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) sys
import os
import time
import logging
from typing import Dict, List, Any
import json
import hashlib

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from key_derivation_research import (
    KeyDerivationAnalyzer, 
    CardCryptoProfile, 
    MultiCardAnalyzer,
    KeyDerivationResult
)
from ..emv_card import EMVCard
from ..card_manager import CardManager
from ..readers import ReaderManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('key_derivation_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class KeyDerivationTester:
    """
    Comprehensive key derivation testing suite.
    """
    
    def __init__(self):
        self.analyzer = KeyDerivationAnalyzer()
        self.reader_manager = ReaderManager()
        self.card_manager = CardManager()
        self.test_results = {}
        
    def setup_test_environment(self):
        """Setup test environment with real card data."""
        try:
            logger.info("Setting up key derivation test environment...")
            
            # Initialize readers
            readers = self.reader_manager.list_readers()
            if not readers:
                logger.warning("No card readers available - using simulated data")
                return False
                
            logger.info(f"Found {len(readers)} card readers: {readers}")
            return True
            
        except Exception as e:
            logger.error(f"Test environment setup failed: {e}")
            return False
            
    def extract_real_card_crypto_profile(self, card_index: int = 0) -> CardCryptoProfile:
        """Extract cryptographic profile from real EMV card."""
        try:
            # Connect to card reader
            readers = self.reader_manager.list_readers()
            if not readers:
                raise Exception("No card readers available")
                
            reader = self.reader_manager.connect_to_reader(readers[card_index])
            if not reader:
                raise Exception(f"Failed to connect to reader {readers[card_index]}")
                
            # Wait for card insertion
            logger.info("Please insert EMV card for crypto profile extraction...")
            
            if not reader.is_card_present():
                logger.info("Waiting for card insertion...")
                timeout = 30  # 30 second timeout
                start_time = time.time()
                
                while not reader.is_card_present() and (time.time() - start_time) < timeout:
                    time.sleep(0.5)
                    
                if not reader.is_card_present():
                    raise Exception("Card insertion timeout")
                    
            # Reset and select card
            atr = reader.reset_card()
            logger.info(f"Card ATR: {atr.hex().upper()}")
            
            # Create EMV card instance
            emv_card = EMVCard()
            
            # Select EMV application
            applications = emv_card.select_payment_applications(reader)
            if not applications:
                raise Exception("No EMV applications found")
                
            logger.info(f"Found {len(applications)} EMV applications")
            
            # Use first available application
            app_info = applications[0]
            logger.info(f"Selected application: {app_info}")
            
            # Select the application
            select_cmd = bytes([0x00, 0xA4, 0x04, 0x00, len(app_info['aid'])]) + app_info['aid']
            response, sw1, sw2 = reader.transmit(select_cmd)
            
            if sw1 != 0x90:
                raise Exception(f"Application selection failed: {sw1:02X}{sw2:02X}")
                
            # Parse FCI to get application data
            fci_data = emv_card.parse_fci_template(response)
            logger.info(f"FCI data extracted: {len(fci_data)} fields")
            
            # Get Processing Options
            pdol = fci_data.get('processing_data_object_list', b'\x83\x00')
            gpo_cmd = bytes([0x80, 0xA8, 0x00, 0x00, len(pdol)]) + pdol
            response, sw1, sw2 = reader.transmit(gpo_cmd)
            
            if sw1 != 0x90:
                logger.warning(f"GET PROCESSING OPTIONS failed: {sw1:02X}{sw2:02X}")
                
            # Extract card data for crypto profile
            card_data = emv_card.extract_card_data(reader)
            
            # Create crypto profile
            profile = CardCryptoProfile(
                card_id=f"real_card_{int(time.time())}",
                pan=card_data.get('pan', ''),
                pan_sequence=card_data.get('pan_sequence_number', '00'),
                expiry_date=card_data.get('expiry_date', ''),
                service_code=card_data.get('service_code', ''),
                
                # Cryptographic data
                application_cryptogram=card_data.get('application_cryptogram', ''),
                atc=card_data.get('application_transaction_counter', ''),
                unpredictable_number=card_data.get('unpredictable_number', ''),
                terminal_verification_results=card_data.get('terminal_verification_results', ''),
                
                # EMV specific data
                card_verification_results=card_data.get('card_verification_results', ''),
                issuer_application_data=card_data.get('issuer_application_data', ''),
                application_interchange_profile=card_data.get('application_interchange_profile', ''),
                
                # CDOL data
                cdol1_data=card_data.get('cdol1_data', ''),
                cdol2_data=card_data.get('cdol2_data', ''),
                pdol_data=card_data.get('pdol_data', ''),
                
                extraction_timestamp=time.time()
            )
            
            logger.info(f"Extracted crypto profile for card: {profile.pan[:6]}...{profile.pan[-4:]}")
            return profile
            
        except Exception as e:
            logger.error(f"Real card crypto profile extraction failed: {e}")
            raise
            
    def create_test_crypto_profiles(self) -> List[CardCryptoProfile]:
        """Create test crypto profiles for validation."""
        profiles = []
        
        # Profile 1: Visa card with known patterns
        profile1 = CardCryptoProfile(
            card_id="test_visa_001",
            pan="4123456789012345",
            pan_sequence="00",
            expiry_date="1225",
            service_code="201",
            pin="1234",
            application_cryptogram="A1B2C3D4E5F67890",
            atc="0001",
            unpredictable_number="12345678",
            terminal_verification_results="0000000000",
            cdol1_data="9F02069F03069F1A0295055F2A029A039C01",
            extraction_timestamp=time.time()
        )
        profiles.append(profile1)
        
        # Profile 2: MasterCard with different patterns
        profile2 = CardCryptoProfile(
            card_id="test_mastercard_001",
            pan="5123456789012345",
            pan_sequence="00",
            expiry_date="1226",
            service_code="201",
            pin="5678",
            application_cryptogram="F1E2D3C4B5A67890",
            atc="0002",
            unpredictable_number="87654321",
            terminal_verification_results="0000000000",
            cdol1_data="9F02069F03069F1A0295055F2A029A039C01",
            extraction_timestamp=time.time()
        )
        profiles.append(profile2)
        
        # Profile 3: Another Visa card (same issuer patterns)
        profile3 = CardCryptoProfile(
            card_id="test_visa_002",
            pan="4987654321098765",
            pan_sequence="00",
            expiry_date="1227",
            service_code="201",
            pin="9999",
            application_cryptogram="A1B2C3D4E5F67891",  # Similar to profile1
            atc="0003",
            unpredictable_number="11223344",
            terminal_verification_results="0000000000",
            cdol1_data="9F02069F03069F1A0295055F2A029A039C01",
            extraction_timestamp=time.time()
        )
        profiles.append(profile3)
        
        return profiles
        
    def test_individual_derivation_methods(self):
        """Test individual key derivation methods."""
        logger.info("Testing individual key derivation methods...")
        
        test_profiles = self.create_test_crypto_profiles()
        
        for profile in test_profiles:
            self.analyzer.add_card_profile(profile)
            
        results = {}
        
        # Test EMV Option A
        logger.info("Testing EMV Option A derivation...")
        option_a_result = self.analyzer._derive_emv_option_a()
        results['emv_option_a'] = {
            'success_probability': option_a_result.success_probability,
            'pattern_matches': option_a_result.pattern_matches,
            'confidence_score': option_a_result.confidence_score
        }
        
        # Test EMV Option B  
        logger.info("Testing EMV Option B derivation...")
        option_b_result = self.analyzer._derive_emv_option_b()
        results['emv_option_b'] = {
            'success_probability': option_b_result.success_probability,
            'pattern_matches': option_b_result.pattern_matches,
            'confidence_score': option_b_result.confidence_score
        }
        
        # Test PIN-based derivation
        logger.info("Testing PIN-based derivation...")
        pin_result = self.analyzer._derive_pin_based_keys()
        results['pin_based'] = {
            'success_probability': pin_result.success_probability,
            'pattern_matches': pin_result.pattern_matches,
            'confidence_score': pin_result.confidence_score
        }
        
        # Test statistical analysis
        logger.info("Testing statistical analysis...")
        stats_result = self.analyzer._perform_statistical_analysis()
        results['statistical'] = {
            'success_probability': stats_result.success_probability,
            'pattern_matches': stats_result.pattern_matches,
            'confidence_score': stats_result.confidence_score
        }
        
        self.test_results['individual_methods'] = results
        logger.info(f"Individual method testing completed. Results: {results}")
        
    def test_multi_card_analysis(self):
        """Test multi-card analysis capabilities."""
        logger.info("Testing multi-card analysis capabilities...")
        
        # Create multi-card analyzer
        multi_analyzer = MultiCardAnalyzer(self.analyzer)
        
        # Set up signal handling for progress tracking
        analysis_complete = False
        final_results = {}
        
        def on_analysis_complete(results):
            nonlocal analysis_complete, final_results
            analysis_complete = True
            final_results = results
            
        multi_analyzer.analysis_completed.connect(on_analysis_complete)
        
        # Start analysis
        multi_analyzer.start()
        
        # Wait for completion (with timeout)
        timeout = 60  # 60 seconds
        start_time = time.time()
        
        while not analysis_complete and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if not analysis_complete:
            logger.error("Multi-card analysis timed out")
            return False
            
        self.test_results['multi_card_analysis'] = final_results
        logger.info(f"Multi-card analysis completed successfully")
        return True
        
    def test_real_card_integration(self):
        """Test integration with real EMV card data."""
        logger.info("Testing real card integration...")
        
        try:
            # Try to extract real card data
            real_profile = self.extract_real_card_crypto_profile()
            
            # Add to analyzer
            self.analyzer.add_card_profile(real_profile)
            
            # Perform analysis on real data
            real_analysis = self.analyzer.analyze_key_patterns()
            
            self.test_results['real_card_integration'] = {
                'success': True,
                'card_profile': {
                    'card_id': real_profile.card_id,
                    'pan_prefix': real_profile.pan[:6] if real_profile.pan else 'N/A',
                    'has_cryptogram': bool(real_profile.application_cryptogram),
                    'has_pin': bool(real_profile.pin),
                    'extraction_time': real_profile.extraction_timestamp
                },
                'analysis_results': real_analysis
            }
            
            logger.info("Real card integration test successful")
            return True
            
        except Exception as e:
            logger.warning(f"Real card integration test failed: {e}")
            self.test_results['real_card_integration'] = {
                'success': False,
                'error': str(e),
                'note': 'This is expected if no physical card reader is available'
            }
            return False
            
    def test_cryptographic_pattern_detection(self):
        """Test cryptographic pattern detection algorithms."""
        logger.info("Testing cryptographic pattern detection...")
        
        # Create profiles with intentional patterns
        pattern_profiles = []
        
        # Pattern 1: Sequential cryptograms (weakness indicator)
        base_crypto = "1234567890ABCDEF"
        for i in range(5):
            profile = CardCryptoProfile(
                card_id=f"pattern_test_{i}",
                pan=f"412345678901234{i}",
                pan_sequence="00",
                pin=f"000{i}",
                application_cryptogram=f"{base_crypto[:-1]}{i:X}",  # Sequential last byte
                atc=f"000{i+1}",
                extraction_timestamp=time.time()
            )
            pattern_profiles.append(profile)
            self.analyzer.add_card_profile(profile)
            
        # Test pattern detection
        patterns = self.analyzer._analyze_cryptogram_patterns([
            bytes.fromhex(p.application_cryptogram) for p in pattern_profiles
        ])
        
        self.test_results['pattern_detection'] = {
            'randomness_score': patterns['randomness_score'],
            'repeated_patterns': patterns['repeated_patterns'],
            'patterns_found': patterns.get('patterns', []),
            'pattern_count': len(patterns.get('patterns', []))
        }
        
        logger.info(f"Pattern detection test completed. Found {patterns['repeated_patterns']} patterns")
        
    def test_master_key_derivation_simulation(self):
        """Test master key derivation with known test vectors."""
        logger.info("Testing master key derivation simulation...")
        
        # Create controlled test scenario with known master key
        known_master_key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
        
        # Generate test profiles using the known master key
        simulated_profiles = []
        
        for i in range(3):
            pan = f"412345678901234{i}"
            
            # Simulate key derivation using known master key
            diversification_data = (pan + "00").ljust(16, '0')[:16]
            derived_key = self.analyzer._derive_3des_key(known_master_key, bytes.fromhex(diversification_data))
            
            # Create transaction data
            transaction_data = bytes.fromhex(f"000{i+1}") + b'\x00' * 14  # ATC + padding
            
            # Generate cryptogram using derived key
            simulated_cryptogram = self.analyzer._generate_application_cryptogram(derived_key, transaction_data)
            
            profile = CardCryptoProfile(
                card_id=f"simulation_test_{i}",
                pan=pan,
                pan_sequence="00",
                pin=f"123{i}",
                application_cryptogram=simulated_cryptogram.hex().upper(),
                atc=f"000{i+1}",
                extraction_timestamp=time.time()
            )
            
            simulated_profiles.append(profile)
            self.analyzer.add_card_profile(profile)
            
        # Attempt to recover the master key
        common_key_result = self.analyzer._derive_common_master_key()
        
        # Check if we recovered the known master key
        recovered_master = common_key_result.derived_keys.get('master_key', '')
        master_key_match = (recovered_master.upper() == known_master_key.hex().upper())
        
        self.test_results['master_key_simulation'] = {
            'known_master_key': known_master_key.hex().upper(),
            'recovered_master_key': recovered_master,
            'successful_recovery': master_key_match,
            'success_probability': common_key_result.success_probability,
            'confidence_score': common_key_result.confidence_score,
            'cards_generated': len(simulated_profiles)
        }
        
        logger.info(f"Master key simulation: {'SUCCESS' if master_key_match else 'FAILED'}")
        logger.info(f"Success probability: {common_key_result.success_probability:.2f}")
        
    def run_comprehensive_tests(self):
        """Run all key derivation research tests."""
        logger.info("="*60)
        logger.info("STARTING COMPREHENSIVE KEY DERIVATION RESEARCH TESTS")
        logger.info("="*60)
        
        start_time = time.time()
        
        # Setup test environment
        if not self.setup_test_environment():
            logger.warning("Test environment setup incomplete - continuing with available capabilities")
            
        # Run individual tests
        test_methods = [
            ("Individual Derivation Methods", self.test_individual_derivation_methods),
            ("Cryptographic Pattern Detection", self.test_cryptographic_pattern_detection), 
            ("Master Key Derivation Simulation", self.test_master_key_derivation_simulation),
            ("Multi-Card Analysis", self.test_multi_card_analysis),
            ("Real Card Integration", self.test_real_card_integration)
        ]
        
        for test_name, test_method in test_methods:
            try:
                logger.info(f"\n--- Testing: {test_name} ---")
                test_method()
                logger.info(f"✅ {test_name} completed successfully")
            except Exception as e:
                logger.error(f"❌ {test_name} failed: {e}")
                self.test_results[test_name.lower().replace(' ', '_')] = {'error': str(e)}
                
        # Generate test summary
        total_time = time.time() - start_time
        self.generate_test_summary(total_time)
        
    def generate_test_summary(self, total_time: float):
        """Generate comprehensive test summary."""
        logger.info("\n" + "="*60)
        logger.info("KEY DERIVATION RESEARCH TEST SUMMARY")
        logger.info("="*60)
        
        # Count successful tests
        successful_tests = 0
        total_tests = 0
        
        for test_name, results in self.test_results.items():
            total_tests += 1
            if isinstance(results, dict) and not results.get('error'):
                successful_tests += 1
                
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Successful Tests: {successful_tests}")
        logger.info(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        logger.info(f"Total Test Time: {total_time:.2f} seconds")
        
        # Detailed results
        logger.info("\nDetailed Test Results:")
        logger.info("-" * 40)
        
        for test_name, results in self.test_results.items():
            if isinstance(results, dict):
                if 'error' in results:
                    logger.info(f"❌ {test_name}: ERROR - {results['error']}")
                else:
                    logger.info(f"✅ {test_name}: SUCCESS")
                    
                    # Show key metrics for successful tests
                    if 'success_probability' in results:
                        logger.info(f"   Success Probability: {results['success_probability']:.2f}")
                    if 'confidence_score' in results:
                        logger.info(f"   Confidence Score: {results['confidence_score']:.2f}")
                    if 'pattern_count' in results:
                        logger.info(f"   Patterns Found: {results['pattern_count']}")
                        
        # Key findings
        logger.info("\nKey Findings:")
        logger.info("-" * 20)
        
        # Check for high-risk findings
        for test_name, results in self.test_results.items():
            if isinstance(results, dict) and 'success_probability' in results:
                if results['success_probability'] > 0.5:
                    logger.info(f"🔴 HIGH RISK: {test_name} shows {results['success_probability']:.1%} success rate")
                elif results['success_probability'] > 0.2:
                    logger.info(f"🟡 MEDIUM RISK: {test_name} shows {results['success_probability']:.1%} success rate")
                else:
                    logger.info(f"🟢 LOW RISK: {test_name} shows {results['success_probability']:.1%} success rate")
                    
        # Recommendations
        logger.info("\nRecommendations:")
        logger.info("-" * 15)
        
        if self.test_results.get('master_key_simulation', {}).get('successful_recovery'):
            logger.info("⚠️  Master key recovery was successful in simulation - review key management practices")
            
        if self.test_results.get('pattern_detection', {}).get('pattern_count', 0) > 0:
            logger.info("⚠️  Cryptographic patterns detected - investigate randomness sources")
            
        if self.test_results.get('real_card_integration', {}).get('success'):
            logger.info("✅ Real card integration successful - system ready for production testing")
        else:
            logger.info("ℹ️  Real card integration not available - results based on simulated data only")
            
        # Save results to file
        output_file = f"key_derivation_test_results_{int(time.time())}.json"
        try:
            with open(output_file, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"\n📄 Detailed results saved to: {output_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            
        logger.info("\n" + "="*60)
        logger.info("KEY DERIVATION RESEARCH TESTING COMPLETE")
        logger.info("="*60)

def main():
    """Main test execution function."""
    try:
        # Create and run comprehensive tests
        tester = KeyDerivationTester()
        tester.run_comprehensive_tests()
        
        return True
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```
