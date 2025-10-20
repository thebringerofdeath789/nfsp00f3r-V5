#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AndroidWidget UI: verify HCE/BLE controls, signal emission, and state changes.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from android_widget import AndroidWidget

app = QApplication.instance() or QApplication([])

class TestAndroidWidgetUI(unittest.TestCase):
    def setUp(self):
        self.widget = AndroidWidget()
        self.widget.show()

    def tearDown(self):
        self.widget.close()

    def test_hce_toggle_signal(self):
        """Toggling HCE emulation emits correct signals and updates button text."""
        received = {}
        def on_start(profile_id, mode):
            received['start'] = (profile_id, mode)
        def on_stop():
            received['stop'] = True
        self.widget.hce_start_requested.connect(on_start)
        self.widget.hce_stop_requested.connect(on_stop)
        # Toggle ON
        self.widget.hce_toggle_button.setChecked(True)
        QTest.mouseClick(self.widget.hce_toggle_button, Qt.LeftButton)
        self.assertIn('start', received)
        self.assertIn(self.widget.hce_source_combo.currentText(), received['start'])
        self.assertEqual(self.widget.hce_toggle_button.text(), "Stop HCE Emulation")
        # Toggle OFF
        self.widget.hce_toggle_button.setChecked(False)
        QTest.mouseClick(self.widget.hce_toggle_button, Qt.LeftButton)
        self.assertIn('stop', received)
        self.assertEqual(self.widget.hce_toggle_button.text(), "Start HCE Emulation")

    def test_apdu_log_toggle_signal(self):
        """Toggling APDU log emits signal and updates log."""
        received = {}
        def on_toggle(enabled):
            received['apdu'] = enabled
        self.widget.apdu_stream_toggle.connect(on_toggle)
        self.widget.apdu_log_toggle.setChecked(True)
        QTest.mouseClick(self.widget.apdu_log_toggle, Qt.LeftButton)
        self.assertIn('apdu', received)
        self.assertTrue(received['apdu'])
        self.widget.apdu_log_toggle.setChecked(False)
        QTest.mouseClick(self.widget.apdu_log_toggle, Qt.LeftButton)
        self.assertFalse(self.widget.apdu_log_toggle.isChecked())

    def test_ble_connect_disconnect_signals(self):
        """Connect/disconnect buttons emit BLE signals when device is selected."""
        received = {}
        self.widget.ble_connect_requested.connect(lambda addr: received.setdefault('connect', addr))
        self.widget.ble_disconnect_requested.connect(lambda addr: received.setdefault('disconnect', addr))
        # Simulate device discovery and selection
        self.widget.on_device_found('TestDevice', '00:11:22:33:44:55', -50)
        self.widget.device_list.setCurrentRow(0)
        # Connect
        QTest.mouseClick(self.widget.connect_button, Qt.LeftButton)
        self.assertIn('connect', received)
        # Disconnect
        QTest.mouseClick(self.widget.disconnect_button, Qt.LeftButton)
        self.assertIn('disconnect', received)

    def test_export_session_signal(self):
        """Export session emits export_session_requested signal."""
        received = {}
        self.widget.export_session_requested.connect(lambda session_id, device_id: received.setdefault('export', (session_id, device_id)))
        self.widget.ble_manager = MagicMock()
        self.widget.ble_manager.is_connected.return_value = True
        self.widget.current_session_data = {'session_id': 'sid123'}
        self.widget.export_session_button.setEnabled(True)
        QTest.mouseClick(self.widget.export_session_button, Qt.LeftButton)
        self.assertIn('export', received)
        self.assertEqual(received['export'][0], 'sid123')

    def test_persist_inbound_session_and_apdu(self):
        """Persist inbound SESSION_DATA and APDU_TRACE payloads to exports/ and verify files are created."""
        import os
        # Prepare a fake session payload
        session_payload = {
            'session_id': 'test-session-001',
            'timestamp': '2025-10-19T00:00:00Z',
            'card_data': {'pan': '4111111111111111'},
            'apdu_trace': []
        }

        # Call persist for SESSION_DATA
        path = self.widget.persist_received_message('SESSION_DATA', json.dumps(session_payload).encode('utf-8'))
        self.assertTrue(path and os.path.exists(path))

        # Cleanup
        try:
            os.remove(path)
        except Exception:
            pass

        # Call persist for APDU_TRACE
        apdu_payload = {
            'timestamp': '2025-10-19T00:00:01Z',
            'trace': [
                {'timestamp': '2025-10-19T00:00:01Z', 'command': '00A40400', 'response': '6F00', 'sw1': '90', 'sw2': '00'}
            ]
        }
        path2 = self.widget.persist_received_message('APDU_TRACE', json.dumps(apdu_payload).encode('utf-8'))
        self.assertTrue(path2 and os.path.exists(path2))

        # Cleanup
        try:
            os.remove(path2)
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
