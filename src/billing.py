
import sys
import csv
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.data_loader import load_data, load_commands


# ==================================================
# 1. HELPER: ROUND AMOUNT TO NEAREST RUPEE
# ==================================================

def round_rupee(amount):
    return amount.quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 2. GET APPLICABLE RATE
# ==================================================

def get_rate(data, rate_code, billing_date):

    billing_date = date.fromisoformat(billing_date[:10])

    applicable_rates = []

    for rate in data["rates"]:

        if rate["rate_code"] == rate_code:

            effective_date = date.fromisoformat(
                rate["effective_from"][:10]
            )

            if effective_date <= billing_date:
                applicable_rates.append(rate)

    if not applicable_rates:
        raise ValueError(
            f"No rate found for {rate_code} on {billing_date}"
        )

    latest_rate = max(
        applicable_rates,
        key=lambda rate: rate["effective_from"]
    )

    return Decimal(latest_rate["value"])


# ==================================================
# 3. GET MAINTENANCE RATE
# ==================================================

def get_maintenance_rate(data, billing_date):

    return get_rate(
        data,
        "MAINT_PER_SQFT",
        billing_date
    )


# ==================================================
# 4. FIND FLAT DETAILS
# ==================================================

def get_flat(data, flat_id):

    for flat in data["flats"]:

        if flat["flat_id"] == flat_id:
            return flat

    raise ValueError(f"Flat not found: {flat_id}")


# ==================================================
# 5. CALCULATE BASE MAINTENANCE
# ==================================================

def calculate_base_maintenance(data, flat_id, billing_date):

    flat = get_flat(data, flat_id)

    area = Decimal(flat["super_builtup_sqft"])

    rate = get_maintenance_rate(data, billing_date)

    amount = round_rupee(area * rate)

    return area, rate, amount


# ==================================================
# 6. GET OCCUPANCY AND RESIDENT COUNT
# ==================================================

def get_occupancy_for_month(
    data,
    commands,
    flat_id,
    billing_month
):

    flat = get_flat(data, flat_id)

    occupancy = flat["occupancy"]
    residents = int(flat["declared_residents"])

    month_start = date.fromisoformat(
        billing_month + "-01"
    )

    for command in commands:

        parts = command.split("|")

        if parts[0].strip() != "DECLARE_OCCUPANCY":
            continue

        if len(parts) < 5:
            continue

        if parts[1].strip() != flat_id:
            continue

        try:
            effective_date = date.fromisoformat(
                parts[3].strip()[:10]
            )

        except ValueError:
            print("Invalid occupancy date:", command)
            continue

        if effective_date <= month_start:

            occupancy = parts[2].strip()

            try:
                residents = int(parts[4].strip())
            except ValueError:
                residents = 0

    return occupancy, residents


# ==================================================
# 7. CALCULATE OCCUPANCY-BASED MONTHLY CHARGES
# ==================================================

def calculate_monthly_charges(
    data,
    commands,
    flat_id,
    billing_date
):

    billing_date = billing_date[:10]
    billing_month = billing_date[:7]

    area, maintenance_rate, base_maintenance = (
        calculate_base_maintenance(
            data,
            flat_id,
            billing_date
        )
    )

    occupancy, residents = get_occupancy_for_month(
        data,
        commands,
        flat_id,
        billing_month
    )

    non_occupancy_pct = get_rate(
        data,
        "NON_OCCUPANCY_PCT",
        billing_date
    )

    vacant_pct = get_rate(
        data,
        "VACANT_MAINT_PCT",
        billing_date
    )

    sinking_rate = get_rate(
        data,
        "SINKING_PER_SQFT",
        billing_date
    )

    if occupancy == "OWNER":

        maintenance = base_maintenance
        non_occupancy_charge = Decimal("0")

    elif occupancy == "TENANT":

        maintenance = base_maintenance

        non_occupancy_charge = (
            base_maintenance
            * non_occupancy_pct
            / Decimal("100")
        )

    elif occupancy == "VACANT":

        maintenance = (
            base_maintenance
            * vacant_pct
            / Decimal("100")
        )

        non_occupancy_charge = Decimal("0")

    else:

        raise ValueError(
            f"Unknown occupancy status: {occupancy}"
        )

    maintenance = round_rupee(maintenance)

    non_occupancy_charge = round_rupee(
        non_occupancy_charge
    )

    sinking_fund = round_rupee(
        area * sinking_rate
    )

    total = (
        maintenance
        + non_occupancy_charge
        + sinking_fund
    )

    return {
        "flat_id": flat_id,
        "billing_date": billing_date,
        "occupancy": occupancy,
        "residents": residents,
        "area": area,
        "maintenance_rate": maintenance_rate,
        "base_maintenance": base_maintenance,
        "maintenance": maintenance,
        "non_occupancy_charge": non_occupancy_charge,
        "sinking_fund": sinking_fund,
        "total": total
    }


# ==================================================
# 8. CALCULATE WATER CHARGES
# ==================================================

