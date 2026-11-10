
import csv
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

REPORT_DATES = [
    date(2026, 6, 20),
    date(2026, 11, 3)
]

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP
    )


def add_months(original_date, months):
    """Add calendar months while handling month-end dates."""

    month_index = original_date.month - 1 + months
    year = original_date.year + month_index // 12
    month = month_index % 12 + 1

    import calendar

    day = min(
        original_date.day,
        calendar.monthrange(year, month)[1]
    )

    return date(year, month, day)


def read_transactions():
    file_path = OUTPUT_DIR / "ledger_transactions.csv"

    with open(file_path, "r", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def apply_to_oldest_bills(bills, amount):
    """Reduce principal from the oldest outstanding bill first."""

    remaining = money(amount)

    for bill in bills:
        if remaining <= ZERO:
            break

        if bill["balance"] <= ZERO:
            continue

        applied = min(remaining, bill["balance"])

        bill["balance"] = money(
            bill["balance"] - applied
        )

        remaining = money(remaining - applied)


def generate_report(transactions, report_date):
    """Reconstruct outstanding principal as of the report date."""

    flat_bills = {}
    all_flat_ids = set()

    for transaction in transactions:

        flat_id = transaction["flat_id"]
        all_flat_ids.add(flat_id)

        transaction_date = datetime.strptime(
            transaction["date"], "%Y-%m-%d"
        ).date()

        if transaction_date > report_date:
            continue

        transaction_type = transaction["transaction_type"]

        if flat_id not in flat_bills:
            flat_bills[flat_id] = []

        if transaction_type == "BILL":

            due_date = transaction_date.replace(day=15)

            flat_bills[flat_id].append({
                "bill_date": transaction_date,
                "due_date": due_date,
                "overdue_date": add_months(due_date, 2),
                "balance": money(transaction["amount"])
            })

        elif transaction_type == "PAYMENT":

            # Only the principal portion reduces bill principal.
            principal_paid = money(
                transaction.get("principal_paid") or ZERO
            )

            apply_to_oldest_bills(
                flat_bills[flat_id],
                principal_paid
            )

        elif transaction_type == "ADVANCE_APPLIED":

            # Do not subtract the full advance amount.
            # Interest is settled separately.
            principal_paid = money(
                transaction.get("principal_paid") or ZERO
            )

            apply_to_oldest_bills(
                flat_bills[flat_id],
                principal_paid
            )

        # BILL_CREDIT is not subtracted directly.
        # Its effect is already recorded in ADVANCE_APPLIED.

    report_rows = []

    for flat_id in sorted(all_flat_ids):

        bills = flat_bills.get(flat_id, [])

        total_outstanding = money(
            sum(
                (bill["balance"] for bill in bills),
                ZERO
            )
        )

        overdue_bills = [
            bill for bill in bills
            if bill["balance"] > ZERO
            and bill["overdue_date"] <= report_date
        ]

        overdue_principal = money(
            sum(
                (bill["balance"] for bill in overdue_bills),
                ZERO
            )
        )

        oldest_due_date = ""

        if overdue_bills:
            oldest_due_date = min(
                bill["due_date"] for bill in overdue_bills
            ).isoformat()

        status = (
            "DEFAULTER"
            if overdue_principal > ZERO
            else "NOT A DEFAULTER"
        )

        report_rows.append({
            "flat_id": flat_id,
            "report_date": report_date.isoformat(),
            "status": status,
            "overdue_bill_count": len(overdue_bills),
            "overdue_principal": str(overdue_principal),
            "total_principal_outstanding": str(total_outstanding),
            "oldest_overdue_due_date": oldest_due_date
        })

    return report_rows


def save_report(rows, report_date):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"defaulters_{report_date.isoformat()}.csv"

    output_file = OUTPUT_DIR / filename

    fieldnames = [
        "flat_id",
        "report_date",
        "status",
        "overdue_bill_count",
        "overdue_principal",
        "total_principal_outstanding",
        "oldest_overdue_due_date"
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_file


def main():

    transactions = read_transactions()

    print("\nDEFAULTER REPORT MODULE")
    print("-----------------------")

    for report_date in REPORT_DATES:

        rows = generate_report(
            transactions,
            report_date
        )

        output_file = save_report(
            rows,
            report_date
        )

        defaulters = [
            row for row in rows
            if row["status"] == "DEFAULTER"
        ]

        total_overdue = money(
            sum(
                (
                    Decimal(row["overdue_principal"])
                    for row in defaulters
                ),
                ZERO
            )
        )

        print("\nReport date:", report_date)
        print("Total flats:", len(rows))
        print("Number of defaulters:", len(defaulters))
        print("Total overdue principal: Rs.", total_overdue)
        print("Report saved:", output_file)

        print("\nFirst five defaulter records:")

        for row in defaulters[:5]:
            print(row)


if __name__ == "__main__":
    main()
