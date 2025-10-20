#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct EMV Record Reading
Read EMV records directly to extract PAN and Track2 data.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def read_emv_records_directly():
    """Read EMV records directly from the card."""
    print("=== DIRECT EMV RECORD READING ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get PC/SC readers
        reader_list = readers()
        
        if not reader_list:
            print("❌ No readers found")
            return
            
        reader = reader_list[0]
        print(f"Using reader: {reader}")
        
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Get ATR and UID for reference
        atr_bytes = connection.getATR()
        atr = toHexString(atr_bytes).replace(' ', '')
        print(f"ATR: {atr}")
        
        # Get UID
        uid_response, uid_sw1, uid_sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
        if uid_sw1 == 0x90:
            uid = toHexString(uid_response).replace(' ', '')
            print(f"UID: {uid}")
        
        # Select PPSE
        ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
        response, sw1, sw2 = connection.transmit(ppse_cmd)
        
        if sw1 != 0x90:
            print(f"❌ PPSE selection failed: {sw1:02X}{sw2:02X}")
            return
            
        print("✓ PPSE selected")
        
        # Known EMV AIDs to try
        emv_aids = [
            ("A0000000031010", "Visa Credit/Debit"),
            ("A00000009808", "PayPass/MasterCard"),
            ("A0000000032010", "Visa Credit/Debit Alt"),
            ("A0000000041010", "Visa Credit/Debit Alt2"),
        ]
        
        pan_found = None
        track2_found = None
        
        for aid_hex, aid_desc in emv_aids:
            print(f"\n🔍 Trying {aid_desc} (AID: {aid_hex})")
            
            try:
                aid_bytes = bytes.fromhex(aid_hex)
                
                # Select application
                select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
                sel_response, sel_sw1, sel_sw2 = connection.transmit(select_cmd)
                
                print(f"  Select result: {sel_sw1:02X}{sel_sw2:02X}")
                
                if sel_sw1 == 0x90:
                    print(f"  ✓ Application selected")
                    
                    # Try Get Processing Options (GPO)
                    gpo_variations = [
                        [0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00],
                        [0x80, 0xA8, 0x00, 0x00, 0x04, 0x83, 0x02, 0x00, 0x00],
                    ]
                    
                    gpo_success = False
                    for gpo_cmd in gpo_variations:
                        gpo_response, gpo_sw1, gpo_sw2 = connection.transmit(gpo_cmd)
                        print(f"    GPO result: {gpo_sw1:02X}{gpo_sw2:02X}")
                        
                        if gpo_sw1 == 0x90:
                            print(f"    ✓ GPO successful")
                            print(f"    GPO data: {toHexString(gpo_response)}")
                            gpo_success = True
                            break
                        elif gpo_sw1 == 0x61:
                            # More data available
                            get_response = [0x00, 0xC0, 0x00, 0x00, gpo_sw2]
                            more_data, more_sw1, more_sw2 = connection.transmit(get_response)
                            if more_sw1 == 0x90:
                                print(f"    ✓ GPO data retrieved: {toHexString(more_data)}")
                                gpo_success = True
                                break
                    
                    if not gpo_success:
                        print("    ❌ GPO failed, trying record reading anyway")
                    
                    # Read records from various SFIs
                    print("    🔍 Reading records...")
                    
                    for sfi in range(1, 8):  # Try SFI 1-7
                        for record_num in range(1, 6):  # Try records 1-5
                            try:
                                # READ RECORD command
                                read_cmd = [0x00, 0xB2, record_num, (sfi << 3) | 0x04, 0x00]
                                rec_response, rec_sw1, rec_sw2 = connection.transmit(read_cmd)
                                
                                if rec_sw1 == 0x90 and rec_sw2 == 0x00 and rec_response:
                                    hex_data = toHexString(rec_response).replace(' ', '')
                                    print(f"    ✓ SFI{sfi}.{record_num}: {len(rec_response)} bytes")
                                    print(f"      Data: {hex_data}")
                                    
                                    # Parse for PAN and Track2
                                    pan, track2 = parse_emv_record(hex_data)
                                    
                                    if pan and not pan_found:
                                        pan_found = pan
                                        print(f"      🎯 FOUND PAN: {pan}")
                                    
                                    if track2 and not track2_found:
                                        track2_found = track2
                                        print(f"      🎯 FOUND TRACK2: {track2}")
                                    
                                    # If we found both, we can stop
                                    if pan_found and track2_found:
                                        print(f"    ✅ Both PAN and Track2 found!")
                                        break
                                        
                            except Exception as e:
                                # Record doesn't exist, continue
                                pass
                        
                        if pan_found and track2_found:
                            break
                
                if pan_found and track2_found:
                    break
                    
            except Exception as e:
                print(f"  ❌ Error with {aid_desc}: {e}")
        
        connection.disconnect()
        
        print(f"\n{'='*50}")
        print("📋 EXTRACTION RESULTS:")
        if pan_found:
            print(f"✅ PAN: {pan_found}")
        else:
            print("❌ PAN not found")
            
        if track2_found:
            print(f"✅ Track2: {track2_found}")
        else:
            print("❌ Track2 not found")
        print("="*50)
        
        return pan_found, track2_found
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def parse_emv_record(hex_data):
    """Parse EMV record data to extract PAN and Track2."""
    pan = None
    track2 = None
    
    try:
        # Look for PAN tag (5A)
        pan_index = hex_data.find('5A')
        if pan_index != -1:
            # Get length byte
            length_pos = pan_index + 2
            if length_pos < len(hex_data):
                length = int(hex_data[length_pos:length_pos+2], 16)
                data_pos = length_pos + 2
                pan_hex = hex_data[data_pos:data_pos+(length*2)]
                
                # Remove padding 'F's and convert
                pan = pan_hex.replace('F', '')
                if len(pan) >= 13 and pan.isdigit():
                    print(f"        PAN tag found: {pan}")
        
        # Look for Track 2 tag (57)
        track2_index = hex_data.find('57')
        if track2_index != -1:
            # Get length byte
            length_pos = track2_index + 2
            if length_pos < len(hex_data):
                length = int(hex_data[length_pos:length_pos+2], 16)
                data_pos = length_pos + 2
                track2_hex = hex_data[data_pos:data_pos+(length*2)]
                
                # Convert hex to track2 format
                track2_data = ""
                for i in range(0, len(track2_hex), 2):
                    byte_hex = track2_hex[i:i+2]
                    byte_val = int(byte_hex, 16)
                    
                    # Convert to track2 characters
                    if byte_val == 0xD0:
                        track2_data += "D"
                    elif 0x00 <= byte_val <= 0x09:
                        track2_data += str(byte_val)
                    elif 0x10 <= byte_val <= 0x19:
                        track2_data += str(byte_val - 0x10)
                    elif byte_val == 0xFF:
                        break  # Padding
                    else:
                        track2_data += f"{byte_val:X}"
                
                if 'D' in track2_data:
                    print(f"        Track2 tag found: {track2_data}")
                    track2 = track2_data
        
    except Exception as e:
        print(f"        Parse error: {e}")
    
    return pan, track2

if __name__ == "__main__":
    pan, track2 = read_emv_records_directly()
    
    if pan or track2:
        print(f"\n🎉 SUCCESS!")
        print(f"The card DOES contain readable payment data:")
        if pan:
            print(f"• PAN: {pan} (Valid {len(pan)}-digit card number)")
        if track2:
            print(f"• Track2: {track2}")
        print(f"\nThe issue is in the TLV parsing - we need to fix the extraction logic!")
    else:
        print(f"\n⚠️  No payment data found in accessible records.")
        print(f"This could mean:")
        print(f"• The card stores data in protected records")
        print(f"• Additional authentication is required") 
        print(f"• The card uses different record structures")
