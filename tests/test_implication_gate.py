"""F65 Task 3 (acceptance 2): the deterministic implication gate rejects — loudly — an
uncited line, unknown citation ids, an over-length draft, a recommendation-verb draft, and
an off-allowlist acronym; a clean answer passes."""
from __future__ import annotations
from gpu_agent.implication import (
    gate_implication, ImplicationAnswer, ImplicationLine, MAX_IMPLICATION_LINES)
from gpu_agent.schema.scorecard import DIMENSIONS

DIMS = set(DIMENSIONS)
THESES = {"nvda-demand-durability"}


def _fbi():
    # The gate only checks id membership, never touches finding fields — dummy values are fine.
    return {"f-1": object()}


def _clean_line():
    return ImplicationLine(
        watchItem="Advanced-packaging tightness keeps the revenue ceiling below demand.",
        dimensions=["bottleneck"], thesisIds=["nvda-demand-durability"], findingIds=["f-1"])


def _gate(answer):
    return gate_implication(answer, findings_by_id=_fbi(), thesis_ids=THESES, dimensions=DIMS)


def test_clean_answer_passes():
    assert _gate(ImplicationAnswer(lines=[_clean_line()])) == []


def test_uncited_line_rejected():
    errs = _gate(ImplicationAnswer(lines=[ImplicationLine(watchItem="Something happens.")]))
    assert any("cites nothing" in e for e in errs)


def test_unknown_ids_rejected():
    errs = _gate(ImplicationAnswer(lines=[ImplicationLine(
        watchItem="Foundry exposure is rising.", dimensions=["nope"],
        thesisIds=["ghost"], findingIds=["f-9"])]))
    assert any("unknown dimension" in e for e in errs)
    assert any("unknown thesis" in e for e in errs)
    assert any("unknown finding" in e for e in errs)


def test_over_length_rejected():
    errs = _gate(ImplicationAnswer(lines=[_clean_line() for _ in range(MAX_IMPLICATION_LINES + 1)]))
    assert any("too many" in e for e in errs)


def test_recommendation_verb_rejected():
    errs = _gate(ImplicationAnswer(lines=[ImplicationLine(
        watchItem="TSMC should add packaging capacity.",
        dimensions=["bottleneck"], findingIds=["f-1"])]))
    assert any("recommendation" in e for e in errs)


def test_off_allowlist_acronym_rejected():
    errs = _gate(ImplicationAnswer(lines=[ImplicationLine(
        watchItem="Exposure to ZZZQQ demand is rising.",
        dimensions=["momentum"], findingIds=["f-1"])]))
    assert any("acronym" in e for e in errs)


def test_empty_watchitem_rejected():
    errs = _gate(ImplicationAnswer(lines=[ImplicationLine(watchItem="  ", dimensions=["moat"])]))
    assert any("empty watchItem" in e for e in errs)
