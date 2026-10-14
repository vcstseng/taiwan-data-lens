import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.population_compiler import PopulationQueryCompiler
class TestPopulationCompiler2B(unittest.TestCase):
 def setUp(self): self.c=PopulationQueryCompiler()
 def p(self,op,metric,**kw):
  x={"operation":op,"metric":metric,"scope":{"geography":"臺北市內湖區"}}
  x.update(kw); return x
 def test_snapshot_total(self):
  x=self.c.compile(self.p("snapshot","total_population",period="11508"))
  self.assertIn("SUM(population_total)",x["sql"])
 def test_snapshot_households(self):
  self.assertIn("SUM(households)",self.c.compile(self.p("snapshot","households",period="11508"))["sql"])
 def test_age_group_population(self):
  p=self.p("snapshot","age_group_population",period="11508",parameters={"age_range":{"min":65}})
  self.assertIn("age >= 65",self.c.compile(p)["sql"])
 def test_child_fixed(self):
  x=self.c.compile(self.p("snapshot","child_share",period="11508"))["sql"]
  self.assertIn("age >= 0",x); self.assertIn("age <= 14",x)
 def test_working_fixed(self):
  x=self.c.compile(self.p("snapshot","working_age_share",period="11508"))["sql"]
  self.assertIn("age >= 15",x); self.assertIn("age <= 64",x)
 def test_aging_fixed(self):
  self.assertIn("age >= 65",self.c.compile(self.p("snapshot","aging_share",period="11508"))["sql"])
 def test_compare_parameterized(self):
  p={"operation":"compare","metric":"aging_share","period":"11508","scope":{"geographies":["臺北市內湖區","臺北市士林區"]}}
  x=self.c.compile(p); self.assertNotIn("內湖",x["sql"]); self.assertIn("臺北市內湖區",x["params"])
 def test_rank(self):
  p={"operation":"rank","metric":"aging_share","period":"11508","scope":{"geography_level":"district","parent_geography":"臺北市"},"limit":3}
  x=self.c.compile(p); self.assertIn("ORDER BY metric_value DESC",x["sql"]); self.assertEqual(x["params"][-1],3)
 def test_change(self):
  p={"operation":"change","metric":"aging_share","start_period":"10708","end_period":"11508","scope":{"geography_level":"district","parent_geography":"臺北市"}}
  self.assertIn("end_value-start_value",self.c.compile(p)["sql"])
 def test_no_avg(self):
  p={"operation":"rank","metric":"aging_share","period":"11508","scope":{"geography_level":"district","parent_geography":"臺北市"}}
  self.assertNotIn("AVG(",self.c.compile(p)["sql"].upper())
if __name__=="__main__": unittest.main(verbosity=2)
