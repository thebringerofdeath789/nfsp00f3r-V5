#!/usr/bin/env python3
"""
Quick validation test for key features before key derivation research.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ..emv_card import EMVCard
from ..tlv import TLVParser

def test_core_features():
    """Test core features are working."""
    print("🔍 Testing Core EMV Features")
    print("=" * 40)
    
    # Test TLV parser
    print("1. Testing TLV Parser...")
    parser = TLVParser()
    
    # Test Luhn check
    valid_pan = "4111111111111111"
    invalid_pan = "4111111111111112"
    
    assert parser._luhn_check(valid_pan), "Luhn check should pass for valid PAN"
    assert not parser._luhn_check(invalid_pan), "Luhn check should fail for invalid PAN"
    print("   ✅ Luhn algorithm working")
    
    # Test EMV card
    print("2. Testing EMV Card...")
    emv = EMVCard()
    
    # Test PIN block analysis
    test_pin_block = bytes.fromhex("041234FFFFFFFFFF")
    analysis = emv.analyze_pin_block(test_pin_block, "4111111111111111")
    
    assert analysis['format'] == 'ISO-0 (Format 0)', "PIN block format detection failed"
    assert analysis['pin_length'] == 4, "PIN length detection failed"
    assert analysis['pin_digits'] == '1234', "PIN digit extraction failed"
    print("   ✅ PIN block analysis working")
    
    # Test CDOL extraction
    print("3. Testing CDOL Extraction...")
    mock_tlv = [
        {'tag': '8C', 'value': '9F0206', 'length': 6, 'description': 'CDOL1'},
        {'tag': '8D', 'value': '9F0206', 'length': 6, 'description': 'CDOL2'},
    ]
    
    fields = emv._extract_fields_from_tlv(mock_tlv)
    assert 'cdol1' in fields, "CDOL1 extraction failed"
    assert 'cdol2' in fields, "CDOL2 extraction failed"
    assert fields['cdol1'] == '9F0206', "CDOL1 value incorrect"
    print("   ✅ CDOL extraction working")
    
    # Test ODA parsing
    print("4. Testing ODA Parsing...")
    mock_oda = {
        '82': '1980',  # AIP
        '8F': '01',    # CA PKI
    }
    
    oda_result = emv.parse_oda_structures(mock_oda)
    assert 'authentication_method' in oda_result, "ODA parsing failed"
    print("   ✅ ODA parsing working")
    
    # Test certificate decoding
    print("5. Testing Certificate Decoding...")
    mock_cert = bytes([0x6A] + [0x01] * 142 + [0xBC])  # 144 bytes
    cert_result = emv.decode_emv_certificate(mock_cert)
    assert 'header' in cert_result, "Certificate decoding failed"
    assert 'format' in cert_result, "Certificate format not extracted"
    print("   ✅ Certificate decoding working")
    
    print("\n🎉 ALL CORE FEATURES WORKING!")
    print("Ready to proceed with key derivation research.")
    return True

def test_multi_card_analysis():
    """Test multi-card analysis infrastructure."""
    print("\n🔍 Testing Multi-Card Analysis Infrastructure")
    print("=" * 50)
    
    emv = EMVCard()
    
    # Create mock cards with different PIN blocks
    class MockCard:
        def __init__(self, pin_block_hex, pan):
            self.pin_block = bytes.fromhex(pin_block_hex)
            self.pan = pan
    
    mock_cards = [
        MockCard("041234FFFFFFFFFF", "4111111111111111"),  # ISO-0, PIN 1234
        MockCard("051234FFFFFFFFFF", "5555555555554444"),  # ISO-0, PIN 12345
        MockCard("1234567890123456", "378282246310005"),   # ISO-1 format
    ]
    
    stats = emv.get_pin_block_statistics(mock_cards)
    
    assert stats['total_cards'] == 3, "Card count incorrect"
    assert stats['analyzed_blocks'] == 3, "Analysis count incorrect"
    assert 'format_distribution' in stats, "Format distribution missing"
    assert 'pin_length_distribution' in stats, "PIN length distribution missing"
    
    print("   ✅ Multi-card statistics working")
    print(f"   📊 Analyzed {stats['analyzed_blocks']} cards")
    print(f"   📊 Format distribution: {stats['format_distribution']}")
    
    return True

if __name__ == "__main__":
    try:
        # Test core features
        test_core_features()
        
        # Test multi-card analysis
        test_multi_card_analysis()
        
        print("\n" + "="*60)
        print("🚀 ALL TESTS PASSED - READY FOR KEY DERIVATION RESEARCH!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
