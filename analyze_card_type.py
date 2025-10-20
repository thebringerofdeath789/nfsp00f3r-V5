#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card Type Analysis
Analyze the card's ATR and behavior to determine what type of card it actually is.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_card_type():
    """Analyze the card type based on ATR and responses."""
    print("=== Card Type Analysis ===")
    
    # Our card's ATR
    atr = "3B888001534C4A26312342113B"
    print(f"Card ATR: {atr}")
    
    # Parse ATR components
    print(f"\nATR Analysis:")
    print(f"  TS (Initial Character): {atr[0:2]} = {atr[0:2]}")  # 3B = Direct convention
    print(f"  T0 (Format Character): {atr[2:4]} = {int(atr[2:4], 16)} protocols, {int(atr[2:4], 16) & 0x0F} historical bytes")
    
    # Historical bytes start after T0
    historical_start = 4
    historical_bytes = atr[historical_start:]
    print(f"  Historical Bytes: {historical_bytes}")
    
    # Try to decode historical bytes
    try:
        historical_ascii = bytes.fromhex(historical_bytes).decode('ascii', errors='ignore')
        print(f"  Historical ASCII: '{historical_ascii}'")
    except:
        print(f"  Historical ASCII: (not decodable)")
    
    # Analyze historical bytes pattern
    if "534C4A" in historical_bytes:  # "SLJ" in ASCII
        print(f"  ✓ Card contains 'SLJ' identifier")
        
    # Check UID pattern
    uid = "5501797A"
    print(f"\nUID Analysis:")
    print(f"  UID: {uid}")
    print(f"  UID Length: {len(uid)} hex digits ({len(uid)//2} bytes)")
    
    # Check if this follows ISO14443 Type A format
    if len(uid) == 8:  # 4 bytes
        print(f"  ✓ 4-byte UID (ISO14443 Type A)")
        
        uid_int = int(uid, 16)
        print(f"  UID as integer: {uid_int}")
        print(f"  UID binary: {bin(uid_int)[2:].zfill(32)}")
        
        # Check manufacturer patterns
        first_byte = int(uid[0:2], 16)
        print(f"  First byte: 0x{first_byte:02X}")
        
        if first_byte == 0x55:
            print(f"  ⚠️  First byte 0x55 - this might not be a payment card")
    
    # Card behavior analysis
    print(f"\n✓ Card Behavior Analysis:")
    print(f"  • Responds to PC/SC connection: ✓")
    print(f"  • Responds to Get UID (FFCA0000): ✓")
    print(f"  • Responds to PPSE selection: ✓")
    print(f"  • EMV application selection: ✓ (but GPO fails)")
    print(f"  • Track 2 / PAN extraction: ✗ (protected/not available)")
    
    # Conclusion
    print(f"\n🔍 CONCLUSION:")
    print(f"This appears to be either:")
    print(f"  1. A contactless payment card with strong security (PAN protected)")
    print(f"  2. An EMV card in 'personalization' mode (not activated)")
    print(f"  3. A test/demo card that simulates EMV but doesn't contain real PAN")
    print(f"  4. A non-payment contactless card (access card, transit card, etc.)")
    
    print(f"\n💡 RECOMMENDATION:")
    print(f"For UI display purposes:")
    print(f"  • Keep showing UID (5501797A) as the card identifier")
    print(f"  • Label it as 'Card Number' or 'Card ID' instead of 'PAN'")
    print(f"  • Show card type as 'Contactless Card' or 'Smart Card'")
    print(f"  • This is normal behavior for many non-payment contactless cards")
    
    return {
        'atr': atr,
        'uid': uid,
        'card_type': 'Contactless Smart Card',
        'identifier': uid,
        'identifier_type': 'Card ID',
        'is_payment_card': False
    }

if __name__ == "__main__":
    result = analyze_card_type()
    print(f"\n📋 UI DISPLAY RECOMMENDATION:")
    print(f"  Card ID: {result['identifier']}")
    print(f"  Card Type: {result['card_type']}")
    print(f"  ATR: {result['atr']}")
    if not result['is_payment_card']:
        print(f"  Note: This is not a payment card - no PAN available")
