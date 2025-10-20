#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Attack Panel GUI
==================================

File: attack_panel.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: PyQt5 Attack Panel for replay and pre-play attacks

Classes:
- AttackPanel: Main attack control panel
- APDULogWidget: APDU flow visualization
- DeviceStatusWidget: Connection status display
"""

import asyncio
import logging
import time
import json
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QComboBox, QPushButton, QTextEdit, QFileDialog,
    QProgressBar, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QCheckBox, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPalette

from attack_manager import AttackManager, AttackMode
from proxmark_usb import ProxmarkUSBRelay
from proxmark_bt import ProxmarkBluetoothRelay
from android_hce import AndroidHCERelay

class DeviceStatusWidget(QWidget):
    """Device connection status display."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout()
        
        # device type selector
        self.device_type_combo = QComboBox()
        self.device_type_combo.addItems([
            "Proxmark USB",
            "Proxmark Bluetooth", 
            "Android HCE"
        ])
        layout.addWidget(QLabel("Device Type:"), 0, 0)
        layout.addWidget(self.device_type_combo, 0, 1)
        
        # connection status
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(QLabel("Status:"), 1, 0)
        layout.addWidget(self.status_label, 1, 1)
        
        # device info
        self.device_info_label = QLabel("No device")
        layout.addWidget(QLabel("Device:"), 2, 0)
        layout.addWidget(self.device_info_label, 2, 1)
        
        # connection buttons
        button_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        
        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        layout.addLayout(button_layout, 3, 0, 1, 2)
        
        self.setLayout(layout)
        
    def update_status(self, connected: bool, device_info: str = ""):
        """Update connection status display."""
        if connected:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.device_info_label.setText(device_info)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        else:
            self.status_label.setText("Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.device_info_label.setText("No device")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)

class APDULogWidget(QWidget):
    """APDU flow visualization and logging."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.apdu_count = 0
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # log controls
        controls_layout = QHBoxLayout()
        
        self.auto_scroll_cb = QCheckBox("Auto Scroll")
        self.auto_scroll_cb.setChecked(True)
        controls_layout.addWidget(self.auto_scroll_cb)
        
        self.max_entries_spin = QSpinBox()
        self.max_entries_spin.setRange(100, 10000)
        self.max_entries_spin.setValue(1000)
        controls_layout.addWidget(QLabel("Max Entries:"))
        controls_layout.addWidget(self.max_entries_spin)
        
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_log)
        controls_layout.addWidget(self.clear_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # apdu table
        self.apdu_table = QTableWidget()
        self.apdu_table.setColumnCount(6)
        self.apdu_table.setHorizontalHeaderLabels([
            "Time", "Direction", "APDU", "Response", "Attack", "Notes"
        ])
        
        # set column widths
        header = self.apdu_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # styling
        self.apdu_table.setAlternatingRowColors(True)
        self.apdu_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.apdu_table)
        self.setLayout(layout)
        
    def add_apdu_exchange(self, command: str, response: str = "", 
                         attack_type: str = "", notes: str = ""):
        """Add APDU exchange to log."""
        try:
            self.apdu_count += 1
            
            # check max entries limit
            max_entries = self.max_entries_spin.value()
            if self.apdu_table.rowCount() >= max_entries:
                self.apdu_table.removeRow(0)
                
            # add new row
            row = self.apdu_table.rowCount()
            self.apdu_table.insertRow(row)
            
            # populate row data
            timestamp = time.strftime("%H:%M:%S.%f")[:-3]
            
            self.apdu_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.apdu_table.setItem(row, 1, QTableWidgetItem("CMD"))
            self.apdu_table.setItem(row, 2, QTableWidgetItem(command))
            self.apdu_table.setItem(row, 3, QTableWidgetItem(response))
            self.apdu_table.setItem(row, 4, QTableWidgetItem(attack_type))
            self.apdu_table.setItem(row, 5, QTableWidgetItem(notes))
            
            # color coding for attack types
            if attack_type:
                if attack_type.lower() == "replay":
                    color = QColor(255, 255, 0, 100)  # yellow
                elif attack_type.lower() == "preplay":
                    color = QColor(255, 165, 0, 100)  # orange
                else:
                    color = QColor(255, 0, 0, 100)  # red
                    
                for col in range(6):
                    item = self.apdu_table.item(row, col)
                    if item:
                        item.setBackground(color)
                        
            # auto scroll
            if self.auto_scroll_cb.isChecked():
                self.apdu_table.scrollToBottom()
                
        except Exception as e:
            self.logger.error(f"failed to add apdu log: {e}")
            
    def clear_log(self):
        """Clear APDU log."""
        self.apdu_table.setRowCount(0)
        self.apdu_count = 0

class AttackPanel(QWidget):
    """
    Main attack control panel for replay and pre-play attacks.
    Integrates with AttackManager and relay modules.
    """
    
    # signals for main window integration
    attack_started = pyqtSignal(str)  # attack_mode
    attack_stopped = pyqtSignal()
    status_updated = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # core components
        self.attack_manager = AttackManager()
        self.current_relay = None
        
        # relay instances
        self.proxmark_usb = None
        self.proxmark_bt = None
        self.android_hce = None
        
        # ui state
        self.attack_active = False
        
        self.init_ui()
        self.setup_connections()
        self.setup_timer()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # main controls
        controls_group = QGroupBox("Attack Configuration")
        controls_layout = QGridLayout()
        
        # attack mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Disabled", "Replay", "Pre-play"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        controls_layout.addWidget(QLabel("Attack Mode:"), 0, 0)
        controls_layout.addWidget(self.mode_combo, 0, 1)
        
        # file selection
        self.file_label = QLabel("No file selected")
        self.file_btn = QPushButton("Browse...")
        self.file_btn.clicked.connect(self.select_file)
        controls_layout.addWidget(QLabel("Data File:"), 1, 0)
        controls_layout.addWidget(self.file_label, 1, 1)
        controls_layout.addWidget(self.file_btn, 1, 2)
        
        # attack controls
        attack_controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Attack")
        self.start_btn.clicked.connect(self.start_attack)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop Attack")
        self.stop_btn.clicked.connect(self.stop_attack)
        self.stop_btn.setEnabled(False)
        
        attack_controls_layout.addWidget(self.start_btn)
        attack_controls_layout.addWidget(self.stop_btn)
        attack_controls_layout.addStretch()
        
        controls_layout.addLayout(attack_controls_layout, 2, 0, 1, 3)
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # device status and apdu log in splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # device status
        device_group = QGroupBox("Device Status")
        device_layout = QVBoxLayout()
        self.device_status = DeviceStatusWidget()
        device_layout.addWidget(self.device_status)
        device_layout.addStretch()
        device_group.setLayout(device_layout)
        splitter.addWidget(device_group)
        
        # apdu log
        log_group = QGroupBox("APDU Flow")
        log_layout = QVBoxLayout()
        self.apdu_log = APDULogWidget()
        log_layout.addWidget(self.apdu_log)
        log_group.setLayout(log_layout)
        splitter.addWidget(log_group)
        
        # set splitter sizes
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        # statistics
        stats_group = QGroupBox("Attack Statistics")
        stats_layout = QGridLayout()
        
        self.stats_labels = {
            'commands_processed': QLabel("0"),
            'attacks_triggered': QLabel("0"),
            'replay_hits': QLabel("0"),
            'preplay_hits': QLabel("0")
        }
        
        stats_layout.addWidget(QLabel("Commands Processed:"), 0, 0)
        stats_layout.addWidget(self.stats_labels['commands_processed'], 0, 1)
        stats_layout.addWidget(QLabel("Attacks Triggered:"), 0, 2)
        stats_layout.addWidget(self.stats_labels['attacks_triggered'], 0, 3)
        
        stats_layout.addWidget(QLabel("Replay Hits:"), 1, 0)
        stats_layout.addWidget(self.stats_labels['replay_hits'], 1, 1)
        stats_layout.addWidget(QLabel("Pre-play Hits:"), 1, 2)
        stats_layout.addWidget(self.stats_labels['preplay_hits'], 1, 3)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)
        
    def setup_connections(self):
        """Setup signal connections."""
        # attack manager signals
        self.attack_manager.mode_changed.connect(self.on_attack_mode_changed)
        self.attack_manager.session_loaded.connect(self.on_session_loaded)
        self.attack_manager.database_loaded.connect(self.on_database_loaded)
        self.attack_manager.apdu_processed.connect(self.on_apdu_processed)
        self.attack_manager.attack_triggered.connect(self.on_attack_triggered)
        self.attack_manager.error_occurred.connect(self.on_error_occurred)
        
        # device status connections
        self.device_status.connect_btn.clicked.connect(self.connect_device)
        self.device_status.disconnect_btn.clicked.connect(self.disconnect_device)
        
    def setup_timer(self):
        """Setup update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(1000)  # update every second
        
    def on_mode_changed(self, mode_text: str):
        """Handle attack mode change."""
        mode_map = {
            "Disabled": AttackMode.DISABLED,
            "Replay": AttackMode.REPLAY,
            "Pre-play": AttackMode.PREPLAY
        }
        
        if mode_text in mode_map:
            self.attack_manager.set_mode(mode_map[mode_text])
            
        # update ui state
        file_required = mode_text in ["Replay", "Pre-play"]
        self.file_btn.setEnabled(file_required)
        
        if not file_required:
            self.file_label.setText("No file required")
            self.start_btn.setEnabled(mode_text != "Disabled")
        else:
            self.start_btn.setEnabled(False)
            
    def select_file(self):
        """Select data file for attack."""
        mode = self.mode_combo.currentText()
        
        if mode == "Replay":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Session File", "", 
                "JSON Files (*.json);;All Files (*)"
            )
            if file_path:
                if self.attack_manager.load_session(file_path):
                    self.file_label.setText(file_path.split('/')[-1])
                    self.start_btn.setEnabled(True)
                    
        elif mode == "Pre-play":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Database File", "",
                "JSON Files (*.json);;SQLite Files (*.db *.sqlite);;All Files (*)"
            )
            if file_path:
                if self.attack_manager.load_database(file_path):
                    self.file_label.setText(file_path.split('/')[-1])
                    self.start_btn.setEnabled(True)
                    
    def connect_device(self):
        """Connect to selected device."""
        device_type = self.device_status.device_type_combo.currentText()
        
        try:
            if device_type == "Proxmark USB":
                if not self.proxmark_usb:
                    self.proxmark_usb = ProxmarkUSBRelay(self.attack_manager)
                    self._connect_relay_signals(self.proxmark_usb)
                    
                if self.proxmark_usb.connect():
                    self.current_relay = self.proxmark_usb
                    self.device_status.update_status(True, self.proxmark_usb.device_path)
                    
            elif device_type == "Proxmark Bluetooth":
                if not self.proxmark_bt:
                    self.proxmark_bt = ProxmarkBluetoothRelay(self.attack_manager)
                    self._connect_relay_signals(self.proxmark_bt)
                    
                # run async connect in thread
                asyncio.create_task(self._connect_bt_device())
                
            elif device_type == "Android HCE":
                if not self.android_hce:
                    self.android_hce = AndroidHCERelay(self.attack_manager)
                    self._connect_relay_signals(self.android_hce)
                    
                # run async connect in thread
                asyncio.create_task(self._connect_hce_device())
                
        except Exception as e:
            self.logger.error(f"device connection failed: {e}")
            
    async def _connect_bt_device(self):
        """Connect to Bluetooth Proxmark."""
        try:
            if await self.proxmark_bt.connect():
                self.current_relay = self.proxmark_bt
                self.device_status.update_status(True, self.proxmark_bt.device_address)
        except Exception as e:
            self.logger.error(f"bt connection failed: {e}")
            
    async def _connect_hce_device(self):
        """Connect to Android HCE device."""
        try:
            if await self.android_hce.connect():
                self.current_relay = self.android_hce
                self.device_status.update_status(True, self.android_hce.device_address)
        except Exception as e:
            self.logger.error(f"hce connection failed: {e}")
            
    def _connect_relay_signals(self, relay):
        """Connect relay signals to UI."""
        relay.device_connected.connect(lambda addr: self.device_status.update_status(True, addr))
        relay.device_disconnected.connect(lambda: self.device_status.update_status(False))
        relay.apdu_received.connect(lambda apdu: self.apdu_log.add_apdu_exchange(
            apdu.hex().upper(), "", "", "Received"))
        relay.apdu_sent.connect(lambda apdu: self.apdu_log.add_apdu_exchange(
            "", apdu.hex().upper(), "", "Sent"))
        relay.error_occurred.connect(self.on_error_occurred)
        
    def disconnect_device(self):
        """Disconnect current device."""
        if self.current_relay:
            try:
                if hasattr(self.current_relay, 'disconnect'):
                    if asyncio.iscoroutinefunction(self.current_relay.disconnect):
                        asyncio.create_task(self.current_relay.disconnect())
                    else:
                        self.current_relay.disconnect()
                        
                self.current_relay = None
                self.device_status.update_status(False)
                
            except Exception as e:
                self.logger.error(f"device disconnect failed: {e}")
                
    def start_attack(self):
        """Start attack session."""
        try:
            if self.attack_manager.start_session():
                self.attack_active = True
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
                self.mode_combo.setEnabled(False)
                
                mode = self.attack_manager.mode.value
                self.attack_started.emit(mode)
                self.logger.info(f"attack started: {mode}")
                
        except Exception as e:
            self.logger.error(f"attack start failed: {e}")
            
    def stop_attack(self):
        """Stop attack session."""
        try:
            if self.attack_manager.stop_session():
                self.attack_active = False
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.mode_combo.setEnabled(True)
                
                self.attack_stopped.emit()
                self.logger.info("attack stopped")
                
        except Exception as e:
            self.logger.error(f"attack stop failed: {e}")
            
    def update_stats(self):
        """Update attack statistics display."""
        try:
            stats = self.attack_manager.get_stats()
            
            for key, label in self.stats_labels.items():
                if key in stats:
                    label.setText(str(stats[key]))
                    
        except Exception as e:
            self.logger.error(f"stats update failed: {e}")
            
    @pyqtSlot(str)
    def on_attack_mode_changed(self, mode: str):
        """Handle attack mode change signal."""
        self.logger.debug(f"attack mode changed: {mode}")
        
    @pyqtSlot(str, int)
    def on_session_loaded(self, filename: str, exchange_count: int):
        """Handle session loaded signal."""
        self.logger.info(f"session loaded: {filename} ({exchange_count} exchanges)")
        
    @pyqtSlot(str, int)
    def on_database_loaded(self, filename: str, entry_count: int):
        """Handle database loaded signal."""
        self.logger.info(f"database loaded: {filename} ({entry_count} entries)")
        
    @pyqtSlot(str, str, str)
    def on_apdu_processed(self, command: str, response: str, attack_type: str):
        """Handle APDU processed signal."""
        self.apdu_log.add_apdu_exchange(command, response, attack_type, "Attack")
        
    @pyqtSlot(str, dict)
    def on_attack_triggered(self, attack_type: str, details: dict):
        """Handle attack triggered signal."""
        self.logger.info(f"attack triggered: {attack_type} - {details}")
        
    @pyqtSlot(str)
    def on_error_occurred(self, error_msg: str):
        """Handle error signal."""
        self.logger.error(f"attack panel error: {error_msg}")
        self.apdu_log.add_apdu_exchange("", "", "", f"ERROR: {error_msg}")
        
    def get_status(self) -> Dict[str, Any]:
        """Get current panel status."""
        return {
            'attack_active': self.attack_active,
            'attack_mode': self.attack_manager.mode.value,
            'device_connected': self.current_relay is not None,
            'device_type': self.device_status.device_type_combo.currentText(),
            'apdu_count': self.apdu_log.apdu_count
        }
