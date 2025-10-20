#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze TLV Data from Card
Check what TLV data is actually available and extract PAN and Track2.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_card_tlv_data():
    """Analyze what TLV data is actually available on the card."""
    print("=== ANALYZING CARD TLV DATA ===")
    
    try:
        from card_manager import CardManager
        
        # Create card manager and read card
        card_manager = CardManager()
        result = card_manager.read_card("ACS ACR122 0")
        
        if result and 'card_id' in result:
            card_id = result['card_id']
            
            # Get the EMV card object
            emv_card = card_manager.cards.get(card_id)
            
            if emv_card:
                print("📋 CARD INFORMATION:")
                print(f"  ATR: {emv_card.atr}")
                print(f"  UID: {emv_card.uid}")
                print(f"  Current PAN: {emv_card.pan}")
                print(f"  Track2 Data: {emv_card.track2_data}")
                
                print(f"\n🏷️  TLV DATA ANALYSIS:")
                if emv_card.tlv_data:
                    print(f"  Total TLV tags: {len(emv_card.tlv_data)}")
                    
                    # Check for common EMV tags
                    important_tags = {
                        '5A': 'PAN (Application Primary Account Number)',
                        '57': 'Track 2 Equivalent Data',
                        '5F20': 'Cardholder Name',
                        '5F24': 'Application Expiration Date',
                        '5F30': 'Service Code',
                        '9F1F': 'Track 1 Discretionary Data',
                        '9F20': 'Track 2 Discretionary Data',
                        '9F0D': 'Issuer Action Code - Default',
                        '9F0E': 'Issuer Action Code - Denial',
                        '9F0F': 'Issuer Action Code - Online'
                    }
                    
                    found_tags = []
                    for tag, description in important_tags.items():
                        if tag in emv_card.tlv_data:
                            tag_data = emv_card.tlv_data[tag]
                            print(f"  ✓ {tag}: {description}")
                            print(f"    Data: {tag_data}")
                            found_tags.append(tag)
                            
                            # Extract PAN if found
                            if tag == '5A':
                                pan_data = tag_data.get('value', '') if isinstance(tag_data, dict) else str(tag_data)
                                if pan_data:
                                    print(f"    🎯 FOUND PAN: {pan_data}")
                            
                            # Extract Track 2 if found
                            elif tag == '57':
                                track2_data = tag_data.get('value', '') if isinstance(tag_data, dict) else str(tag_data)
                                if track2_data:
                                    print(f"    🎯 FOUND TRACK 2: {track2_data}")
                                    # Try to extract PAN from Track 2
                                    if 'D' in track2_data:
                                        track2_pan = track2_data.split('D')[0]
                                        print(f"    🎯 PAN FROM TRACK 2: {track2_pan}")
                    
                    if not found_tags:
                        print("  ⚠️  No important EMV tags found")
                        print("  📋 All available tags:")
                        for tag, data in emv_card.tlv_data.items():
                            print(f"    {tag}: {data}")
                    
                else:
                    print("  ❌ No TLV data available")
                
                print(f"\n📱 APPLICATIONS:")
                if emv_card.applications:
                    for aid, app in emv_card.applications.items():
                        print(f"  Application: {app.application_label} (AID: {aid})")
                        if hasattr(app, 'records') and app.records:
                            print(f"    Records: {len(app.records)}")
                            for sfi, records in app.records.items():
                                for record in records:
                                    if hasattr(record, 'tlv_data') and record.tlv_data:
                                        print(f"    SFI {sfi} Record TLV: {list(record.tlv_data.keys())}")
                else:
                    print("  ❌ No applications found")
                
                return emv_card
            else:
                print("❌ No EMV card object found")
                return None
        else:
            print("❌ No card reading result")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_direct_tlv_extraction():
    """Test direct TLV extraction using PC/SC."""
    print("\n=== TESTING DIRECT TLV EXTRACTION ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get PC/SC readers
        reader_list = readers()
        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Select PPSE first
        ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
        response, sw1, sw2 = connection.transmit(ppse_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✓ PPSE selected")
            
            # Try to select known AIDs
            test_aids = [
                "A0000000031010",  # Visa
                "A00000009808",    # US Debit
            ]
            
            for aid_hex in test_aids:
                try:
                    print(f"\nTesting AID: {aid_hex}")
                    aid_bytes = bytes.fromhex(aid_hex)
                    
                    # Select application
                    select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
                    sel_response, sel_sw1, sel_sw2 = connection.transmit(select_cmd)
                    
                    if sel_sw1 == 0x90:
                        print(f"  ✓ Application selected")
                        
                        # Try to read records directly
                        for sfi in range(1, 5):
                            for rec in range(1, 5):
                                try:
                                    read_cmd = [0x00, 0xB2, rec, (sfi << 3) | 0x04, 0x00]
                                    rec_response, rec_sw1, rec_sw2 = connection.transmit(read_cmd)
                                    
                                    if rec_sw1 == 0x90 and rec_sw2 == 0x00:
                                        hex_data = toHexString(rec_response).replace(' ', '')
                                        print(f"  ✓ SFI{sfi}.{rec}: {hex_data}")
                                        
                                        # Look for PAN tag (5A) and Track2 tag (57)
                                        if '5A' in hex_data:
                                            print(f"    🎯 Found PAN tag in record!")
                                        if '57' in hex_data:
                                            print(f"    🎯 Found Track2 tag in record!")
                                            
                                except:
                                    pass
                        
                except Exception as e:
                    print(f"  ❌ AID {aid_hex} failed: {e}")
        
        connection.disconnect()
        
    except Exception as e:
        print(f"❌ Direct extraction failed: {e}")

if __name__ == "__main__":
    emv_card = analyze_card_tlv_data()
    test_direct_tlv_extraction()
    
    if emv_card:
        print(f"\n{'='*50}")
        print("📋 SUMMARY:")
        if emv_card.pan:
            print(f"✅ PAN is available: {emv_card.pan}")
        else:
            print("❌ PAN not extracted - check TLV parsing")
            
        if emv_card.track2_data:
            print(f"✅ Track2 is available: {emv_card.track2_data}")
        else:
            print("❌ Track2 not extracted - check TLV parsing")
        print("="*50)
