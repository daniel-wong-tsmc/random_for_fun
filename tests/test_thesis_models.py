import pytest
from pydantic import ValidationError

from gpu_agent.thesis import (
    LENSES,
    ThesisAnswer,
    ThesisBook,
    ThesisEntry,
    ThesisJudgment,
    seed_book,
    thesis_slug,
)

SEED_PATH = "registry/theses.chips.merchant-gpu.json"
CATEGORY_ID = "chips.merchant-gpu"
AS_OF = "2026-07-03"

EXPECTED_IDS = {
    "nvda-demand-durability",
    "supply-constraint-binding",
    "amd-credible-second-source",
    "custom-asic-substitution",
    "pricing-power-persistence",
    "export-control-exposure",
}


def test_seed_book_has_six_entries_with_seed_defaults():
    book = seed_book(SEED_PATH, CATEGORY_ID, AS_OF)
    assert isinstance(book, ThesisBook)
    assert book.categoryId == CATEGORY_ID
    assert len(book.entries) == 6
    assert {e.id for e in book.entries} == EXPECTED_IDS
    for entry in book.entries:
        assert entry.status == "registered"
        assert entry.conviction == "medium"
        assert entry.provenance == "seeded"
        assert entry.createdAsOf == AS_OF
        assert entry.lastChangedAsOf == AS_OF
        assert entry.streak == 0


def test_seed_entries_have_populated_depth_fields_and_valid_lens():
    book = seed_book(SEED_PATH, CATEGORY_ID, AS_OF)
    for entry in book.entries:
        assert entry.statement.strip() != ""
        assert entry.mechanism.strip() != ""
        assert entry.falsifiableTrigger.strip() != ""
        assert entry.sensitivity.strip() != ""
        assert entry.lens in LENSES


def test_thesis_answer_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ThesisAnswer(judgments=[], x=1)


def test_thesis_judgment_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        ThesisJudgment(
            thesisId="nvda-demand-durability",
            verdict="maybe",
            rationale="r",
            findingIds=["f-1"],
            mechanism="m",
            falsifiableTrigger="t",
            sensitivity="s",
        )


def test_thesis_book_standing_excludes_retired():
    book = ThesisBook(
        categoryId=CATEGORY_ID,
        entries=[
            ThesisEntry(
                id="a", title="A", statement="s", lens="demand", status="registered",
                mechanism="m", falsifiableTrigger="t", sensitivity="se",
                createdAsOf=AS_OF, lastChangedAsOf=AS_OF,
            ),
            ThesisEntry(
                id="b", title="B", statement="s", lens="supply", status="provisional",
                mechanism="m", falsifiableTrigger="t", sensitivity="se",
                createdAsOf=AS_OF, lastChangedAsOf=AS_OF,
            ),
            ThesisEntry(
                id="c", title="C", statement="s", lens="risk", status="retired",
                mechanism="m", falsifiableTrigger="t", sensitivity="se",
                createdAsOf=AS_OF, lastChangedAsOf=AS_OF,
            ),
        ],
    )
    assert {e.id for e in book.standing()} == {"a", "b"}
    assert book.get("c").status == "retired"
    assert book.get("missing") is None


def test_thesis_slug_matches_wiki_ingest_slug_semantics():
    assert thesis_slug("AMD credible 2nd source!") == "amd-credible-2nd-source"
