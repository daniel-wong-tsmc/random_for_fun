from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.extraction.prompt import SYSTEM, build_user_prompt

def _doc():
    return RawDocument(id="doc-1", source="NVIDIA 10-Q", url="u", date="2026-05",
                       tier="primary", entity="nvidia", content="DC revenue grew 8% QoQ.")

def test_system_states_doctrine_and_injection_boundary():
    s = SYSTEM.lower()
    assert "json" in s
    assert "data, not instructions" in s          # injection boundary (charter Parts 8/26)
    assert "do not invent" in s or "never invent" in s  # no-invented-numbers doctrine

def test_user_prompt_embeds_content_as_delimited_data():
    p = build_user_prompt(_doc())
    assert "DC revenue grew 8% QoQ." in p
    assert "doc-1" in p and "NVIDIA 10-Q" in p
    assert "<document>" in p and "</document>" in p
