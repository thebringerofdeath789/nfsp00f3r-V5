#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for BLE fragmentation and reassembly in bluetooth_manager_ble.py

These tests are designed to run without real BLE hardware by exercising
serialization, fragmentation, send logic (with a mocked client), and
notification-based reassembly.
"""

import os
import sys
import unittest
import asyncio
import random

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bluetooth_manager_ble import BLESession, BLEMessage, BLEMessageType


class DummyClient:
    def __init__(self):
        self.writes = []
        self.is_connected = True

    async def write_gatt_char(self, characteristic, data):
        # Record writes for inspection
        self.writes.append((characteristic, bytes(data)))


class TestBLEFragmentation(unittest.TestCase):
    """Test BLE fragmentation helpers and reassembly logic."""

    def test_reassembly_out_of_order(self):
        """Fragments arriving out of order should be reassembled into original payload."""
        session = BLESession()

        captured = {}

        # Replace the real handler with a capture function so we can inspect the
        # reconstructed payload and message type.
        def capture(msg_type, payload):
            captured['msg_type'] = msg_type
            captured['payload'] = payload

        session._handle_complete_message = capture

        # Create a payload larger than typical MTU so we force fragmentation
        payload = bytes([x % 256 for x in range(123)])  # 123 bytes -> multiple fragments
        max_mtu = 20
        total_fragments = (len(payload) + max_mtu - 1) // max_mtu
        sequence_id = 99

        # Build fragments using same wire format as BLEMessage.to_bytes()
        fragments = []
        for idx in range(total_fragments):
            start = idx * max_mtu
            end = min((idx + 1) * max_mtu, len(payload))
            fragment_payload = payload[start:end]
            msg = BLEMessage(
                message_type=BLEMessageType.SESSION_DATA,
                sequence_id=sequence_id,
                total_fragments=total_fragments,
                fragment_index=idx,
                payload=fragment_payload
            )
            fragments.append(msg.to_bytes())

        # Shuffle fragments to simulate out-of-order arrival
        random.shuffle(fragments)

        # Feed fragments into the notification handler as if they arrived via GATT
        for frag in fragments:
            session._notification_handler(None, bytearray(frag))

        # Ensure capture was called and payload reassembled correctly
        self.assertIn('payload', captured)
        self.assertEqual(captured['payload'], payload)
        self.assertEqual(captured['msg_type'], BLEMessageType.SESSION_DATA)

    def test_send_fragmented_message_writes(self):
        """The send routine should call write_gatt_char once per fragment and the
        concatenation of fragment payloads should match the original payload."""
        session = BLESession()

        # Patch the client with a dummy that captures writes
        dummy = DummyClient()
        session.client = dummy
        session.rx_characteristic = 'rx-char-placeholder'

        original_seq = session.sequence_counter
        payload = b"helloworld" * 15  # 150 bytes -> multiple fragments

        # Run the async send routine
        asyncio.run(session._send_fragmented_message(BLEMessageType.SESSION_DATA, payload))

        # Calculate expected fragments (matches implementation: max_mtu=20)
        max_mtu = 20
        expected_fragments = (len(payload) + max_mtu - 1) // max_mtu

        # Verify writes recorded
        self.assertEqual(len(dummy.writes), expected_fragments)

        # Reconstruct payload from recorded fragments
        reconstructed_parts = []
        for char, wire in dummy.writes:
            msg = BLEMessage.from_bytes(wire)
            reconstructed_parts.append(msg.payload)

        reconstructed_payload = b''.join(reconstructed_parts)
        self.assertEqual(reconstructed_payload, payload)

        # Verify the sequence counter was incremented by one
        self.assertEqual(session.sequence_counter, original_seq + 1)


if __name__ == '__main__':
    unittest.main()
