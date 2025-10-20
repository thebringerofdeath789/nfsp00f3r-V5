#!/usr/bin/env python3
"""
NFSP00F3R V5.0 - Real Card Debugging Utility
===========================================

This utility performs comprehensive debugging using ONLY real card data.
NO MOCK DATA is used anywhere in this script.

Features:
- Real card detection and reading
- EMV application enumeration
- Pre-play data generation testing
- Attack vector validation
- Cryptogram extraction verification

Usage:
    python real_card_debug.py [options]

Options:
    --reader NAME     Specify reader name
    --preplay         Enable pre-play mode testing
    --verbose         Enable verbose logging
    --save-data       Save debug data to files

Requirements:
    - Physical card reader connected
    - Real EMV card available
    - Python dependencies installed
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, List

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card_manager import CardManager
from attack_manager import AttackManager
from readers import ReaderManager
from emv_card import EMVCard

class RealCardDebugger:
    """Comprehensive real card debugging utility."""
    
    def __init__(self, verbose: bool = False, save_data: bool = False):
        self.verbose = verbose
        self.save_data = save_data
        self.debug_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'real_card_debug_{self.debug_session}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.card_manager = CardManager()
        self.attack_manager = AttackManager()
        self.reader_manager = ReaderManager()
        
        # Debug data collection
        self.debug_data = {
            'session_id': self.debug_session,
            'timestamp': datetime.now().isoformat(),
            'readers_detected': [],
            'cards_read': [],
            'preplay_entries': [],
            'errors': []
        }
    
    def print_header(self, title: str):
        """Print formatted section header."""
        print("\n" + "=" * 70)
        print(f" {title}")
        print("=" * 70)
    
    def print_info(self, message: str, indent: int = 0):
        """Print formatted info message."""
        prefix = "  " * indent
        print(f"{prefix}• {message}")
    
    def print_success(self, message: str, indent: int = 0):
        """Print formatted success message."""
        prefix = "  " * indent
        print(f"{prefix}✅ {message}")
    
    def print_warning(self, message: str, indent: int = 0):
        """Print formatted warning message."""
        prefix = "  " * indent
        print(f"{prefix}⚠️  {message}")
    
    def print_error(self, message: str, indent: int = 0):
        """Print formatted error message."""
        prefix = "  " * indent
        print(f"{prefix}❌ {message}")
    
    def detect_readers(self) -> List[str]:
        """Detect available card readers."""
        self.print_header("CARD READER DETECTION")
        
        try:
            reader_info_list = self.reader_manager.detect_readers()
            readers = [info['name'] for info in reader_info_list]
            self.debug_data['readers_detected'] = readers
            
            if not readers:
                self.print_error("No card readers detected")
                self.print_info("Please ensure:")
                self.print_info("- Card reader is connected via USB", 1)
                self.print_info("- Reader drivers are installed", 1)
                self.print_info("- Reader is not in use by other software", 1)
                return []
            
            self.print_success(f"Detected {len(readers)} reader(s):")
            for i, reader in enumerate(readers):
                self.print_info(f"[{i}] {reader}", 1)
            
            return readers
            
        except Exception as e:
            self.print_error(f"Reader detection failed: {e}")
            self.debug_data['errors'].append(f"Reader detection: {e}")
            return []
    
    def connect_reader(self, reader_name: str) -> Optional[object]:
        """Connect to specified card reader."""
        self.print_header(f"CONNECTING TO READER: {reader_name}")
        
        try:
            # Get reader info from detected readers
            reader_info_list = self.reader_manager.detect_readers()
            reader_info = None
            
            for info in reader_info_list:
                if info['name'] == reader_name:
                    reader_info = info
                    break
            
            if not reader_info:
                self.print_error(f"Reader '{reader_name}' not found in detected readers")
                return None
            
            # Connect to reader using the info dictionary
            success = self.reader_manager.connect_reader(reader_info)
            if not success:
                self.print_error("Failed to connect to reader")
                return None
            
            self.print_success("Reader connected successfully")
            
            # Get the reader instance
            reader_instance = self.reader_manager.get_reader(reader_name)
            if not reader_instance:
                self.print_error("Failed to get reader instance")
                return None
            
            # Test basic communication
            try:
                if hasattr(reader_instance, 'connection') and reader_instance.connection:
                    self.print_success("Reader communication verified")
                elif hasattr(reader_instance, 'is_connected') and reader_instance.is_connected():
                    self.print_success("Reader communication verified")
                else:
                    self.print_warning("Reader connection may be unstable")
            except Exception as e:
                self.print_warning(f"Reader communication test failed: {e}")
            
            return reader_instance
            
        except Exception as e:
            self.print_error(f"Reader connection failed: {e}")
            self.debug_data['errors'].append(f"Reader connection: {e}")
            return None
    
    def wait_for_card(self, reader_instance) -> bool:
        """Wait for card to be placed on reader."""
        self.print_header("WAITING FOR CARD")
        self.print_info("Place an EMV card on the reader...")
        
        max_attempts = 15
        
        for attempt in range(max_attempts):
            try:
                self.print_info(f"Attempt {attempt + 1}/{max_attempts}: Checking for card...")
                
                connection = reader_instance.connection
                if connection:
                    try:
                        atr = connection.getATR()
                        if atr and len(atr) > 0:
                            atr_hex = ''.join([f'{b:02X}' for b in atr])
                            self.print_success(f"Card detected! ATR: {atr_hex}")
                            return True
                    except Exception as e:
                        self.logger.debug(f"ATR check failed: {e}")
                
                import time
                time.sleep(2)
                
            except Exception as e:
                self.logger.debug(f"Card detection attempt {attempt + 1} failed: {e}")
                continue
        
        self.print_error("No card detected after maximum attempts")
        self.print_info("Troubleshooting tips:")
        self.print_info("- Ensure card is placed flat on reader", 1)
        self.print_info("- Try repositioning the card", 1)
        self.print_info("- Check if card is damaged or expired", 1)
        self.print_info("- Test with a different card", 1)
        
        return False
    
    def read_card_data(self, reader_instance) -> Optional[Dict]:
        """Read comprehensive EMV data from card."""
        self.print_header("READING CARD DATA (NO MOCK DATA)")
        
        try:
            # Read EMV data directly from physical card
            card_data = self.card_manager.read_emv_card(reader_instance)
            
            if not card_data:
                self.print_error("Failed to read EMV data from card")
                return None
            
            # Validate this is real data
            if not self.validate_real_data(card_data):
                self.print_error("Data validation failed - possible mock data detected")
                return None
            
            self.print_success("Successfully read real card data!")
            
            # Display card information (with security masking)
            self.display_card_info(card_data)
            
            # Save to debug data
            card_entry = {
                'timestamp': datetime.now().isoformat(),
                'atr': card_data.get('atr', ''),
                'applications_count': len(card_data.get('all_applications', {})),
                'has_pan': bool(card_data.get('pan')),
                'has_expiry': bool(card_data.get('expiry')),
                'has_name': bool(card_data.get('cardholder_name'))
            }
            self.debug_data['cards_read'].append(card_entry)
            
            return card_data
            
        except Exception as e:
            self.print_error(f"Card reading failed: {e}")
            self.debug_data['errors'].append(f"Card reading: {e}")
            self.logger.exception("Card reading failed")
            return None
    
    def validate_real_data(self, card_data: Dict) -> bool:
        """Validate that data is from real card, not mock."""
        validation_issues = []
        
        # Check ATR for known test values
        atr = card_data.get('atr', '')
        mock_atrs = [
            '3B8F8001804F0CA000000306030001000000006A',
            '3B7F9600000031B865B084136C616E6B',
            'MOCK_ATR', 'TEST_ATR', 'SAMPLE_ATR'
        ]
        if atr in mock_atrs:
            validation_issues.append("ATR matches known mock value")
        
        # Check PAN for test values
        pan = card_data.get('pan', '')
        mock_pans = [
            '4111111111111111', '5555555555554444', '378282246310005',
            '4000000000000002', '5105105105105100', '6011111111111117',
            'MOCK_PAN', 'TEST_PAN', '1234567890123456'
        ]
        if pan in mock_pans:
            validation_issues.append("PAN matches known test value")
        
        # Check cardholder name for test values
        name = card_data.get('cardholder_name', '')
        mock_names = [
            'TEST CARDHOLDER', 'MOCK USER', 'JOHN DOE', 'TEST USER',
            'SAMPLE CARDHOLDER', 'DEBUG USER', 'FAKE NAME'
        ]
        if name in mock_names:
            validation_issues.append("Cardholder name matches known test value")
        
        if validation_issues:
            self.print_warning("Data validation concerns:")
            for issue in validation_issues:
                self.print_warning(f"- {issue}", 1)
            return False
        
        self.print_success("Data validation passed - appears to be real card data")
        return True
    
    def display_card_info(self, card_data: Dict):
        """Display card information with security considerations."""
        print("\n📱 Real Card Information:")
        print("   " + "-" * 50)
        
        # ATR
        if 'atr' in card_data and card_data['atr']:
            atr = card_data['atr']
            print(f"   ATR: {atr[:16]}...{atr[-16:] if len(atr) > 32 else atr}")
        
        # PAN (masked for security)
        if 'pan' in card_data and card_data['pan']:
            pan = card_data['pan']
            if len(pan) >= 8:
                masked_pan = pan[:4] + "*" * (len(pan) - 8) + pan[-4:]
            else:
                masked_pan = "*" * len(pan)
            print(f"   PAN: {masked_pan}")
        
        # Expiry
        if 'expiry' in card_data and card_data['expiry']:
            print(f"   Expiry: {card_data['expiry']}")
        
        # Cardholder name (partially masked)
        if 'cardholder_name' in card_data and card_data['cardholder_name']:
            name = card_data['cardholder_name']
            if len(name) > 4:
                masked_name = name[:2] + "*" * (len(name) - 4) + name[-2:]
            else:
                masked_name = name
            print(f"   Name: {masked_name}")
        
        # Applications
        applications = card_data.get('all_applications', {})
        print(f"\n   📋 EMV Applications ({len(applications)}):")
        for aid, app_info in applications.items():
            app_name = app_info.get('name', 'Unknown Application')
            print(f"     • {aid}: {app_name}")
    
    def test_preplay_mode(self, reader_instance, card_data: Dict) -> bool:
        """Test pre-play mode functionality with real card."""
        self.print_header("PRE-PLAY MODE TESTING")
        
        try:
            # Enable pre-play mode
            self.card_manager.enable_preplay_mode()
            self.card_manager.attack_manager = self.attack_manager
            
            self.print_success("Pre-play mode enabled")
            
            # Initial preplay database state
            initial_entries = len(self.attack_manager.preplay_db)
            self.print_info(f"Initial preplay entries: {initial_entries}")
            
            # Attempt to generate preplay data from real card
            self.print_info("Attempting pre-play data generation...")
            
            # This should trigger preplay data generation during card reading
            emv_card = EMVCard()  # Create EMV card object
            
            # Call preplay generation method directly
            self.card_manager._generate_preplay_data(reader_instance, emv_card, card_data)
            
            # Check results
            final_entries = len(self.attack_manager.preplay_db)
            generated_entries = final_entries - initial_entries
            
            self.print_info(f"Final preplay entries: {final_entries}")
            self.print_info(f"Generated entries: {generated_entries}")
            
            if generated_entries > 0:
                self.print_success(f"Pre-play data generation successful!")
                
                # Display sample preplay data (with security masking)
                self.display_preplay_results()
                
                # Save preplay entries to debug data
                for un, entry in self.attack_manager.preplay_db.items():
                    preplay_entry = {
                        'un': un,
                        'atc': entry.atc,
                        'has_arqc': bool(entry.arqc),
                        'has_tc': bool(entry.tc),
                        'amount': entry.amount,
                        'currency': entry.currency,
                        'timestamp': entry.timestamp
                    }
                    self.debug_data['preplay_entries'].append(preplay_entry)
                
                return True
            else:
                self.print_warning("No pre-play entries generated")
                self.print_info("This may be normal if:")
                self.print_info("- Card doesn't support GENERATE AC commands", 1)
                self.print_info("- Card requires PIN authentication", 1)
                self.print_info("- Card has transaction limits or blocks", 1)
                self.print_info("- Card uses advanced security features", 1)
                return False
            
        except Exception as e:
            self.print_error(f"Pre-play testing failed: {e}")
            self.debug_data['errors'].append(f"Pre-play testing: {e}")
            self.logger.exception("Pre-play testing failed")
            return False
    
    def display_preplay_results(self):
        """Display preplay generation results."""
        print("\n🔐 Pre-play Data Generation Results:")
        print("   " + "-" * 50)
        
        entry_count = 0
        for un, entry in self.attack_manager.preplay_db.items():
            if entry_count >= 3:  # Limit display to first 3 entries
                remaining = len(self.attack_manager.preplay_db) - entry_count
                print(f"   ... and {remaining} more entries")
                break
            
            print(f"   Entry #{entry_count + 1}:")
            print(f"     UN: {un}")
            print(f"     ATC: {entry.atc if entry.atc else 'N/A'}")
            
            # Mask cryptograms for security
            if entry.arqc:
                arqc_masked = entry.arqc[:8] + "..." + entry.arqc[-8:]
                print(f"     ARQC: {arqc_masked}")
            else:
                print(f"     ARQC: N/A")
            
            if entry.tc:
                tc_masked = entry.tc[:8] + "..." + entry.tc[-8:]
                print(f"     TC: {tc_masked}")
            else:
                print(f"     TC: N/A")
            
            print(f"     Amount: ${int(entry.amount)/100:.2f}")
            print(f"     Currency: {entry.currency}")
            print()
            
            entry_count += 1
    
    def save_debug_data(self):
        """Save debug data to files."""
        if not self.save_data:
            return
        
        self.print_header("SAVING DEBUG DATA")
        
        try:
            # Save JSON debug data
            debug_filename = f"debug_data_{self.debug_session}.json"
            with open(debug_filename, 'w') as f:
                json.dump(self.debug_data, f, indent=2)
            
            self.print_success(f"Debug data saved to: {debug_filename}")
            
            # Save preplay database if entries exist
            if self.debug_data['preplay_entries']:
                preplay_filename = f"preplay_data_{self.debug_session}.json"
                preplay_export = {
                    'version': '1.0',
                    'generated_by': 'NFSP00F3R V5.0 Real Card Debugger',
                    'session_id': self.debug_session,
                    'entries': self.debug_data['preplay_entries']
                }
                
                with open(preplay_filename, 'w') as f:
                    json.dump(preplay_export, f, indent=2)
                
                self.print_success(f"Preplay data saved to: {preplay_filename}")
            
        except Exception as e:
            self.print_error(f"Failed to save debug data: {e}")
    
    def run_comprehensive_debug(self, reader_name: Optional[str] = None, test_preplay: bool = True) -> bool:
        """Run comprehensive debugging session."""
        self.print_header("NFSP00F3R V5.0 - REAL CARD DEBUGGING SESSION")
        print("🔍 Comprehensive debugging using ONLY real card data")
        print("⚠️  NO MOCK DATA will be used in this session")
        
        try:
            # 1. Detect readers
            readers = self.detect_readers()
            if not readers:
                return False
            
            # 2. Select reader
            if reader_name:
                if reader_name in readers:
                    selected_reader = reader_name
                else:
                    self.print_error(f"Specified reader '{reader_name}' not found")
                    return False
            else:
                selected_reader = readers[0]
            
            # 3. Connect to reader
            reader_instance = self.connect_reader(selected_reader)
            if not reader_instance:
                return False
            
            # 4. Wait for card
            if not self.wait_for_card(reader_instance):
                return False
            
            # 5. Read card data
            card_data = self.read_card_data(reader_instance)
            if not card_data:
                return False
            
            # 6. Test preplay mode
            preplay_success = True
            if test_preplay:
                preplay_success = self.test_preplay_mode(reader_instance, card_data)
            
            # 7. Save debug data
            self.save_debug_data()
            
            # 8. Summary
            self.print_header("DEBUG SESSION SUMMARY")
            self.print_success("Real card debugging completed successfully!")
            
            summary_stats = {
                'readers_detected': len(self.debug_data['readers_detected']),
                'cards_read': len(self.debug_data['cards_read']),
                'preplay_entries': len(self.debug_data['preplay_entries']),
                'errors_encountered': len(self.debug_data['errors'])
            }
            
            for key, value in summary_stats.items():
                self.print_info(f"{key.replace('_', ' ').title()}: {value}")
            
            if self.debug_data['errors']:
                self.print_warning("Errors encountered during session:")
                for error in self.debug_data['errors']:
                    self.print_warning(f"- {error}", 1)
            
            return True
            
        except Exception as e:
            self.print_error(f"Debug session failed: {e}")
            self.logger.exception("Debug session failed")
            return False
        
        finally:
            # Cleanup
            try:
                if 'reader_instance' in locals() and reader_instance:
                    reader_instance.disconnect()
                    self.print_info("Reader disconnected")
            except:
                pass

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="NFSP00F3R V5.0 - Real Card Debugging Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python real_card_debug.py                    # Basic debugging
  python real_card_debug.py --preplay         # Test preplay mode
  python real_card_debug.py --verbose --save-data  # Full debugging with data saving
  python real_card_debug.py --reader "ACS ACR122U"  # Use specific reader
        """
    )
    
    parser.add_argument('--reader', type=str, help='Specify reader name to use')
    parser.add_argument('--preplay', action='store_true', help='Enable pre-play mode testing')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--save-data', action='store_true', help='Save debug data to files')
    
    args = parser.parse_args()
    
    # Create debugger instance
    debugger = RealCardDebugger(verbose=args.verbose, save_data=args.save_data)
    
    # Run debugging session
    success = debugger.run_comprehensive_debug(
        reader_name=args.reader,
        test_preplay=args.preplay
    )
    
    if success:
        print("\n🎉 Debugging session completed successfully!")
        if args.preplay:
            print("\n📋 Next steps for pre-play attacks:")
            print("1. Use generated cryptogram data for replay attacks")
            print("2. Test with different card types and issuers")
            print("3. Validate attack effectiveness against target systems")
    else:
        print("\n❌ Debugging session failed")
        print("Check logs and ensure hardware is properly configured")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
