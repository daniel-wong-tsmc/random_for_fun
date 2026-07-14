"""F79 Stage 7 — the six SDEWS series are promoted into registry/indicators.json (brain
vocabulary + data-of-record) while registry/series-indicators.json remains the v2
engine's metadata authority. This pins the two files in LOCKSTEP: the shared fields must
agree, so the vocabulary the brain sees can never drift from the weights/polarity the
engine scores. (Divergence would be a silent scoring bug.)
"""
from __future__ import annotations
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.series_registry import SeriesRegistry

SIX = ["pkgCapacityOrderSpread", "hbmSupplyCapex", "hyperscalerCapexRevision",
       "odmMonthlyAiRevenue", "tokenEconomics", "marginalBuyerFinancing"]


def test_six_series_present_in_main_registry_and_scoring():
    reg = IndicatorRegistry.load("registry/indicators.json")
    for iid in SIX:
        spec = reg.resolve(iid, "chips.merchant-gpu")
        assert spec.scoring is True
        assert spec.weight > 0.0
        assert spec.side in ("demand", "supply")


def test_shared_fields_agree_between_the_two_registries():
    main = IndicatorRegistry.load("registry/indicators.json")
    series = SeriesRegistry.load("registry/series-indicators.json")
    for iid in SIX:
        m = main.resolve(iid, "chips.merchant-gpu")
        s = series.resolve(iid)
        assert m.side == s.side, iid
        assert m.weight == s.weight, iid
        assert m.decayLambda == s.decayLambda, iid
        assert m.polarityDemand == s.polarityDemand, iid
        assert m.polaritySupply == s.polaritySupply, iid
        assert m.lifecycle == s.lifecycle, iid
        assert m.unit == s.unit, iid


def test_dual_polarity_and_lifecycle_are_registry_data_not_schema():
    """The F79 fields live on IndicatorSpec (registry), never on the Finding schema."""
    from gpu_agent.registry.indicators import IndicatorSpec
    from gpu_agent.schema.finding import Finding
    assert {"polarityDemand", "polaritySupply", "lifecycle"} <= set(IndicatorSpec.model_fields)
    assert "lifecycle" not in Finding.model_fields   # spec constraint: no schema/* change


def test_promotion_did_not_alter_v1_scoring_of_existing_indicators():
    """The six are NEW ids; no stored finding references them, so v1 DMI/SMI is untouched
    (the full replay pin proves this — this is the fast smoke check)."""
    reg = IndicatorRegistry.load("registry/indicators.json")
    # every pre-F79 scoring indicator keeps polarityDemand/polaritySupply at the default 0
    # (dual polarity is opt-in data on the six only)
    for iid in ("apiArr", "leadTimes", "rpoBacklog"):
        spec = reg.resolve(iid, "chips.merchant-gpu")
        assert spec.polarityDemand == 0 and spec.polaritySupply == 0
