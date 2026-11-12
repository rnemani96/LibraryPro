"""
Database schema creation and initialization for the Library Management System.
"""
import sqlite3
import os
import sys
from pathlib import Path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "data" / "library.db"


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    """Return a connection with foreign keys enabled and row_factory set."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def create_tables(conn: sqlite3.Connection):
    """Create all tables if they don't exist."""
    cur = conn.cursor()

    cur.executescript("""
    -- ─────────────────────────── BOOKS ───────────────────────────
    CREATE TABLE IF NOT EXISTS books (
        acc_no       TEXT PRIMARY KEY,
        title        TEXT NOT NULL,
        author       TEXT NOT NULL,
        volume       TEXT,
        edition      TEXT,
        year         TEXT,
        publisher    TEXT,
        department   TEXT,
        call_no      TEXT,
        cost         REAL DEFAULT 0,
        status       TEXT NOT NULL DEFAULT 'AVAILABLE'
                     CHECK(status IN ('AVAILABLE','ISSUED','LOST','DAMAGED')),
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─────────────────────────── STUDENTS ────────────────────────
    CREATE TABLE IF NOT EXISTS students (
        student_id   TEXT PRIMARY KEY,
        name         TEXT NOT NULL,
        course       TEXT,
        year         TEXT,
        phone        TEXT,
        email        TEXT,
        photo_path   TEXT,
        active       INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─────────────────────────── LOANS ───────────────────────────
    CREATE TABLE IF NOT EXISTS loans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        acc_no          TEXT NOT NULL REFERENCES books(acc_no),
        student_id      TEXT NOT NULL REFERENCES students(student_id),
        issue_date      TEXT NOT NULL,
        due_date        TEXT NOT NULL,
        return_date     TEXT,
        renewals_count  INTEGER NOT NULL DEFAULT 0,
        issued_by       TEXT,
        returned_by     TEXT,
        status          TEXT NOT NULL DEFAULT 'ACTIVE'
                        CHECK(status IN ('ACTIVE','RETURNED','LOST'))
    );

    -- ─────────────────────────── FINES ───────────────────────────
    CREATE TABLE IF NOT EXISTS fines (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id      INTEGER NOT NULL REFERENCES loans(id),
        student_id   TEXT NOT NULL REFERENCES students(student_id),
        days_late    INTEGER NOT NULL DEFAULT 0,
        amount       REAL NOT NULL DEFAULT 0,
        paid_amount  REAL NOT NULL DEFAULT 0,
        status       TEXT NOT NULL DEFAULT 'UNPAID'
                     CHECK(status IN ('UNPAID','PAID','WAIVED','PARTIAL')),
        created_at   TEXT DEFAULT (datetime('now','localtime')),
        paid_on      TEXT
    );

    -- ─────────────────────────── USERS ───────────────────────────
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name     TEXT,
        role          TEXT NOT NULL DEFAULT 'librarian'
                      CHECK(role IN ('admin','librarian')),
        active        INTEGER NOT NULL DEFAULT 1,
        created_at    TEXT DEFAULT (datetime('now','localtime'))
    );

    -- ─────────────────────────── AUDIT LOG ───────────────────────
    CREATE TABLE IF NOT EXISTS audit_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp  TEXT DEFAULT (datetime('now','localtime')),
        username   TEXT,
        action     TEXT NOT NULL,
        details    TEXT
    );

    -- ─────────────────────────── SETTINGS ────────────────────────
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    -- ─────────────────────────── HOLIDAYS ────────────────────────
    CREATE TABLE IF NOT EXISTS holidays (
        date        TEXT PRIMARY KEY,
        description TEXT
    );
    """)

    # Default settings
    defaults = [
        ("max_books",        "2"),
        ("loan_days",        "15"),
        ("fine_per_day",     "20"),
        ("max_fine",         "200"),
        ("renewals_allowed", "-1"),   # -1 = unlimited
        ("block_on_fine",    "0"),    # 0 = don't block
        ("count_sundays",    "0"),    # 0 = exclude Sundays
        ("count_holidays",   "0"),    # 0 = exclude holidays
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", defaults
    )

    conn.commit()


def get_setting(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str):
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
    conn.commit()


def ensure_default_admin(conn: sqlite3.Connection):
    """Create a default admin account if no users exist."""
    import hashlib
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
        conn.execute(
            "INSERT INTO users(username,password_hash,full_name,role) VALUES(?,?,?,?)",
            ("admin", pw_hash, "Administrator", "admin")
        )
        conn.commit()


def init_db(db_path: Path = None) -> sqlite3.Connection:
    """Full initialisation: connect, create tables, seed defaults."""
    conn = get_connection(db_path)
    create_tables(conn)
    ensure_default_admin(conn)
    return conn
