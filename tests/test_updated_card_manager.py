#!/usr/bin/env python3
"""
Test the updated card manager with universal EMV parser
"""
import sys
import os
import logging
from card_manager import CardManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_updated_card_manager():
    """Test card manager with universal EMV parser"""
    
    print("Testing Updated Card Manager")
    print("=" * 40)
    
    try:
        # Create card manager
        card_manager = CardManager()
        
        # Read card from default reader
        print("Reading card from available reader...")
        
        card_data = card_manager.read_card()
        
        if card_data:
            print(f"✓ Card reading successful!")
            
            print(f"\n📋 Card Data:")
            print("-" * 20)
            for key, value in card_data.items():
                print(f"{key}: {value}")
            
            # Get the actual card object
            cards = card_manager.get_all_cards()
            if cards:
                card_id = list(cards.keys())[0]
                card = cards[card_id]
                ui_dict = card.to_ui_dict()
                
                print(f"\n📋 UI Dictionary:")
                print("-" * 20)
                for key, value in ui_dict.items():
                    print(f"{key}: {value}")
                
                # Validate actual data
                if ui_dict.get('pan') and ui_dict.get('pan') not in ['Protected (EMV Security)', 'N/A']:
                    print(f"✅ PAN extracted: {ui_dict.get('pan')}")
                else:
                    print(f"❌ No PAN extracted: {ui_dict.get('pan')}")
                
                if ui_dict.get('expiry_date') and ui_dict.get('expiry_date') != 'N/A':
                    print(f"✅ Expiry extracted: {ui_dict.get('expiry_date')}")
                else:
                    print(f"❌ No expiry extracted: {ui_dict.get('expiry_date')}")
                    
                # Expected values validation
                expected_pan = "4031630501721103"
                expected_expiry = "07/30"
                
                print(f"\n🔍 Validation:")
                if ui_dict.get('pan') == expected_pan:
                    print(f"✅ PAN matches expected: {expected_pan}")
                else:
                    print(f"❌ PAN mismatch - Expected: {expected_pan}, Got: {ui_dict.get('pan')}")
                    
                if ui_dict.get('expiry_date') == expected_expiry:
                    print(f"✅ Expiry matches expected: {expected_expiry}")
                else:
                    print(f"❌ Expiry mismatch - Expected: {expected_expiry}, Got: {ui_dict.get('expiry_date')}")
                    
        else:
            print("❌ No card data returned")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_updated_card_manager()
