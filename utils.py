# =====================================================================
# File: utils.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   General-purpose utilities: resource pathing, hex conversion, version,
#   logging, safe file ops, random generation, and cross-platform helpers.
#   - Used across the entire project for cross-platform support.
#
# Functions:
#   - resource_path(relative_path)
#   - hexify(data, sep=" ")
#   - dehexify(hexstr)
#   - app_version()
#   - safe_open(filename, mode)
#   - is_windows()
#   - is_linux()
#   - is_mac()
#   - random_bytes(length)
#   - try_int(val, default=0)
# =====================================================================

import os
import sys
import random
import string

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    """
    try:
        base_path = sys._MEIPASS  # PyInstaller temp path
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def hexify(data, sep=" "):
    """
    Convert bytes or str to uppercase hex string with optional separator.
    """
    if isinstance(data, (bytes, bytearray)):
        return sep.join(f"{b:02X}" for b in data)
    elif isinstance(data, str):
        return sep.join(f"{ord(c):02X}" for c in data)
    return ""

def dehexify(hexstr):
    """
    Convert hex string (with or without spaces/colons/dashes) to bytes.
    """
    hexstr = hexstr.replace(" ", "").replace(":", "").replace("-", "")
    try:
        return bytes.fromhex(hexstr)
    except Exception:
        return b""

def app_version():
    """
    Return the app version string. If a VERSION file is present, use it.
    """
    version = "4.04"
    version_file = resource_path("VERSION")
    if os.path.isfile(version_file):
        try:
            with open(version_file, "r", encoding="utf-8") as f:
                line = f.readline().strip()
                if line:
                    version = line
        except Exception:
            pass
    return version

def safe_open(filename, mode):
    """
    Open a file safely with robust error handling. Returns (file_object, error).
    """
    try:
        f = open(filename, mode, encoding="utf-8")
        return f, None
    except Exception as e:
        return None, e

def is_windows():
    return sys.platform.startswith("win")

def is_linux():
    return sys.platform.startswith("linux")

def is_mac():
    return sys.platform.startswith("darwin")

def random_bytes(length):
    """
    Generate cryptographically secure random bytes.
    """
    try:
        return os.urandom(length)
    except Exception:
        # Fallback
        return bytes(random.getrandbits(8) for _ in range(length))

def random_string(length, charset=string.ascii_letters + string.digits):
    """
    Generate a random string for filenames, temp data, etc.
    """
    return ''.join(random.choice(charset) for _ in range(length))

def try_int(val, default=0):
    """
    Try to convert val to int, return default if it fails.
    """
    try:
        return int(val)
    except Exception:
        return default

# You could also add a universal debug print/log helper here if not already in your logger module.
