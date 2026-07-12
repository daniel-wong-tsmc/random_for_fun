import json, pathlib
from gpu_agent.cli import main

def _write_doc(d: pathlib.Path):
    d.write_text(json.dumps({
        "id": "doc-1", "source": "NVIDIA 10-Q", "url": "u", "date": "2026-05",
        "tier": "primary", "entity": "nvidia", "content": "DC revenue grew 8% QoQ."}), "utf-8")
    # content contains the draft excerpt "8%"; evidence url == doc url "u"

def _recorded(p: pathlib.Path):
    draft = {"statement": "DC growth", "kind": "measured", "value": {"number": 8.0, "unit": "% QoQ"},
             "trend": "rising", "why": "digestion",
             "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "caps DMI"},
             "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "8%"}],
             "confidence": {"level": "high", "basis": "filing"}, "indicatorId": "D2",
             "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2, "entity": "NVDA", "observedAt": "2026-05-01"}
    p.write_text(json.dumps([json.dumps({"drafts": [draft]})]), "utf-8")

def test_extract_writes_gated_findings(tmp_path):
    docs = tmp_path / "docs"; docs.mkdir(); _write_doc(docs / "doc-1.json")
    rec = tmp_path / "rec.json"; _recorded(rec)
    out = tmp_path / "findings.json"
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--recorded", str(rec), "--out", str(out)])
    assert rc == 0
    findings = json.loads(out.read_text("utf-8"))
    assert len(findings) == 1
    assert findings[0]["id"] == "doc-1-1"
    assert findings[0]["capturedAt"] == "2026-06-12T00:00:00Z"
    assert findings[0]["schemaVersion"] == "1.2"


# --- F24: UNREGISTERED-ENTITY stderr flag line (user-approved Q3 2026-07-12) ---

def _recorded_amd(p: pathlib.Path):
    draft = {"statement": "MI400 ramps", "kind": "measured", "value": {"number": 8.0, "unit": "% QoQ"},
             "trend": "rising", "why": "share gain",
             "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "caps DMI"},
             "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05-01", "excerpt": "8%"}],
             "confidence": {"level": "high", "basis": "filing"}, "indicatorId": "D2",
             "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2, "entity": "AMD", "observedAt": "2026-05-01"}
    p.write_text(json.dumps([json.dumps({"drafts": [draft]})]), "utf-8")


def test_extract_prints_unregistered_entity_line(tmp_path, capsys):
    docs = tmp_path / "docs"; docs.mkdir(); _write_doc(docs / "doc-1.json")
    rec = tmp_path / "rec.json"; _recorded_amd(rec)
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--recorded", str(rec),
               "--out", str(tmp_path / "findings.json")])
    assert rc == 0
    assert "UNREGISTERED-ENTITY 1: AMD" in capsys.readouterr().err


def test_extract_no_unregistered_line_when_all_registered(tmp_path, capsys):
    docs = tmp_path / "docs"; docs.mkdir(); _write_doc(docs / "doc-1.json")
    rec = tmp_path / "rec.json"; _recorded(rec)                 # draft entity NVDA -> registered
    rc = main(["extract", "--docs", str(docs), "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--recorded", str(rec),
               "--out", str(tmp_path / "findings.json")])
    assert rc == 0
    assert "UNREGISTERED-ENTITY" not in capsys.readouterr().err
