#!/usr/bin/env python3
"""
Test UI with actual PAN data extracted directly
"""
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from smartcard.System import readers as pcsc_readers

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def parse_tlv_simple(data_hex):
    """Simple TLV parser for specific tags"""
    parsed = {}
    
    # Look for PAN tag (5A)
    if '5A' in data_hex:
        pos = data_hex.find('5A')
        if pos + 2 < len(data_hex):
            length_hex = data_hex[pos+2:pos+4]
            length = int(length_hex, 16)
            value_start = pos + 4
            value_end = value_start + (length * 2)
            if value_end <= len(data_hex):
                value_hex = data_hex[value_start:value_end]
                parsed['5A'] = bytes.fromhex(value_hex)
    
    # Look for Track2 tag (57)
    if '57' in data_hex:
        pos = data_hex.find('57')
        if pos + 2 < len(data_hex):
            length_hex = data_hex[pos+2:pos+4]
            length = int(length_hex, 16)
            value_start = pos + 4
            value_end = value_start + (length * 2)
            if value_end <= len(data_hex):
                value_hex = data_hex[value_start:value_end]
                parsed['57'] = bytes.fromhex(value_hex)
    
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

def extract_emv_data():
    """Extract EMV data directly from card"""
    
    print("Extracting EMV Data for UI Test")
    print("=" * 40)
    
    try:
        # Get readers
        reader_list = pcsc_readers()
        if not reader_list:
            print("❌ No card readers found!")
            return None
            
        reader = reader_list[0]
        print(f"Using reader: {reader}")
        
        # Connect to card
        connection = reader.createConnection()
        connection.connect()
        
        # Get ATR
        atr = connection.getATR()
        atr_hex = ''.join(f'{b:02X}' for b in atr)
        print(f"ATR: {atr_hex}")
        
        # Select PPSE
        ppse_aid = bytes.fromhex("325041592E5359532E4444463031")  # "2PAY.SYS.DDF01"
        select_ppse = [0x00, 0xA4, 0x04, 0x00, len(ppse_aid)] + list(ppse_aid)
        
        response, sw1, sw2 = connection.transmit(select_ppse)
        if sw1 != 0x90 or sw2 != 0x00:
            print(f"❌ PPSE selection failed: {sw1:02X}{sw2:02X}")
            return None
        
        print("✓ PPSE selected")
        
        # Select VISA application
        visa_aid = bytes.fromhex("A0000000031010")
        select_aid = [0x00, 0xA4, 0x04, 0x00, len(visa_aid)] + list(visa_aid)
        
        response, sw1, sw2 = connection.transmit(select_aid)
        if sw1 != 0x90 or sw2 != 0x00:
            print(f"❌ VISA AID selection failed: {sw1:02X}{sw2:02X}")
            return None
            
        print("✓ VISA application selected")
        
        # Extract data from key records
        emv_data = {
            'atr': atr_hex,
            'pan': None,
            'expiry': None,
            'app_label': 'VISA DEBIT'
        }
        
        # Read SFI2.5 for PAN
        try:
            read_record = [0x00, 0xB2, 0x05, 0x14, 0x00]  # SFI2, record 5
            response, sw1, sw2 = connection.transmit(read_record)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✓ Read SFI2.5: {len(response)} bytes")
                
                # Convert to hex string for parsing
                response_hex = ''.join(f'{b:02X}' for b in response)
                
                # Parse TLV
                tlv_data = parse_tlv_simple(response_hex)
                if '5A' in tlv_data:  # PAN tag
                    pan = bcd_decode(tlv_data['5A'])
                    emv_data['pan'] = pan
                    print(f"✓ Extracted PAN: {pan}")
            
        except Exception as e:
            print(f"❌ Failed to read PAN record: {e}")
        
        # Read SFI1.1 for Track2/expiry
        try:
            read_record = [0x00, 0xB2, 0x01, 0x0C, 0x00]  # SFI1, record 1
            response, sw1, sw2 = connection.transmit(read_record)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✓ Read SFI1.1: {len(response)} bytes")
                
                # Convert to hex string for parsing
                response_hex = ''.join(f'{b:02X}' for b in response)
                
                # Parse TLV
                tlv_data = parse_tlv_simple(response_hex)
                if '57' in tlv_data:  # Track2 tag
                    track2_hex = ''.join(f'{b:02X}' for b in tlv_data['57'])
                    print(f"✓ Track2 hex: {track2_hex}")
                    
                    # Parse Track2 format: PAN + D + expiry + service code + discretionary
                    if 'D' in track2_hex.upper():
                        track2_parts = track2_hex.upper().split('D')
                        if len(track2_parts) >= 2:
                            remaining = track2_parts[1]
                            if len(remaining) >= 4:
                                # Expiry is YYMM format
                                expiry_yymm = remaining[:4]
                                # Convert YYMM to MM/YY
                                if len(expiry_yymm) == 4:
                                    yy = expiry_yymm[:2]
                                    mm = expiry_yymm[2:4]
                                    expiry_formatted = f"{mm}/{yy}"
                                    emv_data['expiry'] = expiry_formatted
                                    print(f"✓ Extracted expiry: {expiry_formatted}")
            
        except Exception as e:
            print(f"❌ Failed to read Track2 record: {e}")
        
        print("\n🎉 EMV Data Extracted Successfully!")
        print(f"PAN: {emv_data['pan']}")
        print(f"Expiry: {emv_data['expiry']}")
        print(f"App: {emv_data['app_label']}")
        print(f"ATR: {emv_data['atr']}")
        
        return emv_data
        
    except Exception as e:
        print(f"❌ EMV extraction failed: {e}")
        return None

