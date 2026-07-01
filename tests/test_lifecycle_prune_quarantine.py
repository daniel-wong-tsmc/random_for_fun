import inspect
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.lint import StaleEntry
from gpu_agent.wiki.lifecycle import prune_candidates, partition_canonical
from gpu_agent.pipeline import build_scorecard


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _page(store, pid, title, *, as_of, status="provisional"):
    store.create_page(pid, pid.split(":")[0], title, as_of=as_of)
    if status == "registered":
        store.update_header(pid, as_of=as_of, status="registered")


def test_prune_provisional_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07")
    prunes = prune_candidates(store, [StaleEntry(pageId="entity:x", effectiveSalience=0.04)])
    assert [p.pageId for p in prunes] == ["entity:x"]
    assert "stale" in prunes[0].reason


def test_no_prune_registered_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07", status="registered")
    prunes = prune_candidates(store, [StaleEntry(pageId="entity:x", effectiveSalience=0.04)])
    assert prunes == []  # registered pages are established coverage, never pruned


def test_no_prune_provisional_not_stale(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:x", "X", as_of="2026-07")
    assert prune_candidates(store, []) == []  # not in the stale list


def test_partition_canonical_splits(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:reg", "Reg", as_of="2026-07", status="registered")
    _page(store, "entity:prov", "Prov", as_of="2026-07")
    registered, provisional = partition_canonical(store.index())
    assert [e.id for e in registered] == ["entity:reg"]
    assert [e.id for e in provisional] == ["entity:prov"]


def test_partition_canonical_all_provisional(tmp_path):
    store = _store(tmp_path)
    _page(store, "entity:a", "A", as_of="2026-07")
    _page(store, "entity:b", "B", as_of="2026-07")
    registered, provisional = partition_canonical(store.index())
    assert registered == []
    assert {e.id for e in provisional} == {"entity:a", "entity:b"}


def test_build_scorecard_takes_no_wiki_input():
    # Quarantine invariant: the canonical scorecard is finding-driven — it takes NO wiki/page/store
    # input, so no page (provisional or registered) can move DMI/SMI. Lock it so a future change
    # cannot silently route page state into scoring.
    params = set(inspect.signature(build_scorecard).parameters)
    assert not (params & {"store", "wiki", "wiki_store", "pages", "page", "provisional", "status"})
