import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validator.investigation_validator import InvestigationValidator

class TestInvestigationValidator15C(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = InvestigationValidator(ROOT)

    def pop(self):
        return {"operation":"change","metric":"total_population",
                "scope":{"geography":"臺北市內湖區"},
                "start_period":"10708","end_period":"11508"}

    def migration(self):
        return {"operation":"trend","metric":"migration_flow_count",
                "scope":{"origin_geography":"臺北市內湖區"},
                "start_period":"10708","end_period":"11508"}

    def test_population_migration_contextual_allowed(self):
        r = self.v.validate({"plans":[self.pop(), self.migration()]})
        self.assertEqual(r["status"], "INVESTIGATE_WITH_LIMITS")
        self.assertEqual(r["relationships"][0]["id"], "population_migration")

    def test_population_migration_causal_claim_reframed(self):
        r = self.v.validate({"plans":[self.pop(), self.migration()],
                             "requested_claim":"內湖人口下降是因為人口外移造成的"})
        self.assertEqual(r["status"], "REFRAME")
        self.assertIn("CAUSAL_CLAIM_NOT_AUTHORIZED", r["codes"])

    def test_youth_outmigration_claim_reframed(self):
        aging = {"operation":"change","metric":"aging_share",
                 "scope":{"geography":"臺北市內湖區"},
                 "start_period":"10708","end_period":"11508"}
        r = self.v.validate({"plans":[aging, self.migration()],
                             "requested_claim":"內湖老化是不是年輕人外移造成的"})
        self.assertEqual(r["status"], "REFRAME")

    def test_disabled_population_marital_relationship_blocks(self):
        marital = {"operation":"trend","metric":"unmarried_share",
                   "scope":{"geography":"臺北市內湖區"},
                   "start_period":"107","end_period":"115"}
        r = self.v.validate({"plans":[self.pop(), marital]})
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("RELATIONSHIP_NOT_EXECUTABLE", r["codes"])

    def test_unrelated_migration_marriage_blocks(self):
        marriage = {"operation":"trend","metric":"marriage_person_count",
                    "scope":{"geography":"臺北市"},
                    "start_period":"107","end_period":"115"}
        r = self.v.validate({"plans":[self.migration(), marriage]})
        self.assertEqual(r["status"], "BLOCK")
        self.assertIn("NO_AUTHORIZED_RELATIONSHIP", r["codes"])

    def test_marital_marriage_activity_allowed_with_limits(self):
        marital = {"operation":"trend","metric":"partnered_share",
                   "scope":{"geography":"臺北市"},
                   "start_period":"107","end_period":"115"}
        marriage = {"operation":"trend","metric":"marriage_person_count",
                    "scope":{"geography":"臺北市"},
                    "start_period":"107","end_period":"115"}
        r = self.v.validate({"plans":[marital, marriage]})
        self.assertEqual(r["status"], "INVESTIGATE_WITH_LIMITS")
        self.assertEqual(r["relationships"][0]["id"], "marital_marriage_activity")

    def test_fertility_relationship_now_allowed_with_limits(self):
        marriage = {"operation":"trend","metric":"marriage_person_count",
                    "scope":{"geography":"臺北市"},
                    "start_period":"107","end_period":"114"}
        fertility = {"operation":"trend","metric":"total_fertility_rate",
                     "scope":{"geography":"臺北市"},
                     "start_period":"107","end_period":"114"}
        r = self.v.validate({"plans":[marriage, fertility]})
        self.assertEqual(r["status"], "INVESTIGATE_WITH_LIMITS")
        self.assertEqual(r["relationships"][0]["id"], "marriage_fertility")

    def test_invalid_subplan_propagates_block(self):
        bad = {"operation":"rank","metric":"divorce_rate","period":"114"}
        r = self.v.validate({"plans":[self.pop(), bad]})
        self.assertEqual(r["status"], "BLOCK")
        self.assertEqual(r["plan_index"], 1)

    def test_single_plan_accepts(self):
        r = self.v.validate({"plans":[self.pop()]})
        self.assertEqual(r["status"], "ACCEPT")

if __name__ == "__main__":
    unittest.main(verbosity=2)
