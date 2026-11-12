"""
Dashboard screen: today's stats at a glance.
Official high-contrast theme.
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from core.rules import get_dashboard_stats, get_overdue_loans, compute_live_fine
from datetime import date


def _stat_card(title: str, value: str, color: str = "#1d4ed8") -> QFrame:
    card = QFrame()
    card.setObjectName("statCard")
    card.setStyleSheet(f"QFrame#statCard {{ border-left: 5px solid {color}; }}")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(4)
    val_lbl = QLabel(value)
    val_lbl.setFont(QFont("Segoe UI", 24, QFont.Bold))
    val_lbl.setStyleSheet(f"color: {color}; font-weight: 800;")
    ttl_lbl = QLabel(title)
    ttl_lbl.setStyleSheet("color: #0f172a; font-size: 12px; font-weight: 700;")
    lay.addWidget(val_lbl)
    lay.addWidget(ttl_lbl)
    return card


class DashboardScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()
        self._refresh()
        # Auto-refresh every 60 s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(60000)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Institutional Overview & Dashboard")
        title_lbl.setObjectName("sectionTitle")
        self.date_lbl = QLabel(date.today().strftime("%A, %d %B %Y"))
        self.date_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 700;")
        refresh_btn = QPushButton("⟳  Refresh Live Data")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.setFixedWidth(160)
        refresh_btn.clicked.connect(self._refresh)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        title_row.addWidget(self.date_lbl)
        title_row.addWidget(refresh_btn)
        layout.addLayout(title_row)

        # Stat cards row
        self.stat_row = QHBoxLayout()
        self.stat_row.setSpacing(14)
        self.stat_cards_widget = QWidget()
        self.stat_cards_widget.setLayout(self.stat_row)
        layout.addWidget(self.stat_cards_widget)

        # Overdue table
        od_lbl = QLabel("Active Overdue Borrowers")
        od_lbl.setObjectName("cardTitle")
        layout.addWidget(od_lbl)

        self.overdue_table = QTableWidget(0, 7)
        self.overdue_table.setHorizontalHeaderLabels([
            "Student ID", "Student Name", "Acc No", "Book Title", "Due Date", "Days Late", "Estimated Fine"
        ])
        self.overdue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.overdue_table.setAlternatingRowColors(True)
        self.overdue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.overdue_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.overdue_table)

    def _refresh(self):
        stats = get_dashboard_stats(self.conn)
        # Clear and rebuild stat cards
        while self.stat_row.count():
            item = self.stat_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            ("Books Issued Today",    str(stats["issued_today"]),     "#1d4ed8"),
            ("Returned Today",        str(stats["returned_today"]),   "#15803d"),
            ("Overdue Books",         str(stats["overdue_count"]),    "#b91c1c"),
            ("Outstanding Fines",     f"₹{stats['total_fines_due']:.0f}", "#c2410c"),
            ("Available Copies",      str(stats["books_available"]),  "#0284c7"),
            ("Active Students",       str(stats["total_students"]),   "#6d28d9"),
        ]
        for title, value, color in cards:
            self.stat_row.addWidget(_stat_card(title, value, color))
        self.stat_row.addStretch()

        # Overdue table
        overdue = get_overdue_loans(self.conn)
        self.overdue_table.setRowCount(len(overdue))
        today = date.today()
        for r, row in enumerate(overdue):
            due = date.fromisoformat(row["due_date"])
            days_late = (today - due).days
            fine = compute_live_fine(self.conn, row)

            def cell(text, align=Qt.AlignLeft, bold=False):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(align | Qt.AlignVCenter)
                item.setForeground(QColor("#0f172a"))
                if bold:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                return item

            self.overdue_table.setItem(r, 0, cell(row["student_id"], bold=True))
            self.overdue_table.setItem(r, 1, cell(row["student_name"]))
            self.overdue_table.setItem(r, 2, cell(row["acc_no"], bold=True))
            self.overdue_table.setItem(r, 3, cell(row["title"]))
            self.overdue_table.setItem(r, 4, cell(row["due_date"]))
            self.overdue_table.setItem(r, 5, cell(str(days_late), Qt.AlignCenter, bold=True))
            
            fi = cell(f"₹{fine:.0f}", Qt.AlignRight, bold=True)
            fi.setForeground(QColor("#b91c1c"))
            self.overdue_table.setItem(r, 6, fi)
