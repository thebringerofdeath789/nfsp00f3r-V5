# =====================================================================
# File: magstripe.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Magstripe/MSD logic. Extracts tracks from card, decodes them,
#   and prepares data for export and MSR emulation.
#
# Functions:
#   - MagstripeEmulator()
#       - extract_tracks(card)
#       - parse_track1(track1)
#       - parse_track2(track2)
#       - normalize_track(track, trackno)
#       - lrc(data)
#       - emulate(card)
#       - save_to_file(track_data, filename)
#       - export_tracks_bin(track_data, filename)
#       - export_tracks_tlv(track_data)
#       - detect_jis2(track1)
#       - replay(card_or_trackdata, saved_list=None)
# =====================================================================

import json
import re
import hmac
import hashlib
import os

class MagstripeEmulator:
    def __init__(self):
        pass

    def extract_tracks(self, card):
        tracks = {}
        tag_map = {"56": "track1", "57": "track2", "9F6B": "track2_equiv"}
        for tag, name in tag_map.items():
            v = card.extract_tag(tag)
            if v:
                tracks[name] = v

        # Scan TLVs for extra track-like data
        track1_pat = re.compile(r"%?B\d{12,19}\^[^\^]*\^\d{4}\d{3}[^\?]*\??")
        track2_pat = re.compile(r";?\d{12,19}=\d{4}\d{3}[^\?]*\??")
        found_track1 = tracks.get("track1", "")
        found_track2 = tracks.get("track2", "") or tracks.get("track2_equiv", "")

        for node in self._walk_tlv_tree(getattr(card, "tlv_tree", [])):
            val = node.get('value', '')
            if isinstance(val, str):
                if not found_track1 and track1_pat.match(val):
                    tracks["track1_auto"] = val
                    found_track1 = val
                if not found_track2 and track2_pat.match(val):
                    tracks["track2_auto"] = val
                    found_track2 = val
        return tracks

    def _walk_tlv_tree(self, tlvs):
        for n in tlvs:
            if isinstance(n, dict):
                yield n
                children = n.get('children', [])
                if children:
                    yield from self._walk_tlv_tree(children)

    def parse_track1(self, track1):
        track1 = track1.rstrip('F')
        pattern = r"^%?B(\d{12,19})\^([^\^]*)\^(\d{4})(\d{3})([^\?]*)\??"
        m = re.match(pattern, track1)
        if m:
            return {
                "PAN": m.group(1),
                "Name": m.group(2).strip(),
                "Expiry": m.group(3),
                "ServiceCode": m.group(4),
                "DiscretionaryData": m.group(5),
            }
        if self.detect_jis2(track1):
            return {"JIS2": track1}
        return {}

    def parse_track2(self, track2):
        track2 = track2.rstrip('F')
        pattern = r"^;?(\d{12,19})=(\d{4})(\d{3})([^\?]*)\??"
        m = re.match(pattern, track2)
        if m:
            return {
                "PAN": m.group(1),
                "Expiry": m.group(2),
                "ServiceCode": m.group(3),
                "DiscretionaryData": m.group(4),
            }
        return {}

    def normalize_track(self, raw, trackno):
        if not raw:
            return ""
        val = raw.rstrip('F')
        if trackno == 1:
            if not val.startswith('%B'):
                val = '%B' + val
            if not val.endswith('?'):
                val += '?'
        elif trackno == 2:
            if not val.startswith(';'):
                val = ';' + val
            if not val.endswith('?'):
                val += '?'
        if self.detect_jis2(val):
            return val
        return val

    def lrc(self, data):
        lrc = 0
        for c in data.encode('ascii'):
            lrc ^= c
        return lrc

    def emulate(self, card):
        tracks = self.extract_tracks(card)
        parsed = {}
        for k, v in tracks.items():
            if "track1" in k:
                parsed[k] = self.parse_track1(v)
            elif "track2" in k:
                parsed[k] = self.parse_track2(v)
        norm_tracks = {
            "track1": self.normalize_track(tracks.get("track1", "") or tracks.get("track1_auto", ""), 1),
            "track2": self.normalize_track(tracks.get("track2", "") or tracks.get("track2_equiv", "") or tracks.get("track2_auto", ""), 2),
        }
        lrcs = {k: self.lrc(val) for k, val in norm_tracks.items() if val}
        print("[Magstripe] Emulating tracks (normalized):", norm_tracks)
        print("[Magstripe] LRCs:", lrcs)
        return {
            "raw": tracks,
            "parsed": parsed,
            "normalized": norm_tracks,
            "lrcs": lrcs,
        }

    def save_to_file(self, track_data, filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(track_data, f, indent=2)

    def export_tracks_bin(self, track_data, filename):
        t1 = track_data.get("normalized", {}).get("track1", "")
        t2 = track_data.get("normalized", {}).get("track2", "")
        t1_bytes = t1.encode('ascii') + bytes([self.lrc(t1)]) if t1 else b""
        t2_bytes = t2.encode('ascii') + bytes([self.lrc(t2)]) if t2 else b""
        with open(filename, "wb") as f:
            if t1_bytes:
                f.write(t1_bytes + b"\n")
            if t2_bytes:
                f.write(t2_bytes + b"\n")

    def export_tracks_tlv(self, track_data):
        tlvs = []
        for k, v in track_data.get("normalized", {}).items():
            tlvs.append({"tag": k, "desc": f"Magstripe {k.upper()}", "value": v})
        return tlvs

    def detect_jis2(self, track1):
        return (
            len(track1) in (69, 70)
            and ';' not in track1 and '%' not in track1 and '?' not in track1
        )

    def replay(self, card_or_trackdata, saved_list=None):
        """
        Simulate ARQC/ARPC using magstripe track2 for fallback/replay.
        If given a card, extracts and uses current tracks.
        If given a track_data dict, uses directly.
        If saved_list is provided, replays all saved tracks in order.
        """
        results = []
        if saved_list:
            for entry in saved_list:
                res = self._replay_single(entry)
                results.append(res)
            return results
        # Accept EMVCard or dict
        if hasattr(card_or_trackdata, "extract_tag"):
            track_data = self.emulate(card_or_trackdata)  # runs extract_tracks
            card = card_or_trackdata
        elif isinstance(card_or_trackdata, dict):
            track_data = card_or_trackdata
            card = None
        else:
            print("[Magstripe] replay: invalid input (must be card or track_data dict)")
            return None
        t2 = track_data.get("normalized", {}).get("track2", "")
        if not t2:
            print("[Magstripe] No Track 2 available for replay.")
            return None
        parsed = self.parse_track2(t2)
        if not parsed.get("PAN"):
            print("[Magstripe] Track 2 does not parse to a PAN for ARQC.")
            return None
        # Use EMV ARQC routine if available
        arqc = None
        if card and hasattr(card, "crypto") and hasattr(card.crypto, "generate_arqc"):
            arqc = card.crypto.generate_arqc(card, t2.encode('ascii'))
            print(f"[Magstripe] EMV ARQC from crypto: {arqc.hex().upper()}")
        else:
            key = os.urandom(16)
            mac = hmac.new(key, t2.encode('ascii'), hashlib.sha256).digest()[:8]
            arqc = mac
            print(f"[Magstripe] (Sim) ARQC for fallback: {arqc.hex().upper()}")
        arpc = bytes([arqc[0] ^ 0xAA]) + arqc[1:]
        print(f"[Magstripe] ARPC: {arpc.hex().upper()}")
        return {
            "PAN": parsed.get("PAN"),
            "Expiry": parsed.get("Expiry"),
            "ServiceCode": parsed.get("ServiceCode"),
            "DiscretionaryData": parsed.get("DiscretionaryData"),
            "ARQC": arqc.hex().upper(),
            "ARPC": arpc.hex().upper(),
        }

    def _replay_single(self, track_data):
        """
        For replaying a saved track (dict format) - supports batch replays.
        """
        t2 = track_data.get("normalized", {}).get("track2", "")
        if not t2:
            print("[Magstripe] [Batch] No Track 2 for entry.")
            return None
        parsed = self.parse_track2(t2)
        if not parsed.get("PAN"):
            print("[Magstripe] [Batch] Track 2 does not parse to a PAN for ARQC.")
            return None
        key = os.urandom(16)
        mac = hmac.new(key, t2.encode('ascii'), hashlib.sha256).digest()[:8]
        arqc = mac
        arpc = bytes([arqc[0] ^ 0xAA]) + arqc[1:]
        return {
            "PAN": parsed.get("PAN"),
            "Expiry": parsed.get("Expiry"),
            "ServiceCode": parsed.get("ServiceCode"),
            "DiscretionaryData": parsed.get("DiscretionaryData"),
            "ARQC": arqc.hex().upper(),
            "ARPC": arpc.hex().upper(),
        }
