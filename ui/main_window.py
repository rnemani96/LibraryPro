"""
Main application window with sidebar navigation.
"""
from __future__ import annotations
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QStatusBar, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from ui.style import STYLESHEET
from ui.dashboard import DashboardScreen
from ui.issue_screen import IssueScreen
from ui.return_screen import ReturnScreen
from ui.book_search_screen import BookSearchScreen
from ui.student_lookup_screen import StudentLookupScreen
from ui.fines_screen import FinesScreen
from ui.reports_screen import ReportsScreen
from ui.import_screen import ImportScreen
from ui.settings_screen import SettingsScreen


class MainWindow(QMainWindow):
    def __init__(self, conn, current_user: dict):
        super().__init__()
        self.conn = conn
        self.current_user = current_user
        self.setWindowTitle("Library Management System")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(STYLESHEET)
        self._build_ui()
        self._switch_screen(0)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        # App title
        title_lbl = QLabel("🏛️  LibraryPro")
        title_lbl.setObjectName("appTitle")
        sb_lay.addWidget(title_lbl)

        role = self.current_user.get("role", "librarian").capitalize()
        user = self.current_user.get("full_name") or self.current_user.get("username", "")
        sub_lbl = QLabel(f"Role: {role}  |  {user}")
        sub_lbl.setObjectName("appSubtitle")
        sb_lay.addWidget(sub_lbl)

        # Divider
        div = QFrame()
        div.setStyleSheet("background-color: #1e293b; min-height: 1px; max-height: 1px; margin: 4px 14px 10px 14px;")
        sb_lay.addWidget(div)

        # Nav buttons
        nav_items = [
            ("🏠  Dashboard",        "dashboard"),
            ("📤  Issue Book",        "issue"),
            ("📥  Return / Renew",    "return"),
            ("🔍  Book Search",       "booksearch"),
            ("🎓  Student Lookup",    "studentlookup"),
            ("💰  Fines",             "fines"),
            ("📊  Reports",           "reports"),
            ("⬆  Import Data",       "import"),
            ("⚙  Settings",          "settings"),
        ]
        self._nav_buttons = []
        for label, key in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            sb_lay.addWidget(btn)
            self._nav_buttons.append((btn, key))

        sb_lay.addStretch()

        # Logout
        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setObjectName("navBtn")
        logout_btn.clicked.connect(self._logout)
        sb_lay.addWidget(logout_btn)

        main_layout.addWidget(sidebar)

        # ── Content area ───────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: #f1f5f9;")

        screens = [
            DashboardScreen(self.conn, self.current_user),
            IssueScreen(self.conn, self.current_user),
            ReturnScreen(self.conn, self.current_user),
            BookSearchScreen(self.conn, self.current_user),
            StudentLookupScreen(self.conn, self.current_user),
            FinesScreen(self.conn, self.current_user),
            ReportsScreen(self.conn, self.current_user),
            ImportScreen(self.conn, self.current_user),
            SettingsScreen(self.conn, self.current_user),
        ]
        self._screens = screens
        for screen in screens:
            # Wrap in scroll area for smaller windows
            scroll = QScrollArea()
            scroll.setWidget(screen)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            self.stack.addWidget(scroll)

        main_layout.addWidget(self.stack)

        # Connect nav buttons
        for idx, (btn, key) in enumerate(self._nav_buttons):
            btn.clicked.connect(lambda checked, i=idx: self._switch_screen(i))

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("background: #0f172a; color: #f8fafc; font-size: 12px; font-weight: 600; padding: 4px 12px; border-top: 1px solid #1e293b;")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            f"Active Session: {self.current_user.get('username', '')} ({role})  |  "
            f"LibraryPro Institutional Management System"
        )

    def _switch_screen(self, index: int):
        for i, (btn, _) in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        # Call on_show if the screen has it
        screen = self._screens[index]
        if hasattr(screen, "on_show"):
            screen.on_show()

    def _logout(self):
        reply = QMessageBox.question(
            self, "Logout", "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()
            # Restart app
            import os
            os.execv(sys.executable, [sys.executable] + sys.argv)
