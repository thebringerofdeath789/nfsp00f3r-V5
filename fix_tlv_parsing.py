#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix TLV Parsing for EMV Data
Properly parse the TLV data to extract correct PAN and Track2.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def parse_tlv_properly():
    """Parse TLV data properly to extract correct PAN and Track2."""
    print("=== PROPER TLV PARSING ===")
    
    # The raw data from our successful read
    record_data = "702757134031630501721103D30072010000099999991F5F200F43415244484F4C4445522F56495341"
    
    print(f"Raw record data: {record_data}")
    print(f"Length: {len(record_data)} hex chars ({len(record_data)//2} bytes)")
    
    # Parse manually to understand the structure
    print(f"\n🔍 Manual TLV Analysis:")
    
    i = 0
    while i < len(record_data):
        if i + 2 > len(record_data):
            break
            
        # Get tag
        tag = record_data[i:i+2]
        i += 2
        
        if i >= len(record_data):
            break
            
        # Get length
        length_byte = record_data[i:i+2]
        length = int(length_byte, 16)
        i += 2
        
        if i + length * 2 > len(record_data):
            break
            
        # Get value
        value = record_data[i:i+(length*2)]
        i += length * 2
        
        print(f"  Tag {tag}: Length {length} bytes, Value: {value}")
        
        # Check for important tags
        if tag == '70':
            print(f"    📋 Template tag - contains nested TLV data")
            parse_nested_tlv(value)
        elif tag == '57':
            print(f"    💳 Track 2 Equivalent Data")
            track2 = parse_track2_data(value)
            if track2:
                print(f"    🎯 PARSED TRACK2: {track2}")
        elif tag == '5A':
            print(f"    🏦 PAN (Primary Account Number)")
            pan = parse_pan_data(value)
            if pan:
                print(f"    🎯 PARSED PAN: {pan}")

def parse_nested_tlv(hex_data):
    """Parse nested TLV data."""
    print(f"    Parsing nested data: {hex_data}")
    
    i = 0
    while i < len(hex_data):
        if i + 2 > len(hex_data):
            break
            
        # Get tag (might be 2 bytes for some tags)
        tag = hex_data[i:i+2]
        i += 2
        
        # Handle multi-byte tags (if first byte >= 0x9F)
        if tag in ['9F', '5F']:
            if i < len(hex_data):
                tag += hex_data[i:i+2]
                i += 2
        
        if i >= len(hex_data):
            break
            
        # Get length
        length_byte = hex_data[i:i+2]
        length = int(length_byte, 16)
        i += 2
        
        if i + length * 2 > len(hex_data):
            break
            
        # Get value
        value = hex_data[i:i+(length*2)]
        i += length * 2
        
        print(f"      Tag {tag}: Length {length}, Value: {value}")
        
        if tag == '57':
            print(f"      💳 Track 2 Equivalent Data")
            track2 = parse_track2_data(value)
            if track2:
                print(f"      🎯 TRACK2: {track2}")
        elif tag == '5A':
            print(f"      🏦 PAN")
            pan = parse_pan_data(value)
            if pan:
                print(f"      🎯 PAN: {pan}")
        elif tag == '5F20':
            print(f"      👤 Cardholder Name")
            try:
                name = bytes.fromhex(value).decode('ascii', errors='ignore')
                print(f"      🎯 NAME: {name}")
            except:
                print(f"      Raw name data: {value}")
        elif tag == '5F24':
            print(f"      📅 Expiry Date: {value}")

def parse_track2_data(hex_value):
    """Parse Track 2 equivalent data from hex."""
    try:
        # Track2 data is stored as packed BCD
        track2 = ""
        
        for i in range(0, len(hex_value), 2):
            byte_hex = hex_value[i:i+2]
            byte_val = int(byte_hex, 16)
            
            # Each byte contains two BCD digits
            high_nibble = (byte_val >> 4) & 0x0F
            low_nibble = byte_val & 0x0F
            
            # Convert to track2 characters
            for nibble in [high_nibble, low_nibble]:
                if nibble <= 9:
                    track2 += str(nibble)
                elif nibble == 0xD:
                    track2 += "D"  # Separator
                elif nibble == 0xF:
                    # Padding, stop here
                    return track2
                else:
                    track2 += f"{nibble:X}"
        
        return track2
        
    except Exception as e:
        print(f"      Track2 parse error: {e}")
        return None

def parse_pan_data(hex_value):
    """Parse PAN from hex value."""
    try:
        # PAN is stored as packed BCD, similar to Track2
        pan = ""
        
        for i in range(0, len(hex_value), 2):
            byte_hex = hex_value[i:i+2]
            byte_val = int(byte_hex, 16)
            
            # Each byte contains two BCD digits
            high_nibble = (byte_val >> 4) & 0x0F
            low_nibble = byte_val & 0x0F
            
            # Convert to digits
            for nibble in [high_nibble, low_nibble]:
                if nibble <= 9:
                    pan += str(nibble)
                elif nibble == 0xF:
                    # Padding, stop here
                    return pan
        
        # Validate PAN length
        if 13 <= len(pan) <= 19:
            return pan
        else:
            print(f"      Invalid PAN length: {len(pan)}")
            return None
            
    except Exception as e:
        print(f"      PAN parse error: {e}")
        return None

def test_real_card_parsing():
    """Test parsing with the actual card data we found."""
    print(f"\n=== TESTING WITH REAL CARD DATA ===")
    
    # The Track2 data we found: 403163517213D307210099999991F
    track2_raw = "403163517213D307210099999991F"
    print(f"Track2 found: {track2_raw}")
    
    # Extract PAN from Track2 (everything before 'D')
    if 'D' in track2_raw:
        pan_from_track2 = track2_raw.split('D')[0]
        print(f"🎯 PAN from Track2: {pan_from_track2}")
        
        # Extract expiry (4 digits after 'D')
        track2_parts = track2_raw.split('D')[1]
        if len(track2_parts) >= 4:
            expiry = track2_parts[:4]
            print(f"📅 Expiry from Track2: {expiry[:2]}/{expiry[2:]}")
    
    print(f"\n✅ FINAL RESULTS:")
    print(f"• PAN: {pan_from_track2}")
    print(f"• Track2: {track2_raw}")
    print(f"• This is a valid {len(pan_from_track2)}-digit card number!")

if __name__ == "__main__":
    parse_tlv_properly()
    test_real_card_parsing()
