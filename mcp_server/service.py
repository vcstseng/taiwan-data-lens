"""Thin, read-only MCP application service. No SQL or new query semantics."""
from pathlib import Path
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]


class LensService:
    def __init__(self, root=None, engine=None):
        self.root = Path(root) if root is not None else ROOT
        self._engine = engine

    def discover_data(self):
        with (self.root / 'capabilities' / 'capability_registry.yaml').open(encoding='utf-8') as f:
            registry = yaml.safe_load(f)
        with (self.root / 'capabilities' / 'metrics.yaml').open(encoding='utf-8') as f:
            metrics = yaml.safe_load(f)['metrics']
        return {
            'status': 'OK',
            'capabilities': [
                {'id': name, 'summary': spec.get('summary'),
                 'metrics': [m for m in spec.get('evidence', {}).get('metrics', [])
                             if m in metrics and metrics[m].get('status') == 'normal'
                             and metrics[m].get('display_enabled', True)],
                 'limitations': spec.get('limitations', [])}
                for name, spec in registry['capabilities'].items()
            ],
            'notice': 'Discoverability is not permission to execute or infer causality. Query validation is mandatory.'
        }

    def get_story(self, stop_id=None):
        with (self.root / 'story' / 'grand_tour_v1.json').open(encoding='utf-8') as f:
            story = json.load(f)
        stops = story['stops']
        if stop_id is not None:
            stops = [s for s in stops if s['id'] == stop_id]
            if not stops:
                return {'status': 'NOT_FOUND', 'stop_id': stop_id, 'stops': []}
        return {'status': 'OK', 'tour_id': story['id'], 'title': story['title'],
                'narrative_rule': story['rule'], 'stops': stops,
                'evidence_status': 'ENTRYPOINTS_ONLY',
                'notice': 'Story titles are curated hypotheses, not numerical observations. Query the engine for evidence.'}

    def explore_data(self, plan):
        if not isinstance(plan, dict):
            return {'status': 'BLOCK', 'validation': {'status': 'BLOCK', 'codes': ['INVALID_PLAN_TYPE']}, 'observation': None}
        # Do not filter fields here: the canonical validator must reject forbidden/unknown fields.
        if self._engine is None:
            from engine.unified_engine import UnifiedDeterministicEngine
            self._engine = UnifiedDeterministicEngine(root=self.root)
        return self._engine.execute(plan)

    def close(self):
        if self._engine is not None:
            self._engine.close()
            self._engine = None
