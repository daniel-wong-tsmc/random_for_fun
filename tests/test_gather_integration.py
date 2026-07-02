import json, os, pathlib
import pytest
from gpu_agent.cli import main
from gpu_agent.gathering.ingest import normalize_documents
from gpu_agent.schema.raw_document import RawDocument

BLOBS = "fixtures/gather/blobs-nvda.json"
ASSIGN = "fixtures/asg.chips.merchant-gpu.json"

def _extract_draft():
    # one observed finding, indicatorId D2 -> momentum; primary evidence so high confidence is allowed
    return json.dumps({"drafts": [{
        "statement": "NVIDIA DC revenue growth slope flattened to ~8% QoQ.",
        "kind": "observed", "value": None, "trend": "flat",
        "why": "Blackwell ramp digesting.",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed",
                   "mechanism": "slope flattening caps DMI"},
        "evidence": [{"source": "NVIDIA 10-Q",
                      "url": "https://www.sec.gov/cgi-bin/browse-edgar/nvda-10q-2026q1",
                      "date": "2026-05-01", "excerpt": "grew about 8% sequentially"}],
        "reasoning": None, "confidence": {"level": "high", "basis": "primary filing"},
        "dispersion": None, "indicatorId": "D2",
        "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
        "entity": "nvidia", "observedAt": "2026-05-01"}]})

def _judge(finding_id):
    return json.dumps({"dimensions": {"momentum": {
        "rating": "Strong", "direction": "worsening", "findingIds": [finding_id],
        "rationale": "DC growth solid but decelerating"}},
        "categoryStatus": {"rating": "Strong", "direction": "worsening",
                           "bottleneck": "momentum",
                           "reason": "DC growth solid but decelerating"},
        "narrative": "NVDA demand momentum is strong but decelerating into 2026."})

def test_snapshot_feeds_brain_to_gate_valid_scorecard(tmp_path):
    docs = tmp_path / "docs"
    # 1) gather snapshot -> ingest -> validated RawDocument folder
    rc = main(["ingest", "--blobs", BLOBS, "--out", str(docs), "--primary-sources", "sec.gov"])
    assert rc == 0
    doc_files = [p for p in docs.glob("*.json") if p.name != "gather-log.json"]
    assert len(doc_files) == 1
    doc = RawDocument.model_validate(json.loads(doc_files[0].read_text("utf-8")))
    assert doc.tier == "primary"                       # sec.gov stamped primary
    finding_id = f"{doc.id}-1"                          # extractor stamps {docId}-{n}

    # 2) recorded brain clients (extract draft is id-agnostic; judge must cite the stamped id)
    rec_extract = tmp_path / "rec-extract.json"
    rec_extract.write_text(json.dumps([_extract_draft()]), "utf-8")
    rec_judge = tmp_path / "rec-judge.json"
    rec_judge.write_text(json.dumps([_judge(finding_id)] * 3), "utf-8")

    # 3) unchanged brain: extract -> judge -> score
    store = tmp_path / "store"
    rc = main(["pipeline", "--docs", str(docs), "--assignment", ASSIGN,
               "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
               "--recorded-extract", str(rec_extract), "--recorded-judge", str(rec_judge),
               "--out", str(store)])
    assert rc == 0
    written = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert written, "pipeline wrote no scorecard"
    sc = json.loads(written[0].read_text("utf-8"))
    assert sc["dimensionRatings"]["momentum"]["rating"] == "Strong"
    assert sc["narrative"].startswith("NVDA demand momentum")
    assert sc["demandSupply"]["anchors"]["momentum"] != 0

@pytest.mark.skipif(os.environ.get("GPU_AGENT_LIVE_GATHER") != "1",
                    reason="live gather smoke disabled (set GPU_AGENT_LIVE_GATHER=1)")
def test_live_gather_smoke_ingests_real_blobs():
    # The search+fetch is a Claude Code SESSION capability (the gather-category skill), not a Python
    # call, so this smoke proves the live WIRING: it ingests a real gathered blob snapshot and asserts
    # well-formed RawDocuments. Point GPU_AGENT_GATHER_BLOBS at a snapshot a real gather run produced;
    # the committed fixture is the default so the test is runnable without a network.
    path = os.environ.get("GPU_AGENT_GATHER_BLOBS", BLOBS)
    payload = json.loads(pathlib.Path(path).read_text("utf-8"))
    blobs = payload["blobs"] if isinstance(payload, dict) else payload
    out = normalize_documents(blobs, primary_sources=["sec.gov", "investor.nvidia.com"])
    assert out.documents, "live gather produced no valid documents"
    for d in out.documents:
        RawDocument.model_validate(d.model_dump())   # every gathered doc is schema-valid
