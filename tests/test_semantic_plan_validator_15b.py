import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validator.semantic_plan_validator import SemanticPlanValidator

class TestSemanticPlanValidator15B(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = SemanticPlanValidator(ROOT)

    def test_age_group_requires_age_range(self):
        p = {"operation":"snapshot","metric":"age_group_population",
             "scope":{"geography":"臺北市內湖區"},"period":"11508"}
        r = self.v.validate(p)
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("MISSING_METRIC_PARAMETER", r["codes"])

    def test_valid_age_range(self):
        p = {"operation":"snapshot","metric":"age_group_population",
             "scope":{"geography":"臺北市內湖區"},"period":"11508",
             "parameters":{"age_range":{"min":65}}}
        self.assertEqual(self.v.validate(p)["status"], "ACCEPT")

    def test_arbitrary_parameter_blocked(self):
        p = {"operation":"snapshot","metric":"total_population",
             "scope":{"geography":"臺北市"},"period":"11508",
             "parameters":{"formula":"population*2"}}
        self.assertIn("UNSUPPORTED_PARAMETER", self.v.validate(p)["codes"])

    def test_unknown_filter_dimension_blocked(self):
        p = {"operation":"snapshot","metric":"migration_flow_count",
             "scope":{"origin_geography":"臺北市內湖區"},"period":"11508",
             "filters":{"age":"20-39"}}
        self.assertIn("UNSUPPORTED_FILTER_DIMENSION", self.v.validate(p)["codes"])

    def test_filter_expression_blocked(self):
        p = {"operation":"snapshot","metric":"migration_flow_count",
             "scope":{"origin_geography":"臺北市內湖區"},"period":"11508",
             "filters":{"sex":{"not":"男"}}}
        self.assertIn("ARBITRARY_FILTER_EXPRESSION", self.v.validate(p)["codes"])

    def test_monthly_metric_rejects_annual_period(self):
        p = {"operation":"snapshot","metric":"total_population",
             "scope":{"geography":"臺北市"},"period":"115"}
        self.assertIn("INVALID_PERIOD_FORMAT", self.v.validate(p)["codes"])

    def test_annual_metric_rejects_monthly_period(self):
        p = {"operation":"snapshot","metric":"unmarried_share",
             "scope":{"geography":"臺北市"},"period":"11508"}
        self.assertIn("INVALID_PERIOD_FORMAT", self.v.validate(p)["codes"])

    def test_reverse_range_blocked(self):
        p = {"operation":"trend","metric":"aging_share",
             "scope":{"geography":"臺北市內湖區"},
             "start_period":"11508","end_period":"10708"}
        self.assertIn("INVALID_PERIOD_RANGE", self.v.validate(p)["codes"])

    def test_compare_needs_two_geographies(self):
        p = {"operation":"compare","metric":"aging_share",
             "scope":{"geographies":["臺北市內湖區"]},"period":"11508"}
        self.assertIn("COMPARE_REQUIRES_MULTIPLE_GEOGRAPHIES", self.v.validate(p)["codes"])

    def test_migration_destination_district_scope_blocked(self):
        p = {"operation":"snapshot","metric":"migration_flow_count",
             "scope":{"origin_geography":"臺北市大安區",
                      "destination_geography":"臺北市信義區",
                      "destination_geography_level":"district"},
             "period":"11508"}
        self.assertIn("UNSUPPORTED_GEOGRAPHY_RESOLUTION", self.v.validate(p)["codes"])

    def test_conflicting_period_fields_blocked(self):
        p = {"operation":"trend","metric":"aging_share",
             "scope":{"geography":"臺北市"},
             "period":"11508","start_period":"10708","end_period":"11508"}
        self.assertIn("CONFLICTING_TIME_FIELDS", self.v.validate(p)["codes"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
