# tests/test_report_top_band.py
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence
from gpu_agent.change import (StateVector, AlertState, ChangeReport, HorizonDiff, ItemDelta)
from gpu_agent.report import render_top_band
from gpu_agent import reader


def _conf():
    return Confidence(level="medium", basis="b")


def _sc():
    return Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                     demandSupply=DemandSupply(dmiContribution=0.1, smiContribution=-0.1),
                     narrative="n", confidence=_conf())


def _state(**kw):
    base = dict(asOf="2026-07-08", demand=0.10, supply=-0.10, sdgi=0.20,
                constraintLabel="memory scarcity")
    base.update(kw)
    return StateVector(**base)


def _change(prior_state=None, items=None, prior_asof="2026-07-07"):
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf=prior_asof,
                    items=items or []),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[]),
    ], priors={"yesterday": prior_state, "last week": None, "last month": None})


def test_band_has_title_dot_tiles_constraint():
    prior = _state(asOf="2026-07-07", demand=-0.10, supply=-0.10, sdgi=0.10)
    out = render_top_band(_sc(), _state(),
                          AlertState(color="yellow", priorColor="green", rawColor="yellow"),
                          _change(prior_state=prior))
    lines = out.splitlines()
    assert "MERCHANT GPU" in lines[0] and "2026-07-08" in lines[0]
    assert "YELLOW" in lines[0] and "(was GREEN)" in lines[0]
    assert "Demand: FIRM" in out and "(was SOFTENING)" in out     # banded, moved
    assert "Supply: SOFTENING" in out and "(was SOFTENING)" in out
    assert "Gap:" in out
    assert "Binding constraint: memory scarcity" in out


def test_first_run_variants():
    out = render_top_band(_sc(), _state(constraintLabel=None),
                          AlertState(color="green", priorColor=None, rawColor="green"),
                          _change(prior_state=None, prior_asof=None))
    assert "(first tracked run)" in out
    assert "(no prior)" in out                       # bands.band_with_prior fallback
    assert "Binding constraint" not in out           # None -> line omitted
    assert "nothing to compare yet" in out


def test_since_yesterday_counts_calls():
    items = [ItemDelta(key="thesis:t1", changed=True, today="high/strengthened",
                       direction="up"),
             ItemDelta(key="index:gap", changed=True, today="flat 0.2",
                       prior="flat 0.1", direction="up")]
    out = render_top_band(_sc(), _state(),
                          AlertState(color="green", priorColor="green", rawColor="green"),
                          _change(prior_state=_state(asOf="2026-07-07"), items=items))
    assert "Since yesterday: 2 moved (1 standing call)" in out


def test_unchanged_since_uses_most_recent_date_and_is_order_independent():
    # Two unchanged items with different stability windows: the band must claim the
    # MOST RECENT unchangedSince (a changed-then-reverted key resets its date; claiming
    # the older date overstates stability) — the same rule render_change_lines pins —
    # and the claim must not depend on item order.
    items = [ItemDelta(key="dim:momentum", changed=False, today="Strong/improving",
                       prior="Strong/improving", direction="same",
                       unchangedSince="2026-06-08"),
             ItemDelta(key="index:gap", changed=False, today="flat 0.2",
                       prior="flat 0.2", direction="same",
                       unchangedSince="2026-07-01")]
    alert = AlertState(color="green", priorColor="green", rawColor="green")
    out = render_top_band(_sc(), _state(), alert,
                          _change(prior_state=_state(asOf="2026-07-07"), items=items))
    assert "unchanged since 2026-07-01" in out
    out_rev = render_top_band(_sc(), _state(), alert,
                              _change(prior_state=_state(asOf="2026-07-07"),
                                      items=list(reversed(items))))
    assert out == out_rev


def test_top_band_passes_acronym_lint_and_is_deterministic():
    prior = _state(asOf="2026-07-07")
    args = (_sc(), _state(),
            AlertState(color="orange", priorColor="yellow", rawColor="orange"),
            _change(prior_state=prior))
    a, b = render_top_band(*args), render_top_band(*args)
    assert a == b
    assert reader.lint_acronyms(a) == []
