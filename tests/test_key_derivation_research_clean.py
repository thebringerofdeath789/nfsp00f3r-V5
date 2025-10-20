#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Key Derivation Research Tests
=================================================

File: test_key_derivation_research_clean.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Comprehensive tests for key derivation research capabilities
"""


import sys
import os
import time
import logging
import json
# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from key_derivation_research_clean import (
    KeyDerivationAnalyzer, 
    CardCryptoProfile, 
    MultiCardAnalyzer
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_key_derivation_research():
    """Main test function for key derivation research."""
    logger.info("=" * 60)
    logger.info("STARTING KEY DERIVATION RESEARCH TESTS")
    logger.info("=" * 60)
    
    try:
        # Initialize analyzer
        analyzer = KeyDerivationAnalyzer()
        
        # Create test profiles
        test_profiles = create_test_profiles()
        
        # Add profiles to analyzer
        for profile in test_profiles:
            analyzer.add_card_profile(profile)
            
        logger.info(f"Added {len(test_profiles)} test card profiles")
        
        # Run analysis
        logger.info("Running key pattern analysis...")
        results = analyzer.analyze_key_patterns()
        
        # Display results
        logger.info("\nAnalysis Results:")
        logger.info("-" * 40)
        
        for method, result in results.get('derivation_attempts', {}).items():
            if 'error' in result:
                logger.info(f"❌ {method}: ERROR - {result['error']}")
            else:
                success_prob = result.get('success_probability', 0)
                logger.info(f"✅ {method}: Success probability: {success_prob:.2f}")
                
        # Test statistical analysis
        logger.info("\nTesting statistical analysis...")
        stats_result = analyzer._perform_statistical_analysis()
        logger.info(f"Statistical analysis completed with {len(stats_result.pattern_matches)} patterns found")
        
        # Test master key derivation simulation
        logger.info("\nTesting master key derivation simulation...")
        test_master_key_simulation(analyzer)
        
        logger.info("\n" + "=" * 60)
        logger.info("KEY DERIVATION RESEARCH TESTS COMPLETED")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

def create_test_profiles():
    """Create test crypto profiles."""
    profiles = []
    
    # Profile 1: Visa card
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
        terminal_verification_results="0000000000"
    )
    profiles.append(profile1)
    
    # Profile 2: MasterCard
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
        terminal_verification_results="0000000000"
    )
    profiles.append(profile2)
    
    # Profile 3: Another Visa (same issuer)
    profile3 = CardCryptoProfile(
        card_id="test_visa_002",
        pan="4987654321098765",
        pan_sequence="00",
        expiry_date="1227",
        service_code="201",
        pin="9999",
        application_cryptogram="A1B2C3D4E5F67891",
        atc="0003",
        unpredictable_number="11223344",
        terminal_verification_results="0000000000"
    )
    profiles.append(profile3)
    
    return profiles

def test_master_key_simulation(analyzer):
    """Test master key derivation with controlled simulation."""
    logger.info("Running master key derivation simulation...")
    
    # Create controlled test with known master key
    known_master_key = bytes.fromhex("0123456789ABCDEF0123456789ABCDEF")
    
    # Generate profiles using known master key
    for i in range(3):
        pan = f"412345678901234{i}"
        
        # Simulate key derivation
        diversification_data = (pan + "00").ljust(16, '0')[:16]
        derived_key = analyzer._derive_3des_key(known_master_key, bytes.fromhex(diversification_data))
        
        # Generate transaction data
        transaction_data = bytes.fromhex(f"000{i+1}") + b'\x00' * 14
        
        # Generate cryptogram
        cryptogram = analyzer._generate_application_cryptogram(derived_key, transaction_data)
        
        profile = CardCryptoProfile(
            card_id=f"simulation_{i}",
            pan=pan,
            pan_sequence="00",
            pin=f"123{i}",
            application_cryptogram=cryptogram.hex().upper(),
            atc=f"000{i+1}"
        )
        
        analyzer.add_card_profile(profile)
        
    # Attempt to recover master key
    result = analyzer._derive_common_master_key()
    
    logger.info(f"Master key recovery attempt:")
    logger.info(f"  Success probability: {result.success_probability:.2f}")
    logger.info(f"  Confidence score: {result.confidence_score:.2f}")
    logger.info(f"  Patterns found: {len(result.pattern_matches)}")

if __name__ == "__main__":
    success = test_key_derivation_research()
    sys.exit(0 if success else 1)
