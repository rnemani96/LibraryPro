"""
Business rules engine: Issue, Return, Renew, Fine calculation.
All logic here; no UI code.

Rules (from confirmed answers):
  - 2 books max per student
  - 15-day loan + 15-day per renewal (unlimited renewals)
  - Overdue book can be renewed only after fine is paid
  - Unpaid fine does NOT block new issues
  - Sundays and listed holidays do NOT count toward fine days
  - Max fine per book: ₹200
  - Fine rate: ₹20/day
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import date, timedelta
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_holidays(conn: sqlite3.Connection) -> set[str]:
    """Return a set of holiday date strings 'YYYY-MM-DD'."""
    rows = conn.execute("SELECT date FROM holidays").fetchall()
    return {r["date"] for r in rows}


def _count_fine_days(issue_date: date, return_date: date,
                     due_date: date, conn: sqlite3.Connection) -> int:
    """
    Count working days between due_date+1 and return_date (inclusive)
    excluding Sundays and registered holidays.
    Returns 0 if return_date <= due_date.
    """
    if return_date <= due_date:
        return 0

    holidays = _load_holidays(conn)
    days = 0
    current = due_date + timedelta(days=1)
    while current <= return_date:
        if current.weekday() != 6 and current.strftime("%Y-%m-%d") not in holidays:
            days += 1
        current += timedelta(days=1)
    return days


def _fine_for_days(days: int, conn: sqlite3.Connection) -> float:
    """Apply per-day rate and cap at max_fine."""
    rate = float(conn.execute(
        "SELECT value FROM settings WHERE key='fine_per_day'").fetchone()["value"])
    max_fine = float(conn.execute(
        "SELECT value FROM settings WHERE key='max_fine'").fetchone()["value"])
    return min(days * rate, max_fine)


def _loan_days_setting(conn: sqlite3.Connection) -> int:
    return int(conn.execute(
        "SELECT value FROM settings WHERE key='loan_days'").fetchone()["value"])


def _max_books_setting(conn: sqlite3.Connection) -> int:
    return int(conn.execute(
        "SELECT value FROM settings WHERE key='max_books'").fetchone()["value"])


def _audit(conn: sqlite3.Connection, username: str, action: str, details: str):
    conn.execute(
        "INSERT INTO audit_log(username,action,details) VALUES(?,?,?)",
        (username, action, details)
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def get_student(conn: sqlite3.Connection, student_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM students WHERE student_id=?", (student_id,)
    ).fetchone()


def get_book(conn: sqlite3.Connection, acc_no: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM books WHERE acc_no=?", (acc_no,)
    ).fetchone()


def get_active_loans_for_student(conn: sqlite3.Connection, student_id: str):
    """Return list of active (unreturned) loans for a student, joined with book info."""
    return conn.execute("""
        SELECT l.*, b.title, b.author, b.acc_no as book_acc
        FROM loans l
        JOIN books b ON b.acc_no = l.acc_no
        WHERE l.student_id=? AND l.status='ACTIVE'
        ORDER BY l.due_date
    """, (student_id,)).fetchall()


def get_loan_history_for_student(conn: sqlite3.Connection, student_id: str):
    return conn.execute("""
        SELECT l.*, b.title, b.author
        FROM loans l
        JOIN books b ON b.acc_no = l.acc_no
        WHERE l.student_id=?
        ORDER BY l.issue_date DESC
    """, (student_id,)).fetchall()


def get_unpaid_fines_for_student(conn: sqlite3.Connection, student_id: str):
    return conn.execute("""
        SELECT f.*, l.acc_no, b.title
        FROM fines f
        JOIN loans l ON l.id = f.loan_id
        JOIN books b ON b.acc_no = l.acc_no
        WHERE f.student_id=? AND f.status IN ('UNPAID','PARTIAL')
    """, (student_id,)).fetchall()


def get_total_unpaid_fine(conn: sqlite3.Connection, student_id: str) -> float:
    row = conn.execute("""
        SELECT COALESCE(SUM(amount - paid_amount), 0) as total
        FROM fines
        WHERE student_id=? AND status IN ('UNPAID','PARTIAL')
    """, (student_id,)).fetchone()
    return float(row["total"])


def compute_live_fine(conn: sqlite3.Connection, loan_row: sqlite3.Row) -> float:
    """Compute the current fine for an active (unreturned) loan as of today."""
    due_date = date.fromisoformat(loan_row["due_date"])
    today = date.today()
    days = _count_fine_days(
        date.fromisoformat(loan_row["issue_date"]),
        today, due_date, conn
    )
    return _fine_for_days(days, conn)


def issue_book(conn: sqlite3.Connection, student_id: str, acc_no: str,
               issued_by: str = "librarian") -> dict:
    """
    Issue a book to a student.
    Returns {'ok': True, 'loan_id': int} or {'ok': False, 'error': str}
    """
    student = get_student(conn, student_id)
    if not student:
        return {"ok": False, "error": f"Student '{student_id}' not found."}
    if not student["active"]:
        return {"ok": False, "error": "Student account is inactive."}

    book = get_book(conn, acc_no)
    if not book:
        return {"ok": False, "error": f"Book accession '{acc_no}' not found."}
    if book["status"] != "AVAILABLE":
        return {"ok": False, "error": f"Book '{acc_no}' is not available (status: {book['status']})."}

    active_loans = get_active_loans_for_student(conn, student_id)
    max_books = _max_books_setting(conn)
    if len(active_loans) >= max_books:
        return {"ok": False, "error": f"Student already has {len(active_loans)} book(s) issued. Return one first."}

    loan_days = _loan_days_setting(conn)
    today = date.today()
    due = today + timedelta(days=loan_days)

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO loans(acc_no, student_id, issue_date, due_date, issued_by)
            VALUES(?,?,?,?,?)
        """, (acc_no, student_id, today.isoformat(), due.isoformat(), issued_by))
        loan_id = cur.lastrowid
        cur.execute("UPDATE books SET status='ISSUED' WHERE acc_no=?", (acc_no,))
        _audit(conn, issued_by, "ISSUE",
               f"Book {acc_no} issued to {student_id}; due {due.isoformat()}")
        conn.commit()
        return {"ok": True, "loan_id": loan_id, "due_date": due.isoformat()}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}


