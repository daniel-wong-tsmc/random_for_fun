import pytest
from pydantic import ValidationError
from gpu_agent.extraction.extractor import FindingDraft, draft_to_finding

def _draft(**over):
    data = {
        "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "w", "impact": {"targets": ["x"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "secondary"}],
        "confidence": {"level": "medium", "basis": "b"}, "indicatorId": "D2",
        "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
        "entity": "NVDA", "observedAt": "2026-05",
    }
    data.update(over)
    return FindingDraft.model_validate(data)

def test_draft_forbids_provenance_fields():
    with pytest.raises(ValidationError):
        FindingDraft.model_validate({**_draft().model_dump(), "capturedAt": "2026-06-12"})

def test_stamping_sets_provenance_from_caller():
    f = draft_to_finding(_draft(), doc_id="doc-1", n=3, as_of="2026-06",
                         captured_at="2026-06-12T00:00:00Z", extraction_model="claude-opus-4-8")
    assert f.id == "doc-1-3"
    assert f.asOf == "2026-06"
    assert f.capturedAt == "2026-06-12T00:00:00Z"
    assert f.extractionModel == "claude-opus-4-8"
    assert f.schemaVersion == "1.1"
    assert f.polarityDemand == 1 and f.entity == "NVDA"
