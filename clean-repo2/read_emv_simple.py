#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple EMV Application Reader
Simplified approach to read EMV applications and extract PAN.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def read_emv_applications():
    """Simple approach to read EMV applications."""
    print("=== Reading EMV Applications ===")
    
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
            print("✓ PPSE selected successfully")
            
            # From the previous output, I can see the applications:
            # Two AIDs were visible: A0000000031010 and A000000098084
            
            applications_to_try = [
                ("A0000000031010", "VISA DEBIT"),
                ("A000000098084", "US DEBIT"),  # This might be shorter, let's try different lengths
                ("A00000009808", "US DEBIT (short)"),
            ]
            
            for aid_hex, label in applications_to_try:
                print(f"\nTrying application: {label} (AID: {aid_hex})")
                
                try:
                    aid_bytes = bytes.fromhex(aid_hex)
                    
                    # Select application
                    select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
                    sel_response, sel_sw1, sel_sw2 = connection.transmit(select_cmd)
                    
                    print(f"  Select result: {sel_sw1:02X}{sel_sw2:02X}")
                    
                    if sel_sw1 == 0x90 and sel_sw2 == 0x00:
                        print(f"  ✓ Application selected successfully")
                        
                        # Try Get Processing Options with minimal PDOL
                        gpo_variations = [
                            [0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00],
                            [0x80, 0xA8, 0x00, 0x00, 0x04, 0x83, 0x02, 0x00, 0x00],
                            [0x80, 0xA8, 0x00, 0x00, 0x08, 0x83, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01],
                        ]
                        
                        gpo_success = False
                        for gpo_cmd in gpo_variations:
                            gpo_response, gpo_sw1, gpo_sw2 = connection.transmit(gpo_cmd)
                            print(f"    GPO attempt: {gpo_sw1:02X}{gpo_sw2:02X}")
                            
                            if gpo_sw1 == 0x90 and gpo_sw2 == 0x00:
                                print(f"    ✓ GPO successful!")
                                print(f"    GPO Response: {toHexString(gpo_response)}")
                                gpo_success = True
                                break
                            elif gpo_sw1 == 0x61:
                                print(f"    ⚠️  More data available")
                                get_resp = [0x00, 0xC0, 0x00, 0x00, gpo_sw2]
                                more_data, more_sw1, more_sw2 = connection.transmit(get_resp)
                                if more_sw1 == 0x90:
                                    print(f"    Additional data: {toHexString(more_data)}")
                                    gpo_success = True
                                    break
                        
                        if gpo_success:
                            # Now try to read EMV data elements
                            data_elements = [
                                ([0x80, 0xCA, 0x00, 0x5A, 0x00], "PAN (5A)"),
                                ([0x80, 0xCA, 0x00, 0x57, 0x00], "Track 2 Equivalent (57)"),
                                ([0x80, 0xCA, 0x5F, 0x24, 0x00], "Expiration Date (5F24)"),
                                ([0x80, 0xCA, 0x5F, 0x20, 0x00], "Cardholder Name (5F20)"),
                                ([0x80, 0xCA, 0x9F, 0x1F, 0x00], "Track 1 Discretionary Data (9F1F)"),
                                ([0x00, 0xB2, 0x01, 0x0C, 0x00], "Read Record SFI 1"),
                                ([0x00, 0xB2, 0x02, 0x0C, 0x00], "Read Record SFI 2"),
                                ([0x00, 0xB2, 0x01, 0x14, 0x00], "Read Record SFI 2 Rec 1"),
                                ([0x00, 0xB2, 0x02, 0x14, 0x00], "Read Record SFI 2 Rec 2"),
                            ]
                            
                            for cmd, desc in data_elements:
                                try:
                                    data_response, data_sw1, data_sw2 = connection.transmit(cmd)
                                    
                                    if data_sw1 == 0x90 and data_sw2 == 0x00:
                                        hex_data = toHexString(data_response).replace(' ', '')
                                        print(f"    ✓ {desc}: {hex_data}")
                                        
                                        # Check if this looks like PAN data
                                        if "PAN" in desc and len(hex_data) >= 16:
                                            # Try to extract PAN
                                            potential_pan = extract_pan_from_hex(hex_data)
                                            if potential_pan:
                                                print(f"    🎉 POTENTIAL PAN: {potential_pan}")
                                                return potential_pan
                                                
                                        elif "Track 2" in desc and len(hex_data) >= 16:
                                            # Track 2 data contains PAN
                                            track2_pan = extract_pan_from_track2(hex_data)
                                            if track2_pan:
                                                print(f"    🎉 PAN FROM TRACK 2: {track2_pan}")
                                                return track2_pan
                                                
                                        elif "Record" in desc and len(hex_data) >= 20:
                                            # Records might contain TLV with PAN
                                            record_pan = extract_pan_from_record(hex_data)
                                            if record_pan:
                                                print(f"    🎉 PAN FROM RECORD: {record_pan}")
                                                return record_pan
                                    
                                    elif data_sw1 == 0x6A and data_sw2 == 0x88:
                                        print(f"    - {desc}: Not found")
                                    else:
                                        print(f"    ✗ {desc}: {data_sw1:02X}{data_sw2:02X}")
                                        
                                except Exception as e:
                                    print(f"    ✗ {desc}: Error {e}")
                        
                    else:
                        print(f"  ✗ Application selection failed")
                        
                except Exception as app_error:
                    print(f"  ✗ Application error: {app_error}")
                    
        else:
            print(f"✗ PPSE selection failed: {sw1:02X}{sw2:02X}")
        
        connection.disconnect()
        return None
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_pan_from_hex(hex_data):
    """Try to extract PAN from hex data."""
    # Look for sequences that start with common card prefixes and are 16 digits
    for i in range(0, len(hex_data) - 15, 2):
        potential = hex_data[i:i+16]
        if potential[0] in ['4', '5', '3', '6'] and potential.isdigit():
            return potential
    return None

def extract_pan_from_track2(hex_data):
    """Extract PAN from Track 2 equivalent data."""
    try:
        # Track 2 format: PAN + 'D' + expiry + service code + discretionary data
        # Look for 'D' separator (0xD in hex)
        if 'D' in hex_data:
            pan_part = hex_data.split('D')[0]
            if len(pan_part) >= 13 and len(pan_part) <= 19 and pan_part.isdigit():
                return pan_part
    except:
        pass
    return None

def extract_pan_from_record(hex_data):
    """Try to extract PAN from EMV record TLV data."""
    # Look for tag 5A (PAN) in TLV
    try:
        i = 0
        while i < len(hex_data) - 4:
            if hex_data[i:i+2] == '5A':  # PAN tag
                # Get length
                length_hex = hex_data[i+2:i+4]
                length = int(length_hex, 16)
                if length > 0 and length <= 10:  # Reasonable PAN length in bytes
                    pan_hex = hex_data[i+4:i+4+(length*2)]
                    if len(pan_hex) >= 16 and pan_hex.replace('F', '').isdigit():
                        # Remove padding F's
                        pan = pan_hex.replace('F', '')
                        if len(pan) >= 13:
                            return pan
            i += 2
    except:
        pass
    return None

if __name__ == "__main__":
    pan = read_emv_applications()
    if pan:
        print(f"\n🎉 REAL PAN EXTRACTED: {pan}")
        print(f"This is a proper {len(pan)}-digit card number!")
    else:
        print(f"\n❌ Could not extract PAN")
        print("The card may not store the PAN in a readable format,")
        print("or it may be protected by additional security measures.")
