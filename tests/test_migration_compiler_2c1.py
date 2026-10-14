import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from engine.migration_compiler import MigrationQueryCompiler

class TestMigrationCompiler2C1(unittest.TestCase):
    def setUp(self): self.c=MigrationQueryCompiler()

    def base(self, metric="migration_flow_count", op="profile"):
        return {"operation":op,"metric":metric,"period":"11508",
                "scope":{"geography":"臺北市內湖區"}}

    def test_direction_is_origin_to_destination(self):
        x=self.c.compile(self.base())
        self.assertIn("origin_district = ?",x["sql"])
        self.assertIn("destination_county",x["sql"])

    def test_values_are_parameterized(self):
        x=self.c.compile(self.base())
        self.assertNotIn("臺北市內湖區",x["sql"])
        self.assertEqual(x["params"][:3],["{migration_path}","11508","臺北市內湖區"])

    def test_destination_share_uses_context_denominator(self):
        x=self.c.compile(self.base("migration_destination_share","profile"))
        self.assertIn("SUM(destination_count)",x["sql"])
        self.assertIn("NULLIF(t.total_count,0)",x["sql"])

    def test_destination_filter_for_share_is_applied_after_denominator(self):
        p=self.base("migration_destination_share","profile")
        p["filters"]={"destination_county":"新北市"}
        x=self.c.compile(p)
        before=x["sql"].split("), t AS")[0]
        self.assertNotIn("destination_county = ?",before)
        self.assertIn("WHERE destination_county = ?",x["sql"])
        self.assertEqual(x["params"][-1],"新北市")

    def test_sex_filter_is_parameterized(self):
        p=self.base(); p["filters"]={"sex":"女"}
        x=self.c.compile(p)
        self.assertIn("sex = ?",x["sql"]); self.assertIn("女",x["params"])

    def test_limit_is_parameterized(self):
        p=self.base(); p["limit"]=5
        x=self.c.compile(p)
        self.assertTrue(x["sql"].endswith("LIMIT ?"))
        self.assertEqual(x["params"][-1],5)

    def test_origin_required(self):
        p=self.base(); p["scope"]={}
        with self.assertRaises(ValueError): self.c.compile(p)

    def test_net_migration_not_available(self):
        p=self.base("net_migration")
        with self.assertRaises(ValueError): self.c.compile(p)
