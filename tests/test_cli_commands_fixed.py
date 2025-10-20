#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - CLI Command Tests (Fixed)
============================================

File: test_cli_commands_fixed.py
Authors: Gregory King & Matthew Braunschweig
Date: August 17, 2025
Description: Comprehensive test suite for CLI commands in main.py (Fixed Version)

This test suite validates all command-line interface functionality with proper
mocking and error handling for Windows environment.
"""

import unittest
import sys
import os
import json
import tempfile
import shutil
import subprocess
import argparse
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
import main
from main import parse_arguments, check_dependencies, Application

class TestArgumentParsing(unittest.TestCase):
    """Test argument parsing functionality."""
    
    def test_parse_no_arguments(self):
        """Test parsing with no arguments."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            self.assertIsNone(args.replay)
            self.assertIsNone(args.preplay)
    
    def test_parse_replay_argument(self):
        """Test parsing replay attack argument."""
        with patch('sys.argv', ['main.py', '--replay', 'session.json']):
            args = parse_arguments()
            self.assertEqual(args.replay, 'session.json')
    
    def test_parse_preplay_argument(self):
        """Test parsing preplay attack argument."""
        with patch('sys.argv', ['main.py', '--preplay', 'database.json']):
            args = parse_arguments()
            self.assertEqual(args.preplay, 'database.json')
    
    def test_parse_android_scan_argument(self):
        """Test parsing Android scan argument."""
        with patch('sys.argv', ['main.py', '--android-scan']):
            args = parse_arguments()
            self.assertTrue(args.android_scan)
    
    def test_parse_android_connect_argument(self):
        """Test parsing Android connect argument."""
        with patch('sys.argv', ['main.py', '--android-connect', '12:34:56:78:90:AB']):
            args = parse_arguments()
            self.assertEqual(args.android_connect, '12:34:56:78:90:AB')
    
    def test_parse_android_send_argument(self):
        """Test parsing Android send argument."""
        with patch('sys.argv', ['main.py', '--android-send', 'test message']):
            args = parse_arguments()
            self.assertEqual(args.android_send, 'test message')
    
    def test_parse_export_session_argument(self):
        """Test parsing export session argument."""
        with patch('sys.argv', ['main.py', '--export-session', 'output.json']):
            args = parse_arguments()
            self.assertEqual(args.export_session, 'output.json')
    
    def test_parse_analyze_card_argument(self):
        """Test parsing analyze card argument."""
        with patch('sys.argv', ['main.py', '--analyze-card']):
            args = parse_arguments()
            self.assertTrue(args.analyze_card)
    
    def test_parse_extract_keys_argument(self):
        """Test parsing extract keys argument."""
        with patch('sys.argv', ['main.py', '--extract-keys']):
            args = parse_arguments()
            self.assertTrue(args.extract_keys)
    
    def test_parse_test_argument(self):
        """Test parsing test argument."""
        with patch('sys.argv', ['main.py', '--test']):
            args = parse_arguments()
            self.assertTrue(args.test)
    
    def test_parse_validate_session_argument(self):
        """Test parsing validate session argument."""
        with patch('sys.argv', ['main.py', '--validate-session', 'session.json']):
            args = parse_arguments()
            self.assertEqual(args.validate_session, 'session.json')
    
    def test_parse_benchmark_argument(self):
        """Test parsing benchmark argument."""
        with patch('sys.argv', ['main.py', '--benchmark']):
            args = parse_arguments()
            self.assertTrue(args.benchmark)
    
    def test_parse_debug_argument(self):
        """Test parsing debug argument."""
        with patch('sys.argv', ['main.py', '--debug']):
            args = parse_arguments()
            self.assertTrue(args.debug)
    
    def test_parse_no_gui_argument(self):
        """Test parsing no-gui argument."""
        with patch('sys.argv', ['main.py', '--no-gui']):
            args = parse_arguments()
            self.assertTrue(args.no_gui)
    
    def test_parse_verbose_argument(self):
        """Test parsing verbose argument."""
        with patch('sys.argv', ['main.py', '--verbose']):
            args = parse_arguments()
            self.assertEqual(args.verbose, 1)
        
        with patch('sys.argv', ['main.py', '-vv']):
            args = parse_arguments()
            self.assertEqual(args.verbose, 2)
    
    def test_parse_combined_arguments(self):
        """Test parsing multiple combined arguments."""
        with patch('sys.argv', ['main.py', '--replay', 'test.json', '--debug', '--no-gui']):
            args = parse_arguments()
            self.assertEqual(args.replay, 'test.json')
            self.assertTrue(args.debug)
            self.assertTrue(args.no_gui)

