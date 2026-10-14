import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.marital_marriage_compiler import MaritalMarriageCompiler
class T(unittest.TestCase):
 def setUp(self): self.c=MaritalMarriageCompiler()
 def test_divorce_is_stock_share(self):
  q=self.c.compile({"operation":"rank","metric":"divorced_stock_share","period":"115","scope":{"parent_geography":"臺北市"}})
  self.assertIn("離婚_不同性別",q["params"]); self.assertIn("離婚_相同性別",q["params"])
 def test_partnered_combines_two_statuses(self):
  q=self.c.compile({"operation":"snapshot","metric":"partnered_share","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertIn("有偶_不同性別",q["params"]);self.assertIn("有偶_相同性別",q["params"])
 def test_denominator_not_status_filtered(self):
  q=self.c.compile({"operation":"snapshot","metric":"marital_status_share","period":"115","scope":{"geography":"臺北市內湖區"},"filters":{"marital_status":"未婚"}})
  self.assertNotIn("marital_status = ?",q["sql"])
 def test_marriage_count_is_persons_no_div2(self):
  q=self.c.compile({"operation":"snapshot","metric":"marriage_person_count","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertNotIn("/2",q["sql"].replace(" ",""))
 def test_same_sex_share_denominator_all_marriage_persons(self):
  q=self.c.compile({"operation":"snapshot","metric":"same_sex_marriage_person_share","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertIn("相同性別",q["params"]);self.assertNotIn("marriage_type = ?",q["sql"].split("GROUP BY")[0].split("WHERE")[1])
 def test_no_rate_metric(self):
  with self.assertRaises(ValueError): self.c.compile({"operation":"snapshot","metric":"marriage_rate","period":"115","scope":{"geography":"臺北市內湖區"}})
 def test_no_divorce_rate_metric(self):
  with self.assertRaises(ValueError): self.c.compile({"operation":"snapshot","metric":"divorce_rate","period":"115","scope":{"geography":"臺北市內湖區"}})
 def test_compare_requires_two_geos(self):
  with self.assertRaises(ValueError): self.c.compile({"operation":"compare","metric":"unmarried_share","period":"115","scope":{"geographies":["臺北市內湖區"]}})
