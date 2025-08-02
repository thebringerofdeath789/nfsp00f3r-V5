# =====================================================================
# File: logger.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Robust, color-capable logger for both UI and file output.
#   - Used for APDU logs, status updates, debug events, errors.
#   - Emits log updates for the debug window (if connected).
#
# Functions:
#   - Logger()
#       - log(msg, level="info")
#       - error(msg)
#       - get_log()
#       - clear_log()
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal
import datetime

class Logger(QObject):
    log_updated = pyqtSignal()

    def __init__(self, logfile="nfsp00f3r.log"):
        super().__init__()
        self._log = []
        self.logfile = logfile

    def log(self, msg, level="info"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level.upper()}] {msg}"
        self._log.append(entry)
        print(entry)  # Print to stdout (useful for dev/debug/APDU)
        try:
            with open(self.logfile, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass  # Ignore file write errors
        self.log_updated.emit()

    def error(self, msg):
        self.log(msg, level="error")

    def get_log(self):
        # Returns last 2000 log entries for performance/UI
        return self._log[-2000:]

    def clear_log(self):
        self._log = []
        self.log_updated.emit()
