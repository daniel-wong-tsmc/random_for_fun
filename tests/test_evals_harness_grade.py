from __future__ import annotations
import json
import pytest
from gpu_agent.evals.cases import EvalCase
from gpu_agent.evals.harness import build_grade_prompt, record_grades, score_cases
from gpu_agent.evals.rubric import RUBRICS

DOC = {"id": "d1", "source": "s", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _case(case_id, kind="positive", seam="extract"):
    return EvalCase.model_validate({
        "caseId": case_id, "seam": seam, "kind": kind, "source": "t",
        "input": {"doc": DOC, "asOf": "2026-07-03"},
        "recordedAnswer": json.dumps({"findings": []}),
        "checks": {"gateOutcome": "pass"}, "notes": "good extraction keeps units exact",
    })

def _grade_json(case_id, score):
    grades = {c.key: {"score": score, "evidence": "quote"} for c in RUBRICS["extract"]}
    return json.dumps({"caseId": case_id, "grades": grades})

def test_build_grade_prompt_contains_rubric_answer_context_and_notes():
    from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.registry.structure import Taxonomy
    registry, taxonomy = IndicatorRegistry.load(REGISTRY_PATH), Taxonomy.load(TAXONOMY_PATH)
    case = _case("extract-t-01")
    bundle = build_grade_prompt(case, case.recordedAnswer, registry, taxonomy)
    assert set(bundle) == {"system", "schema", "user"}
    assert "RUBRIC (extract)" in bundle["user"]
    assert "Blackwell shipments doubled." in bundle["user"]   # brain context included
    assert case.recordedAnswer in bundle["user"]
    assert "good extraction keeps units exact" in bundle["user"]  # curator notes

def test_record_grades_parses_and_reports_violations():
    cases = [_case("extract-t-01"), _case("extract-t-02")]
    answers = {"extract-t-01": _grade_json("extract-t-01", 2),
               "extract-t-02": "not json"}
    grades, violations = record_grades(cases, answers)
    assert "extract-t-01" in grades and grades["extract-t-01"].caseId == "extract-t-01"
    assert "extract-t-02" in violations and violations["extract-t-02"]

def test_record_grades_flags_caseid_mismatch_and_missing_answers():
    cases = [_case("extract-t-01")]
    grades, violations = record_grades(cases, {"extract-t-01": _grade_json("other-id", 2)})
    assert any("caseId" in v for v in violations["extract-t-01"])
    grades, violations = record_grades(cases, {})
    assert any("missing" in v.lower() for v in violations["extract-t-01"])

def test_score_cases_means_and_calibration():
    cases = [_case("extract-t-01"), _case("extract-t-02"),
             _case("extract-t-03", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),   # 8
        "extract-t-02": _grade_json("extract-t-02", 1),   # 4
        "extract-t-03": _grade_json("extract-t-03", 1),   # 4 -> == max//2, calibration ok
    })
    report = score_cases(cases, grades)
    assert report["scores"]["extract-t-01"]["total"] == 8
    assert report["seamMeans"]["extract"] == pytest.approx(6.0)   # positives only
    assert report["calibration"]["extract-t-03"]["ok"] is True
    grades2, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),
        "extract-t-02": _grade_json("extract-t-02", 2),
        "extract-t-03": _grade_json("extract-t-03", 2),   # 8 > 4 -> miscalibrated
    })
    report2 = score_cases(cases, grades2)
    assert report2["calibration"]["extract-t-03"]["ok"] is False
