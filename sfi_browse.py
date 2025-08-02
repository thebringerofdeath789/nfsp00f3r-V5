# =====================================================================
# File: sfi_browse.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   SFI (Short File Identifier) record browser and helper.
#   - Allows browsing all SFI/application records for an EMV card.
#   - Supports full parsing of all SFI/record combinations.
#   - Can list available SFIs, their records, and parse to TLV.
#
# Functions:
#   - list_sfis(card)
#   - read_all_sfi_records(card, sfi)
#   - get_all_records(card)
# =====================================================================

from tlv import TLVParser
from tag_dict import TagDict

def list_sfis(card):
    """
    Attempt to list all available SFI on the card (by probing known range).
    Returns: [sfi_number (int), ...]
    """
    available = []
    for sfi in range(1, 32):  # SFI is 5 bits, so 1-31
        found = False
        for rec in range(1, 17):  # Most SFIs have max 16 records
            apdu = bytes.fromhex(f"00B2{rec:02X}{(sfi<<3)|4:02X}00")
            resp = card.send_apdu(apdu)
            if resp and resp[-2:] == b"\x90\x00":
                found = True
                break
        if found:
            available.append(sfi)
    return available

def read_all_sfi_records(card, sfi):
    """
    Read all available records for given SFI.
    Returns: [bytes, ...] (raw record data)
    """
    records = []
    for rec in range(1, 17):
        apdu = bytes.fromhex(f"00B2{rec:02X}{(sfi<<3)|4:02X}00")
        resp = card.send_apdu(apdu)
        if resp and resp[-2:] == b"\x90\x00":
            records.append(resp)
        else:
            break
    return records

def get_all_records(card):
    """
    Reads and parses all SFI/record pairs for the card,
    returns TLV trees per record.
    """
    tlv_parser = TLVParser(TagDict())
    all_records = []
    for sfi in list_sfis(card):
        recs = read_all_sfi_records(card, sfi)
        for rec in recs:
            try:
                tlvs = tlv_parser.parse(rec)
                all_records.append({
                    "sfi": sfi,
                    "raw": rec.hex(),
                    "tlv": tlvs
                })
            except Exception as e:
                all_records.append({
                    "sfi": sfi,
                    "raw": rec.hex(),
                    "tlv": [],
                    "error": str(e)
                })
    return all_records
