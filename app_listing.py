"""TNT Listing Image — app PySide6 (entry point).

Chạy:  python app_listing.py
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from tnt_license import check_license
from ui_listing.theme import STYLE
from ui_listing.window import MainWindow
from config import migrate_old_profiles


def main():
    # BẢO MẬT LICENSE — kiểm trước MỌI thứ khác. Sai/thiếu license → thoát ngay.
    check_license("TNT_Listing")
    # Chuyển profile cũ (cạnh app) sang ổ C 1 lần → update app vẫn giữ login.
    migrate_old_profiles()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("TNT Listing Image")
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    # căn GIỮA màn hình
    try:
        scr = app.primaryScreen().availableGeometry()
        fg = win.frameGeometry()
        fg.moveCenter(scr.center())
        win.move(fg.topLeft())
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
