import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.population_compiler import PopulationQueryCompiler

class TestPopulationGoldenContractRegression(unittest.TestCase):
 def setUp(self):
  self.c=PopulationQueryCompiler()
  self.p={"operation":"change","metric":"aging_share",
          "scope":{"geography_level":"district","parent_geography":"臺北市"},
          "start_period":"10708","end_period":"11508","order":"descending","limit":10}
 def test_deterministic(self): self.assertEqual(self.c.compile(self.p),self.c.compile(self.p))
 def test_uses_age_fact_and_65_plus(self):
  x=self.c.compile(self.p)
  self.assertEqual(x["source"],"{population_age_path}")
  self.assertIn("age >= 65",x["sql"])
  self.assertIn("SUM(population)",x["sql"])
 def test_share_recomputed_not_averaged(self):
  x=self.c.compile(self.p)["sql"].upper()
  self.assertIn("SUM(CASE WHEN AGE >= 65",x)
  self.assertIn("NULLIF(SUM(POPULATION),0)",x)
  self.assertNotIn("AVG(",x)
 def test_values_parameterized(self):
  x=self.c.compile(self.p)
  self.assertNotIn("10708",x["sql"]); self.assertNotIn("11508",x["sql"])
  self.assertIn("10708",x["params"]); self.assertIn("11508",x["params"])
 def test_limit_parameterized(self):
  x=self.c.compile(self.p); self.assertTrue(x["sql"].rstrip().endswith("LIMIT ?")); self.assertEqual(x["params"][-1],10)
if __name__=="__main__": unittest.main(verbosity=2)