def return_book(conn: sqlite3.Connection, acc_no: str,
                returned_by: str = "librarian") -> dict:
    """
    Return a book. Calculates and records fine if overdue.
    Returns full result dict.
    """
    book = get_book(conn, acc_no)
    if not book:
        return {"ok": False, "error": f"Book '{acc_no}' not found."}

    loan = conn.execute("""
        SELECT * FROM loans WHERE acc_no=? AND status='ACTIVE'
        ORDER BY id DESC LIMIT 1
    """, (acc_no,)).fetchone()
    if not loan:
        return {"ok": False, "error": f"No active loan found for book '{acc_no}'."}

    today = date.today()
    due_date = date.fromisoformat(loan["due_date"])
    days_late = _count_fine_days(
        date.fromisoformat(loan["issue_date"]), today, due_date, conn
    )
    fine_amount = _fine_for_days(days_late, conn)

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE loans SET return_date=?, status='RETURNED', returned_by=?
            WHERE id=?
        """, (today.isoformat(), returned_by, loan["id"]))
        cur.execute("UPDATE books SET status='AVAILABLE' WHERE acc_no=?", (acc_no,))

        fine_id = None
        if fine_amount > 0:
            cur.execute("""
                INSERT INTO fines(loan_id, student_id, days_late, amount, status)
                VALUES(?,?,?,?,'UNPAID')
            """, (loan["id"], loan["student_id"], days_late, fine_amount))
            fine_id = cur.lastrowid

        _audit(conn, returned_by, "RETURN",
               f"Book {acc_no} returned by {loan['student_id']}; "
               f"fine={fine_amount:.2f}")
        conn.commit()
        return {
            "ok": True,
            "days_late": days_late,
            "fine_amount": fine_amount,
            "fine_id": fine_id,
            "student_id": loan["student_id"],
            "loan_id": loan["id"],
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}


def renew_book(conn: sqlite3.Connection, acc_no: str,
               renewed_by: str = "librarian") -> dict:
    """
    Renew an active loan by loan_days more days.
    - If overdue, fine must be paid first (checked here).
    - No renewal limit.
    """
    book = get_book(conn, acc_no)
    if not book:
        return {"ok": False, "error": f"Book '{acc_no}' not found."}

    loan = conn.execute("""
        SELECT * FROM loans WHERE acc_no=? AND status='ACTIVE'
        ORDER BY id DESC LIMIT 1
    """, (acc_no,)).fetchone()
    if not loan:
        return {"ok": False, "error": f"No active loan for book '{acc_no}'."}

    today = date.today()
    due_date = date.fromisoformat(loan["due_date"])

    if today > due_date:
        # Overdue: check if fine is paid
        unpaid = get_total_unpaid_fine(conn, loan["student_id"])
        if unpaid > 0:
            return {
                "ok": False,
                "error": f"Book is overdue. Pay the outstanding fine of ₹{unpaid:.0f} before renewing."
            }

    loan_days = _loan_days_setting(conn)
    new_due = due_date + timedelta(days=loan_days)

    try:
        conn.execute("""
            UPDATE loans SET due_date=?, renewals_count=renewals_count+1
            WHERE id=?
        """, (new_due.isoformat(), loan["id"]))
        _audit(conn, renewed_by, "RENEW",
               f"Book {acc_no} renewed for {loan['student_id']}; new due {new_due.isoformat()}")
        conn.commit()
        return {
            "ok": True,
            "new_due_date": new_due.isoformat(),
            "renewals_count": loan["renewals_count"] + 1,
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}


def record_fine_payment(conn: sqlite3.Connection, fine_id: int, amount_paid: float,
                        collected_by: str = "librarian") -> dict:
    """Record a full or partial fine payment."""
    fine = conn.execute("SELECT * FROM fines WHERE id=?", (fine_id,)).fetchone()
    if not fine:
        return {"ok": False, "error": "Fine record not found."}

    total_paid = fine["paid_amount"] + amount_paid
    if total_paid >= fine["amount"]:
        new_status = "PAID"
        total_paid = fine["amount"]
    else:
        new_status = "PARTIAL"

    try:
        today = date.today().isoformat()
        conn.execute("""
            UPDATE fines SET paid_amount=?, status=?, paid_on=? WHERE id=?
        """, (total_paid, new_status, today, fine_id))
        _audit(conn, collected_by, "FINE_PAYMENT",
               f"Fine {fine_id}: paid ₹{amount_paid:.2f}; status={new_status}")
        conn.commit()
        return {"ok": True, "new_status": new_status, "total_paid": total_paid}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}


def waive_fine(conn: sqlite3.Connection, fine_id: int, waived_by: str) -> dict:
    """Waive a fine (admin only)."""
    try:
        conn.execute(
            "UPDATE fines SET status='WAIVED', paid_on=date('now') WHERE id=?",
            (fine_id,)
        )
        _audit(conn, waived_by, "FINE_WAIVE", f"Fine {fine_id} waived")
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}


def get_book_copies_info(conn: sqlite3.Connection, title: str) -> dict:
    """Return total copies, available copies, and issued copies for a title."""
    rows = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM books
        WHERE LOWER(title) = LOWER(?)
        GROUP BY status
    """, (title,)).fetchall()
    result = {"total": 0, "available": 0, "issued": 0, "lost": 0}
    for r in rows:
        result["total"] += r["cnt"]
        s = r["status"].lower()
        if s in result:
            result[s] = r["cnt"]
    return result


