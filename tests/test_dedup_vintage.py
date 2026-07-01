import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.gathering.dedup import (prior_vintage, changed, DEFAULT_DEDUP_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId, *, number=None, magnitude=2, statement="s", trend="flat",
       capturedAt="2026-07-01", observedAt="2026-07"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend=trend, why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        value=(Value(number=number, unit="usd") if number is not None else None),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt=observedAt, capturedAt=capturedAt)


def _seed(store, f, as_of):
    store.create_page(f"entity:{f.entity.lower()}", "entity", f.entity, as_of=as_of) \
        if not _page_exists(store, f.entity) else None
    store.findings.append(f)
    store.append_observation(f"entity:{f.entity.lower()}", f.id, as_of=as_of)


def _page_exists(store, entity):
    from gpu_agent.wiki.store import PageNotFound
    try:
        store.get_page(f"entity:{entity.lower()}")
        return True
    except PageNotFound:
        return False


def test_prior_vintage_none_when_absent(tmp_path):
    store = _store(tmp_path)
    assert prior_vintage(store, "NVDA", "rpoBacklog") is None


def test_prior_vintage_picks_latest(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("f-old", "NVDA", "rpoBacklog", capturedAt="2026-06-01"), "2026-06")
    _seed(store, _f("f-new", "NVDA", "rpoBacklog", capturedAt="2026-07-01"), "2026-07")
    _seed(store, _f("f-other", "NVDA", "leadTimes", capturedAt="2026-07-01"), "2026-07")
    pv = prior_vintage(store, "NVDA", "rpoBacklog")
    assert pv.id == "f-new"  # latest capturedAt for THIS indicator, ignores leadTimes


def test_changed_measured_within_tolerance_is_false():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.015)  # +0.75% < 1%
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is False


def test_changed_measured_beyond_tolerance_is_true():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.35)  # +17.5% > 1%
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is True


def test_changed_magnitude_flip_is_true():
    prior = _f("f0", "AMD", "gpuSpotPrice", number=2.00, magnitude=1)
    fresh = _f("f1", "AMD", "gpuSpotPrice", number=2.00, magnitude=3)
    assert changed(prior, fresh, DEFAULT_DEDUP_CONFIG) is True


def test_changed_qualitative_statement_or_trend():
    prior = _f("f0", "NVDA", "rpoBacklog", statement="Backlog steady", trend="flat")
    same = _f("f1", "NVDA", "rpoBacklog", statement="backlog   steady", trend="flat")  # folds equal
    diff = _f("f2", "NVDA", "rpoBacklog", statement="Backlog steady", trend="rising")
    assert changed(prior, same, DEFAULT_DEDUP_CONFIG) is False
    assert changed(prior, diff, DEFAULT_DEDUP_CONFIG) is True
