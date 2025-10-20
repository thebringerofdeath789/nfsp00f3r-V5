#!/usr/bin/env python3

"""
Debug the CardManager to see what comprehensive data is actually being stored
"""

import sys
import os
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager

def debug_card_manager_comprehensive_data():
    """Debug what comprehensive data the CardManager is actually storing"""
    print("=== Debugging CardManager Comprehensive Data ===")
    
    # Enable debug logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        card_manager = CardManager()
        
        # Monkey patch the CardManager to add debug output
        original_read_emv = card_manager._read_emv_applications
        
        def debug_read_emv(reader_instance, emv_card):
            print("\n--- _read_emv_applications called ---")
            result = original_read_emv(reader_instance, emv_card)
            print(f"_read_emv_applications returned: {result}")
            
            # Check what's actually in the emv_card after processing
            print(f"\nEMVCard attributes after processing:")
            print(f"- pan: {'***' if emv_card.pan else 'None'}")
            print(f"- expiry_date: {emv_card.expiry_date}")
            print(f"- tlv_data: {len(emv_card.tlv_data) if emv_card.tlv_data else 0} tags")
            print(f"- apdu_log: {len(emv_card.apdu_log) if hasattr(emv_card, 'apdu_log') and emv_card.apdu_log else 0} entries")
            print(f"- all_applications: {len(getattr(emv_card, 'all_applications', {})) if hasattr(emv_card, 'all_applications') else 0} apps")
            print(f"- applications: {len(emv_card.applications)} standard apps")
            
            if hasattr(emv_card, 'all_applications') and emv_card.all_applications:
                print(f"\nAll applications data:")
                for aid, app_data in emv_card.all_applications.items():
                    print(f"  {aid}: {list(app_data.keys())}")
                    
            return result
            
        card_manager._read_emv_applications = debug_read_emv
        
        # Test card reading
        print("Reading card with debug CardManager...")
        result = card_manager.read_card()
        
        if result and result.get('card_data'):
            card_data = result['card_data']
            print(f"\n=== FINAL CARD DATA RESULT ===")
            print(f"Keys: {list(card_data.keys())}")
            print(f"All applications: {len(card_data.get('all_applications', {}))}")
            if card_data.get('all_applications'):
                print(f"All applications content:")
                for aid, app_info in card_data['all_applications'].items():
                    print(f"  {aid}: {list(app_info.keys()) if isinstance(app_info, dict) else type(app_info)}")
            print(f"APDU log: {len(card_data.get('raw_responses', []))}")
            print(f"Comprehensive crypto: {list(card_data.get('comprehensive_crypto', {}).keys())}")
        else:
            print("No result from CardManager")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_card_manager_comprehensive_data()
