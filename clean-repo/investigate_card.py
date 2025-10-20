#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Card Data Structure
Check what data is actually available on the card and try to find the real PAN.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def investigate_card_data():
    """Investigate what data is actually available on the card."""
    print("=== Investigating Card Data Structure ===")
    
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString, toBytes
        
        # Get PC/SC readers
        reader_list = readers()
        
        if not reader_list:
            print("✗ No PC/SC readers found")
            return False
            
        reader = reader_list[0]
        print(f"Using reader: {reader}")
        
        # Create connection
        connection = reader.createConnection()
        connection.connect()
        
        print("✓ Connected to card")
        
        # Get ATR
        atr_bytes = connection.getATR()
        atr = toHexString(atr_bytes).replace(' ', '')
        print(f"✓ ATR: {atr}")
        
        # Try various commands to get card data
        commands_to_try = [
            # Get UID
            ([0xFF, 0xCA, 0x00, 0x00, 0x00], "Get UID"),
            
            # Try to select Master File
            ([0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00], "Select MF"),
            
            # Try to read binary
            ([0x00, 0xB0, 0x00, 0x00, 0x00], "Read Binary"),
            
            # Try PSE (Payment System Environment)
            ([0x00, 0xA4, 0x04, 0x00, 0x0E] + toBytes("315041592E5359532E4444463031"), "Select PSE"),
            
            # Try PPSE (Proximity Payment System Environment)
            ([0x00, 0xA4, 0x04, 0x00, 0x0E] + toBytes("325041592E5359532E4444463031"), "Select PPSE"),
            
            # Get card data
            ([0x80, 0xCA, 0x9F, 0x17, 0x00], "Get PIN Try Counter"),
            ([0x80, 0xCA, 0x9F, 0x36, 0x00], "Get ATC"),
            ([0x80, 0xCA, 0x9F, 0x13, 0x00], "Get Last Online ATC"),
            
            # Try to get processing options
            ([0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00], "Get Processing Options"),
        ]
        
        successful_commands = []
        
        for cmd, description in commands_to_try:
            try:
                print(f"\nTrying: {description}")
                print(f"Command: {toHexString(cmd)}")
                
                response, sw1, sw2 = connection.transmit(cmd)
                
                print(f"Response: {toHexString(response) if response else 'None'}")
                print(f"Status: {sw1:02X}{sw2:02X}")
                
                if sw1 == 0x90 and sw2 == 0x00:
                    print("✓ SUCCESS!")
                    successful_commands.append((description, response))
                    
                    # Try to parse response for PAN-like data
                    if response and len(response) >= 8:
                        hex_response = toHexString(response).replace(' ', '')
                        print(f"Hex data: {hex_response}")
                        
                        # Look for patterns that might be PAN
                        if len(hex_response) >= 16:
                            # Check for potential PAN patterns (starting with common card prefixes)
                            common_prefixes = ['4', '5', '3', '6']  # Visa, MasterCard, Amex, Discover
                            for i in range(0, len(hex_response) - 15, 2):
                                potential_pan = hex_response[i:i+16]
                                if potential_pan[0] in common_prefixes:
                                    print(f"Potential PAN found: {potential_pan}")
                elif sw1 == 0x61:
                    print(f"✓ More data available (0x61{sw2:02X})")
                    # Try to get more data
                    try:
                        get_response = [0x00, 0xC0, 0x00, 0x00, sw2]
                        more_response, more_sw1, more_sw2 = connection.transmit(get_response)
                        if more_sw1 == 0x90 and more_sw2 == 0x00:
                            print(f"Additional data: {toHexString(more_response)}")
                            successful_commands.append((f"{description} (continued)", more_response))
                    except:
                        pass
                else:
                    print(f"✗ Failed: {sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print(f"\n=== Summary ===")
        print(f"Successful commands: {len(successful_commands)}")
        for desc, data in successful_commands:
            print(f"  - {desc}: {len(data) if data else 0} bytes")
        
        connection.disconnect()
        return successful_commands
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    investigate_card_data()
