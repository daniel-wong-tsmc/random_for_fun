"""Wave-2 Lane F — brief/report + price track (F18, F29, F33, F34, F49, F51).

Tests are grouped by task, in plan order. Strict TDD: each task's tests are added and
proven failing before the corresponding implementation change lands.
"""
from __future__ import annotations

import math

from gpu_agent.brief import _traj_arrow, render_demand_supply_board, render_storylines
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence
from gpu_agent.wiki.movement import MarketMovement, StorylineRow
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import _score_move, DEFAULT_LINT_CONFIG


# ── Task 1 (F18): trajectory arrows match TOKENS, not substrings ──────────────

def test_traj_arrow_supply_glut_worsening_is_down_not_up():
    # The review's bug: "up" is a substring of "supply", so naive substring matching
    # rendered UP (▲) for a sentence that is actually about a glut worsening (▼).
    assert _traj_arrow("supply glut worsening") == "▼"


def test_traj_arrow_shutdown_risk_is_unknown_not_down():
    # "down" is a substring of "shutdown" but not a standalone token.
    assert _traj_arrow("shutdown risk") == "·"


def test_traj_arrow_on_track_is_flat():
    assert _traj_arrow("on-track") == "="


def test_traj_arrow_tight_but_improving_is_up_precedence():
    # "tight" (FLAT) and "improving" (UP) both present — UP wins precedence.
    assert _traj_arrow("tight but improving") == "▲"


# ── Task 2 (F29): single-source ⚠ flag in the brief board ─────────────────────

def _ev(url, source="Src", date="2026-06-30", tier="secondary"):
    return Evidence(source=source, url=url, date=date, excerpt="e", tier=tier)


def _finding(fid="f-001", *, side="demand", indicatorId="D2", evidence=None,
             asOf="2026-06", magnitude=2) -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact={"targets": ["t"], "direction": "positive", "mechanism": "m"},
        evidence=evidence or [],
        confidence={"level": "medium", "basis": "b"},
        asOf=asOf, indicatorId=indicatorId, side=side,
        polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity="E", observedAt="2026-06",
        capturedAt="2026-06-12T00:00:00Z",
    )


def _sc(as_of="2026-06", findings=None) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf=as_of,
        findings=findings or [],
        demandSupply=DemandSupply(dmiContribution=0.05, smiContribution=0.02),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
    )


def test_board_single_evidence_finding_is_tagged():
    sc = _sc(findings=[_finding(evidence=[_ev("https://www.ebay.com/x")])])
    out = render_demand_supply_board(sc, None)
    assert "⚠single-source" in out


def test_board_two_different_domains_not_tagged():
    sc = _sc(findings=[_finding(evidence=[
        _ev("https://www.ebay.com/x"), _ev("https://www.lambda.ai/y"),
    ])])
    out = render_demand_supply_board(sc, None)
    assert "⚠single-source" not in out


def test_board_two_same_domain_evidence_is_tagged():
    sc = _sc(findings=[_finding(evidence=[
        _ev("https://www.ebay.com/x"), _ev("https://www.ebay.com/y"),
    ])])
    out = render_demand_supply_board(sc, None)
    assert "⚠single-source" in out


# ── Task 3 (F33): bound STORYLINES growth ──────────────────────────────────────

def _story(title, salience, *, provisional=False):
    return StorylineRow(title=title, state="on-track", trajectory="steady",
                        lastUpdatedAsOf="2026-07", salience=salience, provisional=provisional)


def test_storylines_caps_provisional_group_at_8_with_fold_count():
    provisional = [_story(f"thread-{i}", salience=1.0 - i * 0.01, provisional=True)
                   for i in range(10)]
    mv = MarketMovement(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=provisional)
    out = render_storylines(mv)
    lines = out.splitlines()
    bullet_lines = [ln for ln in lines if ln.strip().startswith("•")]
    assert len(bullet_lines) == 8
    assert "    (+2 more tracked — see wiki-lint)" in out


def test_storylines_8_or_fewer_no_fold_line():
    provisional = [_story(f"thread-{i}", salience=1.0 - i * 0.01, provisional=True)
                   for i in range(8)]
    mv = MarketMovement(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=provisional)
    out = render_storylines(mv)
    assert "more tracked" not in out


def test_storylines_byte_deterministic():
    provisional = [_story(f"thread-{i}", salience=1.0 - i * 0.01, provisional=True)
                   for i in range(10)]
    mv = MarketMovement(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=provisional)
    assert render_storylines(mv) == render_storylines(mv)


# ── Task 4 (F34): recalibrate the materiality fold ─────────────────────────────

def _wiki_store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _lint_finding(fid, entity, indicatorId, magnitude=2, tier="secondary"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date="2026-06", excerpt="e", tier=tier)],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def test_materiality_new_nonscoring_mag2_is_material(tmp_path):
    """A brand-new secondary thread whose only observation is a non-scoring (overlay)
    finding of magnitude 2 must now count as ACTIVITY, not be structurally folded.
    gpuSpotPrice: scoring=False, side=price, daily/coincident (no leading boost).
    base = w_new 0.5 + w_ind 0.3 * ind_sum 2 = 1.1
    score = 1.1 * tier_secondary 0.6 * recency_full 1.0 * (1 + boost 0) * salience_floor 0.5 = 0.33
    """
    reg, hz = _reg_hz()
    ws = _wiki_store(tmp_path)
    route_findings(ws, [_lint_finding("f-1", "NVDA", "gpuSpotPrice", magnitude=2)], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=True,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.indicatorMoves[0].scoring is False   # still recorded as non-scoring for display
    assert math.isclose(mv.score, (0.5 + 0.3 * 2) * 0.6 * 1.0 * 1.0 * 0.5)
    assert math.isclose(mv.score, 0.33)
    assert mv.score >= DEFAULT_LINT_CONFIG.material_threshold   # material


def test_materiality_new_price_only_mag1_stays_folded(tmp_path):
    """A brand-new secondary thread whose only observation is a D6 (price, non-scoring)
    magnitude-1 finding stays below threshold — price noise is quiet, but it is COUNTED
    (not excluded), unlike before F34.
    base = w_new 0.5 + w_ind 0.3 * ind_sum 1 = 0.8
    score = 0.8 * tier_secondary 0.6 * recency_full 1.0 * (1 + boost 0) * salience_floor 0.5 = 0.24
    """
    reg, hz = _reg_hz()
    ws = _wiki_store(tmp_path)
    route_findings(ws, [_lint_finding("f-1", "NVDA", "D6", magnitude=1)], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=True,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.indicatorMoves[0].scoring is False
    assert math.isclose(mv.score, (0.5 + 0.3 * 1) * 0.6 * 1.0 * 1.0 * 0.5)
    assert math.isclose(mv.score, 0.24)
    assert mv.score < DEFAULT_LINT_CONFIG.material_threshold   # folded
