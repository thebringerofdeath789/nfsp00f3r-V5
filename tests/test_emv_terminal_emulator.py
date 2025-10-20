#!/usr/bin/env python3
"""
Test EMV Terminal Emulator - Full Transaction Flow
Tests comprehensive cryptogram extraction and data from all AIDs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager
from emv_terminal_emulator import EMVTerminalEmulator
from universal_emv_parser import UniversalEMVParser


def test_terminal_emulation():
    """Test EMV terminal emulation with real card"""
    print("=" * 80)
    print("EMV TERMINAL EMULATOR - COMPREHENSIVE TESTING")
    print("=" * 80)
    
    try:
        # Initialize card manager
        card_manager = CardManager()
        
        print("🔍 Testing comprehensive EMV terminal emulation...")
        
        # Perform comprehensive EMV terminal emulation
        print("\n🏦 Starting EMV Terminal Emulation...")
        print("   • Building candidate list (discovering ALL applications)")
        print("   • Processing each AID with full transaction flow")
        print("   • Generating cryptograms (ARQC/TC/AAC)")
        print("   • Extracting ALL available EMV data")
        
        card_data = card_manager.read_card()  # Auto-detect reader
        
        if card_data:
            print("\n✅ EMV TERMINAL EMULATION SUCCESSFUL!")
            print("=" * 80)
            
            # Display basic card information
            print("BASIC CARD INFORMATION:")
            print(f"PAN: {card_data.get('pan', 'N/A')}")
            print(f"Expiry: {card_data.get('expiry_date', 'N/A')}")
            print(f"Cardholder: {card_data.get('cardholder_name', 'N/A')}")
            print(f"Card Type: {card_data.get('card_type', 'N/A')}")
            
            # Display comprehensive application data
            if card_data.get('card_object') and hasattr(card_data['card_object'], 'all_applications'):
                all_apps = card_data['card_object'].all_applications
                print(f"\n📱 ALL APPLICATIONS PROCESSED: {len(all_apps)}")
                print("-" * 50)
                
                for i, (aid, app_data) in enumerate(all_apps.items(), 1):
                    print(f"Application #{i}:")
                    print(f"  AID: {aid}")
                    print(f"  Name: {app_data.get('application_label', 'Unknown')}")
                    print(f"  PAN: {app_data.get('pan', 'N/A')}")
                    
                    # Display cryptograms for this application  
                    if 'application_cryptogram' in app_data:
                        print(f"  🔐 Cryptogram: {app_data['application_cryptogram']}")
                        print(f"      Type: {app_data.get('cryptogram_type', 'Unknown')}")
                        if app_data.get('cid'):
                            print(f"      CID: {app_data['cid']}")
                        if app_data.get('atc'):
                            print(f"      ATC: {app_data['atc']}")
                    else:
                        print("  🔐 No cryptogram generated")
                    
                    # Display important EMV tags
                    tlv_data = app_data.get('tlv_data', {})
                    if tlv_data:
                        print(f"  📋 EMV Tags ({len(tlv_data)}):")
                        # Show first few important tags
                        important_tags = ['5A', '5F24', '5F20', '57', '9F26', '9F27', '9F36']
                        shown_tags = 0
                        for tag in important_tags:
                            if tag in tlv_data and shown_tags < 5:
                                try:
                                    value = tlv_data[tag]
                                    if isinstance(value, bytes):
                                        hex_val = value.hex().upper()
                                        if len(hex_val) > 20:
                                            hex_val = hex_val[:20] + "..."
                                        print(f"    {tag}: {hex_val}")
                                    else:
                                        print(f"    {tag}: {value}")
                                    shown_tags += 1
                                except:
                                    pass
                        if len(tlv_data) > shown_tags:
                            print(f"    ... and {len(tlv_data) - shown_tags} more tags")
                    
                    print()
            else:
                print("\n📱 No comprehensive application data found")
            
            # Display cryptographic summary
            if card_data.get('card_object') and hasattr(card_data['card_object'], 'cryptographic_summary'):
                crypto_summary = card_data['card_object'].cryptographic_summary
                if crypto_summary:
                    print(f"🔐 CRYPTOGRAPHIC SUMMARY: {len(crypto_summary)} applications")
                    print("-" * 40)
                    
                    for aid, crypto_info in crypto_summary.items():
                        print(f"AID: {aid}")
                        print(f"  Application: {crypto_info.get('application_name', 'Unknown')}")
                        print(f"  Cryptogram: {crypto_info.get('cryptogram', 'N/A')}")
                        print(f"  Type: {crypto_info.get('cryptogram_type', 'N/A')}")
                        print(f"  CID: {crypto_info.get('cid', 'N/A')}")
                        print(f"  ATC: {crypto_info.get('atc', 'N/A')}")
                        print()
                else:
                    print("🔐 NO CRYPTOGRAPHIC SUMMARY AVAILABLE")
            
            # Display basic card info from consolidated data
            card_obj = card_data.get('card_object')
            if card_obj:
                print("💳 CONSOLIDATED CARD DATA:")
                print("-" * 30)
                print(f"  PAN: {getattr(card_obj, 'pan', 'N/A')}")
                print(f"  Expiry: {getattr(card_obj, 'expiry_date', 'N/A')}")
                print(f"  Name: {getattr(card_obj, 'cardholder_name', 'N/A')}")
                print(f"  Card Type: {getattr(card_obj, 'card_type', 'N/A')}")
                print(f"  AID: {getattr(card_obj, 'aid', 'N/A')}")
                print(f"  Label: {getattr(card_obj, 'application_label', 'N/A')}")
                
                # Show TLV data count
                if hasattr(card_obj, 'tlv_data') and card_obj.tlv_data:
                    print(f"  TLV Tags: {len(card_obj.tlv_data)}")
                else:
                    print("  TLV Tags: 0")
            
            print("\n" + "=" * 80)
            print("✅ COMPREHENSIVE EMV TERMINAL EMULATION COMPLETE!")
            print("   • All available applications processed")
            print("   • Terminal emulation performed")  
            print("   • Cryptographic data extracted (where possible)")
            print("   • Complete transaction flow attempted")
            print("=" * 80)
            
        else:
            print("❌ EMV terminal emulation failed!")
            print("   Check card compatibility and reader connection")
    
    except Exception as e:
        print(f"❌ Error during terminal emulation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_terminal_emulation()
