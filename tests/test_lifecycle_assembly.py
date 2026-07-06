from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lint import StaleEntry
from gpu_agent.wiki.lifecycle import lifecycle, apply_lifecycle, DEFAULT_LIFECYCLE_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, *, sources, asOf, capturedAt):
    ev = [Evidence(source=s, url=f"http://{s}/x", date=asOf, excerpt=f"body:{s}", tier="secondary") for s in sources]
    return Finding(id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
                   impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                   value=None, confidence=Confidence(level="medium", basis="b"), asOf=asOf,
                   indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                   magnitude=2, entity=entity, observedAt=asOf, capturedAt=capturedAt, evidence=ev)


def _seed(store, f, as_of):
    pid = f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _promotable(store):
    # NVDA: 2 cycles, 2 sources -> promotable
    _seed(store, _f("f1", "NVDA", sources=["sec"], asOf="2026-06", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f2", "NVDA", sources=["reuters"], asOf="2026-07", capturedAt="2026-07-01"), "2026-07")


def test_lifecycle_assembles_report(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")  # stale provisional
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)],
                       config=DEFAULT_LIFECYCLE_CONFIG)
    assert [c.pageId for c in report.promotions] == ["entity:nvda"]
    assert [c.pageId for c in report.prunes] == ["entity:amd"]
    assert {q.pageId for q in report.quarantined} == {"entity:nvda", "entity:amd"}


def test_lifecycle_provisional_considered_counts_all(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    report = lifecycle(store, as_of="2026-07", stale=[])
    assert report.provisionalConsidered == 2  # every provisional page examined == len(quarantined)
    assert report.provisionalConsidered == len(report.quarantined)


def test_apply_promotes_and_prunes(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)])
    summary = apply_lifecycle(store, report, as_of="2026-08")
    assert summary.promoted == 1 and summary.pruned == 1
    assert store.get_page("entity:nvda").status == "registered"
    assert store.get_page("entity:amd").salience == 0.0  # floored, non-destructive
    assert store.get_page("entity:amd").state == "slipping"  # state preserved


def test_apply_idempotent(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    store.create_page("entity:amd", "entity", "AMD", as_of="2026-07")
    store.record_state("entity:amd", as_of="2026-07", state="slipping", trajectory="flat", salience=0.5)
    report = lifecycle(store, as_of="2026-07",
                       stale=[StaleEntry(pageId="entity:amd", effectiveSalience=0.04)])
    apply_lifecycle(store, report, as_of="2026-08")
    again = apply_lifecycle(store, report, as_of="2026-09")
    assert again.promoted == 0 and again.pruned == 0  # already registered / already floored


def test_propose_is_read_only(tmp_path):
    store = _store(tmp_path)
    _promotable(store)
    lifecycle(store, as_of="2026-07", stale=[])  # propose only
    assert store.get_page("entity:nvda").status == "provisional"  # NOT mutated
