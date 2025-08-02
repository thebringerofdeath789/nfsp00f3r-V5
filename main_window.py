# =====================================================================
# File: main_window.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   MainWindow for nfsp00f3r Qt application. Sets up:
#     - Card list and tabbed views
#     - Toolbar with all action buttons
#     - Debug dock showing APDU logs (sent in red, recv in green)
#   Applies the ThemeManager for gray-scale backgrounds
#   and enforces black text everywhere except in the debug lines.
# =====================================================================

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QListWidget, QTabWidget, QToolBar, QAction,
    QDockWidget, QPlainTextEdit, QWidget, QVBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from theme import ThemeManager
from settings import SettingsManager
from logger import Logger
from card_manager import CardManager
from profile_exporter import ProfileExporter
from emv_transaction import EmvTransaction
from emv_crypto import EmvCrypto
from relay import RelayManager
from bluetooth_api import BluetoothAPI
from hce_manager import HceManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Settings and theming
        self.settings = SettingsManager()
        self.theme = ThemeManager(self.settings)
        self.theme.apply_theme(self)

        # Core managers
        self.logger       = Logger()
        self.card_manager = CardManager(self.logger)
        self.bt_api       = BluetoothAPI()
        self.relay_mgr    = RelayManager(self.card_manager, self.bt_api)
        self.hce_mgr      = HceManager(self.bt_api)
        self.crypto       = EmvCrypto()
        self.transaction  = EmvTransaction(self.crypto)
        self.exporter     = ProfileExporter()

        # Start Bluetooth API
        self.bt_api.start()

        # Build UI
        self.init_ui()

        # Connect core signals
        self.logger.log_updated.connect(self.on_log_updated)
        self.card_manager.card_inserted.connect(self.on_card_inserted)
        self.card_manager.card_removed.connect(self.on_card_removed)
        self.card_manager.card_switched.connect(self.on_card_switched)

    def init_ui(self):
        # Toolbar
        tb = QToolBar("Main Toolbar", self)
        self.addToolBar(tb)

        act_read = QAction("Read Card", self)
        tb.addAction(act_read); act_read.triggered.connect(self.on_read_card)

        act_export = QAction("Export", self)
        tb.addAction(act_export); act_export.triggered.connect(self.on_export_profile)

        act_import = QAction("Import", self)
        tb.addAction(act_import); act_import.triggered.connect(self.on_import_profile)

        act_purchase = QAction("Run Purchase", self)
        tb.addAction(act_purchase); act_purchase.triggered.connect(self.on_run_purchase)

        act_cash = QAction("Run Cash Adv", self)
        tb.addAction(act_cash); act_cash.triggered.connect(self.on_run_cash_advance)

        act_refund = QAction("Run Refund", self)
        tb.addAction(act_refund); act_refund.triggered.connect(self.on_run_refund)

        act_start_relay = QAction("Start Relay", self)
        tb.addAction(act_start_relay); act_start_relay.triggered.connect(self.on_start_relay)

        act_stop_relay = QAction("Stop Relay", self)
        tb.addAction(act_stop_relay); act_stop_relay.triggered.connect(self.relay_mgr.stop_relay)

        act_push_hce = QAction("Push HCE", self)
        tb.addAction(act_push_hce); act_push_hce.triggered.connect(self.on_push_hce)

        act_pull_hce = QAction("Pull HCE", self)
        tb.addAction(act_pull_hce); act_pull_hce.triggered.connect(self.on_pull_hce)

        act_toggle_theme = QAction("Toggle Theme", self)
        tb.addAction(act_toggle_theme); act_toggle_theme.triggered.connect(self.on_toggle_theme)

        act_debug = QAction("Debug", self)
        tb.addAction(act_debug); act_debug.triggered.connect(self.toggle_debug)

        # Central splitter
        splitter = QSplitter(Qt.Horizontal)
        self.cardList = QListWidget()
        splitter.addWidget(self.cardList)
        self.tabs     = QTabWidget()
        # ... set up tabs (Overview, TLV, Apps, Transactions, APDU Log, Relay, HCE)
        splitter.addWidget(self.tabs)
        self.setCentralWidget(splitter)

        # Debug dock
        self.debugDock = QDockWidget("Debug", self)
        self.debugEdit = QPlainTextEdit()
        self.debugEdit.setReadOnly(True)
        # Force black background, black text default; red/green for lines
        self.debugEdit.setStyleSheet("background-color: #000000; color: #000000;")
        self.debugDock.setWidget(self.debugEdit)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.debugDock)
        self.debugDock.hide()

    def toggle_debug(self):
        if self.debugDock.isVisible():
            self.debugDock.hide()
        else:
            self.debugDock.show()

    def on_log_updated(self):
        entry = self.logger.get_log()[-1]
        if entry.startswith("APDU >>>"):
            # Sent commands in red
            self.debugEdit.setTextColor(QColor(255, 0, 0))
        else:
            # Received responses in green
            self.debugEdit.setTextColor(QColor(0, 255, 0))
        self.debugEdit.appendPlainText(entry)

    # Stub implementations for slots:
    def on_read_card(self):            self.card_manager.read_current_card()
    def on_export_profile(self):       pass  # calls exporter.export(...)
    def on_import_profile(self):       pass  # calls exporter.import_profile(...)
    def on_run_purchase(self):         pass  # calls transaction.run_purchase(...)
    def on_run_cash_advance(self):     pass  # ...
    def on_run_refund(self):           pass
    def on_start_relay(self):          pass
    def on_push_hce(self):             pass
    def on_pull_hce(self):             pass
    def on_toggle_theme(self):         self.theme.toggle_theme(); self.theme.apply_theme(self)
    def on_card_inserted(self, card):  self.cardList.addItem(card.pan)
    def on_card_removed(self, pan):    [self.cardList.takeItem(i) for i in range(self.cardList.count()) if self.cardList.item(i).text()==pan]
    def on_card_switched(self, card):   pass
