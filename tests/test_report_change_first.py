# tests/test_report_change_first.py
from __future__ import annotations
from gpu_agent.report import render_report, render_change_lines
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.scorecard import (Scorecard, DemandSupply, DimensionRating,
                                        CategoryStatus)
from gpu_agent.schema.finding import Confidence
from gpu_agent.change import build_state, StateVector, ChangeReport, HorizonDiff, ItemDelta
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _conf():
    return Confidence(level="medium", basis="b")


def _sc():
    return Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                     dimensionRatings={"momentum": DimensionRating(
                         rating="Very strong", direction="improving", confidence=_conf(),
                         findingIds=[], rationale="r")},
                     demandSupply=DemandSupply(dmiContribution=0.57, smiContribution=0.29),
                     narrative="n", confidence=_conf(),
                     categoryStatus=CategoryStatus(rating="Strong", direction="improving",
                                                   bottleneck="packaging", reason="demand outruns ramp"))


def _change():
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="dim:momentum", changed=True, today="Very strong/improving",
                      prior="Strong/steady", direction="up")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[])])


def test_change_none_is_unchanged_behavior():
    # A caller that passes no change report gets exactly today's report (no WHAT CHANGED lead).
    out = render_report(_sc(), None, _reg(), render_ts="fixed")
    assert "WHAT CHANGED" not in out
    assert "STATE OF THE MARKET" in out


def test_change_first_leads_with_what_changed_then_glance():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    assert out.index("WHAT CHANGED") < out.index("QUICK GLANCE") < out.index(reader.APPENDIX_DIVIDER)
    # change-first lead sits above STATE OF THE MARKET
    assert out.index("WHAT CHANGED") < out.index("STATE OF THE MARKET")


def test_top_band_leads_when_alert_supplied():
    # AMENDED 2026-07-11: TOP BAND above WHAT CHANGED; absent without an AlertState.
    from gpu_agent.change import AlertState
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st,
                        alert=AlertState(color="yellow", priorColor="green", rawColor="yellow"))
    assert out.index("YELLOW") < out.index("WHAT CHANGED")
    assert "(was GREEN)" in out
    no_alert = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    assert "(was GREEN)" not in no_alert


def test_above_fold_passes_acronym_lint():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    above = out.split(reader.APPENDIX_DIVIDER)[0]
    assert reader.lint_acronyms(above) == []


def test_above_fold_within_length_budget():
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    above = out.split(reader.APPENDIX_DIVIDER)[0]
    from gpu_agent.report import _ABOVE_FOLD_BUDGET
    assert len(above.splitlines()) <= _ABOVE_FOLD_BUDGET


def test_change_first_is_byte_deterministic():
    st = build_state(_sc())
    a = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    b = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st)
    assert a == b


def test_change_first_appendix_has_full_the_calls_block():
    # USER-APPROVED ADDITION (2026-07-12, interactive): the ranked-calls fold line above
    # the fold promises "full detail in THE CALLS appendix" — that promise is only true
    # if the appendix actually carries a THE CALLS section. On the change-first path
    # only, render_the_calls (the un-capped, un-folded book) leads the appendix, right
    # after reader.APPENDIX_DIVIDER, so every folded entry's full three-line detail is
    # still reachable one section down.
    from gpu_agent.thesis import ThesisBook, ThesisEntry

    def _entry(eid, conviction, verdict="reaffirmed"):
        return ThesisEntry(id=eid, title=f"call {eid}", statement="s", lens="demand",
                            status="registered", conviction=conviction,
                            lastVerdict=verdict, lastDirection=0, streak=2,
                            mechanism="m", falsifiableTrigger="t", sensitivity="s",
                            createdAsOf="2026-06", lastChangedAsOf="2026-07-08",
                            lastJudgedAsOf="2026-07-08")

    # More standing calls than top_k (default 5) so the above-the-fold block folds the
    # tail; one entry's verdict differs from "reaffirmed" so brief.render_the_calls
    # renders every entry's full three-line detail rather than its own "nothing
    # changed" one-liner shortcut.
    book = ThesisBook(categoryId="chips.merchant-gpu", entries=[
        _entry("a", "high", verdict="strengthened"), _entry("b", "medium"),
        _entry("c", "low"), _entry("d", "medium"), _entry("e", "low"), _entry("f", "low")])
    st = build_state(_sc())
    out = render_report(_sc(), None, _reg(), render_ts="fixed", change=_change(), state=st,
                        thesis_book=book, top_k=5)

    above, appendix_part = out.split(reader.APPENDIX_DIVIDER, 1)
    assert "more calls folded" in above
    assert "full detail in THE CALLS appendix" in above

    # The appendix's FIRST section (right after the divider) is the full THE CALLS
    # block, and it carries every entry's full detail, not folded.
    assert appendix_part.strip().startswith("THE CALLS")
    for eid in ("a", "b", "c", "d", "e", "f"):
        assert f"call {eid}" in appendix_part
    assert appendix_part.count("breaks if:") == 6
