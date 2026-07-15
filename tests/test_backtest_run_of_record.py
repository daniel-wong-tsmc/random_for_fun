"""F79 G2 disposition (user-approved, interactive, 2026-07-13): OPTION B — the
ground-truth event list is amended with three documented 2025 episodes, and the SAME
frozen run of record is re-scored. Zero re-tuning, zero parameter changes, zero new
runs: this file pins BOTH the frozen alert stream (determinism guard — the walk must
keep reproducing the run of record byte-for-value) AND the re-scored verdict.

Motivated-reasoning mitigation (recorded here and in the migration note): the run was
frozen and committed BEFORE the amendment; each amended event carries independent
documentation from the G1-approved store (captured before the backtest existed); the
amendment is user-signed; 2024-11 stays counted as a genuine false alarm — the known
noise rate.
"""
from __future__ import annotations
import pytest
from gpu_agent import backtest as bt
from gpu_agent.series_registry import SeriesRegistry

REGISTRY = "registry/series-indicators.json"
STORE = "store/series"

# The frozen run of record (2026-07-13, committed at fcc93ba): raw orange+ episode
# start months. Any drift here means the walk no longer reproduces the frozen run —
# that is a regression (or a store revision), never something to re-pin silently.
FROZEN_EPISODES = ["2023-06", "2024-01", "2024-03", "2024-05",
                   "2024-11", "2025-03", "2025-07", "2025-11"]


@pytest.fixture(scope="module")
def result():
    reg = SeriesRegistry.load(REGISTRY)
    return bt.run_backtest(reg, STORE, start="2023-01", end="2025-12")


def test_amended_ground_truth_is_named_turns_plus_three_signed_events():
    ids = [t.id for t in bt.GROUND_TRUTH]
    assert ids == ["h100-crunch-onset", "cowos-bottleneck", "hbm-squeeze",
                   "financing-squeeze-2025-03", "re-tightening-2025-07",
                   "credit-stress-2025-11"]
    months = {t.id: t.turnMonth for t in bt.AMENDED_EVENTS_2026_07_13}
    assert months == {"financing-squeeze-2025-03": "2025-03",
                      "re-tightening-2025-07": "2025-07",
                      "credit-stress-2025-11": "2025-11"}


def test_walk_reproduces_the_frozen_run(result):
    assert bt._episodes(result) == FROZEN_EPISODES


def test_rescored_verdict_passes_the_bar(result):
    v = bt.evaluate(result)   # default = the amended GROUND_TRUTH
    # recall clause: the three ORIGINAL named turns, caught with >= 1 quarter lead
    caught = {c.turnId: c.leadMonths for c in v.catches}
    assert caught == {"h100-crunch-onset": 3, "cowos-bottleneck": 6, "hbm-squeeze": 9}
    # the three amended events were detected concurrently (lead 0) — 6/6 ground-truth
    # events have an associated episode
    concurrent = {c.turnId: c.leadMonths for c in v.concurrentDetections}
    assert concurrent == {"financing-squeeze-2025-03": 0,
                          "re-tightening-2025-07": 0,
                          "credit-stress-2025-11": 0}
    assert v.missedTurns == []
    # 2024-11 stays a genuine false alarm — the known noise rate: 1 episode / 3 years
    assert v.falseEpisodes == ["2024-11"]
    assert v.maxFalsePerYear == 1
    assert v.passed is True


def test_original_bar_verdict_still_reproducible(result):
    """Provenance: scored against the ORIGINAL three-turn list, the same frozen run
    still FAILS — the amendment changed the ground truth, not the run."""
    v = bt.evaluate(result, turns=bt.NAMED_TURNS)
    assert v.falseEpisodes == ["2024-11", "2025-03", "2025-07", "2025-11"]
    assert v.maxFalsePerYear == 3
    assert v.passed is False
