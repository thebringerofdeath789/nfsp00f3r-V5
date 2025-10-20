import os\n#!/usr/bin/env python3
"""
Cardholder & Crypto Data Extraction Test
========================================
- Reads all cardholder, magstripe, and crypto data from a real card
- Shows CDOL1, CDOL2, UDOL, Track2, generated Track1, derived keys, PIN block, CVV, discretionary data
- Handles CashApp (Sutton Bank) cards and standard EMV
"""
import sys, os, binascii
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ..tlv import TLVParser
import time

def pretty_hex(data):
    if isinstance(data, bytes):
        return data.hex().upper()
    return str(data)

def parse_track2(track2_bytes):
    # ISO 7813: 5A13...DYYMMSSS...F
    t2 = track2_bytes.decode('ascii', errors='ignore') if isinstance(track2_bytes, bytes) else track2_bytes
    pan, rest = t2.split('D', 1) if 'D' in t2 else (t2, '')
    exp, svc, disc = rest[:4], rest[4:7], rest[7:]
    return pan, exp, svc, disc

def generate_track1(pan, name, exp, svc, disc):
    # ISO/IBM: %B{PAN}^{NAME}^{EXP}{SVC}{DISCRETIONARY}?
    name = (name or '').replace('/', ' ').replace('^', ' ').strip()
    name = name[:26].ljust(26)
    return f'%B{pan}^{name}^{exp}{svc}{disc}?'

def derive_emv_keys(pan, exp):
    # Simulate EMV key derivation (not real keys, for demo)
    from hashlib import sha1
    pan_seq = pan + exp
    ipek = sha1((pan_seq + 'IPEK').encode()).hexdigest()[:32]
    session = sha1((pan_seq + 'SESSION').encode()).hexdigest()[:32]
    return ipek, session

def derive_pin_block(pan):
    # Simulate ISO-0 PIN block (not real PIN, for demo)
    pin = '1234'  # Demo only
    block = f'041234FFFFFFFFFF{pan[-12:]}'
    return block

def scan_records(conn, parser, label):
    """
    Scan all SFI/record numbers for the selected application, parse TLV, and collect all found tags.
    Returns a dict of all found tags (first occurrence wins).
    """
    found = {}
    # SFI: 1-31, Record: 1-16 (per EMV spec, but most cards use 1-10)
    for sfi in range(1, 32):
        for rec in range(1, 17):
            # EMV READ RECORD: CLA INS P1 P2 Lc
            # P1 = record number, P2 = (SFI << 3) | 4
            apdu = [0x00, 0xB2, rec, (sfi << 3) | 4, 0x00]
            try:
                resp, sw1, sw2 = conn.transmit(apdu)
                if sw1 == 0x90 and sw2 == 0x00 and resp:
                    tlv = parser.parse(bytes(resp))
                    # Flatten constructed tags (e.g., 70, 77)
                    if '70' in tlv and isinstance(tlv['70'], dict):
                        tlv = tlv['70']
                    if '77' in tlv and isinstance(tlv['77'], dict):
                        tlv = tlv['77']
                    for tag, val in tlv.items():
                        if tag not in found:
                            found[tag] = val
            except Exception:
                continue
    return found

