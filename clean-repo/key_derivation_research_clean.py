#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Key Derivation Research Module (Clean)
=========================================================

File: key_derivation_research_clean.py
Authors: Gregory King & Matthew Braunschweig  
Date: August 16, 2025
Description: Essential key derivation and cryptographic analysis for EMV cards
"""

import hashlib
import hmac
import struct
import time
import threading
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import statistics
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from Crypto.Cipher import DES3, AES
from Crypto.Hash import SHA256, SHA1, MD5
import binascii
import itertools
import json

@dataclass
class CardCryptoProfile:
    """Cryptographic profile for a single EMV card."""
    card_id: str
    pan: str
    pan_sequence: str = "00"
    expiry_date: str = ""
    service_code: str = ""
    pin: Optional[str] = None
    
    # Key-related data
    application_cryptogram: Optional[str] = None
    atc: Optional[str] = None  # Application Transaction Counter
    unpredictable_number: Optional[str] = None
    terminal_verification_results: Optional[str] = None
    transaction_date: Optional[str] = None
    transaction_type: Optional[str] = None
    amount_authorized: Optional[str] = None
    
    # Derived cryptographic material
    ac_session_key: Optional[str] = None
    mac_session_key: Optional[str] = None
    enc_session_key: Optional[str] = None
    
    # Card-specific cryptographic data
    card_verification_results: Optional[str] = None
    issuer_application_data: Optional[str] = None
    application_interchange_profile: Optional[str] = None
    
    # PIN-related crypto data
    pin_verification_data: Optional[str] = None
    pin_try_counter: Optional[int] = None
    offline_pin_verification_capability: Optional[str] = None
    
    # Additional EMV data
    cdol1_data: Optional[str] = None
    cdol2_data: Optional[str] = None
    pdol_data: Optional[str] = None
    
    # Analysis metadata
    extraction_timestamp: float = field(default_factory=time.time)
    analysis_notes: List[str] = field(default_factory=list)

@dataclass
class KeyDerivationResult:
    """Result of key derivation analysis."""
    derivation_method: str
    success_probability: float
    derived_keys: Dict[str, str]
    correlation_strength: float
    pattern_matches: List[str]
    confidence_score: float
    analysis_details: Dict[str, Any]

class KeyDerivationAnalyzer:
    """
    Multi-card key pattern analysis and derivation engine.
    Analyzes cryptographic patterns across multiple EMV cards.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.card_profiles: Dict[str, CardCryptoProfile] = {}
        self.derivation_results: List[KeyDerivationResult] = []
        
        # Known EMV key derivation methods
        self.derivation_methods = {
            'emv_option_a': self._derive_emv_option_a,
            'emv_option_b': self._derive_emv_option_b,
            'common_master_key': self._derive_common_master_key,
            'pin_based_derivation': self._derive_pin_based_keys,
            'statistical_analysis': self._perform_statistical_analysis
        }
        
    def add_card_profile(self, profile: CardCryptoProfile):
        """Add a card cryptographic profile for analysis."""
        self.card_profiles[profile.card_id] = profile
        self.logger.info(f"Added card profile: {profile.card_id} (PAN: {profile.pan[:6]}...)")
        
    def analyze_key_patterns(self) -> Dict[str, Any]:
        """Analyze cryptographic patterns across all card profiles."""
        if len(self.card_profiles) < 2:
            self.logger.warning("Need at least 2 card profiles for meaningful analysis")
            return {'error': 'Insufficient card data'}
            
        analysis_results = {
            'total_cards': len(self.card_profiles),
            'cards_with_pins': sum(1 for p in self.card_profiles.values() if p.pin),
            'derivation_attempts': {},
            'pattern_analysis': {},
            'recommendations': []
        }
        
        # Attempt each derivation method
        for method_name, method_func in self.derivation_methods.items():
            try:
                self.logger.info(f"Attempting {method_name} derivation")
                result = method_func()
                analysis_results['derivation_attempts'][method_name] = {
                    'success_probability': result.success_probability,
                    'pattern_matches': result.pattern_matches,
                    'confidence_score': result.confidence_score
                }
                
                if result.success_probability > 0.5:
                    analysis_results['recommendations'].append(
                        f"High success probability for {method_name}: {result.success_probability:.2f}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Derivation method {method_name} failed: {e}")
                analysis_results['derivation_attempts'][method_name] = {'error': str(e)}
                
        return analysis_results
        
    def _derive_emv_option_a(self) -> KeyDerivationResult:
        """EMV Option A key derivation (PAN-based)."""
        patterns = []
        derived_keys = {}
        correlations = []
        
        for card_id, profile in self.card_profiles.items():
            if not profile.pan or not profile.application_cryptogram:
                continue
                
            # EMV Option A uses PAN and PAN Sequence Number
            pan_data = profile.pan.ljust(16, 'F')[:16]
            psn_data = (profile.pan_sequence or '00').ljust(2, '0')[:2]
            
            # Standard EMV Option A derivation
            key_data = pan_data + psn_data + '0' * 12
            
            # Attempt to derive UDK (Unique DEA Key)
            master_key_candidates = self._generate_master_key_candidates()
            
            for master_key in master_key_candidates:
                try:
                    # Derive UDK using master key
                    udk = self._derive_3des_key(master_key, bytes.fromhex(key_data))
                    
                    # Test if this UDK can generate the observed cryptogram
                    if self._test_cryptogram_generation(udk, profile):
                        derived_keys[card_id] = {
                            'master_key': master_key.hex(),
                            'udk': udk.hex(),
                            'method': 'emv_option_a'
                        }
                        patterns.append('EMV Option A match')
                        correlations.append(0.8)
                        break
                        
                except Exception:
                    continue
                    
        success_probability = len(derived_keys) / len(self.card_profiles)
        correlation_strength = statistics.mean(correlations) if correlations else 0.0
        
        return KeyDerivationResult(
            derivation_method='emv_option_a',
            success_probability=success_probability,
            derived_keys=derived_keys,
            correlation_strength=correlation_strength,
            pattern_matches=patterns,
            confidence_score=success_probability * correlation_strength,
            analysis_details={
                'cards_analyzed': len(self.card_profiles),
                'successful_derivations': len(derived_keys),
                'method_description': 'EMV Option A PAN-based key derivation'
            }
        )
        
    def _derive_emv_option_b(self) -> KeyDerivationResult:
        """EMV Option B key derivation (random key per card)."""
        patterns = []
        derived_keys = {}
        correlations = []
        
        # Option B uses unique random keys per card
        cryptograms = []
        for profile in self.card_profiles.values():
            if profile.application_cryptogram:
                cryptograms.append(bytes.fromhex(profile.application_cryptogram))
                
        if len(cryptograms) < 2:
            return KeyDerivationResult('emv_option_b', 0.0, {}, 0.0, [], 0.0, {})
            
        # Analyze cryptogram patterns for Option B indicators
        pattern_analysis = self._analyze_cryptogram_patterns(cryptograms)
        
        if pattern_analysis['randomness_score'] < 0.3:
            patterns.append('Low randomness suggests Option B with shared components')
            correlations.append(0.6)
            
        success_probability = len(derived_keys) / len(self.card_profiles)
        correlation_strength = statistics.mean(correlations) if correlations else 0.0
        
        return KeyDerivationResult(
            derivation_method='emv_option_b',
            success_probability=success_probability,
            derived_keys=derived_keys,
            correlation_strength=correlation_strength,
            pattern_matches=patterns,
            confidence_score=success_probability * correlation_strength,
            analysis_details={
                'pattern_analysis': pattern_analysis,
                'option_b_indicators': len([p for p in patterns if 'Option B' in p])
            }
        )
        
    def _derive_common_master_key(self) -> KeyDerivationResult:
        """Attempt to derive a common master key across multiple cards."""
        patterns = []
        correlations = []
        master_key_candidates = {}
        
        # Look for patterns that suggest a common master key
        cryptogram_data = []
        for profile in self.card_profiles.values():
            if profile.application_cryptogram and profile.pan:
                cryptogram_data.append({
                    'cryptogram': profile.application_cryptogram,
                    'pan': profile.pan,
                    'atc': profile.atc or '0001',
                    'profile': profile
                })
                
        if len(cryptogram_data) < 2:
            return KeyDerivationResult('common_master_key', 0.0, {}, 0.0, [], 0.0, {})
            
        # Test common master key hypothesis
        potential_master_keys = self._generate_common_master_key_candidates()
        
        best_master_key = None
        best_success_rate = 0.0
        successful_derivations = {}
        
        for master_key in potential_master_keys:
            successful_cards = 0
            card_keys = {}
            
            for data in cryptogram_data:
                try:
                    # Derive card-specific key from master key
                    card_key = self._derive_card_key_from_master(master_key, data['pan'])
                    
                    # Test if this derived key can generate the observed cryptogram
                    if self._test_cryptogram_generation(card_key, data['profile']):
                        successful_cards += 1
                        card_keys[data['profile'].card_id] = card_key.hex()
                        
                except Exception:
                    continue
                    
            success_rate = successful_cards / len(cryptogram_data)
            
            if success_rate > best_success_rate:
                best_success_rate = success_rate
                best_master_key = master_key
                successful_derivations = card_keys
                
        if best_success_rate > 0.3:  # 30% success rate threshold
            patterns.append(f'Common master key with {best_success_rate:.1%} success rate')
            correlations.append(best_success_rate)
            
        return KeyDerivationResult(
            derivation_method='common_master_key',
            success_probability=best_success_rate,
            derived_keys={'master_key': best_master_key.hex() if best_master_key else '', 'card_keys': successful_derivations},
            correlation_strength=best_success_rate,
            pattern_matches=patterns,
            confidence_score=best_success_rate * 0.8,
            analysis_details={
                'master_key_candidates_tested': len(potential_master_keys),
                'best_success_rate': best_success_rate,
                'cards_successfully_derived': len(successful_derivations)
            }
        )
        
    def _derive_pin_based_keys(self) -> KeyDerivationResult:
        """Analyze PIN-based key derivation patterns."""
        patterns = []
        correlations = []
        pin_based_keys = {}
        
        # Only analyze cards with known PINs
        cards_with_pins = {card_id: profile for card_id, profile in self.card_profiles.items() if profile.pin}
        
        if len(cards_with_pins) < 2:
            return KeyDerivationResult('pin_based_derivation', 0.0, {}, 0.0, [], 0.0, 
                                     {'error': 'Insufficient cards with known PINs'})
                                     
        # Test various PIN-based derivation methods
        for card_id, profile in cards_with_pins.items():
            try:
                # Method 1: PIN as direct key component
                pin_key = self._derive_key_from_pin(profile.pin, profile.pan)
                
                if self._test_cryptogram_generation(pin_key, profile):
                    pin_based_keys[card_id] = {
                        'method': 'direct_pin_derivation',
                        'derived_key': pin_key.hex()
                    }
                    patterns.append('Direct PIN-based key derivation')
                    correlations.append(0.7)
                    continue
                    
            except Exception as e:
                self.logger.debug(f"PIN-based derivation failed for {card_id}: {e}")
                
        success_probability = len(pin_based_keys) / len(cards_with_pins)
        correlation_strength = statistics.mean(correlations) if correlations else 0.0
        
        return KeyDerivationResult(
            derivation_method='pin_based_derivation',
            success_probability=success_probability,
            derived_keys=pin_based_keys,
            correlation_strength=correlation_strength,
            pattern_matches=patterns,
            confidence_score=success_probability * correlation_strength,
            analysis_details={
                'cards_with_pins': len(cards_with_pins),
                'pin_patterns_found': len(set(patterns))
            }
        )
        
    def _perform_statistical_analysis(self) -> KeyDerivationResult:
        """Perform statistical analysis to detect patterns in cryptographic data."""
        patterns = []
        analysis_data = {}
        
        # Collect all cryptographic data for analysis
        crypto_data = {
            'cryptograms': [],
            'atcs': [],
            'pans': [],
            'pins': []
        }
        
        for profile in self.card_profiles.values():
            if profile.application_cryptogram:
                crypto_data['cryptograms'].append(profile.application_cryptogram)
            if profile.atc:
                crypto_data['atcs'].append(profile.atc)
            if profile.pan:
                crypto_data['pans'].append(profile.pan)
            if profile.pin:
                crypto_data['pins'].append(profile.pin)
                
        # Statistical analysis of cryptograms
        if len(crypto_data['cryptograms']) >= 2:
            cryptogram_analysis = self._analyze_cryptogram_entropy(crypto_data['cryptograms'])
            analysis_data['cryptogram_entropy'] = cryptogram_analysis
            
            if cryptogram_analysis['entropy'] < 0.5:
                patterns.append('Low cryptogram entropy detected')
                
        # Calculate overall pattern strength
        pattern_strength = len(patterns) / max(1, len(self.card_profiles))
        
        return KeyDerivationResult(
            derivation_method='statistical_analysis',
            success_probability=pattern_strength,
            derived_keys={'statistical_patterns': analysis_data},
            correlation_strength=pattern_strength,
            pattern_matches=patterns,
            confidence_score=pattern_strength * 0.6,
            analysis_details=analysis_data
        )
        
    # Helper methods for key derivation
    def _generate_master_key_candidates(self) -> List[bytes]:
        """Generate candidate master keys for testing."""
        candidates = []
        
        # Common weak master keys
        weak_keys = [
            b'\x00' * 16,  # All zeros
            b'\xFF' * 16,  # All ones
            b'\x12\x34\x56\x78\x9A\xBC\xDE\xF0' * 2,  # Pattern
            b'\x01\x23\x45\x67\x89\xAB\xCD\xEF' * 2,  # Sequential
        ]
        candidates.extend(weak_keys)
        
        # Derive candidates from known data
        for profile in self.card_profiles.values():
            if profile.pan:
                # PAN-based master key candidates
                pan_key = hashlib.sha256(profile.pan.encode()).digest()[:16]
                candidates.append(pan_key)
                
        return candidates[:20]  # Limit for performance
        
    def _generate_common_master_key_candidates(self) -> List[bytes]:
        """Generate common master key candidates."""
        candidates = []
        
        # Standard test keys
        test_keys = [
            b'\x01\x23\x45\x67\x89\xAB\xCD\xEF\x01\x23\x45\x67\x89\xAB\xCD\xEF',
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
        ]
        candidates.extend(test_keys)
        
        return candidates
        
    def _derive_3des_key(self, master_key: bytes, diversification_data: bytes) -> bytes:
        """Derive 3DES key using standard EMV method."""
        try:
            # Standard EMV key derivation using 3DES
            cipher = DES3.new(master_key, DES3.MODE_ECB)
            derived_key = cipher.encrypt(diversification_data[:8])
            
            # For 16-byte keys, derive second half
            if len(diversification_data) >= 16:
                derived_key += cipher.encrypt(diversification_data[8:16])
                
            return derived_key[:16]
        except Exception:
            # Fallback to hash-based derivation
            return hashlib.sha256(master_key + diversification_data).digest()[:16]
            
    def _derive_card_key_from_master(self, master_key: bytes, pan: str) -> bytes:
        """Derive card-specific key from master key."""
        # Standard PAN-based derivation
        pan_data = pan.ljust(16, 'F')[:16]
        return self._derive_3des_key(master_key, bytes.fromhex(pan_data))
        
    def _derive_key_from_pin(self, pin: str, pan: str) -> bytes:
        """Derive key from PIN and PAN."""
        # Simple PIN+PAN based key derivation
        combined = (pin + pan).encode()
        return hashlib.sha256(combined).digest()[:16]
        
    def _test_cryptogram_generation(self, key: bytes, profile: CardCryptoProfile) -> bool:
        """Test if a key can generate the observed application cryptogram."""
        if not profile.application_cryptogram or not profile.atc:
            return False
            
        try:
            # Simulate cryptogram generation with the test key
            transaction_data = self._build_transaction_data(profile)
            generated_cryptogram = self._generate_application_cryptogram(key, transaction_data)
            
            # Compare with observed cryptogram (first 8 bytes typically)
            observed = bytes.fromhex(profile.application_cryptogram)[:8]
            return generated_cryptogram[:8] == observed
            
        except Exception:
            return False
            
    def _build_transaction_data(self, profile: CardCryptoProfile) -> bytes:
        """Build transaction data for cryptogram generation."""
        data = bytearray()
        
        # Add ATC
        if profile.atc:
            data.extend(bytes.fromhex(profile.atc.ljust(4, '0')))
            
        # Add default amount
        data.extend(b'\x00\x00\x00\x00\x00\x01')
        
        # Add default terminal verification results
        data.extend(b'\x00\x00\x00\x00\x00')
        
        # Add unpredictable number
        if profile.unpredictable_number:
            data.extend(bytes.fromhex(profile.unpredictable_number.ljust(8, '0')))
        else:
            data.extend(b'\x12\x34\x56\x78')
            
        return bytes(data)
        
    def _generate_application_cryptogram(self, key: bytes, transaction_data: bytes) -> bytes:
        """Generate application cryptogram using EMV algorithm."""
        try:
            # Standard EMV MAC generation (simplified)
            cipher = DES3.new(key, DES3.MODE_CBC, iv=b'\x00' * 8)
            
            # Pad transaction data to multiple of 8 bytes
            padded_data = transaction_data + b'\x80'
            while len(padded_data) % 8:
                padded_data += b'\x00'
                
            # Generate MAC
            mac = cipher.encrypt(padded_data)
            
            # Return last block as cryptogram
            return mac[-8:]
            
        except Exception:
            # Fallback: simple hash-based cryptogram
            return hashlib.sha256(key + transaction_data).digest()[:8]
            
    def _analyze_cryptogram_patterns(self, cryptograms: List[bytes]) -> Dict[str, Any]:
        """Analyze patterns in cryptogram data."""
        if len(cryptograms) < 2:
            return {'randomness_score': 1.0, 'patterns': []}
            
        # Convert to hex strings for pattern analysis
        hex_cryptograms = [crypto.hex().upper() for crypto in cryptograms]
        
        # Check for repeated bytes
        byte_frequency = Counter()
        for crypto_hex in hex_cryptograms:
            for i in range(0, len(crypto_hex), 2):
                byte_frequency[crypto_hex[i:i+2]] += 1
                
        # Calculate randomness score
        total_bytes = sum(byte_frequency.values())
        expected_frequency = total_bytes / 256
        chi_square = sum((freq - expected_frequency) ** 2 / expected_frequency 
                        for freq in byte_frequency.values())
        
        # Normalize chi-square to 0-1 scale
        randomness_score = min(1.0, chi_square / (total_bytes * 2))
        
        return {
            'randomness_score': randomness_score,
            'repeated_patterns': 0,
            'patterns': []
        }
        
    def _analyze_cryptogram_entropy(self, cryptograms: List[str]) -> Dict[str, Any]:
        """Analyze entropy in cryptogram data."""
        if not cryptograms:
            return {'entropy': 0.0}
            
        # Combine all cryptogram data
        combined_data = ''.join(cryptograms)
        
        # Calculate byte entropy
        byte_counts = Counter(combined_data[i:i+2] for i in range(0, len(combined_data), 2))
        total_bytes = len(combined_data) // 2
        
        entropy = 0.0
        for count in byte_counts.values():
            probability = count / total_bytes
            if probability > 0:
                import math
                entropy -= probability * math.log2(probability)
                
        # Normalize to 0-1 scale
        max_entropy = math.log2(256)
        normalized_entropy = entropy / max_entropy
        
        return {
            'entropy': normalized_entropy,
            'total_bytes': total_bytes,
            'unique_bytes': len(byte_counts)
        }
        
