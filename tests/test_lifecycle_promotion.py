from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lifecycle import (persistence, corroboration, promotion_candidates,
                                       DEFAULT_LIFECYCLE_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, sources, asOf, capturedAt):
    ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt="e", tier="secondary")
          for s in sources]
    return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                   impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                   value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                   indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
                   magnitude=2, entity=entity, observedAt=asOf, capturedAt=capturedAt, evidence=ev)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_persistence_counts_distinct_cycles(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert persistence(store, "entity:nvda") == 2


def test_corroboration_counts_distinct_sources(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec", "reuters"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert corroboration(store, "entity:nvda") == 2  # {sec, reuters}


def test_promote_when_persist_and_corroborate_met(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    cands = promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG)
    assert [c.pageId for c in cands] == ["entity:nvda"]
    assert cands[0].persistCycles == 2 and cands[0].distinctSources == 2


def test_no_promote_when_one_cycle(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec", "reuters"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # persistence 1 < 2


def test_no_promote_when_one_source(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "AMD", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "AMD", "rpoBacklog", sources=["sec"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # corroboration 1 < 2


def test_registered_page_skipped(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f1", "NVDA", "rpoBacklog", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", "rpoBacklog", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")
    store.update_header("entity:nvda", as_of="2026-07", status="registered")
    assert promotion_candidates(store, DEFAULT_LIFECYCLE_CONFIG) == []  # already registered
