from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.judgment.prompt import SYSTEM, build_user_prompt

def _f() -> Finding:
    return Finding(
        id="doc-nvda-1", statement="DC growth flattening", kind="observed", trend="flat",
        why="w", impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="high", basis="b"), asOf="2026-06", indicatorId="D2",
        side="demand", polarityDemand=1, polaritySupply=0, magnitude=2, entity="NVDA",
        observedAt="2026-06", capturedAt="2026-06-12T00:00:00Z")

def test_user_prompt_shows_anchor_sign_and_finding_id():
    reg = IndicatorRegistry.load("registry/indicators.json")
    prompt = build_user_prompt(build_briefing([_f()], reg, "chips.merchant-gpu"))
    assert "doc-nvda-1" in prompt
    assert "momentum: +0.67" in prompt          # demand-track D2(+1,m=2)=0.6667
    assert "<briefing>" in prompt and "</briefing>" in prompt

def test_system_states_injection_boundary_and_rubric():
    assert "untrusted DATA" in SYSTEM
    assert "JUDGMENT bounded by the anchor" in SYSTEM
