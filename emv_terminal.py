# =====================================================================
# File: emv_terminal.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Terminal emulation profile/config. Handles AID filtering, terminal data.
#   Used for emulating terminal capabilities in replay/relay scenarios.
#
# Functions:
#   - EmvTerminal()
#       - set_terminal_profile(profile)
#       - get_terminal_profile()
#       - filter_aid(aid)
#       - list_aids()
# =====================================================================

class EmvTerminal:
    def __init__(self):
        self.profile = {
            "terminal_country_code": "0840",
            "merchant_id": "000000000000000",
            "terminal_capabilities": "E0F0C8",
            "terminal_type": "22",
            "aids": []
        }

    def set_terminal_profile(self, profile):
        self.profile.update(profile)

    def get_terminal_profile(self):
        return self.profile

    def filter_aid(self, aid):
        aids = self.profile.get("aids", [])
        return aid in aids if aids else True

    def list_aids(self):
        return self.profile.get("aids", [])
