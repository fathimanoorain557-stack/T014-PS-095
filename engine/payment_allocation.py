
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value):
    """Round money to two decimal places."""
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP
    )


def get_interest_rate():
    """Read annual simple interest rate from rates.csv."""

    rate_file = INPUT_DIR / "rates.csv"

    if not rate_file.exists():
        raise FileNotFoundError(
            f"Rates file not found: {rate_file}"
        )

    with open(
        rate_file,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        rates = list(csv.DictReader(file))

    eligible = [
        row for row in rates
        if row["rate_code"] == "INTEREST_PA_PCT"
    ]

    if not eligible:
        raise ValueError("Interest rate not found")

    latest = max(
        eligible,
        key=lambda row: row["effective_from"]
    )

    rate = Decimal(latest["value"])

    if rate < 0:
        raise ValueError("Interest rate cannot be negative")

    return rate


def allocate_payment(
    payment,
    interest_balance,
    principal_balance
):
    """
    Allocate payment:
    1. Interest first
    2. Principal second
    3. Remaining amount becomes advance
    """

    amount = money(payment)
    interest_balance = money(interest_balance)
    principal_balance = money(principal_balance)

    if amount < ZERO:
        raise ValueError("Payment cannot be negative")

    if interest_balance < ZERO or principal_balance < ZERO:
        raise ValueError("Outstanding balances cannot be negative")

    interest_paid = min(amount, interest_balance)

    remaining = money(amount - interest_paid)

    principal_paid = min(
        remaining,
        principal_balance
    )

    remaining = money(
        remaining - principal_paid
    )

    advance = remaining

    return {
        "interest_paid": interest_paid,
        "principal_paid": principal_paid,
        "advance": advance,
        "remaining_interest": money(
            interest_balance - interest_paid
        ),
        "remaining_principal": money(
            principal_balance - principal_paid
        )
    }


def calculate_simple_interest(
    principal,
    annual_rate,
    start_date,
    end_date
):
    """Calculate simple interest using actual calendar days."""

    principal = money(principal)
    annual_rate = Decimal(str(annual_rate))

    if principal < ZERO:
        raise ValueError("Principal cannot be negative")

    if annual_rate < ZERO:
        raise ValueError("Interest rate cannot be negative")

    if end_date <= start_date or principal == ZERO:
        return ZERO

    days = (end_date - start_date).days

    interest = (
        principal
        * annual_rate
        * Decimal(days)
        / Decimal("100")
        / Decimal("365")
    )

    return money(interest)


def main():

    rate = get_interest_rate()

    print("\nPAYMENT ALLOCATION MODULE")
    print("=" * 45)

    print("Annual interest rate:", rate, "%")

    # Sample payment test
    result = allocate_payment(
        payment="5000",
        interest_balance="1200",
        principal_balance="6000"
    )

    print("\nSAMPLE PAYMENT ALLOCATION")
    print("-" * 45)

    print("Payment: Rs. 5000.00")
    print("Interest paid:", result["interest_paid"])
    print("Principal paid:", result["principal_paid"])
    print("Advance:", result["advance"])

    print(
        "Remaining interest:",
        result["remaining_interest"]
    )

    print(
        "Remaining principal:",
        result["remaining_principal"]
    )

    # Sample interest calculation
    start_date = datetime.strptime(
        "2026-06-16", "%Y-%m-%d"
    ).date()

    end_date = datetime.strptime(
        "2026-07-16", "%Y-%m-%d"
    ).date()

    interest = calculate_simple_interest(
        principal="10000",
        annual_rate=rate,
        start_date=start_date,
        end_date=end_date
    )

    print("\nSAMPLE INTEREST CALCULATION")
    print("-" * 45)
    print("Principal: Rs. 10000.00")
    print("Interest:", interest)
    print("Period:", (end_date - start_date).days, "days")

    print("\nPayment allocation module completed.")
    print("=" * 45)


if __name__ == "__main__":
    main()
