from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
import yaml


class CapabilityRegistryError(ValueError):
    pass


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise CapabilityRegistryError(f"{path.name} must contain a YAML mapping")
    return data


def validate_capability_registry(root: str | Path) -> Dict[str, Any]:
    """Validate Gate 3A registry against frozen Gate 1 capability files.

    The registry is an index, not a second execution contract. It therefore
    references Gate 1 metric IDs and derives fact traceability from metrics.yaml.
    """
    root = Path(root)
    registry = _load_yaml(root / "capabilities" / "capability_registry.yaml")
    metrics_doc = _load_yaml(root / "capabilities" / "metrics.yaml")
    facts_doc = _load_yaml(root / "capabilities" / "facts.yaml")

    capabilities = registry.get("capabilities")
    metrics = metrics_doc.get("metrics")
    facts = facts_doc.get("facts")
    if not isinstance(capabilities, dict) or not capabilities:
        raise CapabilityRegistryError("registry must define at least one capability")
    if not isinstance(metrics, dict) or not isinstance(facts, dict):
        raise CapabilityRegistryError("Gate 1 metrics/facts are missing")

    executable_metrics: Set[str] = {
        metric_id for metric_id, spec in metrics.items()
        if spec.get("display_enabled") is True and spec.get("status") == "normal"
    }

    homes: Dict[str, List[str]] = {m: [] for m in executable_metrics}
    capability_facts: Dict[str, List[str]] = {}

    required_fields = {"domain", "topic", "summary", "evidence", "dimensions", "limitations"}
    for capability_id, spec in capabilities.items():
        if not isinstance(spec, dict):
            raise CapabilityRegistryError(f"{capability_id}: capability must be a mapping")
        missing = sorted(required_fields - set(spec))
        if missing:
            raise CapabilityRegistryError(f"{capability_id}: missing fields {missing}")
        if "ODRP" in capability_id.upper():
            raise CapabilityRegistryError(f"{capability_id}: capability IDs must not encode dataset IDs")

        evidence = spec.get("evidence", {})
        metric_ids = evidence.get("metrics") if isinstance(evidence, dict) else None
        if not isinstance(metric_ids, list) or not metric_ids:
            raise CapabilityRegistryError(f"{capability_id}: evidence.metrics must be a non-empty list")

        traced_facts: Set[str] = set()
        for metric_id in metric_ids:
            if metric_id not in metrics:
                raise CapabilityRegistryError(f"{capability_id}: unknown metric {metric_id}")
            metric = metrics[metric_id]
            if metric_id not in executable_metrics:
                raise CapabilityRegistryError(f"{capability_id}: metric {metric_id} is not executable/display-enabled")
            source_fact = metric.get("source_fact")
            if source_fact not in facts:
                raise CapabilityRegistryError(
                    f"{capability_id}: metric {metric_id} references unknown fact {source_fact}"
                )
            homes[metric_id].append(capability_id)
            traced_facts.add(source_fact)

        limitations = spec.get("limitations")
        if not isinstance(limitations, list) or not limitations:
            raise CapabilityRegistryError(f"{capability_id}: limitations must be a non-empty list")
        capability_facts[capability_id] = sorted(traced_facts)

    homeless = sorted(metric_id for metric_id, ids in homes.items() if not ids)
    if homeless:
        raise CapabilityRegistryError(f"executable metrics without a capability home: {homeless}")

    return {
        "status": "PASS",
        "capability_count": len(capabilities),
        "executable_metric_count": len(executable_metrics),
        "metric_homes": {k: v for k, v in sorted(homes.items())},
        "capability_facts": capability_facts,
    }
