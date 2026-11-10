import csv
from decimal import Decimal

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ledger_file = BASE_DIR / "outputs" / "ledger_transactions.csv"

transfer_dates = {
    "FLT-A101": "2026-08-12",
    "FLT-B202": "2026-09-14",
    "FLT-A602": "2026-10-08"
}

balances = {
    flat_id: {
        "principal": Decimal("0.00"),
        "interest": Decimal("0.00")
    }
    for flat_id in transfer_dates
}

with open(ledger_file, "r", encoding="utf-8-sig") as file:
    transactions = csv.DictReader(file)

    for row in transactions:
        flat_id = row["flat_id"]

        if flat_id not in transfer_dates:
            continue

        if row["date"] > transfer_dates[flat_id]:
            continue

        transaction_type = row["transaction_type"]

        if transaction_type == "BILL":
            balances[flat_id]["principal"] += Decimal(
                row["amount"]
            )

        elif transaction_type == "INTEREST":
            balances[flat_id]["interest"] += Decimal(
                row["amount"]
            )

        elif transaction_type == "PAYMENT":
            balances[flat_id]["principal"] -= Decimal(
                row["principal_paid"]
            )

            balances[flat_id]["interest"] -= Decimal(
                row["interest_paid"]
            )

        elif transaction_type == "ADVANCE_APPLIED":
            balances[flat_id]["principal"] -= Decimal(
                row["amount"]
            )


print("\nTRANSFER DATE BALANCES")
print("----------------------")

for flat_id, balance in balances.items():
    print("\nFlat:", flat_id)
    print("Transfer date:", transfer_dates[flat_id])
    print("Principal outstanding:", balance["principal"])
    print("Interest outstanding:", balance["interest"])
    print(
        "Total outstanding:",
        balance["principal"] + balance["interest"]
    )