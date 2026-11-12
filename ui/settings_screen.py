"""
Settings Screen: manage app rules, user accounts, holidays, and backup.
"""
from __future__ import annotations
from pathlib import Path
import shutil
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox, QComboBox
)
from PySide6.QtCore import Qt

from db.schema import get_setting, set_setting


class SettingsScreen(QWidget):
    def __init__(self, conn, current_user: dict, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._make_rules_tab(), "⚙  Library Rules")
        tabs.addTab(self._make_users_tab(), "👥  User Accounts")
        tabs.addTab(self._make_holidays_tab(), "📅  Holidays")
        tabs.addTab(self._make_backup_tab(), "💾  Backup & Restore")
        layout.addWidget(tabs)

    # ── Rules tab ──────────────────────────────────────────────────────
    def _make_rules_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(12)

        self.max_books_spin = QSpinBox()
        self.max_books_spin.setRange(1, 10)
        self.max_books_spin.setValue(int(get_setting(self.conn, "max_books", "2")))

        self.loan_days_spin = QSpinBox()
        self.loan_days_spin.setRange(1, 60)
        self.loan_days_spin.setValue(int(get_setting(self.conn, "loan_days", "15")))

        self.fine_per_day_spin = QDoubleSpinBox()
        self.fine_per_day_spin.setRange(0, 500)
        self.fine_per_day_spin.setValue(float(get_setting(self.conn, "fine_per_day", "20")))
        self.fine_per_day_spin.setPrefix("₹ ")

        self.max_fine_spin = QDoubleSpinBox()
        self.max_fine_spin.setRange(0, 10000)
        self.max_fine_spin.setValue(float(get_setting(self.conn, "max_fine", "200")))
        self.max_fine_spin.setPrefix("₹ ")

        form.addRow("Max books per student:", self.max_books_spin)
        form.addRow("Loan/renewal period (days):", self.loan_days_spin)
        form.addRow("Fine per working day:", self.fine_per_day_spin)
        form.addRow("Maximum fine per book:", self.max_fine_spin)

        save_btn = QPushButton("💾  Save Rules")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self._save_rules)

        self.rules_status = QLabel("")
        lay.addLayout(form)
        lay.addWidget(save_btn)
        lay.addWidget(self.rules_status)
        lay.addStretch()
        return w

    def _save_rules(self):
        is_admin = self.current_user.get("role") == "admin"
        if not is_admin:
            QMessageBox.warning(self, "Access Denied", "Only admin can change rules.")
            return
        set_setting(self.conn, "max_books",    str(self.max_books_spin.value()))
        set_setting(self.conn, "loan_days",    str(self.loan_days_spin.value()))
        set_setting(self.conn, "fine_per_day", str(self.fine_per_day_spin.value()))
        set_setting(self.conn, "max_fine",     str(self.max_fine_spin.value()))
        self.rules_status.setText("✅  Settings saved.")
        self.rules_status.setStyleSheet("color: #198754;")

    # ── Users tab ──────────────────────────────────────────────────────
    def _make_users_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)

        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(["ID", "Username", "Full Name", "Role"])
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.users_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("➕  Add User")
        add_btn.setObjectName("successBtn")
        add_btn.clicked.connect(self._add_user)
        chpw_btn = QPushButton("🔑  Change My Password")
        chpw_btn.setObjectName("secondaryBtn")
        chpw_btn.clicked.connect(self._change_password)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(chpw_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        self._load_users()
        return w

    def _load_users(self):
        rows = self.conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        self.users_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate([row["id"], row["username"],
                                     row["full_name"] or "", row["role"]]):
                self.users_table.setItem(r, c, QTableWidgetItem(str(val)))

    def _add_user(self):
        if self.current_user.get("role") != "admin":
            QMessageBox.warning(self, "Access Denied", "Only admin can add users.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Add User")
        dlg.setFixedWidth(360)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()

        u_edit = QLineEdit()
        p_edit = QLineEdit()
        p_edit.setEchoMode(QLineEdit.Password)
        n_edit = QLineEdit()
        role_combo = QComboBox()
        role_combo.addItems(["librarian", "admin"])

        form.addRow("Username:", u_edit)
        form.addRow("Password:", p_edit)
        form.addRow("Full Name:", n_edit)
        form.addRow("Role:", role_combo)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            import hashlib
            u = u_edit.text().strip()
            p = p_edit.text()
            n = n_edit.text().strip()
            r = role_combo.currentText()
            if not u or not p:
                QMessageBox.warning(self, "Error", "Username and password are required.")
                return
            ph = hashlib.sha256(p.encode()).hexdigest()
            try:
                self.conn.execute(
                    "INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
                    (u, ph, n, r)
                )
                self.conn.commit()
                self._load_users()
                QMessageBox.information(self, "Done", f"User '{u}' created.")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _change_password(self):
        from core.rules import change_password
        dlg = QDialog(self)
        dlg.setWindowTitle("Change Password")
        dlg.setFixedWidth(340)
        lay = QVBoxLayout(dlg)
        form = QFormLayout()
        old_edit = QLineEdit(); old_edit.setEchoMode(QLineEdit.Password)
        new_edit = QLineEdit(); new_edit.setEchoMode(QLineEdit.Password)
        cfm_edit = QLineEdit(); cfm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Current password:", old_edit)
        form.addRow("New password:", new_edit)
        form.addRow("Confirm new:", cfm_edit)
        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        if dlg.exec() == QDialog.Accepted:
            if new_edit.text() != cfm_edit.text():
                QMessageBox.warning(self, "Mismatch", "New passwords do not match.")
                return
            result = change_password(
                self.conn,
                self.current_user["username"],
                old_edit.text(),
                new_edit.text()
            )
            if result["ok"]:
                QMessageBox.information(self, "Done", "Password changed successfully.")
            else:
                QMessageBox.critical(self, "Error", result["error"])

    # ── Holidays tab ───────────────────────────────────────────────────
    def _make_holidays_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 12, 16, 12)

        note = QLabel("Holidays are excluded from fine calculations. Add national/state/college holidays.")
        note.setWordWrap(True)
        note.setObjectName("studentInfo")
        lay.addWidget(note)

        add_row = QHBoxLayout()
        self.holiday_date_edit = QLineEdit()
        self.holiday_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.holiday_desc_edit = QLineEdit()
        self.holiday_desc_edit.setPlaceholderText("Description (e.g. Diwali)")
        add_btn = QPushButton("Add Holiday")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_holiday)
        add_row.addWidget(self.holiday_date_edit)
        add_row.addWidget(self.holiday_desc_edit)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        self.holiday_table = QTableWidget(0, 2)
        self.holiday_table.setHorizontalHeaderLabels(["Date", "Description"])
        self.holiday_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.holiday_table.setAlternatingRowColors(True)
        self.holiday_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.holiday_table)

        del_btn = QPushButton("🗑  Delete Selected")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_holiday)
        lay.addWidget(del_btn)
        self._load_holidays()
        return w

    def _load_holidays(self):
        rows = self.conn.execute("SELECT * FROM holidays ORDER BY date").fetchall()
        self.holiday_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.holiday_table.setItem(r, 0, QTableWidgetItem(row["date"]))
            self.holiday_table.setItem(r, 1, QTableWidgetItem(row["description"] or ""))

    def _add_holiday(self):
        d = self.holiday_date_edit.text().strip()
        desc = self.holiday_desc_edit.text().strip()
        if not d:
            return
        try:
            date.fromisoformat(d)  # validate
        except ValueError:
            QMessageBox.warning(self, "Invalid Date", "Use format YYYY-MM-DD")
            return
        self.conn.execute(
            "INSERT OR REPLACE INTO holidays(date,description) VALUES(?,?)", (d, desc)
        )
        self.conn.commit()
        self.holiday_date_edit.clear()
        self.holiday_desc_edit.clear()
        self._load_holidays()

    def _delete_holiday(self):
        rows = self.holiday_table.selectionModel().selectedRows()
        if not rows:
            return
        d = self.holiday_table.item(rows[0].row(), 0).text()
        self.conn.execute("DELETE FROM holidays WHERE date=?", (d,))
        self.conn.commit()
        self._load_holidays()

    # ── Backup tab ─────────────────────────────────────────────────────
    def _make_backup_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        from db.schema import DB_PATH
        db_path = DB_PATH

        info = QLabel(f"Database location:\n{db_path}")
        info.setWordWrap(True)
        info.setObjectName("studentInfo")
        lay.addWidget(info)

        backup_btn = QPushButton("💾  Backup Now")
        backup_btn.setObjectName("primaryBtn")
        backup_btn.setFixedWidth(180)

        def do_backup():
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Backup",
                f"library_backup_{date.today()}.db",
                "Database (*.db)"
            )
            if path:
                try:
                    shutil.copy2(str(db_path), path)
                    QMessageBox.information(self, "Backup", f"Backup saved:\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))

        backup_btn.clicked.connect(do_backup)
        lay.addWidget(backup_btn)

        restore_btn = QPushButton("📂  Restore from Backup")
        restore_btn.setObjectName("warningBtn")
        restore_btn.setFixedWidth(200)

        def do_restore():
            path, _ = QFileDialog.getOpenFileName(
                self, "Select Backup File", "", "Database (*.db)"
            )
            if not path:
                return
            reply = QMessageBox.warning(
                self, "Confirm Restore",
                "⚠  This will REPLACE the current database!\nAre you sure?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    shutil.copy2(path, str(db_path))
                    QMessageBox.information(
                        self, "Restored",
                        "Database restored.\nPlease restart the application."
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))

        restore_btn.clicked.connect(do_restore)
        lay.addWidget(restore_btn)
        lay.addStretch()
        return w

    def on_show(self):
        pass
