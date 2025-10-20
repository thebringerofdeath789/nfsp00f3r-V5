#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: settings.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Application settings and configuration management

Classes:
- Settings: Main settings management class

Functions:
- load_default_settings(): Load default application settings
- validate_setting(): Validate setting values

This module handles all application settings including reader configurations,
UI preferences, transaction settings, and hardware device parameters.
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from PyQt5.QtCore import QSettings, QStandardPaths

class Settings:
    """
    Manages application settings with persistence and validation.
    Handles all configuration aspects including reader settings, UI preferences,
    and hardware device configurations.
    """
    
    def __init__(self):
        """Initialize settings manager with default values."""
        self.logger = logging.getLogger(__name__)
        
        # Qt settings for system integration
        self.qt_settings = QSettings()
        
        # Default settings dictionary
        self.defaults = {
            # UI Settings
            'ui': {
                'theme': 'light',
                'window_geometry': None,
                'splitter_state': None,
                'font_size': 10,
                'debug_window_geometry': None,
                'auto_read_cards': True,
                'show_sensitive_data': True,
                'log_level': 'INFO'
            },
            
            # Reader Settings
            'readers': {
                'pcsc_enabled': True,
                'pn532_enabled': True,
                'proxmark3_enabled': False,
                'chameleon_enabled': False,
                'magspoof_enabled': False,
                'auto_detect_readers': True,
                'reader_timeout': 5000,
                'card_timeout': 30000,
                'hotplug_monitoring': True
            },
            
            # Transaction Settings
            'transaction': {
                'terminal_type': 0x22,  # Attended online only
                'terminal_capabilities': '0xE0F8C8',
                'additional_terminal_capabilities': '0xF000F0A001',
                'merchant_category_code': '5999',
                'merchant_identifier': 'NFSP00F3R_TERMINAL',
                'terminal_country_code': '0840',  # USA
                'terminal_currency_code': '0840',  # USD
                'terminal_floor_limit': 0,
                'default_pin': '1337',
                'force_offline_pin': True,
                'brute_force_uns': False,
                'un_brute_count': 100,
                'transaction_timeout': 60000
            },
            
            # Bluetooth Settings
            'bluetooth': {
                'enabled': True,
                'auto_connect': False,
                'pairing_timeout': 30000,
                'connection_timeout': 10000,
                'device_name': 'NFSP00F3R_V5',
                'service_uuid': '00001101-0000-1000-8000-00805F9B34FB',
                'secure_connection': True,
                'remembered_devices': []
            },
            
            # Crypto Settings
            'crypto': {
                'use_real_keys': False,
                'key_directory': 'keys',
                'save_derived_keys': True,
                'export_sensitive_data': True,
                'arqc_method': 'method_1',
                'sda_validation': True,
                'dda_validation': True,
                'cda_validation': True
            },
            
            # Export/Import Settings
            'export': {
                'default_directory': 'exports',
                'include_sensitive_data': True,
                'include_apdu_logs': True,
                'include_tlv_data': True,
                'export_format': 'json',
                'auto_backup': True,
                'backup_interval': 3600  # 1 hour
            },
            
            # Replay/Relay Settings
            'replay': {
                'default_device': 'pn532',
                'replay_timeout': 30000,
                'relay_timeout': 60000,
                'auto_approve_transactions': True,
                'emulation_mode': 'hce',
                'track_modifications': True
            },
            
            # MSR Writer Settings
            'msr': {
                'device_path': 'auto',
                'baud_rate': 9600,
                'write_timeout': 5000,
                'verify_write': True,
                'coercivity': 'high',
                'track1_enabled': True,
                'track2_enabled': True,
                'track3_enabled': False
            },
            
            # Logging Settings
            'logging': {
                'file_logging': True,
                'console_logging': True,
                'debug_window_logging': True,
                'apdu_logging': True,
                'max_log_size': 10485760,  # 10MB
                'max_log_files': 5,
                'log_directory': 'logs'
            }
        }
        
        # Current settings (loaded from file or defaults)
        self.settings = {}
        
        # Settings file path
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        self.settings_file = os.path.join(config_dir, 'nfsp00f3r_settings.json')
        
        # Load settings
        self.load()
        
        self.logger.info(f"Settings initialized, file: {self.settings_file}")
    
    def load(self):
        """Load settings from file or use defaults."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Merge with defaults (preserving new default keys)
                self.settings = self._merge_settings(self.defaults, loaded_settings)
                self.logger.info("Settings loaded from file")
            else:
                self.settings = self.defaults.copy()
                self.logger.info("Using default settings")
                
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
            self.settings = self.defaults.copy()
    
    def save(self):
        """Save current settings to file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Settings saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
    
    def get(self, key_path: str, default=None):
        """
        Get a setting value using dot notation (e.g., 'ui.theme').
        
        Args:
            key_path: Dot-separated path to setting
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        try:
            keys = key_path.split('.')
            value = self.settings
            
            for key in keys:
                value = value[key]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set a setting value using dot notation.
        
        Args:
            key_path: Dot-separated path to setting
            value: Value to set
        """
        keys = key_path.split('.')
        settings_ref = self.settings
        
        # Navigate to parent dictionary
        for key in keys[:-1]:
            if key not in settings_ref:
                settings_ref[key] = {}
            settings_ref = settings_ref[key]
        
        # Set the value
        settings_ref[keys[-1]] = value
        
        self.logger.debug(f"Setting {key_path} = {value}")
    
    def _merge_settings(self, defaults: Dict, loaded: Dict) -> Dict:
        """
        Recursively merge loaded settings with defaults.
        
        Args:
            defaults: Default settings dictionary
            loaded: Loaded settings dictionary
            
        Returns:
            Merged settings dictionary
        """
        result = defaults.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = self.defaults.copy()
        self.logger.info("Settings reset to defaults")
    
    def reset_section(self, section: str):
        """Reset a specific settings section to defaults."""
        if section in self.defaults:
            self.settings[section] = self.defaults[section].copy()
            self.logger.info(f"Settings section '{section}' reset to defaults")
    
    def validate_setting(self, key_path: str, value: Any) -> bool:
        """
        Validate a setting value.
        
        Args:
            key_path: Setting path
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules
        validation_rules = {
            'ui.font_size': lambda x: isinstance(x, int) and 8 <= x <= 20,
            'readers.reader_timeout': lambda x: isinstance(x, int) and x > 0,
            'readers.card_timeout': lambda x: isinstance(x, int) and x > 0,
            'transaction.terminal_type': lambda x: isinstance(x, int) and 0 <= x <= 255,
            'bluetooth.pairing_timeout': lambda x: isinstance(x, int) and x > 0,
            'bluetooth.connection_timeout': lambda x: isinstance(x, int) and x > 0,
            'msr.baud_rate': lambda x: x in [9600, 19200, 38400, 57600, 115200],
            'logging.max_log_size': lambda x: isinstance(x, int) and x > 0,
            'logging.max_log_files': lambda x: isinstance(x, int) and x > 0
        }
        
        if key_path in validation_rules:
            return validation_rules[key_path](value)
        
        return True  # No specific validation rule
    
    def get_reader_settings(self) -> Dict[str, Any]:
        """Get all reader-related settings."""
        return self.settings.get('readers', {})
    
    def get_transaction_settings(self) -> Dict[str, Any]:
        """Get all transaction-related settings."""
        return self.settings.get('transaction', {})
    
    def get_bluetooth_settings(self) -> Dict[str, Any]:
        """Get all Bluetooth-related settings."""
        return self.settings.get('bluetooth', {})
    
    def get_crypto_settings(self) -> Dict[str, Any]:
        """Get all crypto-related settings."""
        return self.settings.get('crypto', {})
    
    def add_remembered_device(self, device_info: Dict[str, str]):
        """Add a Bluetooth device to remembered devices."""
        remembered = self.get('bluetooth.remembered_devices', [])
        
        # Check if device already exists
        for device in remembered:
            if device.get('address') == device_info.get('address'):
                return  # Already exists
        
        remembered.append(device_info)
        self.set('bluetooth.remembered_devices', remembered)
        
        self.logger.info(f"Added remembered device: {device_info.get('name', 'Unknown')}")
    
    def remove_remembered_device(self, address: str):
        """Remove a Bluetooth device from remembered devices."""
        remembered = self.get('bluetooth.remembered_devices', [])
        remembered = [dev for dev in remembered if dev.get('address') != address]
        self.set('bluetooth.remembered_devices', remembered)
        
        self.logger.info(f"Removed remembered device: {address}")
    
    def get_window_geometry(self) -> Optional[bytes]:
        """Get main window geometry from Qt settings."""
        return self.qt_settings.value('geometry')
    
    def set_window_geometry(self, geometry: bytes):
        """Save main window geometry to Qt settings."""
        self.qt_settings.setValue('geometry', geometry)
    
    def get_splitter_state(self) -> Optional[bytes]:
        """Get splitter state from Qt settings."""
        return self.qt_settings.value('splitter_state')
    
    def set_splitter_state(self, state: bytes):
        """Save splitter state to Qt settings."""
        self.qt_settings.setValue('splitter_state', state)
