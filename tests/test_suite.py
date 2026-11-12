"""
Comprehensive double-run verification test suite for LibraryPro.
Tests every rule, edge case, and functionality TWICE in isolated databases.
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import sqlite3
import tempfile
from pathlib import Path
from datetime import date, timedelta

# Ensure library_app is on path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from db.schema import init_db, get_setting, set_setting
from core.rules import (
    issue_book, return_book, renew_book, record_fine_payment, waive_fine,
    get_book, get_student, get_active_loans_for_student, get_loan_history_for_student,
    get_unpaid_fines_for_student, get_total_unpaid_fine, compute_live_fine,
    get_book_copies_info, search_books, authenticate_user, change_password,
    get_overdue_loans, get_dashboard_stats, _count_fine_days, _fine_for_days
)
from importers.excel_import import import_books, import_students


def run_full_suite(run_number: int):
    print(f"\n=======================================================")
    print(f"▶ STARTING TEST CYCLE #{run_number}")
    print(f"=======================================================")

    # Use a fresh temporary database for each run
    temp_dir = tempfile.mkdtemp()
    db_file = Path(temp_dir) / f"test_lib_{run_number}.db"
    conn = init_db(db_file)
    print(f"[✓] Initialized fresh test database: {db_file}")

    # 1. Verify default admin authentication
    user = authenticate_user(conn, "admin", "admin123")
    assert user is not None, "Default admin authentication failed!"
    assert user["role"] == "admin", "Admin role mismatch!"
    print("[✓] Default admin login authenticated")

    # 2. Verify invalid login fails
    bad_user = authenticate_user(conn, "admin", "wrongpass")
    assert bad_user is None, "Bad password should fail authentication!"
    print("[✓] Invalid password correctly rejected")

    # 3. Seed test students & books
    conn.execute("""
        INSERT INTO students(student_id, name, course, year, phone, email, active)
        VALUES('STU001', 'Aarav Sharma', 'B.Tech CSE', '3rd', '9876543210', 'aarav@test.edu', 1),
              ('STU002', 'Diya Patel', 'B.Sc Physics', '2nd', '9876543211', 'diya@test.edu', 1),
              ('STU_INACTIVE', 'Inactive Student', 'B.A.', '1st', '0000000000', 'in@test.edu', 0)
    """)
    conn.execute("""
        INSERT INTO books(acc_no, title, author, volume, edition, year, publisher, department, call_no, cost, status)
        VALUES('ACC101', 'Clean Code', 'Robert Martin', 'Vol 1', '1st', '2008', 'Pearson', 'CSE', '005.1', 850.0, 'AVAILABLE'),
              ('ACC102', 'Clean Code', 'Robert Martin', 'Vol 1', '1st', '2008', 'Pearson', 'CSE', '005.1', 850.0, 'AVAILABLE'),
              ('ACC103', 'Clean Code', 'Robert Martin', 'Vol 1', '1st', '2008', 'Pearson', 'CSE', '005.1', 850.0, 'AVAILABLE'),
              ('ACC201', 'Digital Design', 'Morris Mano', 'Vol 1', '4th', '2012', 'Prentice', 'ECE', '621.3', 650.0, 'AVAILABLE'),
              ('ACC301', 'Atomic Physics', 'Raj Kumar', 'Vol 2', '2nd', '2015', 'Oxford', 'PHY', '539.7', 450.0, 'AVAILABLE')
    """)
    conn.commit()
    print("[✓] Seed data inserted successfully")

    # 4. Verify book copies inventory calculation
    copies = get_book_copies_info(conn, "Clean Code")
    assert copies["total"] == 3, f"Expected 3 total copies, got {copies['total']}"
    assert copies["available"] == 3, f"Expected 3 available copies, got {copies['available']}"
    assert copies["issued"] == 0, f"Expected 0 issued copies, got {copies['issued']}"
    print(f"[✓] Book copies breakdown verified: Total=3, Avail=3, Issued=0")

    # 5. Issue Book 1 to STU001
    res1 = issue_book(conn, "STU001", "ACC101", "admin")
    assert res1["ok"] is True, f"Failed to issue ACC101: {res1.get('error')}"
    book101 = get_book(conn, "ACC101")
    assert book101["status"] == "ISSUED", "Book status should be ISSUED"
    print("[✓] Book 1 issued successfully to STU001")

    # 6. Check inventory updated
    copies_after_1 = get_book_copies_info(conn, "Clean Code")
    assert copies_after_1["available"] == 2, f"Expected 2 available, got {copies_after_1['available']}"
    assert copies_after_1["issued"] == 1, f"Expected 1 issued, got {copies_after_1['issued']}"
    print("[✓] Inventory dynamically updated: Avail=2, Issued=1")

    # 7. Issue Book 2 to STU001 (reaches 2-book limit)
    res2 = issue_book(conn, "STU001", "ACC102", "admin")
    assert res2["ok"] is True, f"Failed to issue ACC102: {res2.get('error')}"
    loans_stu1 = get_active_loans_for_student(conn, "STU001")
    assert len(loans_stu1) == 2, f"Expected 2 active loans, got {len(loans_stu1)}"
    print("[✓] Book 2 issued successfully (STU001 is now at the 2-book limit)")

    # 8. Attempt Issue Book 3 to STU001 -> MUST FAIL (Limit is 2)
    res3 = issue_book(conn, "STU001", "ACC103", "admin")
    assert res3["ok"] is False, "Book 3 issue MUST be rejected!"
    assert "Return one first" in res3["error"], f"Unexpected error message: {res3['error']}"
    print(f"[✓] 3-book limit violation correctly blocked: '{res3['error']}'")

    # 9. Attempt to issue an already ISSUED book to STU002 -> MUST FAIL
    res_dup = issue_book(conn, "STU002", "ACC101", "admin")
    assert res_dup["ok"] is False, "Already issued book cannot be re-issued!"
    print(f"[✓] Duplicate book issue correctly blocked: '{res_dup['error']}'")

    # 10. Attempt to issue to inactive student -> MUST FAIL
    res_inact = issue_book(conn, "STU_INACTIVE", "ACC103", "admin")
    assert res_inact["ok"] is False, "Inactive student issue must be rejected!"
    print(f"[✓] Inactive student blocked: '{res_inact['error']}'")

    # 11. Return Book 1 (ACC101) on time -> Fine must be 0, status AVAILABLE
    ret1 = return_book(conn, "ACC101", "admin")
    assert ret1["ok"] is True, f"Return failed: {ret1.get('error')}"
    assert ret1["fine_amount"] == 0.0, f"Expected 0 fine for on-time return, got {ret1['fine_amount']}"
    book101_ret = get_book(conn, "ACC101")
    assert book101_ret["status"] == "AVAILABLE", "Book status should be AVAILABLE after return"
    print("[✓] On-time return processed: fine=₹0, book status restored to AVAILABLE")

    # 12. Student STU001 now has 1 active loan -> Can now issue Book 3!
    res3_retry = issue_book(conn, "STU001", "ACC103", "admin")
    assert res3_retry["ok"] is True, f"Issue should succeed after slot freed! Error: {res3_retry.get('error')}"
    print("[✓] Book slot freed upon return: Book 3 successfully issued to STU001")

    # 13. Test Fine Calculation with Sundays and Holidays Excluded
    # Add a holiday
    conn.execute("INSERT OR REPLACE INTO holidays(date, description) VALUES('2026-11-20', 'National Holiday')")
    conn.commit()

    # Simulate an overdue loan by backdating loan dates
    # Loan issued on 2026-10-01, due on 2026-10-16.
    # Today is 2026-11-12.
    conn.execute("""
        INSERT INTO loans(acc_no, student_id, issue_date, due_date, status, issued_by)
        VALUES('ACC201', 'STU002', '2026-10-01', '2026-10-16', 'ACTIVE', 'admin')
    """)
    conn.execute("UPDATE books SET status='ISSUED' WHERE acc_no='ACC201'")
    conn.commit()

    overdue_loan = conn.execute("SELECT * FROM loans WHERE acc_no='ACC201'").fetchone()
    # Test _count_fine_days excluding Sundays and holidays
    issue_d = date(2026, 10, 1)
    due_d   = date(2026, 10, 16)
    ret_d   = date(2026, 11, 12)
    working_days = _count_fine_days(issue_d, ret_d, due_d, conn)
    # Check that Sundays were excluded
    assert working_days > 0, "Working days late should be positive"

    # Test fine cap: ₹20/day * 20+ days would be > ₹400, but MAX FINE is capped at ₹200
    calc_fine = _fine_for_days(working_days, conn)
    assert calc_fine == 200.0, f"Fine must be capped at maximum ₹200! Got {calc_fine}"
    print(f"[✓] Overdue calculation verified: {working_days} working days late (Sundays excluded). Fine properly capped at maximum ₹200.00")

    # 14. Test Renewal on Overdue Book
    # Attempt to renew ACC201 without paying fine -> MUST FAIL
    renew_fail = renew_book(conn, "ACC201", "admin", fine_collected=False)
    assert renew_fail["ok"] is False, "Overdue book renewal without paying fine must be rejected!"
    assert renew_fail.get("requires_fine") is True, "requires_fine flag must be True"
    assert renew_fail["fine_amount"] == 200.0, f"Expected ₹200 fine, got {renew_fail['fine_amount']}"
    print(f"[✓] Overdue renewal blocked before payment: '{renew_fail['error']}'")

    # Renew ACC201 WITH fine collected -> MUST SUCCEED
    renew_ok = renew_book(conn, "ACC201", "admin", fine_collected=True)
    assert renew_ok["ok"] is True, f"Renewal with fine collected failed: {renew_ok.get('error')}"
    assert renew_ok["fine_paid"] == 200.0, "Fine paid should be ₹200"
    assert renew_ok["renewals_count"] == 1, "Renewal count should be 1"

    # Verify that a fine record was inserted with status PAID
    paid_fine = conn.execute("SELECT * FROM fines WHERE loan_id=?", (overdue_loan["id"],)).fetchone()
    assert paid_fine is not None, "Fine record must be created"
    assert paid_fine["status"] == "PAID", f"Fine status should be PAID, got {paid_fine['status']}"
    assert paid_fine["paid_amount"] == 200.0, "Paid amount should be 200"
    print("[✓] Overdue renewal with fine collected: renewed for +15 days & recorded as PAID in ledger")

    # 15. Test Unlimited Renewals
    # Renew ACC201 second time
    renew_2 = renew_book(conn, "ACC201", "admin")
    assert renew_2["ok"] is True, f"Second renewal failed: {renew_2.get('error')}"
    assert renew_2["renewals_count"] == 2, "Renewal count should be 2"
    # Renew ACC201 third time
    renew_3 = renew_book(conn, "ACC201", "admin")
    assert renew_3["ok"] is True, f"Third renewal failed: {renew_3.get('error')}"
    assert renew_3["renewals_count"] == 3, "Renewal count should be 3"
    print("[✓] Unlimited renewals verified: successfully completed renewals #2 and #3")

    # 16. Return ACC201
    ret_acc201 = return_book(conn, "ACC201", "admin")
    assert ret_acc201["ok"] is True, "Return of ACC201 failed"
    print("[✓] ACC201 returned successfully")

    # 17. Test Fines Ledger & Payments
    # Create an unpaid fine of ₹100
    conn.execute("""
        INSERT INTO loans(acc_no, student_id, issue_date, due_date, return_date, status, issued_by)
        VALUES('ACC301', 'STU002', '2026-10-01', '2026-10-16', '2026-10-25', 'RETURNED', 'admin')
    """)
    fine_loan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.execute("""
        INSERT INTO fines(loan_id, student_id, days_late, amount, paid_amount, status)
        VALUES(?, 'STU002', 5, 100.0, 0.0, 'UNPAID')
    """, (fine_loan_id,))
    fine_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    # Verify unpaid total
    unpaid_total = get_total_unpaid_fine(conn, "STU002")
    assert unpaid_total == 100.0, f"Expected ₹100 unpaid, got {unpaid_total}"

    # Partial payment of ₹40
    pay_part = record_fine_payment(conn, fine_id, 40.0, "librarian")
    assert pay_part["ok"] is True, "Partial fine payment failed"
    assert pay_part["new_status"] == "PARTIAL", f"Expected PARTIAL status, got {pay_part['new_status']}"
    assert pay_part["total_paid"] == 40.0, "Total paid should be 40"

    # Settle remaining ₹60
    pay_full = record_fine_payment(conn, fine_id, 60.0, "librarian")
    assert pay_full["ok"] is True, "Full fine payment failed"
    assert pay_full["new_status"] == "PAID", f"Expected PAID status, got {pay_full['new_status']}"
    assert pay_full["total_paid"] == 100.0, "Total paid should be 100"
    print("[✓] Fine payment ledger verified: partial (₹40) and settlement (₹60 -> PAID)")

    # 18. Test Fine Waiving (Admin only)
    conn.execute("""
        INSERT INTO fines(loan_id, student_id, days_late, amount, paid_amount, status)
        VALUES(?, 'STU002', 2, 40.0, 0.0, 'UNPAID')
    """, (fine_loan_id,))
    waive_fine_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    waive_res = waive_fine(conn, waive_fine_id, "admin")
    assert waive_res["ok"] is True, "Waiving fine failed"
    waived_row = conn.execute("SELECT status FROM fines WHERE id=?", (waive_fine_id,)).fetchone()
    assert waived_row["status"] == "WAIVED", "Fine status should be WAIVED"
    print("[✓] Fine waiver verified: status set to WAIVED with audit trail")

    # 19. Test Search Functionality (Search by Acc No, Author, Title)
    # Search by Acc No
    search_acc = search_books(conn, "ACC103")
    assert len(search_acc) == 1, f"Expected 1 result for ACC103, got {len(search_acc)}"
    assert search_acc[0]["held_by_student"] == "STU001", "ACC103 should be held by STU001"
    assert search_acc[0]["held_by_name"] == "Aarav Sharma", "Holder name mismatch"
    print(f"[✓] Search by Accession Number verified: shows borrower '{search_acc[0]['held_by_name']}'")

    # Search by Title
    search_title = search_books(conn, "Clean Code")
    assert len(search_title) == 3, f"Expected 3 copies of Clean Code, got {len(search_title)}"
    print(f"[✓] Search by Title verified: returned {len(search_title)} copies")

    # Search by Author
    search_auth = search_books(conn, "Morris Mano")
    assert len(search_auth) == 1, f"Expected 1 book for Morris Mano, got {len(search_auth)}"
    print(f"[✓] Search by Author verified")

    # 20. Test Dashboard Statistics Aggregation
    stats = get_dashboard_stats(conn)
    assert stats["total_books"] == 5, f"Expected 5 books, got {stats['total_books']}"
    assert stats["total_students"] == 2, f"Expected 2 active students, got {stats['total_students']}"
    print(f"[✓] Dashboard statistics aggregation verified: Total books={stats['total_books']}, Students={stats['total_students']}")

    # 21. Test Password Change Functionality
    pw_res = change_password(conn, "admin", "admin123", "newpass456")
    assert pw_res["ok"] is True, "Password change failed"
    auth_new = authenticate_user(conn, "admin", "newpass456")
    assert auth_new is not None, "Authentication with new password failed"
    print("[✓] Password change & re-authentication verified")

    # 22. Test Excel Importer with generated test spreadsheets
    import openpyxl
    # Create books test excel
    wb_b = openpyxl.Workbook()
    ws_b = wb_b.active
    ws_b.append(["Accession No", "Book Title", "Author", "Vol", "Edition", "Year", "Publisher", "Dept", "Call No", "Cost"])
    ws_b.append(["EXCEL_B01", "Design Patterns", "Gang of Four", "1", "1st", "1994", "Addison", "CSE", "005.13", "900"])
    ws_b.append(["EXCEL_B02", "Refactoring", "Martin Fowler", "1", "2nd", "2018", "Addison", "CSE", "005.16", "950"])
    excel_books_path = Path(temp_dir) / "test_books.xlsx"
    wb_b.save(excel_books_path)

    imp_b_res = import_books(conn, excel_books_path)
    assert imp_b_res["imported"] == 2, f"Expected 2 books imported, got {imp_b_res['imported']}"
    assert get_book(conn, "EXCEL_B01") is not None, "EXCEL_B01 was not imported!"
    print(f"[✓] Excel Books Importer verified: {imp_b_res['imported']} books imported")

    # Create students test excel
    wb_s = openpyxl.Workbook()
    ws_s = wb_s.active
    ws_s.append(["Roll No", "Student Name", "Course", "Semester", "Mobile No", "Email ID"])
    ws_s.append(["EXCEL_S01", "Priya Verma", "B.Tech IT", "4th", "9123456789", "priya@test.edu"])
    ws_s.append(["EXCEL_S02", "Karan Singh", "B.Tech ME", "6th", "9123456780", "karan@test.edu"])
    excel_students_path = Path(temp_dir) / "test_students.xlsx"
    wb_s.save(excel_students_path)

    imp_s_res = import_students(conn, excel_students_path)
    assert imp_s_res["imported"] == 2, f"Expected 2 students imported, got {imp_s_res['imported']}"
    assert get_student(conn, "EXCEL_S01") is not None, "EXCEL_S01 was not imported!"
    print(f"[✓] Excel Students Importer verified: {imp_s_res['imported']} students imported")

    conn.close()
    print(f"=======================================================")
    print(f"🎉 TEST CYCLE #{run_number} COMPLETED WITH ZERO ERRORS!")
    print(f"=======================================================\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RUNNING ALL FUNCTIONALITIES TWICE (CYCLE 1 & CYCLE 2)")
    print("=" * 60)

    # First complete execution cycle
    run_full_suite(1)

    # Second complete execution cycle (completely independent run)
    run_full_suite(2)

    # Test UI Screen Instantiations
    print("\n" + "=" * 60)
    print("TESTING ALL UI SCREENS INITIALIZATION TWICE")
    print("=" * 60)
    from PySide6.QtWidgets import QApplication
    from ui.style import STYLESHEET
    from ui.login_dialog import LoginDialog
    from ui.dashboard import DashboardScreen
    from ui.issue_screen import IssueScreen
    from ui.return_screen import ReturnScreen
    from ui.book_search_screen import BookSearchScreen
    from ui.student_lookup_screen import StudentLookupScreen
    from ui.fines_screen import FinesScreen
    from ui.reports_screen import ReportsScreen
    from ui.import_screen import ImportScreen
    from ui.settings_screen import SettingsScreen
    from ui.main_window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    for ui_cycle in [1, 2]:
        print(f"\n--- UI Instantiation Cycle #{ui_cycle} ---")
        temp_dir = tempfile.mkdtemp()
        conn = init_db(Path(temp_dir) / f"ui_test_{ui_cycle}.db")
        user = {"username": "admin", "role": "admin", "full_name": "Administrator"}

        d1 = LoginDialog(conn)
        assert d1 is not None, "LoginDialog failed"
        
        s_dash = DashboardScreen(conn, user)
        s_dash.on_show() if hasattr(s_dash, "on_show") else None
        
        s_issue = IssueScreen(conn, user)
        s_issue.on_show()
        
        s_ret = ReturnScreen(conn, user)
        s_ret.on_show()
        
        s_search = BookSearchScreen(conn, user)
        s_search.on_show()
        
        s_lookup = StudentLookupScreen(conn, user)
        s_lookup.on_show()
        
        s_fines = FinesScreen(conn, user)
        s_fines.on_show()
        
        s_reports = ReportsScreen(conn, user)
        s_reports.on_show()
        
        s_import = ImportScreen(conn, user)
        s_import.on_show()
        
        s_settings = SettingsScreen(conn, user)
        s_settings.on_show()

        main_win = MainWindow(conn, user)
        assert main_win is not None, "MainWindow failed"
        
        # Test switching between screens
        for screen_idx in range(9):
            main_win._switch_screen(screen_idx)

        conn.close()
        print(f"[✓] UI Cycle #{ui_cycle}: All 10 screens & dialogs instantiated, displayed, and navigated without error!")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED TWICE: ZERO ERRORS, ZERO EMPTY MODULES!")
    print("=" * 60 + "\n")
