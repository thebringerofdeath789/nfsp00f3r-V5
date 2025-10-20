#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test EMV Data Extraction
Test the EMV data extraction to verify we get the correct PAN and expiry.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_emv_data_extraction():
    """Test EMV data extraction to get correct PAN and expiry."""
    print("=== Testing EMV Data Extraction ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        
        # Get PC/SC readers
        reader_list = readers()
        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Select PPSE and applications
        ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31]
        response, sw1, sw2 = connection.transmit(ppse_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✓ PPSE selected successfully")
            
            # Try different AID lengths for A0000000031010
            aids_to_try = [
                ("A0000000031010", "VISA"),
                ("A000000003101001", "VISA Extended"),
                ("A00000000310", "VISA Short"),
            ]
            
            for aid_hex, label in aids_to_try:
                print(f"\nTrying AID: {aid_hex} ({label})")
                
                try:
                    # Select application
                    aid_bytes = bytes.fromhex(aid_hex)
                    select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
                    sel_response, sel_sw1, sel_sw2 = connection.transmit(select_cmd)
                    
                    print(f"  Select result: {sel_sw1:02X}{sel_sw2:02X}")
                    
                    if sel_sw1 == 0x90 and sel_sw2 == 0x00:
                        print("  ✓ Application selected")
                        
                        # Try GPO with different PDOL lengths
                        gpo_commands = [
                            [0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00],
                            [0x80, 0xA8, 0x00, 0x00, 0x04, 0x83, 0x02, 0x00, 0x00],
                            [0x80, 0xA8, 0x00, 0x00, 0x08, 0x83, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01],
                            [0x80, 0xA8, 0x00, 0x00, 0x0A, 0x83, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00],
                        ]
                        
                        gpo_success = False
                        for gpo_cmd in gpo_commands:
                            try:
                                gpo_response, gpo_sw1, gpo_sw2 = connection.transmit(gpo_cmd)
                                print(f"    GPO result: {gpo_sw1:02X}{gpo_sw2:02X}")
                                
                                if gpo_sw1 == 0x90 and gpo_sw2 == 0x00:
                                    print(f"    ✓ GPO successful!")
                                    gpo_success = True
                                    break
                                elif gpo_sw1 == 0x61:
                                    print(f"    ⚠️ More data available")
                                    get_resp = [0x00, 0xC0, 0x00, 0x00, gpo_sw2]
                                    more_data, more_sw1, more_sw2 = connection.transmit(get_resp)
                                    if more_sw1 == 0x90:
                                        print(f"    Additional GPO data: {toHexString(more_data)}")
                                        gpo_success = True
                                        break
                            except Exception as gpo_error:
                                print(f"    GPO error: {gpo_error}")
                        
                        if gpo_success:
                            # Now try to read records from different SFIs
                            found_data = {}
                            
                            for sfi in range(1, 6):
                                for record in range(1, 6):
                                    try:
                                        read_cmd = [0x00, 0xB2, record, (sfi << 3) | 0x04, 0x00]
                                        rec_response, rec_sw1, rec_sw2 = connection.transmit(read_cmd)
                                        
                                        if rec_sw1 == 0x90 and rec_sw2 == 0x00:
                                            hex_data = toHexString(rec_response).replace(' ', '')
                                            print(f"    ✓ Record SFI{sfi}.{record}: {len(hex_data)//2} bytes")
                                            
                                            # Parse this record for PAN and expiry
                                            pan, expiry, track2 = parse_record_for_data(hex_data)
                                            
                                            if pan:
                                                found_data['pan'] = pan
                                                print(f"      🎉 PAN: {pan}")
                                            if expiry:
                                                found_data['expiry'] = expiry
                                                print(f"      🎉 Expiry: {expiry}")
                                            if track2:
                                                found_data['track2'] = track2
                                                print(f"      🎉 Track2: {track2[:20]}...")
                                                
                                    except Exception as rec_error:
                                        pass  # Record not found
                            
                            if found_data:
                                print(f"\n  📋 EXTRACTED DATA:")
                                print(f"    PAN: {found_data.get('pan', 'Not found')}")
                                print(f"    Expiry: {found_data.get('expiry', 'Not found')}")
                                print(f"    Track2: {found_data.get('track2', 'Not found')}")
                                
                                # Verify against expected values
                                expected_pan = "4031630501721103"
                                expected_expiry = "07/30"
                                
                                if found_data.get('pan') == expected_pan:
                                    print(f"    ✅ PAN matches expected: {expected_pan}")
                                else:
                                    print(f"    ❌ PAN mismatch. Expected: {expected_pan}, Got: {found_data.get('pan')}")
                                    
                                if found_data.get('expiry') == expected_expiry:
                                    print(f"    ✅ Expiry matches expected: {expected_expiry}")
                                else:
                                    print(f"    ❌ Expiry mismatch. Expected: {expected_expiry}, Got: {found_data.get('expiry')}")
                                
                                return found_data
                                
                except Exception as app_error:
                    print(f"  ✗ Application error: {app_error}")
        
        connection.disconnect()
        return None
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_record_for_data(hex_data):
    """Parse EMV record data to extract PAN, expiry, and track2."""
    pan = None
    expiry = None
    track2 = None
    
    try:
        # Simple TLV parser
        i = 0
        while i < len(hex_data):
            if i + 2 > len(hex_data):
                break
                
            # Get tag
            tag = hex_data[i:i+2]
            i += 2
            
            # Handle multi-byte tags
            if tag in ['9F', '5F'] and i + 2 <= len(hex_data):
                tag += hex_data[i:i+2]
                i += 2
            
            if i >= len(hex_data):
                break
                
            # Get length
            if i + 2 > len(hex_data):
                break
                
            length_hex = hex_data[i:i+2]
            length = int(length_hex, 16)
            i += 2
            
            if i + length * 2 > len(hex_data):
                break
            
            # Get value
            value = hex_data[i:i+(length*2)]
            i += length * 2
            
            # Parse specific tags
            if tag == '5A':  # PAN
                pan = parse_pan_from_hex(value)
            elif tag == '57':  # Track 2
                track2 = parse_track2_from_hex(value)
                # Also extract PAN and expiry from track2
                if track2 and 'D' in track2:
                    parts = track2.split('D')
                    if len(parts) >= 2:
                        track2_pan = parts[0]
                        if not pan and 13 <= len(track2_pan) <= 19:
                            pan = track2_pan
                        
                        exp_part = parts[1]
                        if len(exp_part) >= 4:
                            yymm = exp_part[:4]
                            expiry = f"{yymm[2:4]}/{yymm[:2]}"
            elif tag == '5F24':  # Application expiry date
                if len(value) == 6:  # YYMMDD
                    yy = value[:2]
                    mm = value[2:4]
                    expiry = f"{mm}/{yy}"
                    
    except Exception as e:
        print(f"Parse error: {e}")
    
    return pan, expiry, track2

def parse_pan_from_hex(hex_value):
    """Parse PAN from packed BCD hex."""
    try:
        pan = ""
        for i in range(0, len(hex_value), 2):
            byte_hex = hex_value[i:i+2]
            byte_val = int(byte_hex, 16)
            
            high_nibble = (byte_val >> 4) & 0x0F
            low_nibble = byte_val & 0x0F
            
            for nibble in [high_nibble, low_nibble]:
                if nibble <= 9:
                    pan += str(nibble)
                elif nibble == 0xF:
                    return pan if 13 <= len(pan) <= 19 else None
        
        return pan if 13 <= len(pan) <= 19 else None
    except:
        return None

def parse_track2_from_hex(hex_value):
    """Parse Track2 from packed BCD hex."""
    try:
        track2 = ""
        for i in range(0, len(hex_value), 2):
            byte_hex = hex_value[i:i+2]
            byte_val = int(byte_hex, 16)
            
            high_nibble = (byte_val >> 4) & 0x0F
            low_nibble = byte_val & 0x0F
            
            for nibble in [high_nibble, low_nibble]:
                if nibble <= 9:
                    track2 += str(nibble)
                elif nibble == 0xD:
                    track2 += "D"
                elif nibble == 0xF:
                    return track2
        
        return track2
    except:
        return None

if __name__ == "__main__":
    result = test_emv_data_extraction()
    if result:
        print(f"\n🎉 SUCCESS! EMV data extracted correctly")
    else:
        print(f"\n❌ FAILED to extract expected EMV data")
