"""
Issue Screen: Scan student ID → show full student info → scan book accession → issue.
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer

from core.rules import get_student, get_book, issue_book, get_book_copies_info, search_books
from ui.student_panel import StudentInfoPanel


class IssueScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._current_student = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Issue Book")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ── Step 1: Scan Student ───────────────────────────────────────
        step1_frame = QFrame()
        step1_frame.setObjectName("card")
        s1_lay = QVBoxLayout(step1_frame)
        s1_lay.setContentsMargins(16, 12, 16, 12)
        s1_lay.setSpacing(8)

        step1_lbl = QLabel("Step 1 — Scan Student ID or QR Code")
        step1_lbl.setObjectName("cardTitle")
        s1_lay.addWidget(step1_lbl)

        scan_row = QHBoxLayout()
        self.student_scan_edit = QLineEdit()
        self.student_scan_edit.setObjectName("scanBox")
        self.student_scan_edit.setPlaceholderText("🔍  Scan student QR code or type Student ID → Enter")
        self.student_scan_edit.setFixedHeight(44)
        self.student_scan_edit.returnPressed.connect(self._load_student)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self._clear_student)

        scan_row.addWidget(self.student_scan_edit)
        scan_row.addWidget(clear_btn)
        s1_lay.addLayout(scan_row)
        layout.addWidget(step1_frame)

        # ── Student info panel (hidden until scanned) ──────────────────
        self.student_panel = StudentInfoPanel()
        self.student_panel.setVisible(False)
        layout.addWidget(self.student_panel)

        # ── Step 2: Issue Book (shown only after student loaded) ────────
        self.step2_frame = QFrame()
        self.step2_frame.setObjectName("card")
        self.step2_frame.setVisible(False)
        s2_lay = QVBoxLayout(self.step2_frame)
        s2_lay.setContentsMargins(16, 12, 16, 12)
        s2_lay.setSpacing(10)

        step2_lbl = QLabel("Step 2 — Scan or Enter Book Accession Number")
        step2_lbl.setObjectName("cardTitle")
        s2_lay.addWidget(step2_lbl)

        book_row = QHBoxLayout()
        self.book_acc_edit = QLineEdit()
        self.book_acc_edit.setObjectName("scanBox")
        self.book_acc_edit.setPlaceholderText("🔍  Scan book QR or type Accession No → Enter")
        self.book_acc_edit.setFixedHeight(44)
        self.book_acc_edit.returnPressed.connect(self._issue_book)

        issue_btn = QPushButton("✔  Issue Book")
        issue_btn.setObjectName("successBtn")
        issue_btn.setFixedHeight(44)
        issue_btn.clicked.connect(self._issue_book)
        book_row.addWidget(self.book_acc_edit)
        book_row.addWidget(issue_btn)
        s2_lay.addLayout(book_row)

        # Book preview info
        self.book_info_lbl = QLabel("")
        self.book_info_lbl.setObjectName("studentInfo")
        s2_lay.addWidget(self.book_info_lbl)

        # Copies info
        self.copies_lbl = QLabel("")
        self.copies_lbl.setObjectName("studentInfo")
        s2_lay.addWidget(self.copies_lbl)

        self.issue_status_lbl = QLabel("")
        self.issue_status_lbl.setAlignment(Qt.AlignCenter)
        s2_lay.addWidget(self.issue_status_lbl)

        layout.addWidget(self.step2_frame)
        layout.addStretch()

        self.student_scan_edit.setFocus()

    # ──────────────────────────────────────────────────────────────────
    def _load_student(self):
        raw = self.student_scan_edit.text().strip()
        if not raw:
            return

        # Support QR format: "STU|2024|0123" or plain student ID
        student_id = raw
        if "|" in raw:
            parts = raw.split("|")
            student_id = "|".join(parts[1:]) if len(parts) >= 2 else raw

        student = get_student(self.conn, student_id)
        if not student:
            # Try exact from raw
            student = get_student(self.conn, raw)

        if not student:
            QMessageBox.warning(self, "Student Not Found",
                                f"No student found with ID: {raw}")
            self.student_scan_edit.selectAll()
            return

        self._current_student = dict(student)
        self.student_panel.load_student(self.conn, student)
        self.student_panel.setVisible(True)
        self.step2_frame.setVisible(True)
        self.book_acc_edit.setFocus()
        self.book_acc_edit.clear()
        self.book_info_lbl.clear()
        self.copies_lbl.clear()
        self.issue_status_lbl.clear()

    def _clear_student(self):
        self._current_student = None
        self.student_scan_edit.clear()
        self.student_panel.clear()
        self.student_panel.setVisible(False)
        self.step2_frame.setVisible(False)
        self.student_scan_edit.setFocus()

    def _issue_book(self):
        if not self._current_student:
            return
        raw = self.book_acc_edit.text().strip()
        if not raw:
            return

        # Parse QR code format "ACC No: 123"
        acc_no = raw
        if ":" in raw:
            acc_no = raw.split(":")[-1].strip()

        # Preview book info first
        book = get_book(self.conn, acc_no)
        if not book:
            self.issue_status_lbl.setObjectName("statusError")
            self.issue_status_lbl.setText(f"❌  Book '{acc_no}' not found in database.")
            self.issue_status_lbl.setStyleSheet("color: #dc3545; font-weight: bold;")
            return

        # Show book info and copies
        self.book_info_lbl.setText(
            f"📖  {book['title']}  |  {book['author']}  |  Status: {book['status']}"
        )
        copies = get_book_copies_info(self.conn, book["title"])
        self.copies_lbl.setText(
            f"Copies of this title:  Total: {copies['total']}  |  "
            f"✅ Available: {copies['available']}  |  "
            f"📤 Issued: {copies['issued']}"
        )

        result = issue_book(
            self.conn,
            self._current_student["student_id"],
            acc_no,
            issued_by=self.current_user.get("username", "librarian")
        )

        if result["ok"]:
            self.issue_status_lbl.setText(
                f"✅  Book issued successfully!  Due Date: {result['due_date']}"
            )
            self.issue_status_lbl.setStyleSheet("color: #198754; font-weight: bold;")
            self.book_acc_edit.clear()
            self.book_acc_edit.setFocus()
            # Refresh student panel
            st = get_student(self.conn, self._current_student["student_id"])
            if st:
                self.student_panel.load_student(self.conn, st)
        else:
            self.issue_status_lbl.setText(f"❌  {result['error']}")
            self.issue_status_lbl.setStyleSheet("color: #dc3545; font-weight: bold;")

    def on_show(self):
        """Called when this screen becomes active."""
        self._clear_student()
        self.student_scan_edit.setFocus()
