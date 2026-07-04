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


from gpu_agent.evals.harness import evaluate_v2

def _report(seam_means, scores, hashes=HASHES, calibration=None):
    return {"seamMeans": seam_means,
            "scores": {cid: {"total": t, "grades": {}} for cid, t in scores.items()},
            "calibration": calibration if calibration is not None else {},
            "promptHashes": hashes, "asOf": "2026-07-05"}

# baseline: mean 6.5, eps 0.25 -> bar 6.25, hard bar 6.0; medians e1=7, e2=6
BASE = {"schemaVersion": 2, "promptHashes": HASHES,
        "seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.25},
        "caseMedians": {"e1": 7, "e2": 6}}

def test_verdict_pass_on_bar_touch():
    v = evaluate_v2(BASE, [_report({"extract": 6.25}, {"e1": 7, "e2": 6})])
    assert (v["decision"], v["pass"]) == ("pass", True)

def test_verdict_marginal_within_one_epsilon_below_bar():
    v = evaluate_v2(BASE, [_report({"extract": 6.0}, {"e1": 7, "e2": 5})])
    assert v["decision"] == "marginal-fail"
    assert any("extract" in r for r in v["reasons"])

def test_verdict_hard_fail_below_two_epsilon():
    v = evaluate_v2(BASE, [_report({"extract": 5.875}, {"e1": 6, "e2": 6})])
    assert (v["decision"], v["pass"]) == ("hard-fail", False)

def test_crater_fails_at_median_minus_three_even_when_seam_passes():
    # e1 total 4 = median 7 - 3 -> crater (marginal band: within 1 beyond the line)
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 4, "e2": 8})])
    assert v["decision"] == "marginal-fail"
    assert v["craters"] == [{"caseId": "e1", "value": 4, "median": 7}]

def test_crater_hard_fails_at_median_minus_five():
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 2, "e2": 8})])
    assert v["decision"] == "hard-fail"

def test_two_run_mean_decides_after_marginal():
    r1 = _report({"extract": 6.0}, {"e1": 7, "e2": 5})
    r2 = _report({"extract": 6.5}, {"e1": 7, "e2": 6})   # mean 6.25 == bar -> pass
    assert evaluate_v2(BASE, [r1, r2])["decision"] == "pass"
    r3 = _report({"extract": 6.375}, {"e1": 7, "e2": 6})  # mean 6.1875 < bar -> fail
    assert evaluate_v2(BASE, [r1, r3])["decision"] == "fail"

def test_invalid_run_on_miscalibration_missing_seam_or_hash_mismatch():
    bad_cal = _report({"extract": 6.5}, {"e1": 7, "e2": 6},
                      calibration={"n1": {"score": 5, "max": 4, "ok": False}})
    assert evaluate_v2(BASE, [bad_cal])["decision"] == "invalid-run"
    no_seam = _report({}, {"e1": 7, "e2": 6})
    assert evaluate_v2(BASE, [no_seam])["decision"] == "invalid-run"
    other = _report({"extract": 6.5}, {"e1": 7, "e2": 6}, hashes={"extract": "z" * 64})
    v = evaluate_v2(BASE, [_report({"extract": 6.5}, {"e1": 7, "e2": 6}), other])
    assert v["decision"] == "invalid-run"
