# =====================================================================
# File: theme.py
# Project: nfsp00f3r V4.04 - EMV Terminal & Card Manager with Companion
# Author: Gregory King
# Date: 2025-08-01
#
# Description:
#   Handles theme management for dark and light modes.
#   - Applies gray-scale backgrounds.
#   - Forces all text (WindowText/Text) to black.
#   - Sets widget-specific colors for a more consistent UI.
#
# Functions:
#   - ThemeManager(settings)
#       - apply_theme(main_window)
#       - toggle_theme()
#       - get_theme()
# =====================================================================

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class ThemeManager:
    def __init__(self, settings=None):
        self.settings = settings
        self.theme = self.settings.get("theme", "dark") if self.settings else "dark"

    def apply_theme(self, main_window):
        palette = QPalette()

        # Text always black
        text_color = QColor(0, 0, 0)
        disabled_text = QColor(120, 120, 120)
        link_color = QColor(0, 0, 255)
        visited_link_color = QColor(128, 0, 128)

        if self.theme == "dark":
            bg_window = QColor(64, 64, 64)
            bg_base   = QColor(64, 64, 64)
            bg_alt    = QColor(80, 80, 80)
        else:
            bg_window = QColor(211, 211, 211)
            bg_base   = QColor(211, 211, 211)
            bg_alt    = QColor(225, 225, 225)

        # Apply extended palette
        palette.setColor(QPalette.Window, bg_window)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, bg_base)
        palette.setColor(QPalette.AlternateBase, bg_alt)
        palette.setColor(QPalette.ToolTipBase, text_color)
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
        palette.setColor(QPalette.Button, bg_alt)
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(53, 132, 228))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, link_color)
        palette.setColor(QPalette.LinkVisited, visited_link_color)
        # Menu and selection backgrounds
        palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_text)
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)

        main_window.setPalette(palette)

        # More robust QSS: cover most widgets
        main_window.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_window.name()};
                color: #000000;
            }}
            QToolTip {{
                color: #000000;
                background-color: {bg_alt.name()};
                border: 1px solid #333333;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {bg_base.name()};
                color: #000000;
            }}
            QMenuBar, QMenu {{
                background-color: {bg_alt.name()};
                color: #000000;
            }}
            QPushButton {{
                background-color: {bg_alt.name()};
                border: 1px solid #555;
                color: #000000;
                padding: 5px;
            }}
            QComboBox, QComboBox QAbstractItemView {{
                background-color: {bg_base.name()};
                color: #000000;
            }}
            QListWidget, QTreeWidget, QTableWidget {{
                background-color: {bg_base.name()};
                color: #000000;
                alternate-background-color: {bg_alt.name()};
            }}
            QHeaderView::section {{
                background-color: {bg_alt.name()};
                color: #000000;
                border: 1px solid #aaa;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {bg_alt.name()};
            }}
        """)

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        if self.settings:
            self.settings.set("theme", self.theme)

    def get_theme(self):
        return self.theme
