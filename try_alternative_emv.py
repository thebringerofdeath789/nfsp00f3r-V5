#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Try Alternative EMV Reading Methods
Try different approaches to read EMV data including static records.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def try_alternative_emv_reading():
    """Try alternative methods to read EMV data."""
    print("=== Trying Alternative EMV Reading Methods ===")
    
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
            
            # Select VISA application
            aid_hex = "A0000000031010"
            aid_bytes = bytes.fromhex(aid_hex)
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            sel_response, sel_sw1, sel_sw2 = connection.transmit(select_cmd)
            
            if sel_sw1 == 0x90 and sel_sw2 == 0x00:
                print("✓ VISA application selected")
                
                # Method 1: Try to read records without GPO (some cards allow this)
                print("\n--- Method 1: Direct Record Reading ---")
                for sfi in range(1, 6):
                    for record in range(1, 6):
                        try:
                            read_cmd = [0x00, 0xB2, record, (sfi << 3) | 0x04, 0x00]
                            rec_response, rec_sw1, rec_sw2 = connection.transmit(read_cmd)
                            
                            if rec_sw1 == 0x90 and rec_sw2 == 0x00:
                                hex_data = toHexString(rec_response).replace(' ', '')
                                print(f"  ✓ Record SFI{sfi}.{record}: {hex_data}")
                                
                                # Try to parse for PAN
                                if '5A' in hex_data:
                                    print(f"    Found PAN tag (5A)")
                                    pan = extract_pan_from_record(hex_data)
                                    if pan:
                                        print(f"    🎉 PAN: {pan}")
                                        
                                if '57' in hex_data:
                                    print(f"    Found Track2 tag (57)")
                                    track2 = extract_track2_from_record(hex_data)
                                    if track2:
                                        print(f"    🎉 Track2: {track2}")
                                        
                        except Exception as e:
                            pass
                
                # Method 2: Try GET DATA commands for specific tags
                print("\n--- Method 2: GET DATA Commands ---")
                get_data_tags = [
                    (0x5A, "PAN"),
                    (0x57, "Track 2 Equivalent Data"),
                    (0x5F20, "Cardholder Name"),
                    (0x5F24, "Application Expiry Date"),
                    (0x5F30, "Service Code"),
                    (0x9F0B, "Cardholder Name Extended"),
                    (0x9F1F, "Track 1 Discretionary Data"),
                ]
                
                for tag, description in get_data_tags:
                    try:
                        if tag <= 0xFF:
                            get_data_cmd = [0x80, 0xCA, 0x00, tag, 0x00]
                        else:
                            get_data_cmd = [0x80, 0xCA, (tag >> 8) & 0xFF, tag & 0xFF, 0x00]
                        
                        gd_response, gd_sw1, gd_sw2 = connection.transmit(get_data_cmd)
                        
                        if gd_sw1 == 0x90 and gd_sw2 == 0x00:
                            hex_data = toHexString(gd_response).replace(' ', '')
                            print(f"  ✓ {description}: {hex_data}")
                            
                            if tag == 0x5A:  # PAN
                                pan = parse_pan_from_hex(hex_data)
                                if pan:
                                    print(f"    🎉 Parsed PAN: {pan}")
                            elif tag == 0x57:  # Track 2
                                track2 = parse_track2_from_hex(hex_data)
                                if track2:
                                    print(f"    🎉 Parsed Track2: {track2}")
                        
                        elif gd_sw1 == 0x6A and gd_sw2 == 0x88:
                            print(f"  - {description}: Not found")
                        else:
                            print(f"  ✗ {description}: {gd_sw1:02X}{gd_sw2:02X}")
                    
                    except Exception as e:
                        print(f"  ✗ {description}: Error {e}")
                
                # Method 3: Try GPO with different transaction types
                print("\n--- Method 3: GPO with Different Parameters ---")
                
                # Try different transaction scenarios
                gpo_scenarios = [
                    # Basic scenarios
                    ([0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00], "Empty PDOL"),
                    
                    # With terminal verification results
                    ([0x80, 0xA8, 0x00, 0x00, 0x08, 0x83, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08], "With TVR"),
                    
                    # With amount and country code
                    ([0x80, 0xA8, 0x00, 0x00, 0x0E, 0x83, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x08, 0x40, 0x00, 0x00, 0x00, 0x00], "With Amount"),
                    
                    # Minimal transaction
                    ([0x80, 0xA8, 0x00, 0x00, 0x06, 0x83, 0x04, 0x00, 0x00, 0x00, 0x01], "Minimal Transaction"),
                ]
                
                for gpo_cmd, scenario in gpo_scenarios:
                    try:
                        gpo_response, gpo_sw1, gpo_sw2 = connection.transmit(gpo_cmd)
                        print(f"  {scenario}: {gpo_sw1:02X}{gpo_sw2:02X}")
                        
                        if gpo_sw1 == 0x90 and gpo_sw2 == 0x00:
                            print(f"    ✓ GPO successful! Response: {toHexString(gpo_response)}")
                            # Now try reading records
                            break
                        elif gpo_sw1 == 0x61:
                            print(f"    More data available")
                            get_resp = [0x00, 0xC0, 0x00, 0x00, gpo_sw2]
                            more_data, more_sw1, more_sw2 = connection.transmit(get_resp)
                            if more_sw1 == 0x90:
                                print(f"    Additional data: {toHexString(more_data)}")
                                break
                    except Exception as e:
                        print(f"    Error: {e}")
                
                # Method 4: Check application selection response for FCI data
                print("\n--- Method 4: Parse Application Selection Response ---")
                if sel_response:
                    fci_hex = toHexString(sel_response).replace(' ', '')
                    print(f"  FCI Data: {fci_hex}")
                    
                    # Try to extract any useful data from FCI
                    fci_data = parse_fci_for_data(fci_hex)
                    if fci_data:
                        print(f"  📋 FCI Data: {fci_data}")
        
        connection.disconnect()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

