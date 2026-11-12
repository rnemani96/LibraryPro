"""
Stylesheet for the Library Management System.
Modern, clean look with a navy/teal colour palette.
"""

STYLESHEET = """
QMainWindow, QDialog {
    background-color: #f0f4f8;
}

/* ─── Sidebar ─────────────────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #1a2744;
    min-width: 200px;
    max-width: 200px;
}

QPushButton#navBtn {
    background-color: transparent;
    color: #c8d6e8;
    border: none;
    padding: 12px 20px;
    text-align: left;
    font-size: 13px;
    border-radius: 0px;
}
QPushButton#navBtn:hover {
    background-color: #263660;
    color: white;
}
QPushButton#navBtn:checked {
    background-color: #0d6efd;
    color: white;
    font-weight: bold;
}

QLabel#appTitle {
    color: white;
    font-size: 15px;
    font-weight: bold;
    padding: 16px 12px 8px 12px;
}
QLabel#appSubtitle {
    color: #8ca0bb;
    font-size: 10px;
    padding: 0px 12px 16px 12px;
}

/* ─── Cards / Panels ───────────────────────────────────────────────── */
QFrame#card {
    background-color: white;
    border-radius: 10px;
    border: 1px solid #dde3ec;
}
QFrame#statCard {
    background-color: white;
    border-radius: 10px;
    border: 1px solid #dde3ec;
    min-width: 140px;
}

/* ─── Section headers ─────────────────────────────────────────────── */
QLabel#sectionTitle {
    font-size: 18px;
    font-weight: bold;
    color: #1a2744;
}
QLabel#cardTitle {
    font-size: 13px;
    font-weight: bold;
    color: #4a5568;
}

/* ─── Scan box ────────────────────────────────────────────────────── */
QLineEdit#scanBox {
    font-size: 15px;
    padding: 10px 14px;
    border: 2px solid #0d6efd;
    border-radius: 8px;
    background-color: #eaf3ff;
}
QLineEdit#scanBox:focus {
    border-color: #0a58ca;
    background-color: #dbeafe;
}

/* ─── Normal inputs ───────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    padding: 7px 10px;
    border: 1px solid #c9d4e0;
    border-radius: 6px;
    background-color: white;
    font-size: 13px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #0d6efd;
}

/* ─── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    padding: 8px 18px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#primaryBtn {
    background-color: #0d6efd;
    color: white;
    border: none;
}
QPushButton#primaryBtn:hover  { background-color: #0b5ed7; }
QPushButton#primaryBtn:pressed{ background-color: #0a58ca; }

QPushButton#successBtn {
    background-color: #198754;
    color: white;
    border: none;
}
QPushButton#successBtn:hover  { background-color: #157347; }

QPushButton#dangerBtn {
    background-color: #dc3545;
    color: white;
    border: none;
}
QPushButton#dangerBtn:hover   { background-color: #bb2d3b; }

QPushButton#warningBtn {
    background-color: #fd7e14;
    color: white;
    border: none;
}
QPushButton#secondaryBtn {
    background-color: #6c757d;
    color: white;
    border: none;
}
QPushButton#secondaryBtn:hover{ background-color: #565e64; }

/* ─── Tables ──────────────────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #dde3ec;
    border-radius: 6px;
    background-color: white;
    gridline-color: #edf2f7;
    font-size: 12px;
    alternate-background-color: #f8fafc;
}
QTableWidget::item { padding: 6px 8px; }
QTableWidget::item:selected {
    background-color: #cfe2ff;
    color: #1a2744;
}
QHeaderView::section {
    background-color: #1a2744;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
    font-size: 12px;
}

/* ─── Status labels ───────────────────────────────────────────────── */
QLabel#statusOk    { color: #198754; font-weight: bold; }
QLabel#statusError { color: #dc3545; font-weight: bold; }
QLabel#statusWarn  { color: #fd7e14; font-weight: bold; }

/* ─── Student info panel ──────────────────────────────────────────── */
QFrame#studentPanel {
    background-color: #eaf3ff;
    border: 1px solid #93c5fd;
    border-radius: 10px;
    padding: 8px;
}
QLabel#studentName { font-size: 16px; font-weight: bold; color: #1a2744; }
QLabel#studentInfo { font-size: 12px; color: #4a5568; }

/* ─── Photo frame ─────────────────────────────────────────────────── */
QLabel#photoLabel {
    border: 2px solid #93c5fd;
    border-radius: 8px;
    background-color: #dbeafe;
}

/* ─── Tab widget ──────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #dde3ec;
    border-radius: 6px;
    background: white;
}
QTabBar::tab {
    background: #e2e8f0;
    padding: 7px 18px;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-size: 12px;
}
QTabBar::tab:selected { background: #0d6efd; color: white; }

/* ─── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    width: 8px;
    background: #f0f4f8;
}
QScrollBar::handle:vertical {
    background: #c9d4e0;
    border-radius: 4px;
    min-height: 30px;
}
"""
