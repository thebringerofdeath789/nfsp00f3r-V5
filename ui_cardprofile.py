# =====================================================================
# File: ui_cardprofile.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Card profile dialog for importing/exporting card profiles.
#   - Lets user review, edit, import/export JSON profiles.
#   - Used by main window for profile operations.
#
# Functions:
#   - CardProfileDialog(QDialog)
# =====================================================================

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QFileDialog, QMessageBox

class CardProfileDialog(QDialog):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Card Profile")
        self.resize(600, 700)
        self.textbox = QTextEdit()
        self.textbox.setText(card.export_profile())
        self.save_btn = QPushButton("Save")
        self.load_btn = QPushButton("Load")
        btns = QHBoxLayout()
        btns.addWidget(self.save_btn)
        btns.addWidget(self.load_btn)
        layout = QVBoxLayout()
        layout.addWidget(self.textbox)
        layout.addLayout(btns)
        self.setLayout(layout)
        self.save_btn.clicked.connect(self.save_profile)
        self.load_btn.clicked.connect(self.load_profile)

    def save_profile(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Card Profile", "", "JSON Files (*.json)")
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.textbox.toPlainText())
            QMessageBox.information(self, "Export", "Card profile saved.")

    def load_profile(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Card Profile", "", "JSON Files (*.json)")
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                self.textbox.setText(f.read())
            QMessageBox.information(self, "Import", "Card profile loaded.")
