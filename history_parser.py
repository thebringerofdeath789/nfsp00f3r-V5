# =====================================================================
# File: history_parser.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Parses transaction history/log entries from EMV card records.
#   - Reads log entry SFI and extracts log entries using standard EMV logic.
#   - Converts raw log entries to human-readable transaction events.
#
# Functions:
#   - parse_log_entries(card)
#   - parse_log_record(tlv_tree)
# =====================================================================

from tlv import TLVParser
from tag_dict import TagDict

def parse_log_entries(card):
    """
    Read transaction history using log entry SFI, return as list of dicts.
    """
    # Find log entry SFI (tag 9F4D, format: <SFI:1 byte><#records:1 byte>)
    log_entry = card.extract_tag('9F4D')
    if not log_entry or len(log_entry) < 4:
        return []
    sfi = int(log_entry[:2], 16)
    num_records = int(log_entry[2:], 16)
    records = []
    for rec in range(1, num_records + 1):
        apdu = bytes.fromhex(f"00B2{rec:02X}{(sfi<<3)|4:02X}00")
        resp = card.send_apdu(apdu)
        if resp and resp[-2:] == b"\x90\x00":
            tlvs = TLVParser(TagDict()).parse(resp)
            tx = parse_log_record(tlvs)
            tx['raw'] = resp.hex()
            tx['rec'] = rec
            records.append(tx)
    return records

def parse_log_record(tlv_tree):
    """
    Convert a parsed TLV record (usually one log entry) to readable dict.
    Maps common log tags (amount, date, type, etc).
    """
    result = {}
    def walk(nodes):
        for node in nodes:
            tag = node['tag']
            value = node['value']
            if tag == '9A':  # Transaction Date
                result['date'] = value
            elif tag == '9C':  # Transaction Type
                result['type'] = value
            elif tag == '9F02':  # Amount, Authorised (numeric)
                result['amount'] = int(value, 16)
            elif tag == '5F2A':  # Currency code
                result['currency'] = value
            elif tag == '9F36':  # ATC
                result['atc'] = value
            elif tag == '9F27':  # Cryptogram Info Data
                result['cryptogram_type'] = value
            elif tag == '9F10':  # Issuer Application Data
                result['issuer_app_data'] = value
            # Recurse for children
            if node.get('children'):
                walk(node['children'])
    walk(tlv_tree)
    return result
