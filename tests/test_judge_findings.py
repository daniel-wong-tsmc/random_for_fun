import json
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.judgment.judge import judge_findings, JudgmentError

def _f(fid="real-1", indicator="D2", pD=1, pS=0, mag=2) -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        evidence=[{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e", "tier": "primary"}],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicator, side="demand", polarityDemand=pD, polaritySupply=pS,
        magnitude=mag, entity="E", observedAt="2026-06-01", capturedAt="2026-06-12T00:00:00Z")

def _judgment(rating, find_ids=("real-1",), bottleneck="momentum"):
    return json.dumps({
        "dimensions": {"momentum": {
            "rating": rating, "direction": "steady",
            "findingIds": list(find_ids), "rationale": "r"}},
        "categoryStatus": {"rating": rating, "direction": "steady",
                           "bottleneck": bottleneck, "reason": "r"},
        "narrative": "n"})


def test_bundle_carries_category_status():
    reg = IndicatorRegistry.load("registry/indicators.json")
    client = RecordedClient([_judgment("Strong")] * 3)
    bundle = judge_findings([_f()], client, reg, "chips.merchant-gpu", samples=3)
    assert bundle.categoryStatus is not None
    assert bundle.categoryStatus.bottleneck == "momentum"


def test_invalid_bottleneck_raises():
    reg = IndicatorRegistry.load("registry/indicators.json")
    client = RecordedClient([_judgment("Strong", bottleneck="notADimension")] * 3)
    with pytest.raises(JudgmentError):
        judge_findings([_f()], client, reg, "chips.merchant-gpu", samples=3)

def test_clean_judgment_produces_gate_valid_bundle():
    # D2(+1,m=2) -> momentum anchor +0.67; "Strong" is consistent.
    reg = IndicatorRegistry.load("registry/indicators.json")
    client = RecordedClient([_judgment("Strong")] * 3)
    bundle = judge_findings([_f()], client, reg, "chips.merchant-gpu", samples=3)
    assert bundle.ratings["momentum"].rating == "Strong"
    assert bundle.anchors["momentum"] == pytest.approx(2 / 3)
    assert bundle.narrative == "n"

def test_anchor_conflict_resamples_then_resolves():
    # negative anchor: apiArr(-1,m=3) -> momentum -1.0. First 3 say "Strong" (conflict),
    # the resample round says "Weak" (consistent) -> resolves on round 2.
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f(indicator="apiArr", pD=-1, mag=3)]
    client = RecordedClient([_judgment("Strong")] * 3 + [_judgment("Weak")] * 3)
    bundle = judge_findings(findings, client, reg, "chips.merchant-gpu", samples=3, resample_budget=2)
    assert bundle.ratings["momentum"].rating == "Weak"

def test_anchor_conflict_exhausts_budget_then_raises():
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f(indicator="apiArr", pD=-1, mag=3)]        # anchor -1.0
    client = RecordedClient([_judgment("Strong")] * 9)       # always conflicts
    with pytest.raises(JudgmentError):
        judge_findings(findings, client, reg, "chips.merchant-gpu", samples=3, resample_budget=2)

def test_gate_backstop_rejects_unknown_finding_id():
    # No anchor conflict (Strong vs +0.67), but cites a finding that does not exist.
    # It also is not in the dimension's indicator group (F35), so it fails at the
    # citation-coherence check before ever reaching the gate backstop; resample_budget=0
    # so the (deliberately small) recorded fixture covers exactly one round.
    reg = IndicatorRegistry.load("registry/indicators.json")
    client = RecordedClient([_judgment("Strong", find_ids=("ghost-1",))] * 3)
    with pytest.raises(JudgmentError):
        judge_findings([_f()], client, reg, "chips.merchant-gpu", samples=3, resample_budget=0)
