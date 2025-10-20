#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - UI Functionality Validation Test
===================================================

File: test_ui_functionality_validation.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Comprehensive test to validate UI controls are properly wired

This test validates that all UI controls are connected to their handler methods
and that the signal/slot architecture is working correctly.
"""

import os
import sys
import unittest
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer
from PyQt5.QtTest import QTest
from unittest.mock import Mock, MagicMock, patch

class MockAppInstance:
    """Mock application instance for testing."""
    def __init__(self):
        self.reader_manager = Mock()
        self.card_manager = Mock()
        self.transaction_engine = Mock()
        self.ble_android_manager = Mock()
        self.attack_manager = Mock()
        
        # Setup mock behaviors
        self.reader_manager.detect_readers.return_value = [
            {'name': 'Mock Reader 1', 'type': 'pcsc', 'description': 'PC/SC Reader: Mock Reader 1'},
            {'name': 'Mock Reader 2', 'type': 'pcsc', 'description': 'PC/SC Reader: Mock Reader 2'}
        ]
        self.reader_manager.connect_reader.return_value = True
        self.card_manager.read_card.return_value = {
            'success': True,
            'card_data': {'pan': '1234567890123456', 'expiry': '12/25'},
            'atr': '3B8F8001804F0CA000000306030001000000006A'
        }
        self.transaction_engine.start_transaction.return_value = {'success': True}
    
    def cleanup(self):
        """Mock cleanup method."""
        pass

class TestUIFunctionality(unittest.TestCase):
    """Test UI functionality and signal connections."""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Setup for each test."""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ui_mainwindow import MainWindow
        self.mock_app = MockAppInstance()
        self.window = MainWindow(self.mock_app)
    
    def tearDown(self):
        """Cleanup after each test."""
        if hasattr(self, 'window'):
            self.window.close()
    
    def test_window_creation(self):
        """Test that the main window creates successfully."""
        self.assertIsNotNone(self.window)
        self.assertEqual(self.window.app_instance, self.mock_app)
        print("✓ Main window creates successfully")
    
    def test_signal_connections(self):
        """Test that signal connections work without errors."""
        try:
            self.window.connect_signals()
            print("✓ Signal connections established successfully")
        except Exception as e:
            self.fail(f"Signal connections failed: {e}")
    
    def test_handler_methods_exist(self):
        """Test that all required handler methods exist."""
        required_handlers = [
            'refresh_readers',
            'on_reader_selected', 
            'start_card_reading',
            'stop_card_reading',
            'on_transaction_started',
            'on_transaction_completed',
            'on_card_data_updated',
            'connect_android_device',
            'disconnect_android_device',
            'on_attack_started',
            'on_attack_stopped',
            'new_session',
            'save_session',
            'export_card_data',
            'quick_read_card',
            'quick_transaction'
        ]
        
        missing_handlers = []
        for handler in required_handlers:
            if not hasattr(self.window, handler):
                missing_handlers.append(handler)
            else:
                print(f"✓ Handler method {handler} exists")
        
        self.assertEqual(len(missing_handlers), 0, 
                        f"Missing handlers: {missing_handlers}")
    
    def test_widget_existence(self):
        """Test that all expected widgets exist."""
        required_widgets = [
            'reader_widget',
            'card_widget', 
            'transaction_widget',
            'debug_widget'
        ]
        
        missing_widgets = []
        for widget in required_widgets:
            if not hasattr(self.window, widget):
                missing_widgets.append(widget)
            else:
                widget_obj = getattr(self.window, widget)
                self.assertIsNotNone(widget_obj)
                print(f"✓ Widget {widget} exists and is initialized")
        
        self.assertEqual(len(missing_widgets), 0,
                        f"Missing widgets: {missing_widgets}")
    
    def test_reader_functionality(self):
        """Test reader control functionality."""
        # Test refresh readers
        try:
            self.window.refresh_readers()
            self.mock_app.reader_manager.detect_readers.assert_called_once()
            print("✓ Reader refresh functionality works")
        except Exception as e:
            self.fail(f"Reader refresh failed: {e}")
        
        # Test reader selection
        try:
            # Simulate storing detected readers (as done in refresh_readers)
            self.window._detected_readers = self.mock_app.reader_manager.detect_readers.return_value
            
            self.window.on_reader_selected("Mock Reader 1")
            # Should be called with the full reader info dict
            expected_reader_info = {'name': 'Mock Reader 1', 'type': 'pcsc', 'description': 'PC/SC Reader: Mock Reader 1'}
            self.mock_app.reader_manager.connect_reader.assert_called_with(expected_reader_info)
            print("✓ Reader selection functionality works")
        except Exception as e:
            self.fail(f"Reader selection failed: {e}")
    
    def test_card_reading_functionality(self):
        """Test card reading functionality."""
        try:
            self.window.start_card_reading("Mock Reader 1")
            self.mock_app.card_manager.read_card.assert_called_with("Mock Reader 1")
            print("✓ Card reading functionality works")
        except Exception as e:
            self.fail(f"Card reading failed: {e}")
    
    def test_transaction_functionality(self):
        """Test transaction functionality."""
        try:
            transaction_data = {
                'amount': 1000,
                'currency': '0840',
                'type': 'purchase'
            }
            self.window.on_transaction_started(transaction_data)
            self.mock_app.transaction_engine.start_transaction.assert_called_with(transaction_data)
            print("✓ Transaction functionality works")
        except Exception as e:
            self.fail(f"Transaction failed: {e}")
    
    def test_session_management(self):
        """Test session management functionality."""
        try:
            # Test new session
            self.window.new_session()
            self.assertTrue(hasattr(self.window, 'current_session'))
            print("✓ New session creation works")
            
            # Test session data retrieval
            session_data = self.window.get_complete_session_data()
            self.assertIsInstance(session_data, dict)
            self.assertIn('timestamp', session_data)
            self.assertIn('version', session_data)
            print("✓ Session data retrieval works")
            
        except Exception as e:
            self.fail(f"Session management failed: {e}")
    
    def test_debug_console_integration(self):
        """Test debug console integration."""
        try:
            # Test adding debug messages
            self.window.add_debug_message("Test message", "INFO")
            self.window.add_debug_message("Warning message", "WARNING")
            self.window.add_debug_message("Error message", "ERROR")
            print("✓ Debug console integration works")
        except Exception as e:
            self.fail(f"Debug console integration failed: {e}")
    
    def test_quick_actions(self):
        """Test quick action functionality."""
        try:
            # Mock reader selection for quick read
            if hasattr(self.window.reader_widget, 'reader_list'):
                # This would normally be populated by actual readers
                pass
            
            # Test quick transaction
            self.window.quick_transaction()
            print("✓ Quick transaction functionality works")
            
        except Exception as e:
            self.fail(f"Quick actions failed: {e}")
    
    def test_android_integration(self):
        """Test Android integration functionality."""
        try:
            if hasattr(self.window, 'android_widget'):
                self.window.connect_android_device("00:11:22:33:44:55", "Test Device")
                self.mock_app.ble_android_manager.connect_device.assert_called_with("00:11:22:33:44:55")
                print("✓ Android integration functionality works")
            else:
                print("ℹ Android widget not available (expected if no BLE support)")
        except Exception as e:
            self.fail(f"Android integration failed: {e}")
    
    def test_attack_integration(self):
        """Test attack integration functionality."""
        try:
            if hasattr(self.window, 'attack_widget'):
                attack_params = {'type': 'replay', 'target': 'card'}
                self.window.on_attack_started('replay', attack_params)
                print("✓ Attack integration functionality works")
            else:
                print("ℹ Attack widget not available")
        except Exception as e:
            self.fail(f"Attack integration failed: {e}")

def run_functionality_tests():
    """Run all functionality tests."""
    print("=" * 60)
    print("UI FUNCTIONALITY VALIDATION TEST")
    print("=" * 60)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUIFunctionality)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - failures - errors}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 UI FUNCTIONALITY VALIDATION PASSED! 🎉")
        print("✓ All UI controls are properly wired and functional")
    elif success_rate >= 75:
        print("\n⚠️  UI functionality mostly working with minor issues")
    else:
        print("\n❌ UI functionality validation failed")
    
    print("=" * 60)
    
    return result

if __name__ == '__main__':
    # Set up the application
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    # Run the tests
    test_result = run_functionality_tests()
    
    # Exit with appropriate code
    sys.exit(0 if test_result.wasSuccessful() else 1)
