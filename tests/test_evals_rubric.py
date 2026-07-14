from __future__ import annotations
import pytest
from gpu_agent.evals.rubric import (
    RUBRICS, CriterionGrade, GradeResult, case_score, gate_grade, max_score, render_rubric)

def _grade(seam="judge", **overrides):
    grades = {c.key: CriterionGrade(score=2, evidence="quoted line from the answer")
              for c in RUBRICS[seam]}
    grades.update(overrides)
    return GradeResult(caseId="x", grades=grades)

def test_rubrics_shape():
    # F65 adds the implication rubric (4 criteria, like the others). This is the rubric set,
    # NOT the F6 prompt-hash pin — the pin's seam set stays {extract,judge,thesis} until the
    # implication eval re-gate.
    assert set(RUBRICS) == {"extract", "judge", "thesis", "implication"}
    for seam, criteria in RUBRICS.items():
        assert len(criteria) == 4, seam
        for c in criteria:
            assert set(c.anchors) == {"0", "1", "2"}
        assert max_score(seam) == 8

def test_gate_grade_accepts_complete_grade():
    assert gate_grade(_grade(), "judge") == []

def test_gate_grade_rejects_missing_and_extra_and_blank_evidence():
    g = _grade()
    del g.grades["crux"]
    g.grades["invented"] = CriterionGrade(score=1, evidence="e")
    violations = gate_grade(g, "judge")
    assert any("missing criterion 'crux'" in v for v in violations)
    assert any("unknown criterion 'invented'" in v for v in violations)
    g2 = _grade(mechanism=CriterionGrade(score=1, evidence="   "))
    assert any("evidence" in v for v in gate_grade(g2, "judge"))

def test_score_bounds_enforced_by_model():
    with pytest.raises(Exception):
        CriterionGrade(score=3, evidence="e")

def test_case_score_sums():
    g = _grade(crux=CriterionGrade(score=0, evidence="e"))
    assert case_score(g) == 6

def test_render_rubric_contains_anchors():
    text = render_rubric("thesis")
    assert "trigger-quality" in text and "0:" in text and "2:" in text
