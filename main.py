"""
Library Management System — Entry point.

Usage:
    python main.py

Requires: Python 3.11+, PySide6, openpyxl, reportlab, Pillow
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# ── Add project root to path ───────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from db.schema import init_db, DB_PATH
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.style import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LibraryPro")
    app.setOrganizationName("Library")
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))

    # High-DPI support
    try:
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass

    # Init database
    conn = init_db(DB_PATH)

    # Login loop
    while True:
        login = LoginDialog(conn)
        if login.exec() != LoginDialog.Accepted:
            # User closed dialog without logging in
            sys.exit(0)

        user = login.logged_in_user
        if user:
            window = MainWindow(conn, user)
            window.show()
            ret = app.exec()

            # If we get back here from exec(), check if logout requested
            if ret == 0:
                # Normal close — if no restart needed, exit
                break
            # Otherwise loop back to login

    sys.exit(0)


if __name__ == "__main__":
    main()
