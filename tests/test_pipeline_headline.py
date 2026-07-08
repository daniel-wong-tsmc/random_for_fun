import pytest
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.registry.indicators import IndicatorRegistry

A = load_assignment("fixtures/asg.chips.merchant-gpu.json")
REG = IndicatorRegistry.load("registry/indicators.json")


def _finding(fid="f-1", tier="secondary", indicatorId="D2", side="demand", pd=1, ps=0):
    return Finding.model_validate({
        "id": fid, "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "w", "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05-01", "excerpt": "e", "tier": tier}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06", "indicatorId": indicatorId,
        "side": side, "polarityDemand": pd, "polaritySupply": ps, "magnitude": 2,
        "entity": "NVDA", "observedAt": "2026-05-01", "capturedAt": "2026-06-12T00:00:00Z"})


def _rating(fids, level="high"):
    return DimensionRating(rating="Strong", direction="steady",
        confidence=Confidence(level=level, basis="b"), findingIds=fids, rationale="r")


# 1. F3 — grounded but secondary-only cited findings -> capped + flagged
def test_secondary_only_dimension_capped_and_flagged():
    sc = build_scorecard([_finding(tier="secondary")],
        {"momentum": _rating(["f-1"], level="high")}, {"momentum": 0.4},
        A, "n", Confidence(level="medium", basis="b"), REG)
    assert sc.dimensionStatus["momentum"].confidenceCap == "medium"
    assert sc.dimensionStatus["momentum"].note == "secondary-only evidence"
    assert sc.dimensionRatings["momentum"].confidence.level == "medium"


# 2. F3 — a primary-backed cited finding -> no cap
def test_primary_backed_dimension_not_capped():
    sc = build_scorecard([_finding(tier="primary")],
        {"momentum": _rating(["f-1"], level="high")}, {"momentum": 0.4},
        A, "n", Confidence(level="medium", basis="b"), REG)
    assert sc.dimensionStatus["momentum"].confidenceCap is None
    assert sc.dimensionStatus["momentum"].note == ""
    assert sc.dimensionRatings["momentum"].confidence.level == "high"


# 2b. F71 (contract v1.4) — an anchor-forced move stamps the EXISTING dimensionStatus note
def test_anchor_bounded_stamp_rides_dimension_status_note():
    sc = build_scorecard([_finding(tier="secondary")],
        {"momentum": _rating(["f-1"], level="high")}, {"momentum": 0.4},
        A, "n", Confidence(level="medium", basis="b"), REG,
        anchor_bounded={"momentum"})
    note = sc.dimensionStatus["momentum"].note
    assert "anchor-bounded on thin evidence" in note
    assert "secondary-only evidence" in note   # the F3 note and the F71 stamp coexist


def test_anchor_bounded_stamp_alone_when_no_other_note():
    sc = build_scorecard([_finding(tier="primary")],
        {"momentum": _rating(["f-1"], level="high")}, {"momentum": 0.4},
        A, "n", Confidence(level="medium", basis="b"), REG,
        anchor_bounded={"momentum"})
    assert sc.dimensionStatus["momentum"].note == "anchor-bounded on thin evidence"


def test_no_anchor_bounded_leaves_notes_byte_identical():
    # Default (no anchor_bounded) must be byte-identical to today: secondary-only note unchanged.
    sc = build_scorecard([_finding(tier="secondary")],
        {"momentum": _rating(["f-1"], level="high")}, {"momentum": 0.4},
        A, "n", Confidence(level="medium", basis="b"), REG)
    assert sc.dimensionStatus["momentum"].note == "secondary-only evidence"


# 3. F37 — Finding.side must match the registry spec side
def test_side_contradicting_registry_raises():
    bad = _finding(fid="f-2", indicatorId="S10", side="demand", pd=1, ps=0, tier="primary")
    with pytest.raises(GateError) as ei:
        build_scorecard([bad], {"bottleneck": _rating(["f-2"])}, {"bottleneck": 0.4},
            A, "n", Confidence(level="medium", basis="b"), REG)
    msg = str(ei.value)
    assert "side" in msg and "S10" in msg
