#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Card Analysis
Read the actual card and determine its type and capabilities.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_actual_card():
    """Comprehensive analysis of the actual card in the reader."""
    print("=== COMPREHENSIVE CARD ANALYSIS ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get PC/SC readers
        reader_list = readers()
        
        if not reader_list:
            print("✗ No readers found")
            return
            
        reader = reader_list[0]
        print(f"Reader: {reader}")
        
        # Create connection
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Get ATR and analyze it
        atr_bytes = connection.getATR()
        atr = toHexString(atr_bytes).replace(' ', '')
        print(f"ATR: {atr}")
        
        # Analyze ATR
        print("\n--- ATR Analysis ---")
        analyze_atr(atr)
        
        # Get UID
        print("\n--- Basic Card Data ---")
        try:
            uid_response, uid_sw1, uid_sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            if uid_sw1 == 0x90 and uid_sw2 == 0x00:
                uid = toHexString(uid_response).replace(' ', '')
                print(f"UID: {uid}")
            else:
                print(f"UID read failed: {uid_sw1:02X}{uid_sw2:02X}")
        except Exception as e:
            print(f"UID read error: {e}")
        
        # Test various card types
        print("\n--- Card Type Detection ---")
        card_type = detect_card_type(connection, atr)
        print(f"Detected Card Type: {card_type}")
        
        # Test what commands work
        print("\n--- Supported Commands ---")
        test_supported_commands(connection)
        
        # Final recommendation
        print("\n--- RECOMMENDATION ---")
        recommend_card_display(card_type, uid if 'uid' in locals() else None)
        
        connection.disconnect()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def analyze_atr(atr):
    """Analyze the ATR to understand card type."""
    
    print(f"ATR Length: {len(atr)//2} bytes")
    
    # ATR structure analysis
    if len(atr) >= 2:
        ts = atr[:2]
        print(f"TS (Initial Character): {ts}")
        if ts == "3B":
            print("  - Direct convention")
        elif ts == "3F":
            print("  - Inverse convention")
    
    # Known ATR patterns
    atr_patterns = {
        "3B888001534C4A": "Java Card / Smart Card",
        "3B8F8001804F0C": "EMV Payment Card",
        "3B6800008073C4": "Mifare Classic",
        "3B8C800150": "GSM SIM Card",
    }
    
    for pattern, card_type in atr_patterns.items():
        if atr.startswith(pattern):
            print(f"ATR Pattern Match: {card_type}")
            return card_type
    
    # Generic analysis
    if "534C4A" in atr:
        print("Contains 'SLJ' - likely Smart Logic Java card")
    if "4A26" in atr:
        print("Contains manufacturer-specific data")
    
    return "Unknown Smart Card"

def detect_card_type(connection, atr):
    """Detect card type based on supported commands."""
    
    card_capabilities = {
        'emv_ppse': False,
        'emv_pse': False,
        'mifare': False,
        'iso14443a': False,
        'iso14443b': False,
        'java_card': False,
        'gsm': False
    }
    
    # Test EMV PPSE
    try:
        ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
        response, sw1, sw2 = connection.transmit(ppse_cmd)
        if sw1 == 0x90:
            card_capabilities['emv_ppse'] = True
            print("✓ Supports EMV PPSE")
    except:
        pass
    
    # Test EMV PSE
    try:
        pse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x31, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
        response, sw1, sw2 = connection.transmit(pse_cmd)
        if sw1 == 0x90:
            card_capabilities['emv_pse'] = True
            print("✓ Supports EMV PSE")
    except:
        pass
    
    # Test ISO 14443 Type A
    try:
        uid_cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(uid_cmd)
        if sw1 == 0x90:
            card_capabilities['iso14443a'] = True
            print("✓ ISO 14443 Type A compatible")
    except:
        pass
    
    # Test Java Card SELECT
    try:
        select_cmd = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]
        response, sw1, sw2 = connection.transmit(select_cmd)
        if sw1 == 0x90 or sw1 == 0x61:
            card_capabilities['java_card'] = True
            print("✓ Java Card compatible")
    except:
        pass
    
    # Determine card type
    if card_capabilities['emv_ppse'] or card_capabilities['emv_pse']:
        if card_capabilities['iso14443a']:
            return "EMV Contactless Card"
        else:
            return "EMV Contact Card"
    elif card_capabilities['java_card'] and card_capabilities['iso14443a']:
        return "Contactless Smart Card (Java Card)"
    elif card_capabilities['iso14443a']:
        return "ISO 14443 Type A Card"
    elif card_capabilities['java_card']:
        return "Contact Smart Card (Java Card)"
    elif "534C4A" in atr:
        return "Smart Logic Java Card"
    else:
        return "Unknown Smart Card"

