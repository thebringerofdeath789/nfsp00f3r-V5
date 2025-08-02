# =====================================================================
# File: emvcard.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   EMVCard object: handles multi‐application parsing, proper
#   GPO/PDOL/AFL flows, TLV extraction, track decode,
#   transaction history, crypto key extraction, and full profile.
#
# Functions:
#   - EMVCard(source, log_callback=None)
#       - parse_card()
#       - get_applications_from_ppse()
#       - parse_tlv_records(records)
#       - extract_tag(tag)
#       - extract_pan(tlvs)
#       - extract_cvv(tlvs)
#       - extract_zip(tlvs)
#       - extract_cardholder(tlvs)
#       - extract_expiry(tlvs)
#       - extract_tracks(tlvs)
#       - decode_track2_equiv(track2_hex)
#       - get_cardholder_info()
#       - get_tlv_tree()
#       - export_profile()
#       - import_profile_json(profile_json)
#       - load_from_profile(d)
#       - reparse()
#       - send_apdu(apdu_bytes)
#       - log_apdu(apdu_bytes, resp, error=None)
#       - handle_card_removed()
# =====================================================================

import json
import random
from tlv import TLVParser
from tag_dict import TagDict
from aid_list import AidList
from pdol import build_pdol
from history_parser import parse_log_entries
from emv_crypto_keys import EmvCryptoKeys

try:
    from smartcard.Exceptions import CardConnectionException
except ImportError:
    CardConnectionException = Exception

