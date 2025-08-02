# =====================================================================
# File: tlv.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Recursive TLV parser, fully EMV/ISO7816 compliant, with tag dictionary.
#   Merges parsing logic from danmichaelo/emv, dimalinux/EMV-Tools, RFIDIOt.
#   Looks up tag descriptions in TagDict.
#
# Functions:
#   - TLVParser(tag_dict)
#       - parse(data)
# =====================================================================

class TLVParser:
    def __init__(self, tag_dict):
        self.tag_dict = tag_dict

    def parse(self, data):
        idx = 0
        result = []
        while idx < len(data):
            tag = self._read_tag(data, idx)
            taglen = len(tag)
            idx += taglen
            length, lsize = self._read_length(data, idx)
            idx += lsize
            value = data[idx:idx+length]
            idx += length
            desc = self.tag_dict.get(tag.hex().upper(), "")
            node = {"tag": tag.hex().upper(), "desc": desc, "value": value.hex().upper(), "children": []}
            if self._is_constructed(tag):
                node["children"] = self.parse(value)
                node["value"] = ""
            result.append(node)
        return result

    def _read_tag(self, data, idx):
        tag = bytes([data[idx]])
        if tag[0] & 0x1F == 0x1F:
            tag += bytes([data[idx+1]])
        return tag

    def _read_length(self, data, idx):
        l = data[idx]
        if l & 0x80:
            n = l & 0x7F
            val = int.from_bytes(data[idx+1:idx+1+n], 'big')
            return val, 1 + n
        else:
            return l, 1

    def _is_constructed(self, tag):
        return bool(tag[0] & 0x20)
