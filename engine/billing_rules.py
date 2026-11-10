
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def whole_rupee(value):
    return int(
        Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def percentage(amount, rate):
    return money(
        Decimal(str(amount)) * Decimal(str(rate)) / Decimal("100")
    )


def get_effective_rate(rates, rate_code, covered_month):
    eligible = [
        rate for rate in rates
        if rate["rate_code"] == rate_code
        and rate["effective_from"] <= covered_month
    ]

    if not eligible:
        raise ValueError(f"No rate found for {rate_code}")

    selected = max(
        eligible,
        key=lambda rate: rate["effective_from"]
    )

    return Decimal(selected["value"])


def calculate_maintenance(area, rate, occupancy, full_month_vacant=False):
    amount = Decimal(str(area)) * Decimal(str(rate))

    if full_month_vacant:
        amount *= Decimal("0.50")

    return money(amount)


def calculate_sinking_fund(area, rate):
    return money(Decimal(str(area)) * Decimal(str(rate)))


def calculate_non_occupancy(maintenance, rate, occupancy):
    if occupancy == "TENANT":
        return percentage(maintenance, rate)

    return money(0)


def calculate_gst(maintenance, threshold, gst_rate, society_threshold_met):
    if not society_threshold_met:
        return money(0)

    if Decimal(str(maintenance)) <= Decimal(str(threshold)):
        return money(0)

    return percentage(maintenance, gst_rate)
