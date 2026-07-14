"""F24 stage 2 Part B - the split-page consolidation script (spec 2026-07-13).
Acceptance 3: synthetic-fixture tests cover merge, retire-pointer, conflict rule, and
idempotence. SYNTHETIC ONLY - the live store is never read or written here."""
import pathlib

import pytest

from gpu_agent.corpus import enumerate_store
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.tools.consolidate_entity import (
    ConsolidationConflict, ConsolidationError, consolidate, main, pointer_body,
    retire_state)
from gpu_agent.wiki.store import PageNotFound, WikiStore

HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}})
CAT = "chips.merchant-gpu"
OLD, NEW = "entity:nvda", "entity:nvidia"


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", as_of="2026-07-02", observed_at="2026-07-30"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=[CAT], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observed_at,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId="designWins", side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observed_at,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, pid, title, fid, as_of, entity="NVDA"):
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", title, category=CAT, as_of=as_of)
    f = _f(fid, entity=entity, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def _split(tmp_path):
    """The live-store shape in miniature: an old split page with two observations
    (2026-07-02), a canonical page with one (2026-07-03), no state on either."""
    store = _store(tmp_path)
    _seed(store, OLD, "NVDA", "old-1", "2026-07-02")
    _seed(store, OLD, "NVDA", "old-2", "2026-07-02")
    _seed(store, NEW, "nvidia", "new-1", "2026-07-03")
    return store


def _files(tmp_path):
    """Byte snapshot of every wiki file (pages + log) for idempotence assertions."""
    return {p: p.read_bytes() for p in sorted((tmp_path / "wiki").rglob("*"))
            if p.is_file()}


# ---------------- merge ----------------

def test_moves_old_observations_with_original_vintage_and_provenance(tmp_path):
    store = _split(tmp_path)
    report = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert [(m.findingId, m.asOf) for m in report.moved] == [
        ("old-1", "2026-07-02"), ("old-2", "2026-07-02")]
    obs = store.observations(NEW)
    assert {o.findingId for o in obs} == {"old-1", "old-2", "new-1"}
    # moved copies keep their ORIGINAL asOf and sort into history by vintage
    assert [(o.findingId, o.asOf) for o in obs][:2] == [
        ("old-1", "2026-07-02"), ("old-2", "2026-07-02")]
    moved_events = [e for e in store.log.events_for_page(NEW)
                    if e.kind == "append-observation"
                    and e.detail == f"consolidation: moved from {OLD}"]
    assert {e.findingId for e in moved_events} == {"old-1", "old-2"}
    # append-only: the old page's own history is untouched
    assert {o.findingId for o in store.observations(OLD)} == {"old-1", "old-2"}


def test_shared_finding_is_not_duplicated(tmp_path):
    store = _split(tmp_path)
    store.append_observation(NEW, "old-1", as_of="2026-07-04")  # both pages observe old-1
    report = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert [m.findingId for m in report.moved] == ["old-2"]
    assert report.alreadyPresent == ["old-1"]
    assert [o.findingId for o in store.observations(NEW)].count("old-1") == 1


def test_dangling_observation_fails_loud_before_any_write(tmp_path):
    store = _split(tmp_path)
    # a dangling log ref (no backing finding) - the one way this can exist on disk
    store.log.append(asOf="2026-07-02", kind="append-observation", pageId=OLD,
                     findingId="ghost-1")
    before = _files(tmp_path)
    with pytest.raises(ConsolidationError, match="ghost-1"):
        consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert _files(tmp_path) == before   # plan-first: nothing was written


def test_missing_page_fails_loud(tmp_path):
    store = _split(tmp_path)
    with pytest.raises(PageNotFound):
        consolidate(store, "entity:absent", NEW, as_of="2026-07-13")


# ---------------- retire-pointer ----------------

def test_old_page_retired_with_pointer_and_symmetric_crossrefs(tmp_path):
    store = _split(tmp_path)
    consolidate(store, OLD, NEW, as_of="2026-07-13")
    old = store.get_page(OLD)
    assert old.state == retire_state(NEW) == "retired -> entity:nvidia"
    assert old.salience == 0.0
    assert store.state_history(OLD)          # prune-shaped: floored + has state history
    assert store.window(OLD, 0).body == pointer_body(OLD, NEW, "2026-07-13")
    assert NEW in old.crossRefs
    assert OLD in store.get_page(NEW).crossRefs
    # canonical page keeps its never-scored shape (no state minted on it)
    assert store.state_history(NEW) == []


def test_corpus_stops_double_counting_after_consolidation(tmp_path):
    store = _split(tmp_path)
    inc, _, _, excl = enumerate_store(tmp_path, CAT, "2026-07", HZ)
    assert {f.id for f in inc} == {"old-1", "old-2", "new-1"} and excl == []
    consolidate(store, OLD, NEW, as_of="2026-07-13")
    inc, _, _, excl = enumerate_store(tmp_path, CAT, "2026-07", HZ)
    # same three findings survive - now via the canonical page only; the old page is
    # excluded whole as a lifecycle prune (no lint/corpus special-casing needed)
    assert {f.id for f in inc} == {"old-1", "old-2", "new-1"}
    assert [(s.id, s.category) for s in excl] == [(OLD, CAT)]


# ---------------- conflict rule: latest-vintage-wins ----------------

def test_old_state_wins_by_later_vintage_and_is_applied(tmp_path):
    store = _split(tmp_path)
    store.record_state(NEW, as_of="2026-07-03", state="stable", trajectory="flat",
                       salience=0.4)
    store.record_state(OLD, as_of="2026-07-05", state="expanding", trajectory="up",
                       salience=0.7)
    report = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert report.stateMerge.action == "apply-old"
    assert report.stateMerge.losing and "state='stable'" in report.stateMerge.losing
    page = store.get_page(NEW)
    assert (page.state, page.trajectory, page.salience) == ("expanding", "up", 0.7)
    applied = store.state_history(NEW)[-1]
    assert applied.asOf == "2026-07-05"      # the winner keeps its original vintage
    # the losing canonical value is preserved in the consolidation summary event body
    summary = [e for e in store.log.events_for_page(OLD) if e.kind == "header-change"
               and e.detail.startswith("consolidation:")][-1]
    assert "losing value preserved" in summary.detail
    assert "state='stable'" in summary.detail and "salience=0.4" in summary.detail


def test_canonical_state_wins_by_later_vintage_old_value_preserved(tmp_path):
    store = _split(tmp_path)
    store.record_state(OLD, as_of="2026-07-03", state="expanding", trajectory="up",
                       salience=0.7)
    store.record_state(NEW, as_of="2026-07-05", state="stable", trajectory="flat",
                       salience=0.4)
    report = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert report.stateMerge.action == "keep-canonical"
    page = store.get_page(NEW)
    assert (page.state, page.trajectory, page.salience) == ("stable", "flat", 0.4)
    summary = [e for e in store.log.events_for_page(OLD) if e.kind == "header-change"
               and e.detail.startswith("consolidation:")][-1]
    assert "losing value preserved" in summary.detail
    assert "state='expanding'" in summary.detail and "salience=0.7" in summary.detail


def test_contradictory_states_at_same_vintage_question_stop(tmp_path):
    store = _split(tmp_path)
    store.record_state(OLD, as_of="2026-07-05", state="expanding", trajectory="up",
                       salience=0.7)
    store.record_state(NEW, as_of="2026-07-05", state="contracting", trajectory="down",
                       salience=0.3)
    before = _files(tmp_path)
    with pytest.raises(ConsolidationConflict) as exc:
        consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert "expanding" in str(exc.value) and "contracting" in str(exc.value)  # both shown
    assert _files(tmp_path) == before        # conflict aborts with NOTHING written


def test_no_state_on_either_page_merges_nothing(tmp_path):
    store = _split(tmp_path)
    report = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert report.stateMerge is None
    assert store.get_page(NEW).state == ""


# ---------------- idempotence ----------------

def test_second_run_changes_nothing(tmp_path):
    store = _split(tmp_path)
    store.record_state(OLD, as_of="2026-07-05", state="expanding", trajectory="up",
                       salience=0.7)   # exercise the state-apply path too
    first = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert first.changed
    snap = _files(tmp_path)
    second = consolidate(store, OLD, NEW, as_of="2026-07-13")
    assert second.changed is False
    assert second.moved == [] and second.retired is False
    assert second.pointerBodySet is False and second.crossRefsAdded == []
    assert _files(tmp_path) == snap          # byte-identical: zero writes


# ---------------- CLI + diff artifact ----------------

def test_cli_writes_full_before_after_diff_artifact(tmp_path):
    _split(tmp_path)
    out = tmp_path / "diff.md"
    rc = main(["--store", str(tmp_path), "--old", OLD, "--into", NEW,
               "--as-of", "2026-07-13", "--diff-out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert f"# Entity consolidation diff: {OLD} -> {NEW}" in text
    assert "## Unified diff: entity:nvda" in text
    assert "## Wiki log: appended events" in text
    assert "consolidation: moved from entity:nvda" in text
    assert "## Full page files BEFORE" in text and "## Full page files AFTER" in text
    assert "'pruneShaped': False" in text and "'pruneShaped': True" in text


def test_cli_exits_2_on_conflict_without_writing(tmp_path):
    store = _split(tmp_path)
    store.record_state(OLD, as_of="2026-07-05", state="a", trajectory="t", salience=0.5)
    store.record_state(NEW, as_of="2026-07-05", state="b", trajectory="t", salience=0.5)
    before = _files(tmp_path)
    out = tmp_path / "diff.md"
    rc = main(["--store", str(tmp_path), "--old", OLD, "--into", NEW,
               "--as-of", "2026-07-13", "--diff-out", str(out)])
    assert rc == 2
    assert not out.exists()                  # no artifact for an aborted run
    assert _files(tmp_path) == before
