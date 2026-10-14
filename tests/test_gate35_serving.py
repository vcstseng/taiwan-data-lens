import unittest
from pathlib import Path
class ServingArtifactTests(unittest.TestCase):
    def test_population_serving_exists(self):
        self.assertTrue(Path("parquet/serving/population_site_monthly.parquet").exists())
    def test_marital_serving_exists(self):
        self.assertTrue(Path("parquet/serving/marital_site_annual.parquet").exists())
    def test_manifest_exists(self):
        self.assertTrue(Path("parquet/serving/manifest.json").exists())
if __name__=="__main__": unittest.main()
