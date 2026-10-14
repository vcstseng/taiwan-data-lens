from pathlib import Path
import yaml
from .semantic_plan_validator import SemanticPlanValidator

ROOT = Path(__file__).resolve().parents[1]

class InvestigationValidator:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.plan_validator = SemanticPlanValidator(self.root)
        with open(self.root / "capabilities" / "relationships.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.relationships = data["relationships"]

    def result(self, status, *codes, **extra):
        r = {"status": status, "codes": list(codes)}
        r.update(extra)
        return r

    def _relationship(self, a, b):
        for rel in self.relationships:
            left, right = set(rel["left"]), set(rel["right"])
            if (a in left and b in right) or (b in left and a in right):
                return rel
        return None


    def _time_signature(self, plan):
        if plan.get("period"):
            return ("period", plan["period"])
        return ("range", plan.get("start_period"), plan.get("end_period"))

    def _geography_signature(self, plan):
        s = plan.get("scope") or {}
        if s.get("geography"):
            return ("geography", s["geography"])
        if s.get("origin_geography"):
            return ("geography", s["origin_geography"])
        if s.get("geographies"):
            return ("geographies", tuple(s["geographies"]))
        return ("parent", s.get("parent_geography"), s.get("geography_level"))

    def validate(self, investigation):
        if not isinstance(investigation, dict):
            return self.result("BLOCK", "INVALID_INVESTIGATION_TYPE")
        plans = investigation.get("plans")
        if not isinstance(plans, list) or not plans:
            return self.result("BLOCK", "MISSING_INVESTIGATION_PLANS")

        validated = []
        for i, plan in enumerate(plans):
            r = self.plan_validator.validate(plan)
            validated.append(r)
            if r["status"] == "BLOCK":
                return self.result("BLOCK", "INVALID_SUBPLAN",
                                   plan_index=i, subplan_result=r)
            if r["status"] == "REFRAME":
                return self.result("REFRAME", "SUBPLAN_REQUIRES_REFRAME",
                                   plan_index=i, subplan_result=r)

        if len(plans) == 1:
            return self.result("ACCEPT", "SINGLE_PLAN_INVESTIGATION",
                               validated_plans=validated)

        # v0.1 is deliberately linear: each next step must have an explicit relationship
        # with the immediately preceding metric. No arbitrary graph traversal.
        relationships = []
        for i in range(len(plans)-1):
            a, b = plans[i]["metric"], plans[i+1]["metric"]
            if a == b:
                relationships.append({"type": "same_metric", "execution_enabled": True})
                continue
            rel = self._relationship(a, b)
            if rel is None:
                return self.result("BLOCK", "NO_AUTHORIZED_RELATIONSHIP",
                                   from_metric=a, to_metric=b, edge_index=i)
            if not rel.get("execution_enabled", False):
                return self.result("BLOCK", "RELATIONSHIP_NOT_EXECUTABLE",
                                   relationship_id=rel["id"], edge_index=i,
                                   conditions=rel.get("conditions", []))
            # Gate 2E: relationship conditions are executable contracts, not documentation.
            conds = rel.get("conditions", [])
            if any(c in conds for c in ["same_year", "same_period", "compatible_period"]):
                ta = self._time_signature(plans[i])
                tb = self._time_signature(plans[i+1])
                if ta != tb:
                    return self.result("BLOCK", "RELATIONSHIP_TIME_MISMATCH",
                                       relationship_id=rel["id"], left_time=ta, right_time=tb)
            if "compatible_geography" in conds or "same_geography" in conds:
                ga = self._geography_signature(plans[i])
                gb = self._geography_signature(plans[i+1])
                if ga != gb:
                    return self.result("BLOCK", "RELATIONSHIP_GEOGRAPHY_MISMATCH",
                                       relationship_id=rel["id"], left_geography=ga, right_geography=gb)
            relationships.append({
                "id": rel["id"],
                "type": rel["type"],
                "conditions": conds,
                "does_not_support": rel.get("does_not_support", []),
                "execution_enabled": True
            })

        claim = (investigation.get("requested_claim") or "").lower()
        causal_terms = ["造成", "導致", "因為", "所以", "cause", "caused", "because", "drives", "resulted"]
        asks_cause = any(x in claim for x in causal_terms)
        if asks_cause:
            # No v0.1 relationship grants causal authority.
            return self.result("REFRAME", "CAUSAL_CLAIM_NOT_AUTHORIZED",
                               relationships=relationships,
                               supported_mode="investigate aligned observations without causal attribution")

        # Relationship-specific semantic traps.
        for rel in relationships:
            prohibited = [x.lower() for x in rel.get("does_not_support", [])]
            if any("youth outmigration" in x or "age-specific migration" in x for x in prohibited):
                if any(t in claim for t in ["年輕人外移", "青年外移", "young people", "youth outmigration"]):
                    return self.result("REFRAME", "MISSING_SHARED_DIMENSION",
                                       missing_dimension="migration.age",
                                       relationships=relationships)

        return self.result("INVESTIGATE_WITH_LIMITS",
                           "CONTEXTUAL_EVIDENCE_ONLY",
                           relationships=relationships,
                           validated_plans=validated)
