"""Lane E — wiki integrity (F14, F15, F30, F31, F32, F13-E, F22-E)."""
import re
import pytest
from pydantic import ValidationError
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import (
    apply_enrichment, route_findings, IngestResult, PageEnrichment, INGEST_SYSTEM,
    EnrichmentGateError)
from gpu_agent.wiki.salience import computed_salience
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, *, indicatorId="D2", asOf="2026-06", evidence=None):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=evidence or [], confidence=Confidence(level="medium", basis="b"), asOf=asOf,
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=asOf, capturedAt=f"{asOf}-12")


def _enrich(**kw):
    base = dict(pageId="entity:nvda", bodyMarkdown="## NVDA\nDC up [f-1].\n",
                state="accelerating", trajectory="steady -> accelerating")
    base.update(kw)
    return IngestResult(pages=[PageEnrichment(**base)])


# ---------------------------------------------------------------------------
# Task 1 (F15): salience computed in code; the brain no longer sets it
# ---------------------------------------------------------------------------

def test_computed_salience_single_fresh_secondary_no_contradiction(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28")
    ws.findings.append(_f("f-1", "NVDA"))
    ws.append_observation("entity:nvda", "f-1", as_of="2026-06-28")
    # 0.15 + 0.10*min(1,5) + 0.15*1(fresh) + 0.10*0(primary) + 0.20*0(contra) == 0.40
    got = computed_salience(ws, "entity:nvda", as_of="2026-06-28", contradiction=False)
    assert got == pytest.approx(0.40)


def test_computed_salience_contradiction_primary_and_count_cap(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28")
    primary_ev = [Evidence(source="s", url="http://s/x", date="2026-06-28",
                           excerpt="e", tier="primary")]
    for i in range(6):
        ws.findings.append(_f(f"f-{i}", "NVDA", evidence=primary_ev if i == 0 else []))
        ws.append_observation("entity:nvda", f"f-{i}", as_of="2026-06-28")
    # n_total=6 -> count term capped at min(6,5)=5 -> 0.10*5=0.50
    # fresh=1 (asOf matches) -> 0.15 ; primary=1 (one finding has primary evidence) -> 0.10
    # contradiction=1 -> 0.20
    # 0.15 + 0.50 + 0.15 + 0.10 + 0.20 = 1.10 -> capped at 1.0 by min(1.0, ...)
    got = computed_salience(ws, "entity:nvda", as_of="2026-06-28", contradiction=True)
    assert got == 1.0


def test_computed_salience_everything_maxed_caps_at_one(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28")
    primary_ev = [Evidence(source="s", url="http://s/x", date="2026-06-28",
                           excerpt="e", tier="primary")]
    for i in range(8):
        ws.findings.append(_f(f"f-{i}", "NVDA", evidence=primary_ev))
        ws.append_observation("entity:nvda", f"f-{i}", as_of="2026-06-28")
    got = computed_salience(ws, "entity:nvda", as_of="2026-06-28", contradiction=True)
    assert got == 1.0


def test_page_enrichment_rejects_salience_field_extra_forbid():
    with pytest.raises(ValidationError):
        PageEnrichment(pageId="entity:nvda", bodyMarkdown="b", state="s",
                       trajectory="t", salience=0.9)


def test_apply_enrichment_writes_computed_salience(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")
    # matches rule 1's arithmetic: single fresh secondary observation, no contradiction -> 0.40
    assert ws.get_page("entity:nvda").salience == pytest.approx(0.40)


def test_ingest_system_does_not_mention_salience():
    assert "salience" not in INGEST_SYSTEM.lower()


# ---------------------------------------------------------------------------
# Task 2 (F14): enrichment gate - citations must resolve, numbers must be cited
# ---------------------------------------------------------------------------

def test_gate_rejects_unknown_citation_and_writes_nothing(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    body_before = ws.window("entity:nvda", 0).body
    log_len_before = len(ws.log.read())
    result = _enrich(bodyMarkdown="## NVDA\nSee [no-such-finding].\n")
    with pytest.raises(EnrichmentGateError) as ei:
        apply_enrichment(ws, result, as_of="2026-06-28")
    assert any("entity:nvda" in v and "no-such-finding" in v for v in ei.value.violations)
    assert ws.window("entity:nvda", 0).body == body_before
    assert len(ws.log.read()) == log_len_before


def test_gate_rejects_uncited_number(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")  # plain finding, no matching digits
    result = _enrich(bodyMarkdown="## NVDA\nRevenue $75,200,000,000 rising [f-1].\n")
    with pytest.raises(EnrichmentGateError) as ei:
        apply_enrichment(ws, result, as_of="2026-06-28")
    assert any("uncited number" in v for v in ei.value.violations)


def test_gate_allows_number_cited_via_evidence_excerpt(tmp_path):
    ws = _store(tmp_path)
    ev = [Evidence(source="10-Q", url="http://sec/nvda", date="2026-06",
                   excerpt="revenue reached $75,200,000,000 in the quarter", tier="primary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    result = _enrich(bodyMarkdown="## NVDA\nRevenue $75,200,000,000 rising [f-1].\n")
    apply_enrichment(ws, result, as_of="2026-06-28")
    assert "75,200,000,000" in ws.window("entity:nvda", 0).body


def test_gate_ignores_list_markers_and_matches_year_in_evidence_date(tmp_path):
    ws = _store(tmp_path)
    ev = [Evidence(source="10-Q", url="http://sec/nvda", date="2026-06",
                   excerpt="filed for the period", tier="primary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    body = "## NVDA\n1. Guidance reaffirmed for 2026 [f-1].\n"
    apply_enrichment(ws, _enrich(bodyMarkdown=body), as_of="2026-06-28")
    assert "reaffirmed" in ws.window("entity:nvda", 0).body
