# tests/test_corpus_assemble.py
from gpu_agent.corpus import assemble
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

REGISTRY = IndicatorRegistry.load("registry/indicators.json")
HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"},
                        "rpoBacklog": {"cadence": "quarterly", "horizon": "lagging"}})


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_assemble_empty_store_merged_equals_fresh(tmp_path):
    fresh = [_f("fresh-1", indicatorId="rpoBacklog")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    assert [f.id for f in res.merged] == ["fresh-1"]
    assert [f.id for f in res.dedupedFresh] == ["fresh-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]
    assert res.report.storeIncluded == []
    assert res.report.salienceFloor == 0.1 and res.report.fadedOut == 0
    assert res.report.lifecycleExcluded == []


def test_assemble_store_plus_fresh_new(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", entity="AMD", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    fresh = [_f("fresh-1", entity="NVDA", indicatorId="rpoBacklog", as_of="2026-07")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    assert [f.id for f in res.merged] == ["store-1", "fresh-1"]   # store part first
    assert res.report.storeIncluded == ["store-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]


def test_assemble_fresh_duplicate_dropped_and_reported(tmp_path):
    store = _store(tmp_path)
    prior = _f("store-1", as_of="2026-07-02", observedAt="2026-07-30")
    _seed(store, prior, "2026-07-02")
    # identical statement/trend/magnitude, same (entity, indicator) -> DUPLICATE vs store
    dup = _f("fresh-dup", as_of="2026-07")
    dup = dup.model_copy(update={"statement": prior.statement})
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [dup], REGISTRY, HZ)
    assert [f.id for f in res.merged] == ["store-1"]
    assert res.dedupedFresh == []
    assert [fc.findingId for fc in res.report.freshDuplicate] == ["fresh-dup"]


def test_assemble_id_overlap_keeps_store_copy(tmp_path):
    store = _store(tmp_path)
    f = _f("same-id", as_of="2026-07-02", observedAt="2026-07-30")
    _seed(store, f, "2026-07-02")
    # same id arrives fresh with DIFFERENT statement -> classifier calls it update
    # (changed statement), but the id already exists in the store part: store copy kept
    changed = f.model_copy(update={"statement": "different"})
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [changed], REGISTRY, HZ)
    assert [x.id for x in res.merged] == ["same-id"]
    assert res.merged[0].statement == f.statement          # the store copy
    assert res.report.idOverlaps == ["same-id"]


def test_assemble_deterministic(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    fresh = [_f("fresh-1", indicatorId="rpoBacklog", as_of="2026-07")]
    a = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    b = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    assert a.report.model_dump_json() == b.report.model_dump_json()
    assert [f.id for f in a.merged] == [f.id for f in b.merged]


def test_report_model_shape():
    from gpu_agent.corpus import CorpusReport, CorpusResult
    r = CorpusReport(asOf="2026-07", category="chips.merchant-gpu", salienceFloor=0.1)
    assert r.storeIncluded == [] and r.fadedOut == 0 and r.skippedPages == []
    assert r.lifecycleExcluded == []
    assert r.freshNew == [] and r.freshUpdate == [] and r.freshDuplicate == []
    assert r.idOverlaps == [] and r.coverage == [] and r.notCovered == []
    res = CorpusResult(report=r)
    assert res.merged == [] and res.dedupedFresh == []
