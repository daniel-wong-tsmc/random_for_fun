from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.evals.emit import load_hash_input
from gpu_agent.evals.harness import gate_brain_answer
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy

HASH_INPUT = pathlib.Path("fixtures/evals/hash-input.json")

@pytest.fixture()
def reg():
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    taxonomy = Taxonomy.load(TAXONOMY_PATH)
    return registry, taxonomy

def test_extract_empty_answer_gates_clean(reg):
    registry, taxonomy = reg
    si = load_hash_input(HASH_INPUT)["extract"]
    result = gate_brain_answer("extract", si, json.dumps({"findings": []}), registry, taxonomy)
    assert result.ok and result.violations == []

def test_extract_malformed_answer_rejects(reg):
    registry, taxonomy = reg
    si = load_hash_input(HASH_INPUT)["extract"]
    result = gate_brain_answer("extract", si, "not json", registry, taxonomy)
    assert not result.ok
    assert result.violations

def test_judge_recorded_fixture_answer_gates(reg):
    # fixtures/recorded/judge-nvda.json is the committed known-good recorded judge answer set;
    # its judgment cites findingId "doc-nvda-1", which fixtures/golden/findings.json does not
    # contain (that fixture's ids are f-nvda-d2/f-amd-s9/...). Pairing it with
    # fixtures/golden/findings.json trips the citation-group gate on a mismatched id, not on
    # the recorded answer's own reasoning. tests/test_cli_judge.py::test_judge_writes_status_json
    # pairs this exact recorded fixture with a single inline finding whose id is
    # "doc-nvda-1" (indicatorId D2, category chips.merchant-gpu) — use that same pairing here.
    registry, taxonomy = reg
    from gpu_agent.evals.cases import JudgeInput
    finding = {
        "id": "doc-nvda-1", "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
        "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e",
                      "tier": "primary"}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
        "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "E", "observedAt": "2026-06-01",
        "capturedAt": "2026-06-12T00:00:00Z",
    }
    si = JudgeInput(findings=[finding], category="chips.merchant-gpu", memoryText=None)
    answers = json.loads(pathlib.Path("fixtures/recorded/judge-nvda.json").read_text("utf-8"))
    result = gate_brain_answer("judge", si, answers[0], registry, taxonomy)
    assert result.ok, result.violations

def test_thesis_invalid_json_rejects(reg):
    registry, taxonomy = reg
    si = load_hash_input(HASH_INPUT)["thesis"]
    result = gate_brain_answer("thesis", si, "{}", registry, taxonomy)
    assert not result.ok
