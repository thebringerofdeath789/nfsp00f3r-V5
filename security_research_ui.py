#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Advanced Security Research UI Components
===========================================================

File: security_research_ui.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Advanced UI components for security research features

Classes:
- AttackWidget: PIN brute force and timing attack interface
- ReplayWidget: Transaction replay and analysis interface  
- CloningWidget: Card cloning and emulation interface
- FuzzingWidget: APDU fuzzing and testing interface
- CryptogramWidget: Cryptogram analysis and bulk generation
- ResearchDashboard: Comprehensive research dashboard

This module provides specialized UI components for advanced EMV security
research including attack simulations, cryptogram analysis, and hardware
emulation control.
"""

import time
import json
import logging
from typing import Dict, List, Optional, Any
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import numpy as np

class AttackWidget(QWidget):
    """Advanced attack simulation interface."""
    
    attack_started = pyqtSignal(str, dict)  # attack_type, parameters
    attack_stopped = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.active_attacks = set()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup attack interface."""
        layout = QVBoxLayout(self)
        
        # Attack selection
        attack_group = QGroupBox("Attack Type")
        attack_layout = QVBoxLayout(attack_group)
        
        self.attack_tabs = QTabWidget()
        
        # PIN Brute Force tab
        self.setup_pin_brute_force_tab()
        
        # Timing Attack tab
        self.setup_timing_attack_tab()
        
        # DDA Attack tab
        self.setup_dda_attack_tab()
        
        # Side Channel tab
        self.setup_side_channel_tab()
        
        attack_layout.addWidget(self.attack_tabs)
        layout.addWidget(attack_group)
        
        # Results display
        results_group = QGroupBox("Attack Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Attack Type", "Target", "Status", "Progress", "Result", "Timestamp"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.start_attack_button = QPushButton("Start Attack")
        self.start_attack_button.clicked.connect(self.start_selected_attack)
        controls_layout.addWidget(self.start_attack_button)
        
        self.stop_attack_button = QPushButton("Stop All")
        self.stop_attack_button.clicked.connect(self.stop_all_attacks)
        self.stop_attack_button.setEnabled(False)
        controls_layout.addWidget(self.stop_attack_button)
        
        self.export_results_button = QPushButton("Export Results")
        self.export_results_button.clicked.connect(self.export_results)
        controls_layout.addWidget(self.export_results_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
    def setup_pin_brute_force_tab(self):
        """Setup PIN brute force attack tab."""
        pin_widget = QWidget()
        layout = QFormLayout(pin_widget)
        
        # Attack parameters
        self.pin_max_attempts = QSpinBox()
        self.pin_max_attempts.setRange(1, 10)
        self.pin_max_attempts.setValue(3)
        layout.addRow("Max Attempts:", self.pin_max_attempts)
        
        self.pin_delay = QDoubleSpinBox()
        self.pin_delay.setRange(0.1, 10.0)
        self.pin_delay.setValue(1.0)
        self.pin_delay.setSuffix(" seconds")
        layout.addRow("Delay Between Attempts:", self.pin_delay)
        
        # PIN generation strategies
        strategies_group = QGroupBox("PIN Generation Strategies")
        strategies_layout = QVBoxLayout(strategies_group)
        
        self.use_common_pins = QCheckBox("Common PINs (1234, 0000, etc.)")
        self.use_common_pins.setChecked(True)
        strategies_layout.addWidget(self.use_common_pins)
        
        self.use_date_based = QCheckBox("Date-based PINs (from card data)")
        self.use_date_based.setChecked(True)
        strategies_layout.addWidget(self.use_date_based)
        
        self.use_sequential = QCheckBox("Sequential PINs")
        self.use_sequential.setChecked(True)
        strategies_layout.addWidget(self.use_sequential)
        
        self.use_pattern_based = QCheckBox("Pattern-based PINs")
        self.use_pattern_based.setChecked(True)
        strategies_layout.addWidget(self.use_pattern_based)
        
        layout.addRow(strategies_group)
        
        # Custom PIN list
        self.custom_pins = QTextEdit()
        self.custom_pins.setMaximumHeight(100)
        self.custom_pins.setPlaceholderText("Enter custom PINs, one per line...")
        layout.addRow("Custom PINs:", self.custom_pins)
        
        self.attack_tabs.addTab(pin_widget, "PIN Brute Force")
        
    def setup_timing_attack_tab(self):
        """Setup timing attack analysis tab."""
        timing_widget = QWidget()
        layout = QFormLayout(timing_widget)
        
        # Timing parameters
        self.timing_samples = QSpinBox()
        self.timing_samples.setRange(100, 10000)
        self.timing_samples.setValue(1000)
        layout.addRow("Number of Samples:", self.timing_samples)
        
        self.timing_command = QComboBox()
        self.timing_command.addItems([
            "VERIFY PIN",
            "GENERATE AC",
            "INTERNAL AUTHENTICATE",
            "GET CHALLENGE",
            "Custom APDU"
        ])
        layout.addRow("Target Command:", self.timing_command)
        
        self.custom_apdu = QLineEdit()
        self.custom_apdu.setPlaceholderText("Enter custom APDU (hex)")
        layout.addRow("Custom APDU:", self.custom_apdu)
        
        # Analysis options
        analysis_group = QGroupBox("Analysis Options")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.statistical_analysis = QCheckBox("Statistical Analysis")
        self.statistical_analysis.setChecked(True)
        analysis_layout.addWidget(self.statistical_analysis)
        
        self.histogram_display = QCheckBox("Timing Histogram")
        self.histogram_display.setChecked(True)
        analysis_layout.addWidget(self.histogram_display)
        
        self.outlier_detection = QCheckBox("Outlier Detection")
        self.outlier_detection.setChecked(True)
        analysis_layout.addWidget(self.outlier_detection)
        
        layout.addRow(analysis_group)
        
        self.attack_tabs.addTab(timing_widget, "Timing Analysis")
        
    def setup_dda_attack_tab(self):
        """Setup DDA (Dynamic Data Authentication) attack tab."""
        dda_widget = QWidget()
        layout = QFormLayout(dda_widget)
        
        # DDA attack parameters
        self.dda_attack_type = QComboBox()
        self.dda_attack_type.addItems([
            "Certificate Chain Analysis",
            "Key Recovery Attack",
            "Signature Forgery",
            "Weak Random Analysis"
        ])
        layout.addRow("Attack Type:", self.dda_attack_type)
        
        self.dda_iterations = QSpinBox()
        self.dda_iterations.setRange(10, 1000)
        self.dda_iterations.setValue(100)
        layout.addRow("Iterations:", self.dda_iterations)
        
        # Target selection
        self.dda_target = QComboBox()
        self.dda_target.addItems([
            "ICC Public Key",
            "Issuer Public Key", 
            "CA Public Key",
            "All Keys"
        ])
        layout.addRow("Target:", self.dda_target)
        
        self.attack_tabs.addTab(dda_widget, "DDA Attack")
        
    def setup_side_channel_tab(self):
        """Setup side channel attack tab."""
        side_widget = QWidget()
        layout = QFormLayout(side_widget)
        
        # Side channel parameters
        self.side_channel_type = QComboBox()
        self.side_channel_type.addItems([
            "Power Analysis",
            "Electromagnetic Analysis", 
            "Fault Injection",
            "Clock Glitching"
        ])
        layout.addRow("Attack Type:", self.side_channel_type)
        
        self.side_channel_duration = QSpinBox()
        self.side_channel_duration.setRange(10, 3600)
        self.side_channel_duration.setValue(300)
        self.side_channel_duration.setSuffix(" seconds")
        layout.addRow("Collection Duration:", self.side_channel_duration)
        
        # Hardware requirements
        hardware_group = QGroupBox("Hardware Requirements")
        hardware_layout = QVBoxLayout(hardware_group)
        
        hardware_info = QLabel("""
        Note: Side channel attacks require specialized hardware:
        • Oscilloscope for power analysis
        • Near-field probe for EM analysis  
        • Voltage glitcher for fault injection
        • Clock manipulation capability
        """)
        hardware_info.setWordWrap(True)
        hardware_layout.addWidget(hardware_info)
        
        layout.addRow(hardware_group)
        
        self.attack_tabs.addTab(side_widget, "Side Channel")
        
    def start_selected_attack(self):
        """Start the selected attack."""
        current_tab = self.attack_tabs.currentIndex()
        
        if current_tab == 0:  # PIN Brute Force
            self.start_pin_brute_force()
        elif current_tab == 1:  # Timing Analysis
            self.start_timing_analysis()
        elif current_tab == 2:  # DDA Attack
            self.start_dda_attack()
        elif current_tab == 3:  # Side Channel
            self.start_side_channel_attack()
            
    def start_pin_brute_force(self):
        """Start PIN brute force attack."""
        parameters = {
            'max_attempts': self.pin_max_attempts.value(),
            'delay': self.pin_delay.value(),
            'strategies': {
                'common': self.use_common_pins.isChecked(),
                'dates': self.use_date_based.isChecked(),
                'sequential': self.use_sequential.isChecked(),
                'patterns': self.use_pattern_based.isChecked()
            },
            'custom_pins': self.custom_pins.toPlainText().split('\n')
        }
        
        self.attack_started.emit("pin_brute_force", parameters)
        self.add_attack_result("PIN Brute Force", "Current Card", "Running", "0%", "", datetime.now())
        
    def start_timing_analysis(self):
        """Start timing analysis attack."""
        parameters = {
            'samples': self.timing_samples.value(),
            'command': self.timing_command.currentText(),
            'custom_apdu': self.custom_apdu.text(),
            'statistical_analysis': self.statistical_analysis.isChecked(),
            'histogram': self.histogram_display.isChecked(),
            'outlier_detection': self.outlier_detection.isChecked()
        }
        
        self.attack_started.emit("timing_analysis", parameters)
        self.add_attack_result("Timing Analysis", "Current Card", "Running", "0%", "", datetime.now())
        
    def start_dda_attack(self):
        """Start DDA attack."""
        parameters = {
            'attack_type': self.dda_attack_type.currentText(),
            'iterations': self.dda_iterations.value(),
            'target': self.dda_target.currentText()
        }
        
        self.attack_started.emit("dda_attack", parameters)
        self.add_attack_result("DDA Attack", self.dda_target.currentText(), "Running", "0%", "", datetime.now())
        
    def start_side_channel_attack(self):
        """Start side channel attack."""
        parameters = {
            'type': self.side_channel_type.currentText(),
            'duration': self.side_channel_duration.value()
        }
        
        # Check hardware requirements
        QMessageBox.warning(self, "Hardware Required", 
                          f"Side channel attack '{parameters['type']}' requires specialized hardware.\n\n"
                          "Please ensure proper equipment is connected before proceeding.")
        
        self.attack_started.emit("side_channel", parameters)
        self.add_attack_result("Side Channel", parameters['type'], "Running", "0%", "", datetime.now())
        
    def add_attack_result(self, attack_type: str, target: str, status: str, 
                         progress: str, result: str, timestamp: datetime):
        """Add attack result to table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        self.results_table.setItem(row, 0, QTableWidgetItem(attack_type))
        self.results_table.setItem(row, 1, QTableWidgetItem(target))
        self.results_table.setItem(row, 2, QTableWidgetItem(status))
        self.results_table.setItem(row, 3, QTableWidgetItem(progress))
        self.results_table.setItem(row, 4, QTableWidgetItem(result))
        self.results_table.setItem(row, 5, QTableWidgetItem(timestamp.strftime("%H:%M:%S")))
        
    def stop_all_attacks(self):
        """Stop all running attacks."""
        for attack in self.active_attacks:
            self.attack_stopped.emit(attack)
        self.active_attacks.clear()
        
    def export_results(self):
        """Export attack results to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Attack Results", 
            f"attack_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            results = []
            for row in range(self.results_table.rowCount()):
                result = {
                    'attack_type': self.results_table.item(row, 0).text(),
                    'target': self.results_table.item(row, 1).text(),
                    'status': self.results_table.item(row, 2).text(),
                    'progress': self.results_table.item(row, 3).text(),
                    'result': self.results_table.item(row, 4).text(),
                    'timestamp': self.results_table.item(row, 5).text()
                }
                results.append(result)
                
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2)

class ReplayWidget(QWidget):
    """Transaction replay and analysis interface."""
    
    replay_started = pyqtSignal(dict)
    capture_started = pyqtSignal()
    capture_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.captured_transactions = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup replay interface."""
        layout = QVBoxLayout(self)
        
        # Capture controls
        capture_group = QGroupBox("Transaction Capture")
        capture_layout = QHBoxLayout(capture_group)
        
        self.start_capture_button = QPushButton("Start Capture")
        self.start_capture_button.clicked.connect(self.start_capture)
        capture_layout.addWidget(self.start_capture_button)
        
        self.stop_capture_button = QPushButton("Stop Capture")
        self.stop_capture_button.clicked.connect(self.stop_capture)
        self.stop_capture_button.setEnabled(False)
        capture_layout.addWidget(self.stop_capture_button)
        
        self.capture_status = QLabel("Ready to capture")
        capture_layout.addWidget(self.capture_status)
        
        capture_layout.addStretch()
        layout.addWidget(capture_group)
        
        # Captured transactions list
        transactions_group = QGroupBox("Captured Transactions")
        transactions_layout = QVBoxLayout(transactions_group)
        
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(5)
        self.transactions_table.setHorizontalHeaderLabels([
            "ID", "Type", "Amount", "Timestamp", "APDU Count"
        ])
        self.transactions_table.horizontalHeader().setStretchLastSection(True)
        transactions_layout.addWidget(self.transactions_table)
        
        layout.addWidget(transactions_group)
        
        # Replay configuration
        replay_group = QGroupBox("Replay Configuration")
        replay_layout = QFormLayout(replay_group)
        
        self.target_reader = QComboBox()
        self.target_reader.addItems(["Auto-detect", "PC/SC Reader", "PN532", "Proxmark3"])
        replay_layout.addRow("Target Reader:", self.target_reader)
        
        self.replay_delay = QDoubleSpinBox()
        self.replay_delay.setRange(0.01, 10.0)
        self.replay_delay.setValue(0.1)
        self.replay_delay.setSuffix(" seconds")
        replay_layout.addRow("Command Delay:", self.replay_delay)
        
        self.modify_transaction = QCheckBox("Modify Transaction Parameters")
        replay_layout.addRow(self.modify_transaction)
        
        # Modification options
        mod_group = QGroupBox("Modifications")
        mod_layout = QFormLayout(mod_group)
        
        self.modify_amount = QCheckBox("Modify Amount")
        mod_layout.addRow(self.modify_amount)
        
        self.amount_delta = QSpinBox()
        self.amount_delta.setRange(-999999, 999999)
        self.amount_delta.setValue(0)
        mod_layout.addRow("Amount Delta (cents):", self.amount_delta)
        
        self.modify_currency = QCheckBox("Modify Currency")
        mod_layout.addRow(self.modify_currency)
        
        self.new_currency = QLineEdit("0840")
        mod_layout.addRow("New Currency Code:", self.new_currency)
        
        replay_layout.addRow(mod_group)
        layout.addWidget(replay_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.replay_button = QPushButton("Replay Selected")
        self.replay_button.clicked.connect(self.replay_selected)
        controls_layout.addWidget(self.replay_button)
        
        self.replay_all_button = QPushButton("Replay All")
        self.replay_all_button.clicked.connect(self.replay_all)
        controls_layout.addWidget(self.replay_all_button)
        
        self.export_button = QPushButton("Export Transactions")
        self.export_button.clicked.connect(self.export_transactions)
        controls_layout.addWidget(self.export_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
    def start_capture(self):
        """Start transaction capture."""
        self.capture_started.emit()
        self.start_capture_button.setEnabled(False)
        self.stop_capture_button.setEnabled(True)
        self.capture_status.setText("Capturing transactions...")
        
    def stop_capture(self):
        """Stop transaction capture."""
        self.capture_stopped.emit()
        self.start_capture_button.setEnabled(True)
        self.stop_capture_button.setEnabled(False)
        self.capture_status.setText(f"Captured {len(self.captured_transactions)} transactions")
        
    def add_captured_transaction(self, transaction_data: Dict[str, Any]):
        """Add captured transaction to list."""
        self.captured_transactions.append(transaction_data)
        
        row = self.transactions_table.rowCount()
        self.transactions_table.insertRow(row)
        
        self.transactions_table.setItem(row, 0, QTableWidgetItem(str(transaction_data.get('id', ''))))
        self.transactions_table.setItem(row, 1, QTableWidgetItem(transaction_data.get('type', '')))
        self.transactions_table.setItem(row, 2, QTableWidgetItem(str(transaction_data.get('amount', ''))))
        self.transactions_table.setItem(row, 3, QTableWidgetItem(transaction_data.get('timestamp', '')))
        self.transactions_table.setItem(row, 4, QTableWidgetItem(str(len(transaction_data.get('apdu_sequence', [])))))
        
    def replay_selected(self):
        """Replay selected transaction."""
        current_row = self.transactions_table.currentRow()
        if current_row >= 0 and current_row < len(self.captured_transactions):
            transaction = self.captured_transactions[current_row]
            self.replay_transaction(transaction)
            
    def replay_all(self):
        """Replay all captured transactions."""
        for transaction in self.captured_transactions:
            self.replay_transaction(transaction)
            
    def replay_transaction(self, transaction: Dict[str, Any]):
        """Replay a specific transaction."""
        replay_config = {
            'transaction': transaction,
            'target_reader': self.target_reader.currentText(),
            'delay': self.replay_delay.value(),
            'modify': self.modify_transaction.isChecked(),
            'modifications': {
                'amount': self.modify_amount.isChecked(),
                'amount_delta': self.amount_delta.value(),
                'currency': self.modify_currency.isChecked(),
                'new_currency': self.new_currency.text()
            }
        }
        
        self.replay_started.emit(replay_config)
        
    def export_transactions(self):
        """Export captured transactions."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Transactions",
            f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.captured_transactions, f, indent=2)

