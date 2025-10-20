#!/usr/bin/env python3

"""
Test comprehensive card data display in UI format
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager
from emv_card import EMVCard

def test_comprehensive_ui_display():
    """Test that the UI displays comprehensive data from all AIDs"""
    print("=== Testing Comprehensive UI Data Display ===")
    
    try:
        card_manager = CardManager()
        
        # Read card with comprehensive parsing
        print("Reading card with comprehensive parsing...")
        result = card_manager.read_card()
        
        if result and result.get('card_data'):
            card_data = result['card_data']
            print(f"\n=== RAW CARD DATA ===")
            print(f"Keys: {list(card_data.keys())}")
            print(f"All applications: {len(card_data.get('all_applications', {}))}")
            print(f"APDU log: {len(card_data.get('apdu_log', []))}")
            
            # Create EMVCard from the data to test UI formatting
            card = EMVCard()
            
            # Populate card with comprehensive data
            card.pan = card_data.get('pan')
            card.expiry_date = card_data.get('expiry_date')
            card.cardholder_name = card_data.get('cardholder_name')
            card.tlv_data = card_data.get('tlv_data', {})
            card.apdu_log = card_data.get('apdu_log', [])
            card.card_type = card_data.get('card_type', 'Unknown')
            
            # Add comprehensive application data
            if hasattr(card, 'all_applications_data'):
                card.all_applications_data = card_data.get('all_applications', {})
            
            # Get UI dictionary for display
            ui_data = card.to_ui_dict()
            
            print(f"\n=== UI FORMATTED DATA ===")
            print(f"PAN: {ui_data.get('pan', 'N/A')}")
            print(f"Expiry: {ui_data.get('expiry_date', 'N/A')}")
            print(f"Card Type: {ui_data.get('card_type', 'N/A')}")
            print(f"Applications: {len(ui_data.get('applications', []))}")
            
            print(f"\n=== TLV DATA ===")
            tlv_data = ui_data.get('tlv_data', {})
            if isinstance(tlv_data, dict):
                for tag, info in list(tlv_data.items())[:5]:  # Show first 5 tags
                    if isinstance(info, dict):
                        print(f"  {tag}: {info.get('value', 'N/A')[:50]}... ({info.get('description', 'No description')})")
                    else:
                        print(f"  {tag}: {str(info)[:50]}...")
            
            print(f"\n=== APDU TRANSACTIONS ===")
            raw_responses = ui_data.get('raw_responses', [])
            print(f"Total APDU transactions: {len(raw_responses)}")
            for i, apdu in enumerate(raw_responses[:3]):  # Show first 3
                print(f"  {i+1}. {apdu.get('command', 'Unknown')} -> {apdu.get('status', 'N/A')}")
            
            print(f"\n=== CRYPTOGRAPHIC DATA ===")
            crypto_data = ui_data.get('cryptographic_data', {})
            if crypto_data:
                print(f"Cryptographic entries: {len(crypto_data)}")
                for key, value in list(crypto_data.items())[:3]:
                    print(f"  {key}: {str(value)[:50]}...")
            else:
                print("  No cryptographic data available")
                
        else:
            print("Failed to read card or get card data")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_comprehensive_ui_display()