def calculate_water_charge(
    data,
    commands,
    flat_id,
    billing_month
):

    flat = get_flat(data, flat_id)

    occupancy, declared_residents = get_occupancy_for_month(
        data,
        commands,
        flat_id,
        billing_month
    )

    residents = Decimal(str(declared_residents))

    water_per_kl = get_rate(
        data,
        "WATER_PER_KL",
        billing_month + "-01"
    )

    water_per_head = get_rate(
        data,
        "WATER_PER_HEAD",
        billing_month + "-01"
    )

    if flat["has_water_meter"].strip().lower() != "true":

        return {
            "method": "PER_HEAD",
            "consumption": residents,
            "water_charge": round_rupee(
                residents * water_per_head
            )
        }

    readings = [
        reading
        for reading in data["meter_readings"]
        if reading["flat_id"] == flat_id
    ]

    readings.sort(
        key=lambda r: r["reading_date"]
    )

    current_reading = None
    previous_reading = None

    for i, reading in enumerate(readings):

        if reading["reading_date"][:7] == billing_month:

            current_reading = Decimal(
                reading["reading_kl"]
            )

            if i > 0:
                previous_reading = Decimal(
                    readings[i - 1]["reading_kl"]
                )

    if current_reading is None:
        raise ValueError(
            f"No meter reading found for {flat_id} "
            f"in {billing_month}"
        )

    if previous_reading is None:

        return {
            "method": "PER_HEAD",
            "consumption": residents,
            "water_charge": round_rupee(
                residents * water_per_head
            )
        }

    if current_reading < previous_reading:

        return {
            "method": "PER_HEAD_METER_REPLACEMENT",
            "consumption": residents,
            "water_charge": round_rupee(
                residents * water_per_head
            )
        }

    consumption = current_reading - previous_reading

    charge = consumption * water_per_kl

    return {
        "method": "METER",
        "consumption": consumption,
        "water_charge": round_rupee(charge)
    }


# ==================================================
# 9. VALIDATE PAYMENT COMMANDS
# ==================================================

def validate_payment_commands(data, commands):

    valid_flat_ids = {
        flat["flat_id"]
        for flat in data["flats"]
    }

    seen_payment_ids = set()

    accepted = 0
    rejected = []

    for command in commands:

        parts = command.split("|")

        if parts[0].strip() != "PAYMENT":
            continue

        if len(parts) != 6:
            rejected.append(
                (command, "Invalid command format")
            )
            continue

        payment_id = parts[1].strip()
        flat_id = parts[2].strip()
        payment_date = parts[3].strip()
        amount_text = parts[4].strip()

        if payment_id in seen_payment_ids:
            rejected.append(
                (payment_id, "Duplicate payment ID")
            )
            continue

        seen_payment_ids.add(payment_id)

        if flat_id not in valid_flat_ids:
            rejected.append(
                (payment_id, "Invalid flat ID")
            )
            continue

        try:
            datetime.strptime(
                payment_date,
                "%Y-%m-%d %H:%M:%S"
            )

            amount = Decimal(amount_text)

            if amount <= 0:
                raise ValueError

        except ValueError:
            rejected.append(
                (payment_id, "Invalid date or amount")
            )
            continue

        accepted += 1

    return accepted, rejected


# ==================================================
# 10. CALCULATE INTEREST
# ==================================================

def calculate_interest(
    data,
    principal,
    due_date,
    payment_date
):

    due = date.fromisoformat(due_date[:10])
    paid = date.fromisoformat(payment_date[:10])

    if paid <= due:
        return Decimal("0.00")

    overdue_days = (paid - due).days

    annual_rate = get_rate(
        data,
        "INTEREST_PA_PCT",
        due_date
    )

    interest = (
        principal
        * annual_rate
        / Decimal("100")
        * Decimal(overdue_days)
        / Decimal("365")
    )

    return interest.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 11. CALCULATE PARKING CHARGES
# ==================================================

def calculate_parking_charge(
    data,
    flat_id,
    billing_date
):

    flat = get_flat(data, flat_id)

    covered_slots = int(flat["covered_slots"])
    open_slots = int(flat["open_slots"])

    covered_rate = get_rate(
        data,
        "PARKING_COVERED",
        billing_date
    )

    open_rate = get_rate(
        data,
        "PARKING_OPEN",
        billing_date
    )

    return (
        covered_slots * covered_rate
        + open_slots * open_rate
    )


# ==================================================
# 12. CALCULATE AREA-BASED COMMON EXPENSE
# ==================================================

def calculate_area_share(
    data,
    flat_id,
    billing_month,
    expense_head
):

    flat = get_flat(data, flat_id)

    flat_area = Decimal(
        flat["super_builtup_sqft"]
    )

    total_area = sum(
        Decimal(f["super_builtup_sqft"])
        for f in data["flats"]
    )

    total_expense = sum(
        (
            Decimal(expense["amount"])
            for expense in data["expenses"]
            if expense["expense_month"][:7] == billing_month
            and expense["head"] == expense_head
        ),
        Decimal("0.00")
    )

    if total_area == 0:
        raise ValueError(
            "Total society area cannot be zero"
        )

    share = (
        total_expense * flat_area / total_area
    )

    return share.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 13. CALCULATE LIFT AMC
# ==================================================

def calculate_lift_amc(
    data,
    flat_id,
    billing_month
):

    flat = get_flat(data, flat_id)

    if int(flat["floor"]) == 0:
        return Decimal("0.00")

    tower_id = flat["tower_id"]

    eligible_flats = [
        f for f in data["flats"]
        if f["tower_id"] == tower_id
        and int(f["floor"]) != 0
    ]

    eligible_count = len(eligible_flats)

    if eligible_count == 0:
        return Decimal("0.00")

    total_expense = sum(
        (
            Decimal(expense["amount"])
            for expense in data["expenses"]
            if expense["expense_month"][:7] == billing_month
            and expense["head"] == "LIFT_AMC"
            and expense["tower_id"] == tower_id
        ),
        Decimal("0.00")
    )

    share = (
        total_expense / Decimal(eligible_count)
    )

    return share.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 14. CALCULATE WATER TANKER ALLOCATION
# ==================================================

def calculate_water_tanker(
    data,
    commands,
    flat_id,
    billing_month
):

    tanker_expense = sum(
        (
            Decimal(expense["amount"])
            for expense in data["expenses"]
            if expense["head"] == "WATER_TANKER"
            and expense["expense_month"][:7] == billing_month
        ),
        Decimal("0.00")
    )

    if tanker_expense == 0:
        return Decimal("0.00")

    eligible_flats = []

    for flat in data["flats"]:

        occupancy, residents = get_occupancy_for_month(
            data,
            commands,
            flat["flat_id"],
            billing_month
        )

        if occupancy != "VACANT" and residents > 0:

            eligible_flats.append(flat["flat_id"])

    if not eligible_flats:
        return Decimal("0.00")

    total_paise = int(
        (tanker_expense * Decimal("100")).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )

    number_of_flats = len(eligible_flats)

    base_paise = total_paise // number_of_flats
    extra_paise = total_paise % number_of_flats

    allocations = {}

    for index, eligible_flat_id in enumerate(eligible_flats):

        share_paise = base_paise

        if index < extra_paise:
            share_paise += 1

        allocations[eligible_flat_id] = (
            Decimal(share_paise) / Decimal("100")
        )

    return allocations.get(flat_id, Decimal("0.00"))



