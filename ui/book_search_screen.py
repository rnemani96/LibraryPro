"""
Book Search Screen.
Search by accession number, title, or author.
Shows: book status, who currently has it (if issued), copies of that title available.
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.rules import search_books, get_book_copies_info


class BookSearchScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Book Search")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Search bar
        search_frame = QFrame()
        search_frame.setObjectName("card")
        s_lay = QVBoxLayout(search_frame)
        s_lay.setContentsMargins(16, 12, 16, 12)

        hint = QLabel("Search by Accession Number, Title, or Author:")
        hint.setObjectName("cardTitle")
        s_lay.addWidget(hint)

        row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("scanBox")
        self.search_edit.setPlaceholderText("🔍  Enter accession no / title / author → Enter")
        self.search_edit.setFixedHeight(44)
        self.search_edit.returnPressed.connect(self._search)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("primaryBtn")
        search_btn.setFixedHeight(44)
        search_btn.clicked.connect(self._search)

        clear_btn = QPushButton("✕  Clear")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.setFixedHeight(44)
        clear_btn.clicked.connect(self._clear)

        row.addWidget(self.search_edit)
        row.addWidget(search_btn)
        row.addWidget(clear_btn)
        s_lay.addLayout(row)
        layout.addWidget(search_frame)

        # Copies summary (shown after search if same title)
        self.copies_frame = QFrame()
        self.copies_frame.setObjectName("card")
        self.copies_frame.setVisible(False)
        c_lay = QHBoxLayout(self.copies_frame)
        c_lay.setContentsMargins(16, 10, 16, 10)
        self.copies_lbl = QLabel("")
        self.copies_lbl.setObjectName("studentName")
        c_lay.addWidget(self.copies_lbl)
        layout.addWidget(self.copies_frame)

        # Results table
        self.result_count_lbl = QLabel("")
        self.result_count_lbl.setObjectName("cardTitle")
        layout.addWidget(self.result_count_lbl)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "Acc No", "Title", "Author", "Status",
            "Issued To (ID)", "Issued To (Name)", "Issue Date", "Due Date", "Dept"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self.search_edit.setFocus()

    def _search(self):
        query = self.search_edit.text().strip()
        if not query:
            return

        results = search_books(self.conn, query)
        self.table.setRowCount(len(results))
        self.result_count_lbl.setText(f"Found {len(results)} result(s) for '{query}'")

        # Show copies summary if results share the same title
        titles = {r["title"] for r in results}
        if len(titles) == 1:
            title = list(titles)[0]
            copies = get_book_copies_info(self.conn, title)
            self.copies_lbl.setText(
                f"📚  '{title}'  —  "
                f"Total Copies: {copies['total']}  |  "
                f"✅ Available: {copies['available']}  |  "
                f"📤 Issued: {copies['issued']}"
            )
            self.copies_frame.setVisible(True)
        elif len(titles) > 1 and query:
            # Try exact title match for copies display
            copies = get_book_copies_info(self.conn, query)
            if copies["total"] > 0:
                self.copies_lbl.setText(
                    f"📚  '{query}'  —  "
                    f"Total Copies: {copies['total']}  |  "
                    f"✅ Available: {copies['available']}  |  "
                    f"📤 Issued: {copies['issued']}"
                )
                self.copies_frame.setVisible(True)
            else:
                self.copies_frame.setVisible(False)
        else:
            self.copies_frame.setVisible(False)

        # Populate table
        for r, row in enumerate(results):
            status = row["status"]

            def cell(text, align=Qt.AlignLeft):
                item = QTableWidgetItem(str(text) if text else "—")
                item.setTextAlignment(align | Qt.AlignVCenter)
                return item

            self.table.setItem(r, 0, cell(row["acc_no"]))
            self.table.setItem(r, 1, cell(row["title"]))
            self.table.setItem(r, 2, cell(row["author"]))

            status_item = cell(status, Qt.AlignCenter)
            if status == "AVAILABLE":
                status_item.setForeground(Qt.darkGreen)
            elif status == "ISSUED":
                status_item.setForeground(Qt.blue)
            else:
                status_item.setForeground(Qt.red)
            self.table.setItem(r, 3, status_item)

            self.table.setItem(r, 4, cell(row["held_by_student"] or ""))
            self.table.setItem(r, 5, cell(row["held_by_name"] or ""))
            self.table.setItem(r, 6, cell(row["issue_date"] or ""))
            self.table.setItem(r, 7, cell(row["due_date"] or ""))
            self.table.setItem(r, 8, cell(row["department"] or ""))

    def _clear(self):
        self.search_edit.clear()
        self.table.setRowCount(0)
        self.result_count_lbl.clear()
        self.copies_frame.setVisible(False)
        self.search_edit.setFocus()

    def on_show(self):
        self.search_edit.setFocus()