class TestDependencyChecking(unittest.TestCase):
    """Test dependency checking functionality."""
    
    @patch('importlib.import_module')
    def test_check_dependencies_all_present(self, mock_import):
        """Test dependency check when all dependencies are present."""
        # Mock all imports as successful
        mock_import.return_value = MagicMock()
        
        result = main.check_dependencies()
        self.assertTrue(result)
    
    @patch('importlib.import_module')
    def test_check_dependencies_missing(self, mock_import):
        """Test dependency check when dependencies are missing."""
        # Mock some imports as failing
        def side_effect(module_name):
            if module_name == 'PyQt5.QtWidgets':
                raise ImportError("No module named 'PyQt5.QtWidgets'")
            return MagicMock()
        
        mock_import.side_effect = side_effect
        
        with patch('builtins.print'):
            result = main.check_dependencies()
            self.assertFalse(result)

class TestApplicationInitialization(unittest.TestCase):
    """Test Application class initialization."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass  # Ignore cleanup errors on Windows
    
    @patch('main.MainWindow')
    @patch('main.Settings')
    @patch('main.CardManager')
    @patch('main.ReaderManager')
    @patch('main.BluetoothManager')
    @patch('main.BLEAndroidManager')
    @patch('main.TransactionEngine')
    def test_application_initialization_no_args(self, mock_transaction, mock_ble, 
                                               mock_bluetooth, mock_reader, 
                                               mock_card, mock_settings, mock_window):
        """Test application initialization without CLI arguments."""
        
        # Mock successful initialization
        mock_window.return_value = MagicMock()
        mock_settings.return_value = MagicMock()
        
        args = argparse.Namespace(
            replay=None, preplay=None, android_scan=False,
            android_connect=None, android_send=None,
            export_session=None, analyze_card=False,
            extract_keys=False, test=False,
            validate_session=None, benchmark=False,
            debug=False, no_gui=False, verbose=0
        )
        
        # Should not raise any exceptions
        app = Application(args)
        self.assertIsNotNone(app)
    
    @patch('attack_manager.AttackManager')
    @patch('main.MainWindow')
    @patch('main.Settings')
    @patch('main.CardManager')
    @patch('main.ReaderManager')
    @patch('main.BluetoothManager')
    @patch('main.BLEAndroidManager')
    @patch('main.TransactionEngine')
    def test_application_initialization_with_replay(self, mock_transaction, mock_ble,
                                                  mock_bluetooth, mock_reader,
                                                  mock_card, mock_settings, 
                                                  mock_window, mock_attack):
        """Test application initialization with replay argument."""
        
        # Create a test session file
        test_session = {
            "session_id": "test_123",
            "transactions": [
                {"command": "SELECT", "response": "9000"}
            ]
        }
        
        with open('test_session.json', 'w') as f:
            json.dump(test_session, f)
        
        args = argparse.Namespace(
            replay='test_session.json', preplay=None, android_scan=False,
            android_connect=None, android_send=None,
            export_session=None, analyze_card=False,
            extract_keys=False, test=False,
            validate_session=None, benchmark=False,
            debug=False, no_gui=False, verbose=0
        )
        
        # Mock the attack manager
        mock_attack.return_value = MagicMock()
        
        # Should initialize with replay mode
        app = Application(args)
        self.assertIsNotNone(app)

class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration and main function behavior."""
    
    def test_main_function_help(self):
        """Test main function with help argument."""
        with patch('sys.argv', ['main.py', '--help']):
            with self.assertRaises(SystemExit):
                # Help should cause SystemExit(0)
                parse_arguments()
    
    @patch('main.check_dependencies')
    @patch('builtins.print')
    def test_main_function_missing_dependencies(self, mock_print, mock_check):
        """Test main function with missing dependencies."""
        mock_check.return_value = False
        
        with patch('sys.argv', ['main.py']):
            with self.assertRaises(SystemExit):
                main.main()
    
    @patch('main.Application')
    @patch('main.check_dependencies')
    @patch('main.QApplication')
    def test_main_function_replay_mode(self, mock_qapp, mock_check, mock_app):
        """Test main function with replay mode."""
        mock_check.return_value = True
        mock_qapp.return_value = MagicMock()
        mock_app.return_value = MagicMock()
        
        with patch('sys.argv', ['main.py', '--replay', 'test.json']):
            # Should not raise exceptions
            try:
                main.main()
            except SystemExit:
                pass  # Expected for clean exit

