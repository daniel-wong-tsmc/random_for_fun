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
from gpu_agent.wiki.lifecycle import corroboration
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence, Value


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, *, indicatorId="D2", asOf="2026-06", evidence=None, value=None):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=evidence or [], value=value,
        confidence=Confidence(level="medium", basis="b"), asOf=asOf,
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


def test_gate_rejects_fabricated_number_that_is_substring_of_a_date(tmp_path):
    # Merge-review reproduction: with substring containment, a fabricated "20" passed because
    # "20" is a substring of the evidence date "2026-06-15". Token equality must reject it.
    ws = _store(tmp_path)
    ev = [Evidence(source="10-Q", url="http://sec/nvda", date="2026-06-15",
                   excerpt="no figures disclosed", tier="primary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    result = _enrich(bodyMarkdown="## NVDA\nGained 20 million new customers [f-1].\n")
    with pytest.raises(EnrichmentGateError) as ei:
        apply_enrichment(ws, result, as_of="2026-06-28")
    assert any("uncited number 20" in v for v in ei.value.violations)


def test_gate_allows_large_value_number_by_token_equality(tmp_path):
    # value.number=75200000000.0: f"{v:g}" degrades to "7.52e+10", so the integral rendering
    # str(int(v)) must be in the corpus for the body's "75200000000" to match exactly.
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", value=Value(number=75200000000.0, unit="USD"))],
                   as_of="2026-06-28")
    result = _enrich(bodyMarkdown="## NVDA\nRevenue hit 75200000000 [f-1].\n")
    apply_enrichment(ws, result, as_of="2026-06-28")
    assert "75200000000" in ws.window("entity:nvda", 0).body


def test_gate_allows_honest_date_component_token(tmp_path):
    # "2026" is an honest token of the evidence date "2026-06-15" and must still pass.
    ws = _store(tmp_path)
    ev = [Evidence(source="10-Q", url="http://sec/nvda", date="2026-06-15",
                   excerpt="no figures disclosed", tier="primary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    apply_enrichment(ws, _enrich(bodyMarkdown="## NVDA\nOutlook firm into 2026 [f-1].\n"),
                     as_of="2026-06-28")
    assert "2026" in ws.window("entity:nvda", 0).body


# ---------------------------------------------------------------------------
# Task 3 (F13-E): ingest events keyed per run; asOf grain validated
# ---------------------------------------------------------------------------

def test_apply_enrichment_rejects_invalid_asof_grain(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    with pytest.raises(ValueError, match="invalid asOf grain"):
        apply_enrichment(ws, _enrich(), as_of="June 2026")


def test_route_findings_rejects_invalid_asof_grain(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(ValueError, match="invalid asOf grain"):
        route_findings(ws, [_f("f-1", "NVDA")], as_of="June 2026")


def test_two_different_enrichments_same_asof_both_logged(tmp_path):
    # Different CONTENT (contradiction present vs. not) -> different detail -> both logged, even
    # though both calls share the same asOf.
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    apply_enrichment(ws, _enrich(bodyMarkdown="## NVDA\nDC up [f-1].\n"), as_of="2026-06-28")
    apply_enrichment(ws, _enrich(bodyMarkdown="## NVDA\nDC up [f-1].\n",
                                 contradictsThesis=True, contradictionNote="guidance cut"),
                     as_of="2026-06-28")
    ingest_events = [e for e in ws.log.read() if e.kind == "ingest"]
    assert len(ingest_events) == 2


def test_same_enrichment_applied_twice_same_asof_is_idempotent(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")
    apply_enrichment(ws, _enrich(), as_of="2026-06-28")  # identical re-apply
    ingest_events = [e for e in ws.log.read() if e.kind == "ingest"]
    assert len(ingest_events) == 1


def test_lint_aggregates_contradictions_from_both_same_asof_ingest_events(tmp_path):
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.registry.horizon import IndicatorHorizons
    from gpu_agent.wiki.lint import lint
    reg = IndicatorRegistry.load("registry/indicators.json")
    hz = IndicatorHorizons.load("registry/indicators.json")
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA"), _f("f-2", "AMD")], as_of="2026-06-28")
    apply_enrichment(ws, _enrich(pageId="entity:nvda",
                                 bodyMarkdown="## NVDA\nDC up [f-1].\n",
                                 contradictsThesis=True, contradictionNote="guidance cut"),
                     as_of="2026-06-28")
    apply_enrichment(ws, _enrich(pageId="entity:amd",
                                 bodyMarkdown="## AMD\nShare up [f-2].\n",
                                 contradictsThesis=True, contradictionNote="share loss"),
                     as_of="2026-06-28")
    report = lint(ws, as_of="2026-06-28", registry=reg, horizons=hz)
    contra_ids = {c.pageId for c in report.health.contradictions}
    assert contra_ids == {"entity:nvda", "entity:amd"}


# ---------------------------------------------------------------------------
# Task 4 (F30, F31): promotions logged; corroboration keyed by publisher domain
# ---------------------------------------------------------------------------

def test_update_header_logs_header_change_event(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28")
    ws.update_header("entity:nvda", as_of="2026-06-29", status="registered")
    events = [e for e in ws.log.read() if e.kind == "header-change"]
    assert len(events) == 1
    assert events[0].detail == "status: provisional -> registered"
    assert events[0].pageId == "entity:nvda"


def test_update_header_unchanged_value_logs_nothing(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28", category="chips")
    ws.update_header("entity:nvda", as_of="2026-06-29", category="chips")  # same value
    events = [e for e in ws.log.read() if e.kind == "header-change"]
    assert events == []


def test_corroboration_same_publisher_domain_counts_once(tmp_path):
    ws = _store(tmp_path)
    ev = [Evidence(source="NVIDIA Newsroom", url="https://nvidianews.nvidia.com/a",
                   date="2026-06", excerpt="e", tier="secondary"),
          Evidence(source="NVIDIA press release", url="https://nvidianews.nvidia.com/b",
                   date="2026-06", excerpt="e", tier="secondary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    assert corroboration(ws, "entity:nvda") == 1


def test_corroboration_www_prefix_stripped_and_distinct_domains_counted(tmp_path):
    ws = _store(tmp_path)
    # distinct bodies per citation: this test pins netloc-keyed distinctness (www stripping),
    # not the F72 near-dup content collapse — identical dummy bodies would collapse spuriously.
    ev1 = [Evidence(source="s1", url="https://www.example.com/a",
                    date="2026-06", excerpt="body-a", tier="secondary")]
    ev2 = [Evidence(source="s2", url="https://example.com/b",
                    date="2026-06", excerpt="body-b", tier="secondary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev1)], as_of="2026-06-28")
    route_findings(ws, [_f("f-2", "NVDA", evidence=ev2)], as_of="2026-06-28")
    assert corroboration(ws, "entity:nvda") == 1  # www.example.com == example.com

    ev3 = [Evidence(source="s3", url="https://other.org/c",
                    date="2026-06", excerpt="body-c", tier="secondary")]
    route_findings(ws, [_f("f-3", "NVDA", evidence=ev3)], as_of="2026-06-28")
    assert corroboration(ws, "entity:nvda") == 2  # example.com, other.org


def test_corroboration_empty_netloc_falls_back_to_source(tmp_path):
    ws = _store(tmp_path)
    ev = [Evidence(source="Analyst Call", url="not-a-url",
                   date="2026-06", excerpt="e", tier="secondary")]
    route_findings(ws, [_f("f-1", "NVDA", evidence=ev)], as_of="2026-06-28")
    assert corroboration(ws, "entity:nvda") == 1


# ---------------------------------------------------------------------------
# Task 5 (F32): read paths don't write; provenance events don't age pages
# ---------------------------------------------------------------------------

def _reg_hz():
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.registry.horizon import IndicatorHorizons
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def test_lint_record_false_leaves_log_byte_identical(tmp_path):
    from gpu_agent.wiki.lint import lint
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    log_len_before = len(ws.log.read())
    lint(ws, as_of="2026-06-28", registry=reg, horizons=hz, record=False)
    assert len(ws.log.read()) == log_len_before


def test_lint_record_true_appends_exactly_one_lint_event_per_asof(tmp_path):
    from gpu_agent.wiki.lint import lint
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    lint(ws, as_of="2026-06-28", registry=reg, horizons=hz, record=True)
    lint(ws, as_of="2026-06-28", registry=reg, horizons=hz, record=True)  # re-run, idempotent
    lint_events = [e for e in ws.log.read() if e.kind == "lint"]
    assert len(lint_events) == 1


def test_quiet_age_lint_event_mints_no_cycle(tmp_path):
    from gpu_agent.wiki.lint import lint, quiet_age
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    ws.create_page("entity:x", "entity", "X", as_of="2026-06-01")
    lint(ws, as_of="2026-06-02", registry=reg, horizons=hz, record=True)  # only a "lint" event lands at 06-02
    assert quiet_age(ws, "entity:x", "2026-06-02") == 0


def test_quiet_age_ingest_event_mints_a_cycle(tmp_path):
    from gpu_agent.wiki.lint import quiet_age
    ws = _store(tmp_path)
    ws.create_page("entity:x", "entity", "X", as_of="2026-06-01")
    ws.log.append(asOf="2026-06-02", kind="ingest", detail="enriched 0 page(s)")
    assert quiet_age(ws, "entity:x", "2026-06-02") == 1


# ---------------------------------------------------------------------------
# Task 6 (F22-E): lint surfaces what it used to swallow
# ---------------------------------------------------------------------------

def test_lint_health_surfaces_missing_findings(tmp_path):
    from gpu_agent.wiki.lint import lint
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    ws.findings.append(_f("f-ghost", "NVDA"))
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-28")
    ws.append_observation("entity:nvda", "f-ghost", as_of="2026-06-28")
    # Simulate a dangling observation reference (the finding was removed from the canonical
    # FindingStore out from under the wiki) - the store API itself never deletes gated findings,
    # so we reach under it to recreate the scenario _findings_for used to swallow silently.
    (tmp_path / "findings" / "f-ghost.json").unlink()
    report = lint(ws, as_of="2026-06-28", registry=reg, horizons=hz)
    assert report.health.missingFindings == ["f-ghost"]


def test_lint_health_surfaces_untagged_indicators(tmp_path):
    from gpu_agent.wiki.lint import lint
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", indicatorId="totally-untagged-indicator-xyz")],
                   as_of="2026-06-28")
    report = lint(ws, as_of="2026-06-28", registry=reg, horizons=hz)
    assert "totally-untagged-indicator-xyz" in report.health.untaggedIndicators


def test_lint_health_missing_and_untagged_empty_on_clean_store(tmp_path):
    from gpu_agent.wiki.lint import lint
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA", indicatorId="rpoBacklog")], as_of="2026-06-28")
    report = lint(ws, as_of="2026-06-28", registry=reg, horizons=hz)
    assert report.health.missingFindings == []
    assert report.health.untaggedIndicators == []
