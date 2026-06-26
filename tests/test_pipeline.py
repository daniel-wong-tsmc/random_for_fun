import pytest
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.registry.indicators import IndicatorRegistry

def _finding():
    return Finding.model_validate({
        "id": "f-001", "statement": "s", "kind": "measured", "value": {"number": 8.0, "unit": "%"},
        "trend": "rising", "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": "D2",
        "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 3,
        "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12"})

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