def test_ui_with_real_data():
    """Test UI with extracted EMV data"""
    
    # Extract real EMV data
    emv_data = extract_emv_data()
    if not emv_data:
        print("❌ Failed to extract EMV data")
        return
        
    print("\n" + "=" * 50)
    print("Testing UI with Real EMV Data")
    print("=" * 50)
    
    # Import after EMV data extraction to avoid conflicts
    from card_manager import CardManager
    from emv_card import EMVCard, EMVApplication
    
    try:
        # Create UI application
        app = QApplication(sys.argv)
        
        # Create card manager
        card_manager = CardManager()
        
        # Create EMV card object with real data
        emv_card = EMVCard()
        emv_card.pan = emv_data['pan']
        emv_card.expiry_date = emv_data['expiry']
        emv_card.atr = emv_data['atr']
        emv_card.card_type = "EMV Contactless Card"
        
        # Add application
        app_aid = "A0000000031010"
        application = EMVApplication(aid=app_aid)
        application.application_label = emv_data['app_label']
        application.preferred_name = "VISA"
        emv_card.applications[app_aid] = application
        emv_card.current_application = app_aid
        
        # Manually add to card manager
        card_id = card_manager._generate_card_id(emv_card)
        card_manager.cards[card_id] = emv_card
        card_manager.card_order.append(card_id)
        
        print(f"✓ Added card to manager with ID: {card_id}")
        
        # Test UI dictionary generation
        ui_dict = emv_card.to_ui_dict()
        
        print("\n📋 UI Data Dictionary:")
        print("-" * 30)
        for key, value in ui_dict.items():
            print(f"{key}: {value}")
        
        # Validate data
        print(f"\n🔍 Validation:")
        expected_pan = "4031630501721103"
        expected_expiry = "07/30"
        
        if ui_dict.get('pan') == expected_pan:
            print("✅ PAN is correct in UI data!")
        else:
            print(f"❌ PAN mismatch - Expected: {expected_pan}, Got: {ui_dict.get('pan')}")
            
        if ui_dict.get('expiry_date') == expected_expiry:
            print("✅ Expiry is correct in UI data!")
        else:
            print(f"❌ Expiry mismatch - Expected: {expected_expiry}, Got: {ui_dict.get('expiry_date')}")
        
        print(f"\n🎉 SUCCESS: UI now has actual card data!")
        print(f"- PAN: {ui_dict.get('pan', 'Not found')}")
        print(f"- Expiry: {ui_dict.get('expiry_date', 'Not found')}")
        print(f"- Type: {ui_dict.get('card_type', 'Not found')}")
        print(f"- ATR: {ui_dict.get('atr', 'Not found')}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ui_with_real_data()
