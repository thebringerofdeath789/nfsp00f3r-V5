#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Card ATR Test
Simple test to verify ATR reading is working.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def simple_atr_test():
    """Simple test focusing only on ATR reading."""
    print("=== Simple ATR Test ===")
    
    try:
        from readers import PCSCCardReader
        
        # Create reader directly
        reader = PCSCCardReader("ACS ACR122 0")
        
        print("1. Connecting to reader...")
        if not reader.connect():
            print("✗ Failed to connect to reader")
            return False
        print("✓ Reader connected")
        
        print("2. Checking card presence...")
        card_present = reader.is_card_present()
        print(f"✓ Card present: {card_present}")
        
        if not card_present:
            print("Place a card and run again")
            return True
        
        print("3. Connecting to card...")
        if not reader.connect_to_card():
            print("✗ Failed to connect to card")
            return False
        print("✓ Card connection established")
        
        print("4. Reading ATR...")
        atr = reader.get_atr()
        
        if atr:
            print(f"✓ ATR: {atr.hex().upper()}")
            return True
        else:
            print("✗ No ATR received")
            return False
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run simple ATR test."""
    print("Simple Card ATR Test")
    print("=" * 30)
    
    success = simple_atr_test()
    
    print("\n" + "="*30)
    if success:
        print("✓ ATR test passed!")
    else:
        print("✗ ATR test failed!")

if __name__ == "__main__":
    main()
