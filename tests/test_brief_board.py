"""Tests for gpu_agent/brief.py — render_demand_supply_board (the DEMAND | SUPPLY board).

Task 2 of sub-project 4-5: per-category Market-State brief render.
"""
from __future__ import annotations

from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Finding, Confidence, Evidence

from gpu_agent.brief import render_demand_supply_board
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.indicators import IndicatorRegistry


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ds(dmi: float = 0.05, smi: float = 0.02) -> DemandSupply:
    return DemandSupply(dmiContribution=dmi, smiContribution=smi)


def _f(fid: str = "f-001", *, side: str = "demand", indicatorId: str = "D2",
       trend: str = "flat", polDemand: int = 1, polSupply: int = 0,
       magnitude: int = 2, asOf: str = "2026-06", evidence: list | None = None) -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend=trend, why="w",
        impact={"targets": ["t"], "direction": "positive", "mechanism": "m"},
        evidence=evidence or [],
        confidence={"level": "medium", "basis": "b"},
        asOf=asOf, indicatorId=indicatorId, side=side,
        polarityDemand=polDemand, polaritySupply=polSupply,
        magnitude=magnitude, entity="E", observedAt="2026-06",
        capturedAt="2026-06-12T00:00:00Z",
    )


def _sc(as_of: str = "2026-06", findings: list | None = None) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf=as_of,
        findings=findings or [],
        demandSupply=DemandSupply(dmiContribution=0.05, smiContribution=0.02),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_board_groups_by_side():
    sc = _sc(findings=[
        _f("d1", side="demand", indicatorId="rpoBacklog", trend="rising", polDemand=1),
        _f("s1", side="supply", indicatorId="leadTimes", trend="falling", polSupply=1),
    ])
    out = render_demand_supply_board(sc, None)
    assert "DEMAND" in out and "SUPPLY" in out
    assert "rpoBacklog" in out and "leadTimes" in out


def test_board_collapses_to_latest_vintage_per_indicator():
    # two vintages of the same indicator -> ONE row (the latest capturedAt)
    sc = _sc(findings=[
        _f("d-old", side="demand", indicatorId="rpoBacklog", asOf="2026-06", magnitude=1),
        _f("d-new", side="demand", indicatorId="rpoBacklog", asOf="2026-07", magnitude=3),
    ])
    out = render_demand_supply_board(sc, None)
    assert out.count("rpoBacklog") == 1


def test_board_leading_tag_when_horizons_supplied():
    horizons = IndicatorHorizons.load("registry/indicators.json")
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])
    out = render_demand_supply_board(sc, horizons)
    # rpoBacklog is horizon=leading in the registry (4-2)
    assert "leading" in out


def test_board_no_leading_tag_without_horizons():
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])
    out = render_demand_supply_board(sc, None)
    assert "leading" not in out


def test_board_flags_carried_finding():
    # finding.asOf predates the scorecard asOf -> a stale carry-over, worded
    # plainly for the reader (was the internal "⚠carried" jargon).
    sc = _sc(as_of="2026-07", findings=[
        _f("d1", side="demand", indicatorId="rpoBacklog", asOf="2026-05")])
    out = render_demand_supply_board(sc, None)
    assert "⚠ from a prior cycle" in out


def test_board_empty_side_note():
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog")])
    out = render_demand_supply_board(sc, None)
    assert "no supply findings" in out


# ── Task 7 (F67): registry labels + reader-worded tags ───────────────────────

def test_board_rows_use_registry_labels():
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = _sc(as_of="2026-07", findings=[
        _f("d1", side="demand", indicatorId="rpoBacklog", asOf="2026-05",
           evidence=[Evidence(source="Src", url="https://www.ebay.com/x",
                               date="2026-06-30", excerpt="e", tier="secondary")]),
    ])
    out = render_demand_supply_board(sc, None, registry=reg)
    assert "Backlog" in out or "Guidance" in out    # labels from registry
    assert "rpoBacklog" not in out
    assert " D2 " not in out
    assert "⚠ one source" in out
    assert "single-source" not in out
    assert "⚠ from a prior cycle" in out
    assert "⚠carried" not in out


def test_board_rows_id_fallback_without_registry():
    # Legacy callers passing no registry keep today's id-rendering behavior —
    # indicator_label(id, None) falls back to the raw id.
    sc = _sc(findings=[_f("d1", side="demand", indicatorId="rpoBacklog")])
    out = render_demand_supply_board(sc, None)
    assert "rpoBacklog" in out
