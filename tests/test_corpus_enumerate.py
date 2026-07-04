import pytest

from gpu_agent.corpus import CorpusError, enumerate_store
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

# NOTE: this repo's test convention is LOCAL factories per file (no cross-test imports,
# tests/ is not a package). The _store/_f/_seed block below is repeated verbatim in the
# other F62 test files.


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


def test_missing_wiki_dir_is_honest_empty(tmp_path):
    findings, out, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert findings == [] and out == 0 and skipped == []


def test_in_window_findings_returned_sorted(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("b-2", as_of="2026-07-03"), "2026-07-03")
    _seed(store, _f("a-1", as_of="2026-07-02"), "2026-07-02")
    findings, out, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["a-1", "b-2"]   # sorted by (asOf, id)
    assert out == 0 and skipped == []


def test_out_of_window_counted_not_listed(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("old-1", as_of="2026-04-01"), "2026-04-01")
    _seed(store, _f("new-1", as_of="2026-07-02"), "2026-07-02")
    findings, out, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["new-1"]
    assert out == 1


def test_wrong_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("mine-1"), "2026-07-02", category="chips.merchant-gpu")
    _seed(store, _f("theirs-1", entity="OPENAI"), "2026-07-02",
          category="models.frontier-closed")
    findings, _, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [f.id for f in findings] == ["mine-1"]
    assert [(s.id, s.category) for s in skipped] == [("entity:openai", "models.frontier-closed")]


def test_absent_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("nocat-1"), "2026-07-02", category=None)
    findings, _, skipped = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert findings == []
    assert [(s.id, s.category) for s in skipped] == [("entity:nvda", None)]


def test_same_finding_on_two_pages_deduplicated(tmp_path):
    store = _store(tmp_path)
    f = _f("shared-1")
    _seed(store, f, "2026-07-02")
    # observe the SAME finding from a second page without re-appending it
    store.create_page("entity:amd", "entity", "AMD", category="chips.merchant-gpu",
                      as_of="2026-07-02")
    store.append_observation("entity:amd", f.id, as_of="2026-07-02")
    findings, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
    assert [x.id for x in findings] == ["shared-1"]


def test_dangling_observation_fails_loud(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("ok-1"), "2026-07-02")
    (tmp_path / "findings" / "ok-1.json").unlink()   # corrupt the canonical store
    with pytest.raises(CorpusError, match="ok-1"):
        enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", 45)
