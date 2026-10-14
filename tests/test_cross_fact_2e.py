import unittest
from engine.investigation_engine import CrossFactInvestigationEngine
from validator.investigation_validator import InvestigationValidator

POP={"operation":"snapshot","metric":"total_population","period":"11508","scope":{"geography":"臺北市內湖區"}}
MIG={"operation":"snapshot","metric":"migration_flow_count","period":"11508","scope":{"geography":"臺北市內湖區"}}
MARITAL={"operation":"snapshot","metric":"unmarried_share","period":"113","scope":{"geography":"臺北市內湖區"}}
MARRIAGE={"operation":"snapshot","metric":"marriage_person_count","period":"113","scope":{"geography":"臺北市內湖區"}}
class FakeEngine:
 def execute(self,p): return {"status":"OK","observation":{"metric":p["metric"],"operation":p["operation"],"unit":"x","results":[{"metric_value":1}]}}
class T(unittest.TestCase):
 def setUp(self):
  self.v=InvestigationValidator()
  self.e=CrossFactInvestigationEngine(self.v,{"population":FakeEngine(),"migration":FakeEngine(),"marital_marriage":FakeEngine()})
 def test_population_migration_contextual(self):
  r=self.e.execute({"plans":[POP,MIG],"requested_claim":"同期間人口與戶籍遷徙有什麼變化"})
  self.assertEqual(r["status"],"INVESTIGATE_WITH_LIMITS"); self.assertFalse(r["causal_authority"]); self.assertFalse(r["cross_fact_arithmetic"]); self.assertEqual(len(r["observations"]),2)
 def test_marital_marriage_same_year(self):
  r=self.e.execute({"plans":[MARITAL,MARRIAGE],"requested_claim":"同年度婚姻狀態與結婚活動如何"})
  self.assertEqual(r["status"],"INVESTIGATE_WITH_LIMITS")
 def test_causal_claim_reframed_before_execution(self):
  r=self.e.execute({"plans":[POP,MIG],"requested_claim":"人口下降是不是因為戶籍遷出造成"})
  self.assertEqual(r["status"],"REFRAME"); self.assertEqual(r["observations"],[])
 def test_time_mismatch_blocked(self):
  bad=dict(MIG); bad["period"]="11408"
  r=self.v.validate({"plans":[POP,bad]})
  self.assertEqual(r["status"],"BLOCK"); self.assertIn("RELATIONSHIP_TIME_MISMATCH",r["codes"])
 def test_geography_mismatch_blocked(self):
  bad={**MIG,"scope":{"geography":"臺北市大安區"}}
  r=self.v.validate({"plans":[POP,bad]})
  self.assertEqual(r["status"],"BLOCK"); self.assertIn("RELATIONSHIP_GEOGRAPHY_MISMATCH",r["codes"])
 def test_cross_frequency_population_marital_still_blocked(self):
  r=self.v.validate({"plans":[POP,MARITAL]})
  self.assertEqual(r["status"],"BLOCK")
