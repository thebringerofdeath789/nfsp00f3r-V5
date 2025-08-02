# =====================================================================
# File: pdol.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Robust, universal PDOL builder/parser for any EMV-compliant PDOL.
#   Handles variable-length tags and values (all EMV/ISO7816 cases).
#   Fills all tags with valid, realistic values based on EMV spec,
#   rfidiot, talktoyourcreditcard, and field dumps.
#
# Functions:
#   - build_pdol(pdol_template, terminal_data)
# =====================================================================

import random
import datetime

def parse_emv_tag(data, idx):
    """
    Parse variable-length EMV/ISO tag from data starting at idx.
    Returns (tag_bytes, new_idx)
    """
    tag = bytearray([data[idx]])
    idx += 1
    if (tag[0] & 0x1F) == 0x1F:
        while data[idx] & 0x80:
            tag.append(data[idx])
            idx += 1
        tag.append(data[idx])
        idx += 1
    return bytes(tag), idx

def pdol_value(tag, length):
    """
    Return a valid value for a given PDOL tag, as per EMV spec, or as used in rfidiot/talktoyourcreditcard.
    All values are bytes and will be truncated/padded as needed.
    """
    today = datetime.datetime.now()
    # Use random.randbytes if available (Python 3.9+), else fallback
    randbytes = (lambda l: random.randbytes(l)) if hasattr(random, "randbytes") else (lambda l: bytes(random.getrandbits(8) for _ in range(l)))
    mapping = {
        # Transaction/amount/currency/country
        '9F66': lambda: b'\x37\x00\x40\x00'[:length],      # TTQ
        '9F02': lambda: b'\x00'*(length-1)+b'\x01',        # Amount, Authorised: $0.01
        '9F03': lambda: b'\x00'*length,                    # Amount, Other
        '9F1A': lambda: b'\x08\x40'[:length],              # Terminal Country Code (USA)
        '5F2A': lambda: b'\x08\x40'[:length],              # Transaction Currency Code (USD)
        '9F15': lambda: b'0000'[:length],                  # Merchant Category Code
        '9F1E': lambda: b'12345678'[:length],              # IFM Serial Number
        # Date/time/sequence
        '9A':   lambda: today.strftime("%y%m%d").encode() if length==3 else b'\x00'*length,    # YYMMDD
        '9F21': lambda: today.strftime("%H%M%S").encode() if length==3 else b'\x00'*length,    # HHMMSS
        # CVM, TVR, TSI, UN, ATC, AIP, AFL, etc.
        '95':   lambda: b'\x00'*length,                    # TVR
        '9F34': lambda: b'\x1E\x03\x02'[:length],          # CVM Results
        '9F36': lambda: b'\x00\x01'[:length],              # ATC
        '9F10': lambda: b'\x07\x01\x03\xA0\x00\x10\x01'[:length],  # Issuer App Data
        '9F13': lambda: b'\x00'*length,                    # Last Online ATC Register
        '9F07': lambda: b'\xFF\x00\x00\x00'[:length],      # App Usage Control
        '9F6E': lambda: b'\x00'*length,                    # Third Party Data
        # Terminal/merchant
        '9F35': lambda: b'\x22'[:length],                  # Terminal Type
        '9F33': lambda: b'\xE0\xF8\xC8'[:length],          # Terminal Capabilities
        '9F40': lambda: b'\x60\x00\xF0\xA0'[:length],      # Additional Terminal Capabilities
        '9F09': lambda: b'\x00\x96'[:length],              # App Version No (Visa)
        '9F16': lambda: b'MERCHANTNAME'.ljust(length, b' '), # Merchant Name
        '9F4E': lambda: b'MERCHANTNAME'.ljust(length, b' '), # Merchant Name/Location
        '9F4F': lambda: b'\x00'*length,                    # Log Format
        # Transaction meta
        '9C':   lambda: b'\x00'*length,                    # Transaction Type
        '9F37': lambda: randbytes(length),                 # Unpredictable Number
        '9F7A': lambda: b'\x01\x00'[:length],              # Upper Consecutive Offline Limit
        '9F6C': lambda: b'\x00'*length,                    # Magstripe App Version
        '9F6B': lambda: b'1234567890123456D22122011234567890F'[:length],   # Track 2 Data (dummy)
        '9F74': lambda: b'\x00'*length,                    # VSDC Offline Data Authentication
        '9F6D': lambda: b'\x00'*length,                    # MSD Extended Data
        # Cardholder/issuer/ICS
        '5F34': lambda: b'\x01'[:length],                  # PAN Sequence Number
        '5F36': lambda: b'\x02'[:length],                  # Currency Exponent
        '9F12': lambda: b'CARDLABEL'.ljust(length, b' '),  # App Preferred Name
        '50':   lambda: b'CARDLABEL'.ljust(length, b' '),  # Application Label
        '9F17': lambda: b'\x00'*length,                    # PIN Try Counter
        '9F11': lambda: b'\x01\x00'[:length],              # Issuer Code Table Index
        # Rare/other
        '9F22': lambda: b'\x00\x01'[:length],              # CA Public Key Index
        '9F23': lambda: b'\x00\x01'[:length],              # Upper Consecutive Offline Limit
        '9F25': lambda: b'\x00'*length,                    # Last 4 Digits of PAN
        '9F26': lambda: b'\x00'*length,                    # Application Cryptogram
        '9F27': lambda: b'\x80'[:length],                  # Cryptogram Information Data
        '9F32': lambda: b'\x00\x00\x00'[:length],          # Issuer Public Key Exponent
        '9F41': lambda: b'\x00\x01'[:length],              # Transaction Sequence Counter
        '9F45': lambda: b'\x00'*length,                    # Data Authentication Code
        '9F47': lambda: b'\x03'[:length],                  # ICC Public Key Exponent
        '9F53': lambda: b'\x00'*length,                    # Transaction Category Code
        '9F5C': lambda: b'\x00'*length,                    # CVC3 (Magstripe)
        '9F5D': lambda: b'\x00'*length,                    # Available Offline Spending Amount
        '9F5E': lambda: b'\x00'*length,                    # Digital Signature
        '9F51': lambda: b'\x00'*length,                    # Application Currency Code
        '9F57': lambda: b'\x00'*length,                    # Issuer Country Code
        '9F5B': lambda: b'\x00'*length,                    # Issuer Script Template 1
        '9F5F': lambda: b'\x00'*length,                    # Issuer Script Template 2
        '9F7C': lambda: b'\x00'*length,                    # Merchant Custom Data
        # Fallback
    }
    return mapping.get(tag, lambda: b'\x00'*length)()

def build_pdol(pdol_template, terminal_data):
    """
    Build GPO PDOL from template and terminal_data.
    - pdol_template: bytes (from 9F38 TLV value)
    - terminal_data: dict mapping tag string (e.g. '9F02') to bytes value (manual override)
    Returns: bytes to use in GPO APDU.
    """
    pdol_data = b""
    idx = 0
    while idx < len(pdol_template):
        tag_bytes, idx2 = parse_emv_tag(pdol_template, idx)
        idx = idx2
        length = pdol_template[idx]
        idx += 1
        tag_str = tag_bytes.hex().upper()
        # Prefer manual override, else generate correct default
        val = terminal_data.get(tag_str, None)
        if val is None:
            val = pdol_value(tag_str, length)
        if len(val) < length:
            val += b"\x00" * (length - len(val))
        pdol_data += val[:length]
    return pdol_data
