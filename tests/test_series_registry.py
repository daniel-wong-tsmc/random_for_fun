from gpu_agent.series_registry import SeriesRegistry

PATH = "registry/series-indicators.json"


def test_six_series_registered():
    reg = SeriesRegistry.load(PATH)
    assert set(reg.specs) == {
        "pkgCapacityOrderSpread", "hbmSupplyCapex", "hyperscalerCapexRevision",
        "odmMonthlyAiRevenue", "tokenEconomics", "marginalBuyerFinancing"}


def test_estimate_grade_marked_for_d4_x5():
    reg = SeriesRegistry.load(PATH)
    assert reg.resolve("tokenEconomics").estimateGrade is True
    assert reg.resolve("marginalBuyerFinancing").estimateGrade is True
    assert reg.resolve("odmMonthlyAiRevenue").estimateGrade is False


def test_supply_side_polarity():
    reg = SeriesRegistry.load(PATH)
    assert reg.resolve("pkgCapacityOrderSpread").side == "supply"
    assert reg.resolve("pkgCapacityOrderSpread").polaritySupply == -1


def test_unregistered_series_raises():
    import pytest
    reg = SeriesRegistry.load(PATH)
    with pytest.raises(KeyError):
        reg.resolve("nope")
