#!/usr/bin/env python3
"""
Debug main.py integration to understand why card data isn't showing
"""
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication

# Setup logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_main_integration():
    """Debug the main.py integration step by step"""
    
    print("🔍 Debugging Main.py Integration")
    print("=" * 50)
    
    try:
        # Step 1: Test card manager initialization
        print("1. Testing CardManager initialization...")
        from card_manager import CardManager
        card_manager = CardManager()
        print(f"✅ CardManager created: {card_manager}")
        
        # Step 2: Test card reading directly
        print("\n2. Testing direct card reading...")
        card_data = card_manager.read_card()
        print(f"Card data result: {card_data}")
        
        if card_data:
            print("✅ Card data was returned!")
            for key, value in card_data.items():
                print(f"  {key}: {value}")
        else:
            print("❌ No card data returned")
            
        # Step 3: Check cards in manager
        print("\n3. Checking cards in manager...")
        all_cards = card_manager.get_all_cards()
        print(f"Cards in manager: {len(all_cards)}")
        
        if all_cards:
            for card_id, card in all_cards.items():
                print(f"Card ID: {card_id}")
                print(f"  PAN: {card.pan}")
                print(f"  Expiry: {card.expiry_date}")
                print(f"  Type: {card.card_type}")
                print(f"  Applications: {len(card.applications)}")
                print(f"  TLV Data: {len(card.tlv_data)}")
                
                # Test UI dict
                ui_dict = card.to_ui_dict()
                print(f"  UI PAN: {ui_dict.get('pan')}")
                print(f"  UI Expiry: {ui_dict.get('expiry_date')}")
        
        # Step 4: Test auto-load functionality
        print("\n4. Testing auto-load functionality...")
        if hasattr(card_manager, 'auto_load_card_data'):
            result = card_manager.auto_load_card_data()
            print(f"Auto-load result: {result}")
        else:
            print("❌ auto_load_card_data method not found")
            
        # Step 5: Test universal parser directly
        print("\n5. Testing universal parser directly...")
        from universal_emv_parser import parse_emv_card
        direct_card_data = parse_emv_card()
        
        if direct_card_data:
            print("✅ Universal parser works!")
            print(f"  Direct PAN: {direct_card_data.get('pan')}")
            print(f"  Direct Expiry: {direct_card_data.get('expiry_date')}")
            print(f"  Direct App: {direct_card_data.get('application_label')}")
        else:
            print("❌ Universal parser failed")
            
        # Step 6: Manual integration test
        print("\n6. Testing manual integration...")
        if direct_card_data and direct_card_data.get('pan'):
            from emv_card import EMVCard, EMVApplication
            
            # Create manual EMV card
            manual_card = EMVCard()
            manual_card.pan = direct_card_data.get('pan')
            manual_card.expiry_date = direct_card_data.get('expiry_date')
            manual_card.cardholder_name = direct_card_data.get('cardholder_name')
            manual_card.card_type = direct_card_data.get('card_type', 'EMV Card')
            manual_card.tlv_data = direct_card_data.get('tlv_data', {})
            
            # Add application
            aid = direct_card_data.get('aid', 'A0000000031010')
            app = EMVApplication(aid=aid)
            app.application_label = direct_card_data.get('application_label', 'EMV Application')
            manual_card.applications[aid] = app
            manual_card.current_application = aid
            
            # Test UI dict
            manual_ui = manual_card.to_ui_dict()
            print(f"✅ Manual integration PAN: {manual_ui.get('pan')}")
            print(f"✅ Manual integration Expiry: {manual_ui.get('expiry_date')}")
            
            # Add to card manager
            card_id = card_manager._generate_card_id(manual_card)
            card_manager.cards[card_id] = manual_card
            card_manager.card_order.append(card_id)
            card_manager.current_card_id = card_id
            
            print(f"✅ Added manual card to manager: {card_id}")
            
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_main_integration()
