from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent.cli import main

DOC = {"id": "d1", "source": "s", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _write_cases(tmp_path):
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir()
    from gpu_agent.evals.rubric import RUBRICS
    for cid, kind in (("extract-t-01", "positive"), ("extract-t-02", "negative")):
        (cases_dir / f"{cid}.json").write_text(json.dumps({
            "caseId": cid, "seam": "extract", "kind": kind, "source": "t",
            "input": {"doc": DOC, "asOf": "2026-07-03"},
            "recordedAnswer": json.dumps({"findings": []}),
            "checks": {"gateOutcome": "pass"}, "notes": "n",
        }), "utf-8")
    return cases_dir

def _grade(cid, score):
    from gpu_agent.evals.rubric import RUBRICS
    return json.dumps({"caseId": cid, "grades": {
        c.key: {"score": score, "evidence": "q"} for c in RUBRICS["extract"]}})

def test_eval_full_offline_cycle(tmp_path, capsys):
    cases_dir = _write_cases(tmp_path)
    run = tmp_path / "run"
    assert main(["eval", "emit-brain", "--cases", str(cases_dir), "--out", str(run)]) == 0
    prompts = json.loads((run / "brain-prompts.json").read_text("utf-8"))
    assert set(prompts) == {"extract-t-01"}          # positives only
    assert set(prompts["extract-t-01"]) == {"system", "schema", "user"}

    (run / "brain-answers.json").write_text(
        json.dumps({"extract-t-01": json.dumps({"findings": []})}), "utf-8")
    assert main(["eval", "record-brain", "--cases", str(cases_dir), "--out", str(run)]) == 0
    gates = json.loads((run / "brain-gates.json").read_text("utf-8"))
    assert gates["extract-t-01"]["ok"] is True

    assert main(["eval", "emit-grade", "--cases", str(cases_dir), "--out", str(run)]) == 0
    gp = json.loads((run / "grade-prompts.json").read_text("utf-8"))
    assert set(gp) == {"extract-t-01", "extract-t-02"}   # positives fresh + negatives frozen

    (run / "grade-answers.json").write_text(json.dumps({
        "extract-t-01": _grade("extract-t-01", 2),
        "extract-t-02": _grade("extract-t-02", 0)}), "utf-8")
    baseline = tmp_path / "baseline.json"
    assert main(["eval", "record-grade", "--cases", str(cases_dir), "--out", str(run),
                 "--as-of", "2026-07-04", "--baseline", str(baseline)]) == 0
    report = json.loads((run / "report.json").read_text("utf-8"))
    assert report["verdict"]["pass"] is True

    assert main(["eval", "rebaseline", "--out", str(run), "--baseline", str(baseline)]) == 0
    assert json.loads(baseline.read_text("utf-8"))["seamMeans"]["extract"] == 8.0

def test_record_brain_gate_failure_exits_1(tmp_path):
    cases_dir = _write_cases(tmp_path)
    run = tmp_path / "run"
    main(["eval", "emit-brain", "--cases", str(cases_dir), "--out", str(run)])
    (run / "brain-answers.json").write_text(json.dumps({"extract-t-01": "not json"}), "utf-8")
    assert main(["eval", "record-brain", "--cases", str(cases_dir), "--out", str(run)]) == 1

def test_record_grade_regression_exits_1(tmp_path):
    cases_dir = _write_cases(tmp_path)
    run = tmp_path / "run"
    main(["eval", "emit-brain", "--cases", str(cases_dir), "--out", str(run)])
    (run / "brain-answers.json").write_text(
        json.dumps({"extract-t-01": json.dumps({"findings": []})}), "utf-8")
    main(["eval", "record-brain", "--cases", str(cases_dir), "--out", str(run)])
    main(["eval", "emit-grade", "--cases", str(cases_dir), "--out", str(run)])
    (run / "grade-answers.json").write_text(json.dumps({
        "extract-t-01": _grade("extract-t-01", 1),
        "extract-t-02": _grade("extract-t-02", 0)}), "utf-8")
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"promptHashes": {}, "cases": {},
                                    "seamMeans": {"extract": 8.0}, "provenance": {}}), "utf-8")
    assert main(["eval", "record-grade", "--cases", str(cases_dir), "--out", str(run),
                 "--as-of", "2026-07-04", "--baseline", str(baseline)]) == 1
