import pathlib
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG = pathlib.Path("registry/indicators.json")

def _f(fid, indicatorId, pol_d, pol_s, mag):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity="nvidia",
        observedAt="2026-06", capturedAt="2026-06-25T00:00:00Z")

def test_briefing_groups_by_registry_dimension():
    reg = IndicatorRegistry.load(REG)
    findings = [_f("a", "D2", 1, 0, 3), _f("b", "S10", 0, 1, 3)]
    b = build_briefing(findings, reg, "chips.merchant-gpu")
    assert "momentum" in b.grouped
    assert "bottleneck" in b.grouped
    assert b.anchors["momentum"] == 1.0   # demand-track +1 * 3/3
    assert b.anchors["bottleneck"] == 1.0  # supply-track +1 * 3/3

def test_briefing_skips_non_scoring_indicator():
    reg = IndicatorRegistry.load(REG)
    findings = [_f("a", "perfPerWatt", 1, 0, 3)]  # dimension is None
    b = build_briefing(findings, reg, "chips.merchant-gpu")
    assert b.grouped == {}
