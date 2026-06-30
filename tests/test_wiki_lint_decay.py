import math
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import (half_life, quiet_age, decay, effective_salience,
                                 DEFAULT_LINT_CONFIG)
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId="D2"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


_HZ = IndicatorHorizons({
    "daily-coin": {"cadence": "daily", "horizon": "coincident"},
    "daily-lead": {"cadence": "daily", "horizon": "leading"},
    "quarterly-coin": {"cadence": "quarterly", "horizon": "coincident"},
})


def test_half_life_daily_short():
    hl, untagged = half_life([_f("f1", "A", "daily-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 1 and untagged == []


def test_half_life_quarterly_long():
    hl, _ = half_life([_f("f1", "A", "quarterly-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 6


def test_half_life_leading_floor():
    # daily would be 1, but a leading-horizon signal is floored at H_med (3)
    hl, _ = half_life([_f("f1", "A", "daily-lead")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 3


def test_half_life_longest_class_wins():
    hl, _ = half_life([_f("f1", "A", "daily-coin"), _f("f2", "A", "quarterly-coin")],
                      _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 6


def test_half_life_untagged_default_and_logged():
    hl, untagged = half_life([_f("f1", "A", "ghost-ind")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 3 and untagged == ["ghost-ind"]


def test_quiet_age_fresh_is_zero(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-06")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0


def test_quiet_age_counts_intervening_cycles(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    # two later cycles touch OTHER pages -> distinct asOf cycles 2026-05, 2026-06
    ws.create_page("entity:b", "entity", "B", as_of="2026-05")
    ws.findings.append(_f("f2", "B"))
    ws.append_observation("entity:b", "f2", as_of="2026-05")
    ws.findings.append(_f("f3", "B"))
    ws.append_observation("entity:b", "f3", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 2


def test_quiet_age_material_update_resets(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    ws.create_page("entity:b", "entity", "B", as_of="2026-05")
    ws.findings.append(_f("f2", "B"))
    ws.append_observation("entity:b", "f2", as_of="2026-05")
    # a gets a NEW observation at 2026-06 -> quietness resets
    ws.findings.append(_f("f3", "A"))
    ws.append_observation("entity:a", "f3", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0


def test_decay_and_effective_salience():
    assert math.isclose(decay(2, 3), 0.5 ** (2 / 3))
    assert math.isclose(decay(0, 6), 1.0)
    assert math.isclose(effective_salience(0.8, 1, 1), 0.4)
