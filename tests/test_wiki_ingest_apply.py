import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import apply_enrichment, route_findings, IngestResult, PageEnrichment
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def _seeded(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    return ws


def _enrich(**kw):
    base = dict(pageId="entity:nvda", bodyMarkdown="## NVDA\nDC up [f-1].\n",
                state="accelerating", trajectory="steady -> accelerating", salience=0.8)
    base.update(kw)
    return IngestResult(pages=[PageEnrichment(**base)])


def test_apply_sets_body_state_and_logs_ingest(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(crossRefs=["entity:amd"]), as_of="2026-06-28")
    page = ws.get_page("entity:nvda")
    assert page.state == "accelerating" and page.salience == 0.8
    assert page.crossRefs == ["entity:amd"]
    assert ws.window("entity:nvda", 0).body == "## NVDA\nDC up [f-1].\n"
    assert [e.kind for e in ws.log.read() if e.kind == "ingest"] == ["ingest"]


def test_apply_records_contradiction_in_ingest_event(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(contradictsThesis=True, contradictionNote="guidance cut"),
                     as_of="2026-06-28")
    ingest = [e for e in ws.log.read() if e.kind == "ingest"][0]
    assert "guidance cut" in ingest.detail


def test_apply_rejects_missing_page(tmp_path):
    ws = _seeded(tmp_path)
    with pytest.raises(Exception):
        apply_enrichment(ws, _enrich(pageId="entity:ghost"), as_of="2026-06-28")


def test_apply_rejects_non_entity_page(tmp_path):
    ws = _seeded(tmp_path)
    with pytest.raises(ValueError):
        apply_enrichment(ws, _enrich(pageId="theme:cowos"), as_of="2026-06-28")


def test_apply_is_idempotent(tmp_path):
    ws = _seeded(tmp_path)
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")
    n = len(ws.log.read())
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")  # re-apply same answer
    assert len(ws.log.read()) == n  # no new state-change or ingest event
