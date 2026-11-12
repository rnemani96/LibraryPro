"""
Fines Management Screen: view unpaid fines, record payments, waive fines (admin).
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDoubleSpinBox, QDialog, QDialogButtonBox, QFormLayout
)
from PySide6.QtCore import Qt

from core.rules import record_fine_payment, waive_fine


class FinesScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel("Fines Management")
        title.setObjectName("sectionTitle")
        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self.refresh)
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        hdr_row.addWidget(refresh_btn)
        layout.addLayout(hdr_row)

        # Filter row
        filter_frame = QFrame()
        filter_frame.setObjectName("card")
        f_lay = QHBoxLayout(filter_frame)
        f_lay.setContentsMargins(14, 10, 14, 10)

        f_lay.addWidget(QLabel("Filter by Student ID:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Leave blank to show all unpaid fines")
        self.filter_edit.setFixedHeight(36)
        self.filter_edit.returnPressed.connect(self.refresh)
        f_lay.addWidget(self.filter_edit)

        filter_btn = QPushButton("Filter")
        filter_btn.setObjectName("primaryBtn")
        filter_btn.clicked.connect(self.refresh)
        f_lay.addWidget(filter_btn)
        layout.addWidget(filter_frame)

        # Summary
        self.summary_lbl = QLabel("")
        self.summary_lbl.setObjectName("cardTitle")
        layout.addWidget(self.summary_lbl)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Fine ID", "Student ID", "Student Name", "Book Title",
            "Days Late", "Amount", "Paid", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Action buttons
        btn_row = QHBoxLayout()
        pay_btn = QPushButton("💰  Record Payment")
        pay_btn.setObjectName("successBtn")
        pay_btn.clicked.connect(self._record_payment)

        waive_btn = QPushButton("🎁  Waive Fine (Admin)")
        waive_btn.setObjectName("warningBtn")
        waive_btn.setEnabled(self.current_user.get("role") == "admin")
        waive_btn.clicked.connect(self._waive_fine)

        btn_row.addWidget(pay_btn)
        btn_row.addWidget(waive_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.refresh()

    def refresh(self):
        student_filter = self.filter_edit.text().strip() if hasattr(self, "filter_edit") else ""

        if student_filter:
            rows = self.conn.execute("""
                SELECT f.*, s.name as student_name, b.title
                FROM fines f
                JOIN students s ON s.student_id = f.student_id
                JOIN loans l ON l.id = f.loan_id
                JOIN books b ON b.acc_no = l.acc_no
                WHERE f.student_id=? AND f.status IN ('UNPAID','PARTIAL')
                ORDER BY f.id DESC
            """, (student_filter,)).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT f.*, s.name as student_name, b.title
                FROM fines f
                JOIN students s ON s.student_id = f.student_id
                JOIN loans l ON l.id = f.loan_id
                JOIN books b ON b.acc_no = l.acc_no
                WHERE f.status IN ('UNPAID','PARTIAL')
                ORDER BY f.id DESC
            """).fetchall()

        total = sum(r["amount"] - r["paid_amount"] for r in rows)
        self.summary_lbl.setText(
            f"{len(rows)} unpaid fine(s)  |  Total outstanding: ₹{total:.0f}"
        )

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            def cell(text, align=Qt.AlignLeft):
                item = QTableWidgetItem(str(text) if text is not None else "")
                item.setTextAlignment(align | Qt.AlignVCenter)
                return item

            self.table.setItem(r, 0, cell(str(row["id"]), Qt.AlignCenter))
            self.table.setItem(r, 1, cell(row["student_id"]))
            self.table.setItem(r, 2, cell(row["student_name"]))
            self.table.setItem(r, 3, cell(row["title"]))
            self.table.setItem(r, 4, cell(str(row["days_late"]), Qt.AlignCenter))
            self.table.setItem(r, 5, cell(f"₹{row['amount']:.0f}", Qt.AlignRight))
            self.table.setItem(r, 6, cell(f"₹{row['paid_amount']:.0f}", Qt.AlignRight))
            status_item = cell(row["status"], Qt.AlignCenter)
            if row["status"] == "UNPAID":
                status_item.setForeground(Qt.red)
            elif row["status"] == "PARTIAL":
                status_item.setForeground(Qt.darkYellow)
            self.table.setItem(r, 7, status_item)

    def _get_selected_fine_id(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Select Fine", "Please select a fine row first.")
            return None
        row = rows[0].row()
        return int(self.table.item(row, 0).text())

    def _record_payment(self):
        fine_id = self._get_selected_fine_id()
        if fine_id is None:
            return

        fine = self.conn.execute("SELECT * FROM fines WHERE id=?", (fine_id,)).fetchone()
        if not fine:
            return

        outstanding = fine["amount"] - fine["paid_amount"]

        dlg = QDialog(self)
        dlg.setWindowTitle("Record Fine Payment")
        dlg.setFixedWidth(340)
        lay = QVBoxLayout(dlg)

        form = QFormLayout()
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, outstanding)
        amount_spin.setValue(outstanding)
        amount_spin.setPrefix("₹ ")
        amount_spin.setDecimals(0)
        form.addRow("Amount to collect:", amount_spin)
        form.addRow("Outstanding:", QLabel(f"₹{outstanding:.0f}"))
        lay.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() == QDialog.Accepted:
            amount = amount_spin.value()
            result = record_fine_payment(
                self.conn, fine_id, amount,
                collected_by=self.current_user.get("username", "librarian")
            )
            if result["ok"]:
                QMessageBox.information(self, "Payment Recorded",
                                        f"₹{amount:.0f} collected. Status: {result['new_status']}")
                self.refresh()
            else:
                QMessageBox.critical(self, "Error", result["error"])

    def _waive_fine(self):
        fine_id = self._get_selected_fine_id()
        if fine_id is None:
            return

        reply = QMessageBox.question(
            self, "Waive Fine",
            f"Waive fine #{fine_id}? This action is logged.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            result = waive_fine(
                self.conn, fine_id,
                waived_by=self.current_user.get("username", "admin")
            )
            if result["ok"]:
                QMessageBox.information(self, "Waived", "Fine has been waived.")
                self.refresh()
            else:
                QMessageBox.critical(self, "Error", result["error"])

    def on_show(self):
        self.refresh()
