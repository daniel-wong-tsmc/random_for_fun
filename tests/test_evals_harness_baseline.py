from __future__ import annotations
import json
import pytest
from gpu_agent.evals.cases import EvalCase
from gpu_agent.evals.harness import build_report, load_baseline, record_grades
from gpu_agent.evals.rubric import RUBRICS

HASHES = {"extract": "a" * 64, "judge": "b" * 64, "thesis": "c" * 64}
DOC = {"id": "d1", "source": "s", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _case(case_id, kind="positive"):
    return EvalCase.model_validate({
        "caseId": case_id, "seam": "extract", "kind": kind, "source": "t",
        "input": {"doc": DOC, "asOf": "2026-07-03"},
        "recordedAnswer": json.dumps({"findings": []}),
        "checks": {"gateOutcome": "pass"}, "notes": "n",
    })

def _grade_json(case_id, score):
    return json.dumps({"caseId": case_id, "grades": {
        c.key: {"score": score, "evidence": "q"} for c in RUBRICS["extract"]}})

def _scored():
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),
        "extract-t-02": _grade_json("extract-t-02", 0),
    })
    return cases, grades

def test_bootstrap_report_passes_with_reason():
    cases, grades = _scored()
    report = build_report(cases, grades, HASHES, baseline=None, as_of="2026-07-04")
    assert report["verdict"]["decision"] == "bootstrap"
    assert report["verdict"]["pass"] is True
    assert any("bootstrap" in r for r in report["verdict"]["reasons"])
    assert report["promptHashes"] == HASHES

def test_v2_verdict_embeds_in_report():
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 1),   # total 4
        "extract-t-02": _grade_json("extract-t-02", 0),
    })
    # F65g: the marginal machinery only binds a GATED seam, so the baseline records a
    # different extract hash than the run (the seam's prompt moved).
    base = {"schemaVersion": 2, "promptHashes": dict(HASHES, extract="0" * 64),
            "seamMeans": {"extract": 4.25}, "epsilon": {"extract": 0.25},
            "caseMedians": {"extract-t-01": 4}, "replicates": [], "provenance": {}}
    report = build_report(cases, grades, HASHES, baseline=base, as_of="2026-07-05")
    # F73b: 4.0 == bar 4.0 is a bar-touch, now within the marginal band -> marginal-pass
    assert report["verdict"]["decision"] == "marginal-pass"
    assert report["verdict"]["pass"] is True
    tight = dict(base, seamMeans={"extract": 4.5})        # bar 4.25 -> marginal band
    report2 = build_report(cases, grades, HASHES, baseline=tight, as_of="2026-07-05")
    assert report2["verdict"]["decision"] == "marginal-fail"
    # ...and the same sag on a hash-identical (informational) seam cannot fail the run
    report3 = build_report(cases, grades, HASHES,
                           baseline=dict(tight, promptHashes=HASHES), as_of="2026-07-05")
    assert report3["verdict"]["decision"] == "pass"

def test_v1_baseline_yields_no_comparison():
    cases, grades = _scored()
    v1 = {"seamMeans": {"extract": 8.0}, "cases": {}, "promptHashes": HASHES,
          "provenance": {}}
    report = build_report(cases, grades, HASHES, baseline=v1, as_of="2026-07-05")
    assert report["verdict"]["decision"] == "no-comparison"
    assert report["verdict"]["pass"] is True

def test_miscalibration_fails_verdict():
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),
        "extract-t-02": _grade_json("extract-t-02", 2),   # negative scores 8 -> miscalibrated
    })
    report = build_report(cases, grades, HASHES, baseline=None, as_of="2026-07-04")
    assert report["verdict"]["pass"] is False
    assert report["verdict"]["decision"] == "invalid-run"
    assert any("miscalibrated" in r for r in report["verdict"]["reasons"])

def test_v1_rebaseline_is_gone():
    from gpu_agent.evals import harness
    assert not hasattr(harness, "rebaseline")

def test_load_baseline_missing_returns_none(tmp_path):
    assert load_baseline(tmp_path / "nope.json") is None
