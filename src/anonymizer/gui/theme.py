"""Theme system with dark and light variants.

Readability-first: generous type sizes, decent contrast, minimal letter-spacing
so Cyrillic doesn't break apart.

Windows native title bar:
    Qt can't style the OS-provided title bar directly, but on Win10 20H1+ the
    Desktop Window Manager exposes DWMWA_USE_IMMERSIVE_DARK_MODE which lets
    us flip the entire window chrome to dark. We call that via ctypes on each
    top-level widget right after it's shown.
"""
from __future__ import annotations

import logging
import sys

_log = logging.getLogger(__name__)


# ----------------------------------------------------------------- DARK palette
_DARK = {
    "BG_PRIMARY":    "#0a0a0a",
    "BG_SECONDARY":  "#141414",
    "BG_ELEVATED":   "#1c1c1c",
    "BG_HOVER":      "#262626",
    "BORDER":        "#2e2e2e",
    "BORDER_FOCUS":  "#444444",
    "TEXT_PRIMARY":  "#ffffff",
    "TEXT_SECONDARY":"#c0c0c0",
    "TEXT_DIM":      "#808080",
    "TEXT_DISABLED": "#4a4a4a",
    "ACCENT":        "#00d4ff",
    "ACCENT_HOVER":  "#33ddff",
    "ACCENT_PRESSED":"#00a8cc",
    "ACCENT_INK":    "#001419",
    "SUCCESS":       "#00ff88",
}

# ----------------------------------------------------------------- LIGHT palette
_LIGHT = {
    "BG_PRIMARY":    "#f5f6f8",
    "BG_SECONDARY":  "#ffffff",
    "BG_ELEVATED":   "#ffffff",
    "BG_HOVER":      "#e8ecf2",
    "BORDER":        "#d8dde4",
    "BORDER_FOCUS":  "#b4bac3",
    "TEXT_PRIMARY":  "#1a1d23",
    "TEXT_SECONDARY":"#4a4f58",
    "TEXT_DIM":      "#7e848e",
    "TEXT_DISABLED": "#c0c4cc",
    "ACCENT":        "#0088b3",
    "ACCENT_HOVER":  "#00a0d1",
    "ACCENT_PRESSED":"#006d8f",
    "ACCENT_INK":    "#ffffff",
    "SUCCESS":       "#00a866",
}


