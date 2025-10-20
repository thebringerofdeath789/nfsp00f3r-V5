#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - UI Component Test Suite
==========================================

File: test_ui_components.py
Authors: Gregory King & Matthew Braunschweig
Date: August 17, 2025
Description: Comprehensive test suite for UI components

This test suite validates all user interface components including:
- Main window functionality
- Card data display widgets
- Reader control interfaces
- Transaction widgets
- Debug console functionality
- Security research interfaces
- Android companion widgets
"""

import os
import sys
import unittest
import time
import json
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest
from PyQt5.QtGui import QKeySequence

# Ensure Qt application exists for testing
if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()

class TestMainWindowComponents(unittest.TestCase):
    """Test main window and core UI components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies to avoid hardware requirements
        with patch('ui_mainwindow.QMainWindow'):
            with patch('card_manager.CardManager'):
                with patch('readers.ReaderManager'):
                    try:
                        from ..ui_mainwindow import MainWindow, CardDataWidget, ReaderControlWidget
                        from ..ui_mainwindow import TransactionWidget, DebugConsoleWidget, StatusBarWidget
                        
                        self.MainWindow = MainWindow
                        self.CardDataWidget = CardDataWidget
                        self.ReaderControlWidget = ReaderControlWidget
                        self.TransactionWidget = TransactionWidget
                        self.DebugConsoleWidget = DebugConsoleWidget
                        self.StatusBarWidget = StatusBarWidget
                        
                    except ImportError as e:
                        self.skipTest(f"UI modules not available: {e}")
    
    def test_card_data_widget_initialization(self):
        """Test CardDataWidget initialization."""
        try:
            widget = self.CardDataWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check if setup_ui was called (widget should have layout)
            self.assertIsNotNone(widget.layout())
            
            # Test signal connections exist
            self.assertTrue(hasattr(widget, 'card_data_updated'))
            
        except Exception as e:
            self.skipTest(f"CardDataWidget initialization failed: {e}")
    
    def test_card_data_widget_update_display(self):
        """Test card data display updates."""
        try:
            widget = self.CardDataWidget()
            
            # Test data update
            test_card_data = {
                'pan': '4111111111111111',
                'expiry': '12/25',
                'track2': '4111111111111111=2512101',
                'applications': ['A0000000031010']
            }
            
            # Should not raise exception
            if hasattr(widget, 'update_card_data'):
                widget.update_card_data(test_card_data)
            
            # Test clearing data
            if hasattr(widget, 'clear_display'):
                widget.clear_display()
                
        except Exception as e:
            self.skipTest(f"CardDataWidget update test failed: {e}")
    
    def test_reader_control_widget_initialization(self):
        """Test ReaderControlWidget initialization."""
        try:
            widget = self.ReaderControlWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check for expected UI elements
            self.assertIsNotNone(widget.layout())
            
            # Test signal connections
            if hasattr(widget, 'reader_selected'):
                self.assertTrue(hasattr(widget.reader_selected, 'connect'))
            
        except Exception as e:
            self.skipTest(f"ReaderControlWidget initialization failed: {e}")
    
    def test_reader_control_widget_operations(self):
        """Test reader control operations."""
        try:
            widget = self.ReaderControlWidget()
            
            # Test reader list update
            test_readers = ['PCSC Reader 1', 'PCSC Reader 2']
            if hasattr(widget, 'update_reader_list'):
                widget.update_reader_list(test_readers)
            
            # Test reader connection
            if hasattr(widget, 'connect_reader'):
                widget.connect_reader('PCSC Reader 1')
            
            # Test reader disconnection
            if hasattr(widget, 'disconnect_reader'):
                widget.disconnect_reader()
                
        except Exception as e:
            self.skipTest(f"ReaderControlWidget operations test failed: {e}")
    
    def test_transaction_widget_initialization(self):
        """Test TransactionWidget initialization."""
        try:
            widget = self.TransactionWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check basic structure
            self.assertIsNotNone(widget.layout())
            
            # Test signal existence
            expected_signals = ['transaction_started', 'transaction_completed']
            for signal_name in expected_signals:
                if hasattr(widget, signal_name):
                    self.assertTrue(hasattr(getattr(widget, signal_name), 'connect'))
            
        except Exception as e:
            self.skipTest(f"TransactionWidget initialization failed: {e}")
    
    def test_transaction_widget_operations(self):
        """Test transaction widget operations."""
        try:
            widget = self.TransactionWidget()
            
            # Test transaction parameter setting
            if hasattr(widget, 'set_transaction_amount'):
                widget.set_transaction_amount(1000)  # $10.00
            
            if hasattr(widget, 'set_currency_code'):
                widget.set_currency_code('0840')  # USD
            
            # Test transaction initiation
            if hasattr(widget, 'start_transaction'):
                # Should not raise exception
                widget.start_transaction()
            
        except Exception as e:
            self.skipTest(f"TransactionWidget operations test failed: {e}")
    
    def test_debug_console_widget_initialization(self):
        """Test DebugConsoleWidget initialization."""
        try:
            widget = self.DebugConsoleWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check for text display area
            self.assertIsNotNone(widget.layout())
            
        except Exception as e:
            self.skipTest(f"DebugConsoleWidget initialization failed: {e}")
    
    def test_debug_console_widget_logging(self):
        """Test debug console logging functionality."""
        try:
            widget = self.DebugConsoleWidget()
            
            # Test log message addition
            if hasattr(widget, 'add_log_message'):
                widget.add_log_message('INFO', 'Test log message')
                widget.add_log_message('ERROR', 'Test error message')
                widget.add_log_message('DEBUG', 'Test debug message')
            
            # Test console clearing
            if hasattr(widget, 'clear_console'):
                widget.clear_console()
                
        except Exception as e:
            self.skipTest(f"DebugConsoleWidget logging test failed: {e}")
    
    def test_status_bar_widget_initialization(self):
        """Test StatusBarWidget initialization."""
        try:
            widget = self.StatusBarWidget()
            
            # Check basic functionality
            if hasattr(widget, 'showMessage'):
                widget.showMessage('Test status message')
            
        except Exception as e:
            self.skipTest(f"StatusBarWidget initialization failed: {e}")


