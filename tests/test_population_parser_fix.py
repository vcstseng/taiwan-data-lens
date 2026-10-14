import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.population_compiler import PopulationQueryCompiler

class TestGate2BParserRegression(unittest.TestCase):
    def test_no_reserved_value_alias(self):
        plans=[
          {"operation":"snapshot","metric":"total_population","scope":{"geography":"臺北市內湖區"},"period":"11508"},
          {"operation":"change","metric":"aging_share","scope":{"geography_level":"district","parent_geography":"臺北市"},"start_period":"10708","end_period":"11508","limit":10}
        ]
        c=PopulationQueryCompiler()
        for p in plans:
            sql=c.compile(p)["sql"]
            self.assertNotRegex(sql, r"(?i)\bAS\s+value\b")
            self.assertNotRegex(sql, r"(?i)\bORDER\s+BY\s+value\b")
            self.assertIn("metric_value",sql)
