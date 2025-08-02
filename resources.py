# =====================================================================
# File: resources.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Resource loader utilities for icons and images.
#   Wraps resource_path from utils for PyQt QIcon/QPixmap loading.
#
# Functions:
#   - get_icon(name)
#   - get_pixmap(name)
# =====================================================================

from PyQt5.QtGui import QIcon, QPixmap
from utils import resource_path

def get_icon(name):
    """
    Load QIcon from the 'icons' subdirectory.
    """
    path = resource_path(f"icons/{name}")
    return QIcon(path)

def get_pixmap(name):
    """
    Load QPixmap from the 'images' subdirectory.
    """
    path = resource_path(f"images/{name}")
    return QPixmap(path)
