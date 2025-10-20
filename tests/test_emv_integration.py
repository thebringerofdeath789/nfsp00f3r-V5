#!/usr/bin/env python3
"""
Test EMV integration with direct record reading
"""
import logging
import sys
import os
from smartcard.System import readers as pcsc_readers
from smartcard.util import toHexString

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def parse_tlv(data):
    """Parse TLV data"""
    parsed = {}
    i = 0
    while i < len(data):
        # Get tag
        if i >= len(data):
            break
        
        tag_byte = data[i]
        tag = [tag_byte]
        i += 1
        
        # Multi-byte tag
        if (tag_byte & 0x1F) == 0x1F and i < len(data):
            tag.append(data[i])
            i += 1
        
        if i >= len(data):
            break
            
        # Get length
        length_byte = data[i]
        i += 1
        
        if length_byte & 0x80:
            # Multi-byte length
            num_octets = length_byte & 0x7F
            if num_octets == 0 or i + num_octets > len(data):
                break
            length = 0
            for j in range(num_octets):
                length = (length << 8) + data[i + j]
            i += num_octets
        else:
            length = length_byte
        
        # Get value
        if i + length > len(data):
            break
            
        value = data[i:i+length]
        i += length
        
        tag_str = ''.join(f'{b:02X}' for b in tag)
        parsed[tag_str] = value
        
    return parsed

def bcd_decode(data):
    """Decode BCD data"""
    result = ""
    for byte in data:
        high = (byte >> 4) & 0x0F
        low = byte & 0x0F
        if high <= 9:
            result += str(high)
        if low <= 9:
            result += str(low)
        elif low == 0x0F:  # Padding
            break
    return result

def test_direct_emv_reading():
    """Test direct EMV record reading"""
    
    print("Direct EMV Integration Test")
    print("=" * 40)
    
    try:
        # Get readers
        reader_list = pcsc_readers()
        if not reader_list:
            print("❌ No card readers found!")
            return False
            
        reader = reader_list[0]
        print(f"Using reader: {reader}")
        
        # Connect to card
        connection = reader.createConnection()
        connection.connect()
        print(f"Connected to card, ATR: {toHexString(connection.getATR())}")
        
        # Try to read EMV records directly
        emv_data = {}
        
        # Read various SFI records
        sfi_commands = [
            (0x01, 0x01, "SFI 1, Record 1 (Track2)"),
            (0x01, 0x02, "SFI 1, Record 2"),
            (0x01, 0x03, "SFI 1, Record 3"),
            (0x02, 0x01, "SFI 2, Record 1"),
            (0x02, 0x02, "SFI 2, Record 2"),
            (0x02, 0x03, "SFI 2, Record 3"),
            (0x02, 0x04, "SFI 2, Record 4"),
            (0x02, 0x05, "SFI 2, Record 5 (PAN)"),
        ]
        
        for sfi, record, description in sfi_commands:
            try:
                # READ RECORD command
                p2 = (sfi << 3) | 0x04  # SFI in bits 7-4, read mode in bits 3-1
                command = [0x00, 0xB2, record, p2, 0x00]
                
                response, sw1, sw2 = connection.transmit(command)
                
                if sw1 == 0x90 and sw2 == 0x00:
                    print(f"✓ {description}: {len(response)} bytes")
                    
                    # Parse TLV data
                    tlv_data = parse_tlv(response)
                    for tag, value in tlv_data.items():
                        print(f"  Tag {tag}: {toHexString(value)}")
                        
                        # Check for PAN (tag 5A)
                        if tag == '5A':
                            pan = bcd_decode(value)
                            print(f"  → PAN: {pan}")
                            emv_data['pan'] = pan
                            
                        # Check for Track2 (tag 57)
                        elif tag == '57':
                            track2_hex = toHexString(value, HEX_UPPER=False).replace(' ', '')
                            print(f"  → Track2 raw: {track2_hex}")
                            
                            # Parse Track2 format: PAN + D + expiry + service code + discretionary
                            if 'D' in track2_hex.upper():
                                track2_parts = track2_hex.upper().split('D')
                                if len(track2_parts) >= 2:
                                    pan_from_track2 = track2_parts[0]
                                    remaining = track2_parts[1]
                                    if len(remaining) >= 4:
                                        # Expiry is YYMM format
                                        expiry_yymm = remaining[:4]
                                        # Convert YYMM to MM/YY
                                        if len(expiry_yymm) == 4:
                                            yy = expiry_yymm[:2]
                                            mm = expiry_yymm[2:4]
                                            expiry_formatted = f"{mm}/{yy}"
                                            print(f"  → PAN from Track2: {pan_from_track2}")
                                            print(f"  → Expiry: {expiry_formatted}")
                                            emv_data['pan_track2'] = pan_from_track2
                                            emv_data['expiry'] = expiry_formatted
                            
                        # Check for Application Label (tag 50)
                        elif tag == '50':
                            try:
                                label = value.decode('utf-8', errors='ignore').strip()
                                print(f"  → App Label: {label}")
                                emv_data['app_label'] = label
                            except:
                                pass
                                
                else:
                    print(f"✗ {description}: {sw1:02X} {sw2:02X}")
                    
            except Exception as e:
                print(f"✗ {description}: Error - {e}")
        
        # Summary
        print("\nEMV Data Summary:")
        print("-" * 20)
        for key, value in emv_data.items():
            print(f"{key}: {value}")
            
        # Validate against expected values
        expected_pan = "4031630501721103"
        expected_expiry = "07/30"
        
        print(f"\nValidation:")
        print(f"Expected PAN: {expected_pan}")
        print(f"Expected Expiry: {expected_expiry}")
        
        if emv_data.get('pan') == expected_pan:
            print("✓ PAN matches expected value!")
        elif emv_data.get('pan_track2') == expected_pan:
            print("✓ PAN from Track2 matches expected value!")
        else:
            print(f"❌ PAN mismatch - got: {emv_data.get('pan', 'N/A')}, {emv_data.get('pan_track2', 'N/A')}")
            
        if emv_data.get('expiry') == expected_expiry:
            print("✓ Expiry matches expected value!")
        else:
            print(f"❌ Expiry mismatch - got: {emv_data.get('expiry', 'N/A')}")
            
        return len(emv_data) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_direct_emv_reading()
