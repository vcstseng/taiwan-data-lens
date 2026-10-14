from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

class SemanticPlanValidator:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.metrics = self._load("capabilities/metrics.yaml")["metrics"]
        self.facts = self._load("capabilities/facts.yaml")["facts"]
        self.operations = self._load("capabilities/operations.yaml")["operations"]
        self.schema = self._load("protocol/semantic_plan.schema.yaml")["semantic_plan"]

    def _load(self, rel):
        with open(self.root / rel, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def result(self, status, *codes, **extra):
        x = {"status": status, "codes": list(codes)}
        x.update(extra)
        return x

    def validate(self, plan):
        if not isinstance(plan, dict):
            return self.result("BLOCK", "INVALID_PLAN_TYPE")

        unknown = sorted(set(plan) - set(self.schema["allowed_fields"]))
        forbidden = sorted(set(plan) & set(self.schema["forbidden_fields"]))
        if unknown or forbidden:
            return self.result("BLOCK", "ILLEGAL_PLAN_FIELD",
                               illegal_fields=sorted(set(unknown + forbidden)))

        missing = [x for x in self.schema["required"] if not plan.get(x)]
        if missing:
            return self.result("BLOCK", "MISSING_REQUIRED_FIELD", fields=missing)

        op = plan["operation"]
        metric_name = plan["metric"]

        if op not in self.operations:
            return self.result("BLOCK", "UNKNOWN_OPERATION", operation=op)
        if metric_name not in self.metrics:
            return self.result("BLOCK", "UNKNOWN_METRIC", metric=metric_name)

        metric = self.metrics[metric_name]
        if metric.get("status") != "normal" or not metric.get("display_enabled", True):
            return self.result("BLOCK", "METRIC_NOT_EXECUTABLE",
                               metric=metric_name,
                               metric_status=metric.get("status"),
                               unit=metric.get("unit"))
        if op not in metric.get("allowed_operations", []):
            return self.result("BLOCK", "OPERATION_NOT_ALLOWED_FOR_METRIC",
                               operation=op, metric=metric_name)

        req = self.schema.get("operation_requirements", {}).get(op, {})
        for field in req.get("requires", []):
            if not plan.get(field):
                return self.result("BLOCK", "MISSING_OPERATION_FIELD",
                                   operation=op, field=field)
        time_mode = req.get("time")
        if time_mode == "period" and not plan.get("period"):
            return self.result("BLOCK", "MISSING_PERIOD")
        if time_mode == "range" and (not plan.get("start_period") or not plan.get("end_period")):
            return self.result("BLOCK", "MISSING_PERIOD_RANGE")
        if plan.get("period") and (plan.get("start_period") or plan.get("end_period")):
            return self.result("BLOCK", "CONFLICTING_TIME_FIELDS")

        if "order" in plan and plan["order"] not in self.schema["enums"]["order"]:
            return self.result("BLOCK", "INVALID_ORDER")
        if "limit" in plan and (not isinstance(plan["limit"], int) or isinstance(plan["limit"], bool) or plan["limit"] <= 0):
            return self.result("BLOCK", "INVALID_LIMIT")

        # Deliberately unresolved in v0.1.
        if op == "decompose":
            return self.result("BLOCK", "DECOMPOSITION_CONTRACT_MISSING")

        fact = self.facts[metric["source_fact"]]

        # Parameters are controlled semantic inputs, never arbitrary expressions.
        supplied_params = plan.get("parameters") or {}
        if not isinstance(supplied_params, dict):
            return self.result("BLOCK", "INVALID_PARAMETERS")
        raw_declared_params = metric.get("parameters") or {}
        # Gate 1 uses a deliberately compact parameter notation:
        #   age_range: controlled_age_range
        #   age_band: [allowed values]
        #   fixed_*: internal fixed semantics, not planner-supplied parameters
        #   migration origin/destination/sex are represented by scope/filter, not parameters.
        declared_params = {k: v for k, v in raw_declared_params.items()
                           if not k.startswith("fixed_")
                           and not (metric_name == "migration_flow_count" and k in {"origin","destination","sex"})}
        illegal_params = sorted(set(supplied_params) - set(declared_params))
        if illegal_params:
            return self.result("BLOCK", "UNSUPPORTED_PARAMETER", parameters=illegal_params)

        if metric_name in {"age_group_population", "age_group_share"} and "age_range" not in supplied_params:
            return self.result("BLOCK", "MISSING_METRIC_PARAMETER", parameter="age_range")
        if metric_name == "age_specific_fertility_rate" and plan.get("operation") != "profile" and "age_band" not in supplied_params:
            return self.result("BLOCK", "MISSING_METRIC_PARAMETER", parameter="age_band")

        for name, spec in declared_params.items():
            if name in supplied_params:
                r = self._validate_parameter(name, supplied_params[name], spec)
                if r:
                    return r

        # Filters must target real fact dimensions and use scalar/list values only.
        filters = plan.get("filters") or {}
        if not isinstance(filters, dict):
            return self.result("BLOCK", "INVALID_FILTERS")
        dims = self._fact_dimension_names(fact)
        illegal_filters = sorted(set(filters) - dims)
        if illegal_filters:
            return self.result("BLOCK", "UNSUPPORTED_FILTER_DIMENSION",
                               dimensions=illegal_filters, supported=sorted(dims))
        for k, v in filters.items():
            if isinstance(v, dict):
                return self.result("BLOCK", "ARBITRARY_FILTER_EXPRESSION", dimension=k)
            if isinstance(v, list) and not v:
                return self.result("BLOCK", "EMPTY_FILTER", dimension=k)

        if op == "profile":
            dim = plan.get("profile_dimension")
            if metric_name == "migration_flow_count":
                allowed_profile_dims = {"destination_county", "sex"}
            elif metric_name == "age_specific_fertility_rate":
                allowed_profile_dims = {"age_band"}
            else:
                allowed_profile_dims = dims
            if dim not in allowed_profile_dims:
                return self.result("BLOCK", "UNSUPPORTED_DIMENSION",
                                   dimension=dim, supported=sorted(allowed_profile_dims))

        scope = plan.get("scope") or {}
        if not isinstance(scope, dict):
            return self.result("BLOCK", "INVALID_SCOPE")
        allowed_scope = {
            "geography", "geographies", "geography_level", "parent_geography",
            "origin_geography", "destination_geography",
            "origin_geography_level", "destination_geography_level"
        }
        illegal_scope = sorted(set(scope) - allowed_scope)
        if illegal_scope:
            return self.result("BLOCK", "UNSUPPORTED_SCOPE_FIELD", fields=illegal_scope)
        if "geography" in scope and "geographies" in scope:
            return self.result("BLOCK", "CONFLICTING_GEOGRAPHY_SCOPE")

        # Gate 2 geography-rollup amendment: only additive/recomputable metrics
        # may request country/county rollups. Rates such as fertility remain
        # at their official source geography and migration keeps its existing
        # directional contract.
        geo_level = scope.get("geography_level")
        if geo_level in {"country", "county"}:
            rollup_metrics = {
                "total_population", "households", "age_group_population",
                "age_group_share", "child_share", "working_age_share",
                "aging_share", "aging_speed",
                "marital_population", "marital_status_share",
                "unmarried_share", "partnered_share", "divorced_stock_share",
                "marriage_person_count", "marriage_person_share",
                "same_sex_marriage_person_share",
            }
            if metric_name not in rollup_metrics:
                return self.result("BLOCK", "GEOGRAPHY_ROLLUP_NOT_AUTHORIZED",
                                   metric=metric_name, geography_level=geo_level)
            if geo_level == "country" and scope.get("parent_geography"):
                return self.result("BLOCK", "COUNTRY_ROLLUP_CANNOT_HAVE_PARENT")
        elif geo_level and geo_level not in {"district", "village"}:
            return self.result("BLOCK", "UNSUPPORTED_GEOGRAPHY_LEVEL",
                               geography_level=geo_level)
        if op == "compare":
            gs = scope.get("geographies")
            if not isinstance(gs, list) or len(gs) < 2:
                return self.result("BLOCK", "COMPARE_REQUIRES_MULTIPLE_GEOGRAPHIES")
        if metric["source_fact"] == "migration_flow":
            dest_level = scope.get("destination_geography_level")
            if dest_level and dest_level != "county":
                return self.result("BLOCK", "UNSUPPORTED_GEOGRAPHY_RESOLUTION",
                                   requested=dest_level, maximum="county")

        # Period format must match fact frequency. This checks semantics, not source availability.
        periods = [x for x in (plan.get("period"), plan.get("start_period"), plan.get("end_period")) if x]
        time_grain = (fact.get("dimensions") or {}).get("time")
        expected_len = 5 if time_grain == "month" else 3
        if any(not isinstance(p, str) or not p.isdigit() or len(p) != expected_len for p in periods):
            return self.result("BLOCK", "INVALID_PERIOD_FORMAT",
                               time_grain=time_grain)
        if plan.get("start_period") and plan.get("end_period") and plan["start_period"] > plan["end_period"]:
            return self.result("BLOCK", "INVALID_PERIOD_RANGE")

        claim = (plan.get("requested_claim") or "").lower()
        unsupported = [str(x).lower() for x in metric.get("claims", {}).get("does_not_support", [])]
        trigger_map = {
            "divorce risk": ["容易離婚", "離婚風險", "divorce risk", "probability of divorce"],
            "divorce incidence": ["離婚率", "divorce rate", "divorce incidence"],
            "marriage rate": ["結婚率", "marriage rate"],
            "marriage propensity": ["容易結婚", "結婚機率", "marriage propensity"],
            "cause of aging": ["造成老化", "導致老化", "cause of aging"],
            "causal explanation": ["造成", "導致", "因為", "caused", "because"],
        }
        hits = []
        for unsupported_claim in unsupported:
            for key, triggers in trigger_map.items():
                if key in unsupported_claim and any(t.lower() in claim for t in triggers):
                    hits.append(unsupported_claim)
        if hits:
            return self.result("REFRAME", "UNSUPPORTED_CLAIM",
                               metric=metric_name,
                               unsupported_claims=sorted(set(hits)))

        return self.result("ACCEPT", metric=metric_name, operation=op)

    def _validate_parameter(self, name, value, spec):
        if name == "age_range":
            if not isinstance(value, dict):
                return self.result("BLOCK", "INVALID_PARAMETER_VALUE", parameter=name)
            if set(value) - {"min", "max"} or not value:
                return self.result("BLOCK", "INVALID_PARAMETER_VALUE", parameter=name)
            vals = [value.get("min"), value.get("max")]
            if any(v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0) for v in vals):
                return self.result("BLOCK", "INVALID_PARAMETER_VALUE", parameter=name)
            if value.get("min") is not None and value.get("max") is not None and value["min"] > value["max"]:
                return self.result("BLOCK", "INVALID_PARAMETER_VALUE", parameter=name)
        elif isinstance(spec, list):
            if value not in spec:
                return self.result("BLOCK", "INVALID_PARAMETER_VALUE",
                                   parameter=name, allowed_values=spec)
        return None

    @staticmethod
    def _fact_dimension_names(fact):
        names = set()
        for k, v in (fact.get("dimensions") or {}).items():
            if k == "geography":
                names.add("geography")
            elif k == "origin_geography":
                names.add("origin_geography")
            elif k == "destination_geography":
                names.add("destination_county")
            else:
                names.add(k)
        return names
