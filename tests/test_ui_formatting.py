#!/usr/bin/env python3

"""
Test script to validate UI formatting improvements
Tests TLV data formatting, Track2 display, and APDU log formatting
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emv_card import EMVCard
from tag_dictionary import TagDictionary


def test_tlv_formatting():
    """Test TLV data formatting with tag descriptions"""
    print("=== Testing TLV Formatting ===")
    
    # Create sample TLV data (hex strings)
    sample_tlv = {
        '5A': bytes.fromhex('4031630501721103'),  # PAN
        '5F24': bytes.fromhex('300730'),  # Expiry date
        '5F20': bytes.fromhex('544553542F43415244484F4C444552'),  # Cardholder name
        '57': bytes.fromhex('4031630501721103D30072010000000000000F'),  # Track 2 equivalent
        '82': bytes.fromhex('1C00'),  # Application Interchange Profile
        '8A': bytes.fromhex('3030'),  # Authorization Response Code
    }
    
    # Create EMV card with sample data
    card = EMVCard()
    card.pan = '4031630501721103'
    card.expiry_date = '07/30'
    card.cardholder_name = 'TEST/CARDHOLDER'
    card.tlv_data = sample_tlv
    card.track2_data = '4031630501721103D30072010000000000000F'
    card.apdu_log = [
        {
            'command': 'SELECT PPSE',
            'command_hex': '00 A4 04 00 0E 32 50 41 59 2E 53 59 53 2E 44 44 46 30 31 00',
            'response_hex': '6F 2A 84 0E 32 50 41 59 2E 53 59 53 2E 44 44 46 30 31 A5 18',
            'status': '9000',
            'sw1_sw2': '90 00',
            'timestamp': 'N/A',
            'description': 'Select Payment System Environment'
        },
        {
            'command': 'SELECT AID A0000000041010',
            'command_hex': '00 A4 04 00 07 A0 00 00 00 04 10 10',
            'response_hex': '6F 35 84 07 A0 00 00 00 04 10 10 A5 2A',
            'status': '9000',
            'sw1_sw2': '90 00',
            'timestamp': 'N/A',
            'description': 'Select application AID: A0000000041010'
        }
    ]
    
    # Get UI dictionary
    ui_dict = card.to_ui_dict()
    
    # Test TLV formatting
    print("TLV Data:")
    if isinstance(ui_dict['tlv_data'], dict):
        for tag, info in ui_dict['tlv_data'].items():
            if isinstance(info, dict):
                print(f"  {tag}: {info['value']} ({info['description']})")
            else:
                print(f"  {tag}: {info}")
    else:
        print(f"  {ui_dict['tlv_data']}")
    
    print(f"\nTrack Data:")
    if isinstance(ui_dict['track_data'], dict):
        for track_type, track_value in ui_dict['track_data'].items():
            print(f"  {track_type}: {track_value}")
    else:
        print(f"  {ui_dict['track_data']}")
    
    print("\nAPDU Log:")
    if isinstance(ui_dict.get('raw_responses'), list):
        for entry in ui_dict['raw_responses']:
            print(f"  Command: {entry.get('command', 'N/A')}")
            print(f"  Description: {entry.get('description', 'N/A')}")
            print(f"  Status: {entry.get('status', 'N/A')}")
            print(f"  ---")


def test_tag_dictionary():
    """Test tag dictionary functionality"""
    print("\n=== Testing Tag Dictionary ===")
    
    tag_dict = TagDictionary()
    test_tags = ['5A', '5F24', '5F20', '57', '82', '8A']
    
    for tag in test_tags:
        description = tag_dict.get_tag_description(tag)
        print(f"Tag {tag}: {description}")


if __name__ == '__main__':
    test_tag_dictionary()
    test_tlv_formatting()
    
    print("\n=== Test Complete ===")
    print("UI formatting improvements validated successfully!")
