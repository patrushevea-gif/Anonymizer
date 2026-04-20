"""Dark theme inspired by Tesla/SpaceX interfaces.

Readability-first: generous type sizes, higher contrast on secondary text,
no ALL-CAPS transformation except on the brand mark and primary actions,
minimal letter-spacing so Cyrillic doesn't break apart.
"""

BG_PRIMARY = "#0a0a0a"
BG_SECONDARY = "#141414"
BG_ELEVATED = "#1c1c1c"
BG_HOVER = "#262626"
BORDER = "#2e2e2e"
BORDER_FOCUS = "#444444"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c0c0c0"
TEXT_DIM = "#808080"
TEXT_DISABLED = "#4a4a4a"
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
    font-family: "Segoe UI", "SF Pro Display", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 15px;
    font-weight: 400;
}}
QLabel {{
    color: {TEXT_SECONDARY};
    background: transparent;
    font-size: 13px;
    font-weight: 500;
}}
QLabel#brand {{
    color: {TEXT_PRIMARY};
    font-size: 26px;
    font-weight: 300;
    letter-spacing: 4px;
    padding: 4px 0;
}}
QLabel#brand_accent {{
    color: {ACCENT};
    font-weight: 400;
}}
QLabel#tagline {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 1px;
}}
QLabel#net_on {{
    color: {SUCCESS};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QLabel#section {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 6px 0 4px 0;
}}
QTextEdit, QPlainTextEdit {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 12px;
    font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
    font-size: 15px;
    font-weight: 400;
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
    border: 1px solid {BORDER_FOCUS};
    border-radius: 3px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QPushButton:hover {{
    background-color: {BG_HOVER};
    border-color: {ACCENT};
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
    font-size: 14px;
    letter-spacing: 0.5px;
    padding: 11px 24px;
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
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#ghost:hover {{
    color: {ACCENT};
    background-color: transparent;
}}
QCheckBox {{
    color: {TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_FOCUS};
    border-radius: 3px;
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
    font-size: 12px;
    font-weight: 500;
    padding: 0 10px;
    min-height: 28px;
}}
QStatusBar::item {{
    border: none;
}}
QProgressBar {{
    background-color: {BG_ELEVATED};
    border: none;
    border-radius: 1px;
    max-height: 3px;
    min-height: 3px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
}}
QTableWidget {{
    background-color: {BG_SECONDARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    gridline-color: {BORDER};
    font-size: 14px;
    selection-background-color: rgba(0, 212, 255, 40);
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {BG_ELEVATED};
}}
QTableWidget::item {{
    padding: 8px 10px;
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
    padding: 10px 10px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}
QHeaderView::section:last {{
    border-right: none;
}}
QScrollBar:vertical {{
    background-color: {BG_PRIMARY};
    width: 10px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER_FOCUS};
    border-radius: 5px;
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
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER_FOCUS};
    border-radius: 5px;
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
    font-size: 14px;
    font-weight: 400;
    min-width: 320px;
}}
QDialog {{
    background-color: {BG_PRIMARY};
}}
QInputDialog QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 14px;
    font-weight: 500;
}}
QLineEdit {{
    background-color: {BG_ELEVATED};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER_FOCUS};
    border-radius: 3px;
    padding: 10px 12px;
    font-size: 14px;
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
    padding: 6px 10px;
    font-size: 12px;
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
"""


def apply_theme(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
