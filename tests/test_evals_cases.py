from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent.evals.cases import CaseError, EvalCase, ExtractInput, load_cases

DOC = {"id": "d1", "source": "NVIDIA newsroom", "url": "http://x", "date": "2026-07-01",
       "tier": "primary", "entity": "NVDA", "content": "Blackwell shipments doubled."}

def _case_dict(case_id="extract-t-01", seam="extract", kind="positive"):
    return {
        "caseId": case_id, "seam": seam, "kind": kind,
        "source": "test", "input": {"doc": DOC, "asOf": "2026-07-03"},
        "recordedAnswer": "{\"findings\": []}",
        "checks": {"mustMention": ["Blackwell"], "citationsResolve": True, "gateOutcome": "pass"},
        "notes": "test case",
    }

def test_case_parses_and_seam_input_typed():
    case = EvalCase.model_validate(_case_dict())
    si = case.seam_input()
    assert isinstance(si, ExtractInput)
    assert si.doc.entity == "NVDA"
    assert si.asOf == "2026-07-03"

def test_seam_input_mismatch_raises():
    bad = _case_dict()
    bad["seam"] = "judge"          # judge input requires findings/category
    case = EvalCase.model_validate(bad)
    with pytest.raises(CaseError):
        case.seam_input()

def test_load_cases_sorted_and_duplicate_ids_rejected(tmp_path):
    (tmp_path / "b.json").write_text(json.dumps(_case_dict("extract-t-02")), "utf-8")
    (tmp_path / "a.json").write_text(json.dumps(_case_dict("extract-t-01")), "utf-8")
    cases = load_cases(tmp_path)
    assert [c.caseId for c in cases] == ["extract-t-01", "extract-t-02"]
    (tmp_path / "c.json").write_text(json.dumps(_case_dict("extract-t-01")), "utf-8")
    with pytest.raises(CaseError):
        load_cases(tmp_path)

def test_load_cases_names_bad_file(tmp_path):
    (tmp_path / "broken.json").write_text("{\"caseId\": 1}", "utf-8")
    with pytest.raises(CaseError) as e:
        load_cases(tmp_path)
    assert "broken.json" in str(e.value)
