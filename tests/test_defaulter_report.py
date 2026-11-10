
import sys
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "engine"))

from defaulter_report import generate_report


def make_transaction(flat_id, transaction_type, amount,
                     transaction_date, principal_paid="0.00"):

    return {
        "flat_id": flat_id,
        "date": transaction_date,
        "transaction_type": transaction_type,
        "amount": str(amount),
        "interest_paid": "0.00",
        "principal_paid": str(principal_paid),
        "advance_balance": "0.00",
        "details": "Test transaction"
    }


def test_two_month_overdue_rule():
    transactions = [
        make_transaction(
            "TEST-001", "BILL", "10000.00", "2026-01-01"
        )
    ]

    # Before the two-month overdue date
    rows = generate_report(transactions, date(2026, 3, 14))
    assert rows[0]["status"] == "NOT A DEFAULTER"

    # On the two-month overdue date
    rows = generate_report(transactions, date(2026, 3, 15))
    assert rows[0]["status"] == "DEFAULTER"


def test_becomes_defaulter_after_two_months():
    transactions = [
        make_transaction(
            "TEST-002", "BILL", "10000.00", "2026-01-01"
        )
    ]

    rows = generate_report(transactions, date(2026, 3, 16))

    assert rows[0]["status"] == "DEFAULTER"
    assert rows[0]["overdue_principal"] == "10000.00"


def test_partial_payment_reduces_overdue_principal():
    transactions = [
        make_transaction(
            "TEST-003", "BILL", "10000.00", "2026-01-01"
        ),
        make_transaction(
            "TEST-003", "PAYMENT", "4000.00",
            "2026-03-20", "4000.00"
        )
    ]

    rows = generate_report(transactions, date(2026, 3, 21))

    assert rows[0]["status"] == "DEFAULTER"
    assert rows[0]["overdue_principal"] == "6000.00"


def test_full_payment_removes_defaulter_status():
    transactions = [
        make_transaction(
            "TEST-004", "BILL", "10000.00", "2026-01-01"
        ),
        make_transaction(
            "TEST-004", "PAYMENT", "10000.00",
            "2026-03-20", "10000.00"
        )
    ]

    rows = generate_report(transactions, date(2026, 3, 21))

    assert rows[0]["status"] == "NOT A DEFAULTER"
    assert rows[0]["overdue_principal"] == "0.00"


def test_advance_applied_only_reduces_principal_portion():
    transactions = [
        make_transaction(
            "TEST-005", "BILL", "10000.00", "2026-01-01"
        ),
        make_transaction(
            "TEST-005", "ADVANCE_APPLIED", "5000.00",
            "2026-03-20", "3000.00"
        )
    ]

    rows = generate_report(transactions, date(2026, 3, 21))

    assert rows[0]["overdue_principal"] == "7000.00"


if __name__ == "__main__":
    tests = [
        test_two_month_overdue_rule,
        test_becomes_defaulter_after_two_months,
        test_partial_payment_reduces_overdue_principal,
        test_full_payment_removes_defaulter_status,
        test_advance_applied_only_reduces_principal_portion
    ]

    print("\nDEFAULTER REPORT TESTS")
    print("----------------------")

    for test in tests:
        test()
        print("PASSED:", test.__name__)

    print("\nAll 5 defaulter tests passed!")
