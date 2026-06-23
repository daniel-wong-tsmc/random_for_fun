from gpu_agent.schema.raw_document import RawDocument

def test_raw_document_roundtrips():
    data = {
        "id": "doc-nvda-10q", "source": "NVIDIA 10-Q", "url": "http://sec/nvda",
        "date": "2026-05", "tier": "primary", "entity": "nvidia",
        "content": "Data center revenue growth slowed sequentially...",
    }
    d = RawDocument.model_validate(data)
    assert d.id == "doc-nvda-10q" and d.tier == "primary"
    assert RawDocument.model_validate(d.model_dump()).entity == "nvidia"
