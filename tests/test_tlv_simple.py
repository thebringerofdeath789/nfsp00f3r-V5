#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple TLV Parser Test - Fix verification
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tlv_parser():
    """Test the TLV parser with real EMV data."""
    print("🔍 Testing TLV Parser")
    print("=" * 40)
    
    try:
        from ..tlv import TLVParser
        parser = TLVParser()
        
        # Test 1: Simple PAN tag
        print("\n📋 Test 1: Simple PAN tag")
        test_tlv1 = "5A084761739001010010"
        print(f"Input: {test_tlv1}")
        
        parsed1 = parser.parse(bytes.fromhex(test_tlv1))
        print(f"Result type: {type(parsed1)}")
        print(f"Result: {parsed1}")
        
        # Test 2: Nested TLV (FCI template)
        print("\n📋 Test 2: Nested TLV (FCI Template)")
        test_tlv2 = "6F1C840E315041592E5359532E4444463031A50A880102500550415920"
        print(f"Input: {test_tlv2}")
        
        parsed2 = parser.parse(bytes.fromhex(test_tlv2))
        print(f"Result type: {type(parsed2)}")
        print(f"Result: {parsed2}")
        
        # Test 3: More complex nested structure
        print("\n📋 Test 3: Complex EMV response")
        test_tlv3 = "77819E9F2701809F360200019F260829F37FF71C2C31BB9F10200FA501A030F8000000000000000000000000000F0C0B0C000000000000009A031901019C0100"
        print(f"Input: {test_tlv3}")
        
        parsed3 = parser.parse(bytes.fromhex(test_tlv3))
        print(f"Result type: {type(parsed3)}")
        print(f"Result: {parsed3}")
        
        return True
        
    except Exception as e:
        print(f"❌ TLV test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_tlv_parser()
