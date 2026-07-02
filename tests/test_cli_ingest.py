import json
from gpu_agent.cli import main
from gpu_agent.schema.raw_document import RawDocument

def _blob(url, content="DC revenue grew 8% QoQ."):
    return {"url": url, "entity": "nvidia", "source": "NVIDIA 10-Q", "date": "2026-05", "content": content}

def test_ingest_writes_docs_and_log(tmp_path):
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps({
        "rounds": 2,
        "skipped": ["lead 'amd-rumor' dropped by maxDocuments cap"],
        "blobs": [_blob("https://www.sec.gov/nvda/10q"),
                  _blob("https://www.sec.gov/nvda/10q/#dup"),   # duplicate
                  _blob("https://some-blog.example/post"),
                  {"url": "https://x.example/bad", "entity": "nvidia",
                   "source": "S", "date": "2026-05"}],          # malformed (no content)
    }), "utf-8")
    out = tmp_path / "docs"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out),
               "--primary-sources", "sec.gov"])
    assert rc == 0

    doc_files = sorted(p for p in out.glob("*.json") if p.name != "gather-log.json")
    assert len(doc_files) == 2                                  # 1 dup collapsed, 1 dropped
    for p in doc_files:                                         # every written doc validates
        RawDocument.model_validate(json.loads(p.read_text("utf-8")))

    log = json.loads((out / "gather-log.json").read_text("utf-8"))
    assert log["rounds"] == 2
    assert log["documents"] == 2
    assert log["primary"] == 1 and log["secondary"] == 1
    assert log["duplicates"] == 1
    assert len(log["dropped"]) == 1 and log["dropped"][0]["index"] == 3
    assert log["skipped"] == ["lead 'amd-rumor' dropped by maxDocuments cap"]

def test_ingest_accepts_bare_array(tmp_path):
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("https://www.sec.gov/a")]), "utf-8")
    out = tmp_path / "docs"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out), "--primary-sources", "sec.gov"])
    assert rc == 0
    log = json.loads((out / "gather-log.json").read_text("utf-8"))
    assert log["rounds"] == 0 and log["documents"] == 1 and log["skipped"] == []

def test_extract_ignores_gather_log(tmp_path):
    """Regression: extract --docs on an ingest output folder must skip gather-log.json."""
    # 1) run ingest so gather-log.json lands alongside the RawDocument JSON files
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("https://www.sec.gov/nvda/10q")]), "utf-8")
    docs = tmp_path / "docs"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(docs), "--primary-sources", "sec.gov"])
    assert rc == 0
    assert (docs / "gather-log.json").exists(), "ingest must have written gather-log.json"

    # 2) build a recorded-extract response (one valid FindingDraft that passes the gate)
    draft = {
        "statement": "NVIDIA DC revenue growth slope flattened to ~8% QoQ.",
        "kind": "observed", "value": None, "trend": "flat",
        "why": "Blackwell ramp digesting.",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed",
                   "mechanism": "slope flattening caps DMI"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "https://www.sec.gov/nvda/10q",
                      "date": "2026-05-01", "excerpt": "grew 8% QoQ"}],
        "reasoning": None, "confidence": {"level": "high", "basis": "primary filing"},
        "dispersion": None, "indicatorId": "D2",
        "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
        "entity": "nvidia", "observedAt": "2026-05-01",
    }
    rec = tmp_path / "rec-extract.json"
    rec.write_text(json.dumps([json.dumps({"drafts": [draft]})]), "utf-8")

    # 3) run extract -- gather-log.json must be silently skipped, not crash as a bad RawDocument
    out_file = tmp_path / "out.json"
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z",
               "--recorded", str(rec), "--out", str(out_file)])
    assert rc == 0, "extract crashed (likely tried to parse gather-log.json as a RawDocument)"
    findings = json.loads(out_file.read_text("utf-8"))
    assert len(findings) >= 1, "extract produced no findings"
