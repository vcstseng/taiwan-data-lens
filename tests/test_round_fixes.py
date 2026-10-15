
from engine.migration_compiler import MigrationQueryCompiler
from engine.unified_engine import UnifiedDeterministicEngine
from validator.semantic_plan_validator import SemanticPlanValidator


def test_migration_compiler_accepts_origin_geography():
    plan = {
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11508",
        "profile_dimension": "destination_county",
        "scope": {
            "origin_geography": "臺東縣臺東市"
        },
    }

    compiled = MigrationQueryCompiler().compile(plan)

    assert "origin_district = ?" in compiled["sql"]
    assert compiled["params"][-1] == "臺東縣臺東市"


def test_migration_validator_blocks_missing_origin():
    validator = SemanticPlanValidator()

    result = validator.validate({
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11401",
        "profile_dimension": "destination_county",
        "scope": {},
    })

    assert result["status"] == "BLOCK"
    assert "MISSING_MIGRATION_ORIGIN" in result["codes"]


def test_migration_validator_accepts_valid_origin():
    validator = SemanticPlanValidator()

    result = validator.validate({
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11508",
        "profile_dimension": "destination_county",
        "scope": {
            "origin_geography": "臺東縣臺東市"
        },
    })

    assert result["status"] == "ACCEPT"


def test_unified_engine_converts_empty_results_to_no_data():
    class FakeValidator:
        def validate(self, plan):
            return {"status": "ACCEPT", "codes": []}

    class FakeEngine:
        def execute(self, plan):
            return {
                "status": "OK",
                "observation": {
                    "metric": "migration_flow_count",
                    "operation": "profile",
                    "unit": "persons",
                    "results": [],
                },
            }

    engine = UnifiedDeterministicEngine(
        engines={"migration": FakeEngine()},
        plan_validator=FakeValidator(),
    )

    result = engine.execute({
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11401",
        "profile_dimension": "destination_county",
        "scope": {
            "origin_geography": "臺東縣臺東市"
        },
    })

    assert result["status"] == "NO_DATA"
    assert result["observation"]["results"] == []
    assert result["engine"] == "migration"


def test_migration_county_profile_compiles_aggregate_query():
    compiler = MigrationQueryCompiler()

    result = compiler.compile({
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11508",
        "profile_dimension": "destination_county",
        "scope": {
            "origin_geography": "臺東縣",
            "geography_level": "county",
        },
    })

    assert "origin_district LIKE ?" in result["sql"]
    assert "GROUP BY period,destination_county" in result["sql"]
    assert result["params"] == [
        "{migration_path}",
        "11508",
        "臺東縣%",
    ]


def test_migration_county_profile_passes_validator():
    validator = SemanticPlanValidator()

    result = validator.validate({
        "operation": "profile",
        "metric": "migration_flow_count",
        "period": "11508",
        "profile_dimension": "destination_county",
        "scope": {
            "origin_geography": "臺東縣",
            "geography_level": "county",
        },
    })

    assert result["status"] == "ACCEPT"