SELECT_PPSE = bytes.fromhex('00A404000E325041592E5359532E4444463031')  # '2PAY.SYS.DDF01'
SELECT_AID = lambda aid: bytes.fromhex('00A40400') + bytes([len(aid)//2]) + bytes.fromhex(aid)
READ_RECORD = lambda sfi, rec: bytes.fromhex(f"00B2{rec:02X}{(sfi << 3) | 4:02X}00")

class EMVCard:
    def __init__(self, source, log_callback=None):
        self.source = source
        self.tag_dict = TagDict()
        self.tlv_parser = TLVParser(self.tag_dict)

        # Card attributes
        self.pan = ""
        self.cardholder = ""
        self.expiry = ""
        self.cvv = ""
        self.zip = ""
        self.service_code = ""
        self.discretionary_data = ""
        self.tracks = {}
        self.applications = []
        self.tlv_tree = []
        self.card_present = True
        self.log_callback = log_callback

        if isinstance(source, dict):
            self.load_from_profile(source)
        else:
            self.parse_card()

        # Set card attributes from first app
        if self.applications:
            app = self.applications[0]
            self.pan = app.get('pan', '')
            self.cardholder = app.get('cardholder', '')
            self.expiry = app.get('expiry', '')
            self.cvv = app.get('cvv', '')
            self.zip = app.get('zip', '')
            self.service_code = app.get('service_code', '')
            self.discretionary_data = app.get('discretionary_data', '')
            self.tracks = app.get('tracks', {})
        else:
            self.pan = ""
            self.cardholder = ""
            self.expiry = ""
            self.cvv = ""
            self.zip = ""
            self.service_code = ""
            self.discretionary_data = ""
            self.tracks = {}

    def parse_card(self):
        self.applications = []
        self.tlv_tree = []

        try:
            ppse_resp = self.send_apdu(SELECT_PPSE)
            ppse_tlvs = self.tlv_parser.parse(ppse_resp)
            aids = self.get_applications_from_ppse(ppse_tlvs)
        except Exception as e:
            aids = []
            self.log_apdu(SELECT_PPSE, b"", error=f"PPSE select failed: {e}")
        if not aids:
            aids = AidList().get_all()

        for aid in aids:
            try:
                sel_resp = self.send_apdu(SELECT_AID(aid))
                fci_tlvs = self.tlv_parser.parse(sel_resp)
                pdol_hex = self.extract_tag('9F38', fci_tlvs)
                pdol_data = b''
                term_data = {}

                if pdol_hex:
                    pdol_template = bytes.fromhex(pdol_hex)
                    print(f"[DEBUG] PDOL (9F38) template: {pdol_hex}")
                    term_data = {
                        '9F66': b'\x36\x00\x00\x00',
                        '9F02': b'\x00\x00\x00\x00\x00\x01',
                        '9F03': b'\x00\x00\x00\x00\x00\x00',
                        '9F1A': b'\x02\x50',
                        '95':   b'\x00\x00\x00\x00\x00',
                        '5F2A': b'\x02\x50',
                        '9A':   b'\x20\x01\x01',
                        '9C':   b'\x00',
                        '9F37': b'\x12\x34\x56\x78',
                    }
                    pdol_data = build_pdol(pdol_template, term_data)
                    print(f"[DEBUG] Built PDOL data: {pdol_data.hex()}")
                else:
                    print("[DEBUG] No PDOL requested for this AID.")

                cmd_data = b'\x83' + bytes([len(pdol_data)]) + pdol_data if pdol_data else b''
                gpo_apdu = b'\x80\xa8\x00\x00' + bytes([len(cmd_data)]) + cmd_data + b'\x00'
                print(f"[DEBUG] GPO APDU: {gpo_apdu.hex()}")

                gpo_resp = self.send_apdu(gpo_apdu)
                gpo_tlvs = self.tlv_parser.parse(gpo_resp)

                aip = self.extract_tag('82', gpo_tlvs)
                afl_raw = self.extract_tag('94', gpo_tlvs)
                afl = []
                if afl_raw:
                    data = bytes.fromhex(afl_raw)
                    for i in range(0, len(data), 4):
                        sfi   = data[i] >> 3
                        first = data[i+1]
                        last  = data[i+2]
                        offline = data[i+3]
                        afl.append((sfi, first, last, offline))

                recs = []
                for (sfi, first, last, _) in afl:
                    for rec in range(first, last+1):
                        resp = self.send_apdu(READ_RECORD(sfi, rec))
                        if resp and resp[-2:] == b'\x90\x00':
                            recs.append(resp)
                tlvs = self.parse_tlv_records(recs)

                pan = self.extract_pan(tlvs)
                if not pan:
                    pan = f"NO_PAN_{random.randint(1e9, 1e10-1)}"

                cardholder = self.extract_cardholder(tlvs)
                expiry     = self.extract_expiry(tlvs)
                cvv        = self.extract_cvv(tlvs)
                zip_code   = self.extract_zip(tlvs)
                tracks     = self.extract_tracks(tlvs)
                tx_history = parse_log_entries(self)
                crypto_keys= EmvCryptoKeys().extract_keys_from_profile(self)

                # Get service code and discretionary from decoded track2 if possible
                decoded_track2 = self.decode_track2_equiv(self.extract_tag('57', tlvs) or self.extract_tag('9F6B', tlvs) or '')
                service_code = decoded_track2.get('ServiceCode', '') if decoded_track2 else ''
                discretionary_data = decoded_track2.get('DiscretionaryData', '') if decoded_track2 else ''

                app = {
                    'aid': aid,
                    'fci_tlvs': fci_tlvs,
                    'gpo_tlvs': gpo_tlvs,
                    'aip': aip,
                    'afl': afl,
                    'tlvs': tlvs,
                    'pan': pan,
                    'cardholder': cardholder,
                    'expiry': expiry,
                    'cvv': cvv,
                    'zip': zip_code,
                    'service_code': service_code,
                    'discretionary_data': discretionary_data,
                    'tracks': tracks,
                    'transactions': tx_history,
                    'crypto_keys': crypto_keys
                }
                self.applications.append(app)
            except Exception as e:
                self.log_apdu(SELECT_AID(aid), b"", error=f"AID {aid} parse error: {e}")
                continue

        for app in self.applications:
            self.tlv_tree.extend(app['tlvs'])

        if self.applications:
            app = self.applications[0]
            self.pan = app.get('pan', '')
            self.cardholder = app.get('cardholder', '')
            self.expiry = app.get('expiry', '')
            self.cvv = app.get('cvv', '')
            self.zip = app.get('zip', '')
            self.service_code = app.get('service_code', '')
            self.discretionary_data = app.get('discretionary_data', '')
            self.tracks = app.get('tracks', {})
        else:
            self.pan = ""
            self.cardholder = ""
            self.expiry = ""
            self.cvv = ""
            self.zip = ""
            self.service_code = ""
            self.discretionary_data = ""
            self.tracks = {}

    def get_applications_from_ppse(self, ppse_tlvs):
        aids = []
        def walk(nodes):
            for n in nodes:
                t = getattr(n, 'tag', None) if hasattr(n, 'tag') else n.get('tag') if isinstance(n, dict) else None
                if t == '4F':
                    aids.append(getattr(n, 'value', None) if hasattr(n, 'value') else n.get('value'))
                children = getattr(n, 'children', None) if hasattr(n, 'children') else n.get('children') if isinstance(n, dict) else None
                if children:
                    walk(children)
        walk(ppse_tlvs)
        return list(dict.fromkeys(aids))

    def parse_tlv_records(self, records):
        out = []
        for rec in records:
            try:
                out.extend(self.tlv_parser.parse(rec))
            except Exception as e:
                self.log_apdu(rec, b"", error=f"TLV parse error: {e}")
        return out

    def extract_tag(self, tag, tlvs=None):
        tlvs = tlvs if tlvs is not None else self.tlv_tree
        for n in tlvs:
            t = getattr(n, 'tag', None) if hasattr(n, 'tag') else n.get('tag') if isinstance(n, dict) else None
            if t == tag:
                return getattr(n, 'value', None) if hasattr(n, 'value') else n.get('value')
            children = getattr(n, 'children', None) if hasattr(n, 'children') else n.get('children') if isinstance(n, dict) else None
            if children:
                v = self.extract_tag(tag, children)
                if v:
                    return v
        return ''

    def extract_pan(self, tlvs):
        pan = self.extract_tag('5A', tlvs)
        if pan:
            return pan
        track2 = self.extract_tag('57', tlvs)
        if track2:
            decoded = self.decode_track2_equiv(track2)
            if decoded and decoded.get('PAN'):
                return decoded['PAN']
            if 'D' in track2:
                return track2.split('D',1)[0]
            if '=' in track2:
                return track2.split('=',1)[0]
            digits = ''.join([c for c in track2 if c.isdigit()])
            if 12 <= len(digits) <= 19:
                return digits
        track1 = self.extract_tag('56', tlvs)
        if track1:
            parts = track1.split('^')
            if len(parts) >= 1 and parts[0].startswith('B') and len(parts[0]) > 1:
                return parts[0][1:]
            digits = ''.join([c for c in track1 if c.isdigit()])
            if 12 <= len(digits) <= 19:
                return digits
        track2_ms = self.extract_tag('9F6B', tlvs)
        if track2_ms:
            decoded = self.decode_track2_equiv(track2_ms)
            if decoded and decoded.get('PAN'):
                return decoded['PAN']
            if 'D' in track2_ms:
                return track2_ms.split('D',1)[0]
            if '=' in track2_ms:
                return track2_ms.split('=',1)[0]
            digits = ''.join([c for c in track2_ms if c.isdigit()])
            if 12 <= len(digits) <= 19:
                return digits
        return ''

    def decode_track2_equiv(self, track2_hex):
        """
        Decode Track 2 Equivalent data from hex string to PAN, expiry, service code, discretionary data.
        Format: PAN + 'D' + YYMM + ServiceCode + DiscretionaryData + Padding (F)
        """
        try:
            data = bytes.fromhex(track2_hex)
            digits = []
            for b in data:
                high = (b >> 4) & 0x0F
                low = b & 0x0F
                if high == 0xD or high == 0xF:
                    break
                digits.append(str(high))
                if low == 0xD or low == 0xF:
                    break
                digits.append(str(low))
            digit_str = ''.join(digits)
            if 'D' in digit_str:
                pan, rest = digit_str.split('D', 1)
            else:
                pan = digit_str[:16]
                rest = digit_str[16:]
            expiry = rest[:4]
            service_code = rest[4:7]
            discretionary = rest[7:] if len(rest) > 7 else ''
            return {
                "PAN": pan,
                "Expiry": expiry,
                "ServiceCode": service_code,
                "DiscretionaryData": discretionary
            }
        except Exception:
            return {}

    def extract_cvv(self, tlvs):
        v = self.extract_tag('9F1F', tlvs) or self.extract_tag('9F6B', tlvs)
        if v and v.isdigit():
            return v
        return ''

    def extract_zip(self, tlvs):
        v = self.extract_tag('5F50', tlvs) or self.extract_tag('5F55', tlvs)
        if v and (len(v) == 5 or len(v) == 9) and v.isdigit():
            return v
        return ''

    def extract_cardholder(self, tlvs):
        v = self.extract_tag('5F20', tlvs)
        if v:
            # Decode hex if appears hex
            try:
                if all(c in '0123456789ABCDEFabcdef' for c in v) and len(v) % 2 == 0:
                    v = bytes.fromhex(v).decode('ascii').strip()
            except Exception:
                pass
            return v.strip()
        return ''

    def extract_expiry(self, tlvs):
        v = self.extract_tag('5F24', tlvs)
        if v and len(v) >= 4:
            return v[:4]  # YYMM
        # Fallback to decode from track2 equiv if available
        track2 = self.extract_tag('57', tlvs) or self.extract_tag('9F6B', tlvs)
        if track2:
            decoded = self.decode_track2_equiv(track2)
            if decoded and decoded.get('Expiry'):
                return decoded['Expiry']
        return ''

    def extract_tracks(self, tlvs):
        tracks = {}
        for t in ('57', '9F6B', '56'):
            v = self.extract_tag(t, tlvs)
            if v:
                tracks[t] = v
        return tracks

    def get_cardholder_info(self):
        if not self.applications:
            return {}
        app = self.applications[0]
        return {
            'PAN': app.get('pan', ''),
            'Cardholder': app.get('cardholder', ''),
            'Expiry': app.get('expiry', ''),
            'CVV': app.get('cvv', ''),
            'ZIP': app.get('zip', '')
        }

    def get_tlv_tree(self):
        return self.tlv_tree

    def export_profile(self):
        data = {'applications': self.applications}
        return json.dumps(data, indent=2)

    @staticmethod
    def import_profile_json(profile_json):
        d = json.loads(profile_json) if isinstance(profile_json, str) else profile_json
        return EMVCard(d)

    def load_from_profile(self, d):
        self.applications = d.get('applications', [])
        self.tlv_tree = [tlv for app in self.applications for tlv in app.get('tlvs', [])]
        if self.applications:
            app = self.applications[0]
            self.pan = app.get('pan', '')
            self.cardholder = app.get('cardholder', '')
            self.expiry = app.get('expiry', '')
            self.cvv = app.get('cvv', '')
            self.zip = app.get('zip', '')
            self.service_code = app.get('service_code', '')
            self.discretionary_data = app.get('discretionary_data', '')
            self.tracks = app.get('tracks', {})
        else:
            self.pan = ""
            self.cardholder = ""
            self.expiry = ""
            self.cvv = ""
            self.zip = ""
            self.service_code = ""
            self.discretionary_data = ""
            self.tracks = {}

    def reparse(self):
        self.parse_card()

    def send_apdu(self, apdu_bytes):
        print(f">> {apdu_bytes.hex()}")
        if not self.card_present:
            self.log_apdu(apdu_bytes, b'', error="Card not present")
            return b""
        try:
            if hasattr(self.source, 'transmit'):
                resp, sw1, sw2 = self.source.transmit(list(apdu_bytes))
                resp_bytes = bytes(resp)
                sw_bytes = bytes([sw1, sw2])
                result = resp_bytes + sw_bytes
                print(f"<< {result.hex()}")
                self.log_apdu(apdu_bytes, result)
                return result
            if hasattr(self.source, 'transceive'):
                result = self.source.transceive(bytes(apdu_bytes))
                if isinstance(result, list):
                    result = bytes(result)
                print(f"<< {result.hex()}")
                self.log_apdu(apdu_bytes, result)
                return result
            if hasattr(self.source, 'send_apdu'):
                result = self.source.send_apdu(apdu_bytes)
                if isinstance(result, list):
                    result = bytes(result)
                print(f"<< {result.hex()}")
                self.log_apdu(apdu_bytes, result)
                return result
        except CardConnectionException as e:
            self.log_apdu(apdu_bytes, b'', error=f"Card removed: {e}")
            self.handle_card_removed()
            return b""
        except Exception as e:
            self.log_apdu(apdu_bytes, b'', error=f"APDU error: {e}")
        return b""

    def log_apdu(self, apdu_bytes, resp_bytes, error=None):
        if isinstance(apdu_bytes, list):
            apdu_bytes = bytes(apdu_bytes)
        if isinstance(resp_bytes, list):
            resp_bytes = bytes(resp_bytes)
        apdu_hex = ' '.join(f"{b:02X}" for b in apdu_bytes)
        resp_hex = ' '.join(f"{b:02X}" for b in resp_bytes) if resp_bytes else ''
        logline = f">> {apdu_hex}\n<< {resp_hex}"
        if error:
            logline += f"  [ERROR: {error}]"
        print(logline)
        if self.log_callback:
            try:
                self.log_callback(logline)
            except Exception:
                pass

    def handle_card_removed(self):
        self.card_present = False
        print("[INFO] Card has been removed. Further APDUs will not be sent until new card is detected.")
        if self.log_callback:
            try:
                self.log_callback("[INFO] Card has been removed. Please re-insert a card.")
            except Exception:
                pass
