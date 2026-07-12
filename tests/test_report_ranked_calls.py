from __future__ import annotations
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_ranked_calls
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _sc():
    return Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                     demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                     narrative="n", confidence=Confidence(level="medium", basis="b"))


def _entry(eid, conviction, moved_dir=None, **kw):
    f = dict(id=eid, title=f"call {eid}", statement="s", lens="demand",
             status="registered", conviction=conviction, lastVerdict="reaffirmed",
             lastDirection=0, streak=2, mechanism="m", falsifiableTrigger="t",
             sensitivity="s", createdAsOf="2026-06", lastChangedAsOf="2026-07-08",
             lastJudgedAsOf="2026-07-08")
    f.update(kw)
    return ThesisEntry(**f)


def _change(moved_ids):
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07",
                    items=[ItemDelta(key=f"thesis:{i}", changed=True, direction="up") for i in moved_ids])])


def test_moved_high_conviction_leads_and_tail_folds():
    book = ThesisBook(categoryId="c", entries=[
        _entry("a", "low"), _entry("b", "high"), _entry("c", "medium"),
        _entry("d", "low"), _entry("e", "medium"), _entry("f", "low")])
    out = render_ranked_calls(book, _sc(), _change(moved_ids=["d"]), registry=_reg(), top_k=3)
    # moved 'd' (even at low conviction) ranks into the detailed top; 'b' (high) too.
    assert out.index("call d") < out.index("call f")
    assert out.index("call b") < out.index("call f")
    # tail compressed to one line each + explicit fold count
    assert "more calls folded" in out


def test_all_within_top_k_no_fold_line():
    book = ThesisBook(categoryId="c", entries=[_entry("a", "high"), _entry("b", "medium")])
    out = render_ranked_calls(book, _sc(), None, registry=_reg(), top_k=5)
    assert "folded" not in out


def test_book_none_empty_state():
    out = render_ranked_calls(None, _sc(), None, registry=_reg())
    assert "THE CALLS" in out and "no thesis book yet" in out
