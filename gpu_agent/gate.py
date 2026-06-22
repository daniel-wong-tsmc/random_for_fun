from __future__ import annotations
from gpu_agent.schema.finding import Finding, Kind
from gpu_agent.schema.scorecard import Scorecard

def check_finding(f: Finding) -> list[str]:
    errors: list[str] = []
    if f.kind == Kind.measured:
        if f.value is None:
            errors.append(f"{f.id}: measured finding missing value")
        if not f.evidence:
            errors.append(f"{f.id}: measured finding missing evidence")
    else:
        if f.value is not None:
            errors.append(f"{f.id}: non-measured finding has invented value")
    if not f.why.strip():
        errors.append(f"{f.id}: missing why")
    if f.kind == Kind.hypothesis:
        if not f.reasoning:
            errors.append(f"{f.id}: hypothesis missing reasoning")
        if f.confidence.level == "high":
            errors.append(f"{f.id}: hypothesis confidence capped at medium")
    if f.polarityDemand == 0 and f.polaritySupply == 0:
        errors.append(f"{f.id}: finding affects neither demand nor supply track")
    return errors


_POSITIVE = {"Very strong", "Strong"}
_NEGATIVE = {"Weak", "Very weak"}

def _rating_consistent_with_anchor(rating: str, anchor: float) -> bool:
    if rating in _POSITIVE:
        return anchor > -0.5
    if rating in _NEGATIVE:
        return anchor < 0.5
    return True  # "Mixed" is always allowed

def check_scorecard(sc: Scorecard) -> list[str]:
    errors: list[str] = []
    for f in sc.findings:
        errors.extend(check_finding(f))
    known = {f.id for f in sc.findings}
    for dim, r in sc.dimensionRatings.items():
        if not r.findingIds:
            errors.append(f"{dim}: rating cites no findings")
        for fid in r.findingIds:
            if fid not in known:
                errors.append(f"{dim}: cites unknown finding {fid}")
        anchor = sc.demandSupply.anchors.get(dim)
        if anchor is not None and not _rating_consistent_with_anchor(r.rating, anchor):
            errors.append(f"{dim}: rating {r.rating} contradicts anchor z={anchor:.2f}")
    for f in sc.findings:
        for e in f.evidence:
            if e.source == "AI Market State dashboard" or "market-state.json" in e.url:
                errors.append(f"{f.id}: evidence self-references the dashboard output")
    return errors


class GateError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))
