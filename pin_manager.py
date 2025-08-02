# =====================================================================
# File: pin_manager.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Manages offline PIN verification, fail counter reset, PUK generation,
#   and PIN unblocking for cards that support it.
#
# Functions:
#   - PinManager()
#       - verify_pin(card, pin=None)
#       - reset_pin_counter(card)
#       - generate_puk(length=8)
#       - unblock_pin(card, puk=None, new_pin=None)
# =====================================================================

import random

class PinManager:
    def __init__(self):
        pass

    def verify_pin(self, card, pin=None):
        if pin is None:
            return "No PIN provided (use UI prompt to enter)."
        pin_str = str(pin)
        # ISO 9564 Format 2: PIN block, 8 bytes
        pin_block = bytearray.fromhex(f'2{len(pin_str)}{pin_str}FFFFFFFFFFFF')
        apdu = bytes.fromhex("0020008008") + pin_block
        resp = card.send_apdu(apdu)
        if resp and resp[-2:] == 0x90 and resp[-1] == 0x00:
            return "Offline PIN OK."
        elif resp and resp[-2:] == 0x63:
            tries_left = resp[-1] & 0x0F
            return f"PIN Incorrect. Tries left: {tries_left}"
        else:
            return f"PIN Verify failed: SW={resp[-2:].hex()}"

    def reset_pin_counter(self, card):
        # Graceful fallback
        return "Reset PIN counter: Not supported on this card (no EMV standard APDU)."

    def generate_puk(self, length=8):
        """
        Generate a random numeric PUK of specified length.
        Can be stored by user for test/dev cards.
        """
        return ''.join(random.choices("0123456789", k=length))

    def unblock_pin(self, card, puk=None, new_pin=None):
        """
        Attempt to unblock PIN using PUK, and set new PIN if possible.
        If PUK or new_pin is None, instruct UI to prompt user.
        Returns result string.
        """
        if puk is None or new_pin is None:
            return "PUK or new PIN not provided (use UI prompt to enter)."

        puk_str = str(puk)
        new_pin_str = str(new_pin)
        # ISO 9564 Format 2 for PUK block and PIN block, both 8 bytes
        puk_block = bytearray.fromhex(f'2{len(puk_str)}{puk_str}FFFFFFFFFFFF')
        pin_block = bytearray.fromhex(f'2{len(new_pin_str)}{new_pin_str}FFFFFFFFFFFF')
        unblock_apdu = bytes.fromhex("002C0000") + bytes([len(puk_block) + len(pin_block)]) + puk_block + pin_block
        resp = card.send_apdu(unblock_apdu)
        if resp and resp[-2:] == 0x90 and resp[-1] == 0x00:
            return "PIN unblocked and changed successfully."
        elif resp and resp[-2:] == 0x63:
            tries_left = resp[-1] & 0x0F
            return f"PUK Incorrect. Tries left: {tries_left}"
        else:
            return f"PIN unblock failed: SW={resp[-2:].hex()}"
