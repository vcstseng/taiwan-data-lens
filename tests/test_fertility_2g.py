import sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.fertility_compiler import FertilityCompiler
from engine.fertility_engine import FertilityEngine
from validator.semantic_plan_validator import SemanticPlanValidator

class T(unittest.TestCase):
 def setUp(self): self.c=FertilityCompiler(); self.v=SemanticPlanValidator(ROOT)
 def test_validator_accepts_tfr(self):
  r=self.v.validate({'operation':'snapshot','metric':'total_fertility_rate','period':'114','scope':{'geography':'新北市板橋區'}}); self.assertEqual(r['status'],'ACCEPT')
 def test_asfr_requires_band(self):
  r=self.v.validate({'operation':'snapshot','metric':'age_specific_fertility_rate','period':'114','scope':{'geography':'新北市板橋區'}}); self.assertEqual(r['status'],'BLOCK')
 def test_tfr_compile_converts_scale(self):
  q=self.c.compile({'operation':'snapshot','metric':'total_fertility_rate','period':'114','scope':{'geography':'新北市板橋區'}}); self.assertIn('/ 1000.0',q['sql']); self.assertEqual(q['unit'],'births_per_woman')
 def test_no_fertility_filters(self):
  with self.assertRaises(ValueError): self.c.compile({'operation':'snapshot','metric':'total_fertility_rate','period':'114','scope':{'geography':'X'},'filters':{'sex':'F'}})
 def test_profile_all_seven_bands(self):
  q=self.c.compile({'operation':'profile','metric':'age_specific_fertility_rate','period':'114','scope':{'geography':'X'},'profile_dimension':'age_band'}); self.assertEqual(q['sql'].count(' AS age_band'),7)
 def test_live_synthetic_reconciliation_and_units(self):
  try:
   import duckdb
  except ImportError:
   self.skipTest("duckdb not installed in this environment")
  with tempfile.TemporaryDirectory() as td:
   path=Path(td)/'f.parquet'; con=duckdb.connect()
   con.execute("""CREATE TABLE f(year VARCHAR,site_id VARCHAR,total_fertility_rate DOUBLE,general_fertility_rate DOUBLE,asfr_15_19 DOUBLE,asfr_20_24 DOUBLE,asfr_25_29 DOUBLE,asfr_30_34 DOUBLE,asfr_35_39 DOUBLE,asfr_40_44 DOUBLE,asfr_45_49 DOUBLE)""")
   con.execute("INSERT INTO f VALUES ('114','新北市板橋區',560,16,1,6,22,41,33,8,1)")
   con.execute(f"COPY f TO '{path.as_posix()}' (FORMAT PARQUET)")
   e=FertilityEngine(con,path)
   r=e.execute({'operation':'snapshot','metric':'total_fertility_rate','period':'114','scope':{'geography':'新北市板橋區'}})
   self.assertEqual(r['observation']['results'][0]['metric_value'],0.56)
   pr=e.execute({'operation':'profile','metric':'age_specific_fertility_rate','period':'114','scope':{'geography':'新北市板橋區'},'profile_dimension':'age_band'})
   vals=[x['metric_value'] for x in pr['observation']['results']]; self.assertEqual(5*sum(vals),560)
   con.close()
if __name__=='__main__': unittest.main(verbosity=2)
