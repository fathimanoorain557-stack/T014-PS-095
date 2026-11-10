
import csv
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"

CENT = Decimal("0.01")
EXPECTED_TRANSFER_FEE = Decimal("25000.00")


def money(value):
    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP
    )


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def read_commands():
    transfers = []
    ndcs = []
    transfer_fees = []

    command_file = INPUT_DIR / "commands.txt"

    with open(command_file, "r", encoding="utf-8-sig") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split("|")
            command = parts[0].upper()

            if command == "TRANSFER":
                transfers.append({
                    "transfer_id": parts[1],
                    "flat_id": parts[2],
                    "new_owner_id": parts[3],
                    "transfer_date": parts[4][:10]
                })

            elif command == "ISSUE_NDC":
                ndcs.append({
                    "flat_id": parts[1],
                    "ndc_date": parts[2][:10]
                })

            elif command == "TRANSFER_FEE":
                transfer_fees.append({
                    "payment_id": parts[1],
                    "flat_id": parts[2],
                    "payment_date": parts[3],
                    "amount": money(parts[4])
                })

    return transfers, ndcs, transfer_fees


def get_balance(flat_id, target_date, transactions):
    principal = Decimal("0.00")
    interest = Decimal("0.00")

    target_day = target_date[:10]

    for row in transactions:
        if row["flat_id"] != flat_id:
            continue

        transaction_day = row["date"][:10]

        if transaction_day > target_day:
            continue

        transaction_type = row["transaction_type"]

        if transaction_type == "BILL":
            principal += money(row["amount"])

        elif transaction_type == "INTEREST":
            interest += money(row["amount"])

        elif transaction_type == "PAYMENT":
            principal -= money(row["principal_paid"])
            interest -= money(row["interest_paid"])

        elif transaction_type == "ADVANCE_APPLIED":
            principal -= money(row["principal_paid"])
            interest -= money(row["interest_paid"])

    return {
        "principal": money(principal),
        "interest": money(interest),
        "total": money(principal + interest)
    }


def get_owner_on_date(flat_id, target_date, original_owners, transfers):
    owner_id = original_owners.get(flat_id, "")

    flat_transfers = [
        transfer for transfer in transfers
        if transfer["flat_id"] == flat_id
        and transfer["transfer_date"] <= target_date[:10]
    ]

    flat_transfers.sort(
        key=lambda transfer: transfer["transfer_date"]
    )

    for transfer in flat_transfers:
        owner_id = transfer["new_owner_id"]

    return owner_id


def save_csv(filename, rows, columns):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / filename

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_file


