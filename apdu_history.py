# =====================================================================
# File: apdu_history.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Handles storage and retrieval of APDU logs for card sessions.
#   - Allows for review of previous sessions and export of logs.
#
# Functions:
#   - APDUHistory()
#       - add_entry(pan, entry)
#       - get_history(pan)
#       - export_history(pan, filename)
# =====================================================================

import json

class APDUHistory:
    def __init__(self):
        self._history = {}

    def add_entry(self, pan, entry):
        if pan not in self._history:
            self._history[pan] = []
        self._history[pan].append(entry)

    def get_history(self, pan):
        return self._history.get(pan, [])

    def export_history(self, pan, filename):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self._history.get(pan, []), f, indent=2)