# ==================================================
# 15. CALCULATE GST
# ==================================================

def calculate_gst(data, maintenance, billing_date):

    gst_threshold = get_rate(
        data,
        "GST_MAINT_THRESHOLD",
        billing_date
    )

    gst_percentage = get_rate(
        data,
        "GST_PCT",
        billing_date
    )

    if maintenance <= gst_threshold:
        return Decimal("0.00")

    gst_amount = (
        maintenance
        * gst_percentage
        / Decimal("100")
    )

    return gst_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 16. CALCULATE UNAUTHORISED PARKING
# ==================================================

def calculate_unauthorised_parking(
    data,
    commands,
    flat_id,
    billing_month
):

    complaint_found = False

    billing_date = date.fromisoformat(
        billing_month + "-01"
    )

    for command in commands:

        parts = command.split("|")

        if parts[0].strip() != "PARKING_COMPLAINT":
            continue

        if len(parts) != 4:
            continue

        complaint_flat = parts[2].strip()

        if complaint_flat != flat_id:
            continue

        complaint_date = date.fromisoformat(
            parts[3].strip()[:10]
        )

        if complaint_date <= billing_date.replace(day=28):
            complaint_found = True
            break

    if complaint_found:

        return get_rate(
            data,
            "UNAUTH_PARKING",
            billing_month + "-01"
        )

    return Decimal("0.00")


# ==================================================
# 17. CALCULATE MONTHLY ADVANCE APPLICATION
# ==================================================


