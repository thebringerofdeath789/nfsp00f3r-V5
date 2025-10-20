#!/usr/bin/env python3
"""
Card Reader Diagnostic Test
===========================

This test diagnoses card reader issues and provides detailed debugging info.
"""

This script demonstrates the actual APDU communication and card data
extraction process with full console output for debugging.
"""

import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging to show debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def test_apdu_communication():
    """Test APDU communication with debug output."""
    print("🔧 Testing APDU Communication with Debug Output:")
    print("=" * 60)
    
    try:
        # Just test the classes we have
        from ..emv_card import EMVCard
        
        print("\n📡 Testing EMV Components...")
        
        # Create a simulated card for testing
        print("\n💳 Creating Test EMV Card...")
        test_card = EMVCard()
        
        # Simulate APDU commands and responses
        print("\n🔄 Simulating APDU Commands:")
        
        # SELECT command
        select_cmd = "00A404000E315041592E5359532E444446303100"
        print(f">>> SELECT PPSE: {select_cmd}")
        
        # Simulated response
        select_resp = "6F1C840E315041592E5359532E4444463031A50A880102500550415920009000"
        print(f"<<< Response: {select_resp}")
        
        # Parse the response
        print("\n🔍 Parsing SELECT Response:")
        if select_resp.endswith("9000"):
            print("✅ Response successful (SW1SW2: 9000)")
            fci_data = select_resp[:-4]  # Remove status bytes
            print(f"📄 FCI Data: {fci_data}")
            
            # Parse TLV data
            from ..tlv import TLVParser
            parser = TLVParser()
            try:
                parsed_fci = parser.parse(bytes.fromhex(fci_data))
                print("✅ FCI parsed successfully:")
                print(f"📋 Parsed structure: {parsed_fci}")
            except Exception as e:
                print(f"❌ FCI parsing failed: {e}")
        
        # GET PROCESSING OPTIONS
        gpo_cmd = "80A8000002830000"
        print(f"\n>>> GET PROCESSING OPTIONS: {gpo_cmd}")
        
        gpo_resp = "770A8201038402180001009000"
        print(f"<<< Response: {gpo_resp}")
        
        if gpo_resp.endswith("9000"):
            print("✅ GPO successful")
            gpo_data = gpo_resp[:-4]
            print(f"📄 GPO Data: {gpo_data}")
            
            try:
                parsed_gpo = parser.parse(bytes.fromhex(gpo_data))
                print("✅ GPO data parsed:")
                print(f"📋 Parsed structure: {parsed_gpo}")
            except Exception as e:
                print(f"❌ GPO parsing failed: {e}")
        
        # READ RECORD commands
        print("\n🔄 Simulating READ RECORD Commands:")
        
        records = [
            ("00B2010C00", "701A5F24032512315F25031501015A084761739001010010000000000000009000"),
            ("00B2020C00", "70205F280208405F34010195056000000800009F0D05B450848800009000"),
            ("00B2030C00", "70145F30020102571047617390010100109F1F183132333435009000")
        ]
        
        for cmd, resp in records:
            print(f">>> READ RECORD: {cmd}")
            print(f"<<< Response: {resp}")
            
            if resp.endswith("9000"):
                print("✅ Record read successful")
                record_data = resp[:-4]
                
                try:
                    parsed_record = parser.parse(bytes.fromhex(record_data))
                    print("✅ Record parsed:")
                    print(f"📋 Structure: {parsed_record}")
                    
                    # Extract specific EMV data
                    extract_emv_data(parsed_record)
                    
                except Exception as e:
                    print(f"❌ Record parsing failed: {e}")
            print()
        
        # Generate Application Cryptogram
        print("\n🔐 Testing Cryptogram Generation:")
        test_cryptogram_generation()
        
    except Exception as e:
        print(f"❌ APDU test failed: {e}")
        import traceback
        traceback.print_exc()

def extract_emv_data(parsed_data):
    """Extract and display EMV data from parsed TLV."""
    print("🔍 Extracting EMV Data:")
    
    # EMV tag definitions
    emv_tags = {
        '5A': 'Application PAN',
        '5F24': 'Application Expiration Date',
        '5F25': 'Application Effective Date',
        '5F28': 'Issuer Country Code',
        '5F30': 'Service Code',
        '5F34': 'Application PAN Sequence Number',
        '57': 'Track 2 Equivalent Data',
        '82': 'Application Interchange Profile',
        '95': 'Terminal Verification Results',
        '9F07': 'Application Usage Control',
        '9F0D': 'Issuer Action Code - Default',
        '9F1F': 'Track 1 Discretionary Data'
    }
    
    def find_tag_in_structure(data, target_tag):
        """Recursively find a tag in the parsed structure."""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == target_tag:
                    return value
                elif isinstance(value, dict):
                    result = find_tag_in_structure(value, target_tag)
                    if result:
                        return result
                elif isinstance(value, list):
                    for item in value:
                        result = find_tag_in_structure(item, target_tag)
                        if result:
                            return result
        return None
    
    for tag, description in emv_tags.items():
        tag_data = find_tag_in_structure(parsed_data, tag)
        if tag_data:
            if isinstance(tag_data, dict) and 'value' in tag_data:
                value = tag_data['value']
                print(f"  📋 {tag} ({description}): {value}")
                
                # Special processing for specific tags
                if tag == '5A':  # PAN
                    print(f"    💳 Card Number: {format_pan(value)}")
                elif tag == '5F24':  # Expiry
                    print(f"    📅 Expiry: {format_expiry(value)}")
                elif tag == '57':  # Track 2
                    print(f"    🛤️  Track 2: {format_track2(value)}")
            else:
                print(f"  📋 {tag} ({description}): {tag_data}")

def format_pan(pan_hex):
    """Format PAN for display."""
    if len(pan_hex) >= 8:
        masked = pan_hex[:6] + "*" * (len(pan_hex) - 10) + pan_hex[-4:]
        return masked
    return pan_hex

def format_expiry(expiry_hex):
    """Format expiry date."""
    if len(expiry_hex) == 6:
        year = expiry_hex[:2]
        month = expiry_hex[2:4]
        return f"{month}/20{year}"
    return expiry_hex

def format_track2(track2_hex):
    """Format track 2 data."""
    # Track 2 contains PAN + separator + expiry + service code + discretionary data
    if 'D' in track2_hex:
        parts = track2_hex.split('D')
        pan = parts[0]
        if len(parts) > 1 and len(parts[1]) >= 4:
            expiry = parts[1][:4]
            service = parts[1][4:7] if len(parts[1]) >= 7 else ""
            return f"PAN: {format_pan(pan)}, Expiry: {format_expiry(expiry)}, Service: {service}"
    return track2_hex

def test_cryptogram_generation():
    """Test cryptogram generation with debug output."""
    print("\n🔐 Testing Cryptogram Generation:")
    
    try:
        from ..crypto import EMVCrypto
        
        crypto = EMVCrypto()
        print("✅ Crypto engine initialized")
        
        # Initialize for test card
        test_pan = '4761739001010010'
        crypto.initialize_for_card(test_pan, '00')
        print(f"✅ Crypto initialized for PAN: {format_pan(test_pan)}")
        
        # Transaction data
        transaction_data = {
            'amount': 10000,  # $100.00
            'currency_code': '0840',
            'country_code': '0840',
            'tvr': '0000000000',
            'transaction_date': '250816',
            'transaction_type': '00',
            'unpredictable_number': '12345678',
            'aip': '1800',
            'atc': '0001'
        }
        
        print("\n📊 Transaction Data:")
        for key, value in transaction_data.items():
            print(f"  {key}: {value}")
        
        # Generate ARQC
        print("\n🔐 Generating ARQC...")
        arqc = crypto.calculate_application_cryptogram('ARQC', transaction_data)
        print(f"✅ ARQC Generated: {arqc}")
        
        # Generate TC
        print("\n🔐 Generating TC...")
        tc = crypto.calculate_application_cryptogram('TC', transaction_data)
        print(f"✅ TC Generated: {tc}")
        
        # Test key derivation details
        print("\n🔑 Key Derivation Details:")
        for key_type in ['ac', 'smi', 'smc', 'dac']:
            key = crypto.key_manager.get_session_key(key_type)
            if key:
                print(f"  {key_type.upper()} Session Key: {key.hex()}")
            else:
                print(f"  {key_type.upper()} Session Key: Not available")
        
    except Exception as e:
        print(f"❌ Cryptogram test failed: {e}")
        import traceback
        traceback.print_exc()

def test_fixed_issues():
    """Test the specific fixes made."""
    print("\n🔧 Testing Fixed Issues:")
    print("=" * 40)
    
    # Test TLV parsing
    print("1. Testing TLV Parsing Fix:")
    try:
        from ..tlv import TLVParser
        parser = TLVParser()
        
        # Test with bytes (correct way)
        test_tlv = bytes.fromhex("5A084761739001010010")
        parsed = parser.parse(test_tlv)
        
        if parsed:
            print("  ✅ TLV parsing works with bytes")
            print(f"  📋 Parsed: {parsed}")
        else:
            print("  ❌ TLV parsing still returns empty")
            
    except Exception as e:
        print(f"  ❌ TLV test failed: {e}")
    
    # Test crypto key derivation
    print("\n2. Testing Crypto Key Derivation Fix:")
    try:
        from ..crypto import EMVCrypto
        crypto = EMVCrypto()
        
        # Test multiple derivations
        for i in range(3):
            crypto.key_manager.derive_session_keys('4761739001010010', '00')
            ac_key = crypto.key_manager.get_session_key('ac')
            if ac_key:
                print(f"  ✅ Derivation {i+1}: {ac_key.hex()[:16]}...")
            else:
                print(f"  ❌ Derivation {i+1}: Failed")
                
    except Exception as e:
        print(f"  ❌ Crypto derivation test failed: {e}")

if __name__ == "__main__":
    print("🧪 NFSP00F3R V5.00 - Debug APDU Test")
    print("=" * 50)
    
    test_fixed_issues()
    test_apdu_communication()
    
    print("\n" + "=" * 50)
    print("🎯 Debug test complete!")
