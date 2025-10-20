#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: main.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Main application entry point with OS detection and initialization

Classes:
- Application: Main application class with OS detection and setup

Functions:
- main(): Entry point function
- setup_logging(): Configure application logging
- detect_os(): Detect operating system for Bluetooth stack selection
- parse_arguments(): Parse command line arguments for attack modes

This is the main entry point for the NFSP00F3R V5.00 EMV terminal application.
It handles OS detection for proper Bluetooth stack selection, initializes logging,
and launches the main UI window.

Support for CLI arguments:
- --replay session.json: Load and activate replay attack mode
- --preplay db.json: Load and activate pre-play attack mode

Based on code from:
- dimalinux/EMV-Tools (application structure)
- atzedevs/emv-crypto (initialization patterns)
- Various EMV specifications and implementations
"""

import sys
import os
import platform
import logging
import traceback
import argparse
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

# Import our modules
from ui_mainwindow import MainWindow
from settings import Settings
from card_manager import CardManager
from readers import ReaderManager
from bluetooth_manager import BluetoothManager
from bluetooth_manager_ble import BLEAndroidManager
from transaction import TransactionEngine
from crypto import EMVCrypto

class Application(QApplication):
    """
    Main application class that handles initialization and OS detection.
    Inherits from QApplication to provide custom application-wide functionality.
    """
    
    def __init__(self, argv, cli_args=None):
        super().__init__(argv)
        
        # Store CLI arguments
        self.cli_args = cli_args
        
        # Set application properties
        self.setApplicationName("NFSP00F3R V5.00")
        self.setApplicationVersion("5.00")
        self.setOrganizationName("EMV Research Labs")
        self.setOrganizationDomain("emvresearch.local")
        
        # Detect operating system for Bluetooth stack selection
        self.os_type = self.detect_os()
        
        # Initialize logging
        self.setup_logging()
        
        # Log startup
        logging.info("Starting NFSP00F3R V5.00 EMV Terminal")
        logging.info(f"Detected OS: {self.os_type}")
        logging.info(f"Python version: {sys.version}")
        try:
            from PyQt5.QtCore import PYQT_VERSION_STR
            logging.info(f"PyQt5 version: {PYQT_VERSION_STR}")
        except ImportError:
            logging.info("PyQt5 version: Unknown")
        
        # Initialize core components
        self.settings = Settings()
        self.card_manager = CardManager()
        self.reader_manager = ReaderManager()
        self.bluetooth_manager = BluetoothManager()
        self.ble_android_manager = BLEAndroidManager()
        self.transaction_engine = TransactionEngine(self.card_manager, self.reader_manager)
        self.crypto_engine = EMVCrypto()
        
        # Auto-load card data using universal EMV parser
        self._auto_load_card_data()
        
        # Initialize attack manager if CLI args provided
        if self.cli_args and (self.cli_args.replay or self.cli_args.preplay):
            try:
                from attack_manager import AttackManager
                self.attack_manager = AttackManager()
                self._configure_cli_attack_mode()
                logging.info("Attack manager initialized for CLI mode")
            except ImportError as e:
                logging.error(f"Failed to initialize attack manager: {e}")
                self.attack_manager = None
        else:
            self.attack_manager = None
        
        # Create main window
        self.main_window = MainWindow(self)
        
        # Set application icon
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # Handle application exit
        self.aboutToQuit.connect(self.cleanup)
        
        # Show main window unless in headless mode
        if not (self.cli_args and self.cli_args.no_gui):
            self.main_window.show()
        
        logging.info("Application initialization complete")
        
    def _configure_cli_attack_mode(self):
        """Configure attack mode based on CLI arguments."""
        if not self.attack_manager:
            return
            
        try:
            if self.cli_args.replay:
                from attack_manager import AttackMode
                self.attack_manager.set_mode(AttackMode.REPLAY)
                if self.attack_manager.load_session(self.cli_args.replay):
                    logging.info(f"Loaded replay session: {self.cli_args.replay}")
                    self.attack_manager.start_session()
                else:
                    logging.error(f"Failed to load replay session: {self.cli_args.replay}")
                    
            elif self.cli_args.preplay:
                from attack_manager import AttackMode
                self.attack_manager.set_mode(AttackMode.PREPLAY)
                if self.attack_manager.load_database(self.cli_args.preplay):
                    logging.info(f"Loaded preplay database: {self.cli_args.preplay}")
                    self.attack_manager.start_session()
                else:
                    logging.error(f"Failed to load preplay database: {self.cli_args.preplay}")
                    
        except Exception as e:
            logging.error(f"CLI attack configuration failed: {e}")
    
    def detect_os(self):
        """
        Detect the operating system for proper library selection.
        Returns 'windows', 'linux', or 'darwin' (macOS).
        """
        system = platform.system().lower()
        
        if system == "windows":
            return "windows"
        elif system == "linux":
            return "linux"
        elif system == "darwin":
            return "darwin"
        else:
            logging.warning(f"Unknown OS detected: {system}, defaulting to linux")
            return "linux"
    
    def setup_logging(self):
        """
        Configure application logging with appropriate levels and formatting.
        Creates both file and console handlers for comprehensive logging.
        """
        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # Configure logging format
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # Set up root logger
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt=date_format,
            handlers=[
                logging.FileHandler("logs/nfsp00f3r.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Set specific logger levels
        logging.getLogger("smartcard").setLevel(logging.WARNING)
        logging.getLogger("nfcpy").setLevel(logging.WARNING)
        logging.getLogger("bluetooth").setLevel(logging.INFO)
        logging.getLogger("apdu").setLevel(logging.DEBUG)
        logging.getLogger("tlv").setLevel(logging.DEBUG)
        logging.getLogger("crypto").setLevel(logging.INFO)
        
        logging.info("Logging initialized")
    
    def cleanup(self):
        """
        Clean up resources before application exit.
        Ensures all readers and connections are properly closed.
        """
        logging.info("Application shutting down...")
        
        try:
            # Stop all readers
            if hasattr(self, 'reader_manager'):
                self.reader_manager.stop_all_readers()
            
            # Close Bluetooth connections
            if hasattr(self, 'bluetooth_manager'):
                self.bluetooth_manager.cleanup()
            
            # Save settings
            if hasattr(self, 'settings'):
                self.settings.save()
            
            logging.info("Cleanup complete")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            logging.error(traceback.format_exc())

    def _auto_load_card_data(self):
        """
        Automatically load card data using CardManager.
        This runs in the background to populate the UI with actual card data.
        """
        def load_card_data():
            try:
                logging.info("Auto-loading card data using CardManager...")
                
                # Use CardManager to read card with our fixed universal parser integration
                card_result = self.card_manager.read_card()
                
                if card_result and card_result.get('card_data'):
                    logging.info("Successfully auto-loaded real card data")
                    logging.info(f"PAN: {card_result['card_data'].get('pan', 'N/A')}")
                    logging.info(f"Expiry: {card_result['card_data'].get('expiry_date', 'N/A')}")
                    logging.info(f"Application: {card_result['card_data'].get('application_label', 'N/A')}")
                    
                    # Update UI in main thread if needed
                    if hasattr(self, 'ui') and self.ui:
                        self.ui.update_card_display()
                else:
                    logging.warning("No card data could be auto-loaded")
                    
            except Exception as e:
                logging.error(f"Auto-load card data failed: {e}")
    def _auto_load_card_data(self):
        """
        Automatically load card data using CardManager.
        This runs in the background to populate the UI with actual card data.
        """
        def load_card_data():
            try:
                logging.info("Auto-loading card data using CardManager...")
                
                # Use CardManager to read card with our fixed universal parser integration
                card_result = self.card_manager.read_card()
                
                if card_result and card_result.get('card_data'):
                    logging.info("Successfully auto-loaded real card data")
                    logging.info(f"PAN: {card_result['card_data'].get('pan', 'N/A')}")
                    logging.info(f"Expiry: {card_result['card_data'].get('expiry_date', 'N/A')}")
                    logging.info(f"Application: {card_result['card_data'].get('application_label', 'N/A')}")
                    
                    # Update UI in main thread if needed
                    if hasattr(self, 'ui') and self.ui:
                        self.ui.update_card_display()
                else:
                    logging.warning("No card data could be auto-loaded")
                    
            except Exception as e:
                logging.warning(f"Auto-load card data failed (this is normal if no card present): {e}")
        
        # Run in background thread to avoid blocking UI startup
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(2000, load_card_data)  # Wait 2 seconds after UI startup

def check_dependencies():
    """
    Check for required dependencies and display helpful error messages
    if any are missing.
    """
    missing_deps = []
    
    try:
        import smartcard
    except ImportError:
        missing_deps.append("pyscard")
    
    try:
        import nfc
    except ImportError:
        missing_deps.append("nfcpy")
    
    try:
        from cryptography.hazmat.primitives import hashes
    except ImportError:
        missing_deps.append("cryptography")
    
    # Check OS-specific Bluetooth dependencies
    system = platform.system().lower()
    if system == "windows":
        try:
            import bleak
        except ImportError:
            missing_deps.append("bleak")
    else:
        try:
            import bluetooth
        except ImportError:
            missing_deps.append("pybluez")
    
    if missing_deps:
        print("Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nInstall missing dependencies with:")
        print(f"pip install {' '.join(missing_deps)}")
        return False
    
    return True

def parse_arguments():
    """
    Parse command line arguments for various operational modes.
    Supports attack modes, debugging, headless operation, and testing.
    """
    parser = argparse.ArgumentParser(
        description='NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Start GUI application
  %(prog)s --replay session.json        # Load replay attack session
  %(prog)s --preplay database.json      # Load pre-play attack database
  %(prog)s --no-gui --debug             # Headless mode with debug output
  %(prog)s --scan-android               # Scan for Android devices and exit
  %(prog)s --test                       # Run comprehensive test suite
  %(prog)s --export-session card.json   # Export card data to session file
        """
    )
    
    # Attack modes
    attack_group = parser.add_argument_group('Attack Modes')
    attack_group.add_argument(
        '--replay',
        metavar='SESSION_FILE',
        help='Load and activate replay attack mode with session file'
    )
    attack_group.add_argument(
        '--preplay',
        metavar='DATABASE_FILE', 
        help='Load and activate pre-play attack mode with database file'
    )
    
    # Android companion options
    android_group = parser.add_argument_group('Android Companion')
    android_group.add_argument(
        '--scan-android',
        action='store_true',
        help='Scan for Android companion devices and exit'
    )
    android_group.add_argument(
        '--connect-android',
        metavar='DEVICE_ADDRESS',
        help='Connect to specific Android device by BLE address'
    )
    android_group.add_argument(
        '--send-to-android',
        metavar='SESSION_FILE',
        help='Send session file to connected Android device'
    )
    
    # Data processing options
    data_group = parser.add_argument_group('Data Processing')
    data_group.add_argument(
        '--export-session',
        metavar='OUTPUT_FILE',
        help='Export current card data to session file'
    )
    data_group.add_argument(
        '--analyze-card',
        action='store_true',
        help='Perform complete card analysis and exit'
    )
    data_group.add_argument(
        '--extract-keys',
        action='store_true',
        help='Run key derivation analysis on loaded cards'
    )
    
    # Testing and validation
    test_group = parser.add_argument_group('Testing and Validation')
    test_group.add_argument(
        '--test',
        action='store_true',
        help='Run comprehensive test suite'
    )
    test_group.add_argument(
        '--validate-session',
        metavar='SESSION_FILE',
        help='Validate session file format and content'
    )
    test_group.add_argument(
        '--benchmark',
        action='store_true',
        help='Run performance benchmarks'
    )
    
    # General options
    general_group = parser.add_argument_group('General Options')
    general_group.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    general_group.add_argument(
        '--no-gui',
        action='store_true',
        help='Run in headless mode (CLI only)'
    )
    general_group.add_argument(
        '--config',
        metavar='CONFIG_FILE',
        help='Load configuration from file'
    )
    general_group.add_argument(
        '--log-file',
        metavar='LOG_FILE',
        help='Specify custom log file location'
    )
    general_group.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity (use -vv for very verbose)'
    )
    
    return parser.parse_args()

def main():
    """
    Main entry point for the NFSP00F3R application.
    Handles dependency checking, exception handling, and application lifecycle.
    """
    # parse command line arguments
    args = parse_arguments()
    
    # Check dependencies first
    if not check_dependencies():
        return 1
    
    try:
        # Create application instance with CLI args
        app = Application(sys.argv, args)
        
        # configure attack mode if specified
        if args.replay or args.preplay:
            logging.info(f"CLI attack mode: {'replay' if args.replay else 'preplay'}")
            
        # Install global exception handler
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            
            # Show error dialog
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Critical Error")
            msg.setText("A critical error occurred. Please check the log files.")
            msg.setDetailedText(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            msg.exec_()
        
        sys.excepthook = handle_exception
        
        # Run application
        return app.exec_()
        
    except Exception as e:
        print(f"Failed to start application: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Set high DPI support for modern displays
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Run application
    sys.exit(main())
