
import unittest
from decimal import Decimal

from src.billing import (
    round_rupee,
    get_rate,
    get_flat,
    validate_payment_commands,
    calculate_interest,
)


class TestBilling(unittest.TestCase):

    def test_round_rupee_up(self):
        result = round_rupee(Decimal("100.50"))
        self.assertEqual(result, Decimal("101"))

    def test_round_rupee_down(self):
        result = round_rupee(Decimal("100.49"))
        self.assertEqual(result, Decimal("100"))

    def test_get_latest_applicable_rate(self):
        data = {
            "rates": [
                {
                    "rate_code": "MAINT_PER_SQFT",
                    "effective_from": "2025-11-01",
                    "value": "3.50",
                },
                {
                    "rate_code": "MAINT_PER_SQFT",
                    "effective_from": "2026-02-01",
                    "value": "3.75",
                },
            ]
        }

        result = get_rate(data, "MAINT_PER_SQFT", "2026-03-01")
        self.assertEqual(result, Decimal("3.75"))

    def test_get_flat_success(self):
        data = {
            "flats": [
                {"flat_id": "FLT-A001"},
                {"flat_id": "FLT-A002"},
            ]
        }

        result = get_flat(data, "FLT-A001")
        self.assertEqual(result["flat_id"], "FLT-A001")

    def test_get_flat_invalid_id(self):
        data = {"flats": [{"flat_id": "FLT-A001"}]}

        with self.assertRaises(ValueError):
            get_flat(data, "FLT-Z999")

    def test_payment_validation(self):
        data = {
            "flats": [
                {"flat_id": "FLT-A001"},
            ]
        }

        commands = [
            "PAYMENT|PAY-001|FLT-A001|2026-01-10 10:00:00|1000.00|UPI",
            "PAYMENT|PAY-001|FLT-A001|2026-01-11 10:00:00|500.00|UPI",
            "PAYMENT|PAY-002|FLT-Z999|2026-01-12 10:00:00|500.00|UPI",
        ]

        accepted, rejected = validate_payment_commands(data, commands)

        self.assertEqual(accepted, 1)
        self.assertEqual(len(rejected), 2)

    def test_interest_on_due_date_is_zero(self):
        data = {
            "rates": [
                {
                    "rate_code": "INTEREST_PA_PCT",
                    "effective_from": "2025-11-01",
                    "value": "18",
                }
            ]
        }

        result = calculate_interest(
            data,
            Decimal("1000"),
            "2026-01-15",
            "2026-01-15",
        )

        self.assertEqual(result, Decimal("0.00"))

    def test_interest_after_due_date(self):
        data = {
            "rates": [
                {
                    "rate_code": "INTEREST_PA_PCT",
                    "effective_from": "2025-11-01",
                    "value": "18",
                }
            ]
        }

        result = calculate_interest(
            data,
            Decimal("1000"),
            "2026-01-15",
            "2026-01-16",
        )

        self.assertEqual(result, Decimal("0.49"))


if __name__ == "__main__":
    unittest.main()
