"""eval-v2 (replicate baseline) unit tests — pure decision math over synthetic reports.
Spec: docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md."""
from __future__ import annotations
import json
import pytest
from gpu_agent.evals.cases import EvalCase
from gpu_agent.evals.harness import case_medians, compute_epsilon, seam_quanta

HASHES = {"extract": "a" * 64, "judge": "b" * 64, "thesis": "c" * 64}
DOC = {"id": "d1", "source": "s", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _case(case_id, kind="positive", seam="extract"):
    return EvalCase.model_validate({
        "caseId": case_id, "seam": seam, "kind": kind, "source": "t",
        "input": {"doc": DOC, "asOf": "2026-07-03"},
        "recordedAnswer": json.dumps({"findings": []}),
        "checks": {"gateOutcome": "pass"}, "notes": "n",
    })

def test_seam_quanta_counts_positives_only():
    cases = [_case("e1"), _case("e2"), _case("e3", kind="negative"),
             _case("e4"), _case("e5")]
    assert seam_quanta(cases) == {"extract": 0.25}

def test_compute_epsilon_half_range():
    means = [{"extract": 6.75}, {"extract": 6.375}, {"extract": 6.5}]
    eps = compute_epsilon(means, {"extract": 0.125})
    assert eps["extract"] == pytest.approx(0.1875)

def test_compute_epsilon_quantum_floor_when_replicates_tie():
    means = [{"thesis": 6.0}, {"thesis": 6.0}, {"thesis": 6.0}]
    assert compute_epsilon(means, {"thesis": 0.5}) == {"thesis": 0.5}

def test_case_medians_positives_only_median_of_three():
    scores = [{"e1": 7, "e2": 4, "n1": 2}, {"e1": 5, "e2": 8, "n1": 0},
              {"e1": 6, "e2": 6, "n1": 1}]
    assert case_medians(scores, {"e1", "e2"}) == {"e1": 6, "e2": 6}
