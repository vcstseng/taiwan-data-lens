import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.unified_engine import UnifiedDeterministicEngine

class V:
 def __init__(self,status="ACCEPT",codes=None): self.status=status; self.codes=codes or []
 def validate(self,p): return {"status":self.status,"codes":self.codes}
class E:
 def __init__(self,name): self.name=name; self.calls=[]
 def execute(self,p): self.calls.append(p); return {"status":"OK","observation":{"metric":p["metric"],"results":[]}}
class I:
 def execute(self,x): return {"status":"INVESTIGATE_WITH_LIMITS","observations":[]}

class T(unittest.TestCase):
 def setUp(self):
  self.es={x:E(x) for x in ["population","migration","marital_marriage","fertility"]}
  self.u=UnifiedDeterministicEngine(engines=self.es,plan_validator=V(),investigation_engine=I())
 def test_population_route(self): self.assertEqual(self.u.execute({"metric":"aging_share"})["engine"],"population")
 def test_migration_route(self): self.assertEqual(self.u.execute({"metric":"migration_flow_count"})["engine"],"migration")
 def test_marital_route(self): self.assertEqual(self.u.execute({"metric":"unmarried_share"})["engine"],"marital_marriage")
 def test_marriage_route(self): self.assertEqual(self.u.execute({"metric":"marriage_person_count"})["engine"],"marital_marriage")
 def test_validator_blocks_before_execution(self):
  u=UnifiedDeterministicEngine(engines=self.es,plan_validator=V("BLOCK",["X"]),investigation_engine=I())
  r=u.execute({"metric":"aging_share"}); self.assertEqual(r["status"],"BLOCK"); self.assertTrue(all(not e.calls for e in self.es.values()))
 def test_unknown_metric_never_executes(self):
  r=self.u.execute({"metric":"made_up_metric"}); self.assertEqual(r["status"],"BLOCK")
 def test_investigation_entrypoint(self): self.assertEqual(self.u.execute_investigation({"plans":[]})["status"],"INVESTIGATE_WITH_LIMITS")
 def test_fertility_route(self): self.assertEqual(self.u.execute({"metric":"total_fertility_rate"})["engine"],"fertility")
