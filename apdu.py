# =====================================================================
# File: apdu.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   APDU builder/parser, and APDU log/trace logic.
#   - Logs all APDU command/response with color tags for UI/debug window.
#   - Provides utility for building/parsing raw APDUs.
#
# Functions:
#   - APDULogger()
#       - log_command(cmd_bytes)
#       - log_response(resp_bytes)
#       - get_log()
#       - clear_log()
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal

class APDULogger(QObject):
    log_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._log = []

    def log_command(self, cmd_bytes):
        s = ">> " + cmd_bytes.hex().upper()
        self._log.append(s)
        self.log_updated.emit()

    def log_response(self, resp_bytes):
        s = "<< " + resp_bytes.hex().upper()
        self._log.append(s)
        self.log_updated.emit()

    def get_log(self):
        return self._log[-1000:]

    def clear_log(self):
        self._log = []
        self.log_updated.emit()
