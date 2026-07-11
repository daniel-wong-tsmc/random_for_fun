# tests/test_thesis_pacing.py
"""F78 Stage 2: calendar-day thesis pacing. streak advance, conviction swing, and rule-5
promotion are measured in CALENDAR DAYS derived from asOf labels, not per cycle."""
import pytest

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact, Kind
from gpu_agent.thesis import (
    MIN_PACE_GAP_DAYS,
    MIN_PROMOTION_SPAN_DAYS,
    ThesisAnswer,
    ThesisBook,
    ThesisEntry,
    ThesisJudgment,
    _pace_counts,
    apply_answer,
)

CATEGORY_ID = "chips.merchant-gpu"


def _evidence(tier, url="https://example.com/a"):
    return Evidence(source="Example", url=url, date="2026-07-01", excerpt="e", tier=tier)


def _finding(fid, *, evidence, indicator="D2"):
    return Finding(
        id=fid, statement="x", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"),
        asOf="2026-07", indicatorId=indicator, side="demand",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="nvidia",
        observedAt="2026-07-01", capturedAt="2026-07-01", evidence=evidence,
    )


def _fd(fid, domain):
    return _finding(fid, evidence=[_evidence("secondary", url=f"https://{domain}/p")])


def _entry(entry_id, **kw):
    base = dict(
        title="T", statement="s", lens="demand", status="registered",
        conviction="medium", lastDirection=0, streak=0,
        mechanism="m", falsifiableTrigger="Reassessed next quarter.",
        sensitivity="s", createdAsOf="2026-05-01", lastChangedAsOf="2026-05-01",
    )
    base.update(kw)
    return ThesisEntry(id=entry_id, **base)


def _book(*entries):
    return ThesisBook(categoryId=CATEGORY_ID, entries=list(entries))


def _judgment(thesis_id, *, verdict="reaffirmed", finding_ids=("f-1",), rationale="r"):
    return ThesisJudgment(
        thesisId=thesis_id, verdict=verdict, rationale=rationale,
        findingIds=list(finding_ids), mechanism="m",
        falsifiableTrigger="Reassessed next quarter.", sensitivity="s",
    )


def _answer(*judgments):
    return ThesisAnswer(judgments=list(judgments), proposed=[])


SEC = {"f-1": _finding("f-1", evidence=[_evidence("secondary")])}


def test_dials_are_the_provisional_defaults():
    assert MIN_PACE_GAP_DAYS == 21
    assert MIN_PROMOTION_SPAN_DAYS == 21


def test_pace_counts_first_signal_always_counts():
    # no prior counted signal (freshly seeded/proposed: lastPaceAsOf == "") -> counts,
    # so a thesis's FIRST judgment behaves exactly as before this change.
    assert _pace_counts("", "2026-07-03") is True


def test_pace_counts_below_gap_does_not_count():
    assert _pace_counts("2026-07-01", "2026-07-21") is False    # 20 days < 21


def test_pace_counts_at_gap_boundary_counts():
    assert _pace_counts("2026-07-01", "2026-07-22") is True     # exactly 21 days


def test_pace_counts_handles_mixed_grain_labels():
    # month-grain vs day-grain, resolved by period_end, never lexicographically.
    assert _pace_counts("2026-06", "2026-07-31") is True        # Jun30 -> Jul31 = 31 days
    assert _pace_counts("2026-07", "2026-07-15") is False       # Jul31 -> Jul15 = -16 days


# --- streak pacing (via apply_answer's applied path) -----------------------------------

def test_streak_holds_when_confirmation_is_too_soon():
    # a same-direction reaffirm only 7 days after the last counted signal must NOT advance.
    entry = _entry("t", conviction="medium", lastDirection=0, streak=4,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="reaffirmed")),
        as_of="2026-07-08", findings_by_id=SEC, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True
    assert e.streak == 4                      # held, not 5
    assert e.lastPaceAsOf == "2026-07-01"     # clock still runs from the prior counted signal


def test_streak_advances_when_confirmation_clears_the_gap():
    entry = _entry("t", conviction="medium", lastDirection=0, streak=4,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="reaffirmed")),
        as_of="2026-08-01", findings_by_id=SEC, history=[],   # 31 days after 2026-07-01
    )
    e = new_book.get("t")
    assert e.streak == 5
    assert e.lastPaceAsOf == "2026-08-01"     # re-anchored


# --- conviction pacing -----------------------------------------------------------------

def test_conviction_holds_when_strengthened_too_soon():
    # strengthened again only 7 days after the last counted signal must NOT walk medium->high.
    entry = _entry("t", conviction="medium", lastDirection=1, streak=1,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="strengthened")),
        as_of="2026-07-08", findings_by_id=SEC, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True       # a same-direction strengthen still applies
    assert records[0]["conviction"] == "medium"
    assert e.conviction == "medium"            # but the level is rate-limited: held
    assert e.streak == 1                        # no conviction change, too soon -> held


def test_conviction_steps_when_strengthened_clears_the_gap():
    entry = _entry("t", conviction="medium", lastDirection=1, streak=1,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="strengthened")),
        as_of="2026-08-01", findings_by_id=SEC, history=[],   # 31-day gap clears the pace
    )
    e = new_book.get("t")
    assert e.conviction == "high"
    assert e.streak == 1                        # conviction change re-anchors the streak


def test_reversal_steps_conviction_immediately_despite_recent_signal():
    # a reversal is a genuine event: even 1 day after the last counted signal, a primary
    # weakened reversal steps conviction and is NOT rate-limited.
    entry = _entry("t", conviction="high", lastDirection=1, streak=3,
                   lastPaceAsOf="2026-07-07", lastChangedAsOf="2026-07-07")
    findings = {"f-1": _finding("f-1", evidence=[_evidence("primary")])}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="weakened")),
        as_of="2026-07-08", findings_by_id=findings, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True
    assert e.conviction == "medium"            # high -> medium, one step, despite 1-day gap
    assert e.lastDirection == -1


# --- rule-5 promotion pacing -----------------------------------------------------------

def _history_reaffirm(thesis_id, as_of, domain):
    return {
        "asOf": as_of, "thesisId": thesis_id, "verdict": "reaffirmed", "applied": True,
        "conviction": "low", "rationale": "r", "findingIds": ["f-0"], "mechanism": "m",
        "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": [domain],
    }


def test_promotion_needs_calendar_span_not_two_cycles():
    # two judgments only 7 days apart, 2 distinct domains: NOT promotable (span 7 < 21).
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-07-01", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-b.com")}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "provisional"
    assert not any(r.get("event") == "promoted" for r in records)


def test_promotion_when_span_and_domains_met():
    # 33-day span (period_end 2026-06-05 -> 2026-07-08) and 2 distinct domains -> promotes.
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-06-05", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-b.com")}
    new_book, records, notes = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "registered"
    promoted = [r for r in records if r.get("event") == "promoted"]
    assert len(promoted) == 1
    assert "days judged" in promoted[0]["note"]
    assert any("promoted" in n for n in notes)


def test_promotion_blocked_by_single_domain_even_when_span_met():
    # 33-day span but only ONE distinct domain -> the domain bar (unchanged) still blocks.
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-06-05", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-a.com")}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "provisional"
    assert not any(r.get("event") == "promoted" for r in records)