def calculate_advance_applied(
    data,
    commands,
    flat_id,
    billing_month,
    maintenance,
    bill_date
):

    bill_date_obj = date.fromisoformat(
        bill_date[:10]
    )

    billing_month_obj = date.fromisoformat(
        billing_month[:7] + "-01"
    )

    total_advance_for_month = Decimal("0.00")

    for command in commands:

        parts = command.split("|")

        if parts[0].strip() != "ADVANCE":
            continue

        if len(parts) != 7:
            continue

        advance_flat_id = parts[2].strip()
        payment_timestamp = parts[3].strip()
        start_month = parts[4].strip()
        number_of_months_text = parts[5].strip()
        amount_text = parts[6].strip()

        if advance_flat_id != flat_id:
            continue

        try:
            payment_date = datetime.strptime(
                payment_timestamp,
                "%Y-%m-%d %H:%M:%S"
            ).date()

            number_of_months = int(
                number_of_months_text
            )

            advance_amount = Decimal(amount_text)

            # The command already contains YYYY-MM-DD.
            start_date = date.fromisoformat(
                start_month[:10]
            )

        except (ValueError, ArithmeticError):
            continue

        if number_of_months <= 0 or advance_amount <= 0:
            continue

        if payment_date > bill_date_obj:
            continue

        month_difference = (
            (billing_month_obj.year - start_date.year) * 12
            + billing_month_obj.month
            - start_date.month
        )

        if month_difference < 0:
            continue

        if month_difference >= number_of_months:
            continue

        monthly_allocation = (
            advance_amount / Decimal(number_of_months)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if month_difference == number_of_months - 1:

            previous_allocations = (
                monthly_allocation
                * Decimal(number_of_months - 1)
            )

            monthly_allocation = (
                advance_amount - previous_allocations
            )

        total_advance_for_month += monthly_allocation

    advance_applied = min(
        total_advance_for_month,
        maintenance
    )

    return advance_applied.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


# ==================================================
# 18. CALCULATE COMPLETE MONTHLY BILL
# ==================================================

def calculate_full_monthly_bill(
    data,
    commands,
    flat_id,
    covered_month,
    bill_date
):

    flat = get_flat(data, flat_id)

    billing_month = covered_month[:7]
    billing_period_date = billing_month + "-01"

    # 1. Maintenance, non-occupancy and sinking fund

    monthly = calculate_monthly_charges(
        data,
        commands,
        flat_id,
        billing_period_date
    )

    # 2. Water charges

    water = calculate_water_charge(
        data,
        commands,
        flat_id,
        billing_month
    )

    # 3. Common electricity

    common_electricity = calculate_area_share(
        data,
        flat_id,
        billing_month,
        "COMMON_ELECTRICITY"
    )

    # 4. Generator diesel

    generator_diesel = calculate_area_share(
        data,
        flat_id,
        billing_month,
        "GENERATOR_DIESEL"
    )

    # 5. Lift AMC

    lift_amc = calculate_lift_amc(
        data,
        flat_id,
        billing_month
    )

    # 6. Water tanker

    water_tanker = calculate_water_tanker(
        data,
        commands,
        flat_id,
        billing_month
    )

    # 7. Regular parking

    parking = calculate_parking_charge(
        data,
        flat_id,
        billing_period_date
    )

    # 8. Unauthorised parking

    unauthorised_parking = calculate_unauthorised_parking(
        data,
        commands,
        flat_id,
        billing_month
    )

    # 9. GST

    gst = calculate_gst(
        data,
        monthly["maintenance"],
        billing_period_date
    )

    # 10. Apply advance only against maintenance

    advance_applied = calculate_advance_applied(
        data,
        commands,
        flat_id,
        billing_month,
        monthly["maintenance"],
        bill_date
    )

    # 11. Calculate total after advance

    raw_total = (
        monthly["maintenance"]
        + monthly["non_occupancy_charge"]
        + monthly["sinking_fund"]
        + water["water_charge"]
        + common_electricity
        + generator_diesel
        + lift_amc
        + water_tanker
        + parking
        + unauthorised_parking
        + gst
        - advance_applied
    )

    # A negative amount is not issued as a negative bill.
    # This basic billing stage reports zero for such a bill.
    # Carry-forward credit processing will be handled
    # in the later ledger stage.

    if raw_total < 0:
        raw_total = Decimal("0.00")

    # 12. Round final bill to nearest rupee

    bill_total = round_rupee(raw_total)

    rounding = bill_total - raw_total

    # 13. Due date is the 15th of the bill month

    bill_date_obj = date.fromisoformat(
        bill_date[:10]
    )

    due_date = bill_date_obj.replace(day=15)

    # 14. Return complete bill details

    return {
        "bill_id": f"BILL-{flat_id}-{billing_month}",
        "flat_id": flat_id,
        "owner_id": flat["owner_id"],
        "covered_month": billing_month,
        "bill_date": bill_date[:10],
        "due_date": due_date.isoformat(),
        "billing_status": monthly["occupancy"],

        "maintenance": monthly["maintenance"],
        "sinking_fund": monthly["sinking_fund"],
        "non_occupancy": monthly["non_occupancy_charge"],

        "water": water["water_charge"],
        "water_basis": water["method"],

        "common_electricity": common_electricity,
        "generator_diesel": generator_diesel,
        "lift_amc": lift_amc,
        "water_tanker": water_tanker,

        "parking": parking,
        "unauthorised_parking": unauthorised_parking,

        "gst": gst,
        "advance_applied": advance_applied,
        "rounding": rounding,
        "bill_total": bill_total
    }


# ==================================================
# 19. GENERATE BILLS FOR ALL FLATS
# ==================================================


def generate_monthly_bills(
    data,
    commands,
    covered_month,
    bill_date
):

    bills = []

    for flat in data["flats"]:

        flat_id = flat["flat_id"]

        bill = calculate_full_monthly_bill(
            data,
            commands,
            flat_id,
            covered_month,
            bill_date
        )

        bills.append(bill)

    return bills


def adjust_bill_for_available_advance(bill, available_advance):

    available_advance = Decimal(str(available_advance))

    scheduled_advance = Decimal(str(bill["advance_applied"]))

    actual_advance = min(
        scheduled_advance,
        available_advance
    )

    raw_total = (
        Decimal(str(bill["maintenance"]))
        + Decimal(str(bill["non_occupancy"]))
        + Decimal(str(bill["sinking_fund"]))
        + Decimal(str(bill["water"]))
        + Decimal(str(bill["common_electricity"]))
        + Decimal(str(bill["generator_diesel"]))
        + Decimal(str(bill["lift_amc"]))
        + Decimal(str(bill["water_tanker"]))
        + Decimal(str(bill["parking"]))
        + Decimal(str(bill["unauthorised_parking"]))
        + Decimal(str(bill["gst"]))
        - actual_advance
    )

    if raw_total < 0:
        raw_total = Decimal("0.00")

    bill["advance_applied"] = actual_advance

    bill["bill_total"] = round_rupee(raw_total)

    bill["rounding"] = bill["bill_total"] - raw_total

    return bill

# ==================================================
# 20. SAVE BILLS TO CSV
# ==================================================

def save_bills_to_csv(bills):

    output_folder = (
        Path(__file__).resolve().parent.parent / "outputs"
    )

    output_folder.mkdir(exist_ok=True)

    output_file = output_folder / "bills.csv"

    if not bills:
        print("No bills to save.")
        return

    fieldnames = list(bills[0].keys())

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(bills)

    print("Bills saved successfully!")
    print("File:", output_file)
    print("Number of bills:", len(bills))


# ==================================================
# 21. LEDGER: INITIALISE FLAT BALANCES
# ==================================================

def create_flat_balances(data):

    balances = {}

    for flat in data["flats"]:

        flat_id = flat["flat_id"]

        balances[flat_id] = {
            "principal": Decimal("0.00"),
            "interest": Decimal("0.00"),
            "legal": Decimal("0.00"),
            "advance": Decimal("0.00")
        }

    return balances
# ==================================================
# 22. TRACK INDIVIDUAL BILL BALANCES
# ==================================================

def create_bill_balances():
    return {}

# ==================================================
# 22. LEDGER: POST ONE TRANSACTION
# ==================================================

def post_ledger_entry(
    ledger,
    balances,
    flat_id,
    posting_date,
    entry_type,
    reference,
    balance_type,
    debit=Decimal("0.00"),
    credit=Decimal("0.00")
):

    debit = Decimal(str(debit)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    credit = Decimal(str(credit)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if balance_type not in balances:
        raise ValueError(
            f"Invalid balance type: {balance_type}"
        )

    if debit < 0 or credit < 0:
        raise ValueError("Debit and credit cannot be negative")

    if debit > 0 and credit > 0:
        raise ValueError(
            "An entry cannot have both debit and credit"
        )

    if balance_type == "advance":
        balances["advance"] += credit - debit
    else:
        balances[balance_type] += debit - credit

    if balances[balance_type] < 0:
        raise ValueError(
            f"{balance_type} balance cannot be negative"
        )

    ledger.append({
        "flat_id": flat_id,
        "posting_date": posting_date,
        "entry_type": entry_type,
        "reference": reference,
        "debit": debit,
        "credit": credit,
        "principal_balance": balances["principal"],
        "interest_balance": balances["interest"],
        "legal_balance": balances["legal"],
        "advance_balance": balances["advance"]
    })


def post_transfer_fee_entry(
    ledger,
    balances,
    flat_id,
    posting_date,
    reference,
    amount
):
    amount = Decimal(str(amount)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if amount <= 0:
        raise ValueError("Transfer fee must be positive")

    ledger.append({
        "flat_id": flat_id,
        "posting_date": posting_date,
        "entry_type": "TRANSFER_FEE",
        "reference": reference,
        "debit": Decimal("0.00"),
        "credit": amount,
        "principal_balance": balances[flat_id]["principal"],
        "interest_balance": balances[flat_id]["interest"],
        "legal_balance": balances[flat_id]["legal"],
        "advance_balance": balances[flat_id]["advance"]
    })


# ==================================================
# TRACK INDIVIDUAL BILL BALANCES
# ==================================================

def create_bill_balances():
    return {}


def post_bill_to_ledger(
    ledger,
    balances,
    bill,
    bill_balances=None
):

    flat_id = bill["flat_id"]
    bill_date = bill["bill_date"]
    bill_id = bill["bill_id"]

    advance_applied = Decimal(
        str(bill["advance_applied"])
    )

    bill_total = Decimal(
        str(bill["bill_total"])
    )

    # 1. Consume advance applied to this bill

    if advance_applied > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            bill_date,
            "ADVANCE_APPLIED",
            bill_id,
            "advance",
            debit=advance_applied
        )

    # 2. Record remaining bill as principal

    if bill_total > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            bill_date,
            "BILL",
            bill_id,
            "principal",
            debit=bill_total
        )

    # 3. Track individual bill balance

    if bill_balances is not None:

        bill_balances[bill_id] = {
            "flat_id": flat_id,
            "bill_date": bill_date,
            "due_date": bill["due_date"],
            "outstanding": bill_total,
            "last_interest_date": bill["due_date"]
        }

    return balances


# ==================================================
# 23. POST A GENERATED BILL TO THE LEDGER
# ==================================================


def post_bill_to_ledger(
    ledger,
    balances,
    bill,
    bill_balances=None
):

    flat_id = bill["flat_id"]
    bill_date = bill["bill_date"]
    bill_id = bill["bill_id"]

    advance_applied = Decimal(
        str(bill["advance_applied"])
    )

    bill_total = Decimal(
        str(bill["bill_total"])
    )

    # 1. Consume advance applied to this bill

    if advance_applied > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            bill_date,
            "ADVANCE_APPLIED",
            bill_id,
            "advance",
            debit=advance_applied
        )

    # 2. Record remaining bill as principal

    if bill_total > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            bill_date,
            "BILL",
            bill_id,
            "principal",
            debit=bill_total
        )

    # 3. Track individual bill balance

    if bill_balances is not None:

        bill_balances[bill_id] = {
            "flat_id": flat_id,
            "bill_date": bill_date,
            "due_date": bill["due_date"],
            "outstanding": bill_total,
            "last_interest_date": bill["due_date"]
        }

    return balances

