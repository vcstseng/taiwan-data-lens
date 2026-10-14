import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.population_compiler import PopulationQueryCompiler

class TestChangeParameterOrder(unittest.TestCase):
    def test_change_placeholder_parameter_order(self):
        p={"operation":"change","metric":"aging_share",
           "scope":{"geography_level":"district","parent_geography":"臺北市"},
           "start_period":"10708","end_period":"11508",
           "order":"descending","limit":10}
        x=PopulationQueryCompiler().compile(p)
        self.assertEqual(
            x["params"],
            ["{population_age_path}","10708","11508","10708","11508","臺北市%",10]
        )
