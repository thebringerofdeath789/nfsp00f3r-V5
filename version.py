# =====================================================================
# File: version.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Application version and changelog information.
#
# Functions:
#   - get_version()
#   - get_changelog()
# =====================================================================

def get_version():
    return "4.04"

def get_changelog():
    return [
        "V4.04 (2025-08-01): Added full relay & replay, HCE companion support, robust TLV parser.",
        "V4.03 (2025-07-15): Improved APDU logging, UI updates, tag dictionary expansion.",
        "V4.02 (2025-06-30): Added pre-paid AID iteration, PDOL support, SFI browsing.",
        
    ]
