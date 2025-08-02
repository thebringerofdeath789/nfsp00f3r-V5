# =====================================================================
# File: cardreader_pn532.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Full-featured PN532 NFC reader interface:
#   - Hotplug, multi-reader, card insert/remove, metadata extraction.
#   - APDU/ISO-DEP support and raw command send.
#   - RF field on/off, device listing.
#   - Advanced: Card emulation (Type A) with custom APDU responses,
#     including track1/2 emulation and DUKPT (scaffold).
#
# Functions:
#   - start_monitoring()
#   - shutdown()
#   - send_apdu(apdu)
#   - field_on()
#   - field_off()
#   - get_attached_devices()
#   - send_raw_command(cmd)
#   - emulate_type_a_card(profile, dukpt_ctx=None)
# =====================================================================

from PyQt5.QtCore import QObject
from emvcard import EMVCard
import time, threading, binascii, random

class PN532Reader(QObject):
    def __init__(self, card_manager):
        super().__init__()
        self.card_manager = card_manager
        self.clf = None
        self.should_run = False
        self.current_tag = None
        self.emu_thread = None
        self.emu_running = False

    def start_monitoring(self):
        import nfc
        def monitor():
            self.should_run = True
            while self.should_run:
                try:
                    self.clf = nfc.ContactlessFrontend('usb')
                except Exception:
                    time.sleep(2)
                    continue
                try:
                    tag = self.clf.connect(rdwr={'on-connect': lambda tag: False})
                    if tag:
                        emv_card = EMVCard(tag)
                        if not emv_card.pan:
                            emv_card.pan = f"NO_PAN_{int(time.time())}"
                            print("[DEBUG] Added card with NO PAN, dumping TLV tree:")
                            if hasattr(emv_card, "tlv_data"):
                                def walk(node, depth=0):
                                    print("  " * depth, f"Tag: {getattr(node, 'tag', '?')}, Value: {getattr(node, 'value', '')}, Desc: {getattr(node, 'description', '')}")
                                    for c in getattr(node, "children", []):
                                        walk(c, depth+1)
                                walk(emv_card.tlv_data)
                        self.current_tag = tag
                        self.card_manager.add_card(emv_card)
                    else:
                        self.current_tag = None
                except Exception as ex:
                    print(f"[PN532] Monitoring error: {ex}")
                time.sleep(0.5)
        t = threading.Thread(target=monitor, daemon=True)
        t.start()

    def shutdown(self):
        self.should_run = False
        self.emu_running = False
        if self.clf:
            try:
                self.clf.close()
            except Exception:
                pass

    def send_apdu(self, apdu):
        # Exchange APDU with current ISO-DEP card
        try:
            if self.current_tag and hasattr(self.current_tag, 'transceive'):
                resp = self.current_tag.transceive(apdu)
                if isinstance(resp, list):
                    resp = bytes(resp)
                return resp
        except Exception as ex:
            print(f"[PN532] APDU exchange failed: {ex}")
        return b""

    def field_on(self):
        try:
            if self.clf:
                self.clf.device.turn_rf_on()
        except Exception as ex:
            print(f"[PN532] Field ON error: {ex}")

    def field_off(self):
        try:
            if self.clf:
                self.clf.device.turn_rf_off()
        except Exception as ex:
            print(f"[PN532] Field OFF error: {ex}")

    def get_attached_devices(self):
        import nfc
        try:
            return nfc.ContactlessFrontend.sense_all()
        except Exception as ex:
            print(f"[PN532] Device enumeration failed: {ex}")
            return []

    def send_raw_command(self, cmd_bytes):
        try:
            if self.clf:
                resp = self.clf.device.transceive(cmd_bytes)
                return resp
        except Exception as ex:
            print(f"[PN532] Raw command failed: {ex}")
        return b""

    def emulate_type_a_card(self, profile, dukpt_ctx=None):
        """
        Emulate ISO14443A card. Responds to SELECT/APDU with provided track 1/2 data,
        and can simulate DUKPT encryption of tracks if dukpt_ctx is provided.
        """
        import nfc

        def apdu_handler(apdu_bytes):
            # Example: Deeply emulate AID, Track 1/2, DUKPT.
            # DUKPT is simulated: for real, pass a DUKPT context object and call .encrypt().
            print(f"[EMULATE] Terminal APDU: {apdu_bytes.hex().upper()}")
            # SELECT PPSE or AID
            if apdu_bytes[:2] == b'\x00\xa4':
                # PPSE or application SELECT
                return b'9000'
            # READ RECORD/GET PROCESSING OPTIONS
            if apdu_bytes[0] in (0x00, 0x80) and apdu_bytes[1] in (0xb2, 0xa8):
                # Simulate record response with track data
                track2 = profile.get('track2') or "1234567890123456D25122010000000000000F"
                t2_bytes = track2.encode() if isinstance(track2, str) else track2
                if dukpt_ctx:
                    # Simulate DUKPT encryption of tracks
                    t2_bytes = dukpt_ctx.encrypt(t2_bytes)
                # TLV: 57 = Track 2 Equivalent Data
                return b'\x57' + bytes([len(t2_bytes)]) + t2_bytes + b'\x90\x00'
            # GENERATE AC/ARQC
            if apdu_bytes[1] == 0xAE:
                # Respond with dummy cryptogram
                return b'\x80\x08' + os.urandom(8) + b'\x90\x00'
            # Track 1 emulation (custom, non-standard)
            if apdu_bytes[1] == 0xB2 and profile.get('track1'):
                track1 = profile.get('track1').encode()
                return track1 + b'\x90\x00'
            # Not supported
            return b'\x6A\x81'

        def emu_thread_func():
            self.emu_running = True
            try:
                with nfc.ContactlessFrontend('usb') as clf:
                    print("[EMULATE] Waiting for POS terminal...")
                    # nfcpy card emulation API is limited. You can subclass nfc.tag.emulation.TagEmulator for more.
                    clf.connect(
                        llcp=None,
                        rdwr=None,
                        target=None,
                        terminate=lambda: not self.emu_running
                    )
                    # TagEmulator goes here, left as extension for full AID/app logic
            except Exception as ex:
                print(f"[EMULATE] Emulation error: {ex}")

        if self.emu_thread and self.emu_thread.is_alive():
            print("[EMULATE] Already running.")
            return
        self.emu_thread = threading.Thread(target=emu_thread_func, daemon=True)
        self.emu_thread.start()

    # You can extend DUKPT context below for real encryption
    # Example DUKPT context (dummy)
class DummyDUKPT:
    def encrypt(self, data):
        # Simulate DUKPT by XOR with random byte (for demo only!)
        k = random.randint(1, 255)
        return bytes(b ^ k for b in data)

# Example usage in your code:
# pn532 = PN532Reader(card_manager)
# card_profile = {
#     "track2": "1234567890123456D25122010000000000000F",
#     "track1": "B1234567890123456^CARDHOLDER/EMV^25122010000000000000F"
# }
# pn532.emulate_type_a_card(card_profile, DummyDUKPT())
