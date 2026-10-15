import unittest
from pathlib import Path
from validator.semantic_plan_validator import SemanticPlanValidator

class TestPeriodMonthBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = SemanticPlanValidator(Path(__file__).resolve().parents[1])

    def test_invalid_months_blocked(self):
        for period in ("11400", "11413", "11499"):
            with self.subTest(period=period):
                plan = {"operation": "snapshot", "metric": "migration_flow_count", "period": period, "scope": {"origin_geography": "臺東縣臺東市"}}
                result = self.v.validate(plan)
                self.assertEqual(result["status"], "BLOCK")
                self.assertIn("INVALID_PERIOD_FORMAT", result["codes"])

    def test_valid_months_accepted(self):
        for period in ("11401", "11402", "11412"):
            with self.subTest(period=period):
                plan = {"operation": "snapshot", "metric": "migration_flow_count", "period": period, "scope": {"origin_geography": "臺東縣臺東市"}}
                self.assertEqual(self.v.validate(plan)["status"], "ACCEPT")

if __name__ == "__main__":
    unittest.main()
