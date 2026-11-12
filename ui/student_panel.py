"""
Shared widget: Student Info Panel shown after scanning a Student ID or QR code.
Displays photo, personal details, currently issued books (with live fine),
return history, and outstanding fines.
High-contrast official theme with dark/black fonts.
"""
from __future__ import annotations
from pathlib import Path
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont, QColor

from core.rules import (
    get_active_loans_for_student,
    get_loan_history_for_student,
    get_unpaid_fines_for_student,
    compute_live_fine,
    get_total_unpaid_fine,
)


def _make_placeholder(size=100):
    """Generate a neutral placeholder pixmap."""
    px = QPixmap(size, size)
    px.fill(QColor("#f1f5f9"))
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
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)

        # ── Top: photo + personal details ──────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        # Photo
        self.photo_lbl = QLabel()
        self.photo_lbl.setObjectName("photoLabel")
        self.photo_lbl.setFixedSize(100, 115)
        self.photo_lbl.setAlignment(Qt.AlignCenter)
        self.photo_lbl.setScaledContents(True)
        top_row.addWidget(self.photo_lbl)

        # Personal details column
        details_col = QVBoxLayout()
        details_col.setSpacing(4)

        self.name_lbl = QLabel("—")
        self.name_lbl.setStyleSheet("color: #0f172a; font-size: 18px; font-weight: 800;")
        
        self.id_lbl = QLabel("ID: —")
        self.id_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 700;")
        
        self.course_lbl = QLabel("Course: —")
        self.course_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        
        self.year_lbl = QLabel("Year: —")
        self.year_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        
        self.phone_lbl = QLabel("Phone: —")
        self.phone_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")

        # Fine summary badge
        self.fine_lbl = QLabel("Outstanding Fine: ₹0")
        self.fine_lbl.setStyleSheet("color: #15803d; font-size: 13px; font-weight: 800;")

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
            ["Acc No", "Book Title", "Author", "Issue Date", "Due Date", "Current Fine"]
        )
        self.loans_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.loans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.loans_table.setMaximumHeight(165)

        # History tab
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Acc No", "Book Title", "Issue Date", "Return Date", "Status"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setMaximumHeight(165)

        # Fines tab
        self.fines_table = QTableWidget(0, 5)
        self.fines_table.setHorizontalHeaderLabels(
            ["Fine ID", "Book Title", "Days Late", "Amount", "Status"]
        )
        self.fines_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fines_table.setAlternatingRowColors(True)
        self.fines_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fines_table.setMaximumHeight(165)

        self.tabs.addTab(self.loans_table, "📖  Books Currently Issued")
        self.tabs.addTab(self.history_table, "📋  Loan History")
        self.tabs.addTab(self.fines_table, "💰  Fines Ledger")

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
        self.fine_lbl.setStyleSheet("color: #15803d; font-size: 13px; font-weight: 800;")
        self.photo_lbl.setPixmap(_make_placeholder(100))
        self.loans_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.fines_table.setRowCount(0)

    def load_student(self, conn, student_row):
        """Populate all fields from a student sqlite3.Row."""
        self.conn = conn
        s = dict(student_row)

        self.name_lbl.setText(s.get("name", "—"))
        self.id_lbl.setText(f"Student ID: {s.get('student_id', '—')}")
        self.course_lbl.setText(f"Course & Program: {s.get('course', '—')} | Class/Year: {s.get('year', '—')}")
        self.year_lbl.setText(f"Academic Year: {s.get('year', '—')}")
        self.phone_lbl.setText(f"Contact Phone: {s.get('phone', '—')}")

        # Photo
        photo_path = s.get("photo_path", "")
        if photo_path and Path(photo_path).exists():
            px = QPixmap(photo_path)
            self.photo_lbl.setPixmap(px.scaled(100, 115, Qt.KeepAspectRatio, Qt.SmoothTransformation))
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

            self._set_cell(self.loans_table, r, 0, loan["acc_no"], bold=True)
            self._set_cell(self.loans_table, r, 1, loan["title"])
            self._set_cell(self.loans_table, r, 2, loan["author"])
            self._set_cell(self.loans_table, r, 3, loan["issue_date"])
            
            due_item = QTableWidgetItem(loan["due_date"])
            due_item.setForeground(QColor("#b91c1c") if overdue else QColor("#15803d"))
            font = due_item.font()
            font.setBold(True)
            due_item.setFont(font)
            self.loans_table.setItem(r, 4, due_item)
            
            fine_item = QTableWidgetItem(f"₹{fine:.0f}")
            fine_item.setForeground(QColor("#b91c1c") if fine > 0 else QColor("#15803d"))
            fine_font = fine_item.font()
            fine_font.setBold(True)
            fine_item.setFont(fine_font)
            fine_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.loans_table.setItem(r, 5, fine_item)

        # Loan history
        history = get_loan_history_for_student(conn, s["student_id"])
        self.history_table.setRowCount(len(history))
        for r, loan in enumerate(history):
            self._set_cell(self.history_table, r, 0, loan["acc_no"], bold=True)
            self._set_cell(self.history_table, r, 1, loan["title"])
            self._set_cell(self.history_table, r, 2, loan["issue_date"])
            self._set_cell(self.history_table, r, 3, loan["return_date"] or "—")
            
            status_item = QTableWidgetItem(loan["status"])
            status_item.setForeground(QColor("#1d4ed8") if loan["status"] == "ACTIVE" else QColor("#0f172a"))
            status_font = status_item.font()
            status_font.setBold(True)
            status_item.setFont(status_font)
            self.history_table.setItem(r, 4, status_item)

        # Fines
        fines = get_unpaid_fines_for_student(conn, s["student_id"])
        self.fines_table.setRowCount(len(fines))
        for r, fine in enumerate(fines):
            self._set_cell(self.fines_table, r, 0, str(fine["id"]))
            self._set_cell(self.fines_table, r, 1, fine["title"])
            self._set_cell(self.fines_table, r, 2, str(fine["days_late"]))
            self._set_cell(self.fines_table, r, 3, f"₹{fine['amount']:.0f}", bold=True)
            self._set_cell(self.fines_table, r, 4, fine["status"], bold=True)

        # Outstanding fine total
        total_fine = get_total_unpaid_fine(conn, s["student_id"])
        live_total = sum(compute_live_fine(conn, l) for l in loans) if loans else 0
        display_fine = max(total_fine, live_total)
        self.fine_lbl.setText(f"Outstanding Fine: ₹{display_fine:.0f}")
        if display_fine > 0:
            self.fine_lbl.setStyleSheet("color: #b91c1c; font-size: 13px; font-weight: 800;")
        else:
            self.fine_lbl.setStyleSheet("color: #15803d; font-size: 13px; font-weight: 800;")

    def _set_cell(self, table, row, col, text, bold=False):
        item = QTableWidgetItem(str(text) if text is not None else "—")
        item.setForeground(QColor("#0f172a"))
        if bold:
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        table.setItem(row, col, item)
