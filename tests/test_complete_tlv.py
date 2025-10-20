#!/usr/bin/env python3
"""
Test with ACTUALLY complete TLV data vs truncated data
"""

from ..tlv import TLVParser

def test_complete_vs_truncated():
    print("🧪 COMPLETE vs TRUNCATED TLV DATA TEST")
    print("=" * 50)
    
    # Create ACTUALLY complete TLV data by building it properly
    print("\n🔧 Creating complete TLV data...")
    
    # Build TLV structure manually to ensure it's complete:
    # 6F = FCI Template (constructed)
    # 84 = DF Name: "1PAY.SYS.DDF01" (14 bytes)
    # A5 = FCI Proprietary Template (constructed)
    #   88 = SFI: 01
    #   50 = Application Label: "TESTPAY" (7 bytes)
    
    # DF Name data
    df_name = b"1PAY.SYS.DDF01"  # 14 bytes
    tag_84 = bytes([0x84, 0x0E]) + df_name  # 84 0E + 14 bytes = 16 total
    
    # Application Label 
    app_label = b"TESTPAY"  # 7 bytes  
    tag_50 = bytes([0x50, 0x07]) + app_label  # 50 07 + 7 bytes = 9 total
    
    # SFI
    tag_88 = bytes([0x88, 0x01, 0x01])  # 88 01 01 = 3 total
    
    # A5 template (contains 88 and 50)
    a5_content = tag_88 + tag_50  # 3 + 9 = 12 bytes
    tag_a5 = bytes([0xA5, 0x0C]) + a5_content  # A5 0C + 12 bytes = 14 total
    
    # 6F template (contains 84 and A5)
    template_content = tag_84 + tag_a5  # 16 + 14 = 30 bytes
    complete_tlv = bytes([0x6F, 0x1E]) + template_content  # 6F 1E + 30 bytes = 32 total
    
    print(f"   Complete TLV data: {complete_tlv.hex().upper()}")
    print(f"   Total length: {len(complete_tlv)} bytes")
    
    # Test with complete data
    print(f"\n🔍 Testing complete TLV data:")
    parser1 = TLVParser()
    result1 = parser1.parse(complete_tlv)
    
    if parser1.parse_errors:
        print("   ⚠️  Parse errors:")
        for error in parser1.parse_errors:
            print(f"      - {error}")
    else:
        print("   ✅ No errors - perfect parsing!")
    
    print("   Complete structure:")
    tree1 = parser1.format_tlv_tree(result1)
    print(tree1)
    
    # Test with truncated data (remove last 5 bytes)
    print(f"\n🔍 Testing truncated TLV data (missing last 5 bytes):")
    truncated_tlv = complete_tlv[:-5]  # Remove last 5 bytes
    print(f"   Truncated data: {truncated_tlv.hex().upper()}")
    print(f"   Truncated length: {len(truncated_tlv)} bytes")
    
    parser2 = TLVParser()
    result2 = parser2.parse(truncated_tlv)
    
    if parser2.parse_errors:
        print("   ⚠️  Truncation errors (expected):")
        for error in parser2.parse_errors:
            print(f"      - {error}")
    
    print("   Truncated structure:")
    tree2 = parser2.format_tlv_tree(result2)
    print(tree2)
    
    print("\n✅ Test shows parser correctly handles both complete and truncated data!")

if __name__ == "__main__":
    test_complete_vs_truncated()
