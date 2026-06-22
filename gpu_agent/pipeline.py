from __future__ import annotations
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import Scorecard, DimensionRating, DemandSupply
from gpu_agent.assignment import Assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.gate import check_scorecard, GateError

def build_scorecard(findings: list[Finding], ratings: dict[str, DimensionRating],
                    anchors: dict[str, float], assignment: Assignment,
                    narrative: str, confidence: Confidence) -> Scorecard:
    dmi, smi = dmi_smi_contribution(findings, assignment.weights)
    sc = Scorecard(
        categoryId="chips.merchant-gpu", asOf=assignment.asOf, findings=findings,
        dimensionRatings=ratings,
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors),
        narrative=narrative, confidence=confidence,
        sources=sorted({e.source for f in findings for e in f.evidence}),
        provenance={"assignment": f"{assignment.id}@{assignment.version}"})
    violations = check_scorecard(sc)
    if violations:
        raise GateError(violations)
    return sc
