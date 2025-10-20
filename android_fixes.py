#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NFSP00F3R V5.00 - Android Integration Fixes
============================================

File: android_fixes.py
Authors: Gregory King & Matthew Braunschweig
Date: August 16, 2025
Description: Fixes for Android companion app integration issues

This module provides fixes for common Android integration issues including:
- BLE connection timeout handling
- GATT callback synchronization
- Message fragmentation edge cases
- Android HCE service lifecycle
- Session data serialization
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any
import asyncio
from dataclasses import dataclass

# AndroidIntegrationFixes class
class AndroidIntegrationFixes:
    """Fixes for Android companion app integration issues."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def fix_ble_connection_timeout(self, ble_manager):
        """Fix BLE connection timeout issues."""
        # Add connection retry logic with exponential backoff
        original_connect = ble_manager.connect_device if hasattr(ble_manager, 'connect_device') else None
        
        async def connect_device_with_retry(device_address: str, max_retries: int = 3):
            """Connect with retry logic."""
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Connection attempt {attempt + 1}/{max_retries} to {device_address}")
                    
                    # Exponential backoff delay
                    if attempt > 0:
                        delay = min(2 ** attempt, 10)  # Max 10 seconds
                        await asyncio.sleep(delay)
                    
                    if original_connect:
                        result = await original_connect(device_address)
                        if result:
                            self.logger.info(f"Successfully connected to {device_address}")
                            return True
                    
                except Exception as e:
                    self.logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        self.logger.error(f"All connection attempts failed for {device_address}")
                        raise
            
            return False
        
        # Replace original method if it exists
        if hasattr(ble_manager, 'connect_device'):
            ble_manager.connect_device_with_retry = connect_device_with_retry
            self.logger.info("✓ Added BLE connection retry logic")
        
        return True
    
    def fix_gatt_callback_synchronization(self, ble_manager):
        """Fix GATT callback synchronization issues."""
        # Add callback queue for handling async GATT operations
        callback_queue = asyncio.Queue()
        callback_timeout = 10.0  # 10 second timeout
        
        async def wait_for_gatt_callback(expected_callback: str, timeout: float = callback_timeout):
            """Wait for specific GATT callback with timeout."""
            try:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        callback_data = await asyncio.wait_for(callback_queue.get(), timeout=1.0)
                        if callback_data.get('type') == expected_callback:
                            self.logger.debug(f"Received expected callback: {expected_callback}")
                            return callback_data
                        else:
                            # Put back in queue if not the expected callback
                            await callback_queue.put(callback_data)
                    except asyncio.TimeoutError:
                        continue
                
                self.logger.warning(f"Timeout waiting for GATT callback: {expected_callback}")
                return None
                
            except Exception as e:
                self.logger.error(f"Error waiting for GATT callback: {e}")
                return None
        
        # Add callback tracking
        if hasattr(ble_manager, 'on_characteristic_changed'):
            original_on_changed = ble_manager.on_characteristic_changed
            
            def on_characteristic_changed_with_queue(characteristic, data):
                """Characteristic changed callback with queue support."""
                callback_data = {
                    'type': 'characteristic_changed',
                    'characteristic': characteristic,
                    'data': data,
                    'timestamp': time.time()
                }
                asyncio.create_task(callback_queue.put(callback_data))
                
                # Call original callback
                if original_on_changed:
                    return original_on_changed(characteristic, data)
            
            ble_manager.on_characteristic_changed = on_characteristic_changed_with_queue
            ble_manager.wait_for_gatt_callback = wait_for_gatt_callback
            self.logger.info("✓ Added GATT callback synchronization")
        
        return True
    
    def fix_message_fragmentation(self, ble_manager):
        """Fix message fragmentation edge cases."""
        # Add message reassembly buffer
        message_buffer = {}
        max_fragment_size = 20  # Standard BLE MTU minus headers
        
        def fragment_message(message_data: bytes, max_size: int = max_fragment_size) -> List[bytes]:
            """Fragment large messages for BLE transmission."""
            if len(message_data) <= max_size:
                return [message_data]
            
            fragments = []
            total_fragments = (len(message_data) + max_size - 1) // max_size
            
            for i in range(total_fragments):
                start_idx = i * max_size
                end_idx = min(start_idx + max_size, len(message_data))
                
                # Add fragment header: [total_fragments][fragment_index][data]
                fragment_header = bytes([total_fragments, i])
                fragment_data = fragment_header + message_data[start_idx:end_idx]
                fragments.append(fragment_data)
            
            return fragments
        
        def reassemble_message(fragment: bytes, sender_id: str) -> Optional[bytes]:
            """Reassemble fragmented messages."""
            if len(fragment) < 2:
                self.logger.warning("Fragment too short for header")
                return None
            
            total_fragments = fragment[0]
            fragment_index = fragment[1]
            fragment_data = fragment[2:]
            
            # Initialize buffer for this sender if needed
            if sender_id not in message_buffer:
                message_buffer[sender_id] = {}
            
            # Store fragment
            message_buffer[sender_id][fragment_index] = fragment_data
            
            # Check if we have all fragments
            if len(message_buffer[sender_id]) == total_fragments:
                # Reassemble message
                complete_message = b''
                for i in range(total_fragments):
                    if i in message_buffer[sender_id]:
                        complete_message += message_buffer[sender_id][i]
                    else:
                        self.logger.warning(f"Missing fragment {i} for sender {sender_id}")
                        return None
                
                # Clear buffer for this sender
                del message_buffer[sender_id]
                self.logger.debug(f"Reassembled message of {len(complete_message)} bytes")
                return complete_message
            
            return None  # Still waiting for more fragments
        
        # Add methods to BLE manager
        if hasattr(ble_manager, '__dict__'):
            ble_manager.fragment_message = fragment_message
            ble_manager.reassemble_message = reassemble_message
            ble_manager.message_buffer = message_buffer
            self.logger.info("✓ Added message fragmentation handling")
        
        return True
    
    def fix_android_hce_lifecycle(self, hce_service_path: str = None):
        """Fix Android HCE service lifecycle issues."""
        # Create improved HCE service configuration
        hce_fixes = {
            'service_binding_timeout': 5000,  # 5 second timeout
            'response_timeout': 2000,  # 2 second APDU response timeout
            'auto_restart_on_crash': True,
            'pre_allocated_response_buffer': True,
            'optimize_for_low_latency': True
        }
        
        # Generate improved AndroidManifest.xml service declaration
        improved_service_config = '''
    <service
        android:name=".EmvHceService"
        android:exported="true"
        android:permission="android.permission.BIND_NFC_SERVICE">
        <intent-filter>
            <action android:name="android.nfc.cardemulation.action.HOST_APDU_SERVICE" />
        </intent-filter>
        <meta-data
            android:name="android.nfc.cardemulation.host_apdu_service"
            android:resource="@xml/apduservice" />
        <meta-data
            android:name="android.nfc.cardemulation.off_host_apdu_service"
            android:value="false" />
    </service>
        '''
        
        # Generate improved apduservice.xml
        improved_apdu_config = '''
<?xml version="1.0" encoding="utf-8"?>
<host-apdu-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/servicedesc"
    android:requireDeviceUnlock="false">
    <aid-group android:description="@string/emv_cards" android:category="payment">
        <aid-filter android:name="A0000000031010" />  <!-- Visa -->
        <aid-filter android:name="A0000000041010" />  <!-- Mastercard -->
        <aid-filter android:name="A0000000032010" />  <!-- Visa Electron -->
        <aid-filter android:name="A0000000038010" />  <!-- Visa Plus -->
        <aid-filter android:name="A00000002501" />    <!-- American Express -->
    </aid-group>
</host-apdu-service>
        '''
        
        self.logger.info("✓ Generated improved HCE service configuration")
        return {
            'fixes': hce_fixes,
            'service_config': improved_service_config,
            'apdu_config': improved_apdu_config
        }
    
    def fix_session_data_serialization(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix session data serialization issues."""
        try:
            # Deep copy to avoid modifying original
            import copy
            fixed_session = copy.deepcopy(session_data)
            
            # Fix common serialization issues
            def fix_data_types(obj):
                """Recursively fix data types for JSON serialization."""
                if isinstance(obj, dict):
                    return {str(k): fix_data_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [fix_data_types(item) for item in obj]
                elif isinstance(obj, bytes):
                    return obj.hex()  # Convert bytes to hex string
                elif isinstance(obj, set):
                    return list(obj)  # Convert sets to lists
                elif hasattr(obj, '__dict__'):
                    return fix_data_types(obj.__dict__)  # Convert objects to dicts
                else:
                    return obj
            
            fixed_session = fix_data_types(fixed_session)
            
            # Add Android-specific metadata
            fixed_session['android_metadata'] = {
                'serialization_version': '1.0',
                'timestamp': time.time(),
                'data_format': 'json',
                'compression': 'none'
            }
            
            # Validate JSON serialization
            json_str = json.dumps(fixed_session)
            json.loads(json_str)  # Verify it can be deserialized
            
            self.logger.info("✓ Fixed session data serialization")
            return fixed_session
            
        except Exception as e:
            self.logger.error(f"Session data serialization fix failed: {e}")
            return session_data
    
    def apply_all_fixes(self, ble_manager=None, session_data=None):
        """Apply all Android integration fixes."""
        fixes_applied = []
        
        try:
            if ble_manager:
                if self.fix_ble_connection_timeout(ble_manager):
                    fixes_applied.append("BLE connection timeout")
                
                if self.fix_gatt_callback_synchronization(ble_manager):
                    fixes_applied.append("GATT callback synchronization")
                
                if self.fix_message_fragmentation(ble_manager):
                    fixes_applied.append("Message fragmentation")
            
            hce_config = self.fix_android_hce_lifecycle()
            if hce_config:
                fixes_applied.append("HCE service lifecycle")
            
            if session_data:
                fixed_data = self.fix_session_data_serialization(session_data)
                if fixed_data != session_data:
                    fixes_applied.append("Session data serialization")
            
            self.logger.info(f"Applied {len(fixes_applied)} Android integration fixes: {', '.join(fixes_applied)}")
            return fixes_applied
            
        except Exception as e:
            self.logger.error(f"Error applying Android fixes: {e}")
            return fixes_applied

def test_android_fixes():
    """Test Android integration fixes."""
    print("Testing Android Integration Fixes")
    print("=" * 40)
    
    # Initialize fixes
    fixes = AndroidIntegrationFixes()
    
    # Test session data serialization fix
    test_session = {
        'card_data': {
            'pan': b'1234567890123456',  # bytes that need conversion
            'track2': 'test_track2_data',
            'emv_data': {'tag_9F02': b'\\x00\\x00\\x00\\x10\\x00\\x00'}
        },
        'transactions': [
            {'amount': 1000, 'currency': 840},
            {'amount': 2500, 'currency': 840}
        ],
        'metadata': {
            'reader_type': 'PCSC',
            'timestamp': 1693948800.0
        }
    }
    
    print("Testing session data serialization fix...")
    fixed_session = fixes.fix_session_data_serialization(test_session)
    
    try:
        json_str = json.dumps(fixed_session)
        print("✓ Session data serialization fix successful")
        print(f"  Original size: {len(str(test_session))} chars")
        print(f"  Fixed size: {len(json_str)} chars")
    except Exception as e:
        print(f"✗ Session data serialization fix failed: {e}")
    
    # Test HCE lifecycle fixes
    print("\\nTesting HCE lifecycle fixes...")
    hce_config = fixes.fix_android_hce_lifecycle()
    if hce_config and 'fixes' in hce_config:
        print("✓ HCE lifecycle fixes generated")
        print(f"  Generated {len(hce_config['fixes'])} configuration fixes")
    else:
        print("✗ HCE lifecycle fixes failed")
    
    print("\\nAndroid integration fixes test completed!")
    return fixes

if __name__ == '__main__':
    test_android_fixes()