class CloningWidget(QWidget):
    """Card cloning and emulation interface."""
    
    clone_started = pyqtSignal(str, str, str)  # card_id, target_device, profile_name
    emulation_started = pyqtSignal(str, str)   # profile_name, target_device
    emulation_stopped = pyqtSignal(str)        # target_device
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.clone_profiles = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup cloning interface."""
        layout = QVBoxLayout(self)
        
        # Source card selection
        source_group = QGroupBox("Source Card")
        source_layout = QFormLayout(source_group)
        
        self.source_card = QComboBox()
        self.source_card.addItem("Current Card")
        source_layout.addRow("Card:", self.source_card)
        
        self.card_info = QTextEdit()
        self.card_info.setMaximumHeight(100)
        self.card_info.setReadOnly(True)
        source_layout.addRow("Card Info:", self.card_info)
        
        layout.addWidget(source_group)
        
        # Target device selection
        target_group = QGroupBox("Target Device")
        target_layout = QFormLayout(target_group)
        
        self.target_device = QComboBox()
        self.target_device.addItems([
            "Chameleon Mini",
            "Magspoof",
            "Proxmark3",
            "Android HCE",
            "Software Emulation"
        ])
        target_layout.addRow("Device:", self.target_device)
        
        self.device_status = QLabel("Not connected")
        self.device_status.setStyleSheet("color: red;")
        target_layout.addRow("Status:", self.device_status)
        
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self.test_device_connection)
        target_layout.addRow(self.test_connection_button)
        
        layout.addWidget(target_group)
        
        # Clone configuration
        clone_group = QGroupBox("Clone Configuration")
        clone_layout = QFormLayout(clone_group)
        
        self.profile_name = QLineEdit()
        self.profile_name.setText(f"Clone_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        clone_layout.addRow("Profile Name:", self.profile_name)
        
        self.include_tracks = QCheckBox("Include Magnetic Stripe Data")
        self.include_tracks.setChecked(True)
        clone_layout.addRow(self.include_tracks)
        
        self.include_emv = QCheckBox("Include EMV Application Data")
        self.include_emv.setChecked(True)
        clone_layout.addRow(self.include_emv)
        
        self.include_certificates = QCheckBox("Include Certificates")
        self.include_certificates.setChecked(False)
        clone_layout.addRow(self.include_certificates)
        
        layout.addWidget(clone_group)
        
        # Clone profiles list
        profiles_group = QGroupBox("Clone Profiles")
        profiles_layout = QVBoxLayout(profiles_group)
        
        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(4)
        self.profiles_table.setHorizontalHeaderLabels([
            "Profile Name", "Card Type", "Created", "Status"
        ])
        self.profiles_table.horizontalHeader().setStretchLastSection(True)
        profiles_layout.addWidget(self.profiles_table)
        
        layout.addWidget(profiles_group)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.clone_button = QPushButton("Clone Card")
        self.clone_button.clicked.connect(self.clone_card)
        controls_layout.addWidget(self.clone_button)
        
        self.emulate_button = QPushButton("Start Emulation")
        self.emulate_button.clicked.connect(self.start_emulation)
        controls_layout.addWidget(self.emulate_button)
        
        self.stop_emulation_button = QPushButton("Stop Emulation")
        self.stop_emulation_button.clicked.connect(self.stop_emulation)
        self.stop_emulation_button.setEnabled(False)
        controls_layout.addWidget(self.stop_emulation_button)
        
        self.export_profile_button = QPushButton("Export Profile")
        self.export_profile_button.clicked.connect(self.export_profile)
        controls_layout.addWidget(self.export_profile_button)
        
        self.import_profile_button = QPushButton("Import Profile")
        self.import_profile_button.clicked.connect(self.import_profile)
        controls_layout.addWidget(self.import_profile_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
    def test_device_connection(self):
        """Test connection to target device."""
        device = self.target_device.currentText()
        
        # Simulate connection test
        QTimer.singleShot(1000, lambda: self.device_status.setText("Connected"))
        QTimer.singleShot(1000, lambda: self.device_status.setStyleSheet("color: green;"))
        
    def clone_card(self):
        """Start card cloning process."""
        card_id = self.source_card.currentText()
        target_device = self.target_device.currentText()
        profile_name = self.profile_name.text()
        
        if not profile_name:
            QMessageBox.warning(self, "Warning", "Please enter a profile name.")
            return
            
        self.clone_started.emit(card_id, target_device, profile_name)
        
        # Add to profiles table
        row = self.profiles_table.rowCount()
        self.profiles_table.insertRow(row)
        
        self.profiles_table.setItem(row, 0, QTableWidgetItem(profile_name))
        self.profiles_table.setItem(row, 1, QTableWidgetItem("EMV"))
        self.profiles_table.setItem(row, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
        self.profiles_table.setItem(row, 3, QTableWidgetItem("Cloning..."))
        
    def start_emulation(self):
        """Start card emulation."""
        current_row = self.profiles_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a profile to emulate.")
            return
            
        profile_name = self.profiles_table.item(current_row, 0).text()
        target_device = self.target_device.currentText()
        
        self.emulation_started.emit(profile_name, target_device)
        
        self.emulate_button.setEnabled(False)
        self.stop_emulation_button.setEnabled(True)
        
    def stop_emulation(self):
        """Stop card emulation."""
        target_device = self.target_device.currentText()
        self.emulation_stopped.emit(target_device)
        
        self.emulate_button.setEnabled(True)
        self.stop_emulation_button.setEnabled(False)
        
    def export_profile(self):
        """Export selected clone profile."""
        current_row = self.profiles_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Warning", "Please select a profile to export.")
            return
            
        profile_name = self.profiles_table.item(current_row, 0).text()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Clone Profile",
            f"{profile_name}.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            # Export profile data
            QMessageBox.information(self, "Success", f"Profile exported to {file_path}")
            
    def import_profile(self):
        """Import clone profile from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Clone Profile",
            "", "JSON Files (*.json)"
        )
        
        if file_path:
            # Import profile data
            profile_name = os.path.basename(file_path).replace('.json', '')
            
            row = self.profiles_table.rowCount()
            self.profiles_table.insertRow(row)
            
            self.profiles_table.setItem(row, 0, QTableWidgetItem(profile_name))
            self.profiles_table.setItem(row, 1, QTableWidgetItem("Imported"))
            self.profiles_table.setItem(row, 2, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.profiles_table.setItem(row, 3, QTableWidgetItem("Ready"))
            
            QMessageBox.information(self, "Success", f"Profile imported: {profile_name}")

class CryptogramWidget(QWidget):
    """Cryptogram analysis and bulk generation interface."""
    
    bulk_generation_started = pyqtSignal(dict)
    analysis_started = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.cryptogram_database = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup cryptogram analysis interface."""
        layout = QVBoxLayout(self)
        
        # Bulk generation
        generation_group = QGroupBox("Bulk Cryptogram Generation")
        generation_layout = QFormLayout(generation_group)
        
        self.generation_count = QSpinBox()
        self.generation_count.setRange(10, 100000)
        self.generation_count.setValue(1000)
        generation_layout.addRow("Number of Cryptograms:", self.generation_count)
        
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["Purchase", "Cash Advance", "Refund", "Mixed"])
        generation_layout.addRow("Transaction Type:", self.transaction_type)
        
        self.amount_range = QCheckBox("Random Amount Range")
        self.amount_range.setChecked(True)
        generation_layout.addRow(self.amount_range)
        
        self.min_amount = QSpinBox()
        self.min_amount.setRange(1, 999999)
        self.min_amount.setValue(100)
        generation_layout.addRow("Min Amount (cents):", self.min_amount)
        
        self.max_amount = QSpinBox()
        self.max_amount.setRange(1, 999999)
        self.max_amount.setValue(50000)
        generation_layout.addRow("Max Amount (cents):", self.max_amount)
        
        self.generate_button = QPushButton("Generate Cryptograms")
        self.generate_button.clicked.connect(self.start_bulk_generation)
        generation_layout.addRow(self.generate_button)
        
        layout.addWidget(generation_group)
        
        # Analysis options
        analysis_group = QGroupBox("Cryptogram Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        analysis_options = QHBoxLayout()
        
        self.pattern_analysis = QCheckBox("Pattern Analysis")
        self.pattern_analysis.setChecked(True)
        analysis_options.addWidget(self.pattern_analysis)
        
        self.frequency_analysis = QCheckBox("Frequency Analysis")
        self.frequency_analysis.setChecked(True)
        analysis_options.addWidget(self.frequency_analysis)
        
        self.statistical_analysis = QCheckBox("Statistical Analysis")
        self.statistical_analysis.setChecked(True)
        analysis_options.addWidget(self.statistical_analysis)
        
        analysis_layout.addLayout(analysis_options)
        
        self.analyze_button = QPushButton("Analyze Cryptograms")
        self.analyze_button.clicked.connect(self.start_analysis)
        analysis_layout.addWidget(self.analyze_button)
        
        layout.addWidget(analysis_group)
        
        # Cryptogram database
        database_group = QGroupBox("Cryptogram Database")
        database_layout = QVBoxLayout(database_group)
        
        self.cryptogram_table = QTableWidget()
        self.cryptogram_table.setColumnCount(6)
        self.cryptogram_table.setHorizontalHeaderLabels([
            "ARQC", "Amount", "Currency", "PAN", "Transaction Type", "Timestamp"
        ])
        self.cryptogram_table.horizontalHeader().setStretchLastSection(True)
        database_layout.addWidget(self.cryptogram_table)
        
        layout.addWidget(database_group)
        
        # Analysis results
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
    def start_bulk_generation(self):
        """Start bulk cryptogram generation."""
        parameters = {
            'count': self.generation_count.value(),
            'transaction_type': self.transaction_type.currentText(),
            'random_amounts': self.amount_range.isChecked(),
            'min_amount': self.min_amount.value(),
            'max_amount': self.max_amount.value()
        }
        
        self.bulk_generation_started.emit(parameters)
        
    def start_analysis(self):
        """Start cryptogram analysis."""
        analysis_types = []
        
        if self.pattern_analysis.isChecked():
            analysis_types.append('pattern')
        if self.frequency_analysis.isChecked():
            analysis_types.append('frequency')
        if self.statistical_analysis.isChecked():
            analysis_types.append('statistical')
            
        self.analysis_started.emit(analysis_types)
        
    def add_cryptogram(self, cryptogram_data: Dict[str, Any]):
        """Add cryptogram to database."""
        self.cryptogram_database.append(cryptogram_data)
        
        row = self.cryptogram_table.rowCount()
        self.cryptogram_table.insertRow(row)
        
        self.cryptogram_table.setItem(row, 0, QTableWidgetItem(cryptogram_data.get('arqc', '')))
        self.cryptogram_table.setItem(row, 1, QTableWidgetItem(str(cryptogram_data.get('amount', ''))))
        self.cryptogram_table.setItem(row, 2, QTableWidgetItem(cryptogram_data.get('currency', '')))
        self.cryptogram_table.setItem(row, 3, QTableWidgetItem(cryptogram_data.get('pan_masked', '')))
        self.cryptogram_table.setItem(row, 4, QTableWidgetItem(cryptogram_data.get('transaction_type', '')))
        self.cryptogram_table.setItem(row, 5, QTableWidgetItem(cryptogram_data.get('timestamp', '')))
        
    def update_analysis_results(self, results: Dict[str, Any]):
        """Update analysis results display."""
        results_text = f"""
Analysis Results:
================

Total Cryptograms: {results.get('total', 0)}
Unique Cryptograms: {results.get('unique', 0)}
Duplicate Rate: {results.get('duplicate_rate', 0):.2%}

Pattern Analysis:
{results.get('patterns', 'No patterns detected')}

Recommendations:
{results.get('recommendations', 'No recommendations')}
        """
        
        self.results_text.setPlainText(results_text.strip())

class ResearchDashboard(QWidget):
    """Comprehensive security research dashboard."""
    
    analysis_started = pyqtSignal(str)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup research dashboard."""
        layout = QVBoxLayout(self)
        
        # Research tabs
        self.research_tabs = QTabWidget()
        
        # Attack simulation tab
        self.attack_widget = AttackWidget()
        self.research_tabs.addTab(self.attack_widget, "Attack Simulation")
        
        # Transaction replay tab
        self.replay_widget = ReplayWidget()
        self.research_tabs.addTab(self.replay_widget, "Transaction Replay")
        
        # Card cloning tab
        self.cloning_widget = CloningWidget()
        self.research_tabs.addTab(self.cloning_widget, "Card Cloning")
        
        # Cryptogram analysis tab
        self.cryptogram_widget = CryptogramWidget()
        self.research_tabs.addTab(self.cryptogram_widget, "Cryptogram Analysis")
        
        layout.addWidget(self.research_tabs)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Research tools ready")
        layout.addWidget(self.status_bar)
        
    def update_status(self, message: str):
        """Update status bar message."""
        self.status_bar.showMessage(message)
        
    def display_card_analysis(self, card_data: Dict[str, Any]):
        """Display cardholder, magstripe, PIN, and simulated Track2 info in the UI."""
        info = []
        info.append(f"PAN: {card_data.get('pan','')}")
        info.append(f"Expiry: {card_data.get('expiry','')}")
        info.append(f"Service Code: {card_data.get('service_code','')}")
        info.append(f"Discretionary: {card_data.get('discretionary','')}")
        info.append(f"Cardholder Name: {card_data.get('cardholder_name','')}")
        info.append(f"Track2 (HEX): {card_data.get('track2_hex','')}")
        info.append(f"Track2 (ASCII): {card_data.get('track2_ascii','')}")
        info.append(f"Derived Card PIN: {card_data.get('derived_pin','')}")
        info.append(f"Track2 (101 SVC, simulated CVV): {card_data.get('track2_101','')}")
        self.status_bar.showMessage("Card data loaded.")
        # Show in a dedicated text area or dialog
        if hasattr(self, 'card_info_text'):
            self.card_info_text.setPlainText('\n'.join(info))
        else:
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Card Analysis")
            dlg.setText('\n'.join(info))
            dlg.exec_()
