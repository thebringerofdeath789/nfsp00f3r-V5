#!/usr/bin/env python3

"""
Simple test to debug card reading issues
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager

def test_simple_card_reading():
    """Test basic card reading functionality"""
    print("=== Testing Simple Card Reading ===")
    
    try:
        card_manager = CardManager()
        print("CardManager created successfully")
        
        # Import reader manager separately
        from readers import ReaderManager
        reader_manager = ReaderManager()
        
        # Test reader detection
        readers = reader_manager.detect_readers()
        print(f"Detected {len(readers)} readers: {readers}")
        
        if not readers:
            print("No readers found - cannot test card reading")
            return
        
        # Try to read a card
        print("Attempting to read card...")
        card_data = card_manager.read_card()
        
        if card_data:
            print(f"Card read successfully!")
            print(f"Card data keys: {list(card_data.keys())}")
            
            # Check what's actually in card_data
            if 'card_data' in card_data and card_data['card_data']:
                actual_data = card_data['card_data']
                print(f"Actual card data keys: {list(actual_data.keys())}")
                print(f"PAN: {'***' if actual_data.get('pan') else 'N/A'}")
                print(f"Card Type: {actual_data.get('card_type', 'N/A')}")
                print(f"TLV Tags: {len(actual_data.get('tlv_data', {}))}")
                print(f"APDU Log entries: {len(actual_data.get('apdu_log', []))}")
                print(f"All applications: {len(actual_data.get('all_applications', {}))}")
            else:
                print("No card_data found in result")
        else:
            print("Failed to read card")
            
    except Exception as e:
        print(f"Error during card reading test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_simple_card_reading()
