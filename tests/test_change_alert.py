# tests/test_change_alert.py
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import (StateVector, AlertState, _raw_alert, _fold_displayed,
                              alert_state, build_state)


def _conf():
    return Confidence(level="medium", basis="b")


def _st(demand=0.10, supply=0.10, sdgi=0.10, constraint=None, as_of="2026-07-08"):
    return StateVector(asOf=as_of, demand=demand, supply=supply, sdgi=sdgi,
                       constraintLabel=constraint)


def _entry(eid="t1", conviction="high", status="registered", verdict="strengthened",
           direction=1, changed="2026-07-05"):
    return ThesisEntry(id=eid, title="T", statement="s", lens="demand", status=status,
                       conviction=conviction, lastVerdict=verdict, lastDirection=direction,
                       streak=2, mechanism="m", falsifiableTrigger="t", sensitivity="s",
                       createdAsOf="2026-06", lastChangedAsOf=changed,
                       lastJudgedAsOf=changed)


def test_green_when_nothing_moved():
    color, trig = _raw_alert(_st(), _st(as_of="2026-07-01"), "2026-07-01", None)
    assert color == "green" and trig == []


def test_yellow_on_gap_band_change():
    # firm (0.10) -> accelerating (0.35) crosses a band edge
    color, trig = _raw_alert(_st(sdgi=0.35), _st(sdgi=0.10, as_of="2026-07-01"),
                             "2026-07-01", None)
    assert color == "yellow" and "gap-band-changed" in trig


def test_yellow_on_constraint_rotation():
    color, trig = _raw_alert(_st(constraint="memory scarcity"),
                             _st(constraint="export enforcement", as_of="2026-07-01"),
                             "2026-07-01", None)
    assert color == "yellow" and "constraint-rotated" in trig


def test_yellow_on_high_call_moved():
    book = ThesisBook(categoryId="c", entries=[_entry(changed="2026-07-05")])
    color, trig = _raw_alert(_st(), _st(as_of="2026-07-01"), "2026-07-01", book)
    assert color == "yellow" and "high-call-moved" in trig


def test_reaffirmed_high_call_in_window_stays_green():
    # USER-APPROVED 2026-07-12 (spec §4 governs): a plain reaffirmation re-stamps
    # lastChangedAsOf without a real move — it must not fire high-call-moved/calls-co-move.
    book = ThesisBook(categoryId="c", entries=[
        _entry(eid="t1", verdict="reaffirmed", direction=0, changed="2026-07-05"),
        _entry(eid="t2", verdict="reaffirmed", direction=0, changed="2026-07-06")])
    color, trig = _raw_alert(_st(), _st(as_of="2026-07-01"), "2026-07-01", book)
    assert color == "green"
    assert "high-call-moved" not in trig and "calls-co-move" not in trig


def test_two_yellow_rules_escalate_orange():
    color, trig = _raw_alert(_st(sdgi=0.35, constraint="memory"),
                             _st(sdgi=0.10, constraint="export", as_of="2026-07-01"),
                             "2026-07-01", None)
    assert color == "orange"
    assert {"gap-band-changed", "constraint-rotated"} <= set(trig)


def test_orange_on_high_break():
    book = ThesisBook(categoryId="c", entries=[
        _entry(status="retired", verdict="broken", changed="2026-07-06")])
    color, trig = _raw_alert(_st(), _st(as_of="2026-07-01"), "2026-07-01", book)
    assert color == "orange" and "high-call-broke" in trig


def test_orange_on_asymmetric_demand_reversal():
    # demand band worsens (firm 0.10 -> softening -0.10) AND sdgi slides toward glut
    # WITHIN the same band (0.28 -> 0.10, both "firm") so no other rule fires.
    color, trig = _raw_alert(_st(demand=-0.10, sdgi=0.10),
                             _st(demand=0.10, sdgi=0.28, as_of="2026-07-01"),
                             "2026-07-01", None)
    assert color == "orange" and trig == ["demand-reversal"]


def test_red_on_break_plus_gap_band_flip():
    book = ThesisBook(categoryId="c", entries=[
        _entry(status="retired", verdict="broken", changed="2026-07-06")])
    color, trig = _raw_alert(_st(sdgi=-0.35), _st(sdgi=0.10, as_of="2026-07-01"),
                             "2026-07-01", book)
    assert color == "red"


def test_no_prior_run_is_green():
    color, trig = _raw_alert(_st(), None, None, None)
    assert color == "green"


def test_fold_immediate_escalation_and_two_calm_step_down():
    assert _fold_displayed(["green", "orange"]) == ["green", "orange"]      # escalate now
    assert _fold_displayed(["orange", "green"]) == ["orange", "orange"]     # 1st calm holds
    assert _fold_displayed(["orange", "green", "green"]) == ["orange", "orange", "green"]
    assert _fold_displayed(["orange", "green", "yellow"]) == ["orange", "orange", "yellow"]
    assert _fold_displayed(["yellow", "red"]) == ["yellow", "red"]


def test_alert_state_walk_deterministic(tmp_path):
    def _write(as_of, constraint):
        cat = tmp_path / "chips.merchant-gpu"
        cat.mkdir(parents=True, exist_ok=True)
        sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                       demandSupply=DemandSupply(dmiContribution=0.1, smiContribution=0.1),
                       narrative="n", confidence=_conf())
        (cat / f"{as_of}-v1.json").write_text(sc.model_dump_json(), "utf-8")
        return sc

    _write("2026-07-01", None)
    _write("2026-07-07", None)
    today = _write("2026-07-08", None)
    a = alert_state(tmp_path, today)
    b = alert_state(tmp_path, today)
    assert a == b
    assert a.color == "green" and a.priorColor == "green" and a.rawColor == "green"
