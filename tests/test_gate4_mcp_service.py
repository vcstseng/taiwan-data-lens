import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import yaml
from mcp_server.service import LensService


class Gate4McpServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'capabilities').mkdir()
        (self.root / 'story').mkdir()
        (self.root / 'capabilities' / 'capability_registry.yaml').write_text(yaml.safe_dump({
            'capabilities': {'population_level': {'summary': 'Population',
                'evidence': {'metrics': ['total_population', 'unavailable']},
                'limitations': ['Registered residents only']}}}), encoding='utf-8')
        (self.root / 'capabilities' / 'metrics.yaml').write_text(yaml.safe_dump({
            'metrics': {'total_population': {'status': 'normal'}}}), encoding='utf-8')
        (self.root / 'story' / 'grand_tour_v1.json').write_text(json.dumps({
            'id': 'tour', 'title': 'Tour', 'rule': 'No causal links',
            'stops': [{'id': 'population_redistribution', 'title': 'Population', 'capabilities': ['population_level']}]}
        ), encoding='utf-8')
        self.engine = Mock()
        self.service = LensService(root=self.root, engine=self.engine)

    def tearDown(self):
        self.tmp.cleanup()

    def test_discover_uses_registry_not_hardcoded_metrics(self):
        result = self.service.discover_data()
        self.assertEqual(result['capabilities'][0]['metrics'], ['total_population'])
        self.engine.execute.assert_not_called()

    def test_story_is_entrypoint_not_observation(self):
        result = self.service.get_story('population_redistribution')
        self.assertEqual(result['evidence_status'], 'ENTRYPOINTS_ONLY')
        self.assertEqual(len(result['stops']), 1)

    def test_unknown_story_returns_not_found(self):
        self.assertEqual(self.service.get_story('missing')['status'], 'NOT_FOUND')

    def test_explore_passes_exact_plan_to_canonical_engine(self):
        plan = {'operation': 'snapshot', 'metric': 'total_population', 'period': '11401',
                'scope': {'geography_level': 'country'}}
        self.engine.execute.return_value = {'status': 'OK', 'observation': {'value': 1}}
        self.assertEqual(self.service.explore_data(plan)['status'], 'OK')
        self.engine.execute.assert_called_once_with(plan)

    def test_forbidden_sql_is_not_silently_removed(self):
        plan = {'operation': 'snapshot', 'metric': 'total_population', 'sql': 'DROP TABLE x'}
        self.service.explore_data(plan)
        self.engine.execute.assert_called_once_with(plan)

    def test_invalid_plan_never_reaches_engine(self):
        self.assertEqual(self.service.explore_data('not a plan')['status'], 'BLOCK')
        self.engine.execute.assert_not_called()

    def test_block_is_returned_unchanged(self):
        blocked = {'status': 'BLOCK', 'validation': {'codes': ['INVALID_PERIOD_FORMAT']}, 'observation': None}
        self.engine.execute.return_value = blocked
        self.assertEqual(self.service.explore_data({'operation': 'snapshot'}), blocked)


if __name__ == '__main__':
    unittest.main()
