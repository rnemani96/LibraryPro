"""
Reports Screen: overdue list, issue history export, most borrowed books.
"""
from __future__ import annotations
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QTabWidget, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from core.rules import get_overdue_loans, compute_live_fine


class ReportsScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("Reports")
        title.setObjectName("sectionTitle")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        tabs = QTabWidget()
        tabs.addTab(self._make_overdue_tab(), "🔴  Overdue Books")
        tabs.addTab(self._make_history_tab(), "📋  Issue History")
        tabs.addTab(self._make_most_borrowed_tab(), "🏆  Most Borrowed")
        layout.addWidget(tabs)

    # ── Overdue tab ────────────────────────────────────────────────────
    def _make_overdue_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setObjectName("secondaryBtn")
        export_btn  = QPushButton("📥  Export to Excel")
        export_btn.setObjectName("primaryBtn")
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        btn_row.addWidget(export_btn)
        lay.addLayout(btn_row)

        self.overdue_summary = QLabel("")
        lay.addWidget(self.overdue_summary)

        self.overdue_table = QTableWidget(0, 7)
        self.overdue_table.setHorizontalHeaderLabels([
            "Student ID", "Name", "Course", "Acc No", "Title", "Due Date", "Est. Fine"
        ])
        self.overdue_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.overdue_table.setAlternatingRowColors(True)
        self.overdue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.overdue_table)

        def load():
            loans = get_overdue_loans(self.conn)
            self.overdue_table.setRowCount(len(loans))
            today = date.today()
            total_fine = 0
            for r, loan in enumerate(loans):
                fine = compute_live_fine(self.conn, loan)
                total_fine += fine
                days = (today - date.fromisoformat(loan["due_date"])).days

                def cell(text, align=Qt.AlignLeft, bold=False):
                    item = QTableWidgetItem(str(text) if text else "")
                    item.setTextAlignment(align | Qt.AlignVCenter)
                    item.setForeground(QColor("#0f172a"))
                    if bold:
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)
                    return item

                self.overdue_table.setItem(r, 0, cell(loan["student_id"], bold=True))
                self.overdue_table.setItem(r, 1, cell(loan["student_name"]))
                self.overdue_table.setItem(r, 2, cell(loan["course"]))
                self.overdue_table.setItem(r, 3, cell(loan["acc_no"], bold=True))
                self.overdue_table.setItem(r, 4, cell(loan["title"]))
                self.overdue_table.setItem(r, 5, cell(loan["due_date"]))
                fi = cell(f"₹{fine:.0f}", Qt.AlignRight, bold=True)
                fi.setForeground(QColor("#b91c1c"))
                self.overdue_table.setItem(r, 6, fi)

            self.overdue_summary.setText(
                f"{len(loans)} overdue book(s)  |  Total estimated fines: ₹{total_fine:.0f}"
            )

        def export_excel():
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Overdue Report", f"overdue_{date.today()}.xlsx",
                "Excel Files (*.xlsx)"
            )
            if not path:
                return
            try:
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Overdue"
                headers = ["Student ID", "Name", "Course", "Acc No", "Title", "Due Date", "Fine"]
                ws.append(headers)
                for r in range(self.overdue_table.rowCount()):
                    ws.append([
                        self.overdue_table.item(r, c).text() if self.overdue_table.item(r, c) else ""
                        for c in range(self.overdue_table.columnCount())
                    ])
                wb.save(path)
                QMessageBox.information(self, "Exported", f"Saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

        refresh_btn.clicked.connect(load)
        export_btn.clicked.connect(export_excel)
        load()
        return w

    # ── History tab ────────────────────────────────────────────────────
    def _make_history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("From:"))
        self.from_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        date_row.addWidget(self.from_date)
        date_row.addWidget(QLabel("To:"))
        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        date_row.addWidget(self.to_date)
        load_btn = QPushButton("Load")
        load_btn.setObjectName("primaryBtn")
        date_row.addWidget(load_btn)
        date_row.addStretch()
        lay.addLayout(date_row)

        self.history_table = QTableWidget(0, 7)
        self.history_table.setHorizontalHeaderLabels([
            "Student ID", "Name", "Acc No", "Title", "Issue Date", "Return Date", "Status"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.history_table)

        def load():
            from_str = self.from_date.date().toString("yyyy-MM-dd")
            to_str   = self.to_date.date().toString("yyyy-MM-dd")
            rows = self.conn.execute("""
                SELECT l.*, s.name as student_name, b.title
                FROM loans l
                JOIN students s ON s.student_id = l.student_id
                JOIN books b ON b.acc_no = l.acc_no
                WHERE l.issue_date BETWEEN ? AND ?
                ORDER BY l.issue_date DESC
            """, (from_str, to_str)).fetchall()

            self.history_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate([
                    row["student_id"], row["student_name"], row["acc_no"],
                    row["title"], row["issue_date"],
                    row["return_date"] or "—", row["status"]
                ]):
                    self.history_table.setItem(r, c, QTableWidgetItem(str(val)))

        load_btn.clicked.connect(load)
        return w

    # ── Most borrowed tab ──────────────────────────────────────────────
    def _make_most_borrowed_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)

        load_btn = QPushButton("⟳  Load")
        load_btn.setObjectName("primaryBtn")
        lay.addWidget(load_btn)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["Title", "Author", "Times Borrowed", "Currently Issued"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(table)

        def load():
            rows = self.conn.execute("""
                SELECT b.title, b.author,
                       COUNT(l.id) as borrow_count,
                       SUM(CASE WHEN l.status='ACTIVE' THEN 1 ELSE 0 END) as active_count
                FROM books b
                LEFT JOIN loans l ON l.acc_no = b.acc_no
                GROUP BY b.title, b.author
                ORDER BY borrow_count DESC
                LIMIT 50
            """).fetchall()
            table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate([row["title"], row["author"],
                                         row["borrow_count"], row["active_count"]]):
                    table.setItem(r, c, QTableWidgetItem(str(val)))

        load_btn.clicked.connect(load)
        load()
        return w

    def on_show(self):
        pass
