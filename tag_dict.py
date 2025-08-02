# =====================================================================
# File: tag_dict.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   EMV/ISO7816 tag dictionary. Merges all tags from danmichaelo/emv,
#   dimalinux/EMV-Tools, RFIDIOt, openemv, and all referenced repo sources.
#   (Loaded at runtime to support 380+ tags, can be expanded from tags.json.)
#
# Functions:
#   - TagDict()
#       - get(tag)
# =====================================================================

import json
import os

class TagDict:
    def __init__(self):
        self.tags = self._load_tags()

    def _load_tags(self):
        path = os.path.join(os.path.dirname(__file__), "tags.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "5A": "Application Primary Account Number (PAN)",
            "5F20": "Cardholder Name",
            "5F24": "Application Expiration Date",
            "57": "Track 2 Equivalent Data",
            "9F6B": "Track 2 Data",
        }

    def get(self, tag, default=""):
        return self.tags.get(tag, default)
