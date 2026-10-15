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
            'navigation': {'type': 'main_menu', 'items': [{'id': 'A', 'label': '探索一座城市'}, {'id': 'B', 'label': '探索一個主題'}, {'id': 'C', 'label': '精選數據故事'}, {'id': 'D', 'label': '隨機發現'}, {'id': 'E', 'label': '資料範圍與限制'}]},
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

    def get_snapshot(self, metric, geography, period="latest", parameters=None):
        from mcp_server.query_resolver import QueryResolver
        resolver = QueryResolver(root=self.root)
        contract = resolver.metric_contract(metric)
        if contract["status"] != "OK":
            return contract
        if "snapshot" not in contract["allowed_operations"]:
            return {"status": "BLOCK", "codes": ["SNAPSHOT_NOT_SUPPORTED"], "metric": metric}
        if contract["source_fact"] not in {"population_summary", "population_age", "marital_population", "marriage_activity"}:
            return {"status": "BLOCK", "codes": ["SNAPSHOT_GEOGRAPHY_NOT_IMPLEMENTED"], "metric": metric}
        geo = resolver.resolve_geography(geography)
        if geo["status"] != "OK":
            return geo
        if period == "latest":
            latest = resolver.latest_period(metric, geo["geography"])
            if latest["status"] != "OK":
                return latest
            period = latest["period"]
        if parameters is not None and not isinstance(parameters, dict):
            return {"status": "BLOCK", "codes": ["INVALID_PARAMETERS"]}
        plan = {"operation": "snapshot", "metric": metric, "period": period, "scope": {"geography": geo["geography"], "geography_level": geo["geography_level"]}}
        if parameters is not None:
            plan["parameters"] = parameters

        result = self.explore_data(plan)
        if result.get("status") == "OK" and not (result.get("observation") or {}).get("results"):
            return {"status": "NO_DATA", "metric": metric, "geography": geo["geography"], "period": period, "observation": result.get("observation")}
        return result

    def close(self):
        if self._engine is not None:
            self._engine.close()
            self._engine = None
