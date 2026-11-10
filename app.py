
from flask import Flask, render_template
from pathlib import Path
from decimal import Decimal
from database import read_table
import csv

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "outputs"


# READ DATA FROM SQLITE DATABASE
# USE CSV AS FALLBACK


def read_csv(file_path):
    """Read data from SQLite; use CSV if the table is empty or unavailable."""

    table_name = file_path.stem.replace("-", "_")

    try:
        data = read_table(table_name)

        if len(data) > 0:
            return data

    except (Exception):
        pass

    if not file_path.exists():
        return []

    with open(
        file_path,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        return list(csv.DictReader(file))




def decimal_value(value):
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


# DASHBOARD PAGE
@app.route("/")
def dashboard():

    flats = read_csv(INPUT_DIR / "flats.csv")
    towers = read_csv(INPUT_DIR / "towers.csv")
    bills = read_csv(OUTPUT_DIR / "monthly_bills.csv")
    flat_ledger = read_csv(OUTPUT_DIR / "flat_ledger.csv")
    payments = read_csv(OUTPUT_DIR / "payments.csv")
    expenses = read_csv(INPUT_DIR / "expenses.csv")

    total_flats = len(flats)
    total_towers = len(towers)

    latest_month = max(
        (row["month"] for row in bills),
        default=""
    )

    monthly_bill_count = sum(
        1 for row in bills
        if row["month"] == latest_month
    )

    pending_payments = sum(
        1 for row in flat_ledger
        if decimal_value(row.get("total_outstanding")) > 0
    )

    total_outstanding = sum(
        (
            decimal_value(row.get("total_outstanding"))
            for row in flat_ledger
        ),
        Decimal("0.00")
    )

    # TOTAL PAYMENT COLLECTION
    total_payment_collection = sum(
        (decimal_value(row.get("amount")) for row in payments),
        Decimal("0.00")
    )

    # TOTAL EXPENSES
    total_expenses = sum(
        (decimal_value(row.get("amount")) for row in expenses),
        Decimal("0.00")
    )

    # OCCUPANCY DISTRIBUTION
    occupancy_counts = {}

    for flat in flats:
        status = flat.get("occupancy", "UNKNOWN").strip().upper()

        occupancy_counts[status] = (
            occupancy_counts.get(status, 0) + 1
        )

    occupancy_labels = list(occupancy_counts.keys())
    occupancy_values = list(occupancy_counts.values())

    # MONTHLY BILLING TOTALS
    billing_totals = {}

    for bill in bills:
        month = bill["month"][:7]

        billing_totals[month] = (
            billing_totals.get(month, Decimal("0.00"))
            + decimal_value(bill.get("total"))
        )

    # MONTHLY PAYMENT COLLECTION TOTALS
    payment_totals = {}

    for payment in payments:

        date_value = payment.get("payment_date", "")
        amount_value = payment.get("amount", "0")

        if date_value:
            month = date_value[:7]

            payment_totals[month] = (
                payment_totals.get(month, Decimal("0.00"))
                + decimal_value(amount_value)
            )

    # COMBINE MONTHS FOR CHART
    all_months = sorted(
        set(billing_totals.keys()) |
        set(payment_totals.keys())
    )

    billing_chart = [
        float(billing_totals.get(month, Decimal("0.00")))
        for month in all_months
    ]

    payment_chart = [
        float(payment_totals.get(month, Decimal("0.00")))
        for month in all_months
    ]

    # TOP 10 FLATS WITH OUTSTANDING BALANCES
    outstanding_flats = [
        row for row in flat_ledger
        if decimal_value(row.get("total_outstanding")) > 0
    ]

    outstanding_flats.sort(
        key=lambda row: decimal_value(row.get("total_outstanding")),
        reverse=True
    )

    outstanding_flats = outstanding_flats[:10]

    outstanding_labels = [
        row["flat_id"] for row in outstanding_flats
    ]

    outstanding_values = [
        float(decimal_value(row.get("total_outstanding")))
        for row in outstanding_flats
    ]

    return render_template(
        "dashboard.html",
        total_flats=total_flats,
        total_towers=total_towers,
        monthly_bills=monthly_bill_count,
        pending_payments=pending_payments,
        total_outstanding=total_outstanding,
        latest_month=latest_month,
        chart_months=all_months,
        billing_chart=billing_chart,
        payment_chart=payment_chart,
        outstanding_labels=outstanding_labels,
        outstanding_values=outstanding_values,
        total_payment_collection=total_payment_collection,
        total_expenses=total_expenses,
        occupancy_labels=occupancy_labels,
        occupancy_values=occupancy_values
    )


# RESIDENTS PAGE
@app.route("/residents")
def residents():

    flats = read_csv(INPUT_DIR / "flats.csv")
    owners = read_csv(INPUT_DIR / "owners.csv")

    owner_lookup = {
        owner["owner_id"]: owner
        for owner in owners
    }

    resident_data = []

    for flat in flats:

        owner = owner_lookup.get(flat["owner_id"], {})

        resident_data.append({
            "flat_id": flat["flat_id"],
            "tower_id": flat["tower_id"],
            "floor": flat["floor"],
            "owner_id": flat["owner_id"],
            "owner_name": owner.get("owner_name", "Not Available"),
            "occupancy": flat["occupancy"],
            "area": flat["super_builtup_sqft"]
        })

    return render_template(
        "residents.html",
        residents=resident_data
    )


# MONTHLY BILLS PAGE
@app.route("/bills")
def monthly_bills_page():

    bills = read_csv(OUTPUT_DIR / "monthly_bills.csv")

    bills.sort(
        key=lambda row: (row["month"], row["flat_id"]),
        reverse=True
    )

    total_bills = len(bills)

    total_amount = sum(
        (decimal_value(row["total"]) for row in bills),
        Decimal("0.00")
    )

    return render_template(
        "monthly_bills.html",
        bills=bills,
        total_bills=total_bills,
        total_amount=total_amount
    )


# PAYMENTS PAGE
@app.route("/payments")
def payments():

    payment_data = read_csv(OUTPUT_DIR / "payments.csv")

    return render_template(
        "payments.html",
        payments=payment_data,
        total_payments=len(payment_data)
    )


# DEFAULTERS PAGE
@app.route("/defaulters")
def defaulters():

    reports = [
        {
            "date": "2026-06-20",
            "records": read_csv(
                OUTPUT_DIR / "defaulters_2026-06-20.csv"
            )
        },
        {
            "date": "2026-11-03",
            "records": read_csv(
                OUTPUT_DIR / "defaulters_2026-11-03.csv"
            )
        }
    ]

    return render_template(
        "defaulters.html",
        reports=reports
    )


# OWNERSHIP TRANSFER PAGE
@app.route("/ownership")
def ownership():

    ndc_records = read_csv(OUTPUT_DIR / "ndc_status.csv")
    ownership_records = read_csv(OUTPUT_DIR / "ownership_history.csv")
    settlement_records = read_csv(OUTPUT_DIR / "resale_settlements.csv")

    return render_template(
        "ownership.html",
        ndc_records=ndc_records,
        ownership_records=ownership_records,
        settlement_records=settlement_records
    )


# WATER READINGS PAGE
@app.route("/water")
def water():

    readings = read_csv(INPUT_DIR / "meter_readings.csv")
    flats = read_csv(INPUT_DIR / "flats.csv")
    rates = read_csv(INPUT_DIR / "rates.csv")

    # GET WATER RATES
    water_per_kl = Decimal("25")
    water_per_head = Decimal("150")

    for rate in rates:

        if rate["rate_code"] == "WATER_PER_KL":
            water_per_kl = decimal_value(rate["value"])

        elif rate["rate_code"] == "WATER_PER_HEAD":
            water_per_head = decimal_value(rate["value"])

    # FLAT LOOKUP
    flat_lookup = {
        flat["flat_id"]: flat
        for flat in flats
    }

    # SORT READINGS
    readings.sort(
        key=lambda row: (row["flat_id"], row["reading_date"])
    )

    water_data = []
    previous_readings = {}

    for reading in readings:

        flat_id = reading["flat_id"]
        current_reading = decimal_value(reading["reading_kl"])

        previous = previous_readings.get(flat_id)

        flat = flat_lookup.get(flat_id, {})

        residents = decimal_value(
            flat.get("declared_residents", 0)
        )

        if previous is None:

            consumption = Decimal("0")
            charge = Decimal("0")
            method = "Baseline Reading"

        elif current_reading < previous:

            # METER REPLACEMENT OR RESET
            consumption = Decimal("0")
            charge = residents * water_per_head
            method = "Per-Head Calculation (Meter Reset)"

        else:

            # NORMAL METER CONSUMPTION
            consumption = current_reading - previous
            charge = consumption * water_per_kl
            method = "Meter-Based Calculation"

        water_data.append({
            "reading_id": reading["reading_id"],
            "flat_id": flat_id,
            "reading_date": reading["reading_date"],
            "previous_reading": (
                previous if previous is not None else "-"
            ),
            "reading_kl": current_reading,
            "consumption": consumption,
            "method": method,
            "charge": charge,
            "remarks": reading.get("remarks", "")
        })

        previous_readings[flat_id] = current_reading

    total_readings = len(water_data)

    total_consumption = sum(
        (row["consumption"] for row in water_data),
        Decimal("0")
    )

    total_water_charges = sum(
        (row["charge"] for row in water_data),
        Decimal("0")
    )

    return render_template(
        "water.html",
        readings=water_data,
        total_readings=total_readings,
        total_consumption=total_consumption,
        total_water_charges=total_water_charges
    )


# RUN FLASK APPLICATION
if __name__ == "__main__":
    app.run(debug=True)
