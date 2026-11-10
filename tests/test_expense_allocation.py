
from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent)
)

from engine.expense_allocation import allocate_expense


def sample_flats():
    return [
        {
            "flat_id": "A001",
            "tower_id": "TWR-A",
            "floor": "0",
            "super_builtup_sqft": "1000",
            "declared_residents": "3"
        },
        {
            "flat_id": "A002",
            "tower_id": "TWR-A",
            "floor": "1",
            "super_builtup_sqft": "1200",
            "declared_residents": "4"
        },
        {
            "flat_id": "A003",
            "tower_id": "TWR-B",
            "floor": "2",
            "super_builtup_sqft": "800",
            "declared_residents": "2"
        }
    ]


def test_security_not_allocated():

    result = allocate_expense(
        {"head": "SECURITY", "amount": "10000"},
        sample_flats()
    )

    assert result == []


def test_housekeeping_not_allocated():

    result = allocate_expense(
        {"head": "HOUSEKEEPING", "amount": "5000"},
        sample_flats()
    )

    assert result == []


def test_lift_amc_excludes_ground_floor():

    result = allocate_expense(
        {
            "head": "LIFT_AMC",
            "amount": "2000",
            "tower_id": "TWR-A"
        },
        sample_flats()
    )

    assert len(result) == 1
    assert result[0]["flat_id"] == "A002"
    assert result[0]["amount"] == Decimal("2000.00")


def test_electricity_area_allocation():

    result = allocate_expense(
        {
            "head": "COMMON_ELECTRICITY",
            "amount": "3000",
            "tower_id": ""
        },
        sample_flats()
    )

    amounts = {
        item["flat_id"]: item["amount"]
        for item in result
    }

    assert amounts["A001"] == Decimal("1000.00")
    assert amounts["A002"] == Decimal("1200.00")
    assert amounts["A003"] == Decimal("800.00")


def test_generator_diesel_area_allocation():

    result = allocate_expense(
        {
            "head": "GENERATOR_DIESEL",
            "amount": "2000",
            "tower_id": "TWR-A"
        },
        sample_flats()
    )

    amounts = {
        item["flat_id"]: item["amount"]
        for item in result
    }

    assert amounts["A001"] == Decimal("909.09")
    assert amounts["A002"] == Decimal("1090.91")


def test_water_tanker_equal_allocation():

    result = allocate_expense(
        {
            "head": "WATER_TANKER",
            "amount": "3000",
            "tower_id": ""
        },
        sample_flats()
    )

    amounts = {
        item["flat_id"]: item["amount"]
        for item in result
    }

    assert amounts["A001"] == Decimal("1000.00")
    assert amounts["A002"] == Decimal("1000.00")
    assert amounts["A003"] == Decimal("1000.00")


def test_unknown_expense():

    try:
        allocate_expense(
            {"head": "UNKNOWN", "amount": "1000"},
            sample_flats()
        )

        raise AssertionError("Unknown expense should raise ValueError")

    except ValueError as error:
        assert "Unknown expense head" in str(error)


def test_empty_flats():

    try:
        allocate_expense(
            {
                "head": "WATER_TANKER",
                "amount": "1000"
            },
            []
        )

        raise AssertionError("Empty flats should raise ValueError")

    except ValueError as error:
        assert "No eligible flats" in str(error)


if __name__ == "__main__":

    test_security_not_allocated()
    test_housekeeping_not_allocated()
    test_lift_amc_excludes_ground_floor()
    test_electricity_area_allocation()
    test_generator_diesel_area_allocation()
    test_water_tanker_equal_allocation()
    test_unknown_expense()
    test_empty_flats()

    print("\nAll 8 expense allocation tests passed!")
