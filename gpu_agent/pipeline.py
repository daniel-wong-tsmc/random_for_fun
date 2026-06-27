from __future__ import annotations
from typing import Literal
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import (
    Scorecard, DimensionRating, DemandSupply, DimensionStatus, CategoryStatus, DIMENSIONS)
from gpu_agent.assignment import Assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.gate import check_scorecard, GateError

def _sdgi_direction(sdgi: float, eps: float = 0.02) -> Literal["demand-led", "supply-led", "balanced"]:
    if sdgi > eps:
        return "demand-led"
    if sdgi < -eps:
        return "supply-led"
    return "balanced"

def _dimension_status(ratings: dict[str, DimensionRating]) -> dict[str, DimensionStatus]:
    status: dict[str, DimensionStatus] = {}
    for dim in DIMENSIONS:
        r = ratings.get(dim)
        if r is not None:
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
                    *, category_status: CategoryStatus | None = None) -> Scorecard:
    dmi, smi = dmi_smi_contribution(findings, registry, assignment.category, assignment.weights)
    sdgi = dmi - smi
    status = _dimension_status(ratings)
    any_under = any(s.evidenceStatus == "under-supported" for s in status.values())
    sc = Scorecard(
        categoryId=assignment.category, asOf=assignment.asOf, findings=findings,
        dimensionRatings=ratings,
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors,
                                  sdgi=sdgi, sdgiDirection=_sdgi_direction(sdgi)),
        narrative=narrative, confidence=_cap_confidence(confidence, any_under),
        sources=sorted({e.source for f in findings for e in f.evidence}),
        provenance={"assignment": f"{assignment.id}@{assignment.version}"},
        dimensionStatus=status, categoryStatus=category_status)
    violations = check_scorecard(sc)   # FROZEN gate sees only grounded dimensionRatings
    if violations:
        raise GateError(violations)
    return sc