def extract_pan_from_record(hex_data):
    """Extract PAN from record hex data."""
    try:
        # Find 5A tag
        pos = hex_data.find('5A')
        if pos >= 0 and pos + 4 < len(hex_data):
            # Get length
            length_pos = pos + 2
            length = int(hex_data[length_pos:length_pos+2], 16)
            
            # Get PAN data
            pan_pos = length_pos + 2
            pan_hex = hex_data[pan_pos:pan_pos+(length*2)]
            
            return parse_pan_from_hex(pan_hex)
    except:
        pass
    return None

def extract_track2_from_record(hex_data):
    """Extract Track2 from record hex data."""
    try:
        # Find 57 tag
        pos = hex_data.find('57')
        if pos >= 0 and pos + 4 < len(hex_data):
            # Get length
            length_pos = pos + 2
            length = int(hex_data[length_pos:length_pos+2], 16)
            
            # Get Track2 data
            track2_pos = length_pos + 2
            track2_hex = hex_data[track2_pos:track2_pos+(length*2)]
            
            return parse_track2_from_hex(track2_hex)
    except:
        pass
    return None

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

def parse_fci_for_data(fci_hex):
    """Parse FCI data for useful information."""
    fci_data = {}
    try:
        # Look for application label, preferred name, etc.
        # This is basic parsing - real FCI parsing is more complex
        if '50' in fci_hex:  # Application label
            pos = fci_hex.find('50')
            if pos >= 0:
                length = int(fci_hex[pos+2:pos+4], 16)
                label_hex = fci_hex[pos+4:pos+4+(length*2)]
                try:
                    label = bytes.fromhex(label_hex).decode('ascii', errors='ignore')
                    fci_data['application_label'] = label
                except:
                    pass
    except:
        pass
    return fci_data

if __name__ == "__main__":
    try_alternative_emv_reading()
