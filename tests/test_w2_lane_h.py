"""Wave-2 Lane H — generalization.

F26: extraction/judgment personas are parameterized (GPU is a default, not a
hardcode). F27: models.frontier-closed becomes actually runnable.
"""
from __future__ import annotations

import json

import pytest

from gpu_agent.extraction import prompt as extraction_prompt
from gpu_agent.judgment import prompt as judgment_prompt
from gpu_agent.judgment.judge import judge_findings
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence, Impact
from gpu_agent.registry.indicators import IndicatorRegistry

REG = "registry/indicators.json"


# ── F26: SYSTEM byte-identity pins (CRITICAL compatibility rule) ──────────────

def test_extraction_system_is_byte_identical_to_build_system_default():
    assert extraction_prompt.SYSTEM == extraction_prompt.build_system()


def test_judgment_system_is_byte_identical_to_build_system_default():
    assert judgment_prompt.SYSTEM == judgment_prompt.build_system()


# ── F26: build_system is additive parameterization ─────────────────────────

def test_extraction_build_system_swaps_persona():
    s = extraction_prompt.build_system("frontier AI model market")
    assert "frontier AI model market" in s
    assert "GPU" not in s


def test_judgment_build_system_swaps_persona():
    s = judgment_prompt.build_system("frontier AI model market")
    assert "frontier AI model market" in s
    assert "GPU" not in s


# ── F26: assignment.py additive field ───────────────────────────────────────

def test_old_assignment_fixture_still_loads_with_persona_label_none():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    assert a.personaLabel is None


# ── F26: judge_findings persona pass-through ────────────────────────────────

class _CapturingClient:
    """Test double recording the `system` string of every complete_json call."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.seen_systems: list[str] = []

    def complete_json(self, prompt, system, schema, model):
        self.seen_systems.append(system)
        data = json.loads(self._responses.pop(0))
        return schema.model_validate(data)


def _judgment_json(rating="Strong", bottleneck="momentum") -> str:
    return json.dumps({
        "dimensions": {"momentum": {
            "rating": rating, "direction": "steady",
            "findingIds": ["real-1"], "rationale": "r"}},
        "categoryStatus": {"rating": rating, "direction": "steady",
                           "bottleneck": bottleneck, "reason": "r"},
        "narrative": "n"})


def _finding() -> Finding:
    # D2(+1, m=2) -> momentum anchor +0.67; "Strong" is anchor-consistent.
    return Finding(
        id="real-1", statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        evidence=[{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e",
                   "tier": "primary"}],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="E", observedAt="2026-06-01", capturedAt="2026-06-12T00:00:00Z")


def test_judge_findings_default_path_is_byte_identical_prompt():
    reg = IndicatorRegistry.load(REG)
    client = _CapturingClient([_judgment_json()] * 3)
    judge_findings([_finding()], client, reg, "chips.merchant-gpu", samples=3)
    assert client.seen_systems
    assert all(s == judgment_prompt.SYSTEM for s in client.seen_systems)


def test_judge_findings_persona_param_swaps_system():
    reg = IndicatorRegistry.load(REG)
    client = _CapturingClient([_judgment_json()] * 3)
    judge_findings([_finding()], client, reg, "chips.merchant-gpu", samples=3,
                   persona="frontier AI model market")
    expected = judgment_prompt.build_system("frontier AI model market")
    assert client.seen_systems
    assert all(s == expected for s in client.seen_systems)
    assert all("GPU" not in s for s in client.seen_systems)
