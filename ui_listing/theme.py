"""Tone màu theo logo TNT Group: nâu đô + cam + nền trắng."""

MAROON = "#4A1712"       # nâu đô chữ TNT
MAROON_DARK = "#35100C"
ORANGE = "#EC8722"       # cam swoosh
ORANGE_HOVER = "#F59A3E"
ORANGE_DARK = "#D9741A"
BG = "#FAF6F3"           # nền trắng ấm
CARD = "#FFFFFF"
BORDER = "#E7DAD2"
TEXT = "#3A1712"
TEXT_MUTED = "#8A6F65"
OK = "#2E7D32"
ERR = "#C0392B"

STYLE = f"""
* {{
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#Root {{ background: {BG}; }}

QLabel#H1 {{ font-size: 20px; font-weight: 800; color: {MAROON}; }}
QLabel#H2 {{ font-size: 14px; font-weight: 700; color: {MAROON}; }}
QLabel[muted="true"] {{ color: {TEXT_MUTED}; }}

QFrame#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}

QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 9px;
    selection-background-color: {ORANGE};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ORANGE};
}}
QComboBox::drop-down {{ border: 0; width: 22px; }}

QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    color: {MAROON};
    font-weight: 600;
}}
QPushButton:hover {{ border: 1px solid {ORANGE}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; background: #F0EAE6; }}

QPushButton#Primary {{
    background: {ORANGE};
    color: white;
    border: 0;
}}
QPushButton#Primary:hover {{ background: {ORANGE_HOVER}; }}
QPushButton#Primary:disabled {{ background: #E9C7A6; color: #FFF; }}

QPushButton#Maroon {{
    background: {MAROON};
    color: white;
    border: 0;
}}
QPushButton#Maroon:hover {{ background: {MAROON_DARK}; }}

QCheckBox {{ spacing: 7px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {BORDER}; background: {CARD};
}}
QCheckBox::indicator:checked {{
    background: {ORANGE}; border: 1px solid {ORANGE};
}}

QProgressBar {{
    border: 1px solid {BORDER}; border-radius: 8px;
    background: {CARD}; text-align: center; height: 20px;
    color: {MAROON}; font-weight: 700;
}}
QProgressBar::chunk {{
    background: {ORANGE}; border-radius: 7px;
}}

QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; background: {CARD}; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_MUTED};
    padding: 8px 18px; margin-right: 4px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {MAROON}; background: {CARD}; border: 1px solid {BORDER}; border-bottom: 2px solid {ORANGE}; }}

QPlainTextEdit#Log {{
    font-family: "Consolas", monospace; font-size: 12px;
    background: #FFFDFB; color: {MAROON};
}}

QScrollArea {{ border: 0; background: transparent; }}

QFrame#Thumb {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#Thumb:hover {{ border: 1px solid {ORANGE}; }}
"""