def test_supported_commands(connection):
    """Test various commands to see what the card supports."""
    
    test_commands = [
        ([0xFF, 0xCA, 0x00, 0x00, 0x00], "Get UID"),
        ([0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00], "Select Master File"),
        ([0x00, 0xB0, 0x00, 0x00, 0x08], "Read Binary (8 bytes)"),
        ([0x80, 0xCA, 0x00, 0x5A, 0x00], "Get PAN"),
        ([0x80, 0xCA, 0x00, 0x57, 0x00], "Get Track 2"),
        ([0x00, 0xC0, 0x00, 0x00, 0x08], "Get Response"),
        ([0x80, 0xF2, 0x00, 0x00, 0x02, 0x00, 0x00], "PIN Verify"),
    ]
    
    supported = []
    for cmd, desc in test_commands:
        try:
            response, sw1, sw2 = connection.transmit(cmd)
            status = f"{sw1:02X}{sw2:02X}"
            
            if sw1 == 0x90:
                print(f"✓ {desc}: SUCCESS ({status})")
                supported.append(desc)
            elif sw1 == 0x61:
                print(f"⚠️ {desc}: More data available ({status})")
                supported.append(f"{desc} (partial)")
            elif sw1 == 0x6A and sw2 == 0x88:
                print(f"- {desc}: Not found ({status})")
            elif sw1 == 0x6D and sw2 == 0x00:
                print(f"- {desc}: Command not supported ({status})")
            else:
                print(f"✗ {desc}: Failed ({status})")
                
        except Exception as e:
            print(f"✗ {desc}: Error - {e}")
    
    return supported

def recommend_card_display(card_type, uid):
    """Provide recommendations for displaying this card type."""
    
    print(f"Card Type: {card_type}")
    
    if "EMV" in card_type and "Contactless" in card_type:
        print("\nRecommendation:")
        print("- This appears to be an EMV contactless payment card")
        print("- The UID should NOT be displayed as PAN")
        print("- PAN extraction failed due to security restrictions")
        print("- Display: 'EMV Contactless Card' with masked UID")
        
    elif "Smart Card" in card_type or "Java Card" in card_type:
        print("\nRecommendation:")
        print("- This is a smart card but NOT a payment card")
        print(f"- UID ({uid}) is the correct identifier")
        print("- Display: 'Smart Card' with UID as card identifier")
        print("- No PAN expected (not a payment card)")
        
    elif "ISO 14443" in card_type:
        print("\nRecommendation:")
        print("- This is a contactless smart card")
        print(f"- UID ({uid}) is the card identifier")
        print("- Display: 'Contactless Smart Card' with UID")
        print("- May be access card, transit card, or similar")
    
    else:
        print("\nRecommendation:")
        print("- Card type unclear")
        print("- Display available data (ATR, UID)")
        print("- Label as 'Unknown Smart Card'")
    
    print(f"\nSUGGESTED UI DISPLAY:")
    print(f"- Card Type: {card_type}")
    print(f"- Card ID: {uid if uid else 'N/A'}")
    print(f"- PAN: N/A (Not a payment card)" if "Smart Card" in card_type and "EMV" not in card_type else "- PAN: Protected/Not readable")

if __name__ == "__main__":
    analyze_actual_card()
