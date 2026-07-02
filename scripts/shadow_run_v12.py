"""Shadow run: old (pre-v1.2) vs new (v1.2) scoring over the SAME stored 2026-06 findings.

One-shot migration artifact (charter Part 33). Reads store/chips.merchant-gpu/2026-06-v*.json,
takes each stored scorecard's `findings`, and computes DMI/SMI + anchors two ways:

  OLD  - an inline, frozen copy of the pre-v1.2 algorithm:
         * DMI/SMI bucket by indicatorId ONLY (entities shadow each other), latest vintage wins,
           skip !scoring or spec.side in (price, structural).
         * anchors group by registry dimension; the polarity track is the LAST finding's
           per-indicator polarityTrack (order-dependent).
         * uses the pre-v1.2 registry: ONLY D6 changed in v1.2, so we restore D6 to its
           pre-v1.2 spec (momentum / demand / weight 0.12 / scoring true) and use the current
           registry for everything else.

  NEW  - the current package: scoring.dmi_smi_contribution (buckets per (entity, indicator))
         and judgment.briefing.build_briefing (registry-level dimensionTracks, order-independent).

No store writes. Prints a Markdown table to stdout.
"""
from __future__ import annotations
import json, pathlib, sys

# gpu_agent is editable-installed from the MAIN repo checkout; force THIS worktree's
# package onto sys.path[0] so the "new" math is the v1.2 code, not the installed pre-v1.2 one.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from gpu_agent.schema.finding import Finding
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec
from gpu_agent.assignment import load_assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.judgment.briefing import build_briefing

CATEGORY = "chips.merchant-gpu"
STORE = pathlib.Path("store") / CATEGORY
ASSIGN = "fixtures/asg.chips.merchant-gpu.json"

# D6 was the only indicator whose spec changed in v1.2 (momentum/demand/scoring -> price overlay).
_PRE_V12_D6 = IndicatorSpec(
    id="D6", label="GPU rental price", dimension="momentum", polarityTrack="demand",
    side="demand", weight=0.12, unit="USD_per_gpu_hr", kind="measured",
    readsLevelOrSlope="slope", decayLambda=0.6, scoring=True)


def _old_resolve(registry, ind_id, category):
    if ind_id == "D6":
        return _PRE_V12_D6
    return registry.resolve(ind_id, category)


def _latest(findings):
    return max(findings, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))


def _old_dmi_smi(findings, registry, category, weights):
    """Frozen pre-v1.2 DMI/SMI: bucket by indicatorId only (entity shadowing)."""
    by_ind = {}
    for f in findings:
        spec = _old_resolve(registry, f.indicatorId, category)
        if not spec.scoring or spec.side in ("price", "structural"):
            continue
        by_ind.setdefault(f.indicatorId, []).append(f)
    dmi = smi = 0.0
    for ind_id, fs in by_ind.items():
        spec = _old_resolve(registry, ind_id, category)
        weight = weights.get(ind_id, spec.weight)
        chosen = _latest(fs)
        dmi += weight * chosen.polarityDemand * chosen.magnitude / 3
        smi += weight * chosen.polaritySupply * chosen.magnitude / 3
    return dmi, smi


def _old_anchors(findings, registry, category):
    """Frozen pre-v1.2 anchors: last finding's per-indicator polarityTrack wins (order-dependent)."""
    grouped, tracks = {}, {}
    for f in findings:
        spec = _old_resolve(registry, f.indicatorId, category)
        if spec.dimension is None:
            continue
        grouped.setdefault(spec.dimension, []).append(f)
        tracks[spec.dimension] = spec.polarityTrack or "demand"
    anchors = {}
    for dim, fs in grouped.items():
        track = tracks[dim]
        pol = (lambda f: f.polarityDemand if track == "demand" else f.polaritySupply)
        anchors[dim] = sum(pol(f) * f.magnitude / 3 for f in fs) / len(fs)
    return anchors


def _fmt_anchors(a):
    return "{" + ", ".join(f"{k} {v:+.2f}" for k, v in sorted(a.items())) + "}" if a else "{}"


def _notes(findings, old_dmi, new_dmi, old_smi, new_smi):
    notes = []
    d6 = sum(1 for f in findings if f.indicatorId == "D6")
    if d6:
        notes.append(f"{d6} D6 finding(s) dropped from index (price overlay)")
    # multi-entity same-indicator collisions the new per-entity buckets no longer shadow
    seen = {}
    for f in findings:
        seen.setdefault(f.indicatorId, set()).add(f.entity)
    collisions = sorted(k for k, v in seen.items() if len(v) > 1)
    if collisions:
        notes.append("un-shadowed multi-entity: " + ", ".join(collisions))
    notes.append(f"dDMI {new_dmi - old_dmi:+.3f}, dSMI {new_smi - old_smi:+.3f}")
    return "; ".join(notes)


def main():
    registry = IndicatorRegistry.load("registry/indicators.json")
    weights = load_assignment(ASSIGN).weights
    files = sorted(STORE.glob("2026-06-v*.json"), key=lambda p: int(p.stem.split("-v")[-1]))
    header = ("| file | old DMI | new DMI | old SMI | new SMI | old anchors | new anchors | delta notes |")
    sep = ("|---|---|---|---|---|---|---|---|")
    print(header)
    print(sep)
    for p in files:
        sc = json.loads(p.read_text(encoding="utf-8"))
        findings = [Finding.model_validate(d) for d in sc.get("findings", [])]
        old_dmi, old_smi = _old_dmi_smi(findings, registry, CATEGORY, weights)
        new_dmi, new_smi = dmi_smi_contribution(findings, registry, CATEGORY, weights)
        old_anch = _old_anchors(findings, registry, CATEGORY)
        new_anch = build_briefing(findings, registry, CATEGORY).anchors
        print(f"| {p.name} | {old_dmi:+.4f} | {new_dmi:+.4f} | {old_smi:+.4f} | {new_smi:+.4f} "
              f"| {_fmt_anchors(old_anch)} | {_fmt_anchors(new_anch)} "
              f"| {_notes(findings, old_dmi, new_dmi, old_smi, new_smi)} |")


if __name__ == "__main__":
    main()
