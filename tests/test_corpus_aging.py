# tests/test_corpus_aging.py — F78 Stage 3 aging primitives.
# Repo convention: LOCAL factories per file (tests/ is not a package).
from gpu_agent.asof import days_between
from gpu_agent.corpus import SALIENCE_FLOOR_DEFAULT, aged_salience, _is_pruned
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.lint import effective_salience
from gpu_agent.wiki.store import WikiStore

WEEKLY = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}})
QUARTERLY = IndicatorHorizons({"designWins": {"cadence": "quarterly", "horizon": "lagging"}})


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07",
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


def test_salience_floor_is_the_wiki_stale_threshold():
    assert SALIENCE_FLOOR_DEFAULT == 0.1


def test_aged_salience_wires_floor_age_and_cadence():
    # unscored page (salience 0.0) -> intrinsic floored to salience_floor (0.5);
    # age = days_between(as_of, observedAt); half-life = weekly -> h_med_days (21).
    f = _f("f1", observedAt="2026-06-01")
    expected = effective_salience(0.5, days_between("2026-07", "2026-06-01"), 21)
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) == expected


def test_aged_salience_uses_page_salience_when_above_floor():
    f = _f("f1", observedAt="2026-07-30")
    expected = effective_salience(0.9, days_between("2026-07", "2026-07-30"), 21)
    assert aged_salience(f, 0.9, "2026-07", WEEKLY) == expected


def test_aged_salience_monotonic_in_age():
    fresh = _f("fresh", observedAt="2026-07-30")
    old = _f("old", observedAt="2026-01-15")
    assert aged_salience(fresh, 0.0, "2026-07", WEEKLY) > aged_salience(old, 0.0, "2026-07", WEEKLY)


def test_aged_salience_quarterly_outlives_weekly():
    # a ~72-day fact: fades under a weekly half-life, survives under a quarterly one.
    f = _f("f1", observedAt="2026-05-20")
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) < SALIENCE_FLOOR_DEFAULT
    assert aged_salience(f, 0.0, "2026-07", QUARTERLY) >= SALIENCE_FLOOR_DEFAULT


def test_aged_salience_clamps_future_observed_at():
    # observedAt after as_of (out-of-order label) clamps age to 0 -> no decay, full intrinsic.
    f = _f("f1", observedAt="2026-09-01")
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) == effective_salience(0.5, 0, 21)


def test_is_pruned_true_only_for_scored_then_floored(tmp_path):
    store = _store(tmp_path)
    store.create_page("entity:a", "entity", "A", category="chips.merchant-gpu", as_of="2026-06")
    # scored, then lifecycle-floored to 0.0 (a real prune) -> excluded
    store.record_state("entity:a", as_of="2026-06", state="live", trajectory="steady", salience=0.6)
    store.record_state("entity:a", as_of="2026-07", state="live", trajectory="steady", salience=0.0)
    assert _is_pruned(store, "entity:a", store.get_page("entity:a")) is True


def test_is_not_pruned_when_never_scored(tmp_path):
    # a never-scored page (salience default 0.0, no state-change) is NOT pruned — the live-store case.
    store = _store(tmp_path)
    store.create_page("entity:b", "entity", "B", category="chips.merchant-gpu", as_of="2026-07")
    assert _is_pruned(store, "entity:b", store.get_page("entity:b")) is False
