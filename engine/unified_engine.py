from pathlib import Path

POPULATION = {"total_population","households","age_group_population","age_group_share","child_share","working_age_share","aging_share","aging_speed"}
MIGRATION = {"migration_flow_count","migration_destination_share"}
FERTILITY = {"total_fertility_rate","general_fertility_rate","age_specific_fertility_rate"}
MARITAL_MARRIAGE = {"marital_population","marital_status_share","unmarried_share","partnered_share","divorced_stock_share","marriage_person_count","marriage_person_share","same_sex_marriage_person_share"}

class UnifiedDeterministicEngine:
    """Single deterministic entry point for every executable v0.1 metric."""
    def __init__(self, root=None, data_root=None, engines=None, plan_validator=None, investigation_engine=None):
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
        self.data_root = Path(data_root) if data_root is not None else self.root
        self.engines = engines or self._build_engines()
        if plan_validator is None:
            from validator.semantic_plan_validator import SemanticPlanValidator
            plan_validator = SemanticPlanValidator(self.root)
        self.plan_validator = plan_validator
        self.investigation_engine = investigation_engine

    def _build_engines(self):
        import duckdb
        from .population_engine import PopulationEngine
        from .migration_engine import MigrationEngine
        from .marital_marriage_engine import MaritalMarriageEngine
        from .fertility_engine import FertilityEngine
        con = duckdb.connect()
        self._shared_connection = con
        return {
            "population": PopulationEngine(self.root, self.data_root),
            "migration": MigrationEngine(con, self.data_root / "parquet" / "fact_migration" / "**" / "*.parquet"),
            "fertility": FertilityEngine(con, self.data_root / "parquet" / "fact_fertility" / "**" / "*.parquet"),
            "marital_marriage": MaritalMarriageEngine(
                con,
                self.data_root / "parquet" / "fact_marital_population" / "**" / "*.parquet",
                self.data_root / "parquet" / "fact_marriage" / "**" / "*.parquet",
            ),
        }

    def route(self, metric):
        if metric in POPULATION: return "population"
        if metric in MIGRATION: return "migration"
        if metric in MARITAL_MARRIAGE: return "marital_marriage"
        if metric in FERTILITY: return "fertility"
        return None

    def execute(self, plan):
        validation = self.plan_validator.validate(plan)
        if validation["status"] != "ACCEPT":
            return {"status": validation["status"], "validation": validation, "observation": None}
        route = self.route(plan["metric"])
        if route is None or route not in self.engines:
            return {"status":"BLOCK","validation":{"status":"BLOCK","codes":["NO_DETERMINISTIC_ENGINE"]},"observation":None}
        result = self.engines[route].execute(plan)

        if result.get("status") == "OK":
            result["engine"] = route

            observation = result.get("observation") or {}
            rows = observation.get("results")

            if isinstance(rows, list) and len(rows) == 0:
                result["status"] = "NO_DATA"

        return result

    def execute_investigation(self, investigation):
        if self.investigation_engine is None:
            from validator.investigation_validator import InvestigationValidator
            from .investigation_engine import CrossFactInvestigationEngine
            self.investigation_engine = CrossFactInvestigationEngine(InvestigationValidator(self.root), self.engines)
        return self.investigation_engine.execute(investigation)

    def close(self):
        con = getattr(self, "_shared_connection", None)
        if con is not None:
            con.close()
            self._shared_connection = None
