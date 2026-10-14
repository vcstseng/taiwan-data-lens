import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validator.semantic_plan_validator import SemanticPlanValidator
from validator.investigation_validator import InvestigationValidator


class TestAdversarialBattery15D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pv = SemanticPlanValidator(ROOT)
        cls.iv = InvestigationValidator(ROOT)

    def assert_block(self, plan, code=None):
        r = self.pv.validate(plan)
        self.assertEqual(r["status"], "BLOCK", r)
        if code:
            self.assertIn(code, r["codes"], r)

    def test_01_raw_sql_injection_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"total_population","period":"11508",
            "scope":{"geography":"臺北市"},
            "where":"1=1; DROP TABLE fact_population_summary"
        }, "ILLEGAL_PLAN_FIELD")

    def test_02_formula_smuggling_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"total_population","period":"11508",
            "scope":{"geography":"臺北市"},
            "formula":"SUM(population)/2"
        }, "ILLEGAL_PLAN_FIELD")

    def test_03_marriage_persons_to_couples_not_available(self):
        self.assert_block({
            "operation":"snapshot","metric":"marriage_pair_count","period":"114",
            "scope":{"geography":"臺北市"}
        }, "UNKNOWN_METRIC")

    def test_04_divorce_rate_proxy_not_available(self):
        self.assert_block({
            "operation":"rank","metric":"divorce_rate","period":"114",
            "scope":{"geography_level":"district","parent_geography":"臺北市"}
        }, "UNKNOWN_METRIC")

    def test_05_migration_age_filter_blocked(self):
        self.assert_block({
            "operation":"trend","metric":"migration_flow_count",
            "scope":{"origin_geography":"臺北市"},
            "start_period":"10708","end_period":"11508",
            "filters":{"age_band":"20-39"}
        }, "UNSUPPORTED_FILTER_DIMENSION")

    def test_06_destination_district_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"migration_flow_count","period":"11508",
            "scope":{"origin_geography":"臺北市大安區",
                     "destination_geography":"臺北市信義區",
                     "destination_geography_level":"district"}
        }, "UNSUPPORTED_GEOGRAPHY_RESOLUTION")

    def test_07_sum_tfr_operation_blocked_upstream(self):
        self.assert_block({
            "operation":"sum","metric":"total_fertility_rate","period":"114",
            "scope":{"geography_level":"county"}
        }, "UNKNOWN_OPERATION")

    def test_08_tfr_compare_now_allowed_but_never_aggregated(self):
        r=self.pv.validate({
            "operation":"compare","metric":"total_fertility_rate","period":"114",
            "scope":{"geographies":["臺北市","新北市"]}
        })
        self.assertEqual(r["status"],"ACCEPT")

    def test_09_average_share_expression_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"aging_share","period":"11508",
            "scope":{"geography":"臺北市"},
            "aggregation":"AVG"
        }, "ILLEGAL_PLAN_FIELD")

    def test_10_annual_marital_with_monthly_period_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"unmarried_share","period":"11508",
            "scope":{"geography":"臺北市"}
        }, "INVALID_PERIOD_FORMAT")

    def test_11_population_marital_cross_frequency_relationship_blocked(self):
        pop = {"operation":"trend","metric":"total_population",
               "scope":{"geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        marital = {"operation":"trend","metric":"unmarried_share",
                   "scope":{"geography":"臺北市"},
                   "start_period":"107","end_period":"115"}
        r = self.iv.validate({"plans":[pop, marital]})
        self.assertEqual(r["status"], "BLOCK", r)
        self.assertIn("RELATIONSHIP_NOT_EXECUTABLE", r["codes"], r)

    def test_12_population_migration_causation_reframed(self):
        pop = {"operation":"trend","metric":"total_population",
               "scope":{"geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        mig = {"operation":"trend","metric":"migration_flow_count",
               "scope":{"origin_geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        r = self.iv.validate({"plans":[pop,mig],
                              "requested_claim":"臺北人口下降是因為人口外移"})
        self.assertEqual(r["status"], "REFRAME", r)
        self.assertIn("CAUSAL_CLAIM_NOT_AUTHORIZED", r["codes"], r)

    def test_13_youth_outmigration_causal_story_reframed(self):
        aging = {"operation":"trend","metric":"aging_share",
                 "scope":{"geography":"臺北市"},
                 "start_period":"10708","end_period":"11508"}
        mig = {"operation":"trend","metric":"migration_flow_count",
               "scope":{"origin_geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        r = self.iv.validate({"plans":[aging,mig],
                              "requested_claim":"年輕人外移導致臺北老化"})
        self.assertEqual(r["status"], "REFRAME", r)

    def test_14_migration_marriage_arbitrary_graph_edge_blocked(self):
        mig = {"operation":"trend","metric":"migration_flow_count",
               "scope":{"origin_geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        marriage = {"operation":"trend","metric":"marriage_person_count",
                    "scope":{"geography":"臺北市"},
                    "start_period":"107","end_period":"115"}
        r = self.iv.validate({"plans":[mig, marriage]})
        self.assertEqual(r["status"], "BLOCK", r)
        self.assertIn("NO_AUTHORIZED_RELATIONSHIP", r["codes"], r)

    def test_15_decompose_does_not_sneak_through(self):
        self.assert_block({
            "operation":"decompose","metric":"total_population",
            "scope":{"geography":"臺北市內湖區"},
            "start_period":"10708","end_period":"11508",
            "profile_dimension":"age_group"
        }, "OPERATION_NOT_ALLOWED_FOR_METRIC")

    def test_16_negative_limit_blocked(self):
        self.assert_block({
            "operation":"rank","metric":"aging_share","period":"11508",
            "scope":{"geography_level":"district","parent_geography":"臺北市"},
            "limit":-1
        }, "INVALID_LIMIT")

    def test_17_boolean_limit_blocked(self):
        self.assert_block({
            "operation":"rank","metric":"aging_share","period":"11508",
            "scope":{"geography_level":"district","parent_geography":"臺北市"},
            "limit":True
        }, "INVALID_LIMIT")

    def test_18_conflicting_geography_scope_blocked(self):
        self.assert_block({
            "operation":"compare","metric":"aging_share","period":"11508",
            "scope":{"geography":"臺北市",
                     "geographies":["臺北市","新北市"]}
        }, "CONFLICTING_GEOGRAPHY_SCOPE")

    def test_19_arbitrary_scope_field_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"total_population","period":"11508",
            "scope":{"geography":"臺北市","sql_filter":"population > 0"}
        }, "UNSUPPORTED_SCOPE_FIELD")

    def test_20_unknown_top_level_field_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"total_population","period":"11508",
            "scope":{"geography":"臺北市"},
            "creative_mode":True
        }, "ILLEGAL_PLAN_FIELD")

    def test_21_empty_filter_list_blocked(self):
        self.assert_block({
            "operation":"snapshot","metric":"marriage_person_count","period":"114",
            "scope":{"geography":"臺北市"},
            "filters":{"sex":[]}
        }, "EMPTY_FILTER")

    def test_22_reversed_period_range_blocked(self):
        self.assert_block({
            "operation":"trend","metric":"aging_share",
            "scope":{"geography":"臺北市"},
            "start_period":"11508","end_period":"10708"
        }, "INVALID_PERIOD_RANGE")

    def test_23_single_valid_plan_still_accepts(self):
        r = self.iv.validate({"plans":[{
            "operation":"snapshot","metric":"total_population","period":"11508",
            "scope":{"geography":"臺北市"}
        }]})
        self.assertEqual(r["status"], "ACCEPT", r)

    def test_24_contextual_relationship_stays_limited(self):
        pop = {"operation":"trend","metric":"total_population",
               "scope":{"geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        mig = {"operation":"trend","metric":"migration_flow_count",
               "scope":{"origin_geography":"臺北市"},
               "start_period":"10708","end_period":"11508"}
        r = self.iv.validate({"plans":[pop,mig]})
        self.assertEqual(r["status"], "INVESTIGATE_WITH_LIMITS", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
