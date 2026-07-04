"""F63 rule-6 amendment: a secondary-only reversal APPLIES when its cited findings span
>=3 distinct publishers (F31 key); <3 defers exactly as before, with the count visible."""
from gpu_agent.schema.finding import Finding, Confidence, Impact, Evidence
from gpu_agent.thesis import ThesisBook, ThesisEntry, ThesisAnswer, ThesisJudgment, apply_answer

AS_OF = "2026-07-04"
AS_OF_PRIOR = "2026-06-27"
CATEGORY_ID = "chips.merchant-gpu"


def _sec(url):
    return Evidence(source="s", url=url, date="2026-07-01", excerpt="e", tier="secondary")


def _finding(fid, evidence):
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="NVDA", observedAt="2026-07-01",
        capturedAt="2026-07-04T00:00:00Z", evidence=evidence)


def _book_with_positive_last_direction():
    entry = ThesisEntry(
        id="t1", lens="demand", title="T1", statement="s",
        status="registered", conviction="medium", lastVerdict="strengthened",
        lastDirection=1, streak=1, mechanism="m", falsifiableTrigger="Reassessed next quarter.",
        sensitivity="s", createdAsOf=AS_OF_PRIOR, lastChangedAsOf=AS_OF_PRIOR,
    )
    return ThesisBook(categoryId=CATEGORY_ID, entries=[entry])


def _weaken_judgment(finding_ids):
    return ThesisAnswer(judgments=[ThesisJudgment(
        thesisId="t1", verdict="weakened", rationale="r", findingIds=finding_ids,
        mechanism="m", falsifiableTrigger="drops for 2 consecutive quarters",
        sensitivity="s")], proposed=[])


def test_corroborated_secondary_reversal_applies():
    fbi = {"f1": _finding("f1", [_sec("https://reuters.com/a")]),
           "f2": _finding("f2", [_sec("https://digitimes.com/b")]),
           "f3": _finding("f3", [_sec("https://tomshardware.com/c")])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1", "f2", "f3"]),
        as_of=AS_OF, findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is True
    assert rec["corroboratedStep"] is True
    assert rec["note"] == ("t1: applied: corroborated secondary reversal "
                           "(3 distinct publishers; pending filing checkpoint)")
    assert rec["conviction"] == "low"          # medium weakened -> low (bounded -1)


def test_two_publisher_reversal_still_defers_with_count():
    fbi = {"f1": _finding("f1", [_sec("https://reuters.com/a")]),
           "f2": _finding("f2", [_sec("https://www.reuters.com/b")]),   # syndication: same key
           "f3": _finding("f3", [_sec("https://digitimes.com/c")])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1", "f2", "f3"]),
        as_of=AS_OF, findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is False
    assert rec["corroboratedStep"] is False
    assert rec["note"] == "t1: deferred: secondary-only reversal (2 distinct publishers < 3)"
    assert rec["conviction"] == "medium"       # unchanged


def test_primary_reversal_unaffected_no_corroborated_flag():
    prim = Evidence(source="sec.gov", url="https://sec.gov/x", date="2026-07-01",
                    excerpt="e", tier="primary")
    fbi = {"f1": _finding("f1", [prim])}
    book, records, notes = apply_answer(
        _book_with_positive_last_direction(), _weaken_judgment(["f1"]),
        as_of=AS_OF, findings_by_id=fbi, history=[])
    rec = next(r for r in records if r.get("thesisId") == "t1" and "verdict" in r)
    assert rec["applied"] is True
    assert rec["corroboratedStep"] is False    # primary applied it, not corroboration
