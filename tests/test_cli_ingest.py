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