def _build_stylesheet(p: dict[str, str]) -> str:
    return f"""
* {{
    outline: none;
}}
QMainWindow, QWidget, QDialog {{
    background-color: {p["BG_PRIMARY"]};
    color: {p["TEXT_PRIMARY"]};
    font-family: "Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 15px;
    font-weight: 400;
}}
QLabel {{
    color: {p["TEXT_SECONDARY"]};
    background: transparent;
    font-size: 13px;
    font-weight: 500;
}}
QLabel#brand {{
    color: {p["TEXT_PRIMARY"]};
    font-size: 26px;
    font-weight: 300;
    letter-spacing: 4px;
    padding: 4px 0;
}}
QLabel#brand_accent {{
    color: {p["ACCENT"]};
    font-weight: 400;
}}
QLabel#net_on {{
    color: {p["SUCCESS"]};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QLabel#section {{
    color: {p["TEXT_SECONDARY"]};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 6px 0 4px 0;
}}
QLabel#author {{
    color: {p["TEXT_DIM"]};
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.5px;
}}
QLabel#group_header {{
    color: {p["ACCENT"]};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 10px 0 4px 0;
}}
QTextEdit, QPlainTextEdit {{
    background-color: {p["BG_ELEVATED"]};
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 3px;
    padding: 12px;
    font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
    font-size: 15px;
    font-weight: 400;
    selection-background-color: {p["ACCENT"]};
    selection-color: {p["ACCENT_INK"]};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {p["ACCENT"]};
}}
QTextEdit[readOnly="true"] {{
    background-color: {p["BG_SECONDARY"]};
}}
QPushButton {{
    background-color: transparent;
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER_FOCUS"]};
    border-radius: 3px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {p["BG_HOVER"]};
    border-color: {p["ACCENT"]};
    color: {p["ACCENT"]};
}}
QPushButton:pressed {{
    background-color: {p["BG_ELEVATED"]};
}}
QPushButton:disabled {{
    color: {p["TEXT_DISABLED"]};
    border-color: {p["BORDER"]};
    background-color: transparent;
}}
QPushButton#primary {{
    background-color: {p["ACCENT"]};
    color: {p["ACCENT_INK"]};
    border: 1px solid {p["ACCENT"]};
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.5px;
    padding: 11px 24px;
}}
QPushButton#primary:hover {{
    background-color: {p["ACCENT_HOVER"]};
    border-color: {p["ACCENT_HOVER"]};
    color: {p["ACCENT_INK"]};
}}
QPushButton#primary:pressed {{
    background-color: {p["ACCENT_PRESSED"]};
}}
QPushButton#primary:disabled {{
    background-color: {p["BG_ELEVATED"]};
    border-color: {p["BORDER"]};
    color: {p["TEXT_DISABLED"]};
}}
QPushButton#ghost {{
    border: none;
    color: {p["TEXT_SECONDARY"]};
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#ghost:hover {{
    color: {p["ACCENT"]};
    background-color: transparent;
}}
QPushButton#icon {{
    border: 1px solid {p["BORDER_FOCUS"]};
    border-radius: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
    font-size: 14px;
    font-weight: 700;
    color: {p["TEXT_SECONDARY"]};
}}
QPushButton#icon:hover {{
    color: {p["ACCENT"]};
    border-color: {p["ACCENT"]};
}}
QCheckBox {{
    color: {p["TEXT_SECONDARY"]};
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p["BORDER_FOCUS"]};
    border-radius: 3px;
    background-color: {p["BG_ELEVATED"]};
}}
QCheckBox::indicator:checked {{
    background-color: {p["ACCENT"]};
    border-color: {p["ACCENT"]};
    image: none;
}}
QCheckBox::indicator:hover {{
    border-color: {p["ACCENT"]};
}}
QStatusBar {{
    background-color: {p["BG_SECONDARY"]};
    color: {p["TEXT_SECONDARY"]};
    border-top: 1px solid {p["BORDER"]};
    font-size: 12px;
    font-weight: 500;
    padding: 0 10px;
    min-height: 28px;
}}
QStatusBar::item {{
    border: none;
}}
QProgressBar {{
    background-color: {p["BG_ELEVATED"]};
    border: none;
    border-radius: 1px;
    max-height: 3px;
    min-height: 3px;
}}
QProgressBar::chunk {{
    background-color: {p["ACCENT"]};
}}
QTableWidget {{
    background-color: {p["BG_SECONDARY"]};
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 3px;
    gridline-color: {p["BORDER"]};
    font-size: 14px;
    selection-background-color: rgba(0, 136, 179, 40);
    selection-color: {p["TEXT_PRIMARY"]};
    alternate-background-color: {p["BG_ELEVATED"]};
}}
QTableWidget::item {{
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {p["BORDER"]};
}}
QHeaderView::section {{
    background-color: {p["BG_PRIMARY"]};
    color: {p["TEXT_SECONDARY"]};
    border: none;
    border-right: 1px solid {p["BORDER"]};
    border-bottom: 1px solid {p["BORDER"]};
    padding: 10px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QScrollBar:vertical {{
    background-color: {p["BG_PRIMARY"]};
    width: 10px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {p["BORDER_FOCUS"]};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {p["TEXT_DIM"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
    border: none;
}}
QScrollBar:horizontal {{
    background-color: {p["BG_PRIMARY"]};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {p["BORDER_FOCUS"]};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {p["TEXT_DIM"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
    border: none;
}}
QMessageBox, QInputDialog {{
    background-color: {p["BG_SECONDARY"]};
}}
QMessageBox QLabel, QInputDialog QLabel {{
    color: {p["TEXT_PRIMARY"]};
    font-size: 14px;
    font-weight: 400;
    min-width: 320px;
}}
QDialog#settings, QDialog#help {{
    background-color: {p["BG_PRIMARY"]};
}}
QFrame#card {{
    background-color: {p["BG_SECONDARY"]};
    border: 1px solid {p["BORDER"]};
    border-radius: 4px;
}}
QLineEdit {{
    background-color: {p["BG_ELEVATED"]};
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER_FOCUS"]};
    border-radius: 3px;
    padding: 10px 12px;
    font-size: 14px;
    selection-background-color: {p["ACCENT"]};
    selection-color: {p["ACCENT_INK"]};
}}
QLineEdit:focus {{
    border-color: {p["ACCENT"]};
}}
QToolTip {{
    background-color: {p["BG_ELEVATED"]};
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER_FOCUS"]};
    padding: 6px 10px;
    font-size: 12px;
}}
QMenu {{
    background-color: {p["BG_ELEVATED"]};
    color: {p["TEXT_PRIMARY"]};
    border: 1px solid {p["BORDER"]};
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 2px;
}}
QMenu::item:selected {{
    background-color: {p["ACCENT"]};
    color: {p["ACCENT_INK"]};
}}
QFrame#divider {{
    background-color: {p["BORDER"]};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame#vdivider {{
    background-color: {p["BORDER"]};
    max-width: 1px;
    min-width: 1px;
    border: none;
}}
"""


DARK_STYLESHEET = _build_stylesheet(_DARK)
LIGHT_STYLESHEET = _build_stylesheet(_LIGHT)

# Kept as constants so other modules (e.g. highlighter) can reference them
# without re-parsing the dict. Default exposes the dark variant for back-compat.
BG_PRIMARY = _DARK["BG_PRIMARY"]
BG_SECONDARY = _DARK["BG_SECONDARY"]
BG_ELEVATED = _DARK["BG_ELEVATED"]
ACCENT = _DARK["ACCENT"]
TEXT_PRIMARY = _DARK["TEXT_PRIMARY"]
TEXT_SECONDARY = _DARK["TEXT_SECONDARY"]


def apply_theme(app, variant: str = "dark") -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(LIGHT_STYLESHEET if variant == "light" else DARK_STYLESHEET)


def apply_native_titlebar(widget, dark: bool = True) -> None:
    """Flip the Windows native title bar between dark and light.

    Uses DWMWA_USE_IMMERSIVE_DARK_MODE. On Win10 before 20H1 the attribute is 19;
    on Win10 20H1+ and Win11 it's 20. We try both so the call succeeds on either.
    No-op on non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        for attr in (20, 19):
            result = dwm.DwmSetWindowAttribute(
                wintypes.HWND(hwnd),
                wintypes.DWORD(attr),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if result == 0:
                return
    except Exception:
        _log.debug("apply_native_titlebar failed (non-fatal)", exc_info=True)
