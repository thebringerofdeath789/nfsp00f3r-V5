# =====================================================================
# File: magstripe_writer.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Logic to write magstripe data to an MSR device (e.g., msrx86BT).
#   Exports and writes tracks to compatible hardware.
#
# Functions:
#   - MagstripeWriter()
#       - write_tracks_to_msr(track_data, device_name)
# =====================================================================

import serial
import time

class MagstripeWriter:
    def __init__(self):
        pass

    def write_tracks_to_msr(self, track_data, device_name):
        try:
            ser = serial.Serial(device_name, baudrate=115200, timeout=2)
            for track, value in track_data.items():
                frame = b"\x02" + value.encode() + b"\x03"
                ser.write(frame)
                time.sleep(0.5)
            ser.close()
            return True
        except Exception as e:
            print(f"[MSR Write] Error: {e}")
            return False
