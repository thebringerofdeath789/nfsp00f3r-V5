#!/usr/bin/env python3
"""
Debug script to check ACR122 reader and card detection status
"""

def debug_reader_status():
    """Debug the reader detection and card presence"""
    
    print("=== ACR122 READER DEBUG ===")
    print()
    
    try:
        # Step 1: Check reader detection
        print("1. Checking reader detection...")
        from readers import ReaderManager
        
        reader_manager = ReaderManager()
        available_readers = reader_manager.detect_readers()
        
        print(f"   Found {len(available_readers)} readers:")
        for i, reader in enumerate(available_readers):
            print(f"   {i+1}. {reader}")
        
        # Step 2: Look for ACR122 specifically
        print("\n2. Looking for ACR122...")
        acr122_reader = None
        for reader in available_readers:
            if 'acr122' in reader.get('description', '').lower():
                acr122_reader = reader
                print(f"   ✅ Found ACR122: {reader['description']}")
                break
        
        if not acr122_reader:
            print("   ❌ No ACR122 reader found!")
            return False
        
        # Step 3: Try to connect to ACR122
        print("\n3. Connecting to ACR122...")
        connection_result = reader_manager.connect_reader(acr122_reader)
        print(f"   Connection result: {connection_result}")
        
        if not connection_result:
            print("   ❌ Failed to connect to ACR122")
            return False
        
        # Step 4: Get reader instance and check card presence
        print("\n4. Checking card presence...")
        reader_instance = reader_manager.get_reader(acr122_reader['name'])  # Use 'name' not 'description'
        
        if reader_instance:
            print(f"   Reader instance: {type(reader_instance).__name__}")
            print(f"   Connected: {reader_instance.connected}")
            print(f"   Card present: {reader_instance.card_present}")
            print(f"   Current ATR: {reader_instance.current_atr}")
            
            if reader_instance.card_present:
                print("   ✅ Card is present!")
                
                # Test card connection directly
                print("\n5. Testing card connection...")
                try:
                    connect_result = reader_instance.connect_to_card()
                    print(f"   Connect result: {connect_result}")
                    if connect_result:
                        print(f"   ATR after connection: {reader_instance.current_atr}")
                        print("   ✅ Card connection successful!")
                    else:
                        print("   ❌ Card connection failed")
                except Exception as e:
                    print(f"   ❌ Card connection error: {e}")
                    import traceback
                    print(f"   Error details: {traceback.format_exc()}")
                
                return True
            else:
                print("   ⚠️  No card detected on reader")
                print("   📝 Place a contactless card on the ACR122 reader and try again")
                return False
        else:
            print("   ❌ Could not get reader instance")
            return False
            
    except Exception as e:
        print(f"❌ Error during reader debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_card_reading_with_card():
    """Test actual card reading if a card is present"""
    
    print("\n=== CARD READING TEST ===")
    
    try:
        from card_manager import CardManager
        
        cm = CardManager()
        print("CardManager created")
        
        # Try reading with exact ACR122 description
        print("Attempting to read from ACR122...")
        result = cm.read_card("PC/SC Reader: ACS ACR122 0")
        
        if result:
            print("✅ Card reading successful!")
            
            card_data = result['card_data']
            reader_name = result.get('reader', 'Unknown')
            atr = result.get('atr', 'N/A')
            
            print(f"Reader: {reader_name}")
            print(f"ATR: {atr}")
            print(f"PAN: {card_data.get('pan', 'N/A')}")
            print(f"Cardholder: {card_data.get('cardholder_name', 'N/A')}")
            
            # Check if this is real or mock data
            if card_data.get('pan') == '5555444433332222':
                print("⚠️  This is mock data (fallback)")
                print("   Real card reading failed, system used test data")
            else:
                print("🎉 This is real card data!")
                print("   Successfully read from physical card")
            
            return card_data.get('pan') != '5555444433332222'
        else:
            print("❌ Card reading failed - returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error during card reading test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 NFSP00F3R ACR122 Debug Tool")
    print("=" * 50)
    
    # Debug reader status
    reader_ok = debug_reader_status()
    
    # Test card reading
    card_ok = test_card_reading_with_card()
    
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    print(f"   Reader Detection: {'✅ OK' if reader_ok else '❌ FAILED'}")
    print(f"   Card Reading: {'✅ REAL DATA' if card_ok else '⚠️  MOCK DATA'}")
    
    if not reader_ok:
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Make sure ACR122U is connected via USB")
        print("   2. Check that PC/SC service is running")
        print("   3. Try installing/reinstalling ACR122U drivers")
    elif not card_ok:
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Place a contactless EMV card on the ACR122 reader")
        print("   2. Make sure the card is positioned correctly")
        print("   3. Try different cards (credit/debit with contactless)")
        print("   4. Check that the card is not damaged")
