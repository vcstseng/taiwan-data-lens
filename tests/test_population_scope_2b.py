import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from engine.population_compiler import PopulationQueryCompiler

class TestPopulationScopePropagation(unittest.TestCase):
    def setUp(self):
        self.c=PopulationQueryCompiler()

    def test_rank_parent_geography_survives_compilation(self):
        p={"operation":"rank","metric":"aging_share","period":"11508",
           "scope":{"geography_level":"district","parent_geography":"臺北市"},
           "order":"descending","limit":3}
        x=self.c.compile(p)
        self.assertIn("geography LIKE ?",x["sql"])
        self.assertIn("臺北市%",x["params"])

    def test_change_parent_geography_survives_compilation(self):
        p={"operation":"change","metric":"aging_share",
           "start_period":"10708","end_period":"11508",
           "scope":{"geography_level":"district","parent_geography":"臺北市"},
           "order":"descending","limit":10}
        x=self.c.compile(p)
        self.assertIn("geography LIKE ?",x["sql"])
        self.assertIn("臺北市%",x["params"])

    def test_compare_parent_geography_survives_when_present(self):
        p={"operation":"compare","metric":"aging_share","period":"11508",
           "scope":{"parent_geography":"臺北市",
                    "geographies":["臺北市內湖區","臺北市士林區"]}}
        x=self.c.compile(p)
        self.assertIn("geography LIKE ?",x["sql"])
        self.assertIn("臺北市%",x["params"])

    def test_scope_value_is_parameterized(self):
        p={"operation":"rank","metric":"aging_share","period":"11508",
           "scope":{"geography_level":"district","parent_geography":"臺北市"}}
        x=self.c.compile(p)
        self.assertNotIn("臺北市",x["sql"])
        self.assertIn("臺北市%",x["params"])
