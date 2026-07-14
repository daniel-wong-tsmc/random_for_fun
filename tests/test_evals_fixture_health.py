"""Golden-set health: every committed case loads, re-emits, deterministic checks hold, and
frozen answers still produce their recorded gate outcome under CURRENT gates (catches contract
drift rotting the golden set). Skips only when the cases dir is absent (pre-curation)."""
from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.evals.cases import load_cases
from gpu_agent.evals.emit import emit_brain_bundle
from gpu_agent.evals.harness import gate_brain_answer
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy

CASES_DIR = pathlib.Path("fixtures/evals/cases")
pytestmark = pytest.mark.skipif(not CASES_DIR.exists(),
                                reason="golden set not yet curated (F6 Task 8)")

def _cases():
    return load_cases(CASES_DIR)

def _reg():
    r = IndicatorRegistry.load(REGISTRY_PATH)
    t = Taxonomy.load(TAXONOMY_PATH)
    return r, t

def test_census_floors():
    cases = _cases()
    by_seam = {s: [c for c in cases if c.seam == s]
               for s in ("extract", "judge", "thesis", "implication")}
    assert len(by_seam["extract"]) >= 5
    assert len(by_seam["judge"]) >= 4
    assert len(by_seam["thesis"]) >= 4
    assert len(by_seam["implication"]) >= 2   # F65: 1 positive + 1 negative at the re-gate
    negatives = [c for c in cases if c.kind == "negative"]
    assert len(negatives) >= 4
    assert {c.seam for c in negatives} == {"extract", "judge", "thesis", "implication"}
    assert len(cases) >= 17

def test_every_case_reemits():
    registry, taxonomy = _reg()
    for c in _cases():
        bundle = emit_brain_bundle(c.seam, c.seam_input(), registry, taxonomy)
        assert bundle["user"], c.caseId

def test_frozen_answers_hold_their_gate_outcome():
    registry, taxonomy = _reg()
    for c in _cases():
        g = gate_brain_answer(c.seam, c.seam_input(), c.recordedAnswer, registry, taxonomy)
        expected_ok = c.checks.gateOutcome == "pass"
        assert g.ok == expected_ok, f"{c.caseId}: {g.violations}"

def test_must_mention_holds_on_positive_frozen_answers():
    for c in _cases():
        if c.kind != "positive":
            continue
        for needle in c.checks.mustMention:
            assert needle in c.recordedAnswer, f"{c.caseId}: '{needle}' missing"

def test_notes_and_source_are_substantive():
    for c in _cases():
        assert len(c.notes.strip()) >= 40, c.caseId
        assert c.source.strip(), c.caseId
