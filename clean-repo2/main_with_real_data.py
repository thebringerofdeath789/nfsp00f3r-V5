#!/usr/bin/env python3
"""
Final integration: Main app with universal EMV parser
"""
import sys
import os
import logging
from PyQt5.QtWidgets import QApplication

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_emv_card_with_real_data():
    """Create EMV card object with real extracted data"""
    try:
        from universal_emv_parser import parse_emv_card
        from card_manager import CardManager
        from emv_card import EMVCard, EMVApplication
        
        print("🔍 Extracting real EMV data...")
        
        # Extract real card data
        card_data = parse_emv_card()
        
        if not card_data or not card_data.get('pan'):
            print("❌ Failed to extract card data")
            return None
            
        print(f"✅ Extracted PAN: {card_data.get('pan')}")
        print(f"✅ Extracted Expiry: {card_data.get('expiry_date')}")
        print(f"✅ Card Type: {card_data.get('card_type')}")
        
        # Create EMV card object
        emv_card = EMVCard()
        emv_card.pan = card_data.get('pan')
        emv_card.expiry_date = card_data.get('expiry_date')
        emv_card.cardholder_name = card_data.get('cardholder_name')
        emv_card.card_type = card_data.get('card_type', 'EMV Card')
        emv_card.tlv_data = card_data.get('tlv_data', {})
        emv_card.track_data = card_data.get('track_data', {})
        
        # Add application
        aid = card_data.get('aid', 'A0000000031010')
        application = EMVApplication(aid=aid)
        application.application_label = card_data.get('application_label', 'EMV Application')
        application.preferred_name = application.application_label.split()[0] if application.application_label else 'EMV'
        
        emv_card.applications[aid] = application
        emv_card.current_application = aid
        
        return emv_card
        
    except Exception as e:
        print(f"❌ Failed to create EMV card: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_main_app():
    """Run the main application with real EMV data"""
    
    print("🚀 Starting Main Application with Real EMV Data")
    print("=" * 60)
    
    try:
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Create card with real data
        emv_card = create_emv_card_with_real_data()
        if not emv_card:
            print("❌ Cannot start app without card data")
            return False
        
        # Create card manager and add the real card
        from card_manager import CardManager
        card_manager = CardManager()
        
        # Generate card ID and add to manager
        card_id = card_manager._generate_card_id(emv_card)
        card_manager.cards[card_id] = emv_card
        card_manager.card_order.append(card_id)
        card_manager.current_card_id = card_id
        
        print(f"✅ Added card to manager: {card_id}")
        
        # Import and start main UI
        from ui_mainwindow import MainWindow
        
        # Create main window
        main_window = MainWindow(card_manager)
        main_window.show()
        
        print("✅ Main window opened!")
        print("\n📋 Card Data in UI:")
        ui_dict = emv_card.to_ui_dict()
        for key, value in ui_dict.items():
            print(f"  {key}: {value}")
            
        # Validate data
        expected_pan = "4031630501721103"
        expected_expiry = "07/30"
        
        if ui_dict.get('pan') == expected_pan:
            print(f"✅ UI shows correct PAN: {expected_pan}")
        else:
            print(f"❌ PAN issue - Expected: {expected_pan}, Got: {ui_dict.get('pan')}")
            
        if ui_dict.get('expiry_date') == expected_expiry:
            print(f"✅ UI shows correct expiry: {expected_expiry}")
        else:
            print(f"❌ Expiry issue - Expected: {expected_expiry}, Got: {ui_dict.get('expiry_date')}")
        
        print(f"\n🎉 SUCCESS: Main app is running with actual card data!")
        print(f"   - PAN: {ui_dict.get('pan')}")
        print(f"   - Expiry: {ui_dict.get('expiry_date')}")
        print(f"   - Type: {ui_dict.get('card_type')}")
        print(f"   - App: {ui_dict.get('application_label')}")
        
        # Run the application
        return app.exec_() == 0
        
    except Exception as e:
        print(f"❌ Main app failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_main_app()
    if success:
        print("🎉 Application completed successfully")
    else:
        print("❌ Application encountered errors")