def accrue_interest_for_flat(
    data,
    ledger,
    balances,
    flat_id,
    payment_date,
    bill_balances
):

    payment_date_obj = date.fromisoformat(
        payment_date[:10]
    )

    for bill_id, bill in bill_balances.items():

        if bill["flat_id"] != flat_id:
            continue

        principal = Decimal(
            str(bill["outstanding"])
        )

        if principal <= 0:
            continue

        due_date = date.fromisoformat(
            bill["due_date"][:10]
        )

        last_interest_date = date.fromisoformat(
            bill["last_interest_date"][:10]
        )

        interest_start = max(
            due_date,
            last_interest_date
        )

        if payment_date_obj <= interest_start:
            continue

        interest_days = (
            payment_date_obj - interest_start
        ).days

        interest = calculate_interest(
            data,
            principal,
            due_date.isoformat(),
            payment_date_obj.isoformat()
        )

        # Calculate only the additional interest since
        # the previous interest calculation.
        previous_interest = calculate_interest(
            data,
            principal,
            due_date.isoformat(),
            interest_start.isoformat()
        )

        additional_interest = (
            interest - previous_interest
        )

        if additional_interest > 0:

            post_ledger_entry(
                ledger,
                balances,
                flat_id,
                payment_date,
                "INTEREST",
                bill_id,
                "interest",
                debit=additional_interest
            )

        bill["last_interest_date"] = payment_date_obj.isoformat()


# ==================================================
# 24. ALLOCATE PAYMENT
# ==================================================


def allocate_payment(
    ledger,
    balances,
    flat_id,
    payment_date,
    payment_id,
    payment_amount,
    bill_balances=None
):

    remaining = Decimal(str(payment_amount)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if remaining <= 0:
        raise ValueError("Payment amount must be positive")

    # 1. Settle outstanding interest first

    interest_payment = min(
        remaining,
        balances["interest"]
    )

    if interest_payment > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            payment_date,
            "PAYMENT_INTEREST",
            payment_id,
            "interest",
            credit=interest_payment
        )

        remaining -= interest_payment

    # 2. Settle oldest outstanding bills first

    if bill_balances is not None:

        flat_bills = [
            (bill_id, bill)
            for bill_id, bill in bill_balances.items()
            if bill["flat_id"] == flat_id
            and bill["outstanding"] > 0
        ]

        flat_bills.sort(
            key=lambda item: item[1]["due_date"]
        )

        for bill_id, bill in flat_bills:

            if remaining <= 0:
                break

            principal_payment = min(
                remaining,
                bill["outstanding"]
            )

            if principal_payment > 0:

                post_ledger_entry(
                    ledger,
                    balances,
                    flat_id,
                    payment_date,
                    "PAYMENT_PRINCIPAL",
                    payment_id,
                    "principal",
                    credit=principal_payment
                )

                bill["outstanding"] -= principal_payment
                remaining -= principal_payment

    else:

        principal_payment = min(
            remaining,
            balances["principal"]
        )

        if principal_payment > 0:

            post_ledger_entry(
                ledger,
                balances,
                flat_id,
                payment_date,
                "PAYMENT_PRINCIPAL",
                payment_id,
                "principal",
                credit=principal_payment
            )

            remaining -= principal_payment

    # 3. Settle outstanding legal charges

    legal_payment = min(
        remaining,
        balances["legal"]
    )

    if legal_payment > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            payment_date,
            "PAYMENT_LEGAL",
            payment_id,
            "legal",
            credit=legal_payment
        )

        remaining -= legal_payment

    # 4. Remaining amount becomes advance

    if remaining > 0:

        post_ledger_entry(
            ledger,
            balances,
            flat_id,
            payment_date,
            "ADVANCE_CREDIT",
            payment_id,
            "advance",
            credit=remaining
        )

    return balances


