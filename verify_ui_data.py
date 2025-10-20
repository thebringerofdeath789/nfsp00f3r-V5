#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick UI Data Verification
Checks what data is passed to the UI widgets.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def verify_ui_data():
    """Verify the data that would be shown in UI."""
    print("=== Verifying UI Data Flow ===")
    
    try:
        from card_manager import CardManager
        from emv_card import EMVCard
        
        # Create card manager and read card
        card_manager = CardManager()
        result = card_manager.read_card("ACS ACR122 0")
        
        if result and 'card_data' in result:
            card_data = result['card_data']
            
            # Create EMV card object (as UI would)
            emv_card = EMVCard()
            emv_card.atr = card_data.get('atr', '')
            emv_card.card_type = card_data.get('card_type', '')
            emv_card.uid = card_data.get('uid', '')
            emv_card.timestamp = card_data.get('timestamp', '')
            
            # Get UI dict (what the UI widgets would see)
            ui_dict = emv_card.to_ui_dict()
            
            print("✓ Data that will be shown in UI:")
            print(f"  - ATR: {ui_dict.get('atr', 'N/A')}")
            print(f"  - Card Type: {ui_dict.get('card_type', 'N/A')}")
            print(f"  - PAN: {ui_dict.get('pan', 'N/A')}")
            print(f"  - UID: {ui_dict.get('uid', 'N/A')}")
            print(f"  - Timestamp: {ui_dict.get('timestamp', 'N/A')}")
            print(f"  - Applications: {len(ui_dict.get('applications', []))}")
            print(f"  - Track Data: {len(ui_dict.get('track_data', {}))}")
            print(f"  - TLV Data: {len(ui_dict.get('tlv_data', {}))}")
            
            # Verify this is not mock data
            if ui_dict.get('atr') == '3B888001534C4A26312342113B':
                print("✓ UI will show actual ATR from your card")
            else:
                print(f"⚠️  Unexpected ATR: {ui_dict.get('atr')}")
                
            if ui_dict.get('card_type') in ['Smart Card', 'NFC/Contactless', 'Contact Card']:
                print("✓ UI will show actual card type")
            else:
                print(f"⚠️  Unexpected card type: {ui_dict.get('card_type')}")
                
            if ui_dict.get('pan') == '5501797A':
                print("✓ UI will show actual card UID as PAN")
            else:
                print(f"⚠️  PAN/UID: {ui_dict.get('pan')}")
                
            return True
            
        else:
            print("✗ No card data available")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_ui_data()
