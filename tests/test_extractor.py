import json
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.extraction.extractor import extract_findings

def _doc():
    return RawDocument(id="doc-1", source="NVIDIA 10-Q", url="u", date="2026-05",
                       tier="primary", entity="nvidia", content="...")

def _good_draft():
    return {"statement": "DC growth flattened", "kind": "measured",
            "value": {"number": 8.0, "unit": "% QoQ"}, "trend": "rising", "why": "digestion",
            "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "caps DMI"},
            "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "8%", "tier": "primary"}],
            "confidence": {"level": "high", "basis": "filing"}, "indicatorId": "D2",
            "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
            "entity": "NVDA", "observedAt": "2026-05-01"}

def _gate_violating_draft():
    # measured but value=None -> check_finding flags "missing value"
    d = _good_draft()
    d["value"] = None
    d["statement"] = "bad measured"
    return d

def _kwargs():
    return dict(as_of="2026-06", captured_at="2026-06-12T00:00:00Z", extraction_model="claude-opus-4-8")

def test_clean_drafts_become_findings():
    client = RecordedClient([json.dumps({"drafts": [_good_draft()]})])
    out = extract_findings(_doc(), client, **_kwargs())
    assert len(out.findings) == 1 and not out.dropped
    assert out.findings[0].id == "doc-1-1"

def test_gate_violating_draft_is_dropped_not_raised():
    client = RecordedClient([json.dumps({"drafts": [_good_draft(), _gate_violating_draft()]})])
    out = extract_findings(_doc(), client, **_kwargs())
    assert len(out.findings) == 1
    assert len(out.dropped) == 1
    assert any("missing value" in v for v in out.dropped[0].violations)
