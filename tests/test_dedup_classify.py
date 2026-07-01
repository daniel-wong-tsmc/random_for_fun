from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.gathering.dedup import classify_findings, DEFAULT_DEDUP_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, number=None, magnitude=2, statement="s",
       capturedAt="2026-07-01"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=(Value(number=number, unit="usd") if number is not None else None),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-07", capturedAt=capturedAt)


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
