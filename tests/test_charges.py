
import unittest
from decimal import Decimal

from src.billing import (
    calculate_base_maintenance,
    calculate_monthly_charges,
    calculate_water_charge,
    calculate_parking_charge,
    calculate_area_share,
    calculate_lift_amc,
    calculate_gst,
    calculate_water_tanker,
    calculate_advance_applied,
    calculate_unauthorised_parking,
)


class TestBillingCharges(unittest.TestCase):

    def setUp(self):
        self.data = {
            "flats": [
                {
                    "flat_id": "FLT-A001",
                    "super_builtup_sqft": "100",
                    "occupancy": "OWNER",
                    "declared_residents": "2",
                    "has_water_meter": "false",
                    "covered_slots": "1",
                    "open_slots": "2",
                    "floor": "1",
                    "tower_id": "TWR-A",
                },
                {
                    "flat_id": "FLT-A002",
                    "super_builtup_sqft": "100",
                    "occupancy": "OWNER",
                    "declared_residents": "2",
                    "has_water_meter": "false",
                    "covered_slots": "0",
                    "open_slots": "0",
                    "floor": "0",
                    "tower_id": "TWR-A",
                },
            ],
            "rates": [
                {"rate_code": "MAINT_PER_SQFT",
                 "effective_from": "2025-11-01", "value": "3.50"},
                {"rate_code": "NON_OCCUPANCY_PCT",
                 "effective_from": "2025-11-01", "value": "10"},
                {"rate_code": "VACANT_MAINT_PCT",
                 "effective_from": "2025-11-01", "value": "50"},
                {"rate_code": "SINKING_PER_SQFT",
                 "effective_from": "2025-11-01", "value": "0.50"},
                {"rate_code": "WATER_PER_KL",
                 "effective_from": "2025-11-01", "value": "25"},
                {"rate_code": "WATER_PER_HEAD",
                 "effective_from": "2025-11-01", "value": "150"},
                {"rate_code": "PARKING_COVERED",
                 "effective_from": "2025-11-01", "value": "500"},
                {"rate_code": "PARKING_OPEN",
                 "effective_from": "2025-11-01", "value": "250"},
                {"rate_code": "GST_MAINT_THRESHOLD",
                 "effective_from": "2025-11-01", "value": "7500"},
                {"rate_code": "GST_PCT",
                 "effective_from": "2025-11-01", "value": "18"},
            ],
            "meter_readings": [],
            "expenses": [
                {
                    "expense_month": "2025-11-01",
                    "head": "COMMON_ELECTRICITY",
                    "amount": "1000",
                    "tower_id": "",
                },
                {
                    "expense_month": "2025-11-01",
                    "head": "LIFT_AMC",
                    "amount": "1000",
                    "tower_id": "TWR-A",
                },
            ],
        }

    def test_base_maintenance(self):
        area, rate, amount = calculate_base_maintenance(
            self.data, "FLT-A001", "2025-11-01"
        )
        self.assertEqual(area, Decimal("100"))
        self.assertEqual(rate, Decimal("3.50"))
        self.assertEqual(amount, Decimal("350"))

    def test_owner_monthly_charges(self):
        result = calculate_monthly_charges(
            self.data, [], "FLT-A001", "2025-11-01"
        )
        self.assertEqual(result["maintenance"], Decimal("350"))
        self.assertEqual(result["non_occupancy_charge"], Decimal("0"))
        self.assertEqual(result["sinking_fund"], Decimal("50"))

    def test_tenant_non_occupancy_charge(self):
        commands = [
            "DECLARE_OCCUPANCY|FLT-A001|TENANT|2025-11-01|2"
        ]
        result = calculate_monthly_charges(
            self.data, commands, "FLT-A001", "2025-11-01"
        )
        self.assertEqual(result["non_occupancy_charge"], Decimal("35"))

    def test_unmetered_water_charge(self):
        result = calculate_water_charge(
            self.data, [], "FLT-A001", "2025-11"
        )
        self.assertEqual(result["method"], "PER_HEAD")
        self.assertEqual(result["water_charge"], Decimal("300"))

    def test_parking_charge(self):
        result = calculate_parking_charge(
            self.data, "FLT-A001", "2025-11-01"
        )
        self.assertEqual(result, Decimal("1000.00"))

    def test_area_based_expense_share(self):
        result = calculate_area_share(
            self.data, "FLT-A001", "2025-11",
            "COMMON_ELECTRICITY"
        )
        self.assertEqual(result, Decimal("500.00"))

    def test_lift_amc_for_eligible_floor(self):
        result = calculate_lift_amc(
            self.data, "FLT-A001", "2025-11"
        )
        self.assertEqual(result, Decimal("1000.00"))

    def test_ground_floor_has_no_lift_amc(self):
        result = calculate_lift_amc(
            self.data, "FLT-A002", "2025-11"
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_gst_at_threshold_is_zero(self):
        result = calculate_gst(
            self.data, Decimal("7500"), "2025-11-01"
        )
        self.assertEqual(result, Decimal("0.00"))

    def test_gst_above_threshold(self):
        result = calculate_gst(
            self.data, Decimal("8000"), "2025-11-01"
        )
        self.assertEqual(result, Decimal("1440.00"))

    def test_vacant_flat_maintenance(self):
        commands = [
            "DECLARE_OCCUPANCY|FLT-A001|VACANT|2025-11-01|0"
        ]

        result = calculate_monthly_charges(
            self.data, commands, "FLT-A001", "2025-11-01"
        )

        self.assertEqual(result["maintenance"], Decimal("175"))
        self.assertEqual(result["sinking_fund"], Decimal("50"))

    def test_metered_water_charge(self):
        self.data["flats"][0]["has_water_meter"] = "true"

        self.data["meter_readings"] = [
            {
                "flat_id": "FLT-A001",
                "reading_date": "2025-10-01",
                "reading_kl": "100",
            },
            {
                "flat_id": "FLT-A001",
                "reading_date": "2025-11-01",
                "reading_kl": "110",
            },
        ]

        result = calculate_water_charge(
            self.data, [], "FLT-A001", "2025-11"
        )

        self.assertEqual(result["method"], "METER")
        self.assertEqual(result["consumption"], Decimal("10"))
        self.assertEqual(result["water_charge"], Decimal("250"))

    def test_water_tanker_allocation(self):
        self.data["expenses"].append({
            "expense_month": "2025-11-01",
            "head": "WATER_TANKER",
            "amount": "1000",
            "tower_id": "",
        })

        first_share = calculate_water_tanker(
            self.data, [], "FLT-A001", "2025-11"
        )

        second_share = calculate_water_tanker(
            self.data, [], "FLT-A002", "2025-11"
        )

        self.assertEqual(first_share, Decimal("500.00"))
        self.assertEqual(second_share, Decimal("500.00"))

    def test_advance_applied_to_maintenance(self):
        commands = [
            "ADVANCE|ADV-001|FLT-A001|2025-11-01 10:00:00|2025-11-01|12|1200"
        ]

        result = calculate_advance_applied(
            self.data,
            commands,
            "FLT-A001",
            "2025-11",
            Decimal("350"),
            "2025-11-01",
        )

        self.assertEqual(result, Decimal("100.00"))

    def test_unauthorised_parking_complaint(self):
        self.data["rates"].append({
            "rate_code": "UNAUTH_PARKING",
            "effective_from": "2025-11-01",
            "value": "1000",
        })

        commands = [
            "PARKING_COMPLAINT|CMP-001|FLT-A001|2025-11-10"
        ]

        result = calculate_unauthorised_parking(
            self.data, commands, "FLT-A001", "2025-11"
        )

        self.assertEqual(result, Decimal("1000"))


if __name__ == "__main__":
    unittest.main()
