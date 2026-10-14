from pathlib import Path
from validator.semantic_plan_validator import SemanticPlanValidator
from .population_compiler import PopulationQueryCompiler


class PopulationEngine:
    def __init__(self, root, data_root):
        self.root, self.data_root = Path(root), Path(data_root)
        self.validator = SemanticPlanValidator(self.root)
        self.compiler = PopulationQueryCompiler()

    def execute(self, plan):
        v = self.validator.validate(plan)
        if v["status"] != "ACCEPT":
            return {"status": "BLOCK", "validation": v}

        c = self.compiler.compile(plan)
        paths = {
            "{population_age_path}": str(
                self.data_root / "parquet" / "fact_population_age" / "**" / "*.parquet"
            ),
            "{population_summary_path}": str(
                self.data_root / "parquet" / "fact_population_summary" / "**" / "*.parquet"
            ),
        }
        params = [paths.get(x, x) for x in c["params"]]

        import duckdb

        con = duckdb.connect()
        try:
            cur = con.execute(c["sql"], params)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            con.close()

        return {
            "status": "OK",
            "observation": {
                "metric": plan["metric"],
                "operation": plan["operation"],
                "unit": self._unit(plan["metric"], plan["operation"]),
                "results": rows,
            },
        }

    def _unit(self, metric, op):
        if metric in {"total_population", "age_group_population"}:
            return "persons"
        if metric == "households":
            return "households"
        if metric in {"age_group_share", "child_share", "working_age_share", "aging_share"}:
            return "percentage_point" if op == "change" else "percent"
        if metric == "aging_speed":
            return "percentage_point"
        return None
