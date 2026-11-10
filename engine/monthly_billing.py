
import csv
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date
from calendar import monthrange

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from billing_rules import (
    money,
    whole_rupee,
    get_effective_rate,
    calculate_maintenance,
    calculate_sinking_fund,
    calculate_non_occupancy,
    calculate_gst
)

from expense_allocation import allocate_expense


# --------------------------------------------------
# LOAD CSV FILES
# --------------------------------------------------

def load_csv(filename):
    file_path = INPUT_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# GET EFFECTIVE RATE
# --------------------------------------------------

def get_rate(rates, code, month):
    return get_effective_rate(rates, code, month)


# --------------------------------------------------
# GET ALL BILLING MONTHS
# --------------------------------------------------

def get_billing_months(readings, rates):

    maintenance_rates = [
        row for row in rates
        if row["rate_code"] == "MAINT_PER_SQFT"
    ]

    if not maintenance_rates:
        raise ValueError("Maintenance rate not found in rates.csv")

    first_billing_month = min(
        row["effective_from"] for row in maintenance_rates
    )

    reading_months = [
        date.fromisoformat(row["reading_date"]).strftime("%Y-%m-01")
        for row in readings
    ]

    if not reading_months:
        raise ValueError("No meter readings found")

    last_reading_month = max(reading_months)

    months = sorted({
        month for month in reading_months
        if month >= first_billing_month
    })

    if not months:
        raise ValueError("No billing months found after maintenance rate start")

    expected_months = []

    current = date.fromisoformat(first_billing_month)
    last = date.fromisoformat(last_reading_month)

    while current <= last:
        expected_months.append(current.strftime("%Y-%m-01"))

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    missing_months = [
        month for month in expected_months
        if month not in months
    ]

    if missing_months:
        raise ValueError(f"Missing meter-reading months: {missing_months}")

    return months


# --------------------------------------------------
# OCCUPANCY DETAILS
# --------------------------------------------------

def get_occupancy_details(flats, month):

    month_start = date.fromisoformat(month)

    last_day = monthrange(month_start.year, month_start.month)[1]
    month_end = date(month_start.year, month_start.month, last_day)

    occupancy = {
        flat["flat_id"]: flat["occupancy"].strip().upper()
        for flat in flats
    }

    events = []
    commands_file = INPUT_DIR / "commands.txt"

    with open(commands_file, "r", encoding="utf-8-sig") as file:
        for line in file:

            parts = line.strip().split("|")

            if len(parts) < 4:
                continue

            if parts[0].strip().upper() != "DECLARE_OCCUPANCY":
                continue

            flat_id = parts[1].strip()
            new_status = parts[2].strip().upper()
            effective_date = date.fromisoformat(parts[3].strip())

            events.append((flat_id, new_status, effective_date))

    events.sort(key=lambda event: event[2])

    for flat_id, new_status, effective_date in events:
        if effective_date <= month_start and flat_id in occupancy:
            occupancy[flat_id] = new_status

    full_month_vacant = set()

    for flat_id, status in occupancy.items():

        if status != "VACANT":
            continue

        changed_during_month = any(
            event_flat_id == flat_id
            and month_start < effective_date <= month_end
            for event_flat_id, new_status, effective_date in events
        )

        if not changed_during_month:
            full_month_vacant.add(flat_id)

    return occupancy, full_month_vacant


# --------------------------------------------------
# WATER BILL CALCULATION
# --------------------------------------------------

def calculate_water(flat, readings, rates, month):

    water_rate = get_rate(rates, "WATER_PER_KL", month)
    head_rate = get_rate(rates, "WATER_PER_HEAD", month)

    residents = Decimal(flat["declared_residents"])
    has_meter = flat["has_water_meter"].strip().upper()

    # Flats without water meters use per-head billing.
    if has_meter in ("NO", "N", "FALSE", "0"):
        return Decimal(whole_rupee(residents * head_rate))

    billing_date = date.fromisoformat(month)

    current_readings = [
        r for r in readings
        if r["flat_id"] == flat["flat_id"]
        and date.fromisoformat(r["reading_date"]).year == billing_date.year
        and date.fromisoformat(r["reading_date"]).month == billing_date.month
    ]

    previous_readings = [
        r for r in readings
        if r["flat_id"] == flat["flat_id"]
        and date.fromisoformat(r["reading_date"]) < billing_date
    ]

    if not current_readings or not previous_readings:
        raise ValueError(
            f"Missing water reading for {flat['flat_id']} in {month}"
        )

    current = max(current_readings, key=lambda r: r["reading_date"])
    previous = max(previous_readings, key=lambda r: r["reading_date"])

    current_value = Decimal(current["reading_kl"])
    previous_value = Decimal(previous["reading_kl"])

    # Meter replacement or meter rollback.
    if current_value < previous_value:
        return Decimal(whole_rupee(residents * head_rate))

    consumption = current_value - previous_value

    # Round each flat's water charge to a whole rupee.
    return Decimal(whole_rupee(consumption * water_rate))


# --------------------------------------------------
# CALCULATE INDIVIDUAL FLAT BILL
# --------------------------------------------------

