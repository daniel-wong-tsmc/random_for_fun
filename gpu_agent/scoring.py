from __future__ import annotations
from gpu_agent.schema.finding import Finding

# F79 — scoring v2.0 (Part 33 versioned migration). The v1.x path below
# (dmi_smi_contribution) is FROZEN and byte-identical — its replay fidelity over every
# stored scorecard is pinned by tests/test_scoring_v1_replay_pin.py. v2 is an ADDITIVE
# entry point (score_v2) delegating to the series engine; nothing user-facing renders
# v2 before the G4 cutover. Absorbs the deferred F60 scoring half; supersedes the
# reserved v1.5 side-semantics slot.
SCORING_VERSION = "2.0"


def score_v2(series_registry, series_root, *, as_of: str,
             impulses=()) -> tuple[float, float]:
    """The v2.0 index: (DMI, SMI) as weighted z-sums with freshness decay + event
    impulses over the vintage-stamped series store. See gpu_agent/series.py."""
    from gpu_agent.series import compose_index   # local: keeps the v1 import graph intact
    return compose_index(series_registry, series_root, as_of=as_of, impulses=impulses)


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