def search_books(conn: sqlite3.Connection, query: str):
    """Search books by accession number, title, or author. Returns list of books with who has them."""
    q = f"%{query}%"
    return conn.execute("""
        SELECT b.*,
               l.student_id as held_by_student,
               s.name as held_by_name,
               l.issue_date,
               l.due_date
        FROM books b
        LEFT JOIN loans l ON l.acc_no = b.acc_no AND l.status = 'ACTIVE'
        LEFT JOIN students s ON s.student_id = l.student_id
        WHERE b.acc_no LIKE ? OR LOWER(b.title) LIKE LOWER(?) OR LOWER(b.author) LIKE LOWER(?)
        ORDER BY b.title, b.acc_no
    """, (q, q, q)).fetchall()


def authenticate_user(conn: sqlite3.Connection, username: str, password: str) -> Optional[sqlite3.Row]:
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=? AND active=1",
        (username, pw_hash)
    ).fetchone()


def change_password(conn: sqlite3.Connection, username: str,
                    old_password: str, new_password: str) -> dict:
    if not authenticate_user(conn, username, old_password):
        return {"ok": False, "error": "Current password is incorrect."}
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
    conn.execute("UPDATE users SET password_hash=? WHERE username=?", (new_hash, username))
    conn.commit()
    return {"ok": True}


def get_overdue_loans(conn: sqlite3.Connection):
    """Return all active loans that are past their due date."""
    today = date.today().isoformat()
    return conn.execute("""
        SELECT l.*, b.title, b.author, s.name as student_name, s.course, s.year, s.phone
        FROM loans l
        JOIN books b ON b.acc_no = l.acc_no
        JOIN students s ON s.student_id = l.student_id
        WHERE l.status='ACTIVE' AND l.due_date < ?
        ORDER BY l.due_date
    """, (today,)).fetchall()


def get_dashboard_stats(conn: sqlite3.Connection) -> dict:
    today = date.today().isoformat()
    issued_today = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE issue_date=?", (today,)
    ).fetchone()[0]
    returned_today = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE return_date=?", (today,)
    ).fetchone()[0]
    overdue_count = conn.execute(
        "SELECT COUNT(*) FROM loans WHERE status='ACTIVE' AND due_date < ?", (today,)
    ).fetchone()[0]
    total_fines_due = conn.execute(
        "SELECT COALESCE(SUM(amount-paid_amount),0) FROM fines WHERE status IN ('UNPAID','PARTIAL')"
    ).fetchone()[0]
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    books_issued = conn.execute(
        "SELECT COUNT(*) FROM books WHERE status='ISSUED'"
    ).fetchone()[0]
    total_students = conn.execute(
        "SELECT COUNT(*) FROM students WHERE active=1"
    ).fetchone()[0]
    return {
        "issued_today": issued_today,
        "returned_today": returned_today,
        "overdue_count": overdue_count,
        "total_fines_due": float(total_fines_due),
        "total_books": total_books,
        "books_issued": books_issued,
        "books_available": total_books - books_issued,
        "total_students": total_students,
    }
