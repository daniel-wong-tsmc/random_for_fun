from __future__ import annotations
from gpu_agent.schema.finding import Finding

def _latest(findings: list[Finding]) -> Finding:
    return max(findings, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))

def dmi_smi_contribution(findings, registry, category_id,
                         weight_overrides: dict[str, float] | None = None) -> tuple[float, float]:
    weight_overrides = weight_overrides or {}
    by_key: dict[tuple[str, str], list[Finding]] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        # Use the registry spec's side (not the finding's own side field) — registry is authority.
        if not spec.scoring or spec.side in ("price", "structural"):
            continue
        by_key.setdefault((f.entity, f.indicatorId), []).append(f)   # F7: entity shadowing fix
    dmi = smi = 0.0
    for (_entity, ind_id), fs in by_key.items():
        spec = registry.resolve(ind_id, category_id)
        weight = weight_overrides.get(ind_id, spec.weight)
        chosen = _latest(fs)
        dmi += weight * chosen.polarityDemand * chosen.magnitude / 3
        smi += weight * chosen.polaritySupply * chosen.magnitude / 3
    return dmi, smi
