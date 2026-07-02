import pytest
from gpu_agent.gate import check_finding, check_scorecard
from gpu_agent.schema.finding import Finding
from gpu_agent.schema.scorecard import Scorecard


def _f(**over) -> Finding:
    data = {
        "id": "f", "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "w", "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e", "tier": "primary"}],
        "reasoning": None, "confidence": {"level": "medium", "basis": "b"}, "dispersion": None,
        "asOf": "2026-06", "indicatorId": "D2", "side": "demand", "polarityDemand": 1,
        "polaritySupply": 0, "magnitude": 2, "entity": "NVDA", "observedAt": "2026-06-01",
        "capturedAt": "2026-06-12T00:00:00Z", "schemaVersion": "1.2",
    }
    data.update(over)
    return Finding.model_validate(data)


def _sc(**over) -> Scorecard:
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06",
        "findings": [_f(id="f-001").model_dump()],
        "dimensionRatings": {"momentum": {"rating": "Very strong", "direction": "steady",
            "confidence": {"level": "high", "basis": "b"}, "findingIds": ["f-001"], "rationale": "r"}},
        "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": -0.2}},
        "narrative": "n", "confidence": {"level": "medium", "basis": "b"}, "sources": ["S"], "provenance": {},
    }
    data.update(over)
    return Scorecard.model_validate(data)


# 1. F2a
def test_observed_finding_missing_evidence():
    errs = check_finding(_f(kind="observed", value=None, evidence=[]))
    assert any("observed finding missing evidence" in e for e in errs)

# 2. F2e
def test_secondary_only_cannot_support_high_confidence():
    f = _f(kind="measured", value={"number": 1.0, "unit": "x"},
           evidence=[{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e", "tier": "secondary"}],
           confidence={"level": "high", "basis": "b"})
    assert any("secondary-only evidence cannot support high confidence" in e for e in check_finding(f))

# 3. F8
def test_price_static_level_must_carry_polarity_zero():
    f = _f(side="price", trend="unknown", polarityDemand=1, polaritySupply=0)
    assert any("static price level (trend unknown) must carry polarity 0" in e for e in check_finding(f))

# 4. F8 exemption
def test_price_overlay_zero_polarity_not_affects_neither():
    f = _f(side="price", trend="unknown", polarityDemand=0, polaritySupply=0, magnitude=1)
    assert not any("affects neither" in e for e in check_finding(f))

# 5.
def test_demand_zero_zero_still_affects_neither():
    f = _f(side="demand", polarityDemand=0, polaritySupply=0)
    assert any("affects neither demand nor supply track" in e for e in check_finding(f))

# 6. F17
def test_evidence_date_not_iso():
    f = _f(evidence=[{"source": "S", "url": "u", "date": "July 2, 2026", "excerpt": "e", "tier": "primary"}])
    assert any("evidence date not ISO" in e for e in check_finding(f))

# 7. F17
def test_observed_at_not_iso():
    f = _f(observedAt="soon")
    assert any("observedAt not ISO" in e for e in check_finding(f))

# 8. F17 month grain
def test_future_dated_evidence_month_grain():
    f = _f(asOf="2026-06",
           evidence=[{"source": "S", "url": "u", "date": "2026-07-02", "excerpt": "e", "tier": "primary"}])
    assert any("future-dated evidence" in e for e in check_finding(f))

# 9. F17 day grain
def test_future_dated_evidence_day_grain():
    future = _f(asOf="2026-07-02", observedAt="2026-07-01",
                evidence=[{"source": "S", "url": "u", "date": "2026-07-15", "excerpt": "e", "tier": "primary"}])
    assert any("future-dated evidence" in e for e in check_finding(future))
    clean = _f(asOf="2026-07-02", observedAt="2026-07-01",
               evidence=[{"source": "S", "url": "u", "date": "2026-07-01", "excerpt": "e", "tier": "primary"}])
    assert check_finding(clean) == []

# 10. F21
def test_impact_targets_empty():
    f = _f(impact={"targets": [], "direction": "positive", "mechanism": "m"})
    assert any("impact.targets empty" in e for e in check_finding(f))

# 11. F21
def test_impact_mechanism_empty():
    f = _f(impact={"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "  "})
    assert any("impact.mechanism empty" in e for e in check_finding(f))

# 12. F21 taxonomy membership
def test_impact_target_not_in_taxonomy():
    f = _f(impact={"targets": ["made.up"], "direction": "positive", "mechanism": "m"})
    errs = check_finding(f, valid_targets=frozenset({"chips.merchant-gpu"}))
    assert any("impact target 'made.up' not in taxonomy" in e for e in errs)

# 13. F36 band error + message label
def test_band_contradiction_errors_with_a_label():
    errs = check_scorecard(_sc())  # rating "Very strong", anchor -0.2
    assert any("contradicts anchor a=-0.20" in e for e in errs)
    assert not any("z=" in e for e in errs)

# 14. F36 tolerance
def test_band_tolerance_015_passes():
    sc = _sc(demandSupply={"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": -0.1}})
    assert not any("contradicts anchor" in e for e in check_scorecard(sc))
