import pytest
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.gathering.ingest import normalize_documents

PRIMARY = ["sec.gov", "investor.nvidia.com"]

def _blob(url="https://www.sec.gov/nvda/10q", entity="nvidia",
          source="NVIDIA 10-Q", date="2026-05", content="DC revenue grew 8% QoQ."):
    return {"url": url, "entity": entity, "source": source, "date": date, "content": content}

def test_valid_blob_becomes_validated_rawdocument():
    out = normalize_documents([_blob()], primary_sources=PRIMARY)
    assert len(out.documents) == 1
    doc = out.documents[0]
    assert isinstance(doc, RawDocument)
    assert doc.url == "https://www.sec.gov/nvda/10q"
    assert doc.entity == "nvidia"
    assert doc.content == "DC revenue grew 8% QoQ."

def test_id_is_deterministic_and_filename_safe():
    a = normalize_documents([_blob()], primary_sources=PRIMARY).documents[0]
    b = normalize_documents([_blob()], primary_sources=PRIMARY).documents[0]
    assert a.id == b.id                         # stable across runs (pure, hash-based)
    assert a.id and all(c.isalnum() or c == "-" for c in a.id)  # safe for a filename

def test_sec_gov_is_primary_subdomain_too():
    out = normalize_documents(
        [_blob(url="https://www.sec.gov/x"), _blob(url="https://investor.nvidia.com/y")],
        primary_sources=PRIMARY)
    assert all(d.tier == "primary" for d in out.documents)

def test_open_web_is_secondary():
    out = normalize_documents([_blob(url="https://some-blog.example/post")], primary_sources=PRIMARY)
    assert out.documents[0].tier == "secondary"

def test_duplicate_urls_collapse_and_are_counted():
    # same page, differing only by trailing slash + fragment -> one document, one duplicate
    blobs = [_blob(url="https://www.sec.gov/nvda/10q"),
             _blob(url="https://www.sec.gov/nvda/10q/#section2")]
    out = normalize_documents(blobs, primary_sources=PRIMARY)
    assert len(out.documents) == 1
    assert out.duplicates == 1

def test_malformed_blob_is_dropped_with_reason():
    bad = {"url": "https://x.example/a", "entity": "nvidia", "source": "S", "date": "2026-05"}  # no content
    out = normalize_documents([bad], primary_sources=PRIMARY)
    assert out.documents == []
    assert len(out.dropped) == 1
    assert out.dropped[0].index == 0
    assert "content" in out.dropped[0].reason

def test_empty_input_is_empty_outcome():
    out = normalize_documents([], primary_sources=PRIMARY)
    assert out.documents == [] and out.dropped == [] and out.duplicates == 0