class MultiCardAnalyzer(QThread):
    """
    Multi-card analysis engine for cross-card pattern detection.
    """
    
    analysis_progress = pyqtSignal(int, str)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, key_analyzer: KeyDerivationAnalyzer):
        super().__init__()
        self.key_analyzer = key_analyzer
        self.logger = logging.getLogger(__name__)
        
    def run(self):
        """Execute comprehensive multi-card analysis."""
        try:
            self.analysis_progress.emit(25, "Starting multi-card analysis...")
            
            # Key derivation attempts
            self.analysis_progress.emit(50, "Attempting key derivations...")
            derivation_results = self.key_analyzer.analyze_key_patterns()
            
            # Generate recommendations
            self.analysis_progress.emit(75, "Generating recommendations...")
            recommendations = self._generate_recommendations(derivation_results)
            
            # Compile final results
            final_results = {
                'key_derivation': derivation_results,
                'recommendations': recommendations,
                'analysis_timestamp': time.time(),
                'cards_analyzed': len(self.key_analyzer.card_profiles)
            }
            
            self.analysis_progress.emit(100, "Analysis complete!")
            self.analysis_completed.emit(final_results)
            
        except Exception as e:
            self.logger.error(f"Multi-card analysis failed: {e}")
            self.analysis_completed.emit({'error': str(e)})
            
    def _generate_recommendations(self, derivation_results) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Check for security weaknesses
        for method, result in derivation_results.get('derivation_attempts', {}).items():
            if isinstance(result, dict) and result.get('success_probability', 0) > 0.3:
                recommendations.append(f"RISK: {method} shows {result['success_probability']:.1%} success rate")
                
        return recommendations