class TestCommandExecution(unittest.TestCase):
    """Test command execution functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
    
    @patch('bluetooth_manager_ble.BLEAndroidManager')
    def test_scan_android_command(self, mock_ble):
        """Test Android scan command execution."""
        mock_manager = MagicMock()
        mock_manager.scan_devices.return_value = ['device1', 'device2']
        mock_ble.return_value = mock_manager
        
        args = argparse.Namespace(android_scan=True, android_connect=None,
                                android_send=None, debug=False, verbose=0)
        
        # Should execute scan without errors
        app = Application(args)
        self.assertIsNotNone(app)
    
    @patch('bluetooth_manager_ble.BLEAndroidManager')
    def test_connect_android_command(self, mock_ble):
        """Test Android connect command execution."""
        mock_manager = MagicMock()
        mock_manager.connect.return_value = True
        mock_ble.return_value = mock_manager
        
        args = argparse.Namespace(android_scan=False, 
                                android_connect='12:34:56:78:90:AB',
                                android_send=None, debug=False, verbose=0)
        
        # Should execute connect without errors
        app = Application(args)
        self.assertIsNotNone(app)
    
    def test_export_session_command(self):
        """Test export session command execution."""
        # Create test session data
        test_data = {"session": "test"}
        
        args = argparse.Namespace(export_session='output.json',
                                android_scan=False, android_connect=None,
                                android_send=None, debug=False, verbose=0)
        
        # Should handle export command
        app = Application(args)
        self.assertIsNotNone(app)

class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""
    
    def test_invalid_session_file(self):
        """Test handling of invalid session file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            invalid_file = f.name
        
        try:
            args = argparse.Namespace(replay=invalid_file, preplay=None,
                                    android_scan=False, android_connect=None,
                                    android_send=None, debug=False, verbose=0)
            
            # Should handle invalid file gracefully
            with patch('builtins.print'):
                app = Application(args)
                self.assertIsNotNone(app)
                
        finally:
            os.unlink(invalid_file)
    
    def test_invalid_database_file(self):
        """Test handling of invalid database file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json")
            invalid_file = f.name
        
        try:
            args = argparse.Namespace(replay=None, preplay=invalid_file,
                                    android_scan=False, android_connect=None,
                                    android_send=None, debug=False, verbose=0)
            
            # Should handle invalid database gracefully
            with patch('builtins.print'):
                app = Application(args)
                self.assertIsNotNone(app)
                
        finally:
            os.unlink(invalid_file)

class TestPreplayAttackCommands(unittest.TestCase):
    """Test preplay attack command functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass
    
    @patch('attack_manager.AttackManager')
    def test_verifone_preplay_command(self, mock_attack):
        """Test Verifone VX520 preplay attack command."""
        # Create test preplay database
        preplay_db = {
            "terminal_type": "VERIFONE_VX520",
            "attack_data": {
                "UN_12345678": "ARQC_RESPONSE_DATA"
            }
        }
        
        with open('verifone_db.json', 'w') as f:
            json.dump(preplay_db, f)
        
        mock_attack.return_value = MagicMock()
        
        args = argparse.Namespace(preplay='verifone_db.json', replay=None,
                                android_scan=False, android_connect=None,
                                android_send=None, debug=False, verbose=0)
        
        # Should load preplay database
        app = Application(args)
        self.assertIsNotNone(app)
    
    @patch('attack_manager.AttackManager')
    def test_ingenico_preplay_command(self, mock_attack):
        """Test Ingenico iCT250 preplay attack command."""
        # Create test preplay database
        preplay_db = {
            "terminal_type": "INGENICO_ICT250",
            "attack_data": {
                "UN_87654321": "ARQC_COUNTER_RESPONSE"
            }
        }
        
        with open('ingenico_db.json', 'w') as f:
            json.dump(preplay_db, f)
        
        mock_attack.return_value = MagicMock()
        
        args = argparse.Namespace(preplay='ingenico_db.json', replay=None,
                                android_scan=False, android_connect=None,
                                android_send=None, debug=False, verbose=0)
        
        # Should load preplay database
        app = Application(args)
        self.assertIsNotNone(app)

def run_tests():
    """Run all tests and provide summary."""
    # Configure test environment
    os.environ['PYTEST_CURRENT_TEST'] = 'test_cli_commands_fixed.py'
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestArgumentParsing,
        TestDependencyChecking,
        TestApplicationInitialization,
        TestCLIIntegration,
        TestCommandExecution,
        TestErrorHandling,
        TestPreplayAttackCommands
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("CLI Command Tests Summary (Fixed)")
    print("="*60)
    print(f"Total tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
