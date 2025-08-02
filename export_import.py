# =====================================================================
# File: export_import.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Export/import logic for card profiles, track data, APDU logs, and key databases.
#   - Supports JSON (pretty/compact/phone), CSV, robust error handling, deduplication, backup.
#   - Used by main window, dialogs, and all card management tools.
#
# Functions:
#   - ProfileExporter()
#       - export(card, filename, pretty=True)
#       - import_profile(filename)
#       - export_apdu_log(log, filename, csv_format=False)
#       - import_apdu_log(filename)
#       - export_all_cards(cards, filename, pretty=True, backup=True)
#       - import_all_cards(filename, merge=False)
#       - export_keys(keys_dict, filename, encrypt_password=None)
#       - import_keys(filename, decrypt_password=None)
#       - export_phone_payload(card, filename=None)
#       - import_phone_payload(payload)
#       - export_csv(cards, filename)
# =====================================================================

import json
import csv
import os
import shutil
import time
from emvcard import EMVCard

class ProfileExporter:
    def export(self, card, filename, pretty=True):
        """
        Export card profile as JSON. Optionally pretty (default) or compact.
        """
        try:
            data = card.export_profile()
            if not pretty:
                data = json.dumps(json.loads(data), separators=(',', ':'))
            with open(filename, "w", encoding="utf-8") as f:
                f.write(data)
            return True
        except Exception as e:
            print(f"[Export] Error: {e}")
            return False

    def import_profile(self, filename):
        """
        Import card profile from JSON file.
        Returns: EMVCard object or None (error).
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = f.read()
            card = EMVCard.import_profile_json(data)
            return card
        except Exception as e:
            print(f"[Import] Error: {e}")
            return None

    def export_apdu_log(self, log, filename, csv_format=False):
        """
        Export APDU log to text or CSV file.
        """
        try:
            if csv_format:
                with open(filename, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["APDU", "Response"])
                    for entry in log:
                        if isinstance(entry, (list, tuple)) and len(entry) == 2:
                            apdu, resp = entry
                            writer.writerow([apdu.hex() if hasattr(apdu,'hex') else str(apdu), resp.hex() if hasattr(resp,'hex') else str(resp)])
                        else:
                            writer.writerow([str(entry)])
            else:
                with open(filename, "w", encoding="utf-8") as f:
                    for entry in log:
                        if isinstance(entry, (list, tuple)) and len(entry) == 2:
                            apdu, resp = entry
                            line = f"APDU: {apdu.hex() if hasattr(apdu,'hex') else str(apdu)} | RESP: {resp.hex() if hasattr(resp,'hex') else str(resp)}"
                            f.write(line + "\n")
                        else:
                            f.write(f"{entry}\n")
            return True
        except Exception as e:
            print(f"[Export APDU Log] Error: {e}")
            return False

    def import_apdu_log(self, filename):
        """
        Import APDU log from text or CSV file.
        Returns: List of log entries.
        """
        entries = []
        try:
            if filename.endswith(".csv"):
                with open(filename, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    next(reader, None)
                    for row in reader:
                        entries.append(row)
            else:
                with open(filename, "r", encoding="utf-8") as f:
                    entries = [line.strip() for line in f.readlines()]
        except Exception as e:
            print(f"[Import APDU Log] Error: {e}")
        return entries

    def export_all_cards(self, cards, filename, pretty=True, backup=True):
        """
        Export all card profiles as a JSON list.
        If backup is True, saves a timestamped backup copy before overwriting.
        """
        try:
            profiles = []
            seen_pans = set()
            for card in cards:
                profile = json.loads(card.export_profile())
                pan = profile.get("applications", [{}])[0].get("pan", None)
                if pan and pan not in seen_pans:
                    profiles.append(profile)
                    seen_pans.add(pan)
            if backup and os.path.exists(filename):
                bak = f"{filename}.{time.strftime('%Y%m%d-%H%M%S')}.bak"
                shutil.copy(filename, bak)
            with open(filename, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(profiles, f, indent=2)
                else:
                    json.dump(profiles, f, separators=(',', ':'))
            return True
        except Exception as e:
            print(f"[Export All Cards] Error: {e}")
            return False

    def import_all_cards(self, filename, merge=False, existing_cards=None):
        """
        Import multiple card profiles from a JSON list file.
        Returns: List of EMVCard objects.
        If merge=True, only adds cards with unique PANs.
        """
        cards = []
        seen_pans = set(existing_cards) if existing_cards else set()
        try:
            with open(filename, "r", encoding="utf-8") as f:
                profiles = json.load(f)
            for profile in profiles:
                card = EMVCard(profile)
                pan = getattr(card, "pan", None) or card.get_cardholder_info().get("PAN", "")
                if not merge or (pan and pan not in seen_pans):
                    cards.append(card)
                    if pan:
                        seen_pans.add(pan)
            return cards
        except Exception as e:
            print(f"[Import All Cards] Error: {e}")
            return []

    def export_keys(self, keys_dict, filename, encrypt_password=None):
        """
        Export cryptographic keys as JSON, optionally encrypted (future).
        """
        try:
            # TODO: implement optional encryption
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(keys_dict, f, indent=2)
            return True
        except Exception as e:
            print(f"[Export Keys] Error: {e}")
            return False

    def import_keys(self, filename, decrypt_password=None):
        """
        Import cryptographic keys from JSON, optionally decrypted (future).
        Returns: dict.
        """
        try:
            # TODO: implement optional decryption
            with open(filename, "r", encoding="utf-8") as f:
                keys = json.load(f)
            return keys
        except Exception as e:
            print(f"[Import Keys] Error: {e}")
            return {}

    def export_phone_payload(self, card, filename=None):
        """
        Export a card profile in minimal JSON (BLE-friendly) for phone sync.
        Optionally writes to file; always returns JSON string.
        """
        try:
            profile = json.loads(card.export_profile())
            # Remove large/irrelevant fields, keep only core profile (PAN, expiry, track, keys)
            out = {
                "PAN": profile.get("applications", [{}])[0].get("pan", ""),
                "Expiry": profile.get("applications", [{}])[0].get("expiry", ""),
                "Tracks": profile.get("applications", [{}])[0].get("tracks", {}),
                "Keys":   profile.get("applications", [{}])[0].get("crypto_keys", {}),
            }
            payload = json.dumps(out, separators=(',', ':'))
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(payload)
            return payload
        except Exception as e:
            print(f"[Export Phone Payload] Error: {e}")
            return ""

    def import_phone_payload(self, payload):
        """
        Import a minimal card profile from phone BLE sync.
        Returns: EMVCard object or None.
        """
        try:
            if isinstance(payload, str):
                data = json.loads(payload)
            else:
                data = payload
            # Re-wrap in expected full-card structure for EMVCard
            profile = {
                "applications": [{
                    "pan": data.get("PAN", ""),
                    "expiry": data.get("Expiry", ""),
                    "tracks": data.get("Tracks", {}),
                    "crypto_keys": data.get("Keys", {}),
                    # Optionally, add dummy TLV data for minimal profile
                    "tlvs": [],
                }]
            }
            card = EMVCard(profile)
            return card
        except Exception as e:
            print(f"[Import Phone Payload] Error: {e}")
            return None

    def export_csv(self, cards, filename):
        """
        Export card data (PAN, Expiry, Track1, Track2, Cardholder) as CSV.
        """
        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["PAN", "Expiry", "Track1", "Track2", "Cardholder"])
                for card in cards:
                    app = card.applications[0] if getattr(card, "applications", []) else {}
                    writer.writerow([
                        app.get("pan", ""),
                        app.get("expiry", ""),
                        app.get("tracks", {}).get("56", ""),
                        app.get("tracks", {}).get("57", ""),
                        app.get("cardholder", "")
                    ])
            return True
        except Exception as e:
            print(f"[Export CSV] Error: {e}")
            return False
