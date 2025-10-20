#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: ui_mainwindow.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Main application window with all UI components

Classes:
- MainWindow: Main application window
- CardDataWidget: Card data display widget
- ReaderControlWidget: Reader control panel
- TransactionWidget: Transaction controls
- DebugConsoleWidget: Debug output console
- StatusBarWidget: Custom status bar

This module implements the complete user interface for the EMV terminal
application including real-time card reading, transaction simulation,
debug output, and comprehensive data visualization.

All UI elements are organized in a tabbed interface with real-time
updates and proper error handling for all operations.
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QTextEdit, QPlainTextEdit, QLabel, QPushButton,
    QComboBox, QListWidget, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QGroupBox, QFrame,
    QSplitter, QProgressBar, QCheckBox, QSpinBox, QLineEdit,
    QMessageBox, QFileDialog, QInputDialog, QDialog,
    QDialogButtonBox, QFormLayout, QScrollArea, QSlider,
    QMenu, QMenuBar, QStatusBar, QToolBar, QAction,
    QSystemTrayIcon, QApplication
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSettings,
    QSize, QRect, QPoint
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap,
    QTextCharFormat, QSyntaxHighlighter, QTextDocument
)

# Import custom widgets
try:
    from android_widget import AndroidWidget
    ANDROID_WIDGET_AVAILABLE = True
except ImportError:
    ANDROID_WIDGET_AVAILABLE = False
    logging.warning("Android widget not available")

class DebugHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for debug console."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        
        # Error format
        error_format = QTextCharFormat()
        error_format.setForeground(QColor(255, 100, 100))
        error_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\[ERROR\].*', error_format))
        
        # Warning format
        warning_format = QTextCharFormat()
        warning_format.setForeground(QColor(255, 200, 100))
        warning_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\[WARNING\].*', warning_format))
        
        # Info format
        info_format = QTextCharFormat()
        info_format.setForeground(QColor(100, 200, 255))
        self.highlighting_rules.append((r'\[INFO\].*', info_format))
        
        # APDU format
        apdu_format = QTextCharFormat()
        apdu_format.setForeground(QColor(100, 255, 100))
        apdu_format.setFontFamily("Courier New")
        self.highlighting_rules.append((r'APDU [><]{2} [0-9A-F\s]+', apdu_format))
        
        # Hex data format
        hex_format = QTextCharFormat()
        hex_format.setForeground(QColor(200, 200, 255))
        hex_format.setFontFamily("Courier New")
        self.highlighting_rules.append((r'[0-9A-F]{2}(?:\s[0-9A-F]{2})*', hex_format))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to text block."""
        import re
        for pattern, format in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, format)

class CardDataWidget(QWidget):
    """Widget for displaying card data in organized view."""
    
    card_data_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the card data UI."""
        layout = QVBoxLayout(self)
        
        # Card selection
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Card:"))
        self.card_combo = QComboBox()
        self.card_combo.currentTextChanged.connect(self.on_card_changed)
        selection_layout.addWidget(self.card_combo)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_cards)
        selection_layout.addWidget(self.refresh_button)
        
        selection_layout.addStretch()
        layout.addLayout(selection_layout)
        
        # Splitter for card details
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Card overview
        overview_group = QGroupBox("Card Overview")
        overview_layout = QVBoxLayout(overview_group)
        
        self.card_info_table = QTableWidget()
        self.card_info_table.setColumnCount(2)
        self.card_info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.card_info_table.horizontalHeader().setStretchLastSection(True)
        overview_layout.addWidget(self.card_info_table)
        
        splitter.addWidget(overview_group)
        
        # Right side - EMV data
        emv_group = QGroupBox("EMV Data")
        emv_layout = QVBoxLayout(emv_group)
        
        # EMV data tabs
        self.emv_tabs = QTabWidget()

        # Applications tab
        self.applications_tree = QTreeWidget()
        self.applications_tree.setHeaderLabels(["Tag", "Description", "Value"])
        self.emv_tabs.addTab(self.applications_tree, "Applications")

        # TLV Data tab
        self.tlv_tree = QTreeWidget()
        self.tlv_tree.setHeaderLabels(["Tag", "Length", "Value", "Description"])
        self.emv_tabs.addTab(self.tlv_tree, "TLV Data")

        # ODA/Certificates tab
        self.oda_tree = QTreeWidget()
        self.oda_tree.setHeaderLabels(["Type", "Field", "Value"])
        self.emv_tabs.addTab(self.oda_tree, "ODA/Certificates")

        # PIN Block Analysis tab
        pin_widget = QWidget()
        pin_layout = QVBoxLayout(pin_widget)
        
        # PIN block input
        pin_input_group = QGroupBox("PIN Block Analysis")
        pin_input_layout = QVBoxLayout()
        
        # Input fields
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("PIN Block (hex):"))
        self.pin_block_input = QLineEdit()
        self.pin_block_input.setPlaceholderText("Enter 8-byte PIN block in hex (e.g., 041234FFFFFFFFFF)")
        input_row.addWidget(self.pin_block_input)
        
        self.analyze_pin_btn = QPushButton("Analyze PIN Block")
        self.analyze_pin_btn.clicked.connect(self.analyze_pin_block)
        input_row.addWidget(self.analyze_pin_btn)
        
        pin_input_layout.addLayout(input_row)
        
        # Results area
        self.pin_analysis_text = QPlainTextEdit()
        self.pin_analysis_text.setReadOnly(True)
        self.pin_analysis_text.setFont(QFont("Courier New", 10))
        self.pin_analysis_text.setMaximumHeight(200)
        pin_input_layout.addWidget(self.pin_analysis_text)
        
        pin_input_group.setLayout(pin_input_layout)
        pin_layout.addWidget(pin_input_group)
        
        # Multi-card comparison
        comparison_group = QGroupBox("Multi-Card PIN Block Statistics")
        comparison_layout = QVBoxLayout()
        
        self.load_cards_btn = QPushButton("Load Multiple Cards for Analysis")
        self.load_cards_btn.clicked.connect(self.load_multiple_cards)
        comparison_layout.addWidget(self.load_cards_btn)
        
        self.stats_text = QPlainTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier New", 10))
        comparison_layout.addWidget(self.stats_text)
        
        comparison_group.setLayout(comparison_layout)
        pin_layout.addWidget(comparison_group)
        
        self.emv_tabs.addTab(pin_widget, "PIN Block Analysis")

        # Track Data tab
        self.track_text = QPlainTextEdit()
        self.track_text.setFont(QFont("Courier New", 10))
        self.emv_tabs.addTab(self.track_text, "Track Data")

        # Raw Data tab
        self.raw_text = QPlainTextEdit()
        self.raw_text.setFont(QFont("Courier New", 10))
        self.emv_tabs.addTab(self.raw_text, "Raw APDU")

        emv_layout.addWidget(self.emv_tabs)
        splitter.addWidget(emv_group)
        
        layout.addWidget(splitter)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export Card")
        self.export_button.clicked.connect(self.export_card)
        controls_layout.addWidget(self.export_button)
        
        self.clone_button = QPushButton("Clone Card")
        self.clone_button.clicked.connect(self.clone_card)
        controls_layout.addWidget(self.clone_button)
        
        self.analyze_button = QPushButton("Analyze")
        self.analyze_button.clicked.connect(self.analyze_card)
        controls_layout.addWidget(self.analyze_button)
        
        self.send_android_button = QPushButton("Send to Android")
        self.send_android_button.clicked.connect(self.send_to_android)
        self.send_android_button.setEnabled(False)  # Enable when Android connected
        controls_layout.addWidget(self.send_android_button)
        
        controls_layout.addStretch()
        
        self.clear_button = QPushButton("Clear Data")
        self.clear_button.clicked.connect(self.clear_data)
        controls_layout.addWidget(self.clear_button)
        
        layout.addLayout(controls_layout)
    
    def on_card_changed(self, card_name):
        """Handle card selection change."""
        # Signal will be connected by main window
        pass
    
    def update_card_data(self, card_data):
        """Update display with new card data."""
        try:
            # Add card to combo box if not already present
            card_identifier = card_data.get('pan', card_data.get('card_type', 'Unknown Card'))
            if card_identifier and self.card_combo.findText(card_identifier) == -1:
                self.card_combo.addItem(card_identifier)
                self.card_combo.setCurrentText(card_identifier)
            
            # Clear existing data
            self.card_info_table.setRowCount(0)
            self.applications_tree.clear()
            self.tlv_tree.clear()
            self.track_text.clear()
            self.raw_text.clear()
            self.oda_tree.clear()

            if not card_data:
                return

            # Update card overview
            overview_data = [
                ("ATR", card_data.get('atr', 'N/A')),
                ("Type", card_data.get('card_type', 'Unknown')),
                ("PAN", card_data.get('pan', 'N/A')),
                ("Expiry", card_data.get('expiry_date', 'N/A')),
                ("Cardholder", card_data.get('cardholder_name', 'N/A')),
                ("AID", card_data.get('aid', 'N/A')),
                ("Application Label", card_data.get('application_label', 'N/A')),
                ("Read Time", card_data.get('timestamp', 'N/A'))
            ]

            self.card_info_table.setRowCount(len(overview_data))
            for i, (prop, value) in enumerate(overview_data):
                self.card_info_table.setItem(i, 0, QTableWidgetItem(prop))
                self.card_info_table.setItem(i, 1, QTableWidgetItem(str(value)))

            # Update applications
            applications = card_data.get('applications', [])
            for app in applications:
                app_item = QTreeWidgetItem([
                    app.get('aid', 'Unknown'),
                    app.get('label', 'Unknown Application'),
                    ""
                ])
                # Add application details
                for key, value in app.items():
                    if key not in ['aid', 'label']:
                        detail_item = QTreeWidgetItem([key, str(value), ""])
                        app_item.addChild(detail_item)
                self.applications_tree.addTopLevelItem(app_item)
            self.applications_tree.expandAll()

            # Update TLV data
            tlv_data = card_data.get('tlv_data', {})
            for tag, data in tlv_data.items():
                if isinstance(data, dict):
                    value = data.get('value', '')
                    description = data.get('description', '')
                    length = str(len(value) // 2) if value else '0'
                else:
                    value = str(data)
                    description = ''
                    length = str(len(value))
                item = QTreeWidgetItem([tag, length, value, description])
                self.tlv_tree.addTopLevelItem(item)

            # Update ODA/Certificates tab
            oda_data = card_data.get('oda_data', {})
            for oda_type, fields in oda_data.items():
                oda_type_item = QTreeWidgetItem([oda_type, '', ''])
                for field, value in fields.items():
                    oda_type_item.addChild(QTreeWidgetItem(['', field, str(value)]))
                self.oda_tree.addTopLevelItem(oda_type_item)
            self.oda_tree.expandAll()

            # Update track data
            track_data = card_data.get('track_data', {})
            track_text = ""
            for track, data in track_data.items():
                track_text += f"{track}: {data}\n"
            self.track_text.setPlainText(track_text)

            # Update raw APDU data
            raw_data = card_data.get('raw_responses', [])
            raw_text = ""
            for response in raw_data:
                raw_text += f">> {response.get('command', '')}\n"
                raw_text += f"<< {response.get('response', '')}\n\n"
            self.raw_text.setPlainText(raw_text)
            
        except Exception as e:
            self.logger.error(f"Error updating card data: {e}")
    
    def refresh_cards(self):
        """Refresh card list."""
        # Signal will be connected by main window
        pass
    
    def export_card(self):
        """Export current card data."""
        # Signal will be connected by main window
        pass
    
    def clone_card(self):
        """Clone current card."""
        # Signal will be connected by main window
        pass
    
    def analyze_card(self):
        """Analyze current card."""
        # Signal will be connected by main window
        pass
    
    def send_to_android(self):
        """Send current card data to connected Android device."""
        # Signal will be connected by main window
        pass
    
    def clear_data(self):
        """Clear all displayed data."""
        self.card_info_table.setRowCount(0)
        self.applications_tree.clear()
        self.tlv_tree.clear()
        self.track_text.clear()
        self.raw_text.clear()
        
    def analyze_pin_block(self):
        """Analyze PIN block from user input."""
        try:
            pin_hex = self.pin_block_input.text().strip().replace(' ', '')
            if not pin_hex:
                self.pin_analysis_text.setPlainText("Please enter a PIN block in hex format.")
                return
                
            if len(pin_hex) != 16:
                self.pin_analysis_text.setPlainText("PIN block must be exactly 8 bytes (16 hex characters).")
                return
                
            try:
                pin_bytes = bytes.fromhex(pin_hex)
            except ValueError:
                self.pin_analysis_text.setPlainText("Invalid hex format. Please use only 0-9 and A-F characters.")
                return
                
            # Get PAN from current card if available
            pan = ""
            if hasattr(self, 'current_card_data') and self.current_card_data:
                pan = self.current_card_data.get('pan', '')
                
            # For testing, create a dummy EMV card object
            from emv_card import EMVCard
            emv = EMVCard()
            
            analysis = emv.analyze_pin_block(pin_bytes, pan)
            
            # Display results
            result_text = f"PIN Block Analysis:\n"
            result_text += f"{'='*50}\n"
            result_text += f"Raw Hex: {analysis.get('raw_hex', 'N/A')}\n"
            result_text += f"Format: {analysis.get('format', 'Unknown')}\n"
            
            if 'pin_length' in analysis:
                result_text += f"PIN Length: {analysis['pin_length']}\n"
                
            if 'pin_digits' in analysis:
                result_text += f"PIN Digits: {analysis['pin_digits']}\n"
                
            if 'padding' in analysis:
                result_text += f"Padding: {analysis['padding']}\n"
                result_text += f"Padding Valid: {analysis.get('padding_valid', False)}\n"
                
            if 'pan_part' in analysis:
                result_text += f"PAN Part Used: {analysis['pan_part']}\n"
                
            if 'note' in analysis:
                result_text += f"Note: {analysis['note']}\n"
                
            if 'error' in analysis:
                result_text += f"Error: {analysis['error']}\n"
                
            self.pin_analysis_text.setPlainText(result_text)
            
        except Exception as e:
            self.pin_analysis_text.setPlainText(f"Analysis error: {str(e)}")
            
    def load_multiple_cards(self):
        """Load multiple cards for PIN block statistical analysis."""
        try:
            # This would normally load from saved card data files
            # For now, show a placeholder
            self.stats_text.setPlainText(
                "Multi-Card PIN Block Analysis\n"
                "=" * 40 + "\n"
                "Feature: Load multiple card datasets and analyze PIN block patterns\n"
                "Capabilities:\n"
                "- Format distribution (ISO-0, ISO-1, etc.)\n"
                "- PIN length frequency analysis\n"
                "- Padding pattern validation\n"
                "- First byte distribution\n"
                "- Common pattern detection\n"
                "- Cross-card comparison\n\n"
                "To use: Save multiple card readings and use this feature\n"
                "to identify patterns across different cards/issuers."
            )
            
        except Exception as e:
            self.stats_text.setPlainText(f"Error loading cards: {str(e)}")

class ReaderControlWidget(QWidget):
    """Widget for reader control and monitoring."""
    
    reader_selected = pyqtSignal(str)
    start_reading = pyqtSignal(str)
    stop_reading = pyqtSignal()
    refresh_readers = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._readers = []  # Store full reader info
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the reader control UI."""
        layout = QVBoxLayout(self)
        
        # Reader selection
        reader_group = QGroupBox("Card Readers")
        reader_layout = QVBoxLayout(reader_group)
        
        # Reader list
        list_layout = QHBoxLayout()
        list_layout.addWidget(QLabel("Available Readers:"))
        
        self.refresh_readers_button = QPushButton("Refresh")
        self.refresh_readers_button.clicked.connect(self.refresh_readers.emit)
        list_layout.addWidget(self.refresh_readers_button)
        list_layout.addStretch()
        
        reader_layout.addLayout(list_layout)
        
        self.reader_list = QListWidget()
        self.reader_list.itemClicked.connect(self.on_reader_selected)
        reader_layout.addWidget(self.reader_list)
        
        # Reader status
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("Status:"))
        self.reader_status_label = QLabel("No reader selected")
        status_layout.addWidget(self.reader_status_label)
        status_layout.addStretch()
        
        reader_layout.addLayout(status_layout)
        
        layout.addWidget(reader_group)
        
        # Reading controls
        controls_group = QGroupBox("Reading Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Read mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.read_mode_combo = QComboBox()
        self.read_mode_combo.addItems([
            "Single Read",
            "Continuous",
            "Auto-detect",
            "Clone Mode",
            "Emulation"
        ])
        mode_layout.addWidget(self.read_mode_combo)
        mode_layout.addStretch()
        controls_layout.addLayout(mode_layout)
        
        # Auto-read settings
        auto_layout = QHBoxLayout()
        self.auto_read_checkbox = QCheckBox("Auto-read on card insertion")
        auto_layout.addWidget(self.auto_read_checkbox)
        auto_layout.addStretch()
        controls_layout.addLayout(auto_layout)
        
        # Read buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Reading")
        self.start_button.clicked.connect(self.on_start_reading)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Reading")
        self.stop_button.clicked.connect(self.stop_reading.emit)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        button_layout.addStretch()
        controls_layout.addLayout(button_layout)
        
        layout.addWidget(controls_group)
        
        # Card presence indicator
        presence_group = QGroupBox("Card Status")
        presence_layout = QVBoxLayout(presence_group)
        
        self.card_present_label = QLabel("No card detected")
        self.card_present_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        presence_layout.addWidget(self.card_present_label)
        
        self.atr_label = QLabel("ATR: N/A")
        self.atr_label.setFont(QFont("Courier New", 10))
        presence_layout.addWidget(self.atr_label)
        
        layout.addWidget(presence_group)
        
        layout.addStretch()
    
    def on_reader_selected(self, item):
        """Handle reader selection."""
        reader_index = self.reader_list.row(item)
        if 0 <= reader_index < len(self._readers):
            reader_info = self._readers[reader_index]
            self.reader_selected.emit(reader_info['name'])
            self.reader_status_label.setText(f"Selected: {reader_info['description']}")
    
    def on_start_reading(self):
        """Handle start reading button."""
        current_item = self.reader_list.currentItem()
        if current_item:
            reader_index = self.reader_list.row(current_item)
            if 0 <= reader_index < len(self._readers):
                reader_info = self._readers[reader_index]
                self.start_reading.emit(reader_info['name'])
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
    
    def update_readers(self, readers):
        """Update the reader list."""
        self._readers = readers  # Store the full reader info
        self.reader_list.clear()
        for reader in readers:
            self.reader_list.addItem(reader['description'])
    
    def update_card_status(self, present, atr=None):
        """Update card presence status."""
        if present:
            self.card_present_label.setText("Card detected")
            self.card_present_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            if atr:
                # Handle both string and bytes ATR
                if isinstance(atr, bytes):
                    atr_text = atr.hex().upper()
                else:
                    atr_text = str(atr)
                self.atr_label.setText(f"ATR: {atr_text}")
        else:
            self.card_present_label.setText("No card detected")
            self.card_present_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            self.atr_label.setText("ATR: N/A")
    
    def set_reading_state(self, reading):
        """Update UI for reading state."""
        self.start_button.setEnabled(not reading)
        self.stop_button.setEnabled(reading)

class TransactionWidget(QWidget):
    """Widget for transaction simulation and testing."""
    
    transaction_started = pyqtSignal(dict)
    transaction_completed = pyqtSignal(dict)
    run_transaction = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the transaction UI."""
        layout = QVBoxLayout(self)
        
        # Transaction type
        type_group = QGroupBox("Transaction Type")
        type_layout = QVBoxLayout(type_group)
        
        self.transaction_combo = QComboBox()
        self.transaction_combo.addItems([
            "Purchase",
            "Cash Advance", 
            "Refund",
            "Balance Inquiry",
            "PIN Verify",
            "Pre-authorization",
            "Custom Transaction"
        ])
        type_layout.addWidget(self.transaction_combo)
        
        layout.addWidget(type_group)
        
        # Transaction parameters
        params_group = QGroupBox("Parameters")
        params_layout = QFormLayout(params_group)
        
        self.amount_edit = QLineEdit("1000")  # Amount in cents
        params_layout.addRow("Amount (cents):", self.amount_edit)
        
        self.currency_edit = QLineEdit("0840")  # USD
        params_layout.addRow("Currency Code:", self.currency_edit)
        
        self.merchant_id_edit = QLineEdit("123456789")
        params_layout.addRow("Merchant ID:", self.merchant_id_edit)
        
        self.terminal_id_edit = QLineEdit("12345678")
        params_layout.addRow("Terminal ID:", self.terminal_id_edit)
        
        layout.addWidget(params_group)
        
        # EMV parameters
        emv_group = QGroupBox("EMV Parameters")
        emv_layout = QFormLayout(emv_group)
        
        self.tvr_edit = QLineEdit("0000000000")
        emv_layout.addRow("TVR:", self.tvr_edit)
        
        self.tsi_edit = QLineEdit("0000")
        emv_layout.addRow("TSI:", self.tsi_edit)
        
        self.aip_edit = QLineEdit("1800")
        emv_layout.addRow("AIP:", self.aip_edit)
        
        self.iac_default_edit = QLineEdit("0000000000")
        emv_layout.addRow("IAC Default:", self.iac_default_edit)
        
        layout.addWidget(emv_group)
        
        # Transaction controls
        controls_layout = QHBoxLayout()
        
        self.run_button = QPushButton("Run Transaction")
        self.run_button.clicked.connect(self.on_run_transaction)
        controls_layout.addWidget(self.run_button)
        
        self.generate_bulk_button = QPushButton("Generate Bulk")
        self.generate_bulk_button.clicked.connect(self.on_generate_bulk)
        controls_layout.addWidget(self.generate_bulk_button)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Transaction log
        log_group = QGroupBox("Transaction Log")
        log_layout = QVBoxLayout(log_group)
        
        self.transaction_log = QPlainTextEdit()
        self.transaction_log.setFont(QFont("Courier New", 10))
        self.transaction_log.setMaximumBlockCount(1000)
        log_layout.addWidget(self.transaction_log)
        
        layout.addWidget(log_group)
    
    def on_run_transaction(self):
        """Handle run transaction button."""
        transaction_type = self.transaction_combo.currentText()
        
        params = {
            'amount': self.amount_edit.text(),
            'currency': self.currency_edit.text(),
            'merchant_id': self.merchant_id_edit.text(),
            'terminal_id': self.terminal_id_edit.text(),
            'tvr': self.tvr_edit.text(),
            'tsi': self.tsi_edit.text(),
            'aip': self.aip_edit.text(),
            'iac_default': self.iac_default_edit.text()
        }
        
        self.run_transaction.emit(transaction_type, params)
    
    def on_generate_bulk(self):
        """Handle bulk generation."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QComboBox, QPushButton, QCheckBox
        
        # Create bulk transaction dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Bulk Transaction Generation")
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Number of transactions
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Number of transactions:"))
        count_spin = QSpinBox()
        count_spin.setRange(1, 1000)
        count_spin.setValue(10)
        count_layout.addWidget(count_spin)
        layout.addLayout(count_layout)
        
        # Transaction type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Transaction type:"))
        type_combo = QComboBox()
        type_combo.addItems(["Purchase", "Withdrawal", "Inquiry", "Transfer"])
        type_layout.addWidget(type_combo)
        layout.addLayout(type_layout)
        
        # Amount range
        amount_layout = QHBoxLayout()
        amount_layout.addWidget(QLabel("Amount range ($):"))
        min_amount = QSpinBox()
        min_amount.setRange(1, 999999)
        min_amount.setValue(1)
        amount_layout.addWidget(min_amount)
        amount_layout.addWidget(QLabel("to"))
        max_amount = QSpinBox()
        max_amount.setRange(1, 999999)
        max_amount.setValue(100)
        amount_layout.addWidget(max_amount)
        layout.addLayout(amount_layout)
        
        # Options
        random_timing = QCheckBox("Random timing intervals")
        random_timing.setChecked(True)
        layout.addWidget(random_timing)
        
        save_results = QCheckBox("Save results to file")
        save_results.setChecked(True)
        layout.addWidget(save_results)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("Generate")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            # Emit signal with bulk parameters
            params = {
                'count': count_spin.value(),
                'type': type_combo.currentText().lower(),
                'min_amount': min_amount.value(),
                'max_amount': max_amount.value(),
                'random_timing': random_timing.isChecked(),
                'save_results': save_results.isChecked()
            }
            self.run_transaction.emit('bulk', params)
    
    def add_transaction_log(self, message):
        """Add message to transaction log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.transaction_log.appendPlainText(f"[{timestamp}] {message}")

class DebugConsoleWidget(QWidget):
    """Debug console with command input and log display."""
    
    command_entered = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.command_history = []
        self.history_index = -1
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the debug console UI."""
        layout = QVBoxLayout(self)
        
        # Debug output
        self.debug_output = QPlainTextEdit()
        self.debug_output.setFont(QFont("Courier New", 10))
        self.debug_output.setMaximumBlockCount(10000)
        self.debug_output.setReadOnly(True)
        
        # Apply syntax highlighting
        self.highlighter = DebugHighlighter(self.debug_output.document())
        
        layout.addWidget(self.debug_output)
        
        # Command input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(">>>"))
        
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.on_command_entered)
        input_layout.addWidget(self.command_input)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.on_command_entered)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.debug_output.clear)
        controls_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton("Save Log")
        self.save_button.clicked.connect(self.save_log)
        controls_layout.addWidget(self.save_button)
        
        controls_layout.addStretch()
        
        # Debug levels
        controls_layout.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_combo.setCurrentText("INFO")
        controls_layout.addWidget(self.level_combo)
        
        layout.addLayout(controls_layout)
    
    def on_command_entered(self):
        """Handle command input."""
        command = self.command_input.text().strip()
        if command:
            self.command_history.append(command)
            self.history_index = len(self.command_history)
            self.add_debug_message(f">>> {command}")
            self.command_entered.emit(command)
            self.command_input.clear()
    
    def keyPressEvent(self, event):
        """Handle key press events for command history."""
        if event.key() == Qt.Key_Up and self.command_history:
            if self.history_index > 0:
                self.history_index -= 1
                self.command_input.setText(self.command_history[self.history_index])
        elif event.key() == Qt.Key_Down and self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_input.setText(self.command_history[self.history_index])
            else:
                self.history_index = len(self.command_history)
                self.command_input.clear()
        else:
            super().keyPressEvent(event)
    
    def add_debug_message(self, message, level="INFO"):
        """Add debug message to console."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_message = f"[{timestamp}] [{level}] {message}"
        self.debug_output.appendPlainText(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self.debug_output.textCursor()
        cursor.movePosition(cursor.End)
        self.debug_output.setTextCursor(cursor)
    
    def save_log(self):
        """Save debug log to file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Debug Log", "debug_log.txt", "Text Files (*.txt)"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.debug_output.toPlainText())
                self.add_debug_message(f"Log saved to {filename}")
            except Exception as e:
                self.add_debug_message(f"Failed to save log: {e}", "ERROR")

class StatusBarWidget(QStatusBar):
    """Custom status bar with additional indicators."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup status bar indicators."""
        # Main status message
        self.showMessage("Ready")
        
        # Reader status
        self.reader_label = QLabel("Reader: None")
        self.addPermanentWidget(self.reader_label)
        
        # Card status
        self.card_label = QLabel("Card: None")
        self.addPermanentWidget(self.card_label)
        
        # Bluetooth status
        self.bluetooth_label = QLabel("BT: Disconnected")
        self.addPermanentWidget(self.bluetooth_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(150)
        self.progress_bar.setVisible(False)
        self.addPermanentWidget(self.progress_bar)
    
    def update_reader_status(self, reader_name, connected=True):
        """Update reader status."""
        status = "Connected" if connected else "Disconnected"
        self.reader_label.setText(f"Reader: {reader_name} ({status})")
    
    def update_card_status(self, card_present=False, card_type=""):
        """Update card status."""
        if card_present:
            self.card_label.setText(f"Card: {card_type or 'Present'}")
        else:
            self.card_label.setText("Card: None")
    
    def update_bluetooth_status(self, connected=False, devices=0):
        """Update Bluetooth status."""
        if connected:
            self.bluetooth_label.setText(f"BT: Connected ({devices})")
        else:
            self.bluetooth_label.setText("BT: Disconnected")
    
    def show_progress(self, value=0, maximum=100):
        """Show progress bar."""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
        self.progress_bar.setVisible(True)
    
    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.setVisible(False)

class MainWindow(QMainWindow):
    """
    Main application window.
    Coordinates all UI components and application functionality.
    """
    
    def __init__(self, app_instance):
        super().__init__()
        self.app_instance = app_instance
        self.logger = logging.getLogger(__name__)
        self.settings = QSettings('NFSP00F3R', 'EMVTerminal')
        
        # Reader detection storage
        self._detected_readers = []
        
        # UI components
        self.card_widget = None
        self.reader_widget = None
        self.transaction_widget = None
        self.debug_widget = None
        self.status_bar = None
        
        # Timers
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
        self.setup_ui()
        self.restore_settings()
        
        # Auto-refresh readers after UI is fully loaded
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.setSingleShot(True)
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_readers)
        self.auto_refresh_timer.start(500)  # Refresh after 500ms
        
    def auto_refresh_readers(self):
        """Automatically refresh readers on startup."""
        try:
            self.refresh_readers()
            self.logger.info("Auto-refresh readers completed")
        except Exception as e:
            self.logger.error(f"Auto-refresh readers failed: {e}")
        
    def showEvent(self, event):
        """Handle window show event."""
        super().showEvent(event)
        # Refresh readers when window is shown (but not every time)
        if not hasattr(self, '_readers_refreshed_on_show'):
            self._readers_refreshed_on_show = True
            QTimer.singleShot(1000, self.refresh_readers)  # Delay to ensure full initialization
        
    def setup_ui(self):
        """Setup the main window UI."""
        self.setWindowTitle("NFSP00F3R V5.00 - EMV Terminal & Smart Card Manager")
        self.setMinimumSize(1200, 800)
        
        # Central widget with tabs
        central_widget = QTabWidget()
        self.setCentralWidget(central_widget)
        
        # Card Data tab
        self.card_widget = CardDataWidget()
        central_widget.addTab(self.card_widget, "Card Data")
        
        # Reader Control tab
        self.reader_widget = ReaderControlWidget()
        central_widget.addTab(self.reader_widget, "Readers")
        
        # Transaction tab
        self.transaction_widget = TransactionWidget()
        central_widget.addTab(self.transaction_widget, "Transactions")
        
        # Attack Panel tab
        try:
            from attack_panel import AttackPanel
            self.attack_widget = AttackPanel()
            central_widget.addTab(self.attack_widget, "Attack Panel")
            self.logger.info("Attack panel loaded")
        except ImportError as e:
            self.logger.warning(f"Attack panel not available: {e}")
        
        # Security Research tab
        try:
            from security_research_ui import ResearchDashboard
            self.research_widget = ResearchDashboard()
            central_widget.addTab(self.research_widget, "Security Research")
            self.logger.info("Security research UI loaded")
        except ImportError as e:
            self.logger.warning(f"Security research UI not available: {e}")
        
        # Android Companion tab
        if ANDROID_WIDGET_AVAILABLE:
            try:
                self.android_widget = AndroidWidget()
                central_widget.addTab(self.android_widget, "Android Companion")
                self.logger.info("Android companion widget loaded")
            except Exception as e:
                self.logger.warning(f"Android widget failed to load: {e}")
        
        # Debug Console tab
        self.debug_widget = DebugConsoleWidget()
        central_widget.addTab(self.debug_widget, "Debug Console")
        
        # Setup menu bar
        self.setup_menu_bar()
        
        # Setup toolbar
        self.setup_toolbar()
        
        # Setup status bar
        self.status_bar = StatusBarWidget()
        self.setStatusBar(self.status_bar)
        
        # Connect signals (these will be connected by the main application)
        self.connect_signals()
    
    def setup_menu_bar(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Session', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('Open...', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('Export Card Data...', self)
        export_action.setShortcut('Ctrl+E')
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        readers_action = QAction('Detect Readers', self)
        tools_menu.addAction(readers_action)
        
        bluetooth_action = QAction('Bluetooth Settings', self)
        tools_menu.addAction(bluetooth_action)
        
        tools_menu.addSeparator()
        
        clone_action = QAction('Clone Card', self)
        tools_menu.addAction(clone_action)
        
        emulate_action = QAction('Emulate Card', self)
        tools_menu.addAction(emulate_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        help_action = QAction('Help', self)
        help_action.setShortcut('F1')
        help_menu.addAction(help_action)
    
    def setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = self.addToolBar('Main')
        
        # Reader actions
        detect_action = QAction('Detect Readers', self)
        detect_action.setToolTip('Detect available card readers')
        toolbar.addAction(detect_action)
        
        read_action = QAction('Read Card', self)
        read_action.setToolTip('Start reading card')
        toolbar.addAction(read_action)
        
        stop_action = QAction('Stop', self)
        stop_action.setToolTip('Stop reading')
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        # Transaction actions
        transaction_action = QAction('Transaction', self)
        transaction_action.setToolTip('Run transaction')
        toolbar.addAction(transaction_action)
        
        toolbar.addSeparator()
        
        # Export actions
        export_action = QAction('Export', self)
        export_action.setToolTip('Export card data')
        toolbar.addAction(export_action)
        
        clone_action = QAction('Clone', self)
        clone_action.setToolTip('Clone card')
        toolbar.addAction(clone_action)
    
    def connect_signals(self):
        """Connect widget signals to actual functionality."""
        # Connect reader control signals
        if self.reader_widget and self.app_instance:
            # Connect reader refresh signal
            self.reader_widget.refresh_readers.connect(self.refresh_readers)
            # Connect reader selection signal
            self.reader_widget.reader_selected.connect(self.on_reader_selected)
            # Connect reading control signals
            self.reader_widget.start_reading.connect(self.start_card_reading)
            self.reader_widget.stop_reading.connect(self.stop_card_reading)
            
        # Connect transaction widget signals
        if self.transaction_widget and self.app_instance:
            self.transaction_widget.transaction_started.connect(self.on_transaction_started)
            self.transaction_widget.transaction_completed.connect(self.on_transaction_completed)
            
        # Connect card widget signals
        if self.card_widget and self.app_instance:
            self.card_widget.card_data_updated.connect(self.on_card_data_updated)
            
        # Connect Android widget signals if available
        if hasattr(self, 'android_widget') and self.android_widget:
            self.android_widget.session_export_requested.connect(self.handle_android_export)
            self.android_widget.android_connect_requested.connect(self.connect_android_device)
            self.android_widget.android_disconnect_requested.connect(self.disconnect_android_device)
            self.logger.info("Android widget signals connected")
            
        # Connect attack panel signals if available
        if hasattr(self, 'attack_widget') and self.attack_widget:
            self.attack_widget.attack_started.connect(self.on_attack_started)
            self.attack_widget.attack_stopped.connect(self.on_attack_stopped)
            
        # Connect security research signals if available
        if hasattr(self, 'research_widget') and self.research_widget:
            self.research_widget.analysis_started.connect(self.on_analysis_started)
            self.research_widget.analysis_completed.connect(self.on_analysis_completed)
            
        # Connect menu actions
        self.connect_menu_actions()
        
        self.logger.info("All UI signals connected to business logic")
    
    def connect_menu_actions(self):
        """Connect menu actions to their handlers."""
        menubar = self.menuBar()
        
        # Find and connect File menu actions
        for menu in menubar.children():
            if hasattr(menu, 'title') and menu.title() == 'File':
                for action in menu.actions():
                    if 'New Session' in action.text():
                        action.triggered.connect(self.new_session)
                    elif 'Open' in action.text():
                        action.triggered.connect(self.open_session)
                    elif 'Save' in action.text():
                        action.triggered.connect(self.save_session)
                    elif 'Export' in action.text():
                        action.triggered.connect(self.export_card_data)
                        
        # Find and connect Tools menu actions
        for menu in menubar.children():
            if hasattr(menu, 'title') and menu.title() == 'Tools':
                for action in menu.actions():
                    if 'Detect Readers' in action.text():
                        action.triggered.connect(self.refresh_readers)
                    elif 'Clone Card' in action.text():
                        action.triggered.connect(self.clone_card)
                    elif 'Emulate Card' in action.text():
                        action.triggered.connect(self.emulate_card)
        
        # Connect toolbar actions
        toolbar = self.findChild(QToolBar)
        if toolbar:
            for action in toolbar.actions():
                if 'Detect Readers' in action.text():
                    action.triggered.connect(self.refresh_readers)
                elif 'Read Card' in action.text():
                    action.triggered.connect(self.quick_read_card)
                elif 'Stop' in action.text():
                    action.triggered.connect(self.stop_card_reading)
                elif 'Transaction' in action.text():
                    action.triggered.connect(self.quick_transaction)
                elif 'Export' in action.text():
                    action.triggered.connect(self.export_card_data)
                elif 'Clone' in action.text():
                    action.triggered.connect(self.clone_card)
    
    def handle_android_export(self, export_request: Dict[str, Any]):
        """Handle export request from Android widget."""
        try:
            export_type = export_request.get('type', 'unknown')
            self.logger.info(f"Android export requested: {export_type}")
            
            if export_type == 'current_card':
                # Export current card data
                if hasattr(self.card_widget, 'current_card_data'):
                    card_data = getattr(self.card_widget, 'current_card_data', {})
                    if card_data and hasattr(self, 'android_widget'):
                        self.android_widget.send_session_data({
                            'type': 'single_card',
                            'card_data': card_data,
                            'timestamp': datetime.now().isoformat()
                        })
                        self.add_debug_message("Current card data sent to Android")
                else:
                    self.add_debug_message("No card data available to export", "WARNING")
                    
            elif export_type == 'complete_session':
                # Export complete session data
                session_data = self.get_complete_session_data()
                if session_data and hasattr(self, 'android_widget'):
                    self.android_widget.send_session_data(session_data)
                    self.add_debug_message("Complete session data sent to Android")
                else:
                    self.add_debug_message("No session data available", "WARNING")
                    
            elif export_type == 'apdu_trace':
                # Export APDU trace
                trace_data = self.get_apdu_trace_data()
                if trace_data and hasattr(self, 'android_widget'):
                    self.android_widget.ble_manager.send_apdu_trace_to_android(trace_data)
                    self.add_debug_message("APDU trace sent to Android")
                else:
                    self.add_debug_message("No APDU trace available", "WARNING")
                    
        except Exception as e:
            self.logger.error(f"Android export failed: {e}")
            self.add_debug_message(f"Android export error: {e}", "ERROR")
    
    def get_complete_session_data(self) -> Dict[str, Any]:
        """Get complete session data for Android export."""
        session_data = {
            'session_id': str(id(self)),
            'timestamp': datetime.now().isoformat(),
            'version': '5.0',
            'cards': {},
            'transactions': [],
            'settings': {}
        }
        
        # Add current card data if available
        if hasattr(self.card_widget, 'current_card_data'):
            card_data = getattr(self.card_widget, 'current_card_data', {})
            if card_data:
                session_data['cards']['current'] = card_data
                
        # Add transaction data if available
        if hasattr(self.transaction_widget, 'transaction_history'):
            transactions = getattr(self.transaction_widget, 'transaction_history', [])
            session_data['transactions'] = transactions
            
        return session_data
    
    def get_apdu_trace_data(self) -> List[Dict[str, Any]]:
        """Get APDU trace data for Android export."""
        # This would normally come from the card manager or transaction engine
        # For now, return a placeholder structure
        return [
            {
                'timestamp': datetime.now().isoformat(),
                'command': '00A40400',
                'response': '6F1C840EA0000000031010A50A500842454249545010870101109000',
                'sw1': '90',
                'sw2': '00',
                'description': 'SELECT FILE'
            }
        ]
    
    def send_to_android(self):
        """Send current card data to Android device (button callback)."""
        try:
            if not hasattr(self, 'android_widget') or not self.android_widget:
                self.add_debug_message("Android widget not available", "WARNING")
                return
                
            if not self.android_widget.ble_manager or not self.android_widget.ble_manager.is_connected():
                self.add_debug_message("Android device not connected", "WARNING")
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Not Connected", 
                                  "Please connect to an Android device first.\n"
                                  "Go to the Android Companion tab to scan and connect.")
                return
                
            # Trigger current card export
            self.handle_android_export({'type': 'current_card'})
            
        except Exception as e:
            self.logger.error(f"Send to Android failed: {e}")
            self.add_debug_message(f"Send to Android error: {e}", "ERROR")
    
    def update_status(self):
        """Update status indicators."""
        # This will be called by a timer to update various status indicators
        pass
    
    def add_debug_message(self, message, level="INFO"):
        """Add message to debug console."""
        if self.debug_widget:
            self.debug_widget.add_debug_message(message, level)
    
    def show_about(self):
        """Show about dialog."""
        about_text = """
NFSP00F3R V5.00 - EMV Terminal & Smart Card Manager

A comprehensive tool for EMV card analysis, transaction simulation,
and smart card research.

Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025

Features:
• Multi-reader support (PC/SC, PN532, Proxmark3, etc.)
• Complete EMV data extraction and analysis
• Transaction simulation and replay attacks
• Android companion app integration
• Advanced cryptographic functions

For educational and research purposes only.
        """
        
        QMessageBox.about(self, "About NFSP00F3R", about_text.strip())
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.save_settings()
        
        # Stop all operations
        if self.app_instance:
            self.app_instance.cleanup()
        
        event.accept()
    
    def save_settings(self):
        """Save window settings."""
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
    
    def restore_settings(self):
        """Restore window settings."""
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = self.settings.value('windowState')
        if window_state:
            self.restoreState(window_state)
    
    # UI Handler Methods for Signal Connections
    def refresh_readers(self):
        """Refresh available card readers."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'reader_manager'):
                reader_manager = self.app_instance.reader_manager
                readers = reader_manager.detect_readers()
                
                # Store readers for later lookup
                self._detected_readers = readers
                
                if self.reader_widget:
                    self.reader_widget.update_readers(readers)
                
                self.add_debug_message(f"Found {len(readers)} card readers")
                self.logger.info(f"Refreshed readers, found: {len(readers)}")
            else:
                self.add_debug_message("Reader manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Failed to refresh readers: {e}")
            self.add_debug_message(f"Failed to refresh readers: {e}", "ERROR")
    
    def on_reader_selected(self, reader_name: str):
        """Handle reader selection."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'reader_manager'):
                reader_manager = self.app_instance.reader_manager
                
                # Find the full reader info by name
                reader_info = None
                if hasattr(self, '_detected_readers'):
                    for reader in self._detected_readers:
                        if reader.get('name') == reader_name:
                            reader_info = reader
                            break
                
                if reader_info:
                    if reader_manager.connect_reader(reader_info):
                        self.add_debug_message(f"Connected to reader: {reader_name}")
                        self.logger.info(f"Connected to reader: {reader_name}")
                    else:
                        self.add_debug_message(f"Failed to connect to reader: {reader_name}", "ERROR")
                else:
                    self.add_debug_message(f"Reader info not found for: {reader_name}", "ERROR")
            else:
                self.add_debug_message("Reader manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Reader selection failed: {e}")
            self.add_debug_message(f"Reader selection failed: {e}", "ERROR")
    
    def start_card_reading(self, reader_name: str = None):
        """Start card reading operation."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'card_manager'):
                card_manager = self.app_instance.card_manager
                
                # Start reading from specified or current reader
                result = card_manager.read_card(reader_name)
                
                if result and 'card_data' in result:
                    card_data = result['card_data']
                    
                    # Update card widget with new data
                    if self.card_widget:
                        self.card_widget.update_card_data(card_data)
                    
                    # Update reader status
                    if self.reader_widget:
                        atr = result.get('atr', '')
                        self.reader_widget.update_card_status(True, atr)
                    
                    self.add_debug_message("Card read successfully")
                    self.logger.info("Card reading completed successfully")
                else:
                    self.add_debug_message("No card detected or read failed", "WARNING")
                    
                    # Update reader status
                    if self.reader_widget:
                        self.reader_widget.update_card_status(False)
            else:
                self.add_debug_message("Card manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Card reading failed: {e}")
            self.add_debug_message(f"Card reading failed: {e}", "ERROR")
            
            # Update reader status on error
            if self.reader_widget:
                self.reader_widget.update_card_status(False)
    
    def stop_card_reading(self):
        """Stop card reading operation."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'card_manager'):
                card_manager = self.app_instance.card_manager
                card_manager.stop_reading()
                
                # Update UI state
                if self.reader_widget:
                    self.reader_widget.start_button.setEnabled(True)
                    self.reader_widget.stop_button.setEnabled(False)
                
                self.add_debug_message("Card reading stopped")
                self.logger.info("Card reading stopped")
            else:
                self.add_debug_message("Card manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Failed to stop card reading: {e}")
            self.add_debug_message(f"Failed to stop card reading: {e}", "ERROR")
    
    def on_transaction_started(self, transaction_data: Dict[str, Any]):
        """Handle transaction start."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'transaction_engine'):
                transaction_engine = self.app_instance.transaction_engine
                
                # Start the transaction
                result = transaction_engine.start_transaction(transaction_data)
                
                if result.get('success', False):
                    self.add_debug_message(f"Transaction started: {transaction_data.get('amount', '0.00')}")
                    self.logger.info(f"Transaction started: {transaction_data}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.add_debug_message(f"Transaction failed to start: {error_msg}", "ERROR")
                    
        except Exception as e:
            self.logger.error(f"Transaction start failed: {e}")
            self.add_debug_message(f"Transaction start failed: {e}", "ERROR")
    
    def on_transaction_completed(self, transaction_result: Dict[str, Any]):
        """Handle transaction completion."""
        try:
            self.add_debug_message(f"Transaction completed: {transaction_result.get('status', 'Unknown')}")
            self.logger.info(f"Transaction completed: {transaction_result}")
            
            # Update transaction widget with results
            if self.transaction_widget:
                self.transaction_widget.update_transaction_result(transaction_result)
                
        except Exception as e:
            self.logger.error(f"Transaction completion handling failed: {e}")
            self.add_debug_message(f"Transaction completion failed: {e}", "ERROR")
    
    def on_card_data_updated(self, card_data: Dict[str, Any]):
        """Handle card data updates."""
        try:
            self.add_debug_message("Card data updated in UI")
            self.logger.info("Card data updated")
            
            # Store card data for export
            if not hasattr(self, 'current_session'):
                self.current_session = {}
            self.current_session['card_data'] = card_data
            
        except Exception as e:
            self.logger.error(f"Card data update handling failed: {e}")
    
    def connect_android_device(self, device_address: str, device_name: str):
        """Connect to Android companion device."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'ble_android_manager'):
                ble_manager = self.app_instance.ble_android_manager
                
                if ble_manager.connect_device(device_address):
                    self.add_debug_message(f"Connected to Android device: {device_name}")
                    self.logger.info(f"Connected to Android device: {device_address}")
                else:
                    self.add_debug_message(f"Failed to connect to Android device: {device_name}", "ERROR")
            else:
                self.add_debug_message("BLE Android manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Android connection failed: {e}")
            self.add_debug_message(f"Android connection failed: {e}", "ERROR")
    
    def disconnect_android_device(self):
        """Disconnect from Android companion device."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'ble_android_manager'):
                ble_manager = self.app_instance.ble_android_manager
                ble_manager.disconnect()
                
                self.add_debug_message("Disconnected from Android device")
                self.logger.info("Disconnected from Android device")
            else:
                self.add_debug_message("BLE Android manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Android disconnection failed: {e}")
            self.add_debug_message(f"Android disconnection failed: {e}", "ERROR")
    
    def on_attack_started(self, attack_type: str, attack_params: Dict[str, Any]):
        """Handle attack start."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'attack_manager'):
                attack_manager = self.app_instance.attack_manager
                
                result = attack_manager.start_attack(attack_type, attack_params)
                
                if result.get('success', False):
                    self.add_debug_message(f"Attack started: {attack_type}")
                    self.logger.info(f"Attack started: {attack_type}")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.add_debug_message(f"Attack failed to start: {error_msg}", "ERROR")
            else:
                self.add_debug_message("Attack manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Attack start failed: {e}")
            self.add_debug_message(f"Attack start failed: {e}", "ERROR")
    
    def on_attack_stopped(self, attack_type: str):
        """Handle attack stop."""
        try:
            if self.app_instance and hasattr(self.app_instance, 'attack_manager'):
                attack_manager = self.app_instance.attack_manager
                attack_manager.stop_attack(attack_type)
                
                self.add_debug_message(f"Attack stopped: {attack_type}")
                self.logger.info(f"Attack stopped: {attack_type}")
            else:
                self.add_debug_message("Attack manager not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Attack stop failed: {e}")
            self.add_debug_message(f"Attack stop failed: {e}", "ERROR")
    
    def on_analysis_started(self, analysis_type: str):
        """Handle analysis start."""
        try:
            self.add_debug_message(f"Analysis started: {analysis_type}")
            self.logger.info(f"Analysis started: {analysis_type}")
        except Exception as e:
            self.logger.error(f"Analysis start handling failed: {e}")
    
    def on_analysis_completed(self, analysis_result: Dict[str, Any]):
        """Handle analysis completion."""
        try:
            self.add_debug_message(f"Analysis completed: {analysis_result.get('type', 'Unknown')}")
            self.logger.info(f"Analysis completed: {analysis_result}")
        except Exception as e:
            self.logger.error(f"Analysis completion handling failed: {e}")
    
    # Menu and Toolbar Action Handlers
    def new_session(self):
        """Create a new session."""
        try:
            self.current_session = {}
            if self.card_widget:
                self.card_widget.clear_display()
            self.add_debug_message("New session created")
            self.logger.info("New session created")
        except Exception as e:
            self.logger.error(f"New session creation failed: {e}")
            self.add_debug_message(f"New session creation failed: {e}", "ERROR")
    
    def open_session(self):
        """Open an existing session."""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Open Session File", 
                "", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                import json
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                
                self.current_session = session_data
                
                # Load card data if available
                if 'card_data' in session_data and self.card_widget:
                    self.card_widget.update_card_data(session_data['card_data'])
                
                self.add_debug_message(f"Session loaded from: {file_path}")
                self.logger.info(f"Session loaded from: {file_path}")
                
        except Exception as e:
            self.logger.error(f"Session loading failed: {e}")
            self.add_debug_message(f"Session loading failed: {e}", "ERROR")
    
    def save_session(self):
        """Save current session."""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save Session File", 
                "", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                import json
                session_data = self.get_complete_session_data()
                
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=2)
                
                self.add_debug_message(f"Session saved to: {file_path}")
                self.logger.info(f"Session saved to: {file_path}")
                
        except Exception as e:
            self.logger.error(f"Session saving failed: {e}")
            self.add_debug_message(f"Session saving failed: {e}", "ERROR")
    
    def export_card_data(self):
        """Export card data."""
        try:
            if not hasattr(self, 'current_session') or not self.current_session.get('card_data'):
                self.add_debug_message("No card data available to export", "WARNING")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Export Card Data", 
                "", 
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                import json
                with open(file_path, 'w') as f:
                    json.dump(self.current_session['card_data'], f, indent=2)
                
                self.add_debug_message(f"Card data exported to: {file_path}")
                self.logger.info(f"Card data exported to: {file_path}")
                
        except Exception as e:
            self.logger.error(f"Card data export failed: {e}")
            self.add_debug_message(f"Card data export failed: {e}", "ERROR")
    
    def clone_card(self):
        """Start card cloning operation."""
        try:
            if not hasattr(self, 'current_session') or not self.current_session.get('card_data'):
                self.add_debug_message("No card data available for cloning", "WARNING")
                return
            
            self.add_debug_message("Card cloning started")
            self.logger.info("Card cloning operation started")
            
            # TODO: Implement actual cloning logic
            
        except Exception as e:
            self.logger.error(f"Card cloning failed: {e}")
            self.add_debug_message(f"Card cloning failed: {e}", "ERROR")
    
    def emulate_card(self):
        """Start card emulation."""
        try:
            if not hasattr(self, 'current_session') or not self.current_session.get('card_data'):
                self.add_debug_message("No card data available for emulation", "WARNING")
                return
            
            self.add_debug_message("Card emulation started")
            self.logger.info("Card emulation started")
            
            # TODO: Implement actual emulation logic
            
        except Exception as e:
            self.logger.error(f"Card emulation failed: {e}")
            self.add_debug_message(f"Card emulation failed: {e}", "ERROR")
    
    def quick_read_card(self):
        """Quick card read operation."""
        try:
            current_reader = None
            if self.reader_widget and self.reader_widget.reader_list.currentItem():
                current_reader = self.reader_widget.reader_list.currentItem().text()
            
            if current_reader:
                self.start_card_reading(current_reader)
            else:
                self.add_debug_message("No reader selected for quick read", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Quick read failed: {e}")
            self.add_debug_message(f"Quick read failed: {e}", "ERROR")
    
    def quick_transaction(self):
        """Quick transaction operation."""
        try:
            if self.transaction_widget:
                # Get current transaction parameters
                transaction_data = {
                    'amount': 1000,  # Default $10.00
                    'currency': '0840',  # USD
                    'type': 'purchase'
                }
                self.on_transaction_started(transaction_data)
            else:
                self.add_debug_message("Transaction widget not available", "WARNING")
                
        except Exception as e:
            self.logger.error(f"Quick transaction failed: {e}")
            self.add_debug_message(f"Quick transaction failed: {e}", "ERROR")
    
    def get_complete_session_data(self):
        """Get complete session data for export."""
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'version': '5.0',
            'card_data': getattr(self, 'current_session', {}).get('card_data', {}),
            'transactions': getattr(self, 'current_session', {}).get('transactions', []),
            'settings': {
                'reader_mode': 'auto',
                'debug_enabled': True
            }
        }
        return session_data
