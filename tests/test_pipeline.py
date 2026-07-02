import pytest
from gpu_agent.pipeline import build_scorecard, _partition_by_horizon
from gpu_agent.gate import GateError
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating, DIMENSIONS, CategoryStatus
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons

def _finding():
    return Finding.model_validate({
        "id": "f-001", "statement": "s", "kind": "measured", "value": {"number": 8.0, "unit": "%"},
        "trend": "rising", "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": "D2",
        "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 3,
        "entity": "NVDA", "observedAt": "2026-05-01", "capturedAt": "2026-06-12"})

def _rating(fids):
    return DimensionRating(rating="Strong", direction="worsening",
        confidence=Confidence(level="high", basis="b"), findingIds=fids, rationale="r")

def test_build_scorecard_computes_dmi_and_passes_gate():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "Strong but softening.", Confidence(level="medium", basis="b"), reg)
    assert sc.demandSupply.dmiContribution == pytest.approx(0.10 * 1 * 3 / 3)  # 0.10
    assert sc.dimensionRatings["momentum"].rating == "Strong"

def test_build_scorecard_raises_on_anchor_contradiction():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    bad = DimensionRating(rating="Very strong", direction="steady",
        confidence=Confidence(level="high", basis="b"), findingIds=["f-001"], rationale="r")
    with pytest.raises(GateError):
        build_scorecard([_finding()], {"momentum": bad}, {"momentum": -1.8},
                        a, "n", Confidence(level="low", basis="b"), reg)

def test_build_scorecard_fills_all_six_dimension_status():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="high", basis="b"), reg)
    # all six present
    assert set(sc.dimensionStatus.keys()) == set(DIMENSIONS)
    assert sc.dimensionStatus["momentum"].evidenceStatus == "grounded"
    assert sc.dimensionStatus["momentum"].findingCount == 1
    assert sc.dimensionStatus["strategicRisk"].evidenceStatus == "under-supported"
    assert sc.dimensionStatus["strategicRisk"].confidenceCap == "low"
    # grounded ratings unchanged and still the only ones in dimensionRatings (gate-safe)
    assert set(sc.dimensionRatings.keys()) == {"momentum"}

def test_build_scorecard_computes_sdgi_and_direction():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg)
    assert sc.demandSupply.sdgi == pytest.approx(
        sc.demandSupply.dmiContribution - sc.demandSupply.smiContribution)
    assert sc.demandSupply.sdgiDirection == "demand-led"  # dmi 0.10, smi 0.0 -> +0.10

def test_build_scorecard_caps_overall_confidence_when_under_supported():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="high", basis="b"), reg)
    assert sc.confidence.level == "medium"  # 5 dims under-supported -> capped

def test_build_scorecard_passes_category_status_through():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    cs = CategoryStatus(rating="Mixed", direction="steady", bottleneck="bottleneck", reason="r")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg, category_status=cs)
    assert sc.categoryStatus.bottleneck == "bottleneck"


def _leading_finding(fid="f-lead", indicator="rpoBacklog", pd=1, ps=0, mag=3):
    return Finding.model_validate({
        "id": fid, "statement": "s", "kind": "observed", "value": None, "trend": "rising",
        "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05-01", "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": indicator,
        "side": "demand", "polarityDemand": pd, "polaritySupply": ps, "magnitude": mag,
        "entity": "NVDA", "observedAt": "2026-05-01", "capturedAt": "2026-06-12"})


def test_partition_by_horizon_buckets_leading_vs_rest():
    hz = IndicatorHorizons.load("registry/indicators.json")
    mom, out = _partition_by_horizon([_finding(), _leading_finding()], hz)  # D2=lagging, rpoBacklog=leading
    assert [f.indicatorId for f in mom] == ["D2"]
    assert [f.indicatorId for f in out] == ["rpoBacklog"]


def test_build_scorecard_without_horizons_leaves_indices_none():
    reg = IndicatorRegistry.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg)
    assert sc.indices is None


def test_build_scorecard_computes_indices_and_invariant():
    reg = IndicatorRegistry.load("registry/indicators.json")
    hz = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    findings = [_finding(), _leading_finding()]  # D2 (lagging, demand) + rpoBacklog (leading, demand)
    sc = build_scorecard(findings, {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg, horizons=hz)
    assert sc.indices is not None
    # additive invariant: blended == momentum + outlook
    assert abs(sc.demandSupply.dmiContribution
               - (sc.indices.momentum.dmiContribution + sc.indices.outlook.dmiContribution)) < 1e-9
    assert abs(sc.demandSupply.smiContribution
               - (sc.indices.momentum.smiContribution + sc.indices.outlook.smiContribution)) < 1e-9
    # the leading finding lands in Outlook (nonzero demand push), Momentum has the D2 finding
    assert sc.indices.outlook.dmiContribution > 0.0
    assert sc.indices.divergence.outlookFindingCount == 1
    assert sc.indices.divergence.momentumFindingCount == 1


def test_build_scorecard_insufficient_coverage_without_leading():
    reg = IndicatorRegistry.load("registry/indicators.json")
    hz = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg, horizons=hz)
    assert sc.indices.divergence.state == "insufficient-coverage"
    assert sc.indices.outlook.dmiContribution == 0.0
