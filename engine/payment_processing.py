
import csv
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def load_payment_commands():
    """Load payments, skip exact duplicates, and separate invalid flats."""

    payments = []
    seen_records = {}

    command_file = INPUT_DIR / "commands.txt"

    with open(command_file, "r", encoding="utf-8-sig") as file:
        for line in file:
            parts = line.strip().split("|")

            if not parts or parts[0].upper() != "PAYMENT":
                continue

            if len(parts) != 6:
                raise ValueError(
                    f"Invalid payment command: {line.strip()}"
                )

            payment = {
                "payment_id": parts[1],
                "flat_id": parts[2],
                "payment_date": parts[3],
                "amount": money(parts[4]),
                "method": parts[5]
            }

            payment_id = payment["payment_id"]

            if payment_id in seen_records:
                if seen_records[payment_id] == payment:
                    continue

                raise ValueError(
                    f"Conflicting payment ID: {payment_id}"
                )

            seen_records[payment_id] = payment
            payments.append(payment)

    # Load registered flat IDs.
    with open(
        INPUT_DIR / "flats.csv",
        "r",
        encoding="utf-8-sig"
    ) as file:
        registered_flats = {
            row["flat_id"] for row in csv.DictReader(file)
        }

    valid_payments = []
    invalid_payments = []

    for payment in payments:
        if payment["flat_id"] in registered_flats:
            valid_payments.append(payment)
        else:
            invalid_payments.append(payment)

    valid_payments.sort(
        key=lambda payment: (
            payment["payment_date"],
            payment["payment_id"]
        )
    )

    return valid_payments, invalid_payments


def validate_payments(payments):
    """Validate valid payment records."""

    seen_ids = set()

    for payment in payments:
        if payment["payment_id"] in seen_ids:
            raise ValueError(
                f"Duplicate payment ID: {payment['payment_id']}"
            )

        seen_ids.add(payment["payment_id"])

        if not payment["flat_id"]:
            raise ValueError("Payment has no flat ID")

        if payment["amount"] <= 0:
            raise ValueError(
                f"Invalid payment amount: {payment['payment_id']}"
            )

    return True


def save_payment_file(payments, filename):
    """Save payment records to a CSV file."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / filename

    fieldnames = [
        "payment_id",
        "flat_id",
        "payment_date",
        "amount",
        "method"
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

        for payment in payments:
            writer.writerow({
                **payment,
                "amount": str(payment["amount"])
            })

    return output_file


def main():
    payments, invalid_payments = load_payment_commands()

    validate_payments(payments)

    valid_file = save_payment_file(
        payments,
        "payments.csv"
    )

    invalid_file = save_payment_file(
        invalid_payments,
        "invalid_payments.csv"
    )

    total_amount = sum(
        (payment["amount"] for payment in payments),
        Decimal("0.00")
    )

    print("\nPAYMENT RECORDS PROCESSED")
    print("-------------------------")
    print("Valid unique payments:", len(payments))
    print("Invalid payments:", len(invalid_payments))
    print("Valid payment amount:", total_amount)
    print("Valid records saved:", valid_file)
    print("Invalid records saved:", invalid_file)

    if invalid_payments:
        print("\nInvalid payment details:")
        for payment in invalid_payments:
            print(payment)

    print("\nFirst five valid payments:")
    for payment in payments[:5]:
        print(payment)


if __name__ == "__main__":
    main()

