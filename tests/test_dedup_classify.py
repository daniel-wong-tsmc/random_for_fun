from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.gathering.dedup import classify_findings, DEFAULT_DEDUP_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, number=None, magnitude=2, statement="s",
       capturedAt="2026-07-01", evidence=None, side="demand", unit="usd"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=(Value(number=number, unit=unit) if number is not None else None),
        evidence=evidence or [],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side=side, polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


def _ev(source, url, date="2026-07-01", excerpt="e", tier="primary"):
    return Evidence(source=source, url=url, date=date, excerpt=excerpt, tier=tier)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_classify_new_when_no_prior(tmp_path):
    store = _store(tmp_path)
    res = classify_findings([_f("f-1", "NVDA", "rpoBacklog", number=100.0)], store,
                            config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.new] == ["f-1"]
    assert res.update == [] and res.duplicate == []


def test_classify_update_and_duplicate(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-price0", "AMD", "gpuSpotPrice", number=2.00, capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f-rpo0", "NVDA", "rpoBacklog", number=100.0, capturedAt="2026-06-01"), "2026-06")
    res = classify_findings([
        _f("f-price1", "AMD", "gpuSpotPrice", number=2.35, capturedAt="2026-07-01"),   # +17% -> update
        _f("f-rpo1", "NVDA", "rpoBacklog", number=100.5, capturedAt="2026-07-01")],     # +0.5% -> duplicate
        store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.update] == ["f-price1"]
    assert res.update[0].priorFindingId == "f-price0"
    assert [fc.findingId for fc in res.duplicate] == ["f-rpo1"]


def test_classify_intra_batch_collapse(tmp_path):
    store = _store(tmp_path)
    # two fresh findings, same (entity, indicator); the later capturedAt is the representative
    res = classify_findings([
        _f("f-a", "NVDA", "rpoBacklog", number=100.0, capturedAt="2026-07-01"),
        _f("f-b", "NVDA", "rpoBacklog", number=105.0, capturedAt="2026-07-02")],
        store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.new] == ["f-b"]         # latest vintage -> NEW
    assert [fc.findingId for fc in res.duplicate] == ["f-a"]   # superseded by intra-batch latest
    assert "superseded" in res.duplicate[0].detail


