#!/usr/bin/env python3
"""
Debug TLV parsing issue
"""
from smartcard.System import readers as pcsc_readers
from smartcard.util import toHexString

def debug_tlv_parsing():
    """Debug TLV parsing for EMV records"""
    
    print("Debug TLV Parsing")
    print("=" * 30)
    
    try:
        # Get readers
        reader_list = pcsc_readers()
        if not reader_list:
            print("❌ No card readers found!")
            return
            
        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()
        
        # Select PPSE
        ppse_aid = bytes.fromhex("325041592E5359532E4444463031")  # "2PAY.SYS.DDF01"
        select_ppse = [0x00, 0xA4, 0x04, 0x00, len(ppse_aid)] + list(ppse_aid)
        
        response, sw1, sw2 = connection.transmit(select_ppse)
        if sw1 != 0x90 or sw2 != 0x00:
            print(f"❌ PPSE selection failed: {sw1:02X}{sw2:02X}")
            return
        
        # Select VISA application
        visa_aid = bytes.fromhex("A0000000031010")
        select_aid = [0x00, 0xA4, 0x04, 0x00, len(visa_aid)] + list(visa_aid)
        
        response, sw1, sw2 = connection.transmit(select_aid)
        if sw1 != 0x90 or sw2 != 0x00:
            print(f"❌ VISA AID selection failed: {sw1:02X}{sw2:02X}")
            return
        
        # Read and analyze SFI2.5 for PAN
        print("\n--- SFI2.5 Analysis ---")
        read_record = [0x00, 0xB2, 0x05, 0x14, 0x00]  # SFI2, record 5
        response, sw1, sw2 = connection.transmit(read_record)
        
        if sw1 == 0x90 and sw2 == 0x00:
            raw_hex = toHexString(response).replace(' ', '').upper()
            print(f"Raw data: {raw_hex}")
            print(f"Length: {len(response)} bytes")
            
            # Look for PAN tag (5A)
            if '5A' in raw_hex:
                pos = raw_hex.find('5A')
                print(f"Found 5A at position: {pos}")
                
                # Extract length and value
                if pos + 2 < len(raw_hex):
                    length_hex = raw_hex[pos+2:pos+4]
                    length = int(length_hex, 16)
                    print(f"Length: {length} bytes")
                    
                    value_start = pos + 4
                    value_end = value_start + (length * 2)
                    value_hex = raw_hex[value_start:value_end]
                    print(f"Value hex: {value_hex}")
                    
                    # BCD decode
                    value_bytes = bytes.fromhex(value_hex)
                    pan = ""
                    for byte in value_bytes:
                        high = (byte >> 4) & 0x0F
                        low = byte & 0x0F
                        if high <= 9:
                            pan += str(high)
                        if low <= 9:
                            pan += str(low)
                        elif low == 0x0F:  # Padding
                            break
                    print(f"🎉 Decoded PAN: {pan}")
                    
        # Read and analyze SFI1.1 for Track2
        print("\n--- SFI1.1 Analysis ---")
        read_record = [0x00, 0xB2, 0x01, 0x0C, 0x00]  # SFI1, record 1
        response, sw1, sw2 = connection.transmit(read_record)
        
        if sw1 == 0x90 and sw2 == 0x00:
            raw_hex = toHexString(response).replace(' ', '').upper()
            print(f"Raw data: {raw_hex}")
            print(f"Length: {len(response)} bytes")
            
            # Look for Track2 tag (57)
            if '57' in raw_hex:
                pos = raw_hex.find('57')
                print(f"Found 57 at position: {pos}")
                
                # Extract length and value
                if pos + 2 < len(raw_hex):
                    length_hex = raw_hex[pos+2:pos+4]
                    length = int(length_hex, 16)
                    print(f"Length: {length} bytes")
                    
                    value_start = pos + 4
                    value_end = value_start + (length * 2)
                    value_hex = raw_hex[value_start:value_end]
                    print(f"Value hex: {value_hex}")
                    
                    # Parse Track2 format: PAN + D + expiry + service code + discretionary
                    if 'D' in value_hex:
                        track2_parts = value_hex.split('D')
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
                                    print(f"🎉 PAN from Track2: {pan_from_track2}")
                                    print(f"🎉 Expiry: {expiry_formatted}")
                    
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tlv_parsing()
