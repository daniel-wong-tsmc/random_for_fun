"""Replay: recompute the stored 2026-06 scorecards under v1.2 MATH as new store versions.

For vN in v1..v6 IN ORDER, load the stored Scorecard, recompute demandSupply (per-(entity,
indicator) DMI/SMI, sdgi, direction, order-independent anchors) and indices (only when the
original carried them), stamp provenance.replayOf / provenance.migration, and APPEND via
JsonStore — natural numbering yields v7..v12 (v12 = replay of v6).

Historical judgment is immutable: findings / ratings / narrative / confidence / dimensionStatus /
categoryStatus are copied verbatim. This re-runs the MATH, not the gate — the stored findings
predate the v1.2 trust boundary and are NOT re-validated. Originals v1..v6 are never modified.
"""
from __future__ import annotations
import pathlib, sys

# gpu_agent is editable-installed from the MAIN repo checkout; force THIS worktree first.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from gpu_agent.schema.scorecard import Scorecard, DemandSupply, MarketIndices
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.pipeline import _partition_by_horizon, _index_for, _divergence, _sdgi_direction
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.assignment import load_assignment
from gpu_agent.store import JsonStore

CATEGORY = "chips.merchant-gpu"
STORE_ROOT = pathlib.Path("store")
ASSIGN = "fixtures/asg.chips.merchant-gpu.json"


def replay(sc: Scorecard, n: int, registry, weights, horizons) -> Scorecard:
    findings = sc.findings
    dmi, smi = dmi_smi_contribution(findings, registry, CATEGORY, weights)
    sdgi = dmi - smi
    anchors = build_briefing(findings, registry, CATEGORY).anchors if findings else {}
    ds = DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors,
                      sdgi=sdgi, sdgiDirection=_sdgi_direction(sdgi))
    indices = None
    if sc.indices is not None:   # only re-run the two-index split where the original had it
        mom_f, out_f = _partition_by_horizon(findings, horizons)
        momentum, mom_n = _index_for(mom_f, registry, CATEGORY, weights)
        outlook, out_n = _index_for(out_f, registry, CATEGORY, weights)
        indices = MarketIndices(momentum=momentum, outlook=outlook,
                                divergence=_divergence(momentum, outlook, mom_n, out_n))
    prov = dict(sc.provenance)
    prov["replayOf"] = f"2026-06-v{n}"
    prov["migration"] = "contract-v1.2"
    return sc.model_copy(update={"demandSupply": ds, "indices": indices, "provenance": prov})


def main():
    registry = IndicatorRegistry.load("registry/indicators.json")
    horizons = IndicatorHorizons.load("registry/indicators.json")
    weights = load_assignment(ASSIGN).weights
    store = JsonStore(STORE_ROOT)
    src = STORE_ROOT / CATEGORY
    for n in range(1, 7):
        sc = Scorecard.model_validate_json((src / f"2026-06-v{n}.json").read_text(encoding="utf-8"))
        replayed = replay(sc, n, registry, weights, horizons)
        out = store.append(replayed)
        ds = replayed.demandSupply
        print(f"2026-06-v{n} -> {out.name}  DMI={ds.dmiContribution:+.4f} SMI={ds.smiContribution:+.4f}")


if __name__ == "__main__":
    main()