def test_classify_idempotent_rerun_all_duplicate(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-0", "INTC", "S10", number=5.0, capturedAt="2026-06-01"), "2026-06")
    res = classify_findings([_f("f-0-again", "INTC", "S10", number=5.0, capturedAt="2026-06-01")],
                            store, config=DEFAULT_DEDUP_CONFIG)
    assert res.new == [] and res.update == []
    assert [fc.verdict for fc in res.duplicate] == ["duplicate"]


def test_classify_counts_cover_input(tmp_path):
    store = _store(tmp_path)
    findings = [_f("f-1", "NVDA", "rpoBacklog", number=1.0),
                _f("f-2", "AMD", "gpuSpotPrice", number=2.0),
                _f("f-3", "INTC", "S10", number=3.0)]
    res = classify_findings(findings, store, config=DEFAULT_DEDUP_CONFIG)
    assert len(res.new) + len(res.update) + len(res.duplicate) == 3


def test_classify_deterministic_order(tmp_path):
    store = _store(tmp_path)
    res = classify_findings([_f("f-z", "ZULU", "S10", number=1.0),
                             _f("f-a", "ALPHA", "rpoBacklog", number=1.0)],
                            store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.entity for fc in res.new] == ["ALPHA", "ZULU"]  # sorted by (entity, indicatorId)


# ── F10: corroboration merge + dispersion instead of recency-collapse ─────────

def test_classify_agreeing_batch_mates_merge_evidence(tmp_path):
    """NVDA D2 $75.2B from doc A (primary) + $75.2B from doc B (secondary), same key:
    outFindings has ONE finding for the key, evidence merged from both, and the mate
    is verdict duplicate with detail 'corroborates <rep.id>'."""
    store = _store(tmp_path)
    res = classify_findings([
        _f("f-a", "NVDA", "D2", number=75.2, capturedAt="2026-07-01",
           evidence=[_ev("NVIDIA 10-Q", "http://sec/a")]),
        _f("f-b", "NVDA", "D2", number=75.2, capturedAt="2026-07-02",
           evidence=[_ev("Analyst note", "http://blog/b")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)

    assert [fc.findingId for fc in res.new] == ["f-b"]   # later capturedAt is representative
    assert len(res.outFindings) == 1
    rep = res.outFindings[0]
    assert rep.id == "f-b"
    assert len(rep.evidence) == 2
    assert rep.dispersion is None

    mate = next(fc for fc in res.duplicate if fc.findingId == "f-a")
    assert mate.verdict == "duplicate"
    assert mate.detail.startswith("corroborates f-b")


def test_classify_conflicting_batch_mates_set_dispersion(tmp_path):
    """Conflicting values ($75.2B vs $80B, beyond rel_tol) are NOT recency-collapsed:
    the representative's dispersion is set and mentions both sources; the superseded
    mate keeps its old 'superseded by intra-batch latest vintage' detail."""
    store = _store(tmp_path)
    res = classify_findings([
        _f("f-a", "NVDA", "D2", number=75.2, capturedAt="2026-07-01",
           evidence=[_ev("NVIDIA 10-Q", "http://sec/a")]),
        _f("f-b", "NVDA", "D2", number=80.0, capturedAt="2026-07-02",
           evidence=[_ev("Analyst note", "http://blog/b")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)

    assert len(res.outFindings) == 1
    rep = res.outFindings[0]
    assert rep.id == "f-b"
    assert rep.dispersion is not None
    assert "NVIDIA 10-Q" in rep.dispersion and "Analyst note" in rep.dispersion

    mate = next(fc for fc in res.duplicate if fc.findingId == "f-a")
    assert mate.detail == "superseded by intra-batch latest vintage"


def test_classify_no_batch_mates_out_findings_unmerged(tmp_path):
    """A singleton finding (no batch-mates) passes through outFindings untouched."""
    store = _store(tmp_path)
    res = classify_findings([_f("f-1", "NVDA", "rpoBacklog", number=100.0,
                                evidence=[_ev("NVIDIA 10-Q", "http://sec/x")])],
                            store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.new] == ["f-1"]
    assert res.outFindings == [res.outFindings[0]]
    assert len(res.outFindings) == 1
    assert res.outFindings[0].id == "f-1"
    assert len(res.outFindings[0].evidence) == 1
    assert res.outFindings[0].dispersion is None


# ── F51: price findings dedup per (entity, indicatorId, publisher, unit) series ────
#
# Non-price findings above are untouched by this change (their key is still
# effectively (entity, indicatorId) — the byte-identical-behavior pin for the
# non-price path is simply that every test above this section still passes).

def test_classify_price_findings_per_publisher_no_collapse(tmp_path):
    """Three merchant-gpu cloud providers quoting the same entity+indicator (D6, GPU
    rental price) are three DIFFERENT series (different publisher domains) — not one
    dispersed record. Empty store -> all three classify NEW, no dispersion at all."""
    store = _store(tmp_path)
    res = classify_findings([
        _f("f-lambda", "NVDA", "D6", number=6.69, side="price", unit="USD_per_gpu_hr",
           evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
        _f("f-coreweave", "NVDA", "D6", number=8.60, side="price", unit="USD_per_gpu_hr",
           evidence=[_ev("CoreWeave", "https://www.coreweave.com/pricing")]),
        _f("f-runpod", "NVDA", "D6", number=5.89, side="price", unit="USD_per_gpu_hr",
           evidence=[_ev("Runpod", "https://www.runpod.io/pricing")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)
    assert sorted(fc.findingId for fc in res.new) == ["f-coreweave", "f-lambda", "f-runpod"]
    assert res.update == [] and res.duplicate == []
    assert len(res.outFindings) == 3
    assert all(f.dispersion is None for f in res.outFindings)


def test_classify_price_same_publisher_same_unit_conflict_sets_dispersion(tmp_path):
    """Two quotes from the SAME publisher+unit series that disagree beyond rel_tol are
    NOT split into separate series by finding id — conflict semantics WITHIN a series are
    unchanged: intra-batch collapse to the latest vintage as representative + dispersion."""
    store = _store(tmp_path)
    res = classify_findings([
        _f("f-a", "NVDA", "D6", number=6.00, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-01", evidence=[_ev("Lambda", "https://lambda.ai/x")]),
        _f("f-b", "NVDA", "D6", number=9.00, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-02", evidence=[_ev("Lambda", "https://lambda.ai/y")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)
    assert len(res.outFindings) == 1
    rep = res.outFindings[0]
    assert rep.id == "f-b"                    # later capturedAt is representative
    assert rep.dispersion is not None
    mate = next(fc for fc in res.duplicate if fc.findingId == "f-a")
    assert mate.detail == "superseded by intra-batch latest vintage"


def test_classify_price_no_evidence_publisher_falls_back_to_empty(tmp_path):
    """A price finding with no evidence at all gets publisher '' (still keyed distinctly
    from a real-publisher series of the same entity/indicator/unit) — nothing silent."""
    store = _store(tmp_path)
    res = classify_findings([
        _f("f-nopub", "NVDA", "D6", number=6.69, side="price", unit="USD_per_gpu_hr",
           evidence=[]),
        _f("f-lambda", "NVDA", "D6", number=6.69, side="price", unit="USD_per_gpu_hr",
           evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)
    assert sorted(fc.findingId for fc in res.new) == ["f-lambda", "f-nopub"]
    assert res.duplicate == []


def test_classify_price_cross_cycle_store_prior_is_series_aware(tmp_path):
    """Merge-review reproduction: the STORE holds only Lambda's D6 series; a cycle-2
    batch quotes Lambda (unchanged), CoreWeave, and Runpod. Before the fix,
    prior_vintage keyed candidates by (entity, indicatorId) alone, so CoreWeave and
    Runpod came back UPDATE with priorFindingId pointing at the LAMBDA finding (wrong
    baseline, wrong provenance). The store comparison is now series-aware for price
    findings: Lambda -> DUPLICATE vs its OWN series' prior; CoreWeave and Runpod have
    no matching (publisher, unit) series in the store -> NEW, no priorFindingId."""
    store = _store(tmp_path)
    _seed(store, _f("f-lambda-0", "NVDA", "D6", number=6.69, side="price",
                    unit="USD_per_gpu_hr", capturedAt="2026-07-01",
                    evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
          "2026-06")
    res = classify_findings([
        _f("f-lambda-1", "NVDA", "D6", number=6.69, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-02", evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
        _f("f-coreweave-1", "NVDA", "D6", number=8.60, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-02", evidence=[_ev("CoreWeave", "https://www.coreweave.com/pricing")]),
        _f("f-runpod-1", "NVDA", "D6", number=5.89, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-02", evidence=[_ev("Runpod", "https://www.runpod.io/pricing")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)
    assert sorted(fc.findingId for fc in res.new) == ["f-coreweave-1", "f-runpod-1"]
    assert all(fc.priorFindingId is None for fc in res.new)
    assert res.update == []
    dup = next(fc for fc in res.duplicate if fc.findingId == "f-lambda-1")
    assert dup.priorFindingId == "f-lambda-0"    # its OWN series' prior, not another provider's
    assert dup.detail == "unchanged within tolerance"
    # the two genuinely-new series flow through outFindings; the unchanged one is folded
    assert sorted(f.id for f in res.outFindings) == ["f-coreweave-1", "f-runpod-1"]


def test_classify_price_cross_cycle_same_series_update(tmp_path):
    """Cross-cycle movement WITHIN one series still classifies UPDATE with correct
    provenance: Lambda 6.69 -> 6.99 (+4.5%, beyond rel_tol 1%) vs Lambda's own prior."""
    store = _store(tmp_path)
    _seed(store, _f("f-lambda-0", "NVDA", "D6", number=6.69, side="price",
                    unit="USD_per_gpu_hr", capturedAt="2026-07-01",
                    evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
          "2026-06")
    res = classify_findings([
        _f("f-lambda-1", "NVDA", "D6", number=6.99, side="price", unit="USD_per_gpu_hr",
           capturedAt="2026-07-02", evidence=[_ev("Lambda", "https://lambda.ai/service/gpu-cloud")]),
    ], store, config=DEFAULT_DEDUP_CONFIG)
    assert [fc.findingId for fc in res.update] == ["f-lambda-1"]
    assert res.update[0].priorFindingId == "f-lambda-0"
    assert "value 6.69 -> 6.99" in res.update[0].detail
    assert res.new == [] and res.duplicate == []