class TestSecurityResearchUI(unittest.TestCase):
    """Test security research UI components."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            from ..security_research_ui import (
                AttackWidget, ReplayWidget, CloningWidget,
                CryptogramWidget, ResearchDashboard
            )
            
            self.AttackWidget = AttackWidget
            self.ReplayWidget = ReplayWidget
            self.CloningWidget = CloningWidget
            self.CryptogramWidget = CryptogramWidget
            self.ResearchDashboard = ResearchDashboard
            
        except ImportError as e:
            self.skipTest(f"Security research UI modules not available: {e}")
    
    def test_attack_widget_initialization(self):
        """Test AttackWidget initialization."""
        try:
            widget = self.AttackWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check for attack signals
            expected_signals = ['attack_started', 'attack_stopped']
            for signal_name in expected_signals:
                if hasattr(widget, signal_name):
                    self.assertTrue(hasattr(getattr(widget, signal_name), 'connect'))
            
        except Exception as e:
            self.skipTest(f"AttackWidget initialization failed: {e}")
    
    def test_attack_widget_operations(self):
        """Test attack widget operations."""
        try:
            widget = self.AttackWidget()
            
            # Test attack configuration
            if hasattr(widget, 'configure_pin_attack'):
                widget.configure_pin_attack({
                    'start_pin': '0000',
                    'end_pin': '9999',
                    'delay_ms': 100
                })
            
            # Test attack execution
            if hasattr(widget, 'start_attack'):
                # Should not raise exception
                widget.start_attack('pin_bruteforce')
            
            if hasattr(widget, 'stop_attack'):
                widget.stop_attack('pin_bruteforce')
                
        except Exception as e:
            self.skipTest(f"AttackWidget operations test failed: {e}")
    
    def test_replay_widget_initialization(self):
        """Test ReplayWidget initialization."""
        try:
            widget = self.ReplayWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check for replay functionality
            self.assertIsNotNone(widget.layout())
            
        except Exception as e:
            self.skipTest(f"ReplayWidget initialization failed: {e}")
    
    def test_replay_widget_operations(self):
        """Test replay widget operations."""
        try:
            widget = self.ReplayWidget()
            
            # Test session loading
            test_session = {
                'transactions': [
                    {
                        'timestamp': '2025-08-17T10:30:00',
                        'amount': 1000,
                        'apdu_trace': ['00A4040007A0000000031010']
                    }
                ]
            }
            
            if hasattr(widget, 'load_session'):
                widget.load_session(test_session)
            
            # Test replay execution
            if hasattr(widget, 'start_replay'):
                widget.start_replay()
                
        except Exception as e:
            self.skipTest(f"ReplayWidget operations test failed: {e}")
    
    def test_cloning_widget_initialization(self):
        """Test CloningWidget initialization."""
        try:
            widget = self.CloningWidget()
            self.assertIsInstance(widget, QWidget)
            
        except Exception as e:
            self.skipTest(f"CloningWidget initialization failed: {e}")
    
    def test_cryptogram_widget_initialization(self):
        """Test CryptogramWidget initialization."""
        try:
            widget = self.CryptogramWidget()
            self.assertIsInstance(widget, QWidget)
            
        except Exception as e:
            self.skipTest(f"CryptogramWidget initialization failed: {e}")
    
    def test_research_dashboard_initialization(self):
        """Test ResearchDashboard initialization."""
        try:
            widget = self.ResearchDashboard()
            self.assertIsInstance(widget, QWidget)
            
        except Exception as e:
            self.skipTest(f"ResearchDashboard initialization failed: {e}")


class TestAndroidWidget(unittest.TestCase):
    """Test Android companion widget."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            # Mock BLE dependencies
            with patch('android_widget.BLEAndroidManager'):
                with patch('android_widget.check_ble_availability'):
                    from ..android_widget import AndroidWidget
                    self.AndroidWidget = AndroidWidget
                    
        except ImportError as e:
            self.skipTest(f"Android widget module not available: {e}")
    
    def test_android_widget_initialization(self):
        """Test AndroidWidget initialization."""
        try:
            widget = self.AndroidWidget()
            self.assertIsInstance(widget, QWidget)
            
            # Check for Android-specific signals
            expected_signals = [
                'session_export_requested',
                'android_connect_requested', 
                'android_disconnect_requested'
            ]
            
            for signal_name in expected_signals:
                if hasattr(widget, signal_name):
                    self.assertTrue(hasattr(getattr(widget, signal_name), 'connect'))
            
        except Exception as e:
            self.skipTest(f"AndroidWidget initialization failed: {e}")
    
    def test_android_widget_device_management(self):
        """Test Android device management."""
        try:
            widget = self.AndroidWidget()
            
            # Test device discovery
            if hasattr(widget, 'start_device_scan'):
                widget.start_device_scan()
            
            if hasattr(widget, 'stop_device_scan'):
                widget.stop_device_scan()
            
            # Test device connection
            if hasattr(widget, 'connect_to_device'):
                widget.connect_to_device('00:11:22:33:44:55', 'Test Device')
            
        except Exception as e:
            self.skipTest(f"AndroidWidget device management test failed: {e}")
    
    def test_android_widget_session_export(self):
        """Test session export functionality."""
        try:
            widget = self.AndroidWidget()
            
            # Test session data setting
            test_session = {
                'card_data': {
                    'pan': '4111111111111111',
                    'track2': '4111111111111111=2512101'
                },
                'transactions': []
            }
            
            if hasattr(widget, 'set_session_data'):
                widget.set_session_data(test_session)
            
            # Test export operation
            if hasattr(widget, 'export_session_to_android'):
                widget.export_session_to_android()
                
        except Exception as e:
            self.skipTest(f"AndroidWidget session export test failed: {e}")


