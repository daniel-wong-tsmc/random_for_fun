import json
import pytest
from gpu_agent.cli import main
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value, Evidence
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings


def _blob(url, content="body", entity="NVDA"):
    return {"url": url, "content": content, "source": "example.com", "date": "2026-07",
            "entity": entity}


def _f(fid, entity, indicatorId, number, capturedAt="2026-07-01", evidence=None):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=Value(number=number, unit="usd"),
        evidence=evidence or [],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


def test_ingest_dedup_store_drops_known_docs(tmp_path, capsys):
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("http://x/a"), _blob("http://x/b", content="two")]), "utf-8")
    store = tmp_path / "store"
    out1 = tmp_path / "out1"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out1),
               "--primary-sources", "sec.gov", "--dedup-store", str(store)])
    assert rc == 0
    log1 = json.loads((out1 / "gather-log.json").read_text("utf-8"))
    assert log1["documents"] == 2 and log1.get("droppedKnown", 0) == 0
    # second run over the SAME blobs -> both already seen -> 0 documents written, 2 droppedKnown
    capsys.readouterr()
    out2 = tmp_path / "out2"
    main(["ingest", "--blobs", str(blobs), "--out", str(out2),
          "--primary-sources", "sec.gov", "--dedup-store", str(store)])
    log2 = json.loads((out2 / "gather-log.json").read_text("utf-8"))
    assert log2["documents"] == 0 and log2["droppedKnown"] == 2


def test_ingest_without_dedup_store_unchanged(tmp_path):
    # the flag is opt-in: absent -> the existing behavior (both docs written), no dedup
    blobs = tmp_path / "blobs.json"
    blobs.write_text(json.dumps([_blob("http://x/a"), _blob("http://x/b", content="two")]), "utf-8")
    out = tmp_path / "out"
    rc = main(["ingest", "--blobs", str(blobs), "--out", str(out), "--primary-sources", "sec.gov"])
    assert rc == 0
    log = json.loads((out / "gather-log.json").read_text("utf-8"))
    assert log["documents"] == 2 and "droppedKnown" not in log


def _seed_store(root):
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    route_findings(store, [_f("f-price0", "AMD", "gpuSpotPrice", 2.00, capturedAt="2026-06-01")],
                   as_of="2026-06")
    return store


def test_wiki_dedup_reports_and_writes_deduped(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_store(root)
    findings = tmp_path / "fresh.json"
    findings.write_text(json.dumps([
        _f("f-price1", "AMD", "gpuSpotPrice", 2.35).model_dump(),   # update
        _f("f-price1b", "AMD", "gpuSpotPrice", 2.34).model_dump(),  # same key -> superseded dup
        _f("f-new", "NVDA", "rpoBacklog", 100.0).model_dump()]),    # new
        "utf-8")
    deduped = tmp_path / "deduped.json"
    rc = main(["wiki-dedup", "--findings", str(findings), "--store", str(root),
               "--as-of", "2026-07", "--out-findings", str(deduped)])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert [fc["findingId"] for fc in report["findingsNew"]] == ["f-new"]
    assert [fc["findingId"] for fc in report["findingsUpdate"]] == ["f-price1"]
    assert {fc["findingId"] for fc in report["findingsDuplicate"]} == {"f-price1b"}
    kept = {d["id"] for d in json.loads(deduped.read_text("utf-8"))}
    assert kept == {"f-new", "f-price1"}  # NEW + UPDATE only


def test_wiki_dedup_out_findings_contains_merged_evidence(tmp_path, capsys):
    """F10: --out-findings writes the merged (corroborated) finding, not the raw rep —
    two agreeing same-key findings in the fresh batch collapse to one with 2 evidence items."""
    root = tmp_path / "store"
    _seed_store(root)
    findings = tmp_path / "fresh.json"
    findings.write_text(json.dumps([
        _f("f-new-a", "NVDA", "rpoBacklog", 100.0, capturedAt="2026-07-01",
           evidence=[Evidence(source="NVIDIA 10-Q", url="http://sec/a", date="2026-07-01",
                              excerpt="e", tier="primary").model_dump()]).model_dump(),
        _f("f-new-b", "NVDA", "rpoBacklog", 100.0, capturedAt="2026-07-02",
           evidence=[Evidence(source="Analyst note", url="http://blog/b", date="2026-07-02",
                              excerpt="e", tier="secondary").model_dump()]).model_dump(),
    ]), "utf-8")
    deduped = tmp_path / "deduped.json"
    rc = main(["wiki-dedup", "--findings", str(findings), "--store", str(root),
               "--as-of", "2026-07", "--out-findings", str(deduped)])
    assert rc == 0
    written = json.loads(deduped.read_text("utf-8"))
    assert len(written) == 1
    assert written[0]["id"] == "f-new-b"
    assert len(written[0]["evidence"]) == 2


def test_wiki_dedup_rerun_all_duplicate(tmp_path, capsys):
    root = tmp_path / "store"
    _seed_store(root)
    findings = tmp_path / "same.json"
    findings.write_text(json.dumps([_f("f-price0-again", "AMD", "gpuSpotPrice", 2.00).model_dump()]),
                        "utf-8")
    main(["wiki-dedup", "--findings", str(findings), "--store", str(root), "--as-of", "2026-07"])
    report = json.loads(capsys.readouterr().out)
    assert report["findingsNew"] == [] and report["findingsUpdate"] == []
    assert len(report["findingsDuplicate"]) == 1
