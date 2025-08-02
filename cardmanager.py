# =====================================================================
# File: cardmanager.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   CardManager handles multiple EMVCard instances, current-card selection,
#   card enumeration, manual re-reads, and APDU logging. Integrates with
#   reader modules and the Logger.
#
# Functions:
#   - add_card(card: EMVCard)
#   - remove_card(pan: str)
#   - switch_card(pan: str)
#   - get_current_card() -> EMVCard or None
#   - list_all_cards() -> List[str]
#   - read_current_card() -> bool
#   - send_apdu(apdu: bytes) -> bytes
#   - get_apdu_log() -> List[Tuple[bytes, bytes]]
#
# Signals:
#   - card_inserted(EMVCard)
#   - card_removed(str)
#   - card_switched(EMVCard)
#   - cards_updated(list)
#   - apdu_log_updated()
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal
from emvcard import EMVCard
import random

class CardManager(QObject):
    card_inserted    = pyqtSignal(object)   # EMVCard
    card_removed     = pyqtSignal(str)      # PAN
    card_switched    = pyqtSignal(object)   # EMVCard
    cards_updated    = pyqtSignal(list)     # list of PANs
    apdu_log_updated = pyqtSignal()

    def __init__(self, logger):
        super().__init__()
        self.logger = logger
        self.cards = {}           # pan:str -> EMVCard
        self.current_pan = None
        self.apdu_log = []        # List of tuples (apdu_bytes, response_bytes)
        self.no_pan_counter = 0   # For generating unique NO_PAN keys

    def _get_pan(self, card: EMVCard) -> str:
        # Try direct attribute first, fall back to parsed info
        pan = getattr(card, "pan", None)
        if not pan or not isinstance(pan, str) or not pan.strip():
            info = card.get_cardholder_info()
            pan = info.get("PAN", "")
        if not pan or not isinstance(pan, str) or not pan.strip():
            # Generate a unique NO_PAN key
            rand_part = random.randint(100000000, 999999999)
            pan = f"NO_PAN_{rand_part}"
        return pan

    def add_card(self, card):
        # Re-wrap the card to ensure logging is connected, if not already set
        # If it's a dict (imported), create a new EMVCard with logging
        if isinstance(card, dict):
            card = EMVCard(card, log_callback=self.logger.log)
        elif isinstance(card, EMVCard) and not hasattr(card, 'log_callback'):
            # Defensive: if someone hands in a raw EMVCard, wrap it
            card = EMVCard(card.source, log_callback=self.logger.log)
        pan = self._get_pan(card)
        # Ensure the PAN is unique in our dict
        while pan in self.cards:
            pan = f"{pan}_{random.randint(0,99999)}"
        self.cards[pan] = card
        self.logger.log(f"Added card: PAN={pan}")
        self.card_inserted.emit(card)
        self.cards_updated.emit(list(self.cards.keys()))
        if self.current_pan is None:
            self.switch_card(pan)

    def remove_card(self, pan: str):
        if pan not in self.cards:
            return
        del self.cards[pan]
        self.logger.log(f"Card removed: PAN={pan}")
        self.card_removed.emit(pan)
        self.cards_updated.emit(list(self.cards.keys()))
        if self.current_pan == pan:
            next_pan = next(iter(self.cards.keys()), None)
            self.switch_card(next_pan)

    def switch_card(self, pan: str):
        if pan not in self.cards:
            self.current_pan = None
            self.logger.log("No current card")
            self.card_switched.emit(None)
            return
        self.current_pan = pan
        card = self.cards.get(pan)
        self.logger.log(f"Current card switched to PAN={pan}")
        self.card_switched.emit(card)

    def get_current_card(self):
        return self.cards.get(self.current_pan)

    def list_all_cards(self):
        return list(self.cards.keys())

    def read_current_card(self):
        card = self.get_current_card()
        if not card:
            return False
        self.logger.log(f"Re-reading card PAN={self._get_pan(card)}")
        try:
            # Always re-instantiate to ensure logger is set and state is fresh
            source = card.source if hasattr(card, "source") else card
            new_card = EMVCard(source, log_callback=self.logger.log)
            pan = self._get_pan(new_card)
            # Ensure uniqueness
            while pan in self.cards and self.cards[pan] is not card:
                pan = f"{pan}_{random.randint(0,99999)}"
            self.cards[pan] = new_card
            self.current_pan = pan
            self.card_switched.emit(new_card)
            self.cards_updated.emit(list(self.cards.keys()))
            return True
        except Exception as e:
            self.logger.log(f"Failed to re-read card: {e}")
            return False

    def send_apdu(self, apdu: bytes) -> bytes:
        card = self.get_current_card()
        if not card:
            return b""
        # No need to log APDU here, EMVCard handles all APDU logging directly
        resp = card.send_apdu(apdu)
        self.apdu_log.append((apdu, resp))
        self.apdu_log_updated.emit()
        return resp

    def get_apdu_log(self):
        return list(self.apdu_log)
