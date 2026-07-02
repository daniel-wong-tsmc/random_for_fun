from __future__ import annotations
from typing import Literal
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import (
    Scorecard, DimensionRating, DemandSupply, DimensionStatus, CategoryStatus, DIMENSIONS,
    MarketIndices, Divergence)
from gpu_agent.assignment import Assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.gate import check_scorecard, GateError
from gpu_agent.registry.horizon import IndicatorHorizons

def _sdgi_direction(sdgi: float, eps: float = 0.02) -> Literal["demand-led", "supply-led", "balanced"]:
    if sdgi > eps:
        return "demand-led"
    if sdgi < -eps:
        return "supply-led"
    return "balanced"

# direction rank from a demand perspective: demand-led is the "strongest forward" lean
_DIR_RANK = {"demand-led": 1, "balanced": 0, "supply-led": -1}

def _divergence(momentum: DemandSupply, outlook: DemandSupply,
                mom_count: int, out_count: int, *, floor: int = 1) -> Divergence:
    gap = (outlook.sdgi or 0.0) - (momentum.sdgi or 0.0)
    if out_count < floor:
        state, note = "insufficient-coverage", "no leading findings; Outlook deferred to 4-4"
    elif outlook.sdgiDirection == momentum.sdgiDirection:
        state, note = "aligned", ""
    elif _DIR_RANK[outlook.sdgiDirection] < _DIR_RANK[momentum.sdgiDirection]:
        state, note = "diverging-weakening", ""
    else:
        state, note = "diverging-strengthening", ""
    return Divergence(state=state, sdgiGap=gap, outlookFindingCount=out_count,
                      momentumFindingCount=mom_count, note=note)

def _contributes(spec) -> bool:
    """A finding contributes to an index iff its indicator is scoring and not a price/structural overlay
    (mirrors the filter inside the frozen dmi_smi_contribution)."""
    return spec.scoring and spec.side not in ("price", "structural")

def _partition_by_horizon(findings, horizons: IndicatorHorizons):
    """Split findings into (momentum, outlook) by indicator horizon. leading -> outlook; else momentum.
    horizons.horizon() fails loud on an untagged indicator (never a silent drop)."""
    momentum, outlook = [], []
    for f in findings:
        (outlook if horizons.horizon(f.indicatorId) == "leading" else momentum).append(f)
    return momentum, outlook

def _index_for(findings, registry, category, weights) -> tuple[DemandSupply, int]:
    """Compute one DemandSupply index over a finding bucket via the frozen dmi_smi_contribution,
    plus the count of contributing (scoring, non-overlay) findings."""
    dmi, smi = dmi_smi_contribution(findings, registry, category, weights)
    sdgi = dmi - smi
    # Count contributing FINDINGS (not distinct indicators) — this is the coverage-floor
    # unit the spec specifies; dmi_smi_contribution itself uses only the latest per indicator.
    count = sum(1 for f in findings if _contributes(registry.resolve(f.indicatorId, category)))
    return (DemandSupply(dmiContribution=dmi, smiContribution=smi,
                         sdgi=sdgi, sdgiDirection=_sdgi_direction(sdgi)), count)

def _dimension_status(ratings: dict[str, DimensionRating],
                      findings_by_id: dict[str, Finding]) -> dict[str, DimensionStatus]:
    status: dict[str, DimensionStatus] = {}
    for dim in DIMENSIONS:
        r = ratings.get(dim)
        if r is not None:
            cited = [findings_by_id[fid] for fid in r.findingIds if fid in findings_by_id]
            secondary_only = bool(cited) and not any(
                e.tier == "primary" for f in cited for e in f.evidence)
            if secondary_only:   # F3: headline protection — no primary evidence under this rating
                status[dim] = DimensionStatus(
                    evidenceStatus="grounded", findingCount=len(r.findingIds),
                    confidenceCap="medium", note="secondary-only evidence")
            else:
                status[dim] = DimensionStatus(evidenceStatus="grounded", findingCount=len(r.findingIds))
        else:
            status[dim] = DimensionStatus(
                evidenceStatus="under-supported", findingCount=0, confidenceCap="low",
                note=f"no findings mapped to {dim} this cycle")
    return status

def _cap_confidence(confidence: Confidence, any_under_supported: bool) -> Confidence:
    if any_under_supported and confidence.level == "high":
        return Confidence(level="medium",
                          basis=f"{confidence.basis}; capped: one or more dimensions under-supported")
    return confidence

def build_scorecard(findings: list[Finding], ratings: dict[str, DimensionRating],
                    anchors: dict[str, float], assignment: Assignment,
                    narrative: str, confidence: Confidence, registry,
                    *, category_status: CategoryStatus | None = None,
                    horizons: IndicatorHorizons | None = None) -> Scorecard:
    ratings = dict(ratings)   # F3 caps replace entries; never mutate the caller's dict
    findings_by_id = {f.id: f for f in findings}
    side_violations = [
        f"{f.id}: side '{f.side}' contradicts registry side '{spec.side}' for {f.indicatorId}"
        for f in findings
        for spec in [registry.resolve(f.indicatorId, assignment.category)]
        if spec.side is not None and f.side != spec.side]
    if side_violations:
        raise GateError(side_violations)   # F37: the registry is the side authority
    dmi, smi = dmi_smi_contribution(findings, registry, assignment.category, assignment.weights)
    sdgi = dmi - smi
    status = _dimension_status(ratings, findings_by_id)
    # F3: cap a grounded rating whose cited findings carry no primary evidence
    for dim, st in status.items():
        r = ratings.get(dim)
        if r is not None and st.confidenceCap == "medium" and r.confidence.level == "high":
            ratings[dim] = r.model_copy(update={"confidence": Confidence(
                level="medium", basis=f"{r.confidence.basis}; capped: secondary-only evidence")})
    any_under = any(s.evidenceStatus == "under-supported" for s in status.values())
    indices = None
    if horizons is not None:
        horizons.validate_coverage(registry)  # fail-loud: every scoring indicator must be tagged
        mom_f, out_f = _partition_by_horizon(findings, horizons)
        momentum, mom_n = _index_for(mom_f, registry, assignment.category, assignment.weights)
        outlook, out_n = _index_for(out_f, registry, assignment.category, assignment.weights)
        indices = MarketIndices(momentum=momentum, outlook=outlook,
                                divergence=_divergence(momentum, outlook, mom_n, out_n))
    sc = Scorecard(
        categoryId=assignment.category, asOf=assignment.asOf, findings=findings,
        dimensionRatings=ratings,
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors,
                                  sdgi=sdgi, sdgiDirection=_sdgi_direction(sdgi)),
        narrative=narrative, confidence=_cap_confidence(confidence, any_under),
        sources=sorted({e.source for f in findings for e in f.evidence}),
        provenance={"assignment": f"{assignment.id}@{assignment.version}"},
        dimensionStatus=status, categoryStatus=category_status, indices=indices)
    violations = check_scorecard(sc)   # FROZEN gate sees only grounded dimensionRatings
    if violations:
        raise GateError(violations)
    return sc
