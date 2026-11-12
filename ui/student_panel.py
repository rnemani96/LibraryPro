"""
Shared widget: Student Info Panel shown after scanning a Student ID or QR code.
Displays photo, personal details, currently issued books (with live fine),
return history, and outstanding fines.
"""
from __future__ import annotations
from pathlib import Path
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont

from core.rules import (
    get_active_loans_for_student,
    get_loan_history_for_student,
    get_unpaid_fines_for_student,
    compute_live_fine,
    get_total_unpaid_fine,
)


PLACEHOLDER_PHOTO = None   # Will be generated on first use


def _make_placeholder(size=100):
    """Generate a grey placeholder pixmap."""
    px = QPixmap(size, size)
    px.fill(Qt.lightGray)
    return px


class StudentInfoPanel(QFrame):
    """
    Self-contained panel showing all info for a student.
    Call load_student(conn, student_row) to populate it.
    Call clear() to reset.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("studentPanel")
        self.conn = None
        self._build_ui()
        self.clear()

    # ──────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        # ── Top: photo + personal details ──────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Photo
        self.photo_lbl = QLabel()
        self.photo_lbl.setObjectName("photoLabel")
        self.photo_lbl.setFixedSize(100, 110)
        self.photo_lbl.setAlignment(Qt.AlignCenter)
        self.photo_lbl.setScaledContents(True)
        top_row.addWidget(self.photo_lbl)

        # Personal details column
        details_col = QVBoxLayout()
        details_col.setSpacing(3)

        self.name_lbl   = QLabel("—")
        self.name_lbl.setObjectName("studentName")
        self.id_lbl     = QLabel("ID: —")
        self.id_lbl.setObjectName("studentInfo")
        self.course_lbl = QLabel("Course: —")
        self.course_lbl.setObjectName("studentInfo")
        self.year_lbl   = QLabel("Year: —")
        self.year_lbl.setObjectName("studentInfo")
        self.phone_lbl  = QLabel("Phone: —")
        self.phone_lbl.setObjectName("studentInfo")

        # Fine summary
        self.fine_lbl = QLabel("Outstanding Fine: ₹0")
        self.fine_lbl.setObjectName("studentInfo")
        self.fine_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))

        details_col.addWidget(self.name_lbl)
        details_col.addWidget(self.id_lbl)
        details_col.addWidget(self.course_lbl)
        details_col.addWidget(self.year_lbl)
        details_col.addWidget(self.phone_lbl)
        details_col.addStretch()
        details_col.addWidget(self.fine_lbl)

        top_row.addLayout(details_col)
        top_row.addStretch()
        outer.addLayout(top_row)

        # ── Tabs: Current Loans / History / Fines ──────────────────────
        self.tabs = QTabWidget()

        # Current loans tab
        self.loans_table = QTableWidget(0, 6)
        self.loans_table.setHorizontalHeaderLabels(
            ["Acc No", "Title", "Author", "Issue Date", "Due Date", "Live Fine"]
        )
        self.loans_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.loans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.loans_table.setMaximumHeight(160)

        # History tab
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Acc No", "Title", "Issue Date", "Return Date", "Status"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setMaximumHeight(160)

        # Fines tab
        self.fines_table = QTableWidget(0, 5)
        self.fines_table.setHorizontalHeaderLabels(
            ["Fine ID", "Title", "Days Late", "Amount", "Status"]
        )
        self.fines_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fines_table.setAlternatingRowColors(True)
        self.fines_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fines_table.setMaximumHeight(160)

        self.tabs.addTab(self.loans_table, "📖  Books Currently Issued")
        self.tabs.addTab(self.history_table, "📋  Loan History")
        self.tabs.addTab(self.fines_table, "💰  Fines")

        outer.addWidget(self.tabs)

    # ──────────────────────────────────────────────────────────────────
    # Public methods
    # ──────────────────────────────────────────────────────────────────
    def clear(self):
        self.name_lbl.setText("—")
        self.id_lbl.setText("ID: —")
        self.course_lbl.setText("Course: —")
        self.year_lbl.setText("Year: —")
        self.phone_lbl.setText("Phone: —")
        self.fine_lbl.setText("Outstanding Fine: ₹0")
        self.fine_lbl.setStyleSheet("color: #198754; font-weight: bold;")
        self.photo_lbl.setPixmap(_make_placeholder(100))
        self.loans_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.fines_table.setRowCount(0)

    def load_student(self, conn, student_row):
        """Populate all fields from a student sqlite3.Row."""
        self.conn = conn
        s = dict(student_row)

        self.name_lbl.setText(s.get("name", "—"))
        self.id_lbl.setText(f"ID: {s.get('student_id', '—')}")
        self.course_lbl.setText(f"Course: {s.get('course', '—')} | {s.get('year', '—')}")
        self.year_lbl.setText(f"Year: {s.get('year', '—')}")
        self.phone_lbl.setText(f"Phone: {s.get('phone', '—')}")

        # Photo
        photo_path = s.get("photo_path", "")
        if photo_path and Path(photo_path).exists():
            px = QPixmap(photo_path)
            self.photo_lbl.setPixmap(px.scaled(100, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.photo_lbl.setPixmap(_make_placeholder(100))

        # Active loans
        loans = get_active_loans_for_student(conn, s["student_id"])
        self.loans_table.setRowCount(len(loans))
        today = date.today()
        for r, loan in enumerate(loans):
            due = date.fromisoformat(loan["due_date"])
            fine = compute_live_fine(conn, loan)
            overdue = today > due

            self._set_cell(self.loans_table, r, 0, loan["acc_no"])
            self._set_cell(self.loans_table, r, 1, loan["title"])
            self._set_cell(self.loans_table, r, 2, loan["author"])
            self._set_cell(self.loans_table, r, 3, loan["issue_date"])
            due_item = QTableWidgetItem(loan["due_date"])
            due_item.setForeground(Qt.red if overdue else Qt.darkGreen)
            self.loans_table.setItem(r, 4, due_item)
            fine_item = QTableWidgetItem(f"₹{fine:.0f}")
            fine_item.setForeground(Qt.red if fine > 0 else Qt.darkGreen)
            self.loans_table.setItem(r, 5, fine_item)

        # Loan history
        history = get_loan_history_for_student(conn, s["student_id"])
        self.history_table.setRowCount(len(history))
        for r, loan in enumerate(history):
            self._set_cell(self.history_table, r, 0, loan["acc_no"])
            self._set_cell(self.history_table, r, 1, loan["title"])
            self._set_cell(self.history_table, r, 2, loan["issue_date"])
            self._set_cell(self.history_table, r, 3, loan["return_date"] or "—")
            status_item = QTableWidgetItem(loan["status"])
            if loan["status"] == "ACTIVE":
                status_item.setForeground(Qt.blue)
            self.history_table.setItem(r, 4, status_item)

        # Fines
        fines = get_unpaid_fines_for_student(conn, s["student_id"])
        self.fines_table.setRowCount(len(fines))
        for r, fine in enumerate(fines):
            self._set_cell(self.fines_table, r, 0, str(fine["id"]))
            self._set_cell(self.fines_table, r, 1, fine["title"])
            self._set_cell(self.fines_table, r, 2, str(fine["days_late"]))
            self._set_cell(self.fines_table, r, 3, f"₹{fine['amount']:.0f}")
            self._set_cell(self.fines_table, r, 4, fine["status"])

        # Outstanding fine total
        total_fine = get_total_unpaid_fine(conn, s["student_id"])
        # Also add live fine from active loans
        live_total = sum(compute_live_fine(conn, l) for l in loans) if loans else 0
        display_fine = max(total_fine, live_total)
        self.fine_lbl.setText(f"Outstanding Fine: ₹{display_fine:.0f}")
        if display_fine > 0:
            self.fine_lbl.setStyleSheet("color: #dc3545; font-weight: bold;")
        else:
            self.fine_lbl.setStyleSheet("color: #198754; font-weight: bold;")

    def _set_cell(self, table, row, col, text):
        item = QTableWidgetItem(str(text) if text is not None else "—")
        table.setItem(row, col, item)
