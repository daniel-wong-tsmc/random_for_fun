import pytest

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact, Kind
from gpu_agent.thesis import (
    PendingChallenge,
    ProposedThesis,
    ThesisAnswer,
    ThesisBook,
    ThesisEntry,
    ThesisJudgment,
    apply_answer,
)

AS_OF = "2026-07-03"
AS_OF_PRIOR = "2026-06-26"
CATEGORY_ID = "chips.merchant-gpu"


def _evidence(tier, url="https://Example.com/a", source="Example Source"):
    return Evidence(source=source, url=url, date=AS_OF, excerpt="excerpt", tier=tier)


def _finding(fid, *, evidence, indicator="D2"):
    return Finding(
        id=fid, statement="x", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"),
        asOf=AS_OF, indicatorId=indicator, side="demand",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="nvidia",
        observedAt=AS_OF, capturedAt=AS_OF, evidence=evidence,
    )


def _finding_with_domain(fid, domain):
    return _finding(fid, evidence=[_evidence("secondary", url=f"https://{domain}/page")])


def _entry(entry_id, *, status="registered", conviction="medium", lastDirection=0,
           streak=0, pendingChallenge=None, statement="Original statement.",
           lens="demand", createdAsOf=AS_OF_PRIOR, lastChangedAsOf=AS_OF_PRIOR):
    return ThesisEntry(
        id=entry_id, title=entry_id.replace("-", " ").title(), statement=statement,
        lens=lens, status=status, conviction=conviction, lastDirection=lastDirection,
        streak=streak, pendingChallenge=pendingChallenge,
        mechanism="mechanism", falsifiableTrigger="Reassessed next quarter.",
        sensitivity="sensitivity", createdAsOf=createdAsOf, lastChangedAsOf=lastChangedAsOf,
    )


def _book(*entries):
    return ThesisBook(categoryId=CATEGORY_ID, entries=list(entries))


def _judgment(thesis_id, *, verdict="reaffirmed", finding_ids=("f-1",),
              rationale="r", mechanism="new mechanism",
              trigger="Reassessed next quarter.", sensitivity="new sensitivity"):
    return ThesisJudgment(
        thesisId=thesis_id, verdict=verdict, rationale=rationale,
        findingIds=list(finding_ids), mechanism=mechanism,
        falsifiableTrigger=trigger, sensitivity=sensitivity,
    )


def _answer(*judgments, proposed=()):
    return ThesisAnswer(judgments=list(judgments), proposed=list(proposed))


SECONDARY_FINDING = {"f-1": _finding("f-1", evidence=[_evidence("secondary")])}


# --- a: reaffirmed applies; streak increments; conviction unchanged ---


def test_a_reaffirmed_applies_streak_increments_conviction_unchanged():
    entry = _entry("thesis-a", conviction="medium", lastDirection=0, streak=2)
    book = _book(entry)
    answer = _answer(_judgment("thesis-a", verdict="reaffirmed"))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-a")
    assert new_entry.conviction == "medium"
    assert new_entry.streak == 3
    assert new_entry.lastVerdict == "reaffirmed"
    assert new_entry.lastJudgedAsOf == AS_OF
    assert len(records) == 1
    assert records[0]["applied"] is True
    assert records[0]["verdict"] == "reaffirmed"
    assert records[0]["note"]
    assert notes == []  # a plain applied judgment isn't echoed to the notes list


# --- b: strengthened with no prior direction is NOT a reversal ---


def test_b_strengthened_with_no_prior_direction_is_not_a_reversal():
    entry = _entry("thesis-b", conviction="medium", lastDirection=0)
    book = _book(entry)
    answer = _answer(_judgment("thesis-b", verdict="strengthened"))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-b")
    assert records[0]["applied"] is True
    assert new_entry.conviction == "high"
    assert new_entry.lastDirection == 1
    assert notes == []


# --- c: weakened after lastDirection=+1 with secondary-only evidence -> deferred ---


