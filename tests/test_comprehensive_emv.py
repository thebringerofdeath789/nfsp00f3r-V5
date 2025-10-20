#!/usr/bin/env python3
"""
Test Comprehensive EMV Data Extraction
Tests the enhanced universal parser for:
- All AIDs on card
- Cryptograms (ARQC/TC)
- Application Transaction Counters
- Cryptogram Information Data
- Complete APDU logs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from card_manager import CardManager
from universal_emv_parser import UniversalEMVParser


def test_comprehensive_emv_extraction():
    """Test comprehensive EMV data extraction including all AIDs and cryptograms"""
    print("=" * 80)
    print("COMPREHENSIVE EMV DATA EXTRACTION TEST")
    print("=" * 80)
    
    # Set up logging to see all details
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("\n1. TESTING UNIVERSAL PARSER DIRECTLY:")
    print("-" * 50)
    
    try:
        # Test direct universal parser
        parser = UniversalEMVParser()
        card_data = parser.parse_card()
        
        if card_data:
            print("✓ Universal Parser Success!")
            print(f"  Primary PAN: {card_data.get('pan', 'N/A')}")
            print(f"  Primary Expiry: {card_data.get('expiry_date', 'N/A')}")
            print(f"  Card Type: {card_data.get('card_type', 'N/A')}")
            
            # Check for multiple applications
            if 'applications' in card_data:
                print(f"\n✓ MULTIPLE APPLICATIONS FOUND: {len(card_data['applications'])}")
                for aid, app_data in card_data['applications'].items():
                    print(f"  AID: {aid}")
                    print(f"    Label: {app_data.get('application_label', 'N/A')}")
                    print(f"    PAN: {app_data.get('pan', 'N/A')}")
                    print(f"    Expiry: {app_data.get('expiry_date', 'N/A')}")
                    print(f"    Card Type: {app_data.get('card_type', 'N/A')}")
            
            # Check for cryptographic data
            if 'cryptographic_data' in card_data:
                print(f"\n✓ CRYPTOGRAPHIC DATA FOUND: {len(card_data['cryptographic_data'])} applications")
                for aid, crypto_info in card_data['cryptographic_data'].items():
                    print(f"  AID: {aid}")
                    print(f"    Cryptogram (9F26): {crypto_info.get('application_cryptogram', 'N/A')}")
                    print(f"    CID (9F27): {crypto_info.get('cid', 'N/A')}")
                    print(f"    ATC (9F36): {crypto_info.get('atc', 'N/A')}")
                    print(f"    Type: {crypto_info.get('cryptogram_type', 'N/A')}")
                    
                    if 'arqc_data' in crypto_info and crypto_info['arqc_data']:
                        print(f"    ARQC Data: {len(crypto_info['arqc_data'])} tags")
                        for tag, value in crypto_info['arqc_data'].items():
                            hex_val = value.hex().upper() if isinstance(value, bytes) else str(value)
                            print(f"      {tag}: {hex_val}")
                            
                    if 'tc_data' in crypto_info and crypto_info['tc_data']:
                        print(f"    TC Data: {len(crypto_info['tc_data'])} tags")
                        for tag, value in crypto_info['tc_data'].items():
                            hex_val = value.hex().upper() if isinstance(value, bytes) else str(value)
                            print(f"      {tag}: {hex_val}")
            else:
                print("⚠ No cryptographic data extracted")
            
            # Check for comprehensive data
            if 'all_pans' in card_data:
                print(f"\n✓ ALL PANs FOUND: {card_data['all_pans']}")
            if 'all_expiry_dates' in card_data:
                print(f"✓ ALL EXPIRY DATES: {card_data['all_expiry_dates']}")
            if 'all_cardholder_names' in card_data:
                print(f"✓ ALL NAMES: {card_data['all_cardholder_names']}")
            
            # Check APDU log
            if 'apdu_log' in card_data:
                print(f"\n✓ APDU LOG: {len(card_data['apdu_log'])} transactions")
                print("Recent transactions:")
                for i, apdu in enumerate(card_data['apdu_log'][-5:]):  # Last 5 transactions
                    print(f"  {i+1}. {apdu.get('command', 'Unknown')}")
                    print(f"     Status: {apdu.get('status', 'N/A')}")
                    print(f"     Description: {apdu.get('description', 'N/A')}")
            
            print(f"\n✓ TLV DATA: {len(card_data.get('tlv_data', {}))} tags extracted")
            
            # Look for specific cryptogram tags in TLV data
            crypto_tags_found = []
            for tag in ['9F26', '9F27', '9F36', '9F13', '82']:
                if tag in card_data.get('tlv_data', {}):
                    crypto_tags_found.append(tag)
            
            if crypto_tags_found:
                print(f"✓ CRYPTOGRAM TAGS IN TLV: {crypto_tags_found}")
            
        else:
            print("❌ Universal parser returned no data")
            
    except Exception as e:
        print(f"❌ Universal parser test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. TESTING CARD MANAGER INTEGRATION:")
    print("-" * 50)
    
    try:
        # Test card manager integration
        card_manager = CardManager()
        result = card_manager.read_card()
        
        if result:
            print("✓ Card Manager Success!")
            print(f"  Card ID: {result.get('card_id', 'N/A')}")
            print(f"  ATR: {result.get('atr', 'N/A')}")
            
            card_data_ui = result.get('card_data', {})
            print(f"  UI PAN: {card_data_ui.get('pan', 'N/A')}")
            print(f"  UI Expiry: {card_data_ui.get('expiry_date', 'N/A')}")
            
            # Check UI cryptographic data
            if 'cryptographic_data' in card_data_ui:
                print(f"✓ UI CRYPTOGRAPHIC DATA: {len(card_data_ui['cryptographic_data'])} applications")
                
            if 'cryptographic_tlv' in card_data_ui:
                print(f"✓ UI CRYPTOGRAPHIC TLV: {len(card_data_ui['cryptographic_tlv'])} tags")
                for tag, value in card_data_ui['cryptographic_tlv'].items():
                    print(f"  {tag}: {value[:32]}{'...' if len(value) > 32 else ''}")
                    
            if 'all_applications' in card_data_ui:
                print(f"✓ UI ALL APPLICATIONS: {len(card_data_ui['all_applications'])} applications")
                for aid, app_data in card_data_ui['all_applications'].items():
                    print(f"  {aid}: {app_data.get('Label', 'N/A')} - {app_data.get('PAN', 'N/A')}")
                    if 'Cryptographic Data' in app_data:
                        crypto = app_data['Cryptographic Data']
                        print(f"    Crypto: {crypto.get('Type', 'N/A')} - {crypto.get('Cryptogram', 'N/A')[:16]}...")
        else:
            print("❌ Card manager returned no data")
            
    except Exception as e:
        print(f"❌ Card manager test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST COMPLETE")
    print("=" * 80)
    print("\nWhat should be visible now:")
    print("• Multiple applications (AIDs) extracted from the same card")
    print("• Cryptograms (9F26) from each application")
    print("• CID (9F27) - Cryptogram Information Data")
    print("• ATC (9F36) - Application Transaction Counter") 
    print("• ARQC and TC data when available")
    print("• Complete APDU transaction logs")
    print("• All PANs, expiry dates, and cardholder names found")
    print("• Comprehensive TLV tag data with descriptions")
    print("=" * 80)


if __name__ == '__main__':
    test_comprehensive_emv_extraction()
