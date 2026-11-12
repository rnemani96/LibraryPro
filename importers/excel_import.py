"""
Excel import utilities for books (accession register) and students.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional


def _try_openpyxl(path: Path):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        rows.append(dict(zip(headers, row)))
    return rows


def _normalise(val) -> str:
    if val is None:
        return ""
    return str(val).strip()


# ─── Books import ─────────────────────────────────────────────────────────────

BOOK_COLUMN_ALIASES = {
    "acc_no":    ["acc no", "acc. no", "acc.no", "accession no", "accession number", "accno"],
    "title":     ["title", "book title", "name"],
    "author":    ["author", "authors", "writer"],
    "volume":    ["vol", "volume", "vol."],
    "edition":   ["edition", "ed", "ed."],
    "year":      ["year", "pub year", "year of publication"],
    "publisher": ["publisher", "pub", "publication"],
    "department":["department", "dept", "dept.", "subject"],
    "call_no":   ["call no", "call number", "call_no", "class no"],
    "cost":      ["cost", "price", "value"],
}


def _map_header(header: str, aliases: dict) -> Optional[str]:
    h = header.lower().strip()
    for field, synonyms in aliases.items():
        if h in synonyms or h == field:
            return field
    return None


def import_books(conn: sqlite3.Connection, path: Path,
                 on_progress=None) -> dict:
    """
    Import books from an Excel file.
    Returns {'imported': int, 'skipped': int, 'errors': list[str]}
    """
    try:
        rows = _try_openpyxl(path)
    except Exception as e:
        return {"imported": 0, "skipped": 0, "errors": [f"Cannot read file: {e}"]}

    if not rows:
        return {"imported": 0, "skipped": 0, "errors": ["File is empty."]}

    # Build column mapping
    sample_headers = list(rows[0].keys())
    col_map = {}
    for h in sample_headers:
        f = _map_header(h, BOOK_COLUMN_ALIASES)
        if f:
            col_map[h] = f

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(rows, start=2):
        mapped = {}
        for h, f in col_map.items():
            mapped[f] = _normalise(row.get(h))

        acc_no = mapped.get("acc_no", "")
        title  = mapped.get("title", "")
        author = mapped.get("author", "")

        if not acc_no or not title:
            skipped += 1
            continue

        try:
            cost = float(mapped.get("cost", 0) or 0)
        except ValueError:
            cost = 0.0

        try:
            conn.execute("""
                INSERT INTO books(acc_no,title,author,volume,edition,year,
                                  publisher,department,call_no,cost)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(acc_no) DO UPDATE SET
                    title=excluded.title, author=excluded.author,
                    volume=excluded.volume, edition=excluded.edition,
                    year=excluded.year, publisher=excluded.publisher,
                    department=excluded.department, call_no=excluded.call_no,
                    cost=excluded.cost
            """, (acc_no, title, author,
                  mapped.get("volume",""), mapped.get("edition",""),
                  mapped.get("year",""), mapped.get("publisher",""),
                  mapped.get("department",""), mapped.get("call_no",""),
                  cost))
            imported += 1
        except Exception as e:
            errors.append(f"Row {i} ({acc_no}): {e}")
            skipped += 1

        if on_progress and i % 50 == 0:
            on_progress(i, len(rows))

    conn.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}


# ─── Students import ──────────────────────────────────────────────────────────

STUDENT_COLUMN_ALIASES = {
    "student_id": ["student id", "id", "student_id", "roll no", "roll number", "enrollment no"],
    "name":       ["name", "student name", "full name"],
    "course":     ["course", "branch", "stream", "program", "programme"],
    "year":       ["year", "class", "semester", "sem"],
    "phone":      ["phone", "mobile", "contact", "phone no", "mobile no"],
    "email":      ["email", "e-mail", "email id"],
}


def import_students(conn: sqlite3.Connection, path: Path,
                    on_progress=None) -> dict:
    """
    Import students from an Excel file.
    """
    try:
        rows = _try_openpyxl(path)
    except Exception as e:
        return {"imported": 0, "skipped": 0, "errors": [f"Cannot read file: {e}"]}

    if not rows:
        return {"imported": 0, "skipped": 0, "errors": ["File is empty."]}

    sample_headers = list(rows[0].keys())
    col_map = {}
    for h in sample_headers:
        f = _map_header(h, STUDENT_COLUMN_ALIASES)
        if f:
            col_map[h] = f

    imported = 0
    skipped = 0
    errors = []

    for i, row in enumerate(rows, start=2):
        mapped = {}
        for h, f in col_map.items():
            mapped[f] = _normalise(row.get(h))

        student_id = mapped.get("student_id", "")
        name       = mapped.get("name", "")

        if not student_id or not name:
            skipped += 1
            continue

        try:
            conn.execute("""
                INSERT INTO students(student_id,name,course,year,phone,email)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(student_id) DO UPDATE SET
                    name=excluded.name, course=excluded.course,
                    year=excluded.year, phone=excluded.phone,
                    email=excluded.email
            """, (student_id, name,
                  mapped.get("course",""), mapped.get("year",""),
                  mapped.get("phone",""), mapped.get("email","")))
            imported += 1
        except Exception as e:
            errors.append(f"Row {i} ({student_id}): {e}")
            skipped += 1

        if on_progress and i % 50 == 0:
            on_progress(i, len(rows))

    conn.commit()
    return {"imported": imported, "skipped": skipped, "errors": errors}