def calculate_flat_bill(
    flat,
    rates,
    readings,
    month,
    occupancy,
    full_month_vacant
):

    area = Decimal(flat["super_builtup_sqft"])

    maintenance_rate = get_rate(rates, "MAINT_PER_SQFT", month)
    sinking_rate = get_rate(rates, "SINKING_PER_SQFT", month)

    maintenance = calculate_maintenance(
        area, maintenance_rate, occupancy, full_month_vacant
    )

    sinking_fund = calculate_sinking_fund(area, sinking_rate)

    non_occupancy = calculate_non_occupancy(
        maintenance,
        get_rate(rates, "NON_OCCUPANCY_PCT", month),
        occupancy
    )

    water = calculate_water(flat, readings, rates, month)

    gst_threshold = get_rate(rates, "GST_MAINT_THRESHOLD", month)
    gst_rate = get_rate(rates, "GST_PCT", month)
    society_threshold = get_rate(rates, "GST_SOCIETY_THRESHOLD", month)

    society = load_csv("society.csv")[0]

    society_eligible = (
        Decimal(society["prior_fy_collection"]) > society_threshold
    )

    gst = calculate_gst(
        maintenance,
        gst_threshold,
        gst_rate,
        society_eligible
    )

    total = (
        maintenance
        + sinking_fund
        + non_occupancy
        + water
        + gst
    )

    return {
        "flat_id": flat["flat_id"],
        "month": month,
        "maintenance": money(maintenance),
        "sinking_fund": money(sinking_fund),
        "non_occupancy": money(non_occupancy),
        "water": water,
        "gst": money(gst),
        "lift_amc": Decimal("0.00"),
        "common_electricity": Decimal("0.00"),
        "generator_diesel": Decimal("0.00"),
        "water_tanker": Decimal("0.00"),
        "total": whole_rupee(total)
    }


# --------------------------------------------------
# ADD SHARED EXPENSES
# --------------------------------------------------

def add_shared_expenses(bills, flats, month, full_month_vacant):

    expenses = load_csv("expenses.csv")

    monthly_expenses = [
        expense for expense in expenses
        if expense["expense_month"] == month
    ]

    bill_lookup = {
        bill["flat_id"]: bill for bill in bills
    }

    expense_fields = {
        "LIFT_AMC": "lift_amc",
        "COMMON_ELECTRICITY": "common_electricity",
        "GENERATOR_DIESEL": "generator_diesel",
        "WATER_TANKER": "water_tanker"
    }

    for expense in monthly_expenses:

        head = expense["head"].strip().upper()

        if head in ("SECURITY", "HOUSEKEEPING"):
            continue

        if head not in expense_fields:
            continue

        if head == "WATER_TANKER":
            eligible_flats = [
                flat for flat in flats
                if flat["flat_id"] not in full_month_vacant
            ]
        else:
            eligible_flats = flats

        allocations = allocate_expense(expense, eligible_flats)

        field = expense_fields[head]

        for allocation in allocations:
            flat_id = allocation["flat_id"]
            bill_lookup[flat_id][field] += allocation["amount"]

    # Recalculate totals after shared expenses.
    for bill in bills:

        total = (
            Decimal(str(bill["maintenance"]))
            + Decimal(str(bill["sinking_fund"]))
            + Decimal(str(bill["non_occupancy"]))
            + Decimal(str(bill["water"]))
            + Decimal(str(bill["gst"]))
            + bill["lift_amc"]
            + bill["common_electricity"]
            + bill["generator_diesel"]
            + bill["water_tanker"]
        )

        bill["total"] = whole_rupee(total)

    return bills


# --------------------------------------------------
# GENERATE BILLS FOR ALL AVAILABLE MONTHS
# --------------------------------------------------

def main():

    flats = load_csv("flats.csv")
    rates = load_csv("rates.csv")
    readings = load_csv("meter_readings.csv")

    months = get_billing_months(readings, rates)

    all_bills = []

    print("\nGENERATING MONTHLY BILLS")
    print("------------------------")

    for month in months:

        print(f"\nProcessing: {month}")

        occupancy, full_month_vacant = get_occupancy_details(
            flats, month
        )

        bills = []

        for flat in flats:

            flat_id = flat["flat_id"]

            bill = calculate_flat_bill(
                flat,
                rates,
                readings,
                month,
                occupancy[flat_id],
                flat_id in full_month_vacant
            )

            bills.append(bill)

        bills = add_shared_expenses(
            bills,
            flats,
            month,
            full_month_vacant
        )

        all_bills.extend(bills)

        print("Flats processed:", len(bills))

    if not all_bills:
        raise ValueError("No monthly bills were generated")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "monthly_bills.csv"

    with open(output_file, "w", encoding="utf-8-sig", newline="") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=all_bills[0].keys()
        )

        writer.writeheader()
        writer.writerows(all_bills)

    print("\nALL MONTHLY BILLS GENERATED")
    print("---------------------------")
    print("Total months:", len(months))
    print("Total bill records:", len(all_bills))
    print("Months:", months[0], "to", months[-1])
    print("Output saved:", output_file)

    print("\nFirst five bills:")

    for bill in all_bills[:5]:
        print(bill)


if __name__ == "__main__":
    main()
