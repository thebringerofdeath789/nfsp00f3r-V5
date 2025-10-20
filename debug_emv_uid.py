#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug EMV Card UID Assignment
Check if the UID is being properly assigned to the EMV card object.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def debug_emv_card_uid():
    """Debug EMV card UID assignment."""
    print("=== Debugging EMV Card UID Assignment ===")
    
    try:
        from card_manager import CardManager
        
        # Create card manager
        card_manager = CardManager()
        
        # Try to read card
        print("1. Reading card...")
        result = card_manager.read_card("ACS ACR122 0")
        
        if result and 'card_id' in result:
            card_id = result['card_id']
            
            # Get the EMV card object from card manager
            emv_card = card_manager.cards.get(card_id)
            
            if emv_card:
                print("2. EMV Card object found:")
                print(f"   - ATR: {emv_card.atr}")
                print(f"   - UID: {emv_card.uid}")
                print(f"   - PAN: {emv_card.pan}")
                print(f"   - Card Type: {emv_card._determine_card_type()}")
                
                print("3. UI Dictionary:")
                ui_dict = emv_card.to_ui_dict()
                print(f"   - atr: {ui_dict.get('atr')}")
                print(f"   - pan: {ui_dict.get('pan')}")
                print(f"   - card_type: {ui_dict.get('card_type')}")
                print(f"   - uid (direct): {ui_dict.get('uid', 'NOT FOUND')}")
                
                return True
            else:
                print("✗ No EMV card object found")
                return False
        else:
            print("✗ No card reading result")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_emv_card_uid()
