"""
Return Screen: scan book accession → show book info + who has it + fine → confirm return.
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QDialog, QDialogButtonBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt

from core.rules import (
    get_book, return_book, get_student, record_fine_payment,
    compute_live_fine, renew_book, get_active_loans_for_student
)
from ui.student_panel import StudentInfoPanel
from datetime import date


class ReturnScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._pending_return = None   # dict with book/loan info before confirm
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Return / Renew Book")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Scan box
        scan_frame = QFrame()
        scan_frame.setObjectName("card")
        s_lay = QVBoxLayout(scan_frame)
        s_lay.setContentsMargins(16, 12, 16, 12)
        s_lay.setSpacing(8)

        s_lay.addWidget(QLabel("Scan or enter Accession Number of book to return:"))

        scan_row = QHBoxLayout()
        self.acc_edit = QLineEdit()
        self.acc_edit.setObjectName("scanBox")
        self.acc_edit.setPlaceholderText("🔍  Scan book QR or type Accession No → Enter")
        self.acc_edit.setFixedHeight(44)
        self.acc_edit.returnPressed.connect(self._lookup_book)

        lookup_btn = QPushButton("Look Up")
        lookup_btn.setObjectName("primaryBtn")
        lookup_btn.setFixedHeight(44)
        lookup_btn.clicked.connect(self._lookup_book)
        scan_row.addWidget(self.acc_edit)
        scan_row.addWidget(lookup_btn)
        s_lay.addLayout(scan_row)
        layout.addWidget(scan_frame)

        # Result panel (hidden until scanned)
        self.result_frame = QFrame()
        self.result_frame.setObjectName("card")
        self.result_frame.setVisible(False)
        r_lay = QVBoxLayout(self.result_frame)
        r_lay.setContentsMargins(16, 14, 16, 14)
        r_lay.setSpacing(8)

        # Book details
        self.book_title_lbl = QLabel("")
        self.book_title_lbl.setObjectName("studentName")
        self.book_detail_lbl = QLabel("")
        self.book_detail_lbl.setObjectName("studentInfo")

        # Borrower
        self.borrower_lbl = QLabel("")
        self.borrower_lbl.setObjectName("studentInfo")

        # Fine info
        self.fine_lbl = QLabel("")
        self.fine_lbl.setFont(__import__("PySide6.QtGui", fromlist=["QFont"]).QFont("Segoe UI", 13, __import__("PySide6.QtGui", fromlist=["QFont"]).QFont.Bold))

        # Action buttons
        btn_row = QHBoxLayout()
        self.return_btn = QPushButton("✔  Confirm Return")
        self.return_btn.setObjectName("successBtn")
        self.return_btn.setFixedHeight(42)
        self.return_btn.clicked.connect(self._confirm_return)

        self.renew_btn = QPushButton("🔄  Renew (+15 days)")
        self.renew_btn.setObjectName("primaryBtn")
        self.renew_btn.setFixedHeight(42)
        self.renew_btn.clicked.connect(self._confirm_renew)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self._clear)

        btn_row.addWidget(self.return_btn)
        btn_row.addWidget(self.renew_btn)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)

        r_lay.addWidget(self.book_title_lbl)
        r_lay.addWidget(self.book_detail_lbl)
        r_lay.addWidget(self.borrower_lbl)
        r_lay.addWidget(self.fine_lbl)
        r_lay.addLayout(btn_row)
        r_lay.addWidget(self.status_lbl)
        layout.addWidget(self.result_frame)

        # Student panel (shows borrower details)
        self.student_panel = StudentInfoPanel()
        self.student_panel.setVisible(False)
        layout.addWidget(self.student_panel)
        layout.addStretch()

        self.acc_edit.setFocus()

    # ──────────────────────────────────────────────────────────────────
    def _lookup_book(self):
        raw = self.acc_edit.text().strip()
        if not raw:
            return

        # Parse QR
        acc_no = raw
        if ":" in raw:
            acc_no = raw.split(":")[-1].strip()

        book = get_book(self.conn, acc_no)
        if not book:
            QMessageBox.warning(self, "Not Found", f"No book found with accession: {acc_no}")
            return

        if book["status"] == "AVAILABLE":
            QMessageBox.information(self, "Not Issued",
                                    f"Book '{acc_no}' is currently AVAILABLE — not issued to anyone.")
            return

        # Find the active loan
        loan = self.conn.execute("""
            SELECT l.*, s.name as student_name, s.course, s.year, s.phone
            FROM loans l
            JOIN students s ON s.student_id = l.student_id
            WHERE l.acc_no=? AND l.status='ACTIVE'
            ORDER BY l.id DESC LIMIT 1
        """, (acc_no,)).fetchone()

        if not loan:
            QMessageBox.warning(self, "No Active Loan",
                                f"Book is marked ISSUED but no active loan found.")
            return

        self._pending_return = dict(loan)
        self._pending_return["acc_no"] = acc_no
        self._pending_return["book"] = dict(book)

        # Compute fine
        today = date.today()
        due = date.fromisoformat(loan["due_date"])
        days_late = (today - due).days if today > due else 0

        fine = compute_live_fine(self.conn, loan)

        # Populate result panel
        self.book_title_lbl.setText(f"📖  {book['title']}")
        self.book_title_lbl.setStyleSheet("color: #0f172a; font-size: 17px; font-weight: 800;")
        self.book_detail_lbl.setText(
            f"Acc No: {acc_no}  |  Author: {book['author']}  |  "
            f"Issued: {loan['issue_date']}  |  Due: {loan['due_date']}"
        )
        self.book_detail_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 600;")
        self.borrower_lbl.setText(
            f"Borrower: {loan['student_name']} (ID: {loan['student_id']})  |  "
            f"Renewals Done: {loan['renewals_count']}"
        )
        self.borrower_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: 700;")

        if fine > 0:
            self.fine_lbl.setText(f"⚠  Overdue by {days_late} working day(s)  |  Fine: ₹{fine:.0f}")
            self.fine_lbl.setStyleSheet("color: #b91c1c; font-size: 14px; font-weight: 800;")
        else:
            self.fine_lbl.setText("✅  No fine — book returned on time.")
            self.fine_lbl.setStyleSheet("color: #15803d; font-size: 14px; font-weight: 800;")

        self.result_frame.setVisible(True)
        self.status_lbl.clear()

        # Show student panel
        st = get_student(self.conn, loan["student_id"])
        if st:
            self.student_panel.load_student(self.conn, st)
            self.student_panel.setVisible(True)

    def _confirm_return(self):
        if not self._pending_return:
            return

        acc_no = self._pending_return["acc_no"]
        fine_before = compute_live_fine(self.conn, self.conn.execute(
            "SELECT * FROM loans WHERE acc_no=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1",
            (acc_no,)
        ).fetchone())

        result = return_book(
            self.conn, acc_no,
            returned_by=self.current_user.get("username", "librarian")
        )
        if result["ok"]:
            msg = f"✅  Book returned successfully."
            if result["fine_amount"] > 0:
                msg += f"\n\nFine charged: ₹{result['fine_amount']:.0f}  ({result['days_late']} working day(s) late)"
                # Prompt to collect fine
                reply = QMessageBox.question(
                    self, "Collect Fine",
                    f"Fine of ₹{result['fine_amount']:.0f} is due.\nCollect payment now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes and result["fine_id"]:
                    record_fine_payment(
                        self.conn, result["fine_id"], result["fine_amount"],
                        collected_by=self.current_user.get("username", "librarian")
                    )
                    msg += "\n💰  Fine collected."

            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #198754; font-weight: bold;")
            self._clear()
        else:
            self.status_lbl.setText(f"❌  {result['error']}")
            self.status_lbl.setStyleSheet("color: #dc3545; font-weight: bold;")

    def _confirm_renew(self):
        if not self._pending_return:
            return
        acc_no = self._pending_return["acc_no"]
        result = renew_book(
            self.conn, acc_no,
            renewed_by=self.current_user.get("username", "librarian")
        )
        if not result["ok"] and result.get("requires_fine"):
            fine_due = result["fine_amount"]
            days = result["days_late"]
            reply = QMessageBox.question(
                self, "Collect Overdue Fine for Renewal",
                f"This book is overdue by {days} working day(s).\n\n"
                f"Outstanding Overdue Fine: ₹{fine_due:.0f}\n\n"
                f"Collect ₹{fine_due:.0f} now and renew book for +15 days?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                result = renew_book(
                    self.conn, acc_no,
                    renewed_by=self.current_user.get("username", "librarian"),
                    fine_collected=True
                )
            else:
                self.status_lbl.setText("❌ Renewal cancelled — overdue fine was not paid.")
                self.status_lbl.setStyleSheet("color: #b91c1c; font-weight: bold;")
                return

        if result["ok"]:
            msg = f"✅  Book renewed!  New due date: {result['new_due_date']}  (Renewal #{result['renewals_count']})"
            if result.get("fine_paid", 0) > 0:
                msg += f"\n💰 Overdue fine of ₹{result['fine_paid']:.0f} collected and marked PAID."
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #15803d; font-weight: bold;")
            self._clear()
        else:
            self.status_lbl.setText(f"❌  {result['error']}")
            self.status_lbl.setStyleSheet("color: #b91c1c; font-weight: bold;")

    def _clear(self):
        self._pending_return = None
        self.acc_edit.clear()
        self.result_frame.setVisible(False)
        self.student_panel.clear()
        self.student_panel.setVisible(False)
        self.acc_edit.setFocus()

    def on_show(self):
        self._clear()
        self.acc_edit.setFocus()
