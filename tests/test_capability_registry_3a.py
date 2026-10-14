from pathlib import Path
import copy
import tempfile
import unittest
import yaml

from validator.capability_registry_validator import (
    CapabilityRegistryError,
    validate_capability_registry,
)

ROOT = Path(__file__).resolve().parents[1]


class TestCapabilityRegistry3A(unittest.TestCase):
    def test_registry_matches_gate1(self):
        result = validate_capability_registry(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["executable_metric_count"], 21)
        self.assertEqual(result["capability_count"], 8)

    def test_every_executable_metric_has_home(self):
        result = validate_capability_registry(ROOT)
        self.assertTrue(all(result["metric_homes"].values()))

    def test_registry_ids_are_dataset_agnostic(self):
        doc = yaml.safe_load((ROOT / "capabilities" / "capability_registry.yaml").read_text(encoding="utf-8"))
        for capability_id in doc["capabilities"]:
            self.assertNotIn("ODRP", capability_id.upper())

    def test_traceability_is_derived_from_gate1(self):
        result = validate_capability_registry(ROOT)
        self.assertEqual(result["capability_facts"]["migration_flow"], ["migration_flow"])
        self.assertEqual(result["capability_facts"]["fertility_age_structure"], ["fertility"])
        self.assertIn("population_age", result["capability_facts"]["age_structure"])

    def test_unknown_metric_fails_closed(self):
        self._mutate_and_expect_error(lambda d: d["capabilities"]["population_level"]["evidence"]["metrics"].append("invented_metric"))

    def test_homeless_executable_metric_fails_closed(self):
        def mutate(d):
            d["capabilities"]["population_level"]["evidence"]["metrics"].remove("households")
        self._mutate_and_expect_error(mutate)

    def test_future_capability_uses_same_schema(self):
        # Proves the registry contract can accept a future capability without core-schema changes.
        # We reuse an existing executable metric because Gate 1 intentionally remains frozen here.
        def mutate(d):
            d["capabilities"]["future_example"] = {
                "domain": "future_domain",
                "topic": "future_topic",
                "summary": "Synthetic schema-extension test only.",
                "question_patterns": ["future question"],
                "evidence": {"metrics": ["total_population"]},
                "dimensions": {"time": "inherit_from_fact", "geography": "inherit_from_fact"},
                "limitations": ["synthetic registry-schema test; not a product capability"],
            }
        result = self._mutate_and_validate(mutate)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("future_example", result["metric_homes"]["total_population"])

    def _mutate_and_validate(self, mutator):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "capabilities").mkdir()
            for name in ["metrics.yaml", "facts.yaml"]:
                (td / "capabilities" / name).write_text(
                    (ROOT / "capabilities" / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            registry = yaml.safe_load((ROOT / "capabilities" / "capability_registry.yaml").read_text(encoding="utf-8"))
            mutator(registry)
            (td / "capabilities" / "capability_registry.yaml").write_text(
                yaml.safe_dump(registry, allow_unicode=True, sort_keys=False), encoding="utf-8"
            )
            return validate_capability_registry(td)

    def _mutate_and_expect_error(self, mutator):
        with self.assertRaises(CapabilityRegistryError):
            self._mutate_and_validate(mutator)


if __name__ == "__main__":
    unittest.main()
