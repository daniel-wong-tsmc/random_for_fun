from __future__ import annotations
import statistics
from gpu_agent.schema.finding import Finding

def zscore(value: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    sigma = statistics.pstdev(history)
    if sigma == 0:
        return 0.0
    return (value - statistics.mean(history)) / sigma

def _latest(findings: list[Finding]) -> Finding:
    return max(findings, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))

def dmi_smi_contribution(findings, registry, category_id,
                         weight_overrides: dict[str, float] | None = None) -> tuple[float, float]:
    weight_overrides = weight_overrides or {}
    by_indicator: dict[str, list[Finding]] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        if not spec.scoring or spec.side in ("price", "structural"):
            continue
        by_indicator.setdefault(f.indicatorId, []).append(f)
    dmi = smi = 0.0
    for ind_id, fs in by_indicator.items():
        spec = registry.resolve(ind_id, category_id)
        weight = weight_overrides.get(ind_id, spec.weight)
        chosen = _latest(fs)
        dmi += weight * chosen.polarityDemand * chosen.magnitude / 3
        smi += weight * chosen.polaritySupply * chosen.magnitude / 3
    return dmi, smi
