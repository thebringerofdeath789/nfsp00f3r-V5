import unittest
from bluetooth_manager_ble import SessionExporter


class TestSessionExportSchema(unittest.TestCase):
    def test_export_session_schema(self):
        sample = {
            "fci_data": {"aid": "A0000000031010"},
            "afl_data": {"records": []},
            "pan": "4111111111111111",
            "expiry_date": "2512",
            "cardholder_name": "TEST CARD",
            "amount": 12345,
            "currency": "USD",
            "transaction_type": "purchase",
            "terminal_data": {"tid": "123456"},
            "apdu_trace": [
                {
                    "timestamp": "2025-10-18T00:00:00",
                    "command": "00A40400",
                    "response": "9000",
                    "sw1": "90",
                    "sw2": "00",
                    "description": "SELECT"
                }
            ],
            "cryptogram": "DEADBEEF",
            "unpredictable_number": "01020304",
            "application_cryptogram": "CAFEBABE",
            "issuer_data": "issuer"
        }

        exported = SessionExporter.export_session(sample)

        # Top-level keys
        self.assertIn("session_id", exported)
        self.assertIsInstance(exported["session_id"], str)
        self.assertIn("timestamp", exported)
        self.assertIsInstance(exported["timestamp"], str)
        self.assertIn("version", exported)
        self.assertEqual(exported["version"], "5.0")

        # Card & transaction sections
        self.assertIn("card_data", exported)
        self.assertIsInstance(exported["card_data"], dict)
        self.assertEqual(exported["card_data"].get("pan"), "4111111111111111")
        self.assertIn("transaction_data", exported)
        self.assertIsInstance(exported["transaction_data"], dict)

        # APDU trace
        self.assertIn("apdu_trace", exported)
        self.assertIsInstance(exported["apdu_trace"], list)
        self.assertGreaterEqual(len(exported["apdu_trace"]), 1)
        first = exported["apdu_trace"][0]
        self.assertIn("command", first)
        self.assertIn("response", first)

        # Security data
        self.assertIn("security_data", exported)
        self.assertIsInstance(exported["security_data"], dict)


if __name__ == "__main__":
    unittest.main()
