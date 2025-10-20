#!/usr/bin/env python3
"""
Test script to verify enhanced mock EMV data population
"""

def test_enhanced_mock_data():
    """Test that mock CardManager now returns realistic EMV data"""
    
    from card_manager import CardManager
    from emv_card import EMVCard, EMVApplication
    
    # Create CardManager and read mock card
    card_manager = CardManager()
    result = card_manager.read_card("ACR122U")
    
    if not result:
        print("❌ Card reading failed!")
        return False
    
    print("✅ Card reading successful!")
    print(f"Card ID: {result['card_id']}")
    print(f"ATR: {result['atr']}")
    print(f"Reader: {result['reader']}")
    
    # Test the UI-compatible card data
    card_data = result['card_data']
    print(f"\n📊 Card Data Structure:")
    print(f"  Card Type: {card_data.get('card_type', 'N/A')}")
    print(f"  PAN: {card_data.get('pan', 'N/A')}")
    print(f"  Cardholder: {card_data.get('cardholder_name', 'N/A')}")
    print(f"  Expiry: {card_data.get('expiry_date', 'N/A')}")
    
    # Test applications data
    applications = card_data.get('applications', [])
    print(f"\n🏦 Applications ({len(applications)} found):")
    for i, app in enumerate(applications):
        print(f"  {i+1}. AID: {app.get('aid', 'Unknown')}")
        print(f"     Label: {app.get('label', 'Unknown')}")
        print(f"     Name: {app.get('preferred_name', 'Unknown')}")
    
    # Test TLV data
    tlv_data = card_data.get('tlv_data', {})
    print(f"\n🏷️  TLV Data ({len(tlv_data)} tags):")
    for tag, data in list(tlv_data.items())[:5]:  # Show first 5 tags
        if isinstance(data, dict):
            value = data.get('value', '')[:20] + '...' if len(data.get('value', '')) > 20 else data.get('value', '')
            desc = data.get('description', '')
            print(f"  {tag}: {value} ({desc})")
        else:
            print(f"  {tag}: {str(data)[:20]}...")
    
    if len(tlv_data) > 5:
        print(f"  ... and {len(tlv_data) - 5} more tags")
    
    # Test track data
    track_data = card_data.get('track_data', {})
    print(f"\n💳 Track Data ({len(track_data)} tracks):")
    for track, data in track_data.items():
        print(f"  {track}: {data[:30]}..." if len(data) > 30 else f"  {track}: {data}")
    
    # Test raw APDU responses
    raw_responses = card_data.get('raw_responses', [])
    print(f"\n📡 Raw APDU Responses ({len(raw_responses)} commands):")
    for i, response in enumerate(raw_responses[:3]):  # Show first 3
        cmd = response.get('command', '')[:20] + '...' if len(response.get('command', '')) > 20 else response.get('command', '')
        resp = response.get('response', '')[:20] + '...' if len(response.get('response', '')) > 20 else response.get('response', '')
        print(f"  {i+1}. CMD: {cmd}")
        print(f"     RSP: {resp}")
    
    if len(raw_responses) > 3:
        print(f"  ... and {len(raw_responses) - 3} more responses")
    
    # Verify that data is not empty
    checks = [
        ("Applications", len(applications) > 0),
        ("TLV Data", len(tlv_data) > 0),
        ("Track Data", len(track_data) > 0),
        ("APDU Responses", len(raw_responses) > 0),
        ("PAN Present", bool(card_data.get('pan'))),
        ("Cardholder Name", bool(card_data.get('cardholder_name')))
    ]
    
    print(f"\n✅ Data Verification:")
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    print("🧪 Testing Enhanced Mock EMV Data...")
    print("="*50)
    
    success = test_enhanced_mock_data()
    
    print("\n" + "="*50)
    if success:
        print("🎉 All tests passed! Mock data is properly populated.")
        print("   The UI should now display meaningful EMV data.")
    else:
        print("⚠️  Some tests failed. Check the mock data population.")
