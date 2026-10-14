import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validator.semantic_plan_validator import SemanticPlanValidator

class TestSemanticPlanValidator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = SemanticPlanValidator(ROOT)

    def test_01_golden_aging_change_accept(self):
        p = {
            "operation": "change",
            "metric": "aging_share",
            "scope": {"geography_level": "district", "parent_geography": "臺北市"},
            "start_period": "10708",
            "end_period": "11508",
            "order": "descending",
            "limit": 10
        }
        self.assertEqual(self.v.validate(p)["status"], "ACCEPT")

    def test_02_unknown_divorce_rate_block(self):
        p = {"operation":"rank","metric":"divorce_rate","period":"114"}
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("UNKNOWN_METRIC", r["codes"])

    def test_03_divorced_stock_claim_reframe(self):
        p = {
            "operation":"rank",
            "metric":"divorced_stock_share",
            "scope":{"geography_level":"district","parent_geography":"臺北市"},
            "period":"114",
            "requested_claim":"哪個行政區最容易離婚"
        }
        r = self.v.validate(p)
        self.assertEqual(r["status"], "REFRAME")
        self.assertIn("UNSUPPORTED_CLAIM", r["codes"])

    def test_04_migration_destination_district_block(self):
        p = {
            "operation":"profile",
            "metric":"migration_flow_count",
            "scope":{"geography":"臺北市大安區"},
            "period":"11508",
            "profile_dimension":"destination_district"
        }
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("UNSUPPORTED_DIMENSION", r["codes"])

    def test_05_fertility_verified_accept(self):
        p = {
            "operation":"rank",
            "metric":"total_fertility_rate",
            "scope":{"geography_level":"county"},
            "period":"114"
        }
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("GEOGRAPHY_ROLLUP_NOT_AUTHORIZED", r["codes"])

    def test_06_sql_field_block(self):
        p = {
            "operation":"snapshot",
            "metric":"total_population",
            "period":"11508",
            "sql":"SELECT * FROM x"
        }
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("ILLEGAL_PLAN_FIELD", r["codes"])

    def test_07_unknown_operation_block(self):
        p = {"operation":"sum","metric":"total_population","period":"11508"}
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("UNKNOWN_OPERATION", r["codes"])

    def test_08_invalid_limit_block(self):
        p = {"operation":"rank","metric":"aging_share","period":"11508","limit":0}
        self.assertEqual(self.v.validate(p)["status"], "BLOCK")

    def test_09_decompose_explicitly_blocked_until_contract(self):
        p = {
            "operation":"decompose",
            "metric":"aging_share",
            "start_period":"10708",
            "end_period":"11508",
            "profile_dimension":"age"
        }
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("DECOMPOSITION_CONTRACT_MISSING", r["codes"])

    def test_10_valid_migration_profile_accept(self):
        p = {
            "operation":"profile",
            "metric":"migration_flow_count",
            "scope":{"geography":"臺北市內湖區"},
            "period":"11508",
            "profile_dimension":"destination_county",
            "order":"descending"
        }
        self.assertEqual(self.v.validate(p)["status"], "ACCEPT")

if __name__ == "__main__":
    unittest.main(verbosity=2)