def test_c_weakened_secondary_only_reversal_is_deferred():
    entry = _entry("thesis-c", conviction="medium", lastDirection=1)
    book = _book(entry)
    answer = _answer(_judgment("thesis-c", verdict="weakened", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-c")
    assert records[0]["applied"] is False
    assert new_entry.conviction == "medium"
    assert new_entry.pendingChallenge is not None
    assert new_entry.pendingChallenge.verdict == "weakened"
    assert new_entry.lastJudgedAsOf == AS_OF
    assert any("deferred: secondary-only reversal" in n for n in notes)


# --- d: same as c but with one primary-evidence finding -> applied, conviction down ---


def test_d_weakened_with_primary_evidence_applies_conviction_down():
    entry = _entry("thesis-d", conviction="medium", lastDirection=1)
    book = _book(entry)
    findings = {
        "f-1": _finding("f-1", evidence=[_evidence("secondary")]),
        "f-2": _finding("f-2", evidence=[_evidence("primary")]),
    }
    answer = _answer(_judgment("thesis-d", verdict="weakened", finding_ids=("f-1", "f-2")))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=findings, history=[],
    )

    new_entry = new_book.get("thesis-d")
    assert records[0]["applied"] is True
    assert new_entry.conviction == "low"
    assert new_entry.lastDirection == -1
    assert new_entry.pendingChallenge is None


# --- e: pendingChallenge + same-direction verdict -> applies (any tier), challenge cleared ---


def test_e_pending_challenge_same_direction_confirms_and_applies():
    challenge = PendingChallenge(
        verdict="weakened", asOf=AS_OF_PRIOR, rationale="r", findingIds=["f-0"],
    )
    entry = _entry("thesis-e", conviction="medium", lastDirection=1, pendingChallenge=challenge)
    book = _book(entry)
    answer = _answer(_judgment("thesis-e", verdict="weakened", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-e")
    assert len(records) == 1  # confirmation applies directly, no challenge-lapsed record
    assert records[0]["applied"] is True
    assert new_entry.pendingChallenge is None
    assert new_entry.conviction == "low"
    assert new_entry.lastDirection == -1


# --- f: pendingChallenge + opposite verdict -> challenge-lapsed, challenge cleared ---


def test_f_pending_challenge_opposite_direction_lapses_then_reapplies_normally():
    challenge = PendingChallenge(
        verdict="weakened", asOf=AS_OF_PRIOR, rationale="r", findingIds=["f-0"],
    )
    entry = _entry("thesis-f", conviction="medium", lastDirection=1, pendingChallenge=challenge)
    book = _book(entry)
    answer = _answer(_judgment("thesis-f", verdict="strengthened", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-f")
    assert len(records) == 2
    assert records[0]["event"] == "challenge-lapsed"
    assert records[0]["thesisId"] == "thesis-f"
    assert records[1]["verdict"] == "strengthened"
    assert records[1]["applied"] is True
    assert new_entry.pendingChallenge is None
    assert new_entry.conviction == "high"
    assert any("lapsed" in n for n in notes)


# --- g: broken with primary -> retired; broken secondary-only -> deferred like (c) ---


def test_g1_broken_with_primary_retires():
    entry = _entry("thesis-g1", conviction="medium", lastDirection=0)
    book = _book(entry)
    findings = {"f-1": _finding("f-1", evidence=[_evidence("primary")])}
    answer = _answer(_judgment("thesis-g1", verdict="broken", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=findings, history=[],
    )

    new_entry = new_book.get("thesis-g1")
    assert new_entry.status == "retired"
    assert new_entry.conviction == "low"
    assert len(records) == 2
    assert records[0]["verdict"] == "broken"
    assert records[0]["applied"] is True
    assert records[1]["event"] == "retired"
    assert records[1]["thesisId"] == "thesis-g1"
    assert any("retired" in n for n in notes)


def test_g2_broken_secondary_only_is_deferred():
    entry = _entry("thesis-g2", conviction="medium", lastDirection=0)
    book = _book(entry)
    answer = _answer(_judgment("thesis-g2", verdict="broken", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-g2")
    assert new_entry.status == "registered"  # not applied -> unchanged
    assert records[0]["applied"] is False
    assert len(records) == 1  # no retired lifecycle record when not applied
    assert new_entry.pendingChallenge is not None
    assert new_entry.pendingChallenge.verdict == "broken"
    assert any("deferred: secondary-only reversal" in n for n in notes)


# --- h: adjusted rewrites statement, direction stays 0 ---


def test_h_adjusted_rewrites_statement_direction_stays_zero():
    entry = _entry("thesis-h", conviction="medium", lastDirection=0, statement="Old statement.")
    book = _book(entry)
    answer = _answer(_judgment(
        "thesis-h", verdict="adjusted",
        rationale="ADJUSTED: A materially rewritten statement.",
    ))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-h")
    assert records[0]["applied"] is True
    assert new_entry.statement == "A materially rewritten statement."
    assert new_entry.lastDirection == 0
    assert new_entry.conviction == "medium"


# --- i: proposal appended provisional/low with proposed record ---


def test_i_proposal_appended_provisional_low_with_record():
    entry = _entry("thesis-i", conviction="medium")
    book = _book(entry)
    proposal = ProposedThesis(
        title="Fresh Angle", statement="A brand new falsifiable claim.", lens="risk",
        rationale="r", findingIds=["f-1"], mechanism="m",
        falsifiableTrigger="Reassessed next quarter.", sensitivity="s",
    )
    answer = _answer(_judgment("thesis-i", verdict="reaffirmed"), proposed=[proposal])

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("fresh-angle")
    assert new_entry is not None
    assert new_entry.status == "provisional"
    assert new_entry.conviction == "low"
    assert new_entry.provenance == f"proposed@{AS_OF}"
    assert new_entry.createdAsOf == AS_OF
    assert new_entry.lastChangedAsOf == AS_OF
    proposed_records = [r for r in records if r.get("event") == "proposed"]
    assert len(proposed_records) == 1
    assert proposed_records[0]["thesisId"] == "fresh-angle"
    assert any("fresh-angle" in n for n in notes)


# --- j: promotion at 2 asOfs / 2 publisher domains; stays provisional at 1 domain ---


def test_j1_promotion_across_two_asofs_two_domains():
    entry = _entry("thesis-j", status="provisional", conviction="low")
    book = _book(entry)
    history = [{
        "asOf": "2026-06-05", "thesisId": "thesis-j", "verdict": "reaffirmed",
        "applied": True, "conviction": "low", "rationale": "r", "findingIds": ["f-0"],
        "mechanism": "m", "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": ["domain-a.com"],
    }]
    findings = {"f-1": _finding_with_domain("f-1", "domain-b.com")}
    answer = _answer(_judgment("thesis-j", verdict="reaffirmed", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=findings, history=history,
    )

    new_entry = new_book.get("thesis-j")
    assert new_entry.status == "registered"
    promoted = [r for r in records if r.get("event") == "promoted"]
    assert len(promoted) == 1
    assert promoted[0]["thesisId"] == "thesis-j"
    assert any("promoted" in n for n in notes)


def test_j2_single_domain_stays_provisional():
    entry = _entry("thesis-j2", status="provisional", conviction="low")
    book = _book(entry)
    history = [{
        "asOf": "2026-06-05", "thesisId": "thesis-j2", "verdict": "reaffirmed",
        "applied": True, "conviction": "low", "rationale": "r", "findingIds": ["f-0"],
        "mechanism": "m", "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": ["domain-a.com"],
    }]
    findings = {"f-1": _finding_with_domain("f-1", "domain-a.com")}
    answer = _answer(_judgment("thesis-j2", verdict="reaffirmed", finding_ids=("f-1",)))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=findings, history=history,
    )

    new_entry = new_book.get("thesis-j2")
    assert new_entry.status == "provisional"
    assert not any(r.get("event") == "promoted" for r in records)


# --- k: conviction clamp ---


def test_k_conviction_clamp_strengthened_at_high_stays_high():
    entry = _entry("thesis-k", conviction="high", lastDirection=0)
    book = _book(entry)
    answer = _answer(_judgment("thesis-k", verdict="strengthened"))

    new_book, records, notes = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=[],
    )

    new_entry = new_book.get("thesis-k")
    assert new_entry.conviction == "high"


# --- cross-cutting: nothing silent, purity, deterministic ordering ---


def test_every_record_has_a_note():
    a = _entry("thesis-note-a", conviction="medium", lastDirection=1)
    b = _entry("thesis-note-b", status="provisional", conviction="medium", lastDirection=0)
    book = _book(a, b)
    findings = {
        "f-1": _finding("f-1", evidence=[_evidence("secondary")]),
        "f-2": _finding("f-2", evidence=[_evidence("primary")]),
    }
    proposal = ProposedThesis(
        title="Another Angle", statement="Another falsifiable claim entirely.", lens="supply",
        rationale="r", findingIds=["f-1"], mechanism="m",
        falsifiableTrigger="Reassessed next quarter.", sensitivity="s",
    )
    answer = _answer(
        _judgment("thesis-note-a", verdict="weakened", finding_ids=("f-1",)),  # deferred
        _judgment("thesis-note-b", verdict="reaffirmed", finding_ids=("f-2",)),
        proposed=[proposal],
    )

    _, records, _ = apply_answer(
        book, answer, as_of=AS_OF, findings_by_id=findings, history=[],
    )

    assert records  # sanity: something was produced
    for record in records:
        assert record.get("note"), f"record without a note: {record}"


def test_apply_answer_does_not_mutate_inputs():
    entry = _entry("thesis-pure", conviction="medium", lastDirection=1)
    book = _book(entry)
    book_snapshot = book.model_dump()
    answer = _answer(_judgment("thesis-pure", verdict="weakened", finding_ids=("f-1",)))
    answer_snapshot = answer.model_dump()
    history = [{"asOf": AS_OF_PRIOR, "thesisId": "thesis-pure", "verdict": "reaffirmed",
                "applied": True, "conviction": "medium", "rationale": "r", "findingIds": ["f-0"],
                "mechanism": "m", "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
                "publisherDomains": ["domain-a.com"]}]
    history_snapshot = [dict(r) for r in history]

    apply_answer(book, answer, as_of=AS_OF, findings_by_id=SECONDARY_FINDING, history=history)

    assert book.model_dump() == book_snapshot
    assert answer.model_dump() == answer_snapshot
    assert history == history_snapshot