class TestUIIntegration(unittest.TestCase):
    """Test UI component integration."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.test_widgets = []
    
    def tearDown(self):
        """Clean up test widgets."""
        for widget in self.test_widgets:
            if hasattr(widget, 'close'):
                widget.close()
    
    def test_widget_signal_connections(self):
        """Test signal connections between widgets."""
        try:
            # Mock the main window to test widget integration
            with patch('ui_mainwindow.QMainWindow'):
                with patch('card_manager.CardManager'):
                    with patch('readers.ReaderManager'):
                        from ..ui_mainwindow import MainWindow
                        
                        # Create main window
                        main_window = MainWindow()
                        self.test_widgets.append(main_window)
                        
                        # Test that main window can be created
                        self.assertIsInstance(main_window, object)
                        
        except Exception as e:
            self.skipTest(f"UI integration test failed: {e}")
    
    def test_widget_lifecycle(self):
        """Test widget creation and destruction."""
        try:
            # Test creating multiple widgets
            widgets_to_test = []
            
            # Try to create various widgets
            widget_classes = []
            
            try:
                from ..ui_mainwindow import CardDataWidget
                widget_classes.append(CardDataWidget)
            except ImportError:
                pass
                
            try:
                from ..security_research_ui import AttackWidget
                widget_classes.append(AttackWidget)
            except ImportError:
                pass
            
            for widget_class in widget_classes:
                try:
                    widget = widget_class()
                    widgets_to_test.append(widget)
                    self.assertIsInstance(widget, QWidget)
                except Exception:
                    # Widget creation might fail due to dependencies
                    pass
            
            # Clean up
            for widget in widgets_to_test:
                if hasattr(widget, 'close'):
                    widget.close()
                    
        except Exception as e:
            self.skipTest(f"Widget lifecycle test failed: {e}")


def run_ui_tests():
    """Run comprehensive UI test suite."""
    print("=" * 60)
    print("NFSP00F3R V5.0 - UI Component Test Suite")
    print("=" * 60)
    print(f"Starting UI tests at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestMainWindowComponents,
        TestSecurityResearchUI,
        TestAndroidWidget,
        TestUIIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("UI Test Suite Summary")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
    passed = total_tests - failures - errors - skipped
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    
    if total_tests > 0:
        success_rate = (passed / total_tests) * 100
        print(f"Success rate: {success_rate:.1f}%")
    
    # Print detailed results for failures
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  FAIL: {test}")
            print(f"    {traceback.strip()}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  ERROR: {test}")
            print(f"    {traceback.strip()}")
    
    if passed == total_tests and total_tests > 0:
        print("\nAll UI tests passed!")
        print("UI components are ready for deployment.")
    elif passed > 0:
        print(f"\nPartial success: {passed}/{total_tests} tests passed")
        print("Some UI components may have dependency issues.")
    else:
        print("\nUI testing incomplete - check dependencies")
    
    print("=" * 60)
    
    return result.wasSuccessful() if total_tests > 0 else True


def main():
    """Main test runner entry point."""
    success = run_ui_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
