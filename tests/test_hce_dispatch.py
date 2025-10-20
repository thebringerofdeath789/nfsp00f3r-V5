#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for HCE dispatch and message packing in android_hce.py

These tests validate HCEProtocol.pack_message/unpack_message and the
AndroidHCERelay._handle_apdu_command flow (attack-manager substitution
and default response behavior). Tests skip gracefully if the Android HCE
module cannot be imported in the current environment.
"""

import os
import sys
import unittest
import asyncio

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import the Android HCE module; tests will be skipped if import fails
ANDROID_HCE_IMPORT_ERROR = None
try:
    from android_hce import HCEProtocol, AndroidHCERelay
    ANDROID_HCE_AVAILABLE = True
except Exception as e:
    ANDROID_HCE_AVAILABLE = False
    ANDROID_HCE_IMPORT_ERROR = e


class TestHCEProtocol(unittest.TestCase):
    def test_pack_unpack_message(self):
        """HCEProtocol should pack and unpack messages consistently."""
        # Use a small arbitrary payload
        payload = b"\x01\x02\x03\x04"
        packed = HCEProtocol.pack_message(HCEProtocol.MSG_APDU_COMMAND, payload)
        msg_type, data = HCEProtocol.unpack_message(packed)

        self.assertEqual(msg_type, HCEProtocol.MSG_APDU_COMMAND)
        self.assertEqual(data, payload)


class TestAndroidHCEDispatch(unittest.TestCase):
    def setUp(self):
        if not ANDROID_HCE_AVAILABLE:
            self.skipTest(f"android_hce module not available: {ANDROID_HCE_IMPORT_ERROR}")

    def test_handle_apdu_with_attack_response(self):
        """When the attack manager returns a replacement response, the relay should send it."""
        from unittest.mock import Mock, AsyncMock

        # Create a mock attack manager that will substitute a response
        attack_mgr = Mock()
        substituted_response = b"\x90\x00"
        attack_mgr.process_apdu = Mock(return_value=substituted_response)

        relay = AndroidHCERelay(attack_manager=attack_mgr)

        # Patch _send_apdu_response to capture what would be written over BLE
        relay._send_apdu_response = AsyncMock()

        # Use a sample SELECT APDU
        apdu = bytes.fromhex("00A4040007A0000000031010")

        # Run the async handler
        asyncio.run(relay._handle_apdu_command(apdu))

        # Verify the substituted response was sent
        relay._send_apdu_response.assert_awaited()
        called_args = relay._send_apdu_response.await_args.args
        self.assertEqual(called_args[0], substituted_response)

    def test_handle_apdu_default_response(self):
        """If no attack manager response is provided, the relay should send a default error response."""
        from unittest.mock import Mock, AsyncMock

        attack_mgr = Mock()
        attack_mgr.process_apdu = Mock(return_value=None)

        relay = AndroidHCERelay(attack_manager=attack_mgr)
        relay._send_apdu_response = AsyncMock()

        apdu = bytes.fromhex("00A4040007A0000000031010")

        asyncio.run(relay._handle_apdu_command(apdu))

        # Default response in implementation is 0x6F00
        relay._send_apdu_response.assert_awaited()
        called_args = relay._send_apdu_response.await_args.args
        self.assertEqual(called_args[0], b"\x6F\x00")


if __name__ == '__main__':
    unittest.main()
