import math
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import _score_move, score_moves, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId, magnitude=2, tier="secondary"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date="2026-06", excerpt="e", tier=tier)],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def test_score_new_thread_nonscoring(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # gpuSpotPrice: scoring=False (price overlay), daily/coincident (no leading boost)
    route_findings(ws, [_f("f-1", "NVDA", "gpuSpotPrice")], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=True,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.newThread is True
    assert mv.factors.indicatorMoves[0].scoring is False  # overlay excluded from the indicator factor
    assert mv.tierMult == 0.6 and mv.recencyMult == 1.0   # secondary tier, observed this cycle
    # base = w_new 0.5 (no scoring indicator) ; *0.6 *1.0 *(1+0) *max(0.5,0)=0.5
    assert math.isclose(mv.score, 0.5 * 0.6 * 1.0 * 1.0 * 0.5)


def test_score_scoring_indicator_and_leading_boost(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # rpoBacklog: scoring=True (demand), quarterly/leading, magnitude 3, primary evidence
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog", magnitude=3, tier="primary")], as_of="2026-06")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=False,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.indicatorMoves[0].scoring is True
    assert mv.factors.indicatorMoves[0].magnitude == 3
    # base = w_ind 0.3 * 3 = 0.9 ; tier primary 1.0 ; recency 1.0 ; leading boost (1+0.5) ; salience 0.5
    assert math.isclose(mv.score, 0.9 * 1.0 * 1.0 * 1.5 * 0.5)


def test_score_state_change_factor(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog")], as_of="2026-05")  # findings in a PRIOR cycle
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of="2026-05", is_new=False,
                     state_transition={"from": "steady", "to": "slipping"}, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.stateTransition == {"from": "steady", "to": "slipping"}
    assert mv.factors.newThread is False
    assert mv.recencyMult == 0.7   # no finding observed in THIS cycle (window 2026-05<asOf<=2026-06 is empty)
    # base = w_state 0.6 ; tier secondary 0.6 (no this-cycle findings) ; recency 0.7 ; no boost ; salience 0.5
    assert math.isclose(mv.score, 0.6 * 0.6 * 0.7 * 1.0 * 0.5)


def test_score_contradiction_highest(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog")], as_of="2026-05")
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of="2026-05", is_new=False,
                     state_transition=None, contradiction_note="guidance cut",
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    assert mv.factors.contradiction is True and mv.factors.contradictionNote == "guidance cut"
    # base = w_contra 1.0 ; tier secondary 0.6 ; recency 0.7 ; salience 0.5
    assert math.isclose(mv.score, 1.0 * 0.6 * 0.7 * 1.0 * 0.5)


def test_score_salience_weight_lifts_with_brain_salience(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", "rpoBacklog", magnitude=3, tier="primary")], as_of="2026-06")
    ws.record_state("entity:nvda", as_of="2026-06", state="hot", trajectory="up", salience=0.9)
    mv = _score_move(ws, "entity:nvda", as_of="2026-06", prev_as_of=None, is_new=False,
                     state_transition=None, contradiction_note=None,
                     registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    # salience_weight = max(0.5, 0.9) = 0.9 ; base 0.9 ; primary 1.0 ; recency 1.0 ; leading 1.5
    assert math.isclose(mv.score, 0.9 * 1.0 * 1.0 * 1.5 * 0.9)
    assert math.isclose(mv.effectiveSalience, 0.9)  # fresh move (quiet_age 0) -> effective == intrinsic


def test_score_moves_threshold_split_and_sorted(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # NVDA: a scoring leading magnitude-3 finding -> high score (material).
    # AMD: a non-scoring overlay finding -> low score (dropped under threshold 0.3).
    route_findings(ws, [_f("f-nv", "NVDA", "rpoBacklog", magnitude=3, tier="primary"),
                        _f("f-amd", "AMD", "gpuSpotPrice")], as_of="2026-06")
    diff = ws.diff("2026-06", "")
    material, dropped = score_moves(ws, diff, {}, as_of="2026-06", prev_as_of=None,
                                    registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    mat_ids = [m.pageId for m in material]
    drop_ids = [m.pageId for m in dropped]
    assert "entity:nvda" in mat_ids and "entity:amd" in drop_ids
    assert material == sorted(material, key=lambda m: m.score, reverse=True)
