#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Actual Card Data Display
Tests that the UI shows actual card data instead of mock data.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_actual_card_data():
    """Test that actual card data is returned, not mock data."""
    print("=== Testing Actual Card Data Retrieval ===")
    
    try:
        from card_manager import CardManager
        
        # Create card manager
        card_manager = CardManager()
        
        # Try to read card
        print("1. Attempting to read actual card...")
        result = card_manager.read_card("ACS ACR122 0")
        
        if result and 'card_data' in result:
            card_data = result['card_data']
            
            print(f"✓ Card reading successful!")
            print(f"  - ATR: {card_data.get('atr', 'N/A')}")
            print(f"  - Card Type: {card_data.get('card_type', 'N/A')}")
            print(f"  - PAN/UID: {card_data.get('pan', 'N/A')}")
            print(f"  - Read Time: {card_data.get('timestamp', 'N/A')}")
            
            # Check if this is mock data
            atr = card_data.get('atr', '')
            pan = card_data.get('pan', '')
            
            # Mock data indicators
            is_mock = False
            if atr == '3B8F8001804F0CA000000306030001000000006A':
                is_mock = True
                print("⚠️  This appears to be mock ATR data")
            
            if pan in ['5555444433332222', '4111111111111111']:
                is_mock = True
                print("⚠️  This appears to be mock PAN data")
            
            if not is_mock:
                print("✓ Data appears to be actual card data (not mock)")
                
                # Expected ATR from our tests
                if atr == '3B888001534C4A26312342113B':
                    print("✓ ATR matches expected value from reader tests")
                
                if card_data.get('card_type') == 'NFC/Contactless':
                    print("✓ Card type correctly identified as NFC/Contactless")
                
                return True
            else:
                print("✗ Mock data is still being returned")
                return False
                
        else:
            print("✗ No card data returned")
            print("  - Make sure card is on reader")
            print("  - Check reader connection")
            return False
            
    except Exception as e:
        print(f"✗ Error testing card data: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test actual vs mock card data."""
    print("Testing Actual Card Data Display")
    print("=" * 40)
    
    success = test_actual_card_data()
    
    print("\n" + "="*40)
    if success:
        print("✓ Actual card data is being used!")
        print("The UI should now show your real card's ATR and UID")
    else:
        print("✗ Mock data issue persists")
        print("Check the debug output above for details")

if __name__ == "__main__":
    main()
