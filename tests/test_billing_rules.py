
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))

from billing_rules import (
    money,
    whole_rupee,
    calculate_maintenance,
    calculate_sinking_fund,
    calculate_non_occupancy,
    calculate_gst
)


def test_money_rounding():
    assert money("100.456") == Decimal("100.46")
    assert money("100.454") == Decimal("100.45")


def test_whole_rupee():
    assert whole_rupee("100.50") == 101
    assert whole_rupee("100.49") == 100


def test_maintenance():
    assert calculate_maintenance(2000, 3.75, "OWNER") == Decimal("7500.00")


def test_vacant_maintenance():
    assert calculate_maintenance(2000, 3.75, "VACANT", True) == Decimal("3750.00")


def test_sinking_fund():
    assert calculate_sinking_fund(2000, 0.50) == Decimal("1000.00")


def test_tenant_non_occupancy():
    assert calculate_non_occupancy(7500, 10, "TENANT") == Decimal("750.00")


def test_owner_non_occupancy():
    assert calculate_non_occupancy(7500, 10, "OWNER") == Decimal("0.00")


def test_gst_exact_threshold():
    assert calculate_gst(7500, 7500, 18, True) == Decimal("0.00")


def test_gst_above_threshold():
    assert calculate_gst(7501, 7500, 18, True) == Decimal("1350.18")


tests = [
    test_money_rounding,
    test_whole_rupee,
    test_maintenance,
    test_vacant_maintenance,
    test_sinking_fund,
    test_tenant_non_occupancy,
    test_owner_non_occupancy,
    test_gst_exact_threshold,
    test_gst_above_threshold
]


if __name__ == "__main__":
    for test in tests:
        test()
        print("PASSED:", test.__name__)

    print("\nAll 9 tests passed successfully!")
