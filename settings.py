# =====================================================================
# File: settings.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Persistent application settings using QSettings.
#   - Stores theme, default reader, last Bluetooth address, etc.
#
# Functions:
#   - SettingsManager()
#       - get(key, default)
#       - set(key, value)
#       - remove(key)
# =====================================================================

from PyQt5.QtCore import QSettings

class SettingsManager:
    def __init__(self):
        # Organization and application names
        self.settings = QSettings("GregoryKing", "nfsp00f3r")

    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)
        self.settings.sync()

    def remove(self, key):
        self.settings.remove(key)
        self.settings.sync()
