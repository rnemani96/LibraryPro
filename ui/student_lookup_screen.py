"""
Student Lookup Screen: search a student, view full details, loans, fines.
"""
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from core.rules import get_student
from ui.student_panel import StudentInfoPanel


class StudentLookupScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Student Lookup")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # Search bar
        search_frame = QFrame()
        search_frame.setObjectName("card")
        s_lay = QVBoxLayout(search_frame)
        s_lay.setContentsMargins(16, 12, 16, 12)
        s_lay.setSpacing(8)

        s_lay.addWidget(QLabel("Scan or enter Student ID / QR Code:"))

        row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("scanBox")
        self.search_edit.setPlaceholderText("🔍  Scan QR or type Student ID → Enter")
        self.search_edit.setFixedHeight(44)
        self.search_edit.returnPressed.connect(self._search)

        search_btn = QPushButton("Look Up")
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

        # Also name search
        name_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Or search by name (partial) → Enter")
        self.name_edit.setFixedHeight(36)
        self.name_edit.returnPressed.connect(self._search_by_name)
        name_search_btn = QPushButton("Search by Name")
        name_search_btn.setObjectName("secondaryBtn")
        name_search_btn.clicked.connect(self._search_by_name)
        name_row.addWidget(self.name_edit)
        name_row.addWidget(name_search_btn)
        s_lay.addLayout(name_row)
        layout.addWidget(search_frame)

        # Name search results (small table)
        self.name_results_table = QTableWidget(0, 4)
        self.name_results_table.setHorizontalHeaderLabels(["Student ID", "Name", "Course", "Year"])
        self.name_results_table.setMaximumHeight(130)
        self.name_results_table.setVisible(False)
        self.name_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.name_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.name_results_table.cellDoubleClicked.connect(self._select_from_name_results)
        layout.addWidget(self.name_results_table)

        self.status_lbl = QLabel("")
        self.status_lbl.setObjectName("statusError")
        layout.addWidget(self.status_lbl)

        # Student panel
        self.student_panel = StudentInfoPanel()
        self.student_panel.setVisible(False)
        layout.addWidget(self.student_panel)
        layout.addStretch()

        self.search_edit.setFocus()

    def _search(self):
        raw = self.search_edit.text().strip()
        if not raw:
            return
        student_id = raw
        if "|" in raw:
            parts = raw.split("|")
            student_id = "|".join(parts[1:]) if len(parts) >= 2 else raw

        student = get_student(self.conn, student_id)
        if not student:
            student = get_student(self.conn, raw)

        if not student:
            self.status_lbl.setText(f"❌  No student found with ID: {raw}")
            self.student_panel.setVisible(False)
            return

        self.status_lbl.clear()
        self.student_panel.load_student(self.conn, student)
        self.student_panel.setVisible(True)
        self.name_results_table.setVisible(False)

    def _search_by_name(self):
        name = self.name_edit.text().strip()
        if not name:
            return
        rows = self.conn.execute("""
            SELECT student_id, name, course, year FROM students
            WHERE LOWER(name) LIKE LOWER(?)
            ORDER BY name LIMIT 50
        """, (f"%{name}%",)).fetchall()

        self.name_results_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, field in enumerate(["student_id", "name", "course", "year"]):
                self.name_results_table.setItem(r, c, QTableWidgetItem(str(row[field] or "")))
        self.name_results_table.setVisible(len(rows) > 0)
        if not rows:
            self.status_lbl.setText(f"❌  No students found matching '{name}'")

    def _select_from_name_results(self, row, col):
        student_id = self.name_results_table.item(row, 0)
        if student_id:
            self.search_edit.setText(student_id.text())
            self._search()

    def _clear(self):
        self.search_edit.clear()
        self.name_edit.clear()
        self.status_lbl.clear()
        self.student_panel.clear()
        self.student_panel.setVisible(False)
        self.name_results_table.setVisible(False)
        self.search_edit.setFocus()

    def on_show(self):
        self.search_edit.setFocus()
