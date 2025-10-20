#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract Basic Card Data Without EMV APDUs
Focus on getting UID and basic info without complex APDU sequences.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def extract_basic_card_data():
    """Extract basic card data without EMV APDU sequences."""
    print("=== Extracting Basic Card Data ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get PC/SC readers
        reader_list = readers()
        
        if not reader_list:
            print("✗ No PC/SC readers found")
            return False
            
        reader = reader_list[0]
        print(f"Using reader: {reader}")
        
        # Create connection
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Get ATR
        atr_bytes = connection.getATR()
        atr = toHexString(atr_bytes).replace(' ', '')
        print(f"✓ ATR: {atr}")
        
        # Try to get UID (for contactless cards)
        uid = None
        try:
            # Try standard Get UID command for contactless cards
            # FFCA000000 - Get UID command
            response, sw1, sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            
            if sw1 == 0x90 and sw2 == 0x00 and response:
                uid = toHexString(response).replace(' ', '')
                print(f"✓ UID: {uid}")
            else:
                print(f"⚠️  UID command failed: {sw1:02X}{sw2:02X}")
                
        except Exception as e:
            print(f"⚠️  UID extraction failed: {e}")
            
        # Try simple card identification
        card_type = "Unknown"
        if atr:
            if "5A4A26" in atr:  # Pattern from our card's ATR
                card_type = "Smart Card"
            elif len(atr) >= 6:
                card_type = "Contact Card"
            else:
                card_type = "Unknown Card"
                
        print(f"✓ Card Type: {card_type}")
        
        # Create basic card data structure
        basic_card_data = {
            'atr': atr,
            'uid': uid,
            'card_type': card_type,
            'timestamp': '2025-08-21 14:45:00',
            'pan': uid or 'N/A',  # Use UID as PAN fallback for display
            'track2_data': None,
            'tlv_data': {},
            'applications': []
        }
        
        print("\n=== Basic Card Data Extracted ===")
        for key, value in basic_card_data.items():
            print(f"  {key}: {value}")
            
        connection.disconnect()
        return basic_card_data
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Extract basic card data and show what would appear in UI."""
    print("Basic Card Data Extraction Test")
    print("=" * 40)
    
    card_data = extract_basic_card_data()
    
    if card_data:
        print("\n" + "="*40)
        print("✓ Basic card data extracted successfully!")
        print("This data should appear in the UI:")
        print(f"  - ATR: {card_data['atr']}")
        print(f"  - UID/PAN: {card_data['pan']}")
        print(f"  - Card Type: {card_data['card_type']}")
        print("\nNote: EMV data (Track 2, TLV, Applications) requires stable APDU communication")
    else:
        print("\n" + "="*40)
        print("✗ Failed to extract basic card data")

if __name__ == "__main__":
    main()
