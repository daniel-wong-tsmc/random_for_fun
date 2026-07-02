"""Wave-2 Lane F — brief/report + price track (F18, F29, F33, F34, F49, F51).

Tests are grouped by task, in plan order. Strict TDD: each task's tests are added and
proven failing before the corresponding implementation change lands.
"""
from __future__ import annotations

from gpu_agent.brief import _traj_arrow, render_demand_supply_board
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Finding, Confidence, Evidence


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
