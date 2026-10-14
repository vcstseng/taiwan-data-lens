class CrossFactInvestigationEngine:
    """Validate relationship first, then execute facts independently and compose evidence."""
    def __init__(self, investigation_validator, engines):
        self.validator = investigation_validator
        self.engines = engines

    def execute(self, investigation):
        validation = self.validator.validate(investigation)
        if validation["status"] not in {"ACCEPT", "INVESTIGATE_WITH_LIMITS"}:
            return {"status": validation["status"], "validation": validation, "observations": []}

        observations = []
        for plan in investigation["plans"]:
            engine = self._engine_for(plan["metric"])
            result = engine.execute(plan)
            if result.get("status") != "OK":
                return {"status": "BLOCK", "validation": validation,
                        "codes": ["SUBPLAN_EXECUTION_FAILED"], "failed_result": result,
                        "observations": observations}
            observations.append(result["observation"])

        return {
            "status": validation["status"],
            "codes": validation.get("codes", []),
            "relationships": validation.get("relationships", []),
            "observations": observations,
            "claim_authority": "contextual_evidence_only" if len(observations) > 1 else "single_fact",
            "cross_fact_arithmetic": False,
            "causal_authority": False,
        }

    def _engine_for(self, metric):
        groups = {
            "population": {"total_population","households","age_group_population","age_group_share","child_share","working_age_share","aging_share","aging_speed"},
            "migration": {"migration_flow_count","migration_destination_share"},
            "marital_marriage": {"marital_population","marital_status_share","unmarried_share","partnered_share","divorced_stock_share","marriage_person_count","marriage_person_share","same_sex_marriage_person_share"},
        }
        for name, metrics in groups.items():
            if metric in metrics:
                if name not in self.engines: raise ValueError(f"missing engine: {name}")
                return self.engines[name]
        raise ValueError(f"no deterministic engine for metric: {metric}")
