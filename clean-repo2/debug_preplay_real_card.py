#!/usr/bin/env python3
"""
Pre-play Mode Real Card Debugging Script
===========================================

This script tests pre-play functionality by reading ACTUAL cards from a physical reader.
NO MOCK DATA is used - everything is read directly from the card.

Usage:
    python debug_preplay_real_card.py

Requirements:
    - Physical card reader (ACR122U or similar)
    - Real EMV card placed on the reader
    - All required dependencies installed
"""

import sys
import os
import logging
from datetime import datetime

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager
from attack_manager import AttackManager
from readers import ReaderManager

def setup_logging():
    """Setup detailed logging for debugging."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'debug_preplay_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def test_real_card_preplay():
    """Test pre-play mode with actual card reading."""
    logger = setup_logging()
    
    print("=" * 70)
    print("NFSP00F3R V5.0 - Pre-Play Mode Real Card Debug")
    print("=" * 70)
    print("⚠️  IMPORTANT: This script reads from ACTUAL card readers")
    print("   - Place a real EMV card on the reader")
    print("   - No mock data will be used")
    print("   - All data comes directly from the physical card")
    print("=" * 70)
    
    try:
        # Initialize components
        print("\n1. Initializing card manager and attack manager...")
        card_manager = CardManager()
        attack_manager = AttackManager()
        reader_manager = ReaderManager()
        
        # Enable preplay mode
        print("2. Enabling pre-play mode...")
        card_manager.enable_preplay_mode()
        card_manager.attack_manager = attack_manager
        
        print(f"   ✓ Pre-play mode enabled: {card_manager.preplay_mode_enabled}")
        
        # Detect readers
        print("\n3. Detecting card readers...")
        readers = reader_manager.get_available_readers()
        
        if not readers:
            print("   ❌ No card readers detected!")
            print("   Please connect a card reader (ACR122U recommended)")
            return False
        
        print(f"   ✓ Found {len(readers)} reader(s):")
        for i, reader in enumerate(readers):
            print(f"     [{i}] {reader}")
        
        # Use first available reader
        selected_reader = readers[0]
        print(f"\n4. Connecting to reader: {selected_reader}")
        
        reader_instance = reader_manager.connect_reader(selected_reader)
        if not reader_instance:
            print("   ❌ Failed to connect to reader!")
            return False
        
        print("   ✓ Reader connected successfully")
        
        # Wait for card
        print("\n5. Waiting for card...")
        print("   Please place an EMV card on the reader...")
        
        # Attempt to read card multiple times
        max_attempts = 10
        card_detected = False
        
        for attempt in range(max_attempts):
            try:
                print(f"   Attempt {attempt + 1}/{max_attempts}: Checking for card...")
                
                # Try to connect to card
                connection = reader_instance.connection
                if connection:
                    # Try to get ATR
                    atr = connection.getATR()
                    if atr:
                        print(f"   ✓ Card detected! ATR: {atr}")
                        card_detected = True
                        break
                
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed: {e}")
                continue
        
        if not card_detected:
            print("   ❌ No card detected after multiple attempts")
            print("   Please ensure:")
            print("     - EMV card is placed properly on the reader")
            print("     - Card is not damaged or expired") 
            print("     - Reader is functioning correctly")
            return False
        
        # Read actual card data
        print("\n6. Reading actual card data (NO MOCK DATA)...")
        
        try:
            # Read EMV data directly from the card
            card_data = card_manager.read_emv_card(reader_instance)
            
            if not card_data:
                print("   ❌ Failed to read EMV data from card")
                return False
            
            print("   ✓ Successfully read card data!")
            print(f"   Applications found: {len(card_data.get('all_applications', {}))}")
            
            # Display actual card information
            print("\n7. Actual Card Information:")
            print("   " + "=" * 50)
            
            if 'atr' in card_data:
                print(f"   ATR: {card_data['atr']}")
            
            if 'pan' in card_data and card_data['pan']:
                # Mask PAN for security
                pan = card_data['pan']
                masked_pan = pan[:4] + "*" * (len(pan) - 8) + pan[-4:]
                print(f"   PAN: {masked_pan}")
            
            if 'expiry' in card_data and card_data['expiry']:
                print(f"   Expiry: {card_data['expiry']}")
                
            if 'cardholder_name' in card_data and card_data['cardholder_name']:
                print(f"   Name: {card_data['cardholder_name']}")
            
            # Show applications
            applications = card_data.get('all_applications', {})
            print(f"\n   EMV Applications ({len(applications)}):")
            for aid, app_info in applications.items():
                print(f"     • {aid}: {app_info.get('name', 'Unknown')}")
            
            # Check preplay data generation
            print("\n8. Pre-play Data Generation Results:")
            print("   " + "=" * 50)
            
            preplay_entries = len(attack_manager.preplay_db)
            print(f"   Pre-play entries generated: {preplay_entries}")
            
            if preplay_entries > 0:
                print("   ✓ Pre-play data successfully generated from real card!")
                
                # Show sample entry (mask sensitive data)
                for un, entry in attack_manager.preplay_db.items():
                    print(f"   Sample entry:")
                    print(f"     UN: {un}")
                    print(f"     ATC: {entry.atc if entry.atc else 'N/A'}")
                    print(f"     ARQC: {entry.arqc[:8]}...{entry.arqc[-8:] if entry.arqc else 'N/A'}")
                    print(f"     Amount: {entry.amount}")
                    break  # Only show first entry
            else:
                print("   ⚠️  No pre-play entries generated")
                print("   This may be normal if:")
                print("     - Card doesn't support GENERATE AC commands")
                print("     - Card requires PIN or other authentication")
                print("     - Card is blocked or has restrictions")
            
            print("\n9. Real Card Data Validation:")
            print("   " + "=" * 50)
            
            # Validate this is real data, not mock
            is_real_data = True
            validation_notes = []
            
            # Check ATR
            atr = card_data.get('atr', '')
            if atr in ['3B8F8001804F0CA000000306030001000000006A', 
                      '3B7F9600000031B865B084136C616E6B', 
                      'MOCK_ATR', 'TEST_ATR']:
                is_real_data = False
                validation_notes.append("ATR appears to be mock/test data")
            
            # Check PAN
            pan = card_data.get('pan', '')
            if pan in ['4111111111111111', '5555555555554444', '378282246310005',
                      'MOCK_PAN', 'TEST_PAN', '1234567890123456']:
                is_real_data = False
                validation_notes.append("PAN appears to be mock/test data")
            
            # Check name
            name = card_data.get('cardholder_name', '')
            if name in ['TEST CARDHOLDER', 'MOCK USER', 'JOHN DOE', 'TEST USER']:
                is_real_data = False
                validation_notes.append("Cardholder name appears to be mock/test data")
            
            if is_real_data and not validation_notes:
                print("   ✅ CONFIRMED: Data is from real card (not mock)")
            else:
                print("   ⚠️  WARNING: Data may be mock/test data")
                for note in validation_notes:
                    print(f"     • {note}")
            
            print("\n" + "=" * 70)
            print("✅ Real card pre-play debugging completed successfully!")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error reading card: {e}")
            logger.exception("Card reading failed")
            return False
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        logger.exception("Debug process failed")
        return False
    
    finally:
        # Clean up
        try:
            if 'reader_instance' in locals() and reader_instance:
                reader_instance.disconnect()
                print("\n🔌 Reader disconnected")
        except:
            pass

def main():
    """Main entry point."""
    success = test_real_card_preplay()
    
    if success:
        print("\n🎉 Pre-play mode debugging with real card completed!")
        print("\nNext steps:")
        print("1. Use the generated pre-play data for attack simulations")
        print("2. Test with different card types and issuers")
        print("3. Validate cryptogram extraction accuracy")
    else:
        print("\n❌ Debugging failed - check logs and hardware setup")
        
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
