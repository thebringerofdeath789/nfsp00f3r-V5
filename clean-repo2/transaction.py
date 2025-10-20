#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - EMV Terminal and Smart Card Manager
=======================================================

File: transaction.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: EMV transaction processing and simulation engine

Classes:
- TransactionEngine: Main transaction processing class
- EMVTransaction: Individual transaction handler
- CryptogramGenerator: AC/ARQC generation engine
- TransactionReplay: Replay attack implementation
- BulkTransactionGenerator: Bulk transaction testing

Functions:
- generate_unpredictable_number(): Generate UN for transactions
- calculate_transaction_hash(): Calculate transaction verification hash
- format_transaction_data(): Format transaction for logging

This module implements complete EMV transaction flows including
application selection, cardholder verification, transaction authorization,
and script processing. Supports both genuine transactions and attack
scenarios for security research.

Based on EMV 4.3 specification and ISO/IEC 7816 standards.
"""

import logging
import time
import random
import hashlib
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from PyQt5.QtCore import QObject, QThread, pyqtSignal

class TransactionType(Enum):
    """EMV transaction types."""
    PURCHASE = "00"
    CASH_ADVANCE = "01"
    REFUND = "20"
    BALANCE_INQUIRY = "31"
    PIN_VERIFY = "40"
    PRE_AUTHORIZATION = "03"
    COMPLETION = "04"
    ADJUSTMENT = "02"
    VOID = "05"

class TransactionResult(Enum):
    """Transaction result codes."""
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    PENDING = "PENDING"

class CVMResult(Enum):
    """Cardholder Verification Method results."""
    SUCCESSFUL = "SUCCESS"
    FAILED = "FAILED"
    NOT_PERFORMED = "NOT_PERFORMED"
    UNKNOWN = "UNKNOWN"

@dataclass
class TransactionData:
    """Container for transaction data."""
    transaction_id: str
    transaction_type: TransactionType
    amount: int  # Amount in cents
    currency_code: str
    merchant_id: str
    terminal_id: str
    timestamp: datetime
    
    # EMV specific data
    aid: str = ""
    application_label: str = ""
    pan: str = ""
    pan_sequence: str = "00"
    expiry_date: str = ""
    cardholder_name: str = ""
    
    # Terminal data
    terminal_country_code: str = "0840"  # USA
    terminal_capabilities: str = "E0F8C8"
    terminal_type: str = "22"
    terminal_application_version: str = "0096"
    
    # Transaction specific
    transaction_date: str = ""
    transaction_time: str = ""
    unpredictable_number: str = ""
    transaction_sequence_counter: str = "0001"
    
    # Verification data
    tvr: str = "0000000000"  # Terminal Verification Results
    tsi: str = "0000"        # Transaction Status Information
    aip: str = "1800"        # Application Interchange Profile
    
    # ICC data
    application_transaction_counter: str = "0001"
    application_cryptogram: str = ""
    cryptogram_information_data: str = ""
    issuer_application_data: str = ""
    
    # CVM
    cvm_performed: CVMResult = CVMResult.NOT_PERFORMED
    cvm_results: str = "000000"
    
    # Authorization
    authorization_code: str = ""
    authorization_response_code: str = ""
    
    # Result
    result: TransactionResult = TransactionResult.PENDING
    result_message: str = ""
    
    def __post_init__(self):
        """Initialize derived fields."""
        if not self.transaction_date:
            self.transaction_date = self.timestamp.strftime("%y%m%d")
        if not self.transaction_time:
            self.transaction_time = self.timestamp.strftime("%H%M%S")
        if not self.unpredictable_number:
            self.unpredictable_number = generate_unpredictable_number()

@dataclass
class EMVTag:
    """EMV tag data structure."""
    tag: str
    length: int
    value: str
    description: str = ""

class TransactionEngine(QObject):
    """
    Main transaction processing engine.
    Handles complete EMV transaction flows and attack scenarios.
    """
    
    # Signals
    transaction_started = pyqtSignal(str)  # transaction_id
    transaction_completed = pyqtSignal(str, str)  # transaction_id, result
    transaction_step = pyqtSignal(str, str)  # transaction_id, step_description
    apdu_transmitted = pyqtSignal(str, str, str)  # transaction_id, command, response
    error_occurred = pyqtSignal(str, str)  # transaction_id, error_message
    
    def __init__(self, card_manager, reader_manager):
        super().__init__()
        self.card_manager = card_manager
        self.reader_manager = reader_manager
        self.logger = logging.getLogger(__name__)
        
        # Active transactions
        self.active_transactions: Dict[str, TransactionData] = {}
        
        # Transaction sequence counter
        self.sequence_counter = 1
        
        # Configuration
        self.terminal_config = {
            'terminal_id': '12345678',
            'merchant_id': '123456789012345',
            'merchant_category_code': '5999',
            'country_code': '0840',  # USA
            'currency_code': '0840',  # USD
            'capabilities': 'E0F8C8',
            'additional_capabilities': 'F000F0A001',
            'type': '22',
            'application_version': '0096'
        }
        
        # IAC (Issuer Action Codes) for testing
        self.iac_default = "0000000000"
        self.iac_denial = "0000000000"
        self.iac_online = "0000000000"
        
        self.logger.info("Transaction engine initialized")
    
    def create_transaction(self, transaction_type: str, amount: int, 
                         currency_code: str = "0840", **kwargs) -> str:
        """
        Create a new transaction.
        
        Args:
            transaction_type: Type of transaction
            amount: Amount in cents
            currency_code: ISO currency code
            **kwargs: Additional transaction parameters
            
        Returns:
            Transaction ID
        """
        try:
            # Generate transaction ID
            transaction_id = f"TXN_{int(time.time())}_{self.sequence_counter:04d}"
            self.sequence_counter += 1
            
            # Parse transaction type
            if transaction_type.upper() in [t.name for t in TransactionType]:
                txn_type = TransactionType[transaction_type.upper()]
            else:
                txn_type = TransactionType.PURCHASE
            
            # Create transaction data
            transaction = TransactionData(
                transaction_id=transaction_id,
                transaction_type=txn_type,
                amount=amount,
                currency_code=currency_code,
                merchant_id=kwargs.get('merchant_id', self.terminal_config['merchant_id']),
                terminal_id=kwargs.get('terminal_id', self.terminal_config['terminal_id']),
                timestamp=datetime.now(),
                **{k: v for k, v in kwargs.items() if k not in ['merchant_id', 'terminal_id']}
            )
            
            self.active_transactions[transaction_id] = transaction
            
            self.logger.info(f"Created transaction {transaction_id}: {transaction_type} for {amount/100:.2f}")
            return transaction_id
            
        except Exception as e:
            self.logger.error(f"Failed to create transaction: {e}")
            raise
    
    def run_transaction(self, transaction_id: str, reader_name: str) -> bool:
        """
        Execute a transaction on the specified reader.
        
        Args:
            transaction_id: Transaction to execute
            reader_name: Reader to use for transaction
            
        Returns:
            True if transaction started successfully
        """
        try:
            if transaction_id not in self.active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            transaction = self.active_transactions[transaction_id]
            
            # Get reader
            reader = self.reader_manager.get_reader(reader_name)
            if not reader:
                raise ValueError(f"Reader {reader_name} not available")
            
            if not reader.is_card_present():
                raise ValueError("No card present in reader")
            
            self.transaction_started.emit(transaction_id)
            
            # Run transaction in separate thread
            transaction_thread = EMVTransaction(
                transaction, reader, self
            )
            transaction_thread.finished.connect(
                lambda: self._on_transaction_finished(transaction_id)
            )
            transaction_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start transaction {transaction_id}: {e}")
            self.error_occurred.emit(transaction_id, str(e))
            return False
    
    def _on_transaction_finished(self, transaction_id: str):
        """Handle transaction completion."""
        if transaction_id in self.active_transactions:
            transaction = self.active_transactions[transaction_id]
            self.transaction_completed.emit(transaction_id, transaction.result.value)
            self.logger.info(f"Transaction {transaction_id} completed: {transaction.result.value}")
    
    def get_transaction(self, transaction_id: str) -> Optional[TransactionData]:
        """Get transaction data."""
        return self.active_transactions.get(transaction_id)
    
    def cancel_transaction(self, transaction_id: str):
        """Cancel an active transaction."""
        if transaction_id in self.active_transactions:
            self.active_transactions[transaction_id].result = TransactionResult.CANCELLED
            self.transaction_completed.emit(transaction_id, "CANCELLED")
    
    def get_active_transactions(self) -> List[str]:
        """Get list of active transaction IDs."""
        return list(self.active_transactions.keys())

    def start_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """
        Start a new transaction.
        
        Args:
            transaction_data: Dictionary containing transaction parameters
            
        Returns:
            Transaction ID
        """
        try:
            # Extract transaction parameters
            transaction_type = transaction_data.get('type', 'PURCHASE')
            amount = transaction_data.get('amount', 0)
            currency_code = transaction_data.get('currency', '0840')  # Default to USD
            
            # Create transaction
            transaction_id = self.create_transaction(
                transaction_type=transaction_type,
                amount=amount,
                currency_code=currency_code
            )
            
            # Run transaction on default reader
            reader_name = transaction_data.get('reader', 'default')
            if self.run_transaction(transaction_id, reader_name):
                self.logger.info(f"Started transaction {transaction_id}")
                return transaction_id
            else:
                self.logger.error(f"Failed to start transaction {transaction_id}")
                return ""
                
        except Exception as e:
            self.logger.error(f"Failed to start transaction: {e}")
            return ""


class EMVTransaction(QThread):
    """
    Individual EMV transaction processor.
    Implements complete EMV transaction flow.
    """
    
    def __init__(self, transaction_data: TransactionData, reader, engine):
        super().__init__()
        self.transaction = transaction_data
        self.reader = reader
        self.engine = engine
        self.logger = logging.getLogger(__name__)
        
        # Transaction state
        self.current_step = ""
        self.selected_application = None
        self.emv_tags = {}
        
        # APDU responses
        self.apdu_log = []
    
    def run(self):
        """Execute the EMV transaction flow."""
        try:
            self.logger.info(f"Starting EMV transaction {self.transaction.transaction_id}")
            
            # Step 1: Application Selection
            if not self.application_selection():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Application selection failed"
                return
            
            # Step 2: Application Initialization
            if not self.application_initialization():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Application initialization failed"
                return
            
            # Step 3: Read Application Data
            if not self.read_application_data():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Failed to read application data"
                return
            
            # Step 4: Data Authentication
            if not self.data_authentication():
                self.logger.warning("Data authentication failed, continuing...")
            
            # Step 5: Processing Restrictions
            if not self.processing_restrictions():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Processing restrictions failed"
                return
            
            # Step 6: Cardholder Verification
            if not self.cardholder_verification():
                self.logger.warning("Cardholder verification failed, continuing...")
            
            # Step 7: Terminal Risk Management
            if not self.terminal_risk_management():
                self.logger.warning("Terminal risk management failed, continuing...")
            
            # Step 8: Terminal Action Analysis
            if not self.terminal_action_analysis():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Terminal action analysis failed"
                return
            
            # Step 9: Card Action Analysis
            if not self.card_action_analysis():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Card action analysis failed"
                return
            
            # Step 10: Online Processing (simulated)
            if not self.online_processing():
                self.transaction.result = TransactionResult.DECLINED
                self.transaction.result_message = "Online authorization failed"
                return
            
            # Step 11: Script Processing
            self.script_processing()
            
            # Transaction completed successfully
            self.transaction.result = TransactionResult.APPROVED
            self.transaction.result_message = "Transaction approved"
            
        except Exception as e:
            self.logger.error(f"Transaction error: {e}")
            self.transaction.result = TransactionResult.ERROR
            self.transaction.result_message = str(e)
    
    def application_selection(self) -> bool:
        """EMV Application Selection process."""
        self.current_step = "Application Selection"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Select Payment System Environment
            pse_command = bytes.fromhex("00A404000E315041592E5359532E444446303100")
            response, sw1, sw2 = self.transmit_apdu(pse_command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                # PSE found, read directory
                self.logger.info("PSE found, reading directory")
                
                # Read PSE directory
                read_command = bytes.fromhex("00B2010C00")
                response, sw1, sw2 = self.transmit_apdu(read_command)
                
                if sw1 == 0x90 and sw2 == 0x00:
                    # Parse response for AIDs
                    aids = self.parse_pse_response(response)
                    if aids:
                        # Select first available AID
                        for aid in aids:
                            if self.select_application(aid):
                                self.transaction.aid = aid.hex().upper()
                                return True
            
            # PSE not available, try list of known AIDs
            known_aids = [
                bytes.fromhex("A0000000041010"),  # Mastercard
                bytes.fromhex("A0000000031010"),  # Visa
                bytes.fromhex("A0000000032010"),  # Visa Electron
                bytes.fromhex("A0000000033010"),  # Visa Interlink
                bytes.fromhex("A0000000038010"),  # Visa Plus
                bytes.fromhex("A0000000421010"),  # Maestro
                bytes.fromhex("A0000000651010"),  # JCB
                bytes.fromhex("A0000001523010"),  # Discover
                bytes.fromhex("A0000003330101"),  # American Express
            ]
            
            for aid in known_aids:
                if self.select_application(aid):
                    self.transaction.aid = aid.hex().upper()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Application selection failed: {e}")
            return False
    
    def select_application(self, aid: bytes) -> bool:
        """Select specific application."""
        try:
            # Build SELECT command
            select_command = bytes([0x00, 0xA4, 0x04, 0x00, len(aid)]) + aid + bytes([0x00])
            response, sw1, sw2 = self.transmit_apdu(select_command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                self.selected_application = aid
                self.logger.info(f"Selected application: {aid.hex().upper()}")
                
                # Parse FCI template
                fci_data = self.parse_fci_template(response)
                self.emv_tags.update(fci_data)
                
                return True
            else:
                self.logger.debug(f"Failed to select AID {aid.hex().upper()}: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error selecting application: {e}")
            return False
    
    def application_initialization(self) -> bool:
        """EMV Application Initialization."""
        self.current_step = "Application Initialization"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # GET PROCESSING OPTIONS
            pdol_data = self.build_pdol_data()
            
            command = bytes([0x80, 0xA8, 0x00, 0x00, len(pdol_data)]) + pdol_data + bytes([0x00])
            response, sw1, sw2 = self.transmit_apdu(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                # Parse response
                if response[0] == 0x77:  # Response Message Template Format 2
                    self.parse_response_template(response[1:])
                elif response[0] == 0x80:  # Response Message Template Format 1
                    self.parse_format1_response(response[1:])
                
                return True
            else:
                self.logger.error(f"GET PROCESSING OPTIONS failed: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"Application initialization failed: {e}")
            return False
    
    def read_application_data(self) -> bool:
        """Read Application Data using AFL."""
        self.current_step = "Read Application Data"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Get AFL (Application File Locator)
            afl = self.emv_tags.get('94', '')
            if not afl:
                self.logger.error("No AFL found")
                return False
            
            # Parse AFL and read records
            afl_bytes = bytes.fromhex(afl)
            
            for i in range(0, len(afl_bytes), 4):
                if i + 3 >= len(afl_bytes):
                    break
                
                sfi = afl_bytes[i] >> 3
                start_record = afl_bytes[i + 1]
                end_record = afl_bytes[i + 2]
                
                # Read records
                for record_num in range(start_record, end_record + 1):
                    p2 = (sfi << 3) | 0x04
                    command = bytes([0x00, 0xB2, record_num, p2, 0x00])
                    
                    response, sw1, sw2 = self.transmit_apdu(command)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        # Parse EMV data
                        self.parse_emv_record(response)
                    else:
                        self.logger.warning(f"Failed to read record {record_num}: {sw1:02X}{sw2:02X}")
            
            # Extract key data
            self.extract_card_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to read application data: {e}")
            return False
    
    def data_authentication(self) -> bool:
        """Perform data authentication (SDA/DDA/CDA)."""
        self.current_step = "Data Authentication"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Check AIP for data authentication support
            aip = self.emv_tags.get('82', '0000')
            aip_bytes = bytes.fromhex(aip)
            
            if len(aip_bytes) >= 1:
                # Check if DDA is supported
                if aip_bytes[0] & 0x20:
                    return self.perform_dda()
                # Check if SDA is supported
                elif aip_bytes[0] & 0x40:
                    return self.perform_sda()
            
            # No data authentication supported
            self.logger.info("No data authentication supported")
            return True
            
        except Exception as e:
            self.logger.error(f"Data authentication failed: {e}")
            return False
    
    def perform_sda(self) -> bool:
        """Perform Static Data Authentication."""
        try:
            self.logger.info("Performing Static Data Authentication")
            
            # For SDA, we would verify the Signed Static Application Data
            # This is a simplified implementation
            
            # Check for required data elements
            required_tags = ['90', '92', '93']  # Issuer Public Key Certificate, Issuer Public Key Remainder, Signed Static Application Data
            
            for tag in required_tags:
                if tag not in self.emv_tags:
                    self.logger.warning(f"SDA: Missing tag {tag}")
                    return False
            
            # In a real implementation, we would:
            # 1. Retrieve and validate the issuer public key
            # 2. Verify the Signed Static Application Data
            # 3. Hash the static data and compare with the hash in SSAD
            
            self.logger.info("SDA completed (simulated)")
            return True
            
        except Exception as e:
            self.logger.error(f"SDA failed: {e}")
            return False
    
    def perform_dda(self) -> bool:
        """Perform Dynamic Data Authentication."""
        try:
            self.logger.info("Performing Dynamic Data Authentication")
            
            # INTERNAL AUTHENTICATE command for DDA
            challenge = generate_unpredictable_number()
            command = bytes.fromhex(f"0088000004{challenge}00")
            
            response, sw1, sw2 = self.transmit_apdu(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                # Parse the response (Signed Dynamic Application Data)
                # In a real implementation, we would verify the signature
                self.logger.info("DDA completed (simulated)")
                return True
            else:
                self.logger.error(f"DDA INTERNAL AUTHENTICATE failed: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"DDA failed: {e}")
            return False
    
    def processing_restrictions(self) -> bool:
        """Check processing restrictions."""
        self.current_step = "Processing Restrictions"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Check application usage control
            auc = self.emv_tags.get('9F07', '')
            if auc:
                # Simplified check - in reality would check against terminal capabilities
                self.logger.info(f"Application Usage Control: {auc}")
            
            # Check application effective/expiry dates
            effective_date = self.emv_tags.get('5F25', '')
            expiry_date = self.emv_tags.get('5F24', '')
            
            if effective_date:
                # Check if application is effective
                self.logger.info(f"Application Effective Date: {effective_date}")
            
            if expiry_date:
                # Check if application has expired
                self.logger.info(f"Application Expiry Date: {expiry_date}")
                self.transaction.expiry_date = expiry_date
            
            return True
            
        except Exception as e:
            self.logger.error(f"Processing restrictions check failed: {e}")
            return False
    
    def cardholder_verification(self) -> bool:
        """Perform cardholder verification."""
        self.current_step = "Cardholder Verification"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Get CVM List
            cvm_list = self.emv_tags.get('8E', '')
            if not cvm_list:
                self.logger.info("No CVM List found")
                self.transaction.cvm_performed = CVMResult.NOT_PERFORMED
                return True
            
            # Parse CVM List
            cvm_bytes = bytes.fromhex(cvm_list)
            if len(cvm_bytes) < 10:
                self.logger.error("Invalid CVM List")
                return False
            
            # Amount thresholds
            amount_x = int.from_bytes(cvm_bytes[0:4], 'big')
            amount_y = int.from_bytes(cvm_bytes[4:8], 'big')
            
            # Process CVM rules
            for i in range(8, len(cvm_bytes), 2):
                if i + 1 >= len(cvm_bytes):
                    break
                
                cvm_code = cvm_bytes[i]
                cvm_condition = cvm_bytes[i + 1]
                
                # Check condition
                if self.check_cvm_condition(cvm_condition, amount_x, amount_y):
                    # Perform CVM
                    if self.perform_cvm(cvm_code):
                        self.transaction.cvm_performed = CVMResult.SUCCESSFUL
                        return True
                    else:
                        # If fail, check if should continue
                        if cvm_code & 0x40 == 0:  # Fail if unsuccessful
                            self.transaction.cvm_performed = CVMResult.FAILED
                            return False
            
            # No CVM performed
            self.transaction.cvm_performed = CVMResult.NOT_PERFORMED
            return True
            
        except Exception as e:
            self.logger.error(f"Cardholder verification failed: {e}")
            return False
    
    def check_cvm_condition(self, condition: int, amount_x: int, amount_y: int) -> bool:
        """Check CVM condition."""
        transaction_amount = self.transaction.amount
        
        if condition == 0x00:  # Always
            return True
        elif condition == 0x01:  # If unattended cash
            return self.transaction.transaction_type == TransactionType.CASH_ADVANCE
        elif condition == 0x02:  # If not unattended cash and not manual cash and not purchase with cashback
            return self.transaction.transaction_type == TransactionType.PURCHASE
        elif condition == 0x03:  # If terminal supports CVM
            return True  # Simplified
        elif condition == 0x04:  # If manual cash
            return False  # Not supported
        elif condition == 0x05:  # If purchase with cashback
            return False  # Not implemented
        elif condition == 0x06:  # If transaction is in the application currency and is under amount X
            return transaction_amount < amount_x
        elif condition == 0x07:  # If transaction is in the application currency and is over amount X
            return transaction_amount >= amount_x
        elif condition == 0x08:  # If transaction is in the application currency and is under amount Y
            return transaction_amount < amount_y
        elif condition == 0x09:  # If transaction is in the application currency and is over amount Y
            return transaction_amount >= amount_y
        else:
            return False
    
    def perform_cvm(self, cvm_code: int) -> bool:
        """Perform specific CVM."""
        cvm_method = cvm_code & 0x3F
        
        if cvm_method == 0x00:  # Fail CVM processing
            return False
        elif cvm_method == 0x01:  # Plaintext PIN verification performed by ICC
            return self.verify_pin_icc()
        elif cvm_method == 0x02:  # Enciphered PIN verified online
            return self.verify_pin_online()
        elif cvm_method == 0x03:  # Plaintext PIN verification performed by ICC and signature (paper)
            return self.verify_pin_icc()
        elif cvm_method == 0x04:  # Enciphered PIN verification performed by ICC
            return self.verify_pin_icc_encrypted()
        elif cvm_method == 0x05:  # Enciphered PIN verification performed by ICC and signature (paper)
            return self.verify_pin_icc_encrypted()
        elif cvm_method == 0x1E:  # Signature (paper)
            return True  # Always successful for signature
        elif cvm_method == 0x1F:  # No CVM required
            return True
        else:
            self.logger.warning(f"Unknown CVM method: {cvm_method:02X}")
            return False
    
    def verify_pin_icc(self) -> bool:
        """Perform ICC PIN verification."""
        try:
            # VERIFY command - simplified PIN (1234)
            pin_data = "1234FFFFFFFF"
            command = bytes.fromhex(f"002000800804{pin_data}00")
            
            response, sw1, sw2 = self.transmit_apdu(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                self.logger.info("PIN verification successful")
                return True
            else:
                self.logger.warning(f"PIN verification failed: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"PIN verification error: {e}")
            return False
    
    def verify_pin_icc_encrypted(self) -> bool:
        """Perform encrypted ICC PIN verification."""
        # For now, treat same as plaintext
        return self.verify_pin_icc()
    
    def verify_pin_online(self) -> bool:
        """Online PIN verification (simulated)."""
        # Simulate online PIN verification
        self.logger.info("Online PIN verification (simulated)")
        return True
    
    def terminal_risk_management(self) -> bool:
        """Perform terminal risk management."""
        self.current_step = "Terminal Risk Management"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Floor limit check
            floor_limit = 0  # No floor limit for this example
            if self.transaction.amount > floor_limit:
                # Set bit in TVR for transaction exceeds floor limit
                tvr = list(bytes.fromhex(self.transaction.tvr))
                tvr[3] |= 0x80  # Set bit 8 of byte 4
                self.transaction.tvr = ''.join(f'{b:02X}' for b in tvr)
            
            # Random transaction selection
            if random.randint(1, 100) <= 10:  # 10% random selection
                tvr = list(bytes.fromhex(self.transaction.tvr))
                tvr[3] |= 0x40  # Set bit 7 of byte 4
                self.transaction.tvr = ''.join(f'{b:02X}' for b in tvr)
            
            # Velocity checking (simplified)
            # In real implementation, would check transaction frequency
            
            return True
            
        except Exception as e:
            self.logger.error(f"Terminal risk management failed: {e}")
            return False
    
    def terminal_action_analysis(self) -> bool:
        """Perform terminal action analysis."""
        self.current_step = "Terminal Action Analysis"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            tvr_bytes = bytes.fromhex(self.transaction.tvr)
            iac_default_bytes = bytes.fromhex(self.iac_default)
            iac_denial_bytes = bytes.fromhex(self.iac_denial)
            iac_online_bytes = bytes.fromhex(self.iac_online)
            
            # Check for denial
            for i in range(len(tvr_bytes)):
                if i < len(iac_denial_bytes):
                    if tvr_bytes[i] & iac_denial_bytes[i]:
                        self.logger.info("Transaction denied by terminal")
                        return False
            
            # Check for online
            online_required = False
            for i in range(len(tvr_bytes)):
                if i < len(iac_online_bytes):
                    if tvr_bytes[i] & iac_online_bytes[i]:
                        online_required = True
                        break
            
            if online_required:
                self.logger.info("Online authorization required")
                # Set TSI bit for online authorization
                tsi = list(bytes.fromhex(self.transaction.tsi))
                tsi[0] |= 0x80  # Set bit 8
                self.transaction.tsi = ''.join(f'{b:02X}' for b in tsi)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Terminal action analysis failed: {e}")
            return False
    
    def card_action_analysis(self) -> bool:
        """Request cryptogram from card."""
        self.current_step = "Card Action Analysis"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Build GENERATE AC command
            cdol1_data = self.build_cdol1_data()
            
            # Determine cryptogram type
            if bytes.fromhex(self.transaction.tsi)[0] & 0x80:  # Online required
                p1 = 0x80  # AAC (Application Authentication Cryptogram)
            else:
                p1 = 0x40  # TC (Transaction Certificate)
            
            command = bytes([0x80, 0xAE, p1, 0x00, len(cdol1_data)]) + cdol1_data + bytes([0x00])
            response, sw1, sw2 = self.transmit_apdu(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                # Parse cryptogram response
                self.parse_cryptogram_response(response)
                return True
            else:
                self.logger.error(f"GENERATE AC failed: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            self.logger.error(f"Card action analysis failed: {e}")
            return False
    
    def online_processing(self) -> bool:
        """Simulate online authorization processing."""
        self.current_step = "Online Processing"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # Simulate online authorization
            self.logger.info("Performing online authorization (simulated)")
            
            # Generate authorization response
            auth_code = f"{random.randint(100000, 999999)}"
            self.transaction.authorization_code = auth_code
            self.transaction.authorization_response_code = "00"  # Approved
            
            # Generate ARPC (Authorization Response Cryptogram)
            # In real implementation, this would come from the issuer
            arpc = generate_unpredictable_number()[:8]
            
            # Second GENERATE AC for final cryptogram
            cdol2_data = self.build_cdol2_data(arpc)
            
            command = bytes([0x80, 0xAE, 0x40, 0x00, len(cdol2_data)]) + cdol2_data + bytes([0x00])
            response, sw1, sw2 = self.transmit_apdu(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                self.parse_cryptogram_response(response)
                return True
            else:
                self.logger.warning(f"Second GENERATE AC failed: {sw1:02X}{sw2:02X}")
                return True  # Continue anyway
                
        except Exception as e:
            self.logger.error(f"Online processing failed: {e}")
            return False
    
    def script_processing(self):
        """Process issuer scripts (if any)."""
        self.current_step = "Script Processing"
        self.engine.transaction_step.emit(self.transaction.transaction_id, self.current_step)
        
        try:
            # In real implementation, would process issuer authentication data
            # and issuer scripts from online response
            self.logger.info("Script processing completed (simulated)")
            
        except Exception as e:
            self.logger.error(f"Script processing failed: {e}")
    
    def transmit_apdu(self, apdu: bytes) -> Tuple[bytes, int, int]:
        """Transmit APDU and log the exchange."""
        try:
            response, sw1, sw2 = self.reader.transmit(apdu)
            
            # Log the APDU exchange
            self.apdu_log.append({
                'command': apdu.hex().upper(),
                'response': response.hex().upper() + f"{sw1:02X}{sw2:02X}",
                'timestamp': time.time()
            })
            
            # Emit signal for real-time monitoring
            self.engine.apdu_transmitted.emit(
                self.transaction.transaction_id,
                apdu.hex().upper(),
                response.hex().upper() + f"{sw1:02X}{sw2:02X}"
            )
            
            return response, sw1, sw2
            
        except Exception as e:
            self.logger.error(f"APDU transmission failed: {e}")
            raise
    
    def build_pdol_data(self) -> bytes:
        """Build PDOL (Processing Options Data Object List) data."""
        # Default PDOL data for GET PROCESSING OPTIONS
        pdol_data = bytes([0x83, 0x00])  # Empty PDOL
        
        # Check if PDOL exists in FCI
        pdol = self.emv_tags.get('9F38', '')
        if pdol:
            # Parse PDOL and build data
            # This is simplified - real implementation would parse PDOL structure
            pdol_data = bytes.fromhex('83' + f'{len(pdol)//2:02X}' + pdol)
        
        return pdol_data
    
    def build_cdol1_data(self) -> bytes:
        """Build CDOL1 data for GENERATE AC."""
        # Default transaction data
        data = {
            '9F02': f"{self.transaction.amount:012d}",  # Amount Authorized
            '9F03': "000000000000",  # Amount Other
            '9F1A': self.transaction.terminal_country_code,  # Terminal Country Code
            '95': self.transaction.tvr,  # TVR
            '5F2A': self.transaction.currency_code,  # Transaction Currency Code
            '9A': self.transaction.transaction_date,  # Transaction Date
            '9C': self.transaction.transaction_type.value,  # Transaction Type
            '9F37': self.transaction.unpredictable_number,  # Unpredictable Number
        }
        
        # Build data according to CDOL1
        cdol1 = self.emv_tags.get('8C', '')
        if cdol1:
            # Parse CDOL1 and build data according to specified format
            try:
                from tlv import TLVParser
                parser = TLVParser()
                cdol1_bytes = bytes.fromhex(cdol1)
                
                # Parse CDOL1 structure
                result = b''
                i = 0
                while i < len(cdol1_bytes):
                    # Extract tag
                    tag_start = i
                    if cdol1_bytes[i] & 0x1F == 0x1F:  # Multi-byte tag
                        i += 1
                        while i < len(cdol1_bytes) and cdol1_bytes[i] & 0x80:
                            i += 1
                        i += 1
                    else:  # Single byte tag
                        i += 1
                    
                    if i >= len(cdol1_bytes):
                        break
                        
                    tag = cdol1_bytes[tag_start:i].hex().upper()
                    length = cdol1_bytes[i]
                    i += 1
                    
                    # Get data for this tag
                    if tag in data:
                        tag_data = bytes.fromhex(data[tag])
                        # Pad or truncate to required length
                        if len(tag_data) < length:
                            tag_data += b'\x00' * (length - len(tag_data))
                        elif len(tag_data) > length:
                            tag_data = tag_data[:length]
                        result += tag_data
                    else:
                        # Provide default data if tag not available
                        result += b'\x00' * length
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Error parsing CDOL1: {e}")
                # Fall back to simple concatenation
        
        # Return concatenated data
        result = b''
        for tag, value in data.items():
            result += bytes.fromhex(value)
        
        return result
    
    def build_cdol2_data(self, arpc: str) -> bytes:
        """Build CDOL2 data for second GENERATE AC."""
        # Include ARPC and other data as required
        data = self.build_cdol1_data()  # Start with CDOL1 data
        data += bytes.fromhex(arpc)     # Add ARPC
        
        return data
    
    def parse_pse_response(self, data: bytes) -> List[bytes]:
        """Parse PSE response to extract AIDs."""
        aids = []
        # Simplified PSE parsing
        # Real implementation would properly parse TLV structure
        return aids
    
    def parse_fci_template(self, data: bytes) -> Dict[str, str]:
        """Parse FCI template response."""
        from .tlv import TLVParser
        
        parser = TLVParser()
        parsed = parser.parse(data)
        
        # Extract EMV tags
        tags = {}
        for item in parsed:
            tags[item['tag']] = item['value']
        
        return tags
    
    def parse_response_template(self, data: bytes):
        """Parse response message template format 2."""
        from .tlv import TLVParser
        
        parser = TLVParser()
        parsed = parser.parse(data)
        
        for item in parsed:
            self.emv_tags[item['tag']] = item['value']
    
    def parse_format1_response(self, data: bytes):
        """Parse response message template format 1."""
        if len(data) >= 2:
            aip = data[:2].hex().upper()
            self.emv_tags['82'] = aip
            
            if len(data) > 2:
                afl = data[2:].hex().upper()
                self.emv_tags['94'] = afl
    
    def parse_emv_record(self, data: bytes):
        """Parse EMV record data."""
        from .tlv import TLVParser
        
        parser = TLVParser()
        parsed = parser.parse(data)
        
        for item in parsed:
            self.emv_tags[item['tag']] = item['value']
    
    def parse_cryptogram_response(self, data: bytes):
        """Parse GENERATE AC response."""
        from .tlv import TLVParser
        
        parser = TLVParser()
        parsed = parser.parse(data)
        
        for item in parsed:
            self.emv_tags[item['tag']] = item['value']
            
            # Extract specific cryptogram data
            if item['tag'] == '9F26':  # Application Cryptogram
                self.transaction.application_cryptogram = item['value']
            elif item['tag'] == '9F27':  # Cryptogram Information Data
                self.transaction.cryptogram_information_data = item['value']
            elif item['tag'] == '9F10':  # Issuer Application Data
                self.transaction.issuer_application_data = item['value']
    
    def extract_card_data(self):
        """Extract key card data from EMV tags."""
        # Extract PAN
        pan = self.emv_tags.get('5A', '')
        if pan:
            # Remove padding
            pan_clean = pan.rstrip('F')
            self.transaction.pan = pan_clean
        
        # Extract cardholder name
        cardholder_name = self.emv_tags.get('5F20', '')
        if cardholder_name:
            try:
                name = bytes.fromhex(cardholder_name).decode('ascii', errors='ignore')
                self.transaction.cardholder_name = name.strip()
            except:
                pass
        
        # Extract application label
        app_label = self.emv_tags.get('50', '')
        if app_label:
            try:
                label = bytes.fromhex(app_label).decode('ascii', errors='ignore')
                self.transaction.application_label = label.strip()
            except:
                pass

class CryptogramGenerator:
    """
    Generate EMV cryptograms for testing and attack scenarios.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_arqc(self, transaction_data: TransactionData, 
                     master_key: bytes = None) -> str:
        """Generate ARQC (Authorization Request Cryptogram)."""
        try:
            # This is a simplified implementation
            # Real ARQC generation requires proper key derivation and MAC calculation
            
            if not master_key:
                # Use dummy key for testing
                master_key = b'\x00' * 16
            
            # Build transaction data for MAC
            mac_data = (
                transaction_data.amount.to_bytes(6, 'big') +
                bytes.fromhex(transaction_data.currency_code.zfill(4)) +
                bytes.fromhex(transaction_data.transaction_date) +
                bytes.fromhex(transaction_data.transaction_type.value) +
                bytes.fromhex(transaction_data.unpredictable_number)
            )
            
            # Generate MAC (simplified)
            mac = hashlib.sha256(master_key + mac_data).digest()[:8]
            
            return mac.hex().upper()
            
        except Exception as e:
            self.logger.error(f"ARQC generation failed: {e}")
            return "0000000000000000"
    
    def generate_tc(self, transaction_data: TransactionData,
                   master_key: bytes = None) -> str:
        """Generate TC (Transaction Certificate)."""
        # Similar to ARQC but with different parameters
        return self.generate_arqc(transaction_data, master_key)
    
    def generate_aac(self, transaction_data: TransactionData,
                    master_key: bytes = None) -> str:
        """Generate AAC (Application Authentication Cryptogram)."""
        # Similar to ARQC but indicates decline
        return self.generate_arqc(transaction_data, master_key)

