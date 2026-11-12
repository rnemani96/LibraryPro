"""
Login dialog shown at app startup.
"""
from __future__ import annotations
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeyEvent


class LoginDialog(QDialog):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.logged_in_user = None
        self.setWindowTitle("Library Management System — Login")
        self.setFixedSize(420, 340)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header banner
        header = QFrame()
        header.setStyleSheet("background-color: #1a2744;")
        header.setFixedHeight(90)
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(24, 16, 24, 16)
        t1 = QLabel("📚  Library Management System")
        t1.setFont(QFont("Segoe UI", 15, QFont.Bold))
        t1.setStyleSheet("color: white;")
        t2 = QLabel("Please sign in to continue")
        t2.setStyleSheet("color: #8ca0bb; font-size: 11px;")
        h_lay.addWidget(t1)
        h_lay.addWidget(t2)
        layout.addWidget(header)

        # Form area
        form = QFrame()
        form.setStyleSheet("background: #f0f4f8;")
        f_lay = QVBoxLayout(form)
        f_lay.setContentsMargins(32, 24, 32, 24)
        f_lay.setSpacing(14)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Username")
        self.username_edit.setFixedHeight(40)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFixedHeight(40)
        self.password_edit.returnPressed.connect(self._login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("statusError")
        self.error_label.setAlignment(Qt.AlignCenter)

        btn = QPushButton("Sign In")
        btn.setObjectName("primaryBtn")
        btn.setFixedHeight(40)
        btn.clicked.connect(self._login)

        f_lay.addWidget(QLabel("Username:"))
        f_lay.addWidget(self.username_edit)
        f_lay.addWidget(QLabel("Password:"))
        f_lay.addWidget(self.password_edit)
        f_lay.addWidget(self.error_label)
        f_lay.addWidget(btn)

        hint = QLabel("Default: admin / admin123")
        hint.setStyleSheet("color: #94a3b8; font-size: 10px;")
        hint.setAlignment(Qt.AlignCenter)
        f_lay.addWidget(hint)

        layout.addWidget(form)
        self.username_edit.setFocus()

    def _login(self):
        from core.rules import authenticate_user
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            self.error_label.setText("Please enter username and password.")
            return
        user = authenticate_user(self.conn, username, password)
        if user:
            self.logged_in_user = dict(user)
            self.accept()
        else:
            self.error_label.setText("❌  Invalid username or password.")
            self.password_edit.clear()
            self.password_edit.setFocus()
