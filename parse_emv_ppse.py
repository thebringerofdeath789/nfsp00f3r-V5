#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse EMV PPSE Response
Parse the PPSE response to extract EMV application information and try to get PAN.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def parse_emv_ppse():
    """Parse EMV PPSE response and try to get PAN from applications."""
    print("=== Parsing EMV PPSE Response ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString, toBytes
        
        # Get PC/SC readers
        reader_list = readers()
        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Select PPSE
        ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E] + toBytes("325041592E5359532E4444463031")
        response, sw1, sw2 = connection.transmit(ppse_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✓ PPSE selected successfully")
            hex_data = toHexString(response).replace(' ', '')
            print(f"PPSE Response: {hex_data}")
            
            # Parse TLV data
            applications = parse_tlv_applications(response)
            
            if applications:
                print(f"Found {len(applications)} EMV applications:")
                
                for i, app in enumerate(applications):
                    print(f"\nApplication {i+1}:")
                    print(f"  AID: {app.get('aid', 'Unknown')}")
                    print(f"  Label: {app.get('label', 'Unknown')}")
                    
                    # Try to select and read each application
                    aid_bytes = bytes.fromhex(app['aid']) if app.get('aid') else None
                    if aid_bytes:
                        pan = select_and_read_application(connection, aid_bytes, app['label'])
                        if pan:
                            print(f"  ✓ PAN FOUND: {pan}")
                            return pan
                        else:
                            print(f"  ✗ Could not extract PAN")
            else:
                print("✗ No EMV applications found in PPSE")
        else:
            print(f"✗ PPSE selection failed: {sw1:02X}{sw2:02X}")
        
        connection.disconnect()
        return None
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_tlv_applications(data):
    """Parse TLV data to extract EMV applications."""
    applications = []
    
    try:
        i = 0
        while i < len(data):
            tag = data[i]
            
            if tag == 0x6F:  # FCI Template
                i += 1
                length = data[i]
                i += 1
                fci_data = data[i:i+length]
                
                # Look for Directory Entry (A5)
                for j in range(len(fci_data)):
                    if fci_data[j] == 0xA5:
                        dir_length = fci_data[j+1]
                        dir_data = fci_data[j+2:j+2+dir_length]
                        apps = parse_directory_entries(dir_data)
                        applications.extend(apps)
                        break
                        
                i += length
            else:
                i += 1
                
    except Exception as e:
        print(f"TLV parsing error: {e}")
        
    return applications

def parse_directory_entries(data):
    """Parse directory entries to find EMV applications."""
    applications = []
    
    try:
        i = 0
        while i < len(data):
            if data[i] == 0x61:  # Entry
                i += 1
                length = data[i]
                i += 1
                entry_data = data[i:i+length]
                
                app = {}
                j = 0
                while j < len(entry_data):
                    if entry_data[j] == 0x4F:  # AID
                        aid_len = entry_data[j+1]
                        aid = entry_data[j+2:j+2+aid_len]
                        app['aid'] = aid.hex().upper()
                        j += 2 + aid_len
                    elif entry_data[j] == 0x50:  # Application Label
                        label_len = entry_data[j+1]
                        label = entry_data[j+2:j+2+label_len]
                        app['label'] = label.decode('ascii', errors='ignore')
                        j += 2 + label_len
                    else:
                        j += 1
                        
                if 'aid' in app:
                    applications.append(app)
                    
                i += length
            else:
                i += 1
                
    except Exception as e:
        print(f"Directory parsing error: {e}")
        
    return applications

def select_and_read_application(connection, aid_bytes, app_label):
    """Select EMV application and try to extract PAN."""
    
    try:
        print(f"  Selecting application: {app_label}")
        
        # Select application
        select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
        response, sw1, sw2 = connection.transmit(select_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print(f"  ✓ Application selected")
            
            # Get Processing Options
            gpo_cmd = [0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00]
            gpo_response, gpo_sw1, gpo_sw2 = connection.transmit(gpo_cmd)
            
            if gpo_sw1 == 0x90 and gpo_sw2 == 0x00:
                print(f"  ✓ Got processing options")
                
                # Try to read common EMV data objects
                data_objects_to_read = [
                    (0x5A, "PAN"),
                    (0x5F24, "Expiration Date"),
                    (0x5F20, "Cardholder Name"),
                    (0x57, "Track 2 Equivalent Data"),
                ]
                
                for tag, description in data_objects_to_read:
                    pan = read_data_object(connection, tag, description)
                    if pan and description == "PAN":
                        return pan
                        
            elif gpo_sw1 == 0x61:
                print(f"  ⚠️  More data available for GPO")
                # Try to get response
                get_resp = [0x00, 0xC0, 0x00, 0x00, gpo_sw2]
                more_data, more_sw1, more_sw2 = connection.transmit(get_resp)
                if more_sw1 == 0x90:
                    print(f"  Additional GPO data: {toHexString(more_data)}")
            else:
                print(f"  ✗ GPO failed: {gpo_sw1:02X}{gpo_sw2:02X}")
                
        else:
            print(f"  ✗ Application selection failed: {sw1:02X}{sw2:02X}")
            
    except Exception as e:
        print(f"  ✗ Application error: {e}")
        
    return None

def read_data_object(connection, tag, description):
    """Read a specific EMV data object."""
    
    try:
        if tag <= 0xFF:
            cmd = [0x80, 0xCA, 0x00, tag, 0x00]
        else:
            cmd = [0x80, 0xCA, (tag >> 8) & 0xFF, tag & 0xFF, 0x00]
            
        response, sw1, sw2 = connection.transmit(cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            hex_data = toHexString(response).replace(' ', '')
            print(f"    ✓ {description}: {hex_data}")
            
            if description == "PAN" and len(hex_data) >= 16:
                # Extract PAN from response (usually the raw data)
                return hex_data
                
        elif sw1 == 0x6A and sw2 == 0x88:
            print(f"    - {description}: Not found")
        else:
            print(f"    ✗ {description}: Failed {sw1:02X}{sw2:02X}")
            
    except Exception as e:
        print(f"    ✗ {description}: Error {e}")
        
    return None

if __name__ == "__main__":
    pan = parse_emv_ppse()
    if pan:
        print(f"\n🎉 REAL PAN FOUND: {pan}")
    else:
        print(f"\n⚠️  Could not extract PAN - card may not store PAN in readable form")
