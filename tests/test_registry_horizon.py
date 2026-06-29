import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import (
    IndicatorHorizons, HorizonError, CADENCES, HORIZONS,
)

REG = pathlib.Path("registry/indicators.json")


def test_load_reads_cadence_horizon_map():
    h = IndicatorHorizons.load(REG)
    assert h.get("rpoBacklog") == {"cadence": "quarterly", "horizon": "leading"}


def test_cadence_and_horizon_return_values():
    h = IndicatorHorizons.load(REG)
    assert h.cadence("gpuSpotPrice") == "daily"
    assert h.horizon("leadTimes") == "coincident"
    assert h.horizon("vendorRevenueGuidance") == "leading"


def test_get_returns_none_for_untagged():
    h = IndicatorHorizons.load(REG)
    assert h.get("does-not-exist") is None


def test_cadence_untagged_raises():
    h = IndicatorHorizons.load(REG)
    with pytest.raises(HorizonError):
        h.cadence("does-not-exist")


def test_invalid_cadence_raises():
    h = IndicatorHorizons({"x": {"cadence": "hourly", "horizon": "leading"}})
    with pytest.raises(HorizonError):
        h.cadence("x")


def test_invalid_horizon_raises():
    h = IndicatorHorizons({"x": {"cadence": "daily", "horizon": "sideways"}})
    with pytest.raises(HorizonError):
        h.horizon("x")


def test_validate_coverage_passes_for_real_registry():
    reg = IndicatorRegistry.load(REG)
    h = IndicatorHorizons.load(REG)
    h.validate_coverage(reg)  # must not raise


def test_validate_coverage_fails_on_untagged_scoring_indicator():
    reg = IndicatorRegistry({"foo": {"dimension": "momentum", "weight": 0.1, "scoring": True}})
    h = IndicatorHorizons({})  # foo is a scoring indicator with no tag
    with pytest.raises(HorizonError):
        h.validate_coverage(reg)


def test_validate_coverage_fails_on_orphan_tag():
    reg = IndicatorRegistry({"foo": {"dimension": "momentum", "weight": 0.1, "scoring": True}})
    h = IndicatorHorizons({
        "foo": {"cadence": "quarterly", "horizon": "leading"},
        "ghost": {"cadence": "daily", "horizon": "leading"},  # not a registered indicator
    })
    with pytest.raises(HorizonError):
        h.validate_coverage(reg)


def test_all_real_indicators_tagged_with_valid_values():
    reg = IndicatorRegistry.load(REG)
    h = IndicatorHorizons.load(REG)
    for ind_id in reg.indicators:
        tag = h.get(ind_id)
        assert tag is not None, f"{ind_id} is untagged"
        assert tag["cadence"] in CADENCES
        assert tag["horizon"] in HORIZONS
