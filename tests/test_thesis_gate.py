import pytest

from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Finding, Impact, Kind
from gpu_agent.thesis import (
    ProposedThesis,
    ThesisAnswer,
    ThesisBook,
    ThesisEntry,
    ThesisJudgment,
    gate_answer,
)

CATEGORY_ID = "chips.merchant-gpu"
AS_OF = "2026-07-03"

REGISTRY = IndicatorRegistry.load("registry/indicators.json")


def _entry(entry_id, title, statement, status):
    return ThesisEntry(
        id=entry_id, title=title, statement=statement, lens="demand", status=status,
        mechanism="m", falsifiableTrigger="t", sensitivity="s",
        createdAsOf=AS_OF, lastChangedAsOf=AS_OF,
    )


def _book():
    """Two standing theses (one registered, one provisional) + one retired thesis, so
    tests can exercise 'unknown thesis' against both a truly-unknown id and a retired
    (in-book-but-not-standing) id."""
    return ThesisBook(categoryId=CATEGORY_ID, entries=[
        _entry("thesis-a", "Thesis A", "Statement A", "registered"),
        _entry("thesis-b", "Thesis B", "Statement B", "provisional"),
        _entry("thesis-c", "Thesis C", "Statement C", "retired"),
    ])


def _finding(fid, indicator="D2"):
    return Finding(
        id=fid, statement="x", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"),
        asOf=AS_OF, indicatorId=indicator, side="demand",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="nvidia",
        observedAt=AS_OF, capturedAt=AS_OF,
    )


FINDINGS = {"f-1": _finding("f-1"), "f-2": _finding("f-2", indicator="apiArr")}


def _judgment(thesis_id, *, finding_ids=("f-1",), mechanism="m",
              trigger="Reassessed next quarter.", sensitivity="s", verdict="reaffirmed"):
    return ThesisJudgment(
        thesisId=thesis_id, verdict=verdict, rationale="r",
        findingIds=list(finding_ids), mechanism=mechanism,
        falsifiableTrigger=trigger, sensitivity=sensitivity,
    )


def _proposal(title="New Thesis", *, statement="A brand new statement.",
              finding_ids=("f-1",), mechanism="m",
              trigger="Reassessed next quarter.", sensitivity="s", lens="demand"):
    return ProposedThesis(
        title=title, statement=statement, lens=lens, rationale="r",
        findingIds=list(finding_ids), mechanism=mechanism,
        falsifiableTrigger=trigger, sensitivity=sensitivity,
    )


# --- clean baseline ---


def test_clean_answer_yields_no_violations():
    book = _book()
    answer = ThesisAnswer(judgments=[_judgment("thesis-a"), _judgment("thesis-b")])
    assert gate_answer(answer, book, FINDINGS, REGISTRY) == []


def test_clean_answer_with_valid_proposal_yields_no_violations():
    book = _book()
    answer = ThesisAnswer(
        judgments=[_judgment("thesis-a"), _judgment("thesis-b")],
        proposed=[_proposal()],
    )
    assert gate_answer(answer, book, FINDINGS, REGISTRY) == []


# --- rule 1: exactly one judgment per standing thesis ---


def test_missing_judgment_for_standing_thesis():
    book = _book()
    answer = ThesisAnswer(judgments=[_judgment("thesis-a")])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "no judgment for thesis thesis-b" in violations


def test_judgment_for_unknown_thesis_id():
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a"), _judgment("thesis-b"), _judgment("ghost-thesis"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "judgment for unknown thesis ghost-thesis" in violations


def test_judgment_for_retired_thesis_counts_as_unknown():
    """Retired theses are in the book but not 'standing' — a judgment naming one is out
    of scope for this cycle, same as a judgment naming an id the book has never seen."""
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a"), _judgment("thesis-b"), _judgment("thesis-c"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "judgment for unknown thesis thesis-c" in violations


def test_duplicate_judgment_for_same_thesis():
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a"), _judgment("thesis-a"), _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "duplicate judgment for thesis-a" in violations


# --- rule 2: findingIds non-empty and every id resolvable ---


def test_judgment_citing_no_findings():
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a", finding_ids=()), _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "thesis-a: cites no findings" in violations


def test_judgment_citing_unknown_finding():
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a", finding_ids=("f-999",)), _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "thesis-a: cites unknown finding f-999" in violations


# --- rule 3: depth fields non-empty + observable trigger ---


def test_judgment_missing_depth_fields():
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a", mechanism="  ", trigger="  ", sensitivity="  "),
        _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "thesis-a: missing mechanism" in violations
    assert "thesis-a: missing falsifiableTrigger" in violations
    assert "thesis-a: missing sensitivity" in violations


def test_trigger_heuristic_rejects_vague_trigger():
    """Pinned: 'lead times normalize' has no indicator id (no space in the registered id
    'leadTimes'), no digit, and no calendar-cadence keyword -> rejected."""
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a", trigger="CoWoS/HBM lead times normalize to historical norms."),
        _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "thesis-a: trigger names no observable" in violations


@pytest.mark.parametrize("trigger, why", [
    ("The D6 price track declines across providers.", "registered indicator id"),
    ("Merchant GPU pricing falls 15% quarter over quarter.", "digit"),
    ("No deployment for two consecutive quarters.", "calendar-cadence keyword"),
])
def test_trigger_heuristic_accepts_observable_triggers(trigger, why):
    book = _book()
    answer = ThesisAnswer(judgments=[
        _judgment("thesis-a", trigger=trigger), _judgment("thesis-b"),
    ])
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "thesis-a: trigger names no observable" not in violations, why


# --- rule 4: proposals ---


def test_proposal_duplicates_existing_thesis_id():
    book = _book()
    answer = ThesisAnswer(
        judgments=[_judgment("thesis-a"), _judgment("thesis-b")],
        proposed=[_proposal(title="Thesis A", statement="Something new entirely.")],
    )
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "proposal duplicates thesis id thesis-a" in violations


def test_proposal_duplicates_existing_statement_case_and_whitespace_insensitive():
    book = _book()
    answer = ThesisAnswer(
        judgments=[_judgment("thesis-a"), _judgment("thesis-b")],
        proposed=[_proposal(title="Totally Different Title", statement="  STATEMENT   A  ")],
    )
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "proposal duplicates statement of thesis-a" in violations


def test_proposal_citation_and_depth_field_rules_apply():
    book = _book()
    answer = ThesisAnswer(
        judgments=[_judgment("thesis-a"), _judgment("thesis-b")],
        proposed=[_proposal(
            title="Fresh Angle", statement="Not previously stated.",
            finding_ids=(), mechanism="", trigger="", sensitivity="",
        )],
    )
    violations = gate_answer(answer, book, FINDINGS, REGISTRY)
    assert "fresh-angle: cites no findings" in violations
    assert "fresh-angle: missing mechanism" in violations
    assert "fresh-angle: missing falsifiableTrigger" in violations
    assert "fresh-angle: missing sensitivity" in violations
