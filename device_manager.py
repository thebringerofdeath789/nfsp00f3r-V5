# =====================================================================
# File: device_manager.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Device and reader manager.
#   - Enumerates all available readers (PCSC, PN532, Bluetooth, etc).
#   - Handles hotplug events and device selection.
#
# Functions:
#   - DeviceManager()
#       - list_pcsc_readers()
#       - list_pn532_devices()
#       - list_bluetooth_devices()
#       - enumerate_all()
# =====================================================================

import sys

class DeviceManager:
    def __init__(self):
        pass

    def list_pcsc_readers(self):
        """
        Return list of available PCSC readers (by name).
        """
        try:
            from smartcard.System import readers
            return [str(r) for r in readers()]
        except Exception as e:
            print(f"[DeviceManager] PCSC error: {e}")
            return []

    def list_pn532_devices(self):
        """
        Return list of available PN532 readers (USB/serial) by name.
        """
        try:
            # nfcpy supports 'usb', 'tty:USB0', etc
            # For simplicity, return standard device names
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            # Filter for likely PN532-compatible serial devices
            return [p.device for p in ports if "usb" in p.device.lower() or "tty" in p.device.lower()]
        except Exception as e:
            print(f"[DeviceManager] PN532 error: {e}")
            return []

    def list_bluetooth_devices(self):
        """
        Return list of paired Bluetooth devices (name and address).
        """
        try:
            import bluetooth
            return bluetooth.discover_devices(lookup_names=True)
        except Exception as e:
            print(f"[DeviceManager] Bluetooth error: {e}")
            return []

    def enumerate_all(self):
        """
        Return a dict of all device types and available devices.
        """
        return {
            "PCSC": self.list_pcsc_readers(),
            "PN532": self.list_pn532_devices(),
            "Bluetooth": self.list_bluetooth_devices()
        }
