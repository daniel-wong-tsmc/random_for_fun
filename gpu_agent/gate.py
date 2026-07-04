from __future__ import annotations
import re
from gpu_agent.schema.finding import Finding, Kind
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.config import min_distinct_publishers
from gpu_agent.publisher import publisher_key

_ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")

def _future_dated(date: str, as_of: str) -> bool:
    """Grain-aware vintage compare: truncate the evidence date to asOf's grain
    (month 'YYYY-MM' or day 'YYYY-MM-DD') and compare lexically."""
    g = len(as_of)
    return bool(as_of) and date[:g] > as_of

def check_finding(f: Finding, *, valid_targets: frozenset[str] | None = None) -> list[str]:
    errors: list[str] = []
    if f.kind == Kind.measured and f.value is None:
        errors.append(f"{f.id}: measured finding missing value")
    if f.kind != Kind.measured and f.value is not None:
        errors.append(f"{f.id}: non-measured finding has invented value")
    if f.kind in (Kind.measured, Kind.observed) and not f.evidence:
        errors.append(f"{f.id}: {f.kind.value} finding missing evidence")   # F2a
    if not f.why.strip():
        errors.append(f"{f.id}: missing why")
    if f.kind == Kind.hypothesis:
        if not f.reasoning:
            errors.append(f"{f.id}: hypothesis missing reasoning")
        if f.confidence.level == "high":
            errors.append(f"{f.id}: hypothesis confidence capped at medium")
    # F2e — headline protection at finding level (contract v1.3: >=N distinct publishers
    # unlock high confidence — docs/migrations/2026-07-contract-v1.3.md)
    if f.evidence and all(e.tier == "secondary" for e in f.evidence) and f.confidence.level == "high":
        n = min_distinct_publishers()
        publishers = {publisher_key(e) for e in f.evidence}
        if len(publishers) < n:
            errors.append(f"{f.id}: secondary-only evidence cannot support high confidence "
                          f"({len(publishers)} distinct publishers < {n})")
    # F8 — price is an overlay: a level without a baseline is not momentum
    if f.side == "price":
        if f.trend == "unknown" and (f.polarityDemand != 0 or f.polaritySupply != 0):
            errors.append(f"{f.id}: static price level (trend unknown) must carry polarity 0")
    elif f.polarityDemand == 0 and f.polaritySupply == 0:
        errors.append(f"{f.id}: finding affects neither demand nor supply track")
    # F17 — vintage honesty
    if not _ISO_PREFIX.match(f.observedAt or ""):
        errors.append(f"{f.id}: observedAt not ISO (YYYY-MM-DD...)")
    for e in f.evidence:
        if not _ISO_PREFIX.match(e.date or ""):
            errors.append(f"{f.id}: evidence date not ISO (YYYY-MM-DD): {e.date!r}")
        elif _future_dated(e.date, f.asOf):
            errors.append(f"{f.id}: future-dated evidence {e.date} vs asOf {f.asOf}")
    # F21 — impact quality
    if not f.impact.targets:
        errors.append(f"{f.id}: impact.targets empty")
    if not f.impact.mechanism.strip():
        errors.append(f"{f.id}: impact.mechanism empty")
    if valid_targets is not None:
        for t in f.impact.targets:
            if t not in valid_targets:
                errors.append(f"{f.id}: impact target '{t}' not in taxonomy")
    return errors


_POSITIVE = {"Very strong", "Strong"}
_NEGATIVE = {"Weak", "Very weak"}
_ANCHOR_TOL = 0.15   # F36: was 0.5 — "Very strong" at anchor -0.49 is not judgment room

def _rating_consistent_with_anchor(rating: str, anchor: float) -> bool:
    if rating in _POSITIVE:
        return anchor > -_ANCHOR_TOL
    if rating in _NEGATIVE:
        return anchor < _ANCHOR_TOL
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
            errors.append(f"{dim}: rating {r.rating} contradicts anchor a={anchor:.2f}")
    for f in sc.findings:
        for e in f.evidence:
            if e.source == "AI Market State dashboard" or "market-state.json" in e.url:
                errors.append(f"{f.id}: evidence self-references the dashboard output")
    return errors


class GateError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))
