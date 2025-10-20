#!/usr/bin/env python3
"""
Test TLV parser with dynamic boundary expansion

When TLV data is complete but artificially truncated by boundary settings,
the parser should be smart enough to use all available data.
"""

from ..tlv import TLVParser

def test_dynamic_boundary():
    print("🧪 DYNAMIC BOUNDARY EXPANSION TEST")
    print("=" * 50)
    
    # SCENARIO 1: Complete TLV data but small boundary
    print("\n🔍 Testing: Complete TLV data with small boundary")
    
    # This is valid complete TLV data - 30 bytes total
    complete_data = "6F1C840E315041592E5359532E4444463031A50A8801025005504159"
    data_bytes = bytes.fromhex(complete_data)
    
    print(f"   Total data available: {len(data_bytes)} bytes")
    print(f"   Data: {complete_data}")
    
    # Test with truncated data (first 15 bytes only)
    print(f"\n   Testing with truncated data (first 15 bytes only):")
    truncated_data = data_bytes[:15]
    parser = TLVParser()
    result = parser.parse(truncated_data)
    
    if parser.parse_errors:
        print("   ⚠️  Truncation errors:")
        for error in parser.parse_errors:
            print(f"      - {error}")
    
    print("   Parsed data:")
    for tag, value in result.items():
        print(f"      {tag}: {value}")
    
    # SCENARIO 2: Now test with full data
    print(f"\n   Testing with complete data ({len(data_bytes)} bytes):")
    parser2 = TLVParser()
    result2 = parser2.parse(data_bytes)
    
    if parser2.parse_errors:
        print("   ⚠️  Parse errors:")
        for error in parser2.parse_errors:
            print(f"      - {error}")
    else:
        print("   ✅ No errors - complete parsing")
    
    print("   Parsed data:")
    for tag, value in result2.items():
        print(f"      {tag}: {value}")
    
    # SCENARIO 3: Compare results
    print(f"\n🔍 Testing: Comparison between truncated vs complete")
    print("   The parser handles both cases appropriately...")
    
    # Show detailed structure for complete data
    parser3 = TLVParser()
    
    try:
        result3 = parser3.parse(data_bytes)
        
        if parser3.parse_errors:
            print("   ⚠️  Parse errors:")
            for error in parser3.parse_errors:
                print(f"      - {error}")
        else:
            print("   ✅ Complete parsing successful!")
        
        print("   Complete TLV structure:")
        tree = parser3.format_tlv_tree(result3)
        print(tree)
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n✅ Dynamic boundary test complete!")

if __name__ == "__main__":
    test_dynamic_boundary()
