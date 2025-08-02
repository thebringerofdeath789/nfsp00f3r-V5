# =====================================================================
# File: ui_mainwindow.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Main window UI builder for the nfsp00f3r PyQt5 application.
#   - Contains all widgets, layouts, and tab setup for card viewing, APDU log,
#     TLV tree, and control buttons.
#   - Provides update methods for card list, card detail, TLV tree, and APDU log.
#   - Wires all buttons to corresponding MainWindow methods via signals.
#   - Implements a Debug Window for live log output.
#   - Adds an About dialog describing the project, author, and license.
#
# Functions:
#   - build_layout(main_window)
#   - update_card_list(cards)
#   - update_card_detail(card)
#   - clear_card_detail()
#   - update_tlv_tree(tlv_tree)
#   - clear_tlv_tree()
#   - update_apdu_log(log)
#   - show_debug_window(logger)
#   - _append_debug()
#   - show_about_dialog()
#   - update_magstripe_result(magstripe_data)
# =====================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTreeWidget,
    QTreeWidgetItem, QTextEdit, QListWidget, QTabWidget, QComboBox, QSplitter, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt

class MainWindowUI:
    def __init__(self, main_window):
        self.main_window = main_window
        self.debug_dialog = None
        self.debug_edit = None
        self.logger = None

    def build_layout(self, main_window):
        # Main vertical layout
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout(self.main_widget)

        # Top row: Card selector and control buttons
        self.top_bar = QHBoxLayout()
        self.card_combo = QComboBox()
        self.card_combo.setMinimumWidth(220)
        self.card_combo.currentIndexChanged.connect(self.on_card_selected)
        self.top_bar.addWidget(QLabel("Detected Cards:"))
        self.top_bar.addWidget(self.card_combo)

        # Control buttons
        self.read_btn = QPushButton("Read Card")
        self.export_btn = QPushButton("Export Card")
        self.import_btn = QPushButton("Import Card")
        self.transaction_btn = QPushButton("Transaction")
        self.magstripe_btn = QPushButton("Emulate Magstripe")
        self.replay_btn = QPushButton("Replay Magstripe")  # NEW: Replay button
        self.randomize_btn = QPushButton("Randomize PAN")
        self.pin_btn = QPushButton("Offline PIN")
        self.reset_pin_btn = QPushButton("Reset PIN Ctr")
        self.theme_btn = QPushButton("Dark/Light Mode")
        self.debug_btn = QPushButton("Debug Window")
        self.sync_to_btn = QPushButton("Sync to Phone")
        self.sync_from_btn = QPushButton("Sync from Phone")
        self.relay_btn = QPushButton("Start Relay")
        self.relay_stop_btn = QPushButton("Stop Relay")
        self.about_btn = QPushButton("About")  # About button

        # Button wiring
        self.read_btn.clicked.connect(main_window.on_read_card)
        self.export_btn.clicked.connect(main_window.on_export_card)
        self.import_btn.clicked.connect(main_window.on_import_card)
        self.transaction_btn.clicked.connect(main_window.on_run_transaction)
        self.magstripe_btn.clicked.connect(main_window.on_emulate_magstripe)
        self.replay_btn.clicked.connect(main_window.on_replay_magstripe)  # Wire replay button
        self.randomize_btn.clicked.connect(main_window.on_randomize_pan)
        self.pin_btn.clicked.connect(main_window.on_verify_pin)
        self.reset_pin_btn.clicked.connect(main_window.on_reset_pin_counter)
        self.theme_btn.clicked.connect(main_window.on_switch_theme)
        self.debug_btn.clicked.connect(main_window.on_show_debug)
        self.sync_to_btn.clicked.connect(main_window.on_sync_to_phone)
        self.sync_from_btn.clicked.connect(main_window.on_sync_from_phone)
        self.relay_btn.clicked.connect(main_window.on_start_relay)
        self.relay_stop_btn.clicked.connect(main_window.on_stop_relay)
        self.about_btn.clicked.connect(self.show_about_dialog)

        for btn in [
            self.read_btn, self.export_btn, self.import_btn, self.transaction_btn,
            self.magstripe_btn, self.replay_btn,  # Make sure replay_btn is in here!
            self.randomize_btn, self.pin_btn, self.reset_pin_btn,
            self.theme_btn, self.debug_btn, self.sync_to_btn, self.sync_from_btn,
            self.relay_btn, self.relay_stop_btn, self.about_btn
        ]:
            btn.setMinimumWidth(110)
            btn.setMaximumWidth(150)
            self.top_bar.addWidget(btn)

        self.main_layout.addLayout(self.top_bar)

        # Main splitter: left (card/tlv), right (APDU log)
        self.splitter = QSplitter(Qt.Horizontal)
        self.left_widget = QWidget()
        self.left_layout = QVBoxLayout(self.left_widget)

        # Card details
        self.card_detail_label = QLabel("Card Details")
        self.card_detail = QTextEdit()
        self.card_detail.setReadOnly(True)
        self.card_detail.setFontPointSize(10)
        self.left_layout.addWidget(self.card_detail_label)
        self.left_layout.addWidget(self.card_detail, 3)

        # Magstripe Emulation Result
        self.magstripe_label = QLabel("Magstripe Emulation Result")
        self.magstripe_result = QTextEdit()
        self.magstripe_result.setReadOnly(True)
        self.magstripe_result.setFontPointSize(10)
        self.left_layout.addWidget(self.magstripe_label)
        self.left_layout.addWidget(self.magstripe_result, 2)

        # TLV Tree
        self.tlv_label = QLabel("TLV Data (Tree View)")
        self.tlv_tree = QTreeWidget()
        self.tlv_tree.setHeaderLabels(["Tag", "Description", "Value"])
        self.left_layout.addWidget(self.tlv_label)
        self.left_layout.addWidget(self.tlv_tree, 5)

        self.left_widget.setLayout(self.left_layout)
        self.splitter.addWidget(self.left_widget)

        # APDU Log (right pane)
        self.apdu_label = QLabel("APDU Log")
        self.apdu_log = QTextEdit()
        self.apdu_log.setReadOnly(True)
        self.apdu_log.setFontPointSize(10)
        self.apdu_log.setStyleSheet("background-color: #111; color: #fff;")
        self.right_layout = QVBoxLayout()
        self.right_layout.addWidget(self.apdu_label)
        self.right_layout.addWidget(self.apdu_log)
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)
        self.splitter.addWidget(self.right_widget)

        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.main_layout.addWidget(self.splitter)

    def update_card_list(self, cards):
        self.card_combo.blockSignals(True)
        self.card_combo.clear()
        for pan in cards:
            self.card_combo.addItem(pan)
        self.card_combo.blockSignals(False)

    def update_card_detail(self, card):
        info = card.get_cardholder_info()
        text = (
            f"PAN: {info.get('PAN','')}\n"
            f"Name: {info.get('Cardholder','')}\n"
            f"Expiry: {info.get('Expiry','')}\n"
            f"CVV: {info.get('CVV','')}\n"
            f"ZIP: {info.get('ZIP','')}\n"
            f"PIN: {info.get('PIN','')}\n"
            f"Apps: {', '.join(info.get('AIDs', []))}\n"
        )
        # Show crypto keys if present
        if hasattr(card, "crypto_keys") and hasattr(card.crypto_keys, "get_keys_for_ui"):
            keys = card.crypto_keys.get_keys_for_ui(card.pan)
            if keys:
                text += "\nCrypto Keys:\n"
                for k in keys:
                    text += f"  {k['type']}: {k['value']} (len {k['length']} src={k['source']})\n"
        self.card_detail.setPlainText(text)

    def clear_card_detail(self):
        self.card_detail.clear()

    def update_magstripe_result(self, magstripe_data):
        if not magstripe_data:
            self.magstripe_result.clear()
            return
        text = (
            f"PAN: {magstripe_data.get('PAN','')}\n"
            f"Expiry: {magstripe_data.get('Expiry','')}\n"
            f"Service Code: {magstripe_data.get('ServiceCode','')}\n"
            f"Discretionary Data: {magstripe_data.get('DiscretionaryData','')}\n"
            f"ARQC: {magstripe_data.get('ARQC','')}\n"
            f"ARPC: {magstripe_data.get('ARPC','')}\n"
        )
        self.magstripe_result.setPlainText(text)

    def update_tlv_tree(self, tlv_tree):
        def make_item(node):
            if hasattr(node, "tag"):
                tag = node.tag
                desc = getattr(node, "desc", "")
                value = node.value
                children = getattr(node, "children", [])
            elif isinstance(node, dict):
                tag = node.get("tag", "")
                desc = node.get("desc", "")
                value = node.get("value", "")
                children = node.get("children", [])
            else:
                tag = str(node)
                desc = ""
                value = ""
                children = []
            tag = tag if tag is not None else ""
            desc = desc if desc is not None else ""
            value = value if value is not None else ""
            item = QTreeWidgetItem([str(tag), str(desc), str(value)])
            for child in children or []:
                item.addChild(make_item(child))
            return item

        self.tlv_tree.clear()
        for node in tlv_tree:
            item = make_item(node)
            self.tlv_tree.addTopLevelItem(item)

    def clear_tlv_tree(self):
        self.tlv_tree.clear()

    def update_apdu_log(self, log_entries):
        self.apdu_log.clear()
        for entry in log_entries:
            self.apdu_log.append(entry)

    def show_debug_window(self, logger):
        self.logger = logger
        if not self.debug_dialog:
            self.debug_dialog = QDialog(self.main_widget)
            self.debug_dialog.setWindowTitle("Debug Window")
            dlg_layout = QVBoxLayout(self.debug_dialog)
            self.debug_edit = QTextEdit()
            self.debug_edit.setReadOnly(True)
            self.debug_edit.setStyleSheet(
                "background-color: black; color: lightgray;"
            )
            dlg_layout.addWidget(self.debug_edit)
        self.debug_dialog.show()

    def _append_debug(self):
        if not self.debug_edit or not self.logger:
            return
        entry = self.logger.get_log()[-1]
        if "APDU >>>" in entry:
            color = "red"
        elif "APDU <<<" in entry:
            color = "green"
        else:
            color = "lightgray"
        self.debug_edit.append(f'<span style="color:{color}">{entry}</span>')

    def on_card_selected(self, index):
        pan = self.card_combo.currentText()
        self.main_window.card_manager.switch_card(pan)

    def show_about_dialog(self):
        about_text = (
            "nfsp00f3r V4.04 - EMV Terminal & Card Manager\n\n"
            "By: Gregory King & Matthew Braunschweig\n"
            "Homepage: https://r00t3d.net\n"
            "GitHub: https://github.com/thebringerofdeath789\n\n"
            "A full-featured, multi-protocol EMV terminal and card companion for research, "
            "education, and private use. Features comprehensive EMV/NFC parsing, cryptography, "
            "magstripe emulation, Bluetooth phone sync, relay/replay, PIN management, multi-card, "
            "and more. All core features and APDU flows are ported from best-in-class open-source projects.\n\n"
            "Copyright (C) 2025 Gregory King / r00t3d.net\n"
            "All rights reserved. This software is private and for educational purposes only. "
            "Distribution or commercial use is strictly prohibited."
        )
        QMessageBox.about(self.main_widget, "About nfsp00f3r", about_text)
