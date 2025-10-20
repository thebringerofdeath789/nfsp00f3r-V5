#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Android BLE Companion Widget
===============================================

File: android_widget.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: UI widget for Android companion app management

Classes:
- AndroidWidget: Main Android companion interface
- DeviceListWidget: BLE device discovery and selection
- SessionManagerWidget: Session export and management
- ConnectionStatusWidget: Real-time connection status

This widget provides the interface for managing BLE connections to Android
companion devices, sending session data, and monitoring communication status.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox,
    QGroupBox, QSplitter, QTextEdit, QFormLayout, QListWidget, QMessageBox
)

from bluetooth_manager_ble import BLEAndroidManager, check_ble_availability, SessionExporter
from card_manager import CardManager

class AndroidWidget(QWidget):
    """Main Android companion management widget."""
    
    # Signals
    session_export_requested = pyqtSignal(dict)  # session_data
    android_connect_requested = pyqtSignal(str, str)  # address, name
    android_disconnect_requested = pyqtSignal()
    
    # --- Batch 2: HCE/BLE integration controls and signals ---
    # New signals for HCE and APDU log integration
    hce_start_requested = pyqtSignal(str, str)  # profile_id, mode
    hce_stop_requested = pyqtSignal()
    apdu_stream_toggle = pyqtSignal(bool)
    export_session_requested = pyqtSignal(str, str)  # session_id, device_id
    ble_connect_requested = pyqtSignal(str)
    ble_disconnect_requested = pyqtSignal(str)

    # --- Batch 3: Hardware Adapter & Permission signals ---
    pn532_connect_requested = pyqtSignal(str, str)  # port, interface
    pn532_disconnect_requested = pyqtSignal()
    pn532_emulate_requested = pyqtSignal(str)  # profile_name
    pn532_stop_emulation_requested = pyqtSignal()
    proxmark_connect_requested = pyqtSignal(str)
    proxmark_disconnect_requested = pyqtSignal()
    proxmark_emulate_requested = pyqtSignal(str)  # profile_name
    proxmark_stop_emulation_requested = pyqtSignal()
    chameleon_connect_requested = pyqtSignal(str)
    chameleon_disconnect_requested = pyqtSignal()
    chameleon_emulate_requested = pyqtSignal(str)  # profile_name
    chameleon_stop_emulation_requested = pyqtSignal()
    magspoof_connect_requested = pyqtSignal(str)
    magspoof_disconnect_requested = pyqtSignal()
    magspoof_emulate_requested = pyqtSignal(str)  # profile_name
    magspoof_stop_emulation_requested = pyqtSignal()
    permission_check_requested = pyqtSignal(str)  # permission type (e.g., 'serial')
    permission_grant_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.ble_manager = None
        # Card manager provides a real source of selectable profiles for the UI
        # (keeps us free from hardcoded placeholders and integrates with the
        # existing desktop card management code).
        try:
            self.card_manager = CardManager()
        except Exception:
            # If the card manager cannot be created for any reason, fall back
            # to a minimal in-memory manager to avoid crashing the UI.
            self.card_manager = None
        self.is_scanning = False
        self.discovered_devices = []
        self.current_session_data = {}
        
        self.setup_ui()
        self.setup_ble_manager()
        
    def setup_ui(self):
        """Setup the Android management interface."""
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Android Companion App")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # BLE status indicator
        self.ble_status_label = QLabel("BLE: Not Available")
        self.ble_status_label.setStyleSheet("color: red; font-weight: bold;")
        header_layout.addWidget(self.ble_status_label)

        # Permission status indicator
        self.permission_status_label = QLabel("Permissions: Unknown")
        self.permission_status_label.setStyleSheet("color: orange; font-weight: bold;")
        header_layout.addWidget(self.permission_status_label)

        # Connection status (desktop view of Android connection)
        self.connection_status = QLabel("Not Connected")
        self.connection_status.setStyleSheet("color: gray; font-weight: bold;")
        header_layout.addWidget(self.connection_status)

        layout.addLayout(header_layout)

        # Main content in splitter
        splitter = QSplitter(Qt.Horizontal)

        # Left panel - Device Discovery
        left_panel = self.create_device_panel()
        splitter.addWidget(left_panel)

        # Right panel - Session Management
        right_panel = self.create_session_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

        # Hardware Adapter Panel (new)
        hardware_group = QGroupBox("Hardware Adapters & Permissions")
        hardware_layout = QVBoxLayout()
        hardware_group.setLayout(hardware_layout)

        # PN532 controls
        pn532_box = QGroupBox("PN532 NFC Reader")
        pn532_layout = QHBoxLayout()
        self.pn532_port_combo = QComboBox()
        self.pn532_port_combo.setEditable(True)
        self.pn532_port_combo.setToolTip("Serial port (auto-detect or enter manually)")
        self.pn532_interface_combo = QComboBox()
        self.pn532_interface_combo.addItems(["uart", "i2c"])
        self.pn532_connect_button = QPushButton("Connect")
        self.pn532_connect_button.clicked.connect(self.on_pn532_connect)
        self.pn532_disconnect_button = QPushButton("Disconnect")
        self.pn532_disconnect_button.clicked.connect(self.on_pn532_disconnect)
        self.pn532_emulate_button = QPushButton("Start Emulation")
        self.pn532_emulate_button.clicked.connect(self.on_pn532_emulate)
        self.pn532_stop_emulation_button = QPushButton("Stop Emulation")
        self.pn532_stop_emulation_button.clicked.connect(self.on_pn532_stop_emulation)
        pn532_layout.addWidget(QLabel("Port:"))
        pn532_layout.addWidget(self.pn532_port_combo)
        pn532_layout.addWidget(QLabel("Interface:"))
        pn532_layout.addWidget(self.pn532_interface_combo)
        pn532_layout.addWidget(self.pn532_connect_button)
        pn532_layout.addWidget(self.pn532_disconnect_button)
        pn532_layout.addWidget(self.pn532_emulate_button)
        pn532_layout.addWidget(self.pn532_stop_emulation_button)
        pn532_box.setLayout(pn532_layout)
        hardware_layout.addWidget(pn532_box)

        # Proxmark controls
        proxmark_box = QGroupBox("Proxmark3")
        proxmark_layout = QHBoxLayout()
        self.proxmark_port_combo = QComboBox()
        self.proxmark_port_combo.setEditable(True)
        self.proxmark_connect_button = QPushButton("Connect")
        self.proxmark_connect_button.clicked.connect(self.on_proxmark_connect)
        self.proxmark_disconnect_button = QPushButton("Disconnect")
        self.proxmark_disconnect_button.clicked.connect(self.on_proxmark_disconnect)
        self.proxmark_emulate_button = QPushButton("Start Emulation")
        self.proxmark_emulate_button.clicked.connect(self.on_proxmark_emulate)
        self.proxmark_stop_emulation_button = QPushButton("Stop Emulation")
        self.proxmark_stop_emulation_button.clicked.connect(self.on_proxmark_stop_emulation)
        proxmark_layout.addWidget(QLabel("Port:"))
        proxmark_layout.addWidget(self.proxmark_port_combo)
        proxmark_layout.addWidget(self.proxmark_connect_button)
        proxmark_layout.addWidget(self.proxmark_disconnect_button)
        proxmark_layout.addWidget(self.proxmark_emulate_button)
        proxmark_layout.addWidget(self.proxmark_stop_emulation_button)
        proxmark_box.setLayout(proxmark_layout)
        hardware_layout.addWidget(proxmark_box)

        # Chameleon Mini controls
        chameleon_box = QGroupBox("Chameleon Mini")
        chameleon_layout = QHBoxLayout()
        self.chameleon_port_combo = QComboBox()
        self.chameleon_port_combo.setEditable(True)
        self.chameleon_connect_button = QPushButton("Connect")
        self.chameleon_connect_button.clicked.connect(self.on_chameleon_connect)
        self.chameleon_disconnect_button = QPushButton("Disconnect")
        self.chameleon_disconnect_button.clicked.connect(self.on_chameleon_disconnect)
        self.chameleon_emulate_button = QPushButton("Start Emulation")
        self.chameleon_emulate_button.clicked.connect(self.on_chameleon_emulate)
        self.chameleon_stop_emulation_button = QPushButton("Stop Emulation")
        self.chameleon_stop_emulation_button.clicked.connect(self.on_chameleon_stop_emulation)
        chameleon_layout.addWidget(QLabel("Port:"))
        chameleon_layout.addWidget(self.chameleon_port_combo)
        chameleon_layout.addWidget(self.chameleon_connect_button)
        chameleon_layout.addWidget(self.chameleon_disconnect_button)
        chameleon_layout.addWidget(self.chameleon_emulate_button)
        chameleon_layout.addWidget(self.chameleon_stop_emulation_button)
        chameleon_box.setLayout(chameleon_layout)
        hardware_layout.addWidget(chameleon_box)

        # Magspoof controls
        magspoof_box = QGroupBox("Magspoof")
        magspoof_layout = QHBoxLayout()
        self.magspoof_port_combo = QComboBox()
        self.magspoof_port_combo.setEditable(True)
        self.magspoof_connect_button = QPushButton("Connect")
        self.magspoof_connect_button.clicked.connect(self.on_magspoof_connect)
        self.magspoof_disconnect_button = QPushButton("Disconnect")
        self.magspoof_disconnect_button.clicked.connect(self.on_magspoof_disconnect)
        self.magspoof_emulate_button = QPushButton("Start Emulation")
        self.magspoof_emulate_button.clicked.connect(self.on_magspoof_emulate)
        self.magspoof_stop_emulation_button = QPushButton("Stop Emulation")
        self.magspoof_stop_emulation_button.clicked.connect(self.on_magspoof_stop_emulation)
        magspoof_layout.addWidget(QLabel("Port:"))
        magspoof_layout.addWidget(self.magspoof_port_combo)
        magspoof_layout.addWidget(self.magspoof_connect_button)
        magspoof_layout.addWidget(self.magspoof_disconnect_button)
        magspoof_layout.addWidget(self.magspoof_emulate_button)
        magspoof_layout.addWidget(self.magspoof_stop_emulation_button)
        magspoof_box.setLayout(magspoof_layout)
        hardware_layout.addWidget(magspoof_box)

        # Permission controls
        permission_box = QGroupBox("Permissions")
        permission_layout = QHBoxLayout()
        self.permission_check_button = QPushButton("Check Serial Permissions")
        self.permission_check_button.clicked.connect(self.on_permission_check)
        self.permission_grant_button = QPushButton("Grant Serial Permissions")
        self.permission_grant_button.clicked.connect(self.on_permission_grant)
        permission_layout.addWidget(self.permission_check_button)
        permission_layout.addWidget(self.permission_grant_button)
        permission_box.setLayout(permission_layout)
        hardware_layout.addWidget(permission_box)

        layout.addWidget(hardware_group)
    self.proxmark_emulate_button = QPushButton("Start Emulation")
    self.proxmark_emulate_button.clicked.connect(self.on_proxmark_emulate)
    self.proxmark_stop_emulation_button = QPushButton("Stop Emulation")
    self.proxmark_stop_emulation_button.clicked.connect(self.on_proxmark_stop_emulation)
    proxmark_layout.addWidget(QLabel("Port:"))
    proxmark_layout.addWidget(self.proxmark_port_combo)
    proxmark_layout.addWidget(self.proxmark_connect_button)
    proxmark_layout.addWidget(self.proxmark_disconnect_button)
    proxmark_layout.addWidget(self.proxmark_emulate_button)
    proxmark_layout.addWidget(self.proxmark_stop_emulation_button)
    hardware_layout.addWidget(proxmark_box)

    # Chameleon Mini controls
    chameleon_box = QGroupBox("Chameleon Mini")
    chameleon_layout = QHBoxLayout(chameleon_box)
    self.chameleon_port_combo = QComboBox()
    self.chameleon_port_combo.setEditable(True)
    self.chameleon_connect_button = QPushButton("Connect")
    self.chameleon_connect_button.clicked.connect(self.on_chameleon_connect)
    self.chameleon_disconnect_button = QPushButton("Disconnect")
    self.chameleon_disconnect_button.clicked.connect(self.on_chameleon_disconnect)
    self.chameleon_emulate_button = QPushButton("Start Emulation")
    self.chameleon_emulate_button.clicked.connect(self.on_chameleon_emulate)
    self.chameleon_stop_emulation_button = QPushButton("Stop Emulation")
    self.chameleon_stop_emulation_button.clicked.connect(self.on_chameleon_stop_emulation)
    chameleon_layout.addWidget(QLabel("Port:"))
    chameleon_layout.addWidget(self.chameleon_port_combo)
    chameleon_layout.addWidget(self.chameleon_connect_button)
    chameleon_layout.addWidget(self.chameleon_disconnect_button)
    chameleon_layout.addWidget(self.chameleon_emulate_button)
    chameleon_layout.addWidget(self.chameleon_stop_emulation_button)
    hardware_layout.addWidget(chameleon_box)

    # Magspoof controls
    magspoof_box = QGroupBox("Magspoof")
    magspoof_layout = QHBoxLayout(magspoof_box)
    self.magspoof_port_combo = QComboBox()
    self.magspoof_port_combo.setEditable(True)
    self.magspoof_connect_button = QPushButton("Connect")
    self.magspoof_connect_button.clicked.connect(self.on_magspoof_connect)
    self.magspoof_disconnect_button = QPushButton("Disconnect")
    self.magspoof_disconnect_button.clicked.connect(self.on_magspoof_disconnect)
    self.magspoof_emulate_button = QPushButton("Start Emulation")
    self.magspoof_emulate_button.clicked.connect(self.on_magspoof_emulate)
    self.magspoof_stop_emulation_button = QPushButton("Stop Emulation")
    self.magspoof_stop_emulation_button.clicked.connect(self.on_magspoof_stop_emulation)
    magspoof_layout.addWidget(QLabel("Port:"))
    magspoof_layout.addWidget(self.magspoof_port_combo)
    magspoof_layout.addWidget(self.magspoof_connect_button)
    magspoof_layout.addWidget(self.magspoof_disconnect_button)
    magspoof_layout.addWidget(self.magspoof_emulate_button)
    magspoof_layout.addWidget(self.magspoof_stop_emulation_button)
    hardware_layout.addWidget(magspoof_box)

    # Permission controls
    permission_box = QGroupBox("Permissions")
    permission_layout = QHBoxLayout(permission_box)
    self.permission_check_button = QPushButton("Check Serial Permissions")
    self.permission_check_button.clicked.connect(self.on_permission_check)
    self.permission_grant_button = QPushButton("Grant Serial Permissions")
    self.permission_grant_button.clicked.connect(self.on_permission_grant)
    permission_layout.addWidget(self.permission_check_button)
    permission_layout.addWidget(self.permission_grant_button)
    hardware_layout.addWidget(permission_box)

    layout.addWidget(hardware_group)
    # --- Hardware Adapter & Permission UI handlers ---
    def on_pn532_connect(self):
        port = self.pn532_port_combo.currentText()
        interface = self.pn532_interface_combo.currentText()
        self.pn532_connect_requested.emit(port, interface)

    def on_pn532_disconnect(self):
        self.pn532_disconnect_requested.emit()

    def on_pn532_emulate(self):
        profile = self.get_selected_profile_id()
        self.pn532_emulate_requested.emit(profile)

    def on_pn532_stop_emulation(self):
        self.pn532_stop_emulation_requested.emit()

    def on_proxmark_connect(self):
        port = self.proxmark_port_combo.currentText()
        self.proxmark_connect_requested.emit(port)

    def on_proxmark_disconnect(self):
        self.proxmark_disconnect_requested.emit()

    def on_proxmark_emulate(self):
        profile = self.get_selected_profile_id()
        self.proxmark_emulate_requested.emit(profile)

    def on_proxmark_stop_emulation(self):
        self.proxmark_stop_emulation_requested.emit()

    def on_chameleon_connect(self):
        port = self.chameleon_port_combo.currentText()
        self.chameleon_connect_requested.emit(port)

    def on_chameleon_disconnect(self):
        self.chameleon_disconnect_requested.emit()

    def on_chameleon_emulate(self):
        profile = self.get_selected_profile_id()
        self.chameleon_emulate_requested.emit(profile)

    def on_chameleon_stop_emulation(self):
        self.chameleon_stop_emulation_requested.emit()

    def on_magspoof_connect(self):
        port = self.magspoof_port_combo.currentText()
        self.magspoof_connect_requested.emit(port)

    def on_magspoof_disconnect(self):
        self.magspoof_disconnect_requested.emit()

    def on_magspoof_emulate(self):
        profile = self.get_selected_profile_id()
        self.magspoof_emulate_requested.emit(profile)

    def on_magspoof_stop_emulation(self):
        self.magspoof_stop_emulation_requested.emit()

    def on_permission_check(self):
        self.permission_check_requested.emit('serial')

    def on_permission_grant(self):
        self.permission_grant_requested.emit('serial')
        
        # Status and controls
        controls_layout = QHBoxLayout()
        
        self.scan_button = QPushButton("Scan for Devices")
        
    def create_device_panel(self) -> QWidget:
        """Create device discovery panel."""
        panel = QGroupBox("Android Devices")
        layout = QVBoxLayout(panel)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.itemClicked.connect(self.on_device_selected)
        layout.addWidget(self.device_list)
        
        # Device info
        info_group = QGroupBox("Device Information")
        info_layout = QFormLayout(info_group)
        
        self.device_name_label = QLabel("Not Selected")
        self.device_address_label = QLabel("Not Selected")
        self.device_rssi_label = QLabel("Not Selected")
        
        info_layout.addRow("Name:", self.device_name_label)
        info_layout.addRow("Address:", self.device_address_label)
        info_layout.addRow("Signal:", self.device_rssi_label)
        
        layout.addWidget(info_group)
        
        # Connection controls
        conn_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.setEnabled(False)
        self.connect_button.clicked.connect(self.connect_to_selected)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self.disconnect_android)
        conn_layout.addWidget(self.connect_button)
        conn_layout.addWidget(self.disconnect_button)
        layout.addLayout(conn_layout)

        return panel
        
    def create_session_panel(self) -> QWidget:
        """Create session management panel."""
        panel = QGroupBox("Session Management")
        layout = QVBoxLayout(panel)

        # Session info
        session_info_group = QGroupBox("Current Session")
        session_info_layout = QFormLayout(session_info_group)

        self.session_status_label = QLabel("No Session Loaded")
        self.session_cards_label = QLabel("0")
        self.session_size_label = QLabel("0 bytes")

        session_info_layout.addRow("Status:", self.session_status_label)
        session_info_layout.addRow("Cards:", self.session_cards_label)
        session_info_layout.addRow("Size:", self.session_size_label)

        layout.addWidget(session_info_group)

        # Profile selector (uses CardManager when available) - avoids placeholders
        profile_group = QGroupBox("Profile / HCE Source")
        pg_layout = QHBoxLayout(profile_group)
        self.profile_combo = QComboBox()
        try:
            if self.card_manager:
                cards = self.card_manager.get_card_list()
                for card_id, display_name, pan_masked, card_type in cards:
                    self.profile_combo.addItem(display_name, card_id)
        except Exception:
            # If something goes wrong while populating, leave empty but usable
            pass
        self.hce_source_combo = QComboBox()
        # Provide sensible source options for HCE operation
        self.hce_source_combo.addItems(["Desktop-backed HCE", "Android-local HCE", "Preplay Profile"])
        pg_layout.addWidget(QLabel("Profile:"))
        pg_layout.addWidget(self.profile_combo)
        pg_layout.addWidget(QLabel("Mode:"))
        pg_layout.addWidget(self.hce_source_combo)
        layout.addWidget(profile_group)

        # HCE controls + Export controls
        hce_controls_group = QGroupBox("HCE Controls")
        hce_layout = QHBoxLayout(hce_controls_group)
        self.hce_toggle_button = QPushButton("Start HCE Emulation")
        self.hce_toggle_button.setCheckable(True)
        self.hce_toggle_button.clicked.connect(lambda: self.on_hce_toggle(self.hce_toggle_button.isChecked()))
        hce_layout.addWidget(self.hce_toggle_button)
        hce_layout.addStretch()
        layout.addWidget(hce_controls_group)

        # Export controls
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout(export_group)

        self.export_current_button = QPushButton("Export Current Card")
        self.export_current_button.clicked.connect(self.export_current_card)
        self.export_current_button.setEnabled(False)
        export_layout.addWidget(self.export_current_button)

        self.export_session_button = QPushButton("Export Complete Session")
        self.export_session_button.clicked.connect(self.export_complete_session)
        self.export_session_button.setEnabled(False)
        export_layout.addWidget(self.export_session_button)

        self.export_trace_button = QPushButton("Export APDU Trace")
        self.export_trace_button.clicked.connect(self.export_apdu_trace)
        self.export_trace_button.setEnabled(False)
        export_layout.addWidget(self.export_trace_button)

        layout.addWidget(export_group)

        # APDU log toggle - control whether APDU stream is shown
        self.apdu_log_toggle = QCheckBox("Show APDU Stream")
        self.apdu_log_toggle.setChecked(False)
        self.apdu_log_toggle.clicked.connect(lambda: self.on_apdu_log_toggle(self.apdu_log_toggle.isChecked()))
        layout.addWidget(self.apdu_log_toggle)

        # Communication log
        log_group = QGroupBox("Communication Log")
        log_layout = QVBoxLayout(log_group)

        self.comm_log = QTextEdit()
        self.comm_log.setMaximumHeight(200)
        self.comm_log.setReadOnly(True)
        log_layout.addWidget(self.comm_log)

        layout.addWidget(log_group)

        return panel
        
    def setup_ble_manager(self):
        """Initialize BLE manager and check availability."""
        try:
            # Check BLE availability
            ble_status = check_ble_availability()
            
            if ble_status['ble_supported']:
                self.ble_manager = BLEAndroidManager(self)
                self.setup_ble_signals()
                self.ble_status_label.setText("BLE: Available")
                self.ble_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.scan_button.setEnabled(True)
                self.logger.info("BLE Android manager initialized")
            else:
                self.ble_status_label.setText("BLE: Not Available")
                self.ble_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.logger.warning("BLE not available - install bleak package")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize BLE manager: {e}")
            self.ble_status_label.setText("BLE: Error")
            self.ble_status_label.setStyleSheet("color: red; font-weight: bold;")
            
    def setup_ble_signals(self):
        """Connect BLE manager signals."""
        if not self.ble_manager:
            return
        self.ble_manager.device_found.connect(self.on_device_found)
        self.ble_manager.android_connected.connect(self.on_android_connected)
        self.ble_manager.android_disconnected.connect(self.on_android_disconnected)
        self.ble_manager.session_sent.connect(self.on_session_sent)
        self.ble_manager.status_changed.connect(self.on_status_changed)
        self.ble_manager.error_occurred.connect(self.on_error_occurred)
        # Connect APDU log toggle signal to handler (sets internal display flag)
        self.apdu_stream_toggle.connect(self.handle_apdu_stream_toggle)
        # Always listen for data_received to persist inbound SESSION_DATA / APDU_TRACE
        try:
            if hasattr(self.ble_manager, 'ble_session') and hasattr(self.ble_manager.ble_session, 'data_received'):
                self.ble_manager.ble_session.data_received.connect(self._on_ble_data_received)
        except Exception:
            # Defensive: BLE session may not yet be initialized or supported in headless test environments
            pass

    def handle_apdu_stream_toggle(self, enabled):
        """Enable or disable APDU log stream display.

        Instead of connecting/disconnecting the BLE data_received signal (which
        can produce duplicate handlers when other listeners are attached), set
        an internal flag that controls whether inbound BLE messages are shown
        in the UI. Persistence still occurs regardless of the display flag.
        """
        try:
            self._show_apdu_log = bool(enabled)
            if self._show_apdu_log:
                self.log_message("APDU log stream enabled")
            else:
                self.log_message("APDU log stream disabled")
        except Exception:
            # Defensive: don't let UI toggles raise
            pass

    def display_apdu_log(self, msg_type, data):
        """Display APDU log messages in comm_log."""
        if msg_type == "APDU_TRACE":
            try:
                apdu_data = json.loads(data.decode("utf-8"))
                for entry in apdu_data.get("trace", []):
                    ts = entry.get("timestamp", "")
                    cmd = entry.get("command", "")
                    resp = entry.get("response", "")
                    sw1 = entry.get("sw1", "")
                    sw2 = entry.get("sw2", "")
                    desc = entry.get("description", "")
                    self.log_message(f"APDU: {cmd} → {resp} (SW: {sw1}{sw2}) {desc}", level="INFO")
            except Exception as e:
                self.log_message(f"APDU log parse error: {e}", level="ERROR")

    def _on_ble_data_received(self, msg_type, data):
        """Internal handler for BLE data_received signal.

        Shows APDU log entries (if applicable) and persists inbound
        SESSION_DATA / APDU_TRACE payloads to disk for auditing.
        """
        try:
            # Display in UI if the APDU stream is enabled
            try:
                if getattr(self, '_show_apdu_log', False):
                    self.display_apdu_log(msg_type, data)
            except Exception:
                # Non-APDU messages or display errors shouldn't stop persistence
                pass

            # Persist the inbound payload for auditing and offline analysis
            try:
                self.persist_received_message(msg_type, data)
            except Exception as e:
                self.log_message(f"Failed to persist inbound BLE message: {e}", level="WARNING")
        except Exception:
            # Be defensive - never raise from a signal handler
            pass

    def persist_received_message(self, msg_type: str, data: bytes):
        """Persist inbound BLE messages to an `exports/` folder adjacent to this module.

        - SESSION_DATA: saved as pretty JSON using session_id if present
        - APDU_TRACE: saved as pretty JSON
        - Others: saved as raw binary
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            exports_dir = os.path.join(base_dir, 'exports')
            os.makedirs(exports_dir, exist_ok=True)

            safe_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            if msg_type == 'SESSION_DATA' or msg_type == 'APDU_TRACE':
                # Try to decode JSON and save prettily
                payload = None
                try:
                    payload = json.loads(data.decode('utf-8'))
                except Exception:
                    # Fall back to raw representation
                    payload = {'raw': data.hex()}

                session_id = payload.get('session_id') if isinstance(payload, dict) else None
                filename = f"{msg_type.lower()}_{session_id or safe_ts}.json"
                path = os.path.join(exports_dir, filename)
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump(payload, fh, indent=2, ensure_ascii=False)
                self.log_message(f"Saved {msg_type} to {path}")
                return path

            # Generic binary save
            filename = f"{msg_type.lower()}_{safe_ts}.bin"
            path = os.path.join(exports_dir, filename)
            with open(path, 'wb') as fh:
                if isinstance(data, (bytes, bytearray)):
                    fh.write(data)
                else:
                    fh.write(str(data).encode('utf-8'))
            self.log_message(f"Saved {msg_type} to {path}")
            return path
        except Exception as e:
            # Ensure we never raise from a signal handler; log and continue
            self.logger.exception(f"Error persisting BLE message: {e}")
            return None

    def start_scan(self):
        """Start scanning for Android devices."""
        if not self.ble_manager or self.is_scanning:
            return
            
        self.is_scanning = True
        self.scan_button.setText("Scanning...")
        self.scan_button.setEnabled(False)
        self.device_list.clear()
        self.discovered_devices.clear()
        
        self.ble_manager.start_android_scan(timeout=10.0)
        
        # Re-enable scan button after timeout
        QTimer.singleShot(11000, self.scan_complete)
        
    def scan_complete(self):
        """Handle scan completion."""
        self.is_scanning = False
        self.scan_button.setText("Scan for Devices")
        self.scan_button.setEnabled(True)
        
    def on_hce_toggle(self, checked):
        """Handle HCE emulation toggle."""
        mode = self.hce_source_combo.currentText()
        profile_id = self.get_selected_profile_id()
        if checked:
            self.hce_toggle_button.setText("Stop HCE Emulation")
            self.hce_start_requested.emit(profile_id, mode)
            self.log_message(f"HCE emulation started (mode: {mode}, profile: {profile_id})")
            # Optionally, call backend to start HCE emulation
            if self.ble_manager and self.ble_manager.is_connected():
                # This would call into android_hce.py or BLE manager as needed
                pass
        else:
            self.hce_toggle_button.setText("Start HCE Emulation")
            self.hce_stop_requested.emit()
            self.log_message("HCE emulation stopped")
            # Optionally, call backend to stop HCE emulation
            if self.ble_manager and self.ble_manager.is_connected():
                pass

    def get_selected_profile_id(self):
        # Return the selected profile id if available; avoid hardcoded placeholders.
        try:
            if hasattr(self, 'profile_combo') and self.profile_combo.count() > 0:
                data = self.profile_combo.currentData()
                if data:
                    return str(data)
            # Fallback to card manager's current card if present
            if self.card_manager:
                current = self.card_manager.get_current_card()
                if current and getattr(current, 'card_id', None):
                    return current.card_id
        except Exception:
            pass
        return 'unknown'

    def get_connected_device_id(self):
        """Return the currently connected Android device address (if any)."""
        try:
            if self.ble_manager and hasattr(self.ble_manager, 'get_connection_info'):
                info = self.ble_manager.get_connection_info()
                if isinstance(info, dict):
                    return info.get('device_address', 'unknown')
        except Exception:
            pass
        return 'unknown'

    def connect_to_selected(self):
        """Connect to selected Android device."""
        if not self.ble_manager:
            return
            
        current_item = self.device_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an Android device first.")
            return
            
        # Find device info
        device_text = current_item.text()
        for device in self.discovered_devices:
            if device['name'] in device_text:
                self.ble_manager.connect_to_android(device['address'], device['name'])
                self.ble_connect_requested.emit(device['address'])
                break
                
    def disconnect_android(self):
        """Disconnect from Android device."""
        if self.ble_manager:
            self.ble_manager.disconnect_android()
            current_item = self.device_list.currentItem()
            if current_item:
                device_text = current_item.text()
                for device in self.discovered_devices:
                    if device['name'] in device_text:
                        self.ble_disconnect_requested.emit(device['address'])
                        break

    def export_current_card(self):
        """Export current card data to Android."""
        if not self.ble_manager or not self.ble_manager.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to an Android device first.")
            return
        # If we have a loaded session, export directly; otherwise ask the
        # surrounding application to provide a session (backwards-compatible).
        if self.current_session_data:
            try:
                # Use the BLE manager to send the session; the BLE layer will
                # call SessionExporter internally as needed.
                self.ble_manager.send_session_to_android(self.current_session_data)
                return
            except Exception as e:
                logging.error(f"Direct export failed: {e}")

        # Fallback: ask parent/owner to prepare session payload
        self.session_export_requested.emit({'type': 'current_card'})
        
    def export_complete_session(self):
        """Export complete session to Android."""
        if not self.ble_manager or not self.ble_manager.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to an Android device first.")
            return
        # If the widget already has a loaded session, send it directly.
        if self.current_session_data:
            try:
                self.ble_manager.send_session_to_android(self.current_session_data)
                # Emit export_session_requested for traceability
                self.export_session_requested.emit(self.current_session_data.get('session_id', 'unknown'), self.get_connected_device_id())
                return
            except Exception as e:
                logging.error(f"Direct session export failed: {e}")

        # Otherwise, request the parent to provide/assemble the complete session
        self.session_export_requested.emit({'type': 'complete_session'})
        
    def export_apdu_trace(self):
        """Export APDU trace to Android."""
        if not self.ble_manager or not self.ble_manager.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to an Android device first.")
            return
        # If we have an APDU trace in the loaded session, send it directly.
        apdu_trace = None
        if self.current_session_data:
            apdu_trace = self.current_session_data.get('apdu_trace')

        if apdu_trace:
            try:
                self.ble_manager.send_apdu_trace_to_android(apdu_trace)
                return
            except Exception as e:
                logging.error(f"Direct APDU trace export failed: {e}")

        # Otherwise, ask the parent for the trace
        self.session_export_requested.emit({'type': 'apdu_trace'})
        
    def send_session_data(self, session_data: Dict[str, Any]):
        """Send session data to connected Android device."""
        if not self.ble_manager or not self.ble_manager.is_connected():
            return
            
        self.current_session_data = session_data
        self.update_session_info()
        
        # Send to Android
        self.ble_manager.send_session_to_android(session_data)
        
    def update_session_info(self):
        """Update session information display."""
        if not self.current_session_data:
            self.session_status_label.setText("No Session Loaded")
            self.session_cards_label.setText("0")
            self.session_size_label.setText("0 bytes")
            return
            
        # Count cards and calculate size
        cards = self.current_session_data.get('cards', [])
        if isinstance(cards, dict):
            card_count = len(cards)
        else:
            card_count = len(cards) if cards else 1
            
        import json
        size_bytes = len(json.dumps(self.current_session_data, indent=None).encode('utf-8'))
        
        self.session_status_label.setText("Session Loaded")
        self.session_cards_label.setText(str(card_count))
        self.session_size_label.setText(f"{size_bytes:,} bytes")
        
    def on_device_found(self, name: str, address: str, rssi: int):
        """Handle discovered Android device."""
        device_info = {
            'name': name,
            'address': address,
            'rssi': rssi
        }
        self.discovered_devices.append(device_info)
        
        # Add to list
        item_text = f"{name} ({address}) - {rssi} dBm"
        self.device_list.addItem(item_text)
        
        self.log_message(f"Found device: {name}")
        
    def on_device_selected(self, item):
        """Handle device selection."""
        device_text = item.text()
        
        # Find device info
        for device in self.discovered_devices:
            if device['name'] in device_text:
                self.device_name_label.setText(device['name'])
                self.device_address_label.setText(device['address'])
                self.device_rssi_label.setText(f"{device['rssi']} dBm")
                self.connect_button.setEnabled(True)
                break
                
    def on_android_connected(self, device_name: str):
        """Handle Android device connection."""
        self.connection_status.setText(f"Connected: {device_name}")
        self.connection_status.setStyleSheet("color: green; font-weight: bold;")
        
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.export_current_button.setEnabled(True)
        self.export_session_button.setEnabled(True)
        self.export_trace_button.setEnabled(True)
        
        self.log_message(f"Connected to {device_name}")
        
    def on_android_disconnected(self):
        """Handle Android device disconnection."""
        self.connection_status.setText("Not Connected")
        self.connection_status.setStyleSheet("color: gray; font-weight: bold;")
        
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.export_current_button.setEnabled(False)
        self.export_session_button.setEnabled(False)
        self.export_trace_button.setEnabled(False)
        
        self.log_message("Disconnected from Android device")
        
    def on_session_sent(self, bytes_sent: int):
        """Handle session data sent confirmation."""
        self.log_message(f"Sent session data: {bytes_sent:,} bytes")
        
    def on_status_changed(self, status: str):
        """Handle BLE status changes."""
        self.log_message(f"Status: {status}")
        
    def on_error_occurred(self, error_msg: str):
        """Handle BLE errors."""
        self.log_message(f"Error: {error_msg}", level="ERROR")
        QMessageBox.warning(self, "BLE Error", error_msg)
        
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to communication log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "orange"
        else:
            color = "black"
            
        formatted_msg = f'<span style="color: gray;">[{timestamp}]</span> <span style="color: {color};">[{level}]</span> {message}'
        self.comm_log.append(formatted_msg)
        
        # Scroll to bottom
        scrollbar = self.comm_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def update_card_data(self, card_data: Dict[str, Any]):
        """Update with new card data for potential export."""
        self.current_card_data = card_data
        if card_data:
            self.export_current_button.setEnabled(self.ble_manager and self.ble_manager.is_connected())

    def on_apdu_log_toggle(self, enabled):
        """Handle APDU log stream toggle."""
        self.apdu_stream_toggle.emit(enabled)
        if enabled:
            self.log_message("APDU log stream enabled")
        else:
            self.log_message("APDU log stream disabled")
