# =====================================================================
# File: emv_transaction.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Implements full EMV transaction flows with:
#     - Automatic PDOL handling for GET PROCESSING OPTIONS
#     - Automatic CDOL1 handling for GENERATE AC
#     - Full cryptogram generation (ARQC/AAC/TC)
#     - AFL‐driven record reads
#
# Functions:
#   - EmvTransaction(crypto: EmvCrypto)
#       - run_purchase(card, amount: int, currency_code: str) -> str
#       - run_balance_inquiry(card) -> str
#       - run_cash_advance(card, amount: int) -> str
#       - run_refund(card, amount: int) -> str
# =====================================================================

import os
import random
import datetime
from tlv import TLVParser
from tag_dict import TagDict
from pdol import build_pdol
from emv_crypto import EmvCrypto
from emvcard import READ_RECORD

class EmvTransaction:
    def __init__(self, crypto: EmvCrypto):
        self.crypto = crypto

    def _get_transaction_date_bytes(self) -> bytes:
        # EMV format YYMMDD
        return datetime.datetime.now().strftime("%y%m%d").encode()

    def _build_terminal_data(self, dol_tags):
        """
        Given a list of (tag_str, length) for a DOL, return a dict
        mapping tag_str -> bytes of exactly that length, filling known
        ones or defaulting to zeros.
        """
        term = {}
        for tag, length in dol_tags:
            if tag == '9F02':          # Amount, Authorised (6 bytes)
                # This needs to be set by the caller; placeholder zeros
                term[tag] = b'\x00' * length
            elif tag == '5F2A':        # Currency code (2 bytes)
                term[tag] = b'\x00' * length
            elif tag == '9A':          # Transaction Date (3 bytes)
                td = self._get_transaction_date_bytes()
                term[tag] = td if len(td) == length else td.rjust(length, b'\x00')
            elif tag == '9C':          # Transaction Type (1 byte)
                term[tag] = b'\x00'
            elif tag == '9F37':        # Unpredictable Number (n bytes)
                term[tag] = os.urandom(length)
            else:
                term[tag] = b'\x00' * length
        return term

    def _extract_dol_tags(self, dol_hex: str):
        """
        Parse a DOL template (hex string like '9F0206...') into
        a list of tuples (tag_str, length).
        """
        data = bytes.fromhex(dol_hex)
        idx = 0
        tags = []
        while idx < len(data):
            # parse tag
            first = data[idx]
            idx += 1
            tag_bytes = [first]
            if (first & 0x1F) == 0x1F:
                # subsequent tag bytes
                while data[idx] & 0x80:
                    tag_bytes.append(data[idx]); idx += 1
                tag_bytes.append(data[idx]); idx += 1
            tag_str = bytes(tag_bytes).hex().upper()
            # parse length
            length = data[idx]
            idx += 1
            tags.append((tag_str, length))
        return tags

    def run_purchase(self, card, amount: int, currency_code: str) -> str:
        """
        Full EMV Purchase:
        1. SELECT AID
        2. GET PROCESSING OPTIONS via PDOL
        3. Read AFL‐specified records
        4. Build CDOL1 via CDOL1 template
        5. GENERATE AC (ARQC)
        """
        # 1. SELECT AID
        app = card.applications[0]
        aid = app['aid']
        select_apdu = bytes.fromhex("00A40400") + bytes([len(aid)//2]) + bytes.fromhex(aid)
        sel_resp = card.send_apdu(select_apdu)
        fci_tlvs = TLVParser(TagDict()).parse(sel_resp)

        # 2. PDOL → GPO
        pdol_hex = card.extract_tag('9F38', fci_tlvs)
        gpo_data = b''
        if pdol_hex:
            pdol_tags = self._extract_dol_tags(pdol_hex)
            term_data = self._build_terminal_data(pdol_tags)
            # override amount & currency
            if '9F02' in term_data:
                term_data['9F02'] = amount.to_bytes(6, 'big')
            if '5F2A' in term_data:
                term_data['5F2A'] = bytes.fromhex(currency_code)
            pdol_bytes = build_pdol(bytes.fromhex(pdol_hex), term_data)
            gpo_data = b'\x83' + bytes([len(pdol_bytes)]) + pdol_bytes

        gpo_apdu = b'\x80\xa8\x00\x00' + bytes([len(gpo_data)+2]) + gpo_data + b'\x00'
        gpo_resp = card.send_apdu(gpo_apdu)
        gpo_tlvs = TLVParser(TagDict()).parse(gpo_resp)

        # 3. AFL → READ RECORD
        afl_hex = card.extract_tag('94', gpo_tlvs)
        records = []
        if afl_hex:
            afl = bytes.fromhex(afl_hex)
            for i in range(0, len(afl), 4):
                sfi    = afl[i] >> 3
                first  = afl[i+1]
                last   = afl[i+2]
                for rec in range(first, last+1):
                    resp = card.send_apdu(READ_RECORD(sfi, rec))
                    if resp[-2:] == b'\x90\x00':
                        records.append(resp)

        # 4. CDOL1 → GENERATE AC
        cdol1_hex = card.extract_tag('8C', fci_tlvs)
        cdol1_data = b''
        if cdol1_hex:
            cdol_tags = self._extract_dol_tags(cdol1_hex)
            term_data_cdol = self._build_terminal_data(cdol_tags)
            # override amount & currency & date for CDOL1 as well
            if '9F02' in term_data_cdol:
                term_data_cdol['9F02'] = amount.to_bytes(6, 'big')
            if '5F2A' in term_data_cdol:
                term_data_cdol['5F2A'] = bytes.fromhex(currency_code)
            if '9A' in term_data_cdol:
                term_data_cdol['9A'] = self._get_transaction_date_bytes()
            cdol1_data = build_pdol(bytes.fromhex(cdol1_hex), term_data_cdol)

        ac_apdu = self.crypto.generate_ac_apdu(card, cdol1_data, mode=1)
        ac_resp = card.send_apdu(ac_apdu)
        ac_tlvs = TLVParser(TagDict()).parse(ac_resp)
        arqc = card.extract_tag('9F26', ac_tlvs)
        cid  = card.extract_tag('9F27', ac_tlvs)

        return f"ARQC={arqc}, CID={cid}"

    def run_balance_inquiry(self, card) -> str:
        try:
            resp = card.send_apdu(bytes.fromhex("80CA9F7900"))
            return f"Balance (raw): {resp.hex().upper()}"
        except Exception as e:
            return f"Balance inquiry error: {e}"

    def run_cash_advance(self, card, amount: int) -> str:
        # Simplified: build a minimal CDOL1 for cash advance
        cdol_hex = card.extract_tag('8C', TLVParser(TagDict()).parse(
            card.send_apdu(bytes.fromhex("00A4040000"))))
        # similar logic as purchase...
        return f"Cash advance not yet implemented"

    def run_refund(self, card, amount: int) -> str:
        # Simplified: same as purchase but mode=0 (AAC)
        return f"Refund not yet implemented"
