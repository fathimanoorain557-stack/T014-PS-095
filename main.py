
import csv
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from src.data_loader import load_data, load_commands

from src.billing import (
    generate_monthly_bills,
    adjust_bill_for_available_advance,
    update_defaulter_states,
    create_flat_balances,
    create_bill_balances,
    post_ledger_entry,
    post_transfer_fee_entry,
    post_bill_to_ledger,
    allocate_payment,
    accrue_interest_for_flat,
    get_flat,
    get_rate,
    save_bills_to_csv,
    save_ledger_to_csv,
    create_income_statement
)



# ==================================================
# SAVE SETTLEMENTS
# ==================================================

def save_settlements_to_csv(settlements):

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "settlements.csv"

    fieldnames = [
        "flat_id",
        "request_date",
        "outstanding_principal",
        "outstanding_interest",
        "outstanding_legal",
        "transfer_fee_paid",
        "decision",
        "reason",
        "dues_carried_to_owner_id"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(settlements)

    print("Settlements saved to:", output_file)


# ==================================================
# SAVE DEFAULTER TIMELINE
# ==================================================

def save_defaulter_timeline_to_csv(defaulter_timeline):

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "defaulter_timeline.csv"

    fieldnames = [
        "flat_id",
        "change_date",
        "from_state",
        "to_state",
        "arrears_months",
        "amenities_suspended",
        "legal_charge_added"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(defaulter_timeline)

    print("Defaulter timeline saved to:", output_file)
    print("Number of state changes:", len(defaulter_timeline))

def save_income_statement_to_csv(income_statement):

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "income_statement.csv"

    fieldnames = [
        "head",
        "billed",
        "collected",
        "expense",
        "surplus"
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in income_statement:
            writer.writerow(row)

    print("Income statement saved to:", output_file)


# ==================================================
# MAIN
# ==================================================

def main():

    # 1. Load input data
    data = load_data()
    commands = load_commands()

    # 2. Create empty records
    bills = []
    ledger = []
    settlements = []
    transferred_flats = {}
    income_statement = []

    # 3. Create balances for all flats
    balances = create_flat_balances(data)

    # 4. Create individual bill tracking
    bill_balances = create_bill_balances()

    # 5. Defaulter tracking
    defaulter_states = {}
    defaulter_timeline = []

    # 6. Track processed payment IDs
    processed_payment_ids = set()

    # 7. Track transfer fees separately
    transfer_fee_paid = {
        flat["flat_id"]: Decimal("0.00")
        for flat in data["flats"]
    }

    # 8. Track NDC status
    ndc_issued = {
        flat["flat_id"]: False
        for flat in data["flats"]
    }

    print("Data loaded successfully!")
    print("Number of flats:", len(data["flats"]))
    print("Number of commands:", len(commands))

    # ==================================================
    # PROCESS COMMANDS STRICTLY IN FILE ORDER
    # ==================================================

    for command in commands:

        parts = command.split("|")
        command_type = parts[0].strip()

        # ----------------------------------------------
        # ADVANCE
        # ----------------------------------------------

        if command_type == "ADVANCE":

            if len(parts) != 7:
                print("Invalid ADVANCE command:", command)
                continue

            payment_id = parts[1].strip()
            flat_id = parts[2].strip()
            payment_timestamp = parts[3].strip()

            try:
                amount = Decimal(parts[6].strip())

                payment_date = datetime.strptime(
                    payment_timestamp,
                    "%Y-%m-%d %H:%M:%S"
                ).date().isoformat()

            except (ValueError, ArithmeticError):
                print("Invalid ADVANCE command:", command)
                continue

            if flat_id not in balances:
                print("Unknown flat:", flat_id)
                continue

            if payment_id in processed_payment_ids:
                print("Duplicate payment rejected:", payment_id)
                continue

            if amount <= 0:
                print("Invalid advance amount:", payment_id)
                continue

            processed_payment_ids.add(payment_id)

            post_ledger_entry(
                ledger,
                balances[flat_id],
                flat_id,
                payment_date,
                "ADVANCE_RECEIVED",
                payment_id,
                "advance",
                credit=amount
            )

        # ----------------------------------------------
        # GENERATE_BILLS
        # ----------------------------------------------

        elif command_type == "GENERATE_BILLS":

            if len(parts) != 3:
                print("Invalid GENERATE_BILLS command:", command)
                continue

            covered_month = parts[1].strip()
            bill_date = parts[2].strip()

            monthly_bills = generate_monthly_bills(
                data,
                commands,
                covered_month,
                bill_date
            )

            for bill in monthly_bills:

                flat_id = bill["flat_id"]

                available_advance = balances[flat_id]["advance"]

                bill = adjust_bill_for_available_advance(
                    bill,
                    available_advance
                )

                post_bill_to_ledger(
                    ledger,
                    balances[flat_id],
                    bill,
                    bill_balances
                )

                bills.append(bill)

                # Update defaulter status after bill posting
                update_defaulter_states(
                    data,
                    ledger,
                    balances,
                    flat_id,
                    bill_date,
                    bill_balances,
                    defaulter_states,
                    defaulter_timeline
                )

            print(
                "Bills generated for:",
                covered_month,
                "| Count:",
                len(monthly_bills)
            )

        # ----------------------------------------------
        # PAYMENT
        # ----------------------------------------------

        elif command_type == "PAYMENT":

            if len(parts) != 6:
                print("Invalid PAYMENT command:", command)
                continue

            payment_id = parts[1].strip()
            flat_id = parts[2].strip()
            payment_timestamp = parts[3].strip()

            try:
                amount = Decimal(parts[4].strip())

                payment_date = datetime.strptime(
                    payment_timestamp,
                    "%Y-%m-%d %H:%M:%S"
                ).date().isoformat()

            except (ValueError, ArithmeticError):
                print("Invalid PAYMENT command:", command)
                continue

            if flat_id not in balances:
                print("Unknown flat:", flat_id)
                continue

            if payment_id in processed_payment_ids:
                print("Duplicate payment rejected:", payment_id)
                continue

            if amount <= 0:
                print("Invalid payment amount:", payment_id)
                continue

            processed_payment_ids.add(payment_id)

            # Accrue interest before payment
            accrue_interest_for_flat(
                data,
                ledger,
                balances[flat_id],
                flat_id,
                payment_date,
                bill_balances
            )

            # Allocate payment
            allocate_payment(
                ledger,
                balances[flat_id],
                flat_id,
                payment_date,
                payment_id,
                amount,
                bill_balances
            )

            # Recalculate arrears after payment
            update_defaulter_states(
                data,
                ledger,
                balances,
                flat_id,
                payment_date,
                bill_balances,
                defaulter_states,
                defaulter_timeline
            )

        # ----------------------------------------------
        # TRANSFER_FEE
        # ----------------------------------------------

        elif command_type == "TRANSFER_FEE":

            if len(parts) != 5:
                print("Invalid TRANSFER_FEE command:", command)
                continue

            payment_id = parts[1].strip()
            flat_id = parts[2].strip()
            payment_timestamp = parts[3].strip()

            try:
                amount = Decimal(parts[4].strip())

                payment_date = datetime.strptime(
                    payment_timestamp,
                    "%Y-%m-%d %H:%M:%S"
                ).date().isoformat()

                expected_fee = get_rate(
                    data,
                    "TRANSFER_FEE",
                    payment_date
                )

            except (ValueError, ArithmeticError):
                print("Invalid TRANSFER_FEE command:", command)
                continue

            if flat_id not in balances:
                print("Unknown flat:", flat_id)
                continue

            if payment_id in processed_payment_ids:
                print("Duplicate payment rejected:", payment_id)
                continue

            if amount <= 0:
                print("Invalid transfer fee:", payment_id)
                continue

            processed_payment_ids.add(payment_id)

            transfer_fee_paid[flat_id] += amount
            post_transfer_fee_entry(
                ledger,
                balances,
                flat_id,
                payment_date,
                payment_id,
                amount
)

            print(
                "Transfer fee received:",
                flat_id,
                "| Amount:",
                amount
            )

        # ----------------------------------------------
        # ISSUE_NDC
        # ----------------------------------------------
        
        elif command_type == "ISSUE_NDC":

            if len(parts) != 3:
                print("Invalid ISSUE_NDC command:", command)
                continue

            flat_id = parts[1].strip()
            request_date = parts[2].strip()

            if flat_id not in balances:
                print("Unknown flat:", flat_id)
                continue

            try:
                datetime.strptime(request_date, "%Y-%m-%d")

                expected_fee = get_rate(
                    data,
                    "TRANSFER_FEE",
                    request_date
                )

            except (ValueError, ArithmeticError):
                print("Invalid NDC request date:", command)
                continue

            principal = balances[flat_id]["principal"]
            interest = balances[flat_id]["interest"]
            legal = balances[flat_id]["legal"]
            fee_paid = transfer_fee_paid[flat_id]

            reason = ""

            if principal > 0:
                reason = "Outstanding principal"

            elif interest > 0:
                reason = "Outstanding interest"

            elif legal > 0:
                reason = "Outstanding legal charges"

            elif fee_paid < expected_fee:
                reason = "Transfer fee not fully paid"

            if reason == "":
                decision = "ISSUED"
                ndc_issued[flat_id] = True
            else:
                decision = "REFUSED"
                ndc_issued[flat_id] = False

            # Check whether the flat was transferred before this request
            dues_carried = ""

            if flat_id in transferred_flats:

                transfer_info = transferred_flats[flat_id]

                if transfer_info["transfer_date"] < request_date:
                    dues_carried = transfer_info["new_owner_id"]

            # Save one record for this NDC request
            settlements.append({
                "flat_id": flat_id,
                "request_date": request_date,
                "outstanding_principal": principal,
                "outstanding_interest": interest,
                "outstanding_legal": legal,
                "transfer_fee_paid": fee_paid,
                "decision": decision,
                "reason": reason,
                "dues_carried_to_owner_id": dues_carried
            })

            print(
                "NDC:",
                flat_id,
                "|",
                decision,
                "|",
                reason
            )


        # ----------------------------------------------
        # TRANSFER
        # ----------------------------------------------
        elif command_type == "TRANSFER":
            if len(parts) != 5:
                print("Invalid TRANSFER command:", command)
                continue

            transfer_id = parts[1].strip()
            flat_id = parts[2].strip()
            new_owner_id = parts[3].strip()
            transfer_date = parts[4].strip()

            if flat_id not in balances:
                print("Unknown flat:", flat_id)
                continue

            # Validate new owner
            owner_exists = any(
                owner["owner_id"] == new_owner_id
                for owner in data["owners"]
            )

            if not owner_exists:
                print("Unknown owner:", new_owner_id)
                continue

            try:
                datetime.strptime(transfer_date, "%Y-%m-%d")
            except ValueError:
                print("Invalid transfer date:", transfer_date)
                continue

            # Check whether NDC was issued before transfer
            if ndc_issued[flat_id]:

                decision = "ISSUED"
                reason = "NDC issued before transfer"

            else:

                decision = "DUES_CARRIED"
                reason = "NDC not issued before transfer"

            # Update the flat's owner
            flat = get_flat(data, flat_id)
            flat["owner_id"] = new_owner_id

            # Store transfer details
            transferred_flats[flat_id] = {
                "transfer_date": transfer_date,
                "new_owner_id": new_owner_id
            }

            # Find an earlier NDC request, if one exists
            matching_record = None

            for record in reversed(settlements):

                if (
                    record["flat_id"] == flat_id
                    and record["request_date"] <= transfer_date
                ):
                    matching_record = record
                    break

            # Update the existing NDC record only
            if matching_record is not None and not ndc_issued[flat_id]:

                matching_record["dues_carried_to_owner_id"] = new_owner_id

            print(
                "Transfer processed:",
                flat_id,
                "->",
                new_owner_id,
                "|",
                decision
            )


        # ----------------------------------------------
        # PRINT_INCOME_STATEMENT
        # ----------------------------------------------

        elif command_type == "PRINT_INCOME_STATEMENT":

            if len(parts) != 3:
                print("Invalid PRINT_INCOME_STATEMENT command:", command)
                continue

            from_month = parts[1].strip()
            to_month = parts[2].strip()

            statement = create_income_statement(
                data,
                bills,
                from_month,
                to_month
            )

            income_statement.extend(statement)

            print(
                "Income statement generated:",
                from_month,
                "to",
                to_month
            )

    # ==================================================
    # SAVE OUTPUT FILES
    # ==================================================

    save_bills_to_csv(bills)
    save_ledger_to_csv(ledger)
    save_settlements_to_csv(settlements)
    save_defaulter_timeline_to_csv(defaulter_timeline)
    save_income_statement_to_csv(income_statement)

    print("\nPROCESSING COMPLETED")
    print("====================")
    print("Bills:", len(bills))
    print("Ledger entries:", len(ledger))
    print("Settlement records:", len(settlements))
    print("Defaulter state changes:", len(defaulter_timeline))
    


if __name__ == "__main__":
    main()
