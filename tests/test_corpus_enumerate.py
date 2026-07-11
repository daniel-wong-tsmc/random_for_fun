import pytest

from gpu_agent.corpus import CorpusError, enumerate_store
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

# designWins tagged weekly -> half-life h_med_days (21). At as_of 2026-07 (period end
# 2026-07-31) a weekly fact fades below the 0.1 floor once its observedAt age exceeds ~49 days.
HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}})


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-30"):
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


def test_missing_wiki_dir_is_honest_empty(tmp_path):
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == [] and faded == 0 and skipped == [] and excluded == []


def test_fresh_facts_surface_sorted(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("b-2", as_of="2026-07-03", observedAt="2026-07-29"), "2026-07-03")
    _seed(store, _f("a-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["a-1", "b-2"]   # sorted by (asOf, id)
    assert faded == 0 and skipped == [] and excluded == []


def test_old_content_fades_and_is_counted_not_listed(tmp_path):
    # cycle stamp is recent (asOf 2026-07-02) but the evidence is dated 2026-01-15 (~197 days):
    # under the OLD window it rode forward; under aging it fades below the floor and drops.
    store = _store(tmp_path)
    _seed(store, _f("stale-1", as_of="2026-07-02", observedAt="2026-01-15"), "2026-07-02")
    _seed(store, _f("fresh-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    included, faded, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["fresh-1"]
    assert faded == 1


def test_pruned_page_excluded_whole_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("on-pruned", observedAt="2026-07-30"), "2026-07-02", pid="entity:amd")
    # scored, then lifecycle-floored to 0.0 -> the whole page is a lifecycle exclusion
    store.record_state("entity:amd", as_of="2026-07-02", state="live", trajectory="steady", salience=0.6)
    store.record_state("entity:amd", as_of="2026-07-03", state="live", trajectory="steady", salience=0.0)
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == [] and faded == 0 and skipped == []
    assert [(s.id, s.category) for s in excluded] == [("entity:amd", "chips.merchant-gpu")]


def test_never_scored_page_surfaces_its_fresh_facts(tmp_path):
    # the live-store case: salience 0.0 with no state-change is NOT pruned; intrinsic floors to 0.5.
    store = _store(tmp_path)
    _seed(store, _f("live-1", observedAt="2026-07-30"), "2026-07-02")
    included, faded, _, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["live-1"] and excluded == []


def test_wrong_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("mine-1"), "2026-07-02", category="chips.merchant-gpu")
    _seed(store, _f("theirs-1", entity="OPENAI"), "2026-07-02", category="models.frontier-closed")
    included, _, skipped, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["mine-1"]
    assert [(s.id, s.category) for s in skipped] == [("entity:openai", "models.frontier-closed")]


def test_absent_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("nocat-1"), "2026-07-02", category=None)
    included, _, skipped, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == []
    assert [(s.id, s.category) for s in skipped] == [("entity:nvda", None)]


def test_same_finding_on_two_pages_deduplicated(tmp_path):
    store = _store(tmp_path)
    f = _f("shared-1", observedAt="2026-07-30")
    _seed(store, f, "2026-07-02")
    store.create_page("entity:amd", "entity", "AMD", category="chips.merchant-gpu", as_of="2026-07-02")
    store.append_observation("entity:amd", f.id, as_of="2026-07-02")
    included, _, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [x.id for x in included] == ["shared-1"]


def test_shared_finding_survives_via_most_salient_page(tmp_path):
    # ~60d-old weekly fact: intrinsic 0.5 fades (0.5*0.5**(60/21) ~= 0.069 < 0.1) but a
    # 0.95-salience page keeps it (0.95*0.5**(60/21) ~= 0.131 >= 0.1). The low page sorts
    # FIRST alphabetically — first-page-wins would wrongly fade it (the reviewed defect).
    store = _store(tmp_path)
    f = _f("shared-1", observedAt="2026-06-01")
    _seed(store, f, "2026-07-02", pid="entity:amd")          # sorts first
    store.record_state("entity:amd", as_of="2026-07-02", state="live", trajectory="steady", salience=0.05)
    store.create_page("entity:nvda", "entity", "NVDA", category="chips.merchant-gpu", as_of="2026-07-02")
    store.append_observation("entity:nvda", f.id, as_of="2026-07-02")
    store.record_state("entity:nvda", as_of="2026-07-02", state="live", trajectory="steady", salience=0.95)
    included, faded, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [x.id for x in included] == ["shared-1"]
    assert faded == 0


def test_dangling_observation_fails_loud(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("ok-1", observedAt="2026-07-30"), "2026-07-02")
    (tmp_path / "findings" / "ok-1.json").unlink()   # corrupt the canonical store
    with pytest.raises(CorpusError, match="ok-1"):
        enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
