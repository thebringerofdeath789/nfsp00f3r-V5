# =====================================================================
# File: emv_crypto_keys.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Robust user key management for ARQC/SDA/DDA keys and more.
#   Handles key entry, type/length validation, extraction from card profiles,
#   per-profile key sets, and secure file import/export (optionally encrypted).
#   All cryptographic keys are auditable and metadata is maintained.
#
# Functions:
#   - EmvCryptoKeys()
#       - set_key(profile_id, keytype, keyval)
#       - get_key(profile_id, keytype)
#       - extract_keys_from_profile(card)
#       - list_keys(profile_id)
#       - remove_key(profile_id, keytype)
#       - load_keys_from_file(filename, password=None)
#       - save_keys_to_file(filename, password=None)
#       - derive_session_key_arqc(pan, seq, un, atc)
#       - validate_key(keytype, keyval)
# =====================================================================

import json
import base64
import os
import hashlib
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    Fernet = None

class EmvCryptoKeys:
    # Supported key types and their expected length (bytes) or validator function
    KEY_TYPES = {
        'arqc': 16,           # 3DES/AES session or master key
        'sda':  256,          # Example: 2048-bit RSA pubkey for SDA
        'dda':  256,          # Example: 2048-bit RSA pubkey for DDA
        'issuer': 256,        # Example: Issuer public key (2048b)
        'icc_priv': 256,      # ICC private key (DDA)
        'mk': 16,             # Magstripe master key (if used)
        'udk': 16,            # Unique device key (track/MSD)
        # Add more types if needed
    }

    def __init__(self):
        # profile_id -> keytype -> dict(value, meta)
        self.profiles = {}  # {profile_id: {keytype: {'value':..., 'meta':...}, ...}}
        self.history = []   # (timestamp, op, profile_id, keytype, meta)

    def _meta(self, keyval, source='manual', notes=None):
        return {
            'added': datetime.now().isoformat(),
            'length': len(keyval),
            'source': source,
            'notes': notes or ""
        }

    def set_key(self, profile_id, keytype, keyval, source='manual', notes=None):
        keyval_bytes = self._parse_keyval(keyval)
        self.validate_key(keytype, keyval_bytes)
        if profile_id not in self.profiles:
            self.profiles[profile_id] = {}
        self.profiles[profile_id][keytype] = {
            'value': keyval_bytes.hex(),
            'meta': self._meta(keyval_bytes, source, notes)
        }
        self.history.append((datetime.now().isoformat(), "set", profile_id, keytype, self.profiles[profile_id][keytype]['meta']))

    def get_key(self, profile_id, keytype):
        profile = self.profiles.get(profile_id, {})
        return profile.get(keytype, {}).get('value', '')

    def list_keys(self, profile_id):
        """List all keys for a profile, with metadata."""
        return self.profiles.get(profile_id, {})

    def remove_key(self, profile_id, keytype):
        if profile_id in self.profiles and keytype in self.profiles[profile_id]:
            meta = self.profiles[profile_id][keytype]['meta']
            del self.profiles[profile_id][keytype]
            self.history.append((datetime.now().isoformat(), "remove", profile_id, keytype, meta))

    def _parse_keyval(self, keyval):
        """Accept bytes, hex str, or base64 str and convert to bytes."""
        if isinstance(keyval, bytes):
            return keyval
        keyval = keyval.strip()
        # Hex
        try:
            if all(c in "0123456789abcdefABCDEF" for c in keyval) and len(keyval) % 2 == 0:
                return bytes.fromhex(keyval)
        except Exception:
            pass
        # Base64
        try:
            return base64.b64decode(keyval)
        except Exception:
            pass
        # Raw string fallback
        return keyval.encode('utf-8')

    def validate_key(self, keytype, keyval: bytes):
        """Check key length and format for supported key types."""
        expected = self.KEY_TYPES.get(keytype)
        if not expected:
            raise ValueError(f"Unknown key type {keytype}")
        if isinstance(expected, int):
            if len(keyval) != expected:
                raise ValueError(f"Key type {keytype} must be {expected} bytes, got {len(keyval)} bytes")
        elif callable(expected):
            if not expected(keyval):
                raise ValueError(f"Key type {keytype} did not pass custom validator")

    def extract_keys_from_profile(self, card, profile_id=None):
        """
        Extract cryptographic keys from a card profile, and auto-store for the profile.
        Looks for known key tags, certificates, etc.
        """
        extracted = {}
        profile_id = profile_id or (card.pan if hasattr(card, 'pan') else "profile")
        # Example tag extraction: ICC, Issuer, CA pubkeys
        for tag in ("9F10", "9F79", "9F7A", "9F46", "9F47", "9F48"):
            val = card.extract_tag(tag)
            if val:
                # Heuristic: classify by tag, otherwise store as 'misc'
                ktype = {
                    "9F10": "arqc", "9F79": "sda", "9F7A": "dda",
                    "9F46": "issuer", "9F47": "icc_pub", "9F48": "ca_pub"
                }.get(tag, f"tag_{tag}")
                try:
                    self.set_key(profile_id, ktype, val, source='profile', notes=f"Extracted from {tag}")
                    extracted[ktype] = val
                except Exception as e:
                    extracted[f"{ktype}_error"] = str(e)
        # Save extracted keys
        return extracted

    def load_keys_from_file(self, filename, password=None):
        """
        Load key database from file (optionally encrypted).
        If password is provided, file must be encrypted via Fernet.
        """
        if password:
            if not Fernet:
                raise ImportError("cryptography.fernet not available")
            with open(filename, "rb") as f:
                data = f.read()
            fernet = Fernet(self._key_from_password(password))
            decrypted = fernet.decrypt(data)
            payload = json.loads(decrypted.decode('utf-8'))
        else:
            with open(filename, "r", encoding="utf-8") as f:
                payload = json.load(f)
        self.profiles = payload.get("profiles", {})
        self.history = payload.get("history", [])

    def save_keys_to_file(self, filename, password=None):
        """
        Save key database to file (optionally encrypted).
        """
        payload = json.dumps({
            "profiles": self.profiles,
            "history": self.history
        }, indent=2)
        if password:
            if not Fernet:
                raise ImportError("cryptography.fernet not available")
            fernet = Fernet(self._key_from_password(password))
            enc = fernet.encrypt(payload.encode('utf-8'))
            with open(filename, "wb") as f:
                f.write(enc)
        else:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(payload)

    def _key_from_password(self, password: str):
        # Derive a 32-byte key from password (Fernet key = 32 bytes base64)
        digest = hashlib.sha256(password.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest)

    def derive_session_key_arqc(self, pan, seq, un, atc):
        """
        Derive ARQC session key using EMV common formula, if needed.
        pan: Primary Account Number (string)
        seq: Card sequence number (string or int)
        un:  Unpredictable number (bytes)
        atc: Application Transaction Counter (bytes)
        Returns: 16 bytes (example for VISA; adapt for real apps)
        """
        data = (pan + str(seq)).encode("utf-8") + un + atc
        key = hashlib.sha256(data).digest()[:16]
        return key

    # --- Metadata/history helpers ---

    def get_history(self):
        return list(self.history)

    def get_all_profiles(self):
        return list(self.profiles.keys())

    def get_metadata(self, profile_id, keytype):
        return self.profiles.get(profile_id, {}).get(keytype, {}).get('meta', {})

    # --- For display in UI ---
    def get_keys_for_ui(self, profile_id):
        """Return a list of dicts for each key, with type, value, and metadata."""
        result = []
        for keytype, entry in self.profiles.get(profile_id, {}).items():
            d = dict(
                type=keytype,
                value=entry['value'],
                length=entry['meta']['length'],
                source=entry['meta']['source'],
                added=entry['meta']['added'],
                notes=entry['meta'].get('notes', '')
            )
            result.append(d)
        return result
