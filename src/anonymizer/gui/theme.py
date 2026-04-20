"""Dark theme inspired by Tesla/SpaceX interfaces: near-black backgrounds,
precise typography, minimal chrome, a single electric-blue accent."""

BG_PRIMARY = "#0a0a0a"
BG_SECONDARY = "#141414"
BG_ELEVATED = "#1c1c1c"
BG_HOVER = "#252525"
BORDER = "#2a2a2a"
BORDER_FOCUS = "#3a3a3a"
TEXT_PRIMARY = "#f5f5f5"
TEXT_SECONDARY = "#8a8a8a"
TEXT_DIM = "#555555"
TEXT_DISABLED = "#3d3d3d"
ACCENT = "#00d4ff"
ACCENT_HOVER = "#33ddff"
ACCENT_PRESSED = "#00a8cc"
SUCCESS = "#00ff88"
WARNING = "#ffaa00"
DANGER = "#ff4466"

STYLESHEET = f"""
* {{
    outline: none;
}}
QMainWindow, QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}
QLabel {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
}}
QLabel#brand {{
    color: {TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 200;
    letter-spacing: 8px;
    padding: 4px 0;
}}
QLabel#brand_accent {{
    color: {ACCENT};
    font-weight: 400;
}}
QLabel#tagline {{
    color: {TEXT_DIM};
    font-size: 9px;
    font-weight: 500;
    letter-spacing: 3px;
}}
QLabel#net_on {{
    color: {SUCCESS};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel#net_off {{
    color: {SUCCESS};
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel#section {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 3px;
    padding: 4px 0 2px 0;
}}
QTextEdit, QPlainTextEdit {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 12px;
    font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: {BG_PRIMARY};
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT};
}}
QTextEdit[readOnly="true"] {{
    background-color: {BG_SECONDARY};
}}
QPushButton {{
    background-color: transparent;
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 9px 18px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {BORDER_FOCUS};
    color: {ACCENT};
}}
QPushButton:pressed {{
    background-color: {BG_ELEVATED};
}}
QPushButton:disabled {{
    color: {TEXT_DISABLED};
    border-color: {BORDER};
    background-color: transparent;
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: #001419;
    border: 1px solid {ACCENT};
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
    color: #001419;
}}
QPushButton#primary:pressed {{
    background-color: {ACCENT_PRESSED};
}}
QPushButton#primary:disabled {{
    background-color: {BG_ELEVATED};
    border-color: {BORDER};
    color: {TEXT_DISABLED};
}}
QPushButton#ghost {{
    border: none;
    color: {TEXT_SECONDARY};
    padding: 4px 10px;
    font-size: 10px;
    letter-spacing: 1px;
}}
QPushButton#ghost:hover {{
    color: {ACCENT};
    background-color: transparent;
}}
QCheckBox {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    spacing: 10px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER_FOCUS};
    border-radius: 2px;
    background-color: {BG_ELEVATED};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    image: none;
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QStatusBar {{
    background-color: {BG_SECONDARY};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 1px;
    padding: 0 8px;
    min-height: 24px;
}}
QStatusBar::item {{
    border: none;
}}
QProgressBar {{
    background-color: {BG_ELEVATED};
    border: none;
    border-radius: 1px;
    max-height: 2px;
    min-height: 2px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
}}
QTableWidget {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 2px;
    gridline-color: {BORDER};
    font-size: 12px;
    selection-background-color: rgba(0, 212, 255, 40);
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {BG_ELEVATED};
}}
QTableWidget::item {{
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QTableWidget::item:selected {{
    background-color: rgba(0, 212, 255, 50);
    color: {TEXT_PRIMARY};
}}
QHeaderView::section {{
    background-color: {BG_PRIMARY};
    color: {TEXT_SECONDARY};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
QScrollBar:vertical {{
    background-color: {BG_PRIMARY};
    width: 8px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_FOCUS};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0;
    border: none;
}}
QScrollBar:horizontal {{
    background-color: {BG_PRIMARY};
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER_FOCUS};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {TEXT_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
    width: 0;
    border: none;
}}
QMessageBox {{
    background-color: {BG_SECONDARY};
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 400;
    letter-spacing: 0.5px;
    min-width: 300px;
}}
QDialog {{
    background-color: {BG_PRIMARY};
}}
QLineEdit {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 2px;
    padding: 10px 12px;
    font-size: 13px;
    selection-background-color: {ACCENT};
    selection-color: {BG_PRIMARY};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_FOCUS};
    padding: 6px 8px;
    font-size: 11px;
}}
QFrame#divider {{
    background-color: {BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame#vdivider {{
    background-color: {BORDER};
    max-width: 1px;
    min-width: 1px;
    border: none;
}}
QFrame#card {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 2px;
}}
"""


def apply_theme(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
