# =====================================================================
# File: cardreader_pcsc.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Manages PCSC smartcard readers using pyscard. Handles hotplug, insert/remove, APDU comms,
#   and passes new cards to CardManager.
#
# Functions:
#   - PCSCCardReader(QObject)
#   - start_monitoring(self)
#   - shutdown(self)
#   - send_apdu(self, apdu)
#   - Signal handlers for card events
# =====================================================================

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from smartcard.System import readers
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import toHexString
from emvcard import EMVCard
import time

class PCSCCardReader(QObject):
    card_inserted_signal = pyqtSignal(object)  # EMVCard

    def __init__(self, card_manager):
        super().__init__()
        self.card_manager = card_manager
        self.monitor = None
        self.observer = None
        self.active_connections = {}  # reader_name -> connection object
        # Ensure that cards are always added to the manager in the main thread
        self.card_inserted_signal.connect(self.card_manager.add_card)

    def start_monitoring(self):
        from threading import Thread
        def monitor_thread():
            self.monitor = CardMonitor()
            self.observer = _PCSCObserver(self.card_manager, self)
            self.monitor.addObserver(self.observer)
        t = Thread(target=monitor_thread, daemon=True)
        t.start()

    def shutdown(self):
        if self.monitor and self.observer:
            self.monitor.deleteObserver(self.observer)
        # Close any open connections on shutdown
        for conn in self.active_connections.values():
            try:
                conn.disconnect()
            except Exception:
                pass
        self.active_connections.clear()

    def send_apdu(self, apdu):
        """
        Send an APDU to the *currently selected* card/reader.
        Returns the response bytes, or b"" on failure.
        """
        try:
            if not self.active_connections:
                print("[PCSC] No active smartcard connection for APDU send.")
                return b""
            conn = list(self.active_connections.values())[0]
            data, sw1, sw2 = conn.transmit(list(apdu))
            resp = bytes(data) + bytes([sw1, sw2])
            print(f"[PCSC] APDU sent: {apdu.hex()} → {resp.hex()}")
            return resp
        except Exception as e:
            print(f"[PCSC] Error sending APDU: {e}")
            return b""

class _PCSCObserver(CardObserver):
    def __init__(self, card_manager, pcsc_reader):
        super().__init__()
        self.card_manager = card_manager
        self.pcsc_reader = pcsc_reader

    def update(self, observable, cards):
        added, removed = cards
        for card in added:
            try:
                reader_name = getattr(card, 'reader', 'Unknown Reader')
                conn = card.createConnection()
                try:
                    conn.connect()
                except Exception as e:
                    print(f"[PCSC] Could not connect to card in {reader_name}: {e}")
                    continue

                # Store active connection for APDU sending
                self.pcsc_reader.active_connections[reader_name] = conn

                # Extract ATR and possibly other metadata
                try:
                    atr = conn.getATR()
                    atr_str = toHexString(atr)
                except Exception as e:
                    atr = b''
                    atr_str = ''
                metadata = {
                    'reader': reader_name,
                    'atr': atr_str,
                    'insert_time': int(time.time())
                }

                # Create the EMVCard and assign extra metadata for UI/logging
                emv_card = EMVCard(conn)
                emv_card.reader = reader_name
                emv_card.atr = atr_str
                emv_card.insert_time = metadata['insert_time']

                if not emv_card.pan:
                    emv_card.pan = f"NO_PAN_{metadata['insert_time']}"
                    print("[DEBUG] Added card with NO PAN, dumping TLV tree:")
                    if hasattr(emv_card, "tlv_tree"):
                        def walk(node, depth=0):
                            print("  " * depth, f"Tag: {getattr(node, 'tag', '?')}, Value: {getattr(node, 'value', '')}, Desc: {getattr(node, 'description', '')}")
                            for c in getattr(node, "children", []):
                                walk(c, depth+1)
                        walk(emv_card.tlv_tree)
                # Signal to main thread for card insertion
                self.pcsc_reader.card_inserted_signal.emit(emv_card)
            except Exception as ex:
                print(f"[PCSC] Exception during card insertion: {ex}")

        for card in removed:
            reader_name = getattr(card, 'reader', None)
            if reader_name and reader_name in self.pcsc_reader.active_connections:
                try:
                    self.pcsc_reader.active_connections[reader_name].disconnect()
                except Exception:
                    pass
                del self.pcsc_reader.active_connections[reader_name]

            # Remove by PAN if known, else remove all as fallback
            pans = self.card_manager.list_all_cards()
            for pan in pans:
                self.card_manager.remove_card(pan)
