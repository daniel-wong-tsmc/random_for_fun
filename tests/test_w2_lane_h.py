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
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.pipeline import build_scorecard
from gpu_agent.manifest import load_manifest
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan

REG = "registry/indicators.json"
TAX = "docs/taxonomy.json"
FRONTIER_CATEGORY = "models.frontier-closed"
FRONTIER_ASSIGNMENT = "fixtures/asg.models.frontier-closed.json"
FRONTIER_MANIFEST = "manifests/models.frontier-closed.json"


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


# ── F27: models.frontier-closed is actually runnable ───────────────────────

def test_frontier_manifest_indicators_resolve_and_are_horizon_tagged():
    reg = IndicatorRegistry.load(REG)
    horizons = IndicatorHorizons.load(REG)
    manifest = load_manifest(FRONTIER_MANIFEST)
    assert manifest.categoryId == FRONTIER_CATEGORY
    assert manifest.expectedIndicators
    for ind in manifest.expectedIndicators:
        spec = reg.resolve(ind.indicatorId, manifest.categoryId)   # raises if unresolved
        assert spec.scoring
        assert horizons.get(ind.indicatorId) is not None           # cadenceHorizon-tagged


def test_frontier_assignment_validates_clean_with_real_weights_and_persona():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    a = load_assignment(FRONTIER_ASSIGNMENT)
    assert validate_assignment(a, reg, tax) == []
    assert a.personaLabel == "frontier AI model market"
    assert a.weights == {
        "apiArr": 0.2, "releaseCadence": 0.1, "market-share-pct": 0.1, "grossMargin": 0.1}


def test_frontier_category_cycle_plan_is_ready():
    tax = Taxonomy.load(TAX)
    provider = AssignmentProvider()   # default root "fixtures"
    plan = build_cycle_plan(f"category:{FRONTIER_CATEGORY}", tax, provider)
    assert len(plan.entries) == 1
    assert plan.entries[0].category_id == FRONTIER_CATEGORY
    assert plan.entries[0].status == "ready"


def _frontier_finding(fid, indicator_id, magnitude, entity="OpenAI") -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend="rising", why="w",
        impact=Impact(targets=[FRONTIER_CATEGORY], direction="positive", mechanism="m"),
        evidence=[{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e",
                   "tier": "primary"}],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicator_id, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06-01",
        capturedAt="2026-06-25T00:00:00Z")


def test_frontier_findings_yield_nonzero_index_through_gate():
    reg = IndicatorRegistry.load(REG)
    a = load_assignment(FRONTIER_ASSIGNMENT)
    findings = [
        _frontier_finding("fx-1", "apiArr", 3),
        _frontier_finding("fx-2", "releaseCadence", 2),
    ]
    briefing = build_briefing(findings, reg, a.category)
    horizons = IndicatorHorizons.load(REG)
    sc = build_scorecard(findings, {}, briefing.anchors, a, "n",
                         Confidence(level="medium", basis="b"), reg, horizons=horizons)
    # hand-computed: apiArr(+1,m=3) w=0.2 -> 0.2*1*3/3=0.2000
    #              + releaseCadence(+1,m=2) w=0.1 -> 0.1*1*2/3=0.0667  => dmi=0.2667
    expected_dmi = 0.2 * 1 * 3 / 3 + 0.1 * 1 * 2 / 3
    assert sc.demandSupply.dmiContribution == pytest.approx(expected_dmi)
    assert sc.demandSupply.dmiContribution != 0.0   # closes the backlog's "empty weights (zero indices)"
    assert sc.indices is not None
    assert sc.indices.momentum.dmiContribution == pytest.approx(expected_dmi)
