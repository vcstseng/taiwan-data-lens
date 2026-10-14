"""Capability-driven query resolution before canonical validation."""
from pathlib import Path
import yaml


class QueryResolver:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
        self.metrics = self._load('capabilities/metrics.yaml')['metrics']
        self.facts = self._load('capabilities/facts.yaml')['facts']

    def _load(self, relative_path):
        with (self.root / relative_path).open(encoding='utf-8') as f:
            return yaml.safe_load(f)

    def metric_contract(self, metric):
        spec = self.metrics.get(metric)
        if spec is None:
            return {'status': 'BLOCK', 'codes': ['UNKNOWN_METRIC'], 'metric': metric}
        return {
            'status': 'OK',
            'metric': metric,
            'source_fact': spec['source_fact'],
            'time_grain': self.facts[spec['source_fact']]['dimensions']['time'],
            'allowed_operations': spec.get('allowed_operations', []),
            'parameters': spec.get('parameters', {}),
        }

    def latest_period(self, metric, geography=None):
        contract = self.metric_contract(metric)
        if contract["status"] != "OK":
            return contract
        import duckdb
        fact = contract["source_fact"]
        column = "period" if contract["time_grain"] == "month" else "year"
        folders = {"marriage_activity": "fact_marriage", "migration_flow": "fact_migration"}
        folder = folders.get(fact, "fact_" + fact)
        files = sorted((self.root / "parquet" / folder).rglob("*.parquet"))
        if not files:
            return {"status": "NO_DATA", "metric": metric, "source_fact": fact}
        sql = "SELECT MAX(" + column + ") FROM read_parquet(?)"
        args = [[str(p) for p in files]]
        if geography is not None:
            if fact not in {"population_summary", "population_age", "marital_population", "marriage_activity"}:
                return {"status": "BLOCK", "codes": ["GEOGRAPHY_PERIOD_NOT_SUPPORTED"], "metric": metric}
            geo = self.resolve_geography(geography)
            if geo["status"] != "OK":
                return geo
            if geo["geography_level"] == "county":
                sql += " WHERE starts_with(site_id, ?)"
            else:
                sql += " WHERE site_id = ?"
            args.append(geo["geography"])
        con = duckdb.connect()
        try:
            value = con.execute(sql, args).fetchone()[0]
        finally:
            con.close()
        return {"status": "OK" if value is not None else "NO_DATA", "metric": metric, "source_fact": fact, "period": str(value) if value is not None else None, "time_grain": contract["time_grain"]}

    from functools import lru_cache

    @lru_cache(maxsize=1)
    def _geography_vocabulary(self):
        import duckdb
        import re
        path = str(self.root / "parquet" / "fact_population_summary" / "*.parquet")
        con = duckdb.connect()
        try:
            rows = con.execute("SELECT DISTINCT site_id FROM read_parquet(?) WHERE site_id IS NOT NULL", [path]).fetchall()
        finally:
            con.close()
        districts = frozenset(row[0] for row in rows)
        counties = frozenset(m.group(1) for x in districts if (m := re.match(r"(.+?[縣市])", x)))
        return counties, districts

    def resolve_geography(self, name):
        import duckdb
        if not isinstance(name, str) or not name.strip():
            return {"status": "BLOCK", "codes": ["INVALID_GEOGRAPHY"]}
        original = name.strip()
        candidate = original.replace("台", "臺")
        counties, districts = self._geography_vocabulary()
        if candidate in counties:
            level = "county"
        elif candidate in districts:
            level = "district"
        else:
            return {"status": "BLOCK", "codes": ["UNKNOWN_GEOGRAPHY"], "input": original}
        return {"status": "OK", "input": original, "geography": candidate, "geography_level": level, "normalized": candidate != original}
