"""F79 Stage 4 — the σ-band alert engine (raw_alert_v2), shadow-only beside the v1
ladder. The v1 ladder (_raw_alert / alert_state) keeps rendering until the G4 cutover:
this file also pins that the v1 functions are untouched by Stage 4.

v2 trigger set (pre-registered parameters, disclosed at G2):
- gap-sigma-crossed (yellow): the v2 SDGI crossed a σ-band edge between the prior and
  current run. Edges around the rolling mean of PRIOR history, ASYMMETRIC (doc-settled):
  shortage side mean+1.0σ / mean+2.0σ; reversal(glut) side mean−0.75σ / mean−1.5σ.
- gap-extreme (yellow): the level sits beyond an outer edge.
- delta-sdgi-momentum (yellow): two consecutive same-direction moves, cum > 0.5σ —
  fires even at green (doc-settled).
- demand-reversal (orange escalator, asymmetric): v2 DMI fell > 0.75σ(dmi history)
  since the prior run AND the gap moved toward glut.
- thesis/constraint rules ride unchanged from v1 (the event channel): high-call-moved,
  calls-co-move, constraint-rotated (yellow); high-call-broke.
Ladder: RED = high-call-broke AND gap-sigma-crossed; ORANGE = high-call-broke OR
demand-reversal OR ≥2 yellow hits; YELLOW = any yellow hit; else GREEN.

Fixture H: zeros with one ±1 spike pair -> mean 0, sample σ = sqrt(2/7) ≈ 0.5345.
Edges over H: yellow_up ≈ +0.535, outer_up ≈ +1.069, yellow_down ≈ −0.401,
outer_down ≈ −0.802.
"""
from __future__ import annotations
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import raw_alert_v2, _raw_alert, _fold_displayed, fold_displayed


def _entry(eid="t1", conviction="high", status="registered", verdict="strengthened",
           direction=1, changed="2026-07-05"):
    return ThesisEntry(id=eid, title="T", statement="s", lens="demand", status=status,
                       conviction=conviction, lastVerdict=verdict, lastDirection=direction,
                       streak=2, mechanism="m", falsifiableTrigger="t", sensitivity="s",
                       createdAsOf="2026-06", lastChangedAsOf=changed,
                       lastJudgedAsOf=changed)


H = [0.0, 0.0, 1.0, -1.0, 0.0, 0.0, 0.0, 0.0]   # mean 0, σ ≈ 0.5345 (see docstring)


def test_green_when_quiet():
    color, trig = raw_alert_v2(H + [0.0], H + [0.0])
    assert color == "green" and trig == []


def test_yellow_on_shortage_side_sigma_cross():
    # 0.0 -> 0.7 crosses yellow_up ≈ 0.535 (single rule -> yellow)
    color, trig = raw_alert_v2(H + [0.7], H + [0.0])
    assert color == "yellow" and trig == ["gap-sigma-crossed"]


def test_asymmetry_reversal_side_trips_earlier():
    # |0.45| is INSIDE the shortage yellow edge (+0.535) but BEYOND the reversal
    # yellow edge (−0.401): +0.45 stays green, −0.45 goes yellow.
    up_color, up_trig = raw_alert_v2(H + [0.45], H + [0.0])
    down_color, down_trig = raw_alert_v2(H + [-0.45], H + [0.0])
    assert up_color == "green" and up_trig == []
    assert down_color == "yellow" and "gap-sigma-crossed" in down_trig


def test_delta_sdgi_momentum_fires_even_at_green_level():
    # two consecutive +0.15 moves (cum 0.30 > 0.5σ ≈ 0.24) with the level still inside
    # every band edge -> the momentum rule alone -> yellow
    color, trig = raw_alert_v2(H + [0.15, 0.3], H + [0.0, 0.0])
    assert color == "yellow" and trig == ["delta-sdgi-momentum"]


def test_demand_reversal_alone_escalates_to_orange():
    # DMI falls 0.8 (> 0.75σ_d ≈ 0.40) while the gap moves toward glut
    color, trig = raw_alert_v2(H + [0.2, 0.0], H + [0.5, -0.3])
    assert color == "orange" and trig == ["demand-reversal"]


def test_equal_shortage_side_move_does_not_escalate():
    # the mirror-image move (DMI RISES 0.8, gap toward shortage) must NOT fire
    # demand-reversal — the asymmetric doctrine protects the downside only
    color, trig = raw_alert_v2(H + [0.0, 0.2], H + [-0.3, 0.5])
    assert "demand-reversal" not in trig
    assert color == "green"


def test_two_yellow_rules_make_orange():
    # gap crosses the shortage edge AND the constraint rotated
    color, trig = raw_alert_v2(H + [0.7], H + [0.0],
                               constraint_now="HBM", constraint_prior="CoWoS")
    assert color == "orange"
    assert "gap-sigma-crossed" in trig and "constraint-rotated" in trig


def test_red_reserved_for_break_plus_sigma_cross():
    book = ThesisBook(categoryId="c", entries=[
        _entry(status="retired", verdict="broken", direction=-1, changed="2026-07-05")])
    color, trig = raw_alert_v2(H + [0.7], H + [0.0],
                               book=book, prior7_asof="2026-07-01", cur_asof="2026-07-08")
    assert color == "red"
    assert "high-call-broke" in trig and "gap-sigma-crossed" in trig


def test_high_call_moved_rides_from_v1_event_channel():
    book = ThesisBook(categoryId="c", entries=[_entry(changed="2026-07-05")])
    color, trig = raw_alert_v2(H + [0.0], H + [0.0],
                               book=book, prior7_asof="2026-07-01", cur_asof="2026-07-08")
    assert color == "yellow" and trig == ["high-call-moved"]


def test_gap_extreme_beyond_outer_edge():
    # a level parked beyond the outer edge keeps a standing yellow even without a NEW
    # crossing. Prior history H+[3.0]: mean 0.333, σ ≈ 1.118 -> outer_up ≈ 2.569; both
    # 3.0 and 2.95 sit beyond it (no crossing), and the -0.05 down-tick kills the
    # momentum rule (direction flip) -> gap-extreme alone.
    color, trig = raw_alert_v2(H + [3.0, 2.95], H + [0.0, 0.0])
    assert color == "yellow" and trig == ["gap-extreme"]


def test_short_history_never_fires_sigma_rules():
    color, trig = raw_alert_v2([0.0, 5.0], [0.0, -5.0])
    assert color == "green" and trig == []


def test_fold_semantics_shared_with_v1():
    # anti-flapping is the SAME fold: escalation immediate, de-escalation after 2 calm runs
    assert fold_displayed(["green", "orange", "green", "green"]) == \
        ["green", "orange", "orange", "green"]
    assert fold_displayed(["green", "orange", "green", "green"]) == \
        _fold_displayed(["green", "orange", "green", "green"])


def test_v1_ladder_untouched_by_stage4():
    """The v1 path still renders until G4 — same signature, same quiet-green behavior."""
    from gpu_agent.change import StateVector
    cur = StateVector(asOf="2026-07-08", demand=0.1, supply=0.1, sdgi=0.1)
    prior = StateVector(asOf="2026-07-01", demand=0.1, supply=0.1, sdgi=0.1)
    color, trig = _raw_alert(cur, prior, "2026-07-01", None)
    assert color == "green" and trig == []