def main():
    flats = read_csv(INPUT_DIR / "flats.csv")
    owners = read_csv(INPUT_DIR / "owners.csv")

    transactions = read_csv(
        OUTPUT_DIR / "ledger_transactions.csv"
    )

    transfers, ndcs, transfer_fees = read_commands()

    original_owners = {
        flat["flat_id"]: flat["owner_id"]
        for flat in flats
    }

    owner_names = {
        owner["owner_id"]: owner["owner_name"]
        for owner in owners
    }

    # Sort transfers chronologically.
    transfers.sort(
        key=lambda transfer: transfer["transfer_date"]
    )

    # ------------------------------------------------
    # 1. GENERATE NDC REPORT
    # ------------------------------------------------

    ndc_results = []

    for ndc in ndcs:
        flat_id = ndc["flat_id"]
        ndc_date = ndc["ndc_date"]

        owner_id = get_owner_on_date(
            flat_id,
            ndc_date,
            original_owners,
            transfers
        )

        balance = get_balance(
            flat_id,
            ndc_date,
            transactions
        )

        status = (
            "ELIGIBLE"
            if balance["total"] <= 0
            else "NOT ELIGIBLE - OUTSTANDING DUES"
        )

        ndc_results.append({
            "flat_id": flat_id,
            "owner_id": owner_id,
            "owner_name": owner_names.get(owner_id, ""),
            "ndc_date": ndc_date,
            "principal_outstanding": str(balance["principal"]),
            "recorded_interest_outstanding": str(balance["interest"]),
            "total_recorded_outstanding": str(balance["total"]),
            "ndc_status": status
        })

    # ------------------------------------------------
    # 2. PREPARE TRANSFER FEE RECORDS
    # ------------------------------------------------

    fee_by_flat = {}

    for fee in transfer_fees:
        fee_by_flat.setdefault(
            fee["flat_id"], []
        ).append(fee)

    # ------------------------------------------------
    # 3. GENERATE OWNERSHIP HISTORY
    # ------------------------------------------------

    ownership_results = []
    settlement_results = []

    for transfer in transfers:
        flat_id = transfer["flat_id"]
        transfer_date = transfer["transfer_date"]
        new_owner_id = transfer["new_owner_id"]

        previous_owner_id = get_owner_on_date(
            flat_id,
            transfer_date,
            original_owners,
            [
                item for item in transfers
                if item["transfer_date"] < transfer_date
            ]
        )

        if not previous_owner_id:
            raise ValueError(
                f"Previous owner not found for {flat_id}"
            )

        if new_owner_id not in owner_names:
            raise ValueError(
                f"New owner not found: {new_owner_id}"
            )

        balance = get_balance(
            flat_id,
            transfer_date,
            transactions
        )

        # Only an eligible NDC issued before transfer
        # counts as valid NDC clearance.
        eligible_ndcs = [
            result
            for result in ndc_results
            if result["flat_id"] == flat_id
            and result["ndc_date"] < transfer_date
            and result["ndc_status"] == "ELIGIBLE"
        ]

        ndc_before_transfer = bool(eligible_ndcs)

        matching_fees = [
            fee for fee in fee_by_flat.get(flat_id, [])
            if fee["payment_date"][:10] <= transfer_date
        ]

        fee_amount = sum(
            (fee["amount"] for fee in matching_fees),
            Decimal("0.00")
        )

        fee_valid = fee_amount >= EXPECTED_TRANSFER_FEE

        if not ndc_before_transfer:
            transfer_status = (
                "TRANSFER BEFORE NDC - DUES CARRIED FORWARD"
            )

        elif balance["total"] > 0:
            transfer_status = (
                "TRANSFER WITH OUTSTANDING DUES"
            )

        elif not fee_valid:
            transfer_status = (
                "TRANSFER FEE INCOMPLETE"
            )

        else:
            transfer_status = (
                "TRANSFER COMPLETED - NO RECORDED DUES"
            )

        ownership_results.append({
            "transfer_id": transfer["transfer_id"],
            "flat_id": flat_id,
            "transfer_date": transfer_date,
            "previous_owner_id": previous_owner_id,
            "previous_owner_name": owner_names.get(
                previous_owner_id, ""
            ),
            "new_owner_id": new_owner_id,
            "new_owner_name": owner_names.get(
                new_owner_id, ""
            ),
            "transfer_fee_paid": str(fee_amount),
            "transfer_fee_valid": str(fee_valid),
            "ndc_before_transfer": str(ndc_before_transfer),
            "transfer_status": transfer_status
        })

        settlement_results.append({
            "transfer_id": transfer["transfer_id"],
            "flat_id": flat_id,
            "transfer_date": transfer_date,
            "old_owner_id": previous_owner_id,
            "new_owner_id": new_owner_id,
            "principal_carried_forward": str(
                balance["principal"]
            ),
            "recorded_interest_carried_forward": str(
                balance["interest"]
            ),
            "total_recorded_dues_carried_forward": str(
                balance["total"]
            ),
            "transfer_fee": str(fee_amount),
            "dues_responsibility": (
                "NEW OWNER"
                if balance["total"] > 0
                else "NO RECORDED DUES"
            )
        })

    # ------------------------------------------------
    # 4. SAVE ALL REPORTS
    # ------------------------------------------------

    ndc_file = save_csv(
        "ndc_status.csv",
        ndc_results,
        [
            "flat_id",
            "owner_id",
            "owner_name",
            "ndc_date",
            "principal_outstanding",
            "recorded_interest_outstanding",
            "total_recorded_outstanding",
            "ndc_status"
        ]
    )

    ownership_file = save_csv(
        "ownership_history.csv",
        ownership_results,
        [
            "transfer_id",
            "flat_id",
            "transfer_date",
            "previous_owner_id",
            "previous_owner_name",
            "new_owner_id",
            "new_owner_name",
            "transfer_fee_paid",
            "transfer_fee_valid",
            "ndc_before_transfer",
            "transfer_status"
        ]
    )

    settlement_file = save_csv(
        "resale_settlements.csv",
        settlement_results,
        [
            "transfer_id",
            "flat_id",
            "transfer_date",
            "old_owner_id",
            "new_owner_id",
            "principal_carried_forward",
            "recorded_interest_carried_forward",
            "total_recorded_dues_carried_forward",
            "transfer_fee",
            "dues_responsibility"
        ]
    )

    # ------------------------------------------------
    # 5. DISPLAY RESULTS
    # ------------------------------------------------

    print("\nOWNERSHIP TRANSFER MODULE")
    print("------------------------")

    print("\nNDC RESULTS:")

    for result in ndc_results:
        print(
            result["flat_id"],
            result["ndc_date"],
            result["owner_id"],
            result["owner_name"],
            result["ndc_status"]
        )

    print("\nTRANSFER RESULTS:")

    for result in ownership_results:
        print(
            result["flat_id"],
            result["previous_owner_name"],
            "->",
            result["new_owner_name"],
            result["transfer_status"]
        )

    print("\nRESALE SETTLEMENTS:")

    for result in settlement_results:
        print(
            result["flat_id"],
            "Dues carried forward:",
            result["total_recorded_dues_carried_forward"]
        )

    print("\nFILES GENERATED:")
    print(ndc_file)
    print(ownership_file)
    print(settlement_file)


if __name__ == "__main__":
    main()
