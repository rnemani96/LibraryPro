"""
Official Institutional Stylesheet for LibraryPro.
High-contrast, pleasant, official enterprise palette with crisp dark/black typography.
"""

STYLESHEET = """
/* ─── Global Reset & Window Background ────────────────────────────── */
QWidget {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    color: #0f172a;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #f1f5f9;
}

QLabel {
    color: #0f172a;
    font-size: 13px;
}

/* ─── Sidebar Navigation ──────────────────────────────────────────── */
QFrame#sidebar {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
    min-width: 220px;
    max-width: 220px;
}

QPushButton#navBtn {
    background-color: transparent;
    color: #cbd5e1;
    border: none;
    padding: 13px 22px;
    text-align: left;
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    margin: 2px 10px;
}
QPushButton#navBtn:hover {
    background-color: #1e293b;
    color: #ffffff;
}
QPushButton#navBtn:checked {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 700;
}

QLabel#appTitle {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 20px 18px 4px 18px;
}
QLabel#appSubtitle {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 0px 18px 18px 18px;
}

/* ─── Cards & Surface Panels ──────────────────────────────────────── */
QFrame#card {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
}

QFrame#statCard {
    background-color: #ffffff;
    border-radius: 8px;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #2563eb;
    min-width: 150px;
}

/* ─── Typography & Headings ───────────────────────────────────────── */
QLabel#sectionTitle {
    font-size: 20px;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 2px;
}
QLabel#cardTitle {
    font-size: 14px;
    font-weight: 700;
    color: #0f172a;
}
QLabel#subTitle {
    font-size: 12px;
    font-weight: 600;
    color: #334155;
}

/* ─── Barcode & QR Scan Input ─────────────────────────────────────── */
QLineEdit#scanBox {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    padding: 10px 14px;
    border: 2px solid #2563eb;
    border-radius: 8px;
    background-color: #eff6ff;
}
QLineEdit#scanBox:focus {
    border-color: #1d4ed8;
    background-color: #ffffff;
}

/* ─── Standard Form Controls ──────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QDateEdit {
    padding: 8px 12px;
    border: 1.5px solid #94a3b8;
    border-radius: 6px;
    background-color: #ffffff;
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border-color: #2563eb;
    background-color: #ffffff;
}
QLineEdit::placeholder {
    color: #64748b;
    font-weight: normal;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
    border: 1px solid #cbd5e1;
}

/* ─── High-Contrast Action Buttons ────────────────────────────────── */
QPushButton {
    padding: 9px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    border: none;
}

QPushButton#primaryBtn {
    background-color: #1d4ed8;
    color: #ffffff;
}
QPushButton#primaryBtn:hover {
    background-color: #1e40af;
}
QPushButton#primaryBtn:pressed {
    background-color: #172554;
}

QPushButton#successBtn {
    background-color: #15803d;
    color: #ffffff;
}
QPushButton#successBtn:hover {
    background-color: #166534;
}
QPushButton#successBtn:pressed {
    background-color: #14532d;
}

QPushButton#dangerBtn {
    background-color: #b91c1c;
    color: #ffffff;
}
QPushButton#dangerBtn:hover {
    background-color: #991b1b;
}

QPushButton#warningBtn {
    background-color: #c2410c;
    color: #ffffff;
}
QPushButton#warningBtn:hover {
    background-color: #9a3412;
}

QPushButton#secondaryBtn {
    background-color: #334155;
    color: #ffffff;
}
QPushButton#secondaryBtn:hover {
    background-color: #1e293b;
}

/* ─── Institutional Tables ────────────────────────────────────────── */
QTableWidget {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background-color: #ffffff;
    gridline-color: #e2e8f0;
    font-size: 13px;
    color: #0f172a;
    alternate-background-color: #f8fafc;
}
QTableWidget::item {
    padding: 8px 10px;
    color: #0f172a;
    font-weight: 500;
}
QTableWidget::item:selected {
    background-color: #dbeafe;
    color: #0f172a;
    font-weight: 700;
}
QHeaderView::section {
    background-color: #1e293b;
    color: #ffffff;
    padding: 9px 10px;
    border: none;
    border-right: 1px solid #334155;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

/* ─── System Badges & Feedback ────────────────────────────────────── */
QLabel#statusOk {
    color: #15803d;
    font-weight: 700;
    font-size: 13px;
}
QLabel#statusError {
    color: #b91c1c;
    font-weight: 700;
    font-size: 13px;
}
QLabel#statusWarn {
    color: #c2410c;
    font-weight: 700;
    font-size: 13px;
}

/* ─── Student Summary Card ────────────────────────────────────────── */
QFrame#studentPanel {
    background-color: #ffffff;
    border: 2px solid #93c5fd;
    border-radius: 8px;
    padding: 10px;
}
QLabel#studentName {
    font-size: 18px;
    font-weight: 800;
    color: #0f172a;
}
QLabel#studentInfo {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
}

/* ─── Photo Frame ─────────────────────────────────────────────────── */
QLabel#photoLabel {
    border: 2px solid #cbd5e1;
    border-radius: 6px;
    background-color: #f8fafc;
}

/* ─── Tabs ────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
}
QTabBar::tab {
    background: #e2e8f0;
    color: #0f172a;
    padding: 9px 20px;
    border-radius: 6px 6px 0 0;
    margin-right: 3px;
    font-size: 13px;
    font-weight: 700;
}
QTabBar::tab:selected {
    background: #1d4ed8;
    color: #ffffff;
}

/* ─── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    width: 10px;
    background: #f1f5f9;
}
QScrollBar::handle:vertical {
    background: #94a3b8;
    border-radius: 5px;
    min-height: 35px;
}
QScrollBar::handle:vertical:hover {
    background: #64748b;
}
"""
