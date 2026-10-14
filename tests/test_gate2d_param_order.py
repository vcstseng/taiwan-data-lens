import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine.marital_marriage_compiler import MaritalMarriageCompiler

class TestGate2DParamOrder(unittest.TestCase):
 def setUp(self): self.c=MaritalMarriageCompiler()
 def test_unmarried_share_param_order(self):
  q=self.c.compile({"operation":"snapshot","metric":"unmarried_share","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertEqual(q["params"],["未婚","{marital_path}","115","臺北市內湖區"])
 def test_divorced_share_param_order(self):
  q=self.c.compile({"operation":"snapshot","metric":"divorced_stock_share","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertEqual(q["params"][:2],["離婚_不同性別","離婚_相同性別"])
  self.assertEqual(q["params"][2:],["{marital_path}","115","臺北市內湖區"])
 def test_same_sex_marriage_share_param_order(self):
  q=self.c.compile({"operation":"snapshot","metric":"same_sex_marriage_person_share","period":"115","scope":{"geography":"臺北市內湖區"}})
  self.assertEqual(q["params"],["相同性別","{marriage_path}","115","臺北市內湖區"])
