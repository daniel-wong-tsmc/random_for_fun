"""F24 Seam A: a validated brain answer carrying a registered alias stores the finding
under the canonical id; unregistered names pass through UNCHANGED, flagged on the outcome
(user-approved Q2 2026-07-12). Uses the real repo taxonomy (nvidia/tsmc registered)."""
import json
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.extraction.extractor import extract_findings


def _doc():
    return RawDocument(id="doc-1", source="NVIDIA 10-Q", url="u", date="2026-05",
                       tier="primary", entity="nvidia", content="DC revenue grew 8% QoQ.")


def _draft(entity="NVDA", statement="DC growth flattened"):
    return {"statement": statement, "kind": "measured",
            "value": {"number": 8.0, "unit": "% QoQ"}, "trend": "rising", "why": "digestion",
            "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "caps DMI"},
            "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "8%"}],
            "confidence": {"level": "high", "basis": "filing"}, "indicatorId": "D2",
            "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
            "entity": entity, "observedAt": "2026-05-01"}


def _extract(*drafts):
    client = RecordedClient([json.dumps({"drafts": list(drafts)})])
    return extract_findings(_doc(), client, as_of="2026-06",
                            captured_at="2026-06-12T00:00:00Z",
                            extraction_model="claude-opus-4-8")


def test_registered_alias_stores_under_canonical_id():        # acceptance 2
    out = _extract(_draft(entity="NVDA"))
    assert len(out.findings) == 1 and not out.dropped
    assert out.findings[0].entity == "nvidia"
    assert out.unregisteredEntities == []


def test_canonical_id_passes_untouched():
    out = _extract(_draft(entity="nvidia"))
    assert out.findings[0].entity == "nvidia"
    assert out.unregisteredEntities == []


def test_unregistered_passes_through_unchanged_and_flagged():  # acceptance 4 (outcome half)
    out = _extract(_draft(entity="Super Micro"))
    assert len(out.findings) == 1 and not out.dropped          # NEVER rejected
    assert out.findings[0].entity == "Super Micro"             # NOT rewritten (Q2)
    assert out.unregisteredEntities == ["Super Micro"]


def test_unregistered_names_are_distinct_and_sorted():
    # F24 stage 2: AMD is registered now; the server ODMs stay unregistered by user
    # decision (Option A, 2026-07-13) and are the honest unregistered specimens.
    out = _extract(_draft(entity="Super Micro"),
                   _draft(entity="Quanta", statement="rack ramps"),
                   _draft(entity="Quanta", statement="rack pricing"))
    assert out.unregisteredEntities == ["Quanta", "Super Micro"]


def test_registered_mixed_with_unregistered():
    out = _extract(_draft(entity="NVDA"), _draft(entity="Quanta", statement="rack ramps"))
    assert [f.entity for f in out.findings] == ["nvidia", "Quanta"]
    assert out.unregisteredEntities == ["Quanta"]
