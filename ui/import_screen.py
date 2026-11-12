"""
Import Screen: import books and students from Excel files.
"""
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QProgressBar, QTextEdit, QFileDialog, QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal

from importers.excel_import import import_books, import_students


class _ImportWorker(QThread):
    progress = Signal(int, int)
    done = Signal(dict)

    def __init__(self, conn, path: Path, kind: str):
        super().__init__()
        self.conn = conn
        self.path = path
        self.kind = kind

    def run(self):
        def on_progress(current, total):
            self.progress.emit(current, total)

        if self.kind == "books":
            result = import_books(self.conn, self.path, on_progress)
        else:
            result = import_students(self.conn, self.path, on_progress)
        self.done.emit(result)


class ImportScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Import Data from Excel")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        tabs = QTabWidget()

        tabs.addTab(self._make_import_tab("books"), "📚  Import Books")
        tabs.addTab(self._make_import_tab("students"), "🎓  Import Students")

        layout.addWidget(tabs)
        layout.addStretch()

    def _make_import_tab(self, kind: str) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        if kind == "books":
            hint = (
                "Excel columns (any order, flexible headers):\n"
                "  Acc No | Title | Author | Vol | Edition | Year | Publisher | Dept | Call No | Cost"
            )
        else:
            hint = (
                "Excel columns (any order, flexible headers):\n"
                "  Student ID | Name | Course | Year | Phone | Email"
            )

        hint_lbl = QLabel(hint)
        hint_lbl.setStyleSheet("color: #0f172a; font-size: 13px; font-weight: 600; background-color: #f8fafc; padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1;")
        hint_lbl.setWordWrap(True)
        lay.addWidget(hint_lbl)

        # File picker
        file_row = QHBoxLayout()
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("Select Excel file (.xlsx)…")
        path_edit.setReadOnly(True)
        path_edit.setFixedHeight(36)

        browse_btn = QPushButton("📂  Browse…")
        browse_btn.setObjectName("secondaryBtn")

        def browse():
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Excel File", "", "Excel Files (*.xlsx *.xls)"
            )
            if path:
                path_edit.setText(path)

        browse_btn.clicked.connect(browse)
        file_row.addWidget(path_edit)
        file_row.addWidget(browse_btn)
        lay.addLayout(file_row)

        # Progress bar
        progress = QProgressBar()
        progress.setVisible(False)
        lay.addWidget(progress)

        # Import button
        import_btn = QPushButton(f"⬆  Import {kind.title()}")
        import_btn.setObjectName("primaryBtn")
        import_btn.setFixedHeight(40)

        # Log box
        log_box = QTextEdit()
        log_box.setStyleSheet("background-color: #ffffff; color: #0f172a; font-family: Consolas, monospace; font-size: 12px; font-weight: 600; border: 1.5px solid #94a3b8;")
        log_box.setReadOnly(True)
        log_box.setMaximumHeight(200)

        def do_import():
            path_str = path_edit.text().strip()
            if not path_str:
                QMessageBox.warning(self, "No File", "Please select an Excel file first.")
                return
            path = Path(path_str)
            if not path.exists():
                QMessageBox.warning(self, "Not Found", "File not found.")
                return

            import_btn.setEnabled(False)
            progress.setVisible(True)
            progress.setValue(0)
            log_box.clear()

            self._worker = _ImportWorker(self.conn, path, kind)

            def on_progress(cur, total):
                if total > 0:
                    progress.setValue(int(cur * 100 / total))

            def on_done(result):
                progress.setValue(100)
                progress.setVisible(False)
                import_btn.setEnabled(True)
                log_box.append(f"✅  Imported: {result['imported']}")
                log_box.append(f"⚠   Skipped:  {result['skipped']}")
                if result.get("errors"):
                    log_box.append("\nErrors:")
                    for e in result["errors"][:20]:
                        log_box.append(f"  • {e}")

            self._worker.progress.connect(on_progress)
            self._worker.done.connect(on_done)
            self._worker.start()

        import_btn.clicked.connect(do_import)
        lay.addWidget(import_btn)
        lay.addWidget(QLabel("Import Log:"))
        lay.addWidget(log_box)

        return widget

    def on_show(self):
        pass
