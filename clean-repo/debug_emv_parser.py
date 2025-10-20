#!/usr/bin/env python3

"""
Debug the universal EMV parser to see why it's not extracting data from multiple AIDs
"""

import sys
import os
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_emv_parser import UniversalEMVParser

def debug_emv_parsing():
    """Debug EMV parsing to see why multiple AIDs aren't being extracted"""
    print("=== Debugging EMV Parser ===")
    
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    try:
        parser = UniversalEMVParser()
        print(f"Parser created with {len(parser.US_CARD_AIDS)} known AIDs")
        
        # Test parsing
        print("Starting card parsing...")
        card_data = parser.parse_card()
        
        if card_data:
            print(f"\n=== PARSING RESULTS ===")
            print(f"Main card data keys: {list(card_data.keys())}")
            print(f"PAN: {'***' if card_data.get('pan') else 'N/A'}")
            print(f"Card Type: {card_data.get('card_type', 'N/A')}")
            print(f"TLV Tags: {len(card_data.get('tlv_data', {}))}")
            print(f"APDU Log entries: {len(card_data.get('apdu_log', []))}")
            print(f"All applications: {len(card_data.get('all_applications', {}))}")
            
            if card_data.get('all_applications'):
                print(f"\n=== ALL APPLICATIONS ===")
                for aid, app_data in card_data['all_applications'].items():
                    print(f"AID {aid}:")
                    print(f"  - PAN: {'***' if app_data.get('pan') else 'N/A'}")
                    print(f"  - Label: {app_data.get('application_label', 'N/A')}")
                    print(f"  - TLV Tags: {len(app_data.get('tlv_data', {}))}")
                    print(f"  - Cryptogram: {app_data.get('application_cryptogram', 'N/A')}")
            
            if card_data.get('apdu_log'):
                print(f"\n=== FIRST 5 APDU ENTRIES ===")
                for i, entry in enumerate(card_data['apdu_log'][:5]):
                    print(f"{i+1}. {entry.get('command', 'Unknown')} -> {entry.get('status', 'N/A')}")
        else:
            print("Parser returned None - check logs above for errors")
            
    except Exception as e:
        print(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_emv_parsing()