# ==================================================
# 25. SAVE LEDGER TO CSV
# ==================================================

def save_ledger_to_csv(ledger):

    output_folder = (
        Path(__file__).resolve().parent.parent / "outputs"
    )

    output_folder.mkdir(exist_ok=True)

    output_file = output_folder / "ledger.csv"

    fieldnames = [
        "flat_id",
        "posting_date",
        "entry_type",
        "reference",
        "debit",
        "credit",
        "principal_balance",
        "interest_balance",
        "legal_balance",
        "advance_balance"
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(ledger)

    print("Ledger saved successfully!")
    print("File:", output_file)
    print("Number of entries:", len(ledger))

# ==================================================
# 26. UPDATE DEFAULTER STATES
# ==================================================

def update_defaulter_states(
    data,
    ledger,
    balances,
    flat_id,
    as_of_date,
    bill_balances,
    defaulter_states,
    defaulter_timeline
):

    current_date = date.fromisoformat(
        as_of_date[:10]
    )

    # Count bills that are overdue and not fully paid.
    arrears_months = 0

    for bill in bill_balances.values():

        if bill["flat_id"] != flat_id:
            continue

        due_date = date.fromisoformat(
            bill["due_date"][:10]
        )

        outstanding = Decimal(
            str(bill["outstanding"])
        )

        if due_date < current_date and outstanding > 0:
            arrears_months += 1

    # Determine the new defaulter state.
    if arrears_months >= 6:
        new_state = "LEGAL"

    elif arrears_months >= 3:
        new_state = "NOTICE"

    elif arrears_months == 2:
        new_state = "REMINDER"

    else:
        new_state = "NORMAL"

    old_state = defaulter_states.get(
        flat_id,
        "NORMAL"
    )

    # Record only state changes.
    if new_state != old_state:

        legal_charge_added = False

        # Add legal charge when entering LEGAL.
        if new_state == "LEGAL":

            legal_charge_already_posted = any(
                entry["flat_id"] == flat_id
                and entry["entry_type"] == "LEGAL_CHARGE"
                for entry in ledger
            )

            if not legal_charge_already_posted:

                legal_charge = get_rate(
                    data,
                    "LEGAL_CHARGE",
                    as_of_date
                )

                post_ledger_entry(
                    ledger,
                    balances[flat_id],
                    flat_id,
                    as_of_date,
                    "LEGAL_CHARGE",
                    "LEGAL-" + flat_id,
                    "legal",
                    debit=legal_charge
                )

                legal_charge_added = True

        defaulter_timeline.append({
            "flat_id": flat_id,
            "change_date": as_of_date,
            "from_state": old_state,
            "to_state": new_state,
            "arrears_months": arrears_months,
            "amenities_suspended": (
                new_state in ["NOTICE", "LEGAL"]
            ),
            "legal_charge_added": legal_charge_added
        })

        defaulter_states[flat_id] = new_state

    return arrears_months

if __name__ == "__main__":

    data = load_data()
    commands = load_commands()

    # ----------------------------------------------
    # Test 1: Unauthorised parking
    # ----------------------------------------------

    print("\nUNAUTHORISED PARKING TEST")
    print("=========================")

    for month in ["2026-03", "2026-04", "2026-05"]:
        charge = calculate_unauthorised_parking(
            data, commands, "FLT-B602", month
        )
        print(f"{month} : {charge:.2f}")

    # ----------------------------------------------
    # Test 2: Water tanker allocation
    # ----------------------------------------------

    print("\nWATER TANKER TEST")
    print("=================")

    for flat_id in ["FLT-A001", "FLT-A002", "FLT-A802"]:
        for month in ["2026-03", "2026-04"]:
            charge = calculate_water_tanker(
                data, commands, flat_id, month
            )
            print(f"{flat_id} | {month} : Rs. {charge:.2f}")

    # ----------------------------------------------
    # Test 3: Water tanker reconciliation
    # ----------------------------------------------

    print("\nWATER TANKER RECONCILIATION")
    print("===========================")

    for month in ["2026-03", "2026-04", "2026-05"]:

        total_allocated = sum(
            (
                calculate_water_tanker(
                    data, commands, flat["flat_id"], month
                )
                for flat in data["flats"]
            ),
            Decimal("0.00")
        )

        total_expense = sum(
            (
                Decimal(expense["amount"])
                for expense in data["expenses"]
                if expense["head"] == "WATER_TANKER"
                and expense["expense_month"][:7] == month
            ),
            Decimal("0.00")
        )

        print(f"\nMonth: {month}")
        print(f"Expense:   Rs. {total_expense:.2f}")
        print(f"Allocated: Rs. {total_allocated:.2f}")
        print(
            f"Difference: Rs. "
            f"{total_expense - total_allocated:.2f}"
        )

    # ----------------------------------------------
    # Test 4: GST calculation
    # ----------------------------------------------

    print("\nGST TEST")
    print("========")

    for maintenance in [
        Decimal("7000"),
        Decimal("7500"),
        Decimal("8000")
    ]:
        gst = calculate_gst(
            data, maintenance, "2026-08-01"
        )

        print(
            f"Maintenance: Rs. {maintenance:.2f}"
            f" | GST: Rs. {gst:.2f}"
        )

    # ----------------------------------------------
    # Test 5: Complete monthly bill
    # ----------------------------------------------

    print("\nCOMPLETE MONTHLY BILL TEST")
    print("==========================")

    bill = calculate_full_monthly_bill(
        data,
        commands,
        "FLT-B501",
        "2026-08-01",
        "2026-09-01"
    )

    for key, value in bill.items():
        print(f"{key}: {value}")

    # ----------------------------------------------
    # Test 6: Generate bills for all flats
    # ----------------------------------------------

    print("\nALL FLATS BILL GENERATION TEST")
    print("==============================")

    all_bills = generate_monthly_bills(
        data,
        commands,
        "2026-08-01",
        "2026-09-01"
    )

    print("Number of bills generated:", len(all_bills))

    save_bills_to_csv(all_bills)

    print("\nFirst 5 bills:")

    for bill in all_bills[:5]:
        print(
            bill["bill_id"],
            "|",
            bill["flat_id"],
            "| Rs.",
            bill["bill_total"]
        )

    # ----------------------------------------------
    # Test 7: Display advance payment commands
    # ----------------------------------------------

    print("\nADVANCE PAYMENT COMMANDS")
    print("========================")

    for command in commands:
        if command.startswith("ADVANCE|"):
            print(command)

    # ----------------------------------------------
    # Test 8: Advance payment calculation
    # ----------------------------------------------

    print("\nADVANCE PAYMENT CALCULATION TEST")
    print("================================")

    flat_id = "FLT-A801"

    area, rate, rounded_monthly_maintenance = (
        calculate_base_maintenance(
            data,
            flat_id,
            "2025-11-01"
        )
    )

    raw_monthly_maintenance = area * rate
    number_of_months = 12

    total_maintenance = (
        raw_monthly_maintenance * number_of_months
    )

    discount_percentage = get_rate(
        data,
        "ADVANCE_DISCOUNT_PCT",
        "2025-11-01"
    )

    discount = (
        total_maintenance
        * discount_percentage
        / Decimal("100")
    )

    expected_advance = total_maintenance - discount

    print("Flat:", flat_id)
    print("Area:", area)
    print("Maintenance rate:", rate)
    print(
        "Rounded monthly maintenance:",
        rounded_monthly_maintenance
    )
    print(
        "Unrounded monthly maintenance:",
        raw_monthly_maintenance
    )
    print("Number of months:", number_of_months)
    print("Total maintenance:", total_maintenance)
    print("Discount:", discount)
    print("Expected advance:", expected_advance)
    print(
        "Expected advance rounded to rupee:",
        round_rupee(expected_advance)
    )

    # ----------------------------------------------
    # Test 9: Water meter replacement
    # ----------------------------------------------

    print("\nWATER METER REPLACEMENT TEST")
    print("============================")

    for month in ["2026-05", "2026-06", "2026-07"]:

        result = calculate_water_charge(
            data,
            commands,
            "FLT-A501",
            month
        )

        print(
            f"{month} | "
            f"Method: {result['method']} | "
            f"Consumption: {result['consumption']} | "
            f"Charge: Rs. {result['water_charge']}"
        )

    # ----------------------------------------------
    # Test 10: Actual advance application
    # ----------------------------------------------

    print("\nADVANCE APPLICATION TEST")
    print("========================")

    for month in [
        "2025-11",
        "2025-12",
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
        "2026-11"
    ]:

        monthly = calculate_monthly_charges(
            data,
            commands,
            "FLT-A801",
            month + "-01"
        )

        advance = calculate_advance_applied(
            data,
            commands,
            "FLT-A801",
            month,
            monthly["maintenance"],
            "2026-12-01"
        )

        print(
            f"{month} | "
            f"Maintenance: Rs. {monthly['maintenance']} | "
            f"Advance applied: Rs. {advance}"
        )

    # ----------------------------------------------
    # Test 11: Check complete bill with advance
    # ----------------------------------------------

    print("\nFLT-A801 BILL WITH ADVANCE TEST")
    print("===============================")

    advance_bill = calculate_full_monthly_bill(
        data,
        commands,
        "FLT-A801",
        "2026-02-01",
        "2026-03-01"
    )

    for key, value in advance_bill.items():
        print(f"{key}: {value}")

    # ----------------------------------------------
    # Test 12: Basic ledger test
    # ----------------------------------------------

    print("\nBASIC LEDGER TEST")
    print("=================")

    test_ledger = []

    all_balances = create_flat_balances(data)
    test_balances = all_balances["FLT-A001"]

    post_ledger_entry(
        test_ledger,
        test_balances,
        "FLT-A001",
        "2026-09-01",
        "BILL",
        "BILL-001",
        "principal",
        debit=Decimal("12000.00")
    )

    post_ledger_entry(
        test_ledger,
        test_balances,
        "FLT-A001",
        "2026-09-10",
        "PAYMENT",
        "PAY-001",
        "principal",
        credit=Decimal("5000.00")
    )

    print(test_ledger)
    print("Final balance:", test_balances)

    # ----------------------------------------------
    # Test 13: Payment allocation
    # ----------------------------------------------

    print("\nPAYMENT ALLOCATION TEST")
    print("=======================")

    test_ledger = []

    all_balances = create_flat_balances(data)
    test_balances = all_balances["FLT-A001"]

    test_balances["interest"] = Decimal("500.00")
    test_balances["principal"] = Decimal("10000.00")

    allocate_payment(
        test_ledger,
        test_balances,
        "FLT-A001",
        "2026-11-10",
        "PAY-TEST-002",
        Decimal("12000.00")
    )

    for entry in test_ledger:
        print(entry)

    print("\nFinal balances:")
    print(test_balances)

    # ----------------------------------------------
    # Test 14: Save ledger CSV
    # ----------------------------------------------

    print("\nSAVE LEDGER CSV TEST")
    print("====================")

    save_ledger_to_csv(test_ledger)

    print("Ledger CSV saved successfully.")

    # ----------------------------------------------
    # Test 15: Post one generated bill to ledger
    # ----------------------------------------------

    print("\nPOST BILL TO LEDGER TEST")
    print("========================")

    test_ledger = []

    all_balances = create_flat_balances(data)
    test_balances = all_balances["FLT-A001"]

    test_bill = calculate_full_monthly_bill(
        data,
        commands,
        "FLT-A001",
        "2026-08-01",
        "2026-09-01"
    )

    post_bill_to_ledger(
        test_ledger,
        test_balances,
        test_bill
    )

    for entry in test_ledger:
        print(entry)

    print("\nFinal balances:")
    print(test_balances)

    # ----------------------------------------------
    # Individual bill balance test
    # ----------------------------------------------

    print("\nINDIVIDUAL BILL BALANCE TEST")
    print("============================")

    bill_balances = create_bill_balances()

    test_bill = {
        "bill_id": "BILL-FLT-A001-2026-08",
        "flat_id": "FLT-A001",
        "bill_date": "2026-09-01",
        "due_date": "2026-09-15",
        "advance_applied": "0.00",
        "bill_total": "12559.00"
    }

    balances = {
        "principal": Decimal("0.00"),
        "interest": Decimal("0.00"),
        "legal": Decimal("0.00"),
        "advance": Decimal("0.00")
    }

    ledger = []

    post_bill_to_ledger(
        ledger,
        balances,
        test_bill,
        bill_balances
    )

    print("\nTRACKED BILL")
    print("============")
    print(bill_balances)

    # ----------------------------------------------
    # Oldest bill payment test
    # ----------------------------------------------

    print("\nOLDEST BILL PAYMENT TEST")
    print("========================")

    test_balances = {
        "principal": Decimal("15000.00"),
        "interest": Decimal("0.00"),
        "legal": Decimal("0.00"),
        "advance": Decimal("0.00")
    }

    test_ledger = []

    test_bill_balances = {
        "BILL-OLD": {
            "flat_id": "FLT-A001",
            "bill_date": "2026-07-01",
            "due_date": "2026-07-15",
            "outstanding": Decimal("5000.00")
        },
        "BILL-NEW": {
            "flat_id": "FLT-A001",
            "bill_date": "2026-08-01",
            "due_date": "2026-08-15",
            "outstanding": Decimal("10000.00")
        }
    }

    allocate_payment(
        test_ledger,
        test_balances,
        "FLT-A001",
        "2026-09-10",
        "PAY-OLDEST-001",
        Decimal("6000.00"),
        test_bill_balances
    )

    print(
        "Old bill remaining:",
        test_bill_balances["BILL-OLD"]["outstanding"]
    )

    print(
        "New bill remaining:",
        test_bill_balances["BILL-NEW"]["outstanding"]
    )

    print(
        "Total principal remaining:",
        test_balances["principal"]
    )

        # ----------------------------------------------
    # Interest first payment test
    # ----------------------------------------------

    print("\nINTEREST FIRST PAYMENT TEST")
    print("============================")

    test_balances = {
        "principal": Decimal("10000.00"),
        "interest": Decimal("500.00"),
        "legal": Decimal("0.00"),
        "advance": Decimal("0.00")
    }

    test_ledger = []

    test_bill_balances = {
        "BILL-OLD": {
            "flat_id": "FLT-A001",
            "bill_date": "2026-07-01",
            "due_date": "2026-07-15",
            "outstanding": Decimal("10000.00")
        }
    }

    allocate_payment(
        test_ledger,
        test_balances,
        "FLT-A001",
        "2026-09-10",
        "PAY-INTEREST-001",
        Decimal("2000.00"),
        test_bill_balances
    )

    print("Interest remaining:", test_balances["interest"])
    print("Principal remaining:", test_balances["principal"])
    print(
        "Bill remaining:",
        test_bill_balances["BILL-OLD"]["outstanding"]
    )



def create_income_statement(data, bills, from_month, to_month):

    from_month = from_month[:7]
    to_month = to_month[:7]

    # Income and expense heads
    heads = [
        "MAINTENANCE",
        "SINKING_FUND",
        "NON_OCCUPANCY",
        "WATER",
        "COMMON_ELECTRICITY",
        "GENERATOR_DIESEL",
        "LIFT_AMC",
        "WATER_TANKER",
        "PARKING",
        "UNAUTHORISED_PARKING",
        "GST"
    ]

    statement = {}

    # Create empty statement rows
    for head in heads:
        statement[head] = {
            "head": head,
            "billed": Decimal("0.00"),
            "collected": "",
            "expense": Decimal("0.00"),
            "surplus": Decimal("0.00")
        }

    # Map bill columns to income heads
    bill_mapping = {
        "MAINTENANCE": "maintenance",
        "SINKING_FUND": "sinking_fund",
        "NON_OCCUPANCY": "non_occupancy",
        "WATER": "water",
        "COMMON_ELECTRICITY": "common_electricity",
        "GENERATOR_DIESEL": "generator_diesel",
        "LIFT_AMC": "lift_amc",
        "WATER_TANKER": "water_tanker",
        "PARKING": "parking",
        "UNAUTHORISED_PARKING": "unauthorised_parking",
        "GST": "gst"
    }

    # Calculate billed amounts
    for bill in bills:

        month = bill["covered_month"][:7]

        if not from_month <= month <= to_month:
            continue

        for head, column in bill_mapping.items():

            amount = Decimal(str(bill[column]))

            statement[head]["billed"] += amount

    # Calculate expenses
    for expense in data["expenses"]:

        month = expense["expense_month"][:7]

        if not from_month <= month <= to_month:
            continue

        head = expense["head"]

        amount = Decimal(str(expense["amount"]))

        # Security and housekeeping are funded from maintenance
        if head in ("SECURITY", "HOUSEKEEPING"):

            statement["MAINTENANCE"]["expense"] += amount

        elif head in statement:

            statement[head]["expense"] += amount

    # Calculate surplus for each head
    for head in statement:

        billed = statement[head]["billed"]
        expense = statement[head]["expense"]

        statement[head]["surplus"] = billed - expense

    return list(statement.values())
