
import csv
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    return Decimal(str(value)).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def read_csv(filename, folder=INPUT_DIR):
    with open(folder / filename, "r", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def read_interest_rate():
    rates = read_csv("rates.csv")

    eligible = [
        row for row in rates
        if row["rate_code"] == "INTEREST_PA_PCT"
    ]

    if not eligible:
        raise ValueError("Interest rate not found in rates.csv")

    latest = max(eligible, key=lambda row: row["effective_from"])
    return Decimal(latest["value"])


def get_report_date():
    dates = []

    with open(INPUT_DIR / "commands.txt", "r", encoding="utf-8-sig") as file:
        for line in file:
            parts = line.strip().split("|")

            if parts[0] in ("PRINT_LEDGER", "PRINT_DEFAULTERS"):
                dates.append(date.fromisoformat(parts[-1]))

    return max(dates) if dates else date.today()


def load_special_commands():
    advances = []
    transfer_fees = []

    with open(INPUT_DIR / "commands.txt", "r", encoding="utf-8-sig") as file:
        for line in file:
            parts = line.strip().split("|")

            if not parts:
                continue

            command = parts[0].upper()

            if command == "ADVANCE":
                advances.append({
                    "payment_id": parts[1],
                    "flat_id": parts[2],
                    "payment_date": datetime.strptime(
                        parts[3], "%Y-%m-%d %H:%M:%S"
                    ),
                    "amount": money(parts[6])
                })

            elif command == "TRANSFER_FEE":
                transfer_fees.append({
                    "payment_id": parts[1],
                    "flat_id": parts[2],
                    "payment_date": datetime.strptime(
                        parts[3], "%Y-%m-%d %H:%M:%S"
                    ),
                    "amount": money(parts[4])
                })

    return advances, transfer_fees


def load_checkpoint_dates():
    """Load NDC and transfer dates for interest calculation."""

    checkpoint_dates = set()

    with open(
        INPUT_DIR / "commands.txt",
        "r",
        encoding="utf-8-sig"
    ) as file:

        for line in file:
            parts = line.strip().split("|")

            if not parts:
                continue

            command = parts[0].upper()

            if command in ("ISSUE_NDC", "TRANSFER"):
                checkpoint_dates.add(
                    date.fromisoformat(parts[-1][:10])
                )

    return sorted(checkpoint_dates)


def add_transaction(
    transactions,
    flat_id,
    transaction_date,
    transaction_type,
    amount=ZERO,
    interest_paid=ZERO,
    principal_paid=ZERO,
    advance_balance=ZERO,
    details=""
):
    transactions.append({
        "flat_id": flat_id,
        "date": transaction_date,
        "transaction_type": transaction_type,
        "amount": money(amount),
        "interest_paid": money(interest_paid),
        "principal_paid": money(principal_paid),
        "advance_balance": money(advance_balance),
        "details": details
    })


def accrue_interest(bills, flat_id, target_date, rate, transactions):
    """Accrue simple interest on unpaid principal."""

    for bill in bills:
        principal = bill["principal"]
        due_date = bill["due_date"]

        if principal <= ZERO or target_date <= due_date:
            continue

        last_date = bill["last_interest_date"]

        if target_date <= last_date:
            continue

        days = (target_date - last_date).days

        interest = money(
            principal * rate * Decimal(days)
            / Decimal("100") / Decimal("365")
        )

        if interest > ZERO:
            bill["interest"] = money(bill["interest"] + interest)

            add_transaction(
                transactions,
                flat_id,
                target_date,
                "INTEREST",
                amount=interest,
                details=f"{days} days of simple interest"
            )

        bill["last_interest_date"] = target_date


def apply_payment(bills, amount):
    """Apply money to interest first, then principal."""

    remaining = money(amount)
    interest_paid = ZERO
    principal_paid = ZERO

    for bill in bills:
        if remaining <= ZERO:
            break

        paid = min(remaining, bill["interest"])

        bill["interest"] = money(bill["interest"] - paid)
        remaining = money(remaining - paid)
        interest_paid = money(interest_paid + paid)

    for bill in bills:
        if remaining <= ZERO:
            break

        paid = min(remaining, bill["principal"])

        bill["principal"] = money(bill["principal"] - paid)
        remaining = money(remaining - paid)
        principal_paid = money(principal_paid + paid)

    return {
        "interest_paid": interest_paid,
        "principal_paid": principal_paid,
        "advance": remaining
    }


def apply_advance(bills, advance_balance):
    """Use available advance against interest first, then principal."""

    result = apply_payment(bills, advance_balance)

    interest_paid = money(result["interest_paid"])
    principal_paid = money(result["principal_paid"])
    unused_advance = money(result["advance"])

    used = money(interest_paid + principal_paid)

    return {
        "used": used,
        "unused_advance": unused_advance,
        "interest_paid": interest_paid,
        "principal_paid": principal_paid
    }


def next_month(month):
    year = month.year
    month_number = month.month + 1

    if month_number == 13:
        year += 1
        month_number = 1

    return date(year, month_number, 1)


def build_flat_ledger():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    bills_data = read_csv("monthly_bills.csv", OUTPUT_DIR)
    payments_data = read_csv("payments.csv", OUTPUT_DIR)

    rate = read_interest_rate()
    report_date = get_report_date()

    advances, transfer_fees = load_special_commands()
    checkpoint_dates = load_checkpoint_dates()

    flats = set()

    for row in bills_data:
        flats.add(row["flat_id"])

    for row in payments_data:
        flats.add(row["flat_id"])

    for row in advances + transfer_fees:
        flats.add(row["flat_id"])

    all_transactions = []
    summaries = []

    for flat_id in sorted(flats):

        events = []

        # Monthly bill events.
        for row in bills_data:
            if row["flat_id"] != flat_id:
                continue

            bill_date = next_month(
                date.fromisoformat(row["month"])
            )

            events.append({
                "date": datetime.combine(
                    bill_date, datetime.min.time()
                ),
                "type": "BILL",
                "data": row
            })

        # Normal payment events.
        for row in payments_data:
            if row["flat_id"] != flat_id:
                continue

            events.append({
                "date": datetime.strptime(
                    row["payment_date"], "%Y-%m-%d %H:%M:%S"
                ),
                "type": "PAYMENT",
                "data": row
            })

        # Advance payment events.
        for row in advances:
            if row["flat_id"] == flat_id:
                events.append({
                    "date": row["payment_date"],
                    "type": "ADVANCE",
                    "data": row
                })

        # Transfer fee receipts.
        for row in transfer_fees:
            if row["flat_id"] == flat_id:
                events.append({
                    "date": row["payment_date"],
                    "type": "TRANSFER_FEE",
                    "data": row
                })

        # NDC and transfer interest checkpoints.
        for checkpoint_date in checkpoint_dates:
            events.append({
                "date": datetime.combine(
                    checkpoint_date,
                    datetime.min.time()
                ),
                "type": "CHECKPOINT",
                "data": {}
            })

        # Process bills first, then checkpoints, then payments.
        events.sort(key=lambda event: (
            event["date"],
            {
                "BILL": 0,
                "CHECKPOINT": 1,
                "ADVANCE": 2,
                "PAYMENT": 3,
                "TRANSFER_FEE": 4
            }[event["type"]]
        ))

        # Ignore events after the reporting date.
        events = [
            event for event in events
            if event["date"].date() <= report_date
        ]

        flat_bills = []
        advance_balance = ZERO

        total_billed = ZERO
        total_payments = ZERO
        total_advance_received = ZERO
        total_transfer_fees = ZERO

        flat_transactions = []

        for event in events:
            event_date = event["date"]
            event_day = event_date.date()
            event_type = event["type"]
            data = event["data"]

            # Accrue interest before processing each event.
            accrue_interest(
                flat_bills,
                flat_id,
                event_day,
                rate,
                flat_transactions
            )

            if event_type == "BILL":

                amount = money(data["total"])
                total_billed = money(total_billed + amount)

                if amount < ZERO:
                    credit = abs(amount)

                    advance_balance = money(
                        advance_balance + credit
                    )

                    add_transaction(
                        flat_transactions,
                        flat_id,
                        event_day,
                        "BILL_CREDIT",
                        amount=credit,
                        advance_balance=advance_balance,
                        details=f"Negative bill credit for {data['month']}"
                    )

                    advance_result = apply_advance(
                        flat_bills, advance_balance
                    )

                    used = advance_result["used"]
                    advance_balance = advance_result["unused_advance"]

                    if used > ZERO:
                        add_transaction(
                            flat_transactions,
                            flat_id,
                            event_day,
                            "ADVANCE_APPLIED",
                            amount=used,
                            interest_paid=advance_result["interest_paid"],
                            principal_paid=advance_result["principal_paid"],
                            advance_balance=advance_balance,
                            details="Bill credit adjusted against outstanding dues"
                        )

                else:
                    bill = {
                        "month": data["month"],
                        "bill_date": event_day,
                        "due_date": event_day.replace(day=15),
                        "last_interest_date": event_day.replace(day=15),
                        "principal": amount,
                        "interest": ZERO
                    }

                    flat_bills.append(bill)

                    add_transaction(
                        flat_transactions,
                        flat_id,
                        event_day,
                        "BILL",
                        amount=amount,
                        details=f"Monthly bill for {data['month']}"
                    )

                    if advance_balance > ZERO:
                        advance_result = apply_advance(
                            flat_bills, advance_balance
                        )

                        used = advance_result["used"]
                        advance_balance = advance_result["unused_advance"]

                        if used > ZERO:
                            add_transaction(
                                flat_transactions,
                                flat_id,
                                event_day,
                                "ADVANCE_APPLIED",
                                amount=used,
                                interest_paid=advance_result["interest_paid"],
                                principal_paid=advance_result["principal_paid"],
                                advance_balance=advance_balance,
                                details="Advance adjusted against bills"
                            )

            elif event_type == "ADVANCE":

                amount = money(data["amount"])

                total_advance_received = money(
                    total_advance_received + amount
                )

                advance_balance = money(
                    advance_balance + amount
                )

                advance_result = apply_advance(
                    flat_bills, advance_balance
                )

                used = advance_result["used"]
                advance_balance = advance_result["unused_advance"]

                add_transaction(
                    flat_transactions,
                    flat_id,
                    event_day,
                    "ADVANCE_RECEIVED",
                    amount=amount,
                    advance_balance=advance_balance,
                    details=f"Advance reference {data['payment_id']}"
                )

                if used > ZERO:
                    add_transaction(
                        flat_transactions,
                        flat_id,
                        event_day,
                        "ADVANCE_APPLIED",
                        amount=used,
                        interest_paid=advance_result["interest_paid"],
                        principal_paid=advance_result["principal_paid"],
                        advance_balance=advance_balance,
                        details="Advance adjusted against outstanding bills"
                    )

            elif event_type == "PAYMENT":

                amount = money(data["amount"])

                total_payments = money(
                    total_payments + amount
                )

                result = apply_payment(flat_bills, amount)

                advance_balance = money(
                    advance_balance + result["advance"]
                )

                add_transaction(
                    flat_transactions,
                    flat_id,
                    event_day,
                    "PAYMENT",
                    amount=amount,
                    interest_paid=result["interest_paid"],
                    principal_paid=result["principal_paid"],
                    advance_balance=advance_balance,
                    details=f"Payment reference {data['payment_id']}"
                )

            elif event_type == "TRANSFER_FEE":

                amount = money(data["amount"])

                total_transfer_fees = money(
                    total_transfer_fees + amount
                )

                add_transaction(
                    flat_transactions,
                    flat_id,
                    event_day,
                    "TRANSFER_FEE_RECEIVED",
                    amount=amount,
                    details=f"Transfer fee reference {data['payment_id']}"
                )

            elif event_type == "CHECKPOINT":
                # Interest has already been accrued through this date.
                pass

        # Calculate interest up to the reporting date.
        accrue_interest(
            flat_bills,
            flat_id,
            report_date,
            rate,
            flat_transactions
        )

        principal_outstanding = sum(
            (bill["principal"] for bill in flat_bills), ZERO
        )

        interest_outstanding = sum(
            (bill["interest"] for bill in flat_bills), ZERO
        )

        principal_outstanding = money(principal_outstanding)
        interest_outstanding = money(interest_outstanding)

        total_outstanding = money(
            principal_outstanding + interest_outstanding
        )

        summaries.append({
            "flat_id": flat_id,
            "report_date": report_date.isoformat(),
            "total_billed": total_billed,
            "total_payments": total_payments,
            "advance_received": total_advance_received,
            "transfer_fees_received": total_transfer_fees,
            "principal_outstanding": principal_outstanding,
            "interest_outstanding": interest_outstanding,
            "total_outstanding": total_outstanding,
            "advance_balance": advance_balance
        })

        all_transactions.extend(flat_transactions)

    # Save detailed transaction ledger.
    transaction_file = OUTPUT_DIR / "ledger_transactions.csv"

    transaction_fields = [
        "flat_id",
        "date",
        "transaction_type",
        "amount",
        "interest_paid",
        "principal_paid",
        "advance_balance",
        "details"
    ]

    with open(
        transaction_file, "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=transaction_fields
        )
        writer.writeheader()
        writer.writerows(all_transactions)

    # Save one summary row per flat.
    summary_file = OUTPUT_DIR / "flat_ledger.csv"

    summary_fields = [
        "flat_id",
        "report_date",
        "total_billed",
        "total_payments",
        "advance_received",
        "transfer_fees_received",
        "principal_outstanding",
        "interest_outstanding",
        "total_outstanding",
        "advance_balance"
    ]

    with open(
        summary_file, "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=summary_fields
        )
        writer.writeheader()
        writer.writerows(summaries)

    print("\nFLAT LEDGER GENERATED")
    print("---------------------")
    print("Number of flats:", len(summaries))
    print("Report date:", report_date)
    print("Annual interest rate:", rate, "%")
    print("Detailed ledger:", transaction_file)
    print("Flat summary:", summary_file)

    print("\nFirst five flat summaries:")
    for row in summaries[:5]:
        print(row)


if __name__ == "__main__":
    build_flat_ledger()
