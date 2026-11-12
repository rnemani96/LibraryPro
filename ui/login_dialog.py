"""
Login dialog shown at app startup.
Official institutional theme with high-contrast text and explicit credential display.
"""
from __future__ import annotations
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class LoginDialog(QDialog):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.logged_in_user = None
        self.setWindowTitle("LibraryPro — Official System Authentication")
        self.setFixedSize(460, 440)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header Banner ──────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background-color: #0f172a; border-bottom: 2px solid #1e293b;")
        header.setFixedHeight(95)
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(28, 16, 28, 16)
        h_lay.setSpacing(4)

        t1 = QLabel("🏛️  LIBRARY MANAGEMENT SYSTEM")
        t1.setFont(QFont("Segoe UI", 14, QFont.Bold))
        t1.setStyleSheet("color: #ffffff; letter-spacing: 0.5px;")

        t2 = QLabel("Official Institutional Portal — Sign In to Access")
        t2.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        h_lay.addWidget(t1)
        h_lay.addWidget(t2)
        layout.addWidget(header)

        # ── Form Area ──────────────────────────────────────────────────
        form = QFrame()
        form.setStyleSheet("background-color: #f8fafc;")
        f_lay = QVBoxLayout(form)
        f_lay.setContentsMargins(32, 20, 32, 20)
        f_lay.setSpacing(10)

        # System credentials callout card
        cred_card = QFrame()
        cred_card.setStyleSheet("""
            QFrame {
                background-color: #eff6ff;
                border: 1.5px solid #3b82f6;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        c_lay = QVBoxLayout(cred_card)
        c_lay.setContentsMargins(12, 8, 12, 8)
        c_lay.setSpacing(3)

        c_header = QLabel("🔐  DEFAULT LOGIN CREDENTIALS")
        c_header.setStyleSheet("color: #1e3a8a; font-size: 11px; font-weight: 800; letter-spacing: 0.3px;")
        
        c_body = QLabel("Username:  <b>admin</b>   |   Password:  <b>admin123</b>")
        c_body.setStyleSheet("color: #0f172a; font-size: 12px;")

        c_lay.addWidget(c_header)
        c_lay.addWidget(c_body)
        f_lay.addWidget(cred_card)

        # Username input
        u_lbl = QLabel("Username:")
        u_lbl.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 13px;")
        self.username_edit = QLineEdit()
        self.username_edit.setText("admin")  # Pre-filled for convenience
        self.username_edit.setPlaceholderText("Enter administrator or librarian username")
        self.username_edit.setFixedHeight(38)
        f_lay.addWidget(u_lbl)
        f_lay.addWidget(self.username_edit)

        # Password input
        p_lbl = QLabel("Password:")
        p_lbl.setStyleSheet("color: #0f172a; font-weight: 700; font-size: 13px;")
        self.password_edit = QLineEdit()
        self.password_edit.setText("admin123")  # Pre-filled for convenience
        self.password_edit.setPlaceholderText("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setFixedHeight(38)
        self.password_edit.returnPressed.connect(self._login)
        f_lay.addWidget(p_lbl)
        f_lay.addWidget(self.password_edit)

        # Error status
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b91c1c; font-weight: 700; font-size: 12px;")
        self.error_label.setAlignment(Qt.AlignCenter)
        f_lay.addWidget(self.error_label)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn = QPushButton("Sign In to Portal")
        btn.setObjectName("primaryBtn")
        btn.setFixedHeight(42)
        btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        btn.clicked.connect(self._login)
        btn_box.addWidget(btn)
        f_lay.addLayout(btn_box)

        layout.addWidget(form)
        self.username_edit.setFocus()
        self.username_edit.selectAll()

    def _login(self):
        from core.rules import authenticate_user
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            self.error_label.setText("⚠ Please enter both username and password.")
            return
        user = authenticate_user(self.conn, username, password)
        if user:
            self.logged_in_user = dict(user)
            self.accept()
        else:
            self.error_label.setText("❌ Invalid username or password. Check credentials above.")
            self.password_edit.clear()
            self.password_edit.setFocus()
