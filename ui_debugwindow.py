# =====================================================================
# File: ui_debugwindow.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Debug window dialog for real-time APDU log viewing.
#   - Displays card communication, color-codes commands (red) and responses (green).
#   - Black background for hacker/terminal feel.
#   - Updates live via APDULogger signals.
#
# Functions:
#   - DebugWindow(QDialog)
#       - update_log()
# =====================================================================

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit
from PyQt5.QtCore import Qt

class DebugWindow(QDialog):
    def __init__(self, apdu_logger):
        super().__init__()
        self.setWindowTitle("Debug - APDU Log")
        self.resize(900, 500)
        self.setMinimumSize(600, 300)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("background-color: #000; color: #fff; font-family: 'Consolas'; font-size: 12pt;")
        layout = QVBoxLayout()
        layout.addWidget(self.log_view)
        self.setLayout(layout)
        self.apdu_logger = apdu_logger
        self.apdu_logger.log_updated.connect(self.update_log)
        self.update_log()

    def update_log(self):
        self.log_view.clear()
        for entry in self.apdu_logger.get_log():
            if entry.startswith(">>"):
                self.log_view.setTextColor(Qt.red)
            elif entry.startswith("<<"):
                self.log_view.setTextColor(Qt.green)
            else:
                self.log_view.setTextColor(Qt.white)
            self.log_view.append(entry)
        self.log_view.moveCursor(self.log_view.textCursor().End)
