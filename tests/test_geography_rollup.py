import unittest
from engine.population_compiler import PopulationQueryCompiler
from engine.marital_marriage_compiler import MaritalMarriageCompiler

class GeographyRollupCompilerTests(unittest.TestCase):
    def test_population_country_recomputes_share_before_grouping(self):
        q=PopulationQueryCompiler().compile({"operation":"snapshot","metric":"aging_share","scope":{"geography_level":"country","geography":"臺灣"},"period":"11508"})
        self.assertIn("'臺灣' AS geography", q["sql"])
        self.assertIn("SUM(CASE WHEN age >= 65 THEN population ELSE 0 END)", q["sql"])
        self.assertNotIn("AVG(", q["sql"].upper())

    def test_population_county_uses_county_prefix(self):
        q=PopulationQueryCompiler().compile({"operation":"rank","metric":"total_population","scope":{"geography_level":"county"},"period":"11508"})
        self.assertIn("regexp_extract(site_id", q["sql"])
        self.assertIn("[縣市]", q["sql"])

    def test_population_existing_district_behavior_unchanged(self):
        q=PopulationQueryCompiler().compile({"operation":"rank","metric":"total_population","scope":{"geography_level":"district","parent_geography":"臺北市"},"period":"11508"})
        self.assertIn("site_id AS geography", q["sql"])
        self.assertIn("geography LIKE ?", q["sql"])
        self.assertIn("臺北市%", q["params"])

    def test_marital_country_share_recomputed(self):
        q=MaritalMarriageCompiler().compile({"operation":"snapshot","metric":"unmarried_share","scope":{"geography_level":"country"},"period":"114"})
        self.assertIn("'臺灣' AS geography", q["sql"])
        self.assertIn("NULLIF(SUM(population),0)", q["sql"])
        self.assertNotIn("AVG(", q["sql"].upper())

    def test_marriage_county_count_is_additive(self):
        q=MaritalMarriageCompiler().compile({"operation":"rank","metric":"marriage_person_count","scope":{"geography_level":"county"},"period":"114"})
        self.assertIn("SUM(marriage_count)", q["sql"])
        self.assertIn("regexp_extract(site_id", q["sql"])

if __name__ == '__main__': unittest.main()
