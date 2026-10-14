import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.migration_compiler import MigrationQueryCompiler

class TestMigrationTemporal2C2(unittest.TestCase):
 def setUp(self): self.c=MigrationQueryCompiler()
 def test_trend_flow_destination(self):
  p={"operation":"trend","metric":"migration_flow_count","start_period":"11401","end_period":"11508",
     "scope":{"geography":"臺北市內湖區"},"filters":{"destination_county":"新北市"}}
  q=self.c.compile(p); self.assertIn("ORDER BY p.period",q["sql"]); self.assertEqual(q["params"][-1],"新北市")
 def test_share_trend_denominator_not_destination_filtered(self):
  p={"operation":"trend","metric":"migration_destination_share","start_period":"11401","end_period":"11508",
     "scope":{"geography":"臺北市內湖區"},"filters":{"destination_county":"新北市"}}
  q=self.c.compile(p); before=q["sql"].split("), t AS")[0]
  self.assertNotIn("destination_county = ?",before)
  self.assertEqual(q["params"][-1],"新北市")
 def test_change_parent_scope(self):
  p={"operation":"change","metric":"migration_flow_count","start_period":"11408","end_period":"11508",
     "scope":{"parent_geography":"臺北市"},"filters":{"destination_county":"新北市"},"limit":5}
  q=self.c.compile(p); self.assertIn("origin_district LIKE ?",q["sql"]); self.assertIn("臺北市%",q["params"])
 def test_change_param_order(self):
  p={"operation":"change","metric":"migration_flow_count","start_period":"11408","end_period":"11508",
     "scope":{"parent_geography":"臺北市"},"filters":{"destination_county":"新北市"}}
  q=self.c.compile(p)
  self.assertEqual(q["params"],["{migration_path}","臺北市%","11408","11508",
                                "{migration_path}","11408","11508","臺北市%",
                                "新北市","11408","11508"])
  self.assertEqual(q["sql"].count("?"),len(q["params"]))
 def test_share_change_blocked(self):
  p={"operation":"change","metric":"migration_destination_share","start_period":"11408","end_period":"11508",
     "scope":{"parent_geography":"臺北市"},"filters":{"destination_county":"新北市"}}
  with self.assertRaises(ValueError): self.c.compile(p)
 def test_compare_flow(self):
  p={"operation":"compare","metric":"migration_flow_count","period":"11508",
     "scope":{"geographies":["臺北市內湖區","臺北市大安區"]},"filters":{"destination_county":"新北市"}}
  q=self.c.compile(p); self.assertIn("origin_district IN (?,?)",q["sql"])
 def test_compare_share_requires_destination(self):
  p={"operation":"compare","metric":"migration_destination_share","period":"11508",
     "scope":{"geographies":["臺北市內湖區","臺北市大安區"]}}
  with self.assertRaises(ValueError): self.c.compile(p)
 def test_point_share_destination_now_safe(self):
  p={"operation":"snapshot","metric":"migration_destination_share","period":"11508",
     "scope":{"geography":"臺北市內湖區"},"filters":{"destination_county":"新北市"}}
  q=self.c.compile(p); before=q["sql"].split("), t AS")[0]
  self.assertNotIn("destination_county = ?",before)