def main():
    print("🧪 CARDHOLDER & CRYPTO DATA EXTRACTION TEST")
    print("="*60)
    from smartcard.System import readers
    reader_list = readers()
    if not reader_list:
        print("❌ No card readers found!"); return
    reader = reader_list[0]
    print(f"📱 Using reader: {reader}")
    conn = reader.createConnection(); conn.connect()
    # PPSE
    ppse_cmd = [0x00,0xA4,0x04,0x00,0x0E,0x32,0x50,0x41,0x59,0x2E,0x53,0x59,0x53,0x2E,0x44,0x44,0x46,0x30,0x31,0x00]
    resp, sw1, sw2 = conn.transmit(ppse_cmd)
    if sw1!=0x90 or sw2!=0x00:
        print("❌ PPSE SELECT failed"); return
    parser = TLVParser(); ppse = parser.parse(bytes(resp))
    # Find all AIDs
    aids = []
    if '6F' in ppse and 'A5' in ppse['6F'] and 'BF0C' in ppse['6F']['A5']:
        bf0c = ppse['6F']['A5']['BF0C']
        apps = bf0c['61'] if isinstance(bf0c['61'], list) else [bf0c['61']]
        for app in apps:
            aids.append((app['4F'], app.get('50', b'').decode('utf-8','ignore')))
    print(f"\n📋 Applications found: {[a[1] for a in aids]}")
    for aid, label in aids:
        print(f"\n🔗 Selecting AID: {aid.hex().upper()} ({label})")
        sel = [0x00,0xA4,0x04,0x00,len(aid)]+list(aid)
        resp, sw1, sw2 = conn.transmit(sel)
        if sw1!=0x90 or sw2!=0x00:
            print(f"❌ SELECT failed for {label}"); continue
        app = parser.parse(bytes(resp))
        # Scan all records for fields
        found = scan_records(conn, parser, label)
        # CDOL1/2, UDOL
        print(f"  CDOL1 (8C): {pretty_hex(found.get('8C'))}")
        print(f"  CDOL2 (8D): {pretty_hex(found.get('8D'))}")
        print(f"  UDOL  (9F69): {pretty_hex(found.get('9F69'))}")
        # Cardholder Name
        name = found.get('5F20', b'').decode('utf-8','ignore') if found.get('5F20') else ''
        print(f"  Cardholder Name (5F20): {name}")
        # Track2, PAN, Expiry, Service Code, Discretionary
        track2 = found.get('57')
        if track2:
            # Try to decode as hex if not ASCII
            try:
                # If it's bytes, try hex->ASCII, else fallback
                if isinstance(track2, bytes):
                    # If it looks like hex, decode as hex string
                    try:
                        t2_ascii = bytes.fromhex(track2.hex()).decode('ascii')
                    except Exception:
                        t2_ascii = track2.decode('ascii', errors='replace')
                else:
                    t2_ascii = str(track2)
                print(f"  Track2 (ASCII): {t2_ascii}")
            except Exception:
                print(f"  Track2: {track2}")
            # Try to parse as EMV hex (standard Track2 format)
            t2_bytes = track2 if isinstance(track2, bytes) else bytes(track2, 'latin1')
            t2_hex = t2_bytes.hex().upper()
            print(f"  Track2 (HEX): {t2_hex}")
            # EMV Track2: PAN (up to D), Expiry (YYMM), SVC (3), Discretionary (rest)
            t2_str = ''
            try:
                t2_str = t2_bytes.decode('ascii')
            except Exception:
                t2_str = ''
            # Try to parse as EMV track2 format
            pan, exp, svc, disc = '', '', '', ''
            if 'D' in t2_str:
                pan, rest = t2_str.split('D', 1)
                exp, svc, disc = rest[:4], rest[4:7], rest[7:]
            elif 'd' in t2_str:
                pan, rest = t2_str.split('d', 1)
                exp, svc, disc = rest[:4], rest[4:7], rest[7:]
            else:
                # Try to parse as BCD (EMV style)
                t2_bcd = t2_hex
                if 'D' in t2_bcd:
                    pan, rest = t2_bcd.split('D', 1)
                    exp, svc, disc = rest[:4], rest[4:7], rest[7:]
            print(f"    PAN: {pan}\n    Expiry: {exp}\n    SVC: {svc}\n    Discretionary: {disc}")
            # Derive PIN (demo: use last 4 of PAN or fallback)
            derived_pin = pan[-4:] if pan and len(pan) >= 4 else '1234'
            print(f"  Derived Card PIN: {derived_pin}")
            # Generate Track2 with 101 service code and simulated CVV/disc
            if pan and exp and disc:
                import hashlib
                new_svc = '101'
                # Simulate CVV1: hash PAN+exp+svc, decimalize, take first 3 digits
                cvv_input = (pan + exp + new_svc).encode()
                cvv_hash = hashlib.sha1(cvv_input).hexdigest()
                cvv_digits = ''.join([c for c in cvv_hash if c.isdigit()])
                new_cvv = (cvv_digits + '000')[:3]
                # Replace CVV in discretionary (first 3 digits)
                new_disc = new_cvv + disc[3:] if len(disc) >= 3 else disc
                new_track2 = f"{pan}D{exp}{new_svc}{new_disc}"
                print(f"  Track2 (101 SVC, simulated CVV): {new_track2}")
        else:
            print("  Track2: Not found")
        # Track1 (generated)
        if pan and exp and svc and disc is not None:
            t1 = generate_track1(pan, name, exp, svc, disc)
            print(f"  Generated Track1: {t1}")
        # Derived keys
        if pan and exp:
            ipek, session = derive_emv_keys(pan, exp)
            print(f"  Derived IPEK: {ipek}\n  Derived Session Key: {session}")
        # PIN block
        if pan:
            pin_block = derive_pin_block(pan)
            print(f"  Derived PIN Block: {pin_block}")
        # CVV/discretionary (simulate)
        if disc:
            print(f"  Discretionary Data: {disc}")
            # Simulate new CVV/disc (not real, demo only)
            new_disc = disc[::-1]
            print(f"  New Discretionary Data (sim): {new_disc}")
        print("\n---")
    print("\n✅ Cardholder & crypto data extraction complete.")

if __name__ == "__main__":
    main()
