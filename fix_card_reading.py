#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Card Reading Diagnostics and Fix Script
Diagnoses and fixes card reading issues with the ACR122 reader.
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

def test_direct_pcsc_reading():
    """Test direct PC/SC card reading to identify issues."""
    print("\n=== Testing Direct PC/SC Card Reading ===")
    
    try:
        import smartcard
        from smartcard.System import readers
        from smartcard.CardRequest import CardRequest
        from smartcard.CardType import AnyCardType
        from smartcard.CardConnection import CardConnection
        from smartcard.Exceptions import CardRequestTimeoutException, NoCardException
        from smartcard.util import toHexString
        
        # Get readers
        reader_list = readers()
        if not reader_list:
            print("✗ No readers found")
            return False
        
        reader = reader_list[0]
        print(f"✓ Using reader: {reader}")
        
        try:
            # Try to detect card with timeout
            print("Detecting card...")
            cardrequest = CardRequest(timeout=5, cardType=AnyCardType(), readers=[reader])
            cardservice = cardrequest.waitforcard()
            
            print("✓ Card detected, attempting connection...")
            
            # Get the connection object
            connection = cardservice.connection
            
            # Try different connection protocols
            protocols = [
                ("T=0", CardConnection.T0_protocol),
                ("T=1", CardConnection.T1_protocol),
                ("Any", None)
            ]
            
            connected = False
            for protocol_name, protocol in protocols:
                try:
                    if protocol:
                        connection.connect(protocol)
                    else:
                        connection.connect()
                    print(f"✓ Connected using {protocol_name} protocol")
                    connected = True
                    break
                except Exception as e:
                    print(f"⚠️  {protocol_name} protocol failed: {e}")
                    continue
            
            if not connected:
                print("✗ Failed to connect with any protocol")
                return False
            
            # Get ATR
            atr = connection.getATR()
            if atr:
                atr_hex = toHexString(atr).replace(' ', '').upper()
                print(f"✓ ATR: {atr_hex}")
                
                # Parse ATR
                if len(atr) > 0:
                    print(f"  - ATR Length: {len(atr)} bytes")
                    if len(atr) > 1:
                        print(f"  - Format byte (T0): 0x{atr[1]:02X}")
                    
                    # Basic ATR analysis
                    if atr_hex.startswith('3B'):
                        print("  - Direct convention")
                    elif atr_hex.startswith('3F'):
                        print("  - Inverse convention")
                    
                    # Try to identify card type
                    if '1402' in atr_hex or 'MIFARE' in str(atr):
                        print("  - Detected: MIFARE card")
                    elif '4F' in atr_hex:
                        print("  - Possible EMV/Payment card")
                    else:
                        print("  - Unknown card type")
            else:
                print("⚠️  No ATR received")
            
            # Test basic APDU communication
            print("\nTesting APDU communication...")
            
            # Try SELECT PPSE (EMV)
            try:
                ppse_cmd = [0x00, 0xA4, 0x04, 0x00, 0x0E, 
                           0x32, 0x50, 0x41, 0x59, 0x2E, 0x53, 0x59, 
                           0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 0x00]
                
                response, sw1, sw2 = connection.transmit(ppse_cmd)
                print(f"✓ SELECT PPSE: SW={sw1:02X}{sw2:02X}")
                
                if sw1 == 0x90:
                    print("  - SELECT successful")
                elif sw1 == 0x6A and sw2 == 0x82:
                    print("  - File not found (not an EMV card)")
                else:
                    print(f"  - Response: {sw1:02X}{sw2:02X}")
                    
            except Exception as e:
                print(f"⚠️  SELECT PPSE failed: {e}")
            
            # Try GET CHALLENGE (basic test)
            try:
                challenge_cmd = [0x00, 0x84, 0x00, 0x00, 0x08]
                response, sw1, sw2 = connection.transmit(challenge_cmd)
                print(f"✓ GET CHALLENGE: SW={sw1:02X}{sw2:02X}")
                
                if response and len(response) > 0:
                    challenge_hex = ''.join([f"{b:02X}" for b in response])
                    print(f"  - Challenge: {challenge_hex}")
                    
            except Exception as e:
                print(f"⚠️  GET CHALLENGE failed: {e}")
            
            # Test reading UID (for MIFARE cards)
            try:
                uid_cmd = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                response, sw1, sw2 = connection.transmit(uid_cmd)
                print(f"✓ GET UID: SW={sw1:02X}{sw2:02X}")
                
                if response and len(response) > 0:
                    uid_hex = ''.join([f"{b:02X}" for b in response])
                    print(f"  - UID: {uid_hex}")
                    
            except Exception as e:
                print(f"⚠️  GET UID failed: {e}")
            
            # Disconnect
            connection.disconnect()
            print("✓ Disconnected from card")
            
            return True
            
        except CardRequestTimeoutException:
            print("⚠️  No card detected (timeout)")
            print("   - Make sure a card is placed on the reader")
            print("   - Try different card types (MIFARE, EMV, etc.)")
            return False
            
    except Exception as e:
        print(f"✗ Error in direct PC/SC test: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_reader_implementation():
    """Create a fixed version of the PCSCCardReader."""
    print("\n=== Creating Fixed Reader Implementation ===")
    
    fixed_code = '''
    def get_atr(self) -> Optional[bytes]:
        """Get the ATR of the current card."""
        try:
            # Always try to get fresh ATR
            if not self.connection:
                if not self.connect_to_card():
                    return None
            
            # Get ATR from active connection
            if self.connection:
                atr = self.connection.getATR()
                if atr:
                    self.current_atr = bytes(atr)
                    return self.current_atr
                    
            return self.current_atr
            
        except Exception as e:
            self.logger.error(f"Error getting ATR: {e}")
            # Try to reconnect and get ATR
            try:
                if self.connect_to_card():
                    atr = self.connection.getATR()
                    if atr:
                        self.current_atr = bytes(atr)
                        return self.current_atr
            except:
                pass
                
            return None
    
    def connect_to_card(self) -> bool:
        """Establish connection to the card for APDU communication."""
        try:
            if self.connection:
                # Already connected, test if still valid
                try:
                    # Try to get ATR to test connection
                    atr = self.connection.getATR()
                    if atr:
                        self.current_atr = bytes(atr)
                        return True
                except:
                    # Connection lost, clean up
                    try:
                        self.connection.disconnect()
                    except:
                        pass
                    self.connection = None
                    
            # Create new connection
            from smartcard.CardRequest import CardRequest
            from smartcard.CardType import AnyCardType
            from smartcard.CardConnection import CardConnection
            
            self.logger.info(f"Connecting to card in {self.name}")
            cardrequest = CardRequest(timeout=5, cardType=AnyCardType(), readers=[self.reader])
            cardservice = cardrequest.waitforcard()
            
            # Get connection
            connection = cardservice.connection
            
            # Try to connect with best protocol
            protocols = [
                CardConnection.T0_protocol,
                CardConnection.T1_protocol,
                None  # Any protocol
            ]
            
            connected = False
            for protocol in protocols:
                try:
                    if protocol:
                        connection.connect(protocol)
                    else:
                        connection.connect()
                    connected = True
                    break
                except Exception as e:
                    self.logger.debug(f"Protocol {protocol} failed: {e}")
                    continue
            
            if not connected:
                self.logger.error("Failed to connect with any protocol")
                return False
                
            self.connection = connection
            
            # Get ATR immediately after connecting
            try:
                atr = connection.getATR()
                if atr:
                    self.current_atr = bytes(atr)
                    self.logger.info(f"Connected to card, ATR: {self.current_atr.hex().upper()}")
                else:
                    self.logger.warning("Connected but no ATR received")
                    self.current_atr = None
            except Exception as e:
                self.logger.warning(f"Connected but ATR read failed: {e}")
                self.current_atr = None
            
            # Update status
            self.card_present = True
            
            if self.card_inserted_callback:
                self.card_inserted_callback(self.name, self.current_atr)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to card: {e}")
            return False
    '''
    
    print("✓ Fixed implementation created")
    print("This implementation:")
    print("  - Always tries to get fresh ATR")
    print("  - Tests connection validity")
    print("  - Tries multiple protocols")
    print("  - Handles reconnection automatically")
    
    return fixed_code

def main():
    """Run card reading diagnostics and fixes."""
    print("Card Reading Diagnostics and Fix Script")
    print("=" * 50)
    
    # Test 1: Direct PC/SC reading
    direct_success = test_direct_pcsc_reading()
    
    # Test 2: Generate fix
    fix_code = fix_reader_implementation()
    
    print("\n" + "="*50)
    print("Diagnostic Results:")
    print(f"Direct PC/SC Test: {'✓ PASS' if direct_success else '✗ FAIL'}")
    
    if direct_success:
        print("\n✓ Card reading works at PC/SC level")
        print("The issue is likely in the ReaderManager implementation")
        print("Apply the fixed implementation to readers.py")
    else:
        print("\n❌ Card reading fails at PC/SC level")
        print("Possible issues:")
        print("  - Card not properly seated on reader")
        print("  - Reader driver issues")
        print("  - Unsupported card type")
        print("  - Hardware malfunction")

if __name__ == "__main__":
    main()
