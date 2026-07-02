import pytest
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.judgment.briefing import build_briefing

def _f(fid: str, indicator: str, pD: int, pS: int, mag: int) -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicator, side="demand", polarityDemand=pD, polaritySupply=pS,
        magnitude=mag, entity="E", observedAt="2026-06", capturedAt="2026-06-12T00:00:00Z")

def test_anchor_is_mean_of_signed_polarity_magnitude():
    # momentum is a demand-track dim: uses polarityDemand. D2(+1,m=3)=1.0, apiArr(-1,m=3)=-1.0 -> mean 0.0
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f("a", "D2", 1, 0, 3), _f("b", "apiArr", -1, 0, 3)]
    b = build_briefing(findings, reg, "chips.merchant-gpu")
    assert b.anchors["momentum"] == pytest.approx(0.0)
    assert b.grouped["momentum"] == ["a", "b"]

def test_supply_track_dim_uses_polarity_supply():
    # bottleneck is the supply-track dim (dimensionTracks): S10(pS=+1, m=2) -> 1*2/3
    reg = IndicatorRegistry.load("registry/indicators.json")
    b = build_briefing([_f("c", "S10", 0, 1, 2)], reg, "chips.merchant-gpu")
    assert b.anchors["bottleneck"] == pytest.approx(2 / 3)

def test_unregistered_indicator_raises():
    reg = IndicatorRegistry.load("registry/indicators.json")
    with pytest.raises(RegistryError):
        build_briefing([_f("d", "totally-unknown", 1, 0, 3)], reg, "chips.merchant-gpu")

def test_dimension_with_no_findings_is_omitted():
    reg = IndicatorRegistry.load("registry/indicators.json")
    b = build_briefing([_f("a", "D2", 1, 0, 3)], reg, "chips.merchant-gpu")
    assert "unitEconomics" not in b.anchors  # grossMargin had no finding
    assert b.findings[0].id == "a"           # all input findings are retained

def test_strategic_risk_finding_forms_an_anchor():
    reg = IndicatorRegistry.load("registry/indicators.json")
    b = build_briefing([_f("r1", "exportControlExposure", -1, 0, 2)], reg, "chips.merchant-gpu")
    assert "strategicRisk" in b.anchors
    assert b.grouped["strategicRisk"] == ["r1"]
