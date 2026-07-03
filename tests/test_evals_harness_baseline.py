from __future__ import annotations
import json
import pytest
from gpu_agent.evals.cases import EvalCase
from gpu_agent.evals.harness import build_report, load_baseline, rebaseline, record_grades
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
    assert report["verdict"]["pass"] is True
    assert any("bootstrap" in r for r in report["verdict"]["reasons"])
    assert report["promptHashes"] == HASHES

def test_regression_fails_and_improvement_passes():
    # Positive case scored 1 per criterion (total 4, seam mean 4.0) so regression,
    # improvement, AND tie are all exercisable. Negative stays 0 so calibration is ok.
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 1),
        "extract-t-02": _grade_json("extract-t-02", 0),
    })
    high = {"seamMeans": {"extract": 6.0}, "cases": {}, "promptHashes": HASHES,
            "provenance": {}}
    report = build_report(cases, grades, HASHES, baseline=high, as_of="2026-07-04")
    assert report["verdict"]["pass"] is False
    assert any("extract" in r for r in report["verdict"]["reasons"])
    low = {"seamMeans": {"extract": 3.0}, "cases": {}, "promptHashes": HASHES,
           "provenance": {}}
    report2 = build_report(cases, grades, HASHES, baseline=low, as_of="2026-07-04")
    assert report2["verdict"]["pass"] is True
    tie = {"seamMeans": {"extract": 4.0}, "cases": {}, "promptHashes": HASHES,
           "provenance": {}}
    report3 = build_report(cases, grades, HASHES, baseline=tie, as_of="2026-07-04")
    assert report3["verdict"]["pass"] is True  # ties PASS per spec comparison rule

def test_miscalibration_fails_verdict():
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),
        "extract-t-02": _grade_json("extract-t-02", 2),   # negative scores 8 -> miscalibrated
    })
    report = build_report(cases, grades, HASHES, baseline=None, as_of="2026-07-04")
    assert report["verdict"]["pass"] is False
    assert any("miscalibrated" in r for r in report["verdict"]["reasons"])

def test_rebaseline_writes_and_refuses(tmp_path):
    cases, grades = _scored()
    report = build_report(cases, grades, HASHES, baseline=None, as_of="2026-07-04")
    path = tmp_path / "baseline.json"
    written = rebaseline(report, path, human_review="spot-checked extract-t-01")
    on_disk = load_baseline(path)
    assert on_disk["seamMeans"] == report["seamMeans"]
    assert on_disk["provenance"]["humanReview"] == "spot-checked extract-t-01"
    assert on_disk["provenance"]["forceReason"] is None
    failing = dict(report, verdict={"pass": False, "reasons": ["x"]})
    with pytest.raises(ValueError):
        rebaseline(failing, path)
    forced = rebaseline(failing, path, force_reason="accepting extract dip for judge gain")
    assert forced["provenance"]["forceReason"].startswith("accepting")

def test_load_baseline_missing_returns_none(tmp_path):
    assert load_baseline(tmp_path / "nope.json") is None
