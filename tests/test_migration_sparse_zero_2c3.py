import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.migration_compiler import MigrationQueryCompiler

class TestSparseZero2C3(unittest.TestCase):
 def setUp(self): self.c=MigrationQueryCompiler()
 def test_destination_trend_reconstructs_zero(self):
  p={"operation":"trend","metric":"migration_flow_count","start_period":"11401","end_period":"11508",
     "scope":{"geography":"臺北市內湖區"},"filters":{"destination_county":"連江縣"}}
  q=self.c.compile(p)
  self.assertIn("LEFT JOIN x USING(period)",q["sql"])
  self.assertIn("COALESCE(x.destination_count,0)",q["sql"])
 def test_trend_parameter_order(self):
  p={"operation":"trend","metric":"migration_flow_count","start_period":"11401","end_period":"11508",
     "scope":{"geography":"臺北市內湖區"},"filters":{"destination_county":"連江縣"}}
  q=self.c.compile(p)
  self.assertEqual(q["params"],["{migration_path}","11401","11508","{migration_path}","11401","11508",
                                "臺北市內湖區","連江縣","臺北市內湖區","連江縣"])
 def test_change_reconstructs_zero_endpoints(self):
  p={"operation":"change","metric":"migration_flow_count","start_period":"11408","end_period":"11508",
     "scope":{"parent_geography":"臺北市"},"filters":{"destination_county":"連江縣"}}
  q=self.c.compile(p)
  self.assertIn("CROSS JOIN endpoints",q["sql"])
  self.assertIn("COALESCE(s.metric_value,0)",q["sql"])
  self.assertNotIn("start_value IS NOT NULL",q["sql"])
 def test_share_change_still_blocked(self):
  p={"operation":"change","metric":"migration_destination_share","start_period":"11408","end_period":"11508",
     "scope":{"parent_geography":"臺北市"},"filters":{"destination_county":"連江縣"}}
  with self.assertRaises(ValueError): self.c.compile(p)