class TransactionReplay:
    """
    Implement transaction replay attacks for security research.
    """
    
    def __init__(self, transaction_engine):
        self.engine = transaction_engine
        self.logger = logging.getLogger(__name__)
    
    def replay_transaction(self, original_transaction: TransactionData,
                          reader_name: str) -> bool:
        """Replay a previous transaction."""
        try:
            # Create replay transaction
            replay_id = self.engine.create_transaction(
                original_transaction.transaction_type.name,
                original_transaction.amount,
                original_transaction.currency_code,
                merchant_id=original_transaction.merchant_id,
                terminal_id=original_transaction.terminal_id
            )
            
            # Execute replay
            return self.engine.run_transaction(replay_id, reader_name)
            
        except Exception as e:
            self.logger.error(f"Transaction replay failed: {e}")
            return False

class BulkTransactionGenerator(QThread):
    """
    Generate bulk transactions for testing and cryptogram collection.
    """
    
    transaction_generated = pyqtSignal(str)  # transaction_id
    batch_completed = pyqtSignal(int, int)   # total, successful
    
    def __init__(self, transaction_engine, count: int, delay: float = 1.0):
        super().__init__()
        self.engine = transaction_engine
        self.count = count
        self.delay = delay
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Generate bulk transactions."""
        successful = 0
        
        for i in range(self.count):
            try:
                # Generate random transaction
                transaction_id = self.engine.create_transaction(
                    "PURCHASE",
                    random.randint(100, 50000),  # $1.00 to $500.00
                    "0840"  # USD
                )
                
                self.transaction_generated.emit(transaction_id)
                successful += 1
                
                time.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"Bulk transaction {i} failed: {e}")
        
        self.batch_completed.emit(self.count, successful)

def generate_unpredictable_number() -> str:
    """Generate 4-byte unpredictable number."""
    return f"{random.randint(0, 0xFFFFFFFF):08X}"

def calculate_transaction_hash(transaction_data: TransactionData) -> str:
    """Calculate hash of transaction for verification."""
    data = f"{transaction_data.transaction_id}{transaction_data.amount}{transaction_data.timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def format_transaction_data(transaction: TransactionData) -> Dict[str, Any]:
    """Format transaction data for logging/export."""
    return asdict(transaction)
