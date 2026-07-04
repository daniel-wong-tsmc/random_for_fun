from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.judgment.prompt import SYSTEM, build_system, build_user_prompt

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

def test_system_prompt_requests_all_six_and_overall_status():
    low = SYSTEM.lower()
    assert "categorystatus" in low
    assert "bottleneck" in low
    # instructs omission of ungroundable dimensions rather than inventing
    assert "omit" in low


# --- F5: memory injection (additive; None path must stay byte-identical) ---


def test_memory_absent_by_default():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    assert "<memory>" not in build_user_prompt(briefing)


def test_memory_prepended_when_given():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    prompt = build_user_prompt(briefing, memory_text="X")
    assert prompt.startswith("<memory>\nX\n</memory>")


def test_memory_none_is_byte_identical_to_the_default_call():
    reg = IndicatorRegistry.load("registry/indicators.json")
    briefing = build_briefing([_f()], reg, "chips.merchant-gpu")
    assert build_user_prompt(briefing, None) == build_user_prompt(briefing)


def test_system_states_direction_relative_to_memory_when_present():
    assert (
        "When a MEMORY section is present, judge direction (improving|steady|worsening) "
        "relative to that prior state."
    ) in SYSTEM


def test_system_equals_build_system_invariant_still_holds():
    assert SYSTEM == build_system()


def test_system_crux_sentence_demands_consensus_departure():
    # F62 eval follow-up: the judge rubric awards sensitivity-differentiation only when the
    # narrative states where the read departs from consensus; the three-sentence budget must
    # ask for it explicitly or generations reliably omit it (both 2026-07-04 eval attempts).
    flat = " ".join(SYSTEM.split())
    assert (
        "(2) the crux — the one or two questions that decide the next rating change, and "
        "where and why this read departs from the consensus view;"
    ) in flat
    assert "exactly three sentences" in SYSTEM   # budget unchanged — the lint still counts 3
