import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec, RegistryError

REG = pathlib.Path("registry/indicators.json")

def test_resolve_returns_spec_with_dimension():
    reg = IndicatorRegistry.load(REG)
    spec = reg.resolve("market-share-pct")
    assert isinstance(spec, IndicatorSpec)
    assert spec.dimension == "moat"
    assert spec.polarityTrack == "demand"
    assert spec.weight == 0.10
    assert spec.scoring is True

def test_resolve_applies_category_override():
    reg = IndicatorRegistry.load(REG)
    base = reg.resolve("market-share-pct")
    overridden = reg.resolve("market-share-pct", "chips.hbm-memory")
    assert base.weight == 0.10
    assert overridden.weight == 0.04
    assert overridden.dimension == "moat"  # non-overridden fields preserved

def test_resolve_unknown_indicator_raises():
    reg = IndicatorRegistry.load(REG)
    with pytest.raises(RegistryError):
        reg.resolve("does-not-exist")

def test_non_scoring_metric_has_null_dimension():
    reg = IndicatorRegistry.load(REG)
    spec = reg.resolve("perfPerWatt")
    assert spec.scoring is False
    assert spec.dimension is None

def test_strategic_risk_indicators_map_to_dimension_and_are_non_scoring():
    reg = IndicatorRegistry.load(REG)
    for ind in ("exportControlExposure", "customerConcentration"):
        spec = reg.resolve(ind, "chips.merchant-gpu")
        assert spec.dimension == "strategicRisk"
        assert spec.scoring is False

def test_strategic_risk_indicators_pass_validate_against_taxonomy():
    from gpu_agent.registry.structure import Taxonomy
    reg = IndicatorRegistry.load(REG)
    tax = Taxonomy.load(pathlib.Path("docs/taxonomy.json"))
    reg.validate_against(tax)  # must not raise (non-scoring indicators are skipped)

def test_new_in_lane_indicators_resolve():
    reg = IndicatorRegistry.load(REG)
    for ind in ("rpoBacklog", "vendorRevenueGuidance", "leadTimes", "designWins", "gpuSpotPrice"):
        spec = reg.resolve(ind, "chips.merchant-gpu")
        assert isinstance(spec, IndicatorSpec)
        assert spec.id == ind


def test_new_scoring_indicators_have_dimension_and_nonzero_weight():
    reg = IndicatorRegistry.load(REG)
    expected = {
        "rpoBacklog": "momentum",
        "vendorRevenueGuidance": "momentum",
        "leadTimes": "bottleneck",
    }
    for ind, dim in expected.items():
        spec = reg.resolve(ind, "chips.merchant-gpu")
        assert spec.scoring is True
        assert spec.dimension == dim
        assert spec.weight > 0.0


def test_new_overlay_indicators_are_non_scoring():
    reg = IndicatorRegistry.load(REG)
    dw = reg.resolve("designWins", "chips.merchant-gpu")
    assert dw.scoring is False
    assert dw.side == "structural"
    assert dw.dimension == "competitiveStructure"
    sp = reg.resolve("gpuSpotPrice", "chips.merchant-gpu")
    assert sp.scoring is False
    assert sp.side == "price"


def test_new_indicators_pass_validate_against_taxonomy():
    from gpu_agent.registry.structure import Taxonomy
    reg = IndicatorRegistry.load(REG)
    tax = Taxonomy.load(pathlib.Path("docs/taxonomy.json"))
    reg.validate_against(tax)  # must not raise (overlay indicators are skipped)


def test_leading_demand_indicators_reweighted_for_freshness():
    # F60 data-half (Option A): give the forward/leading demand set real weight so
    # fresh, corpus-persisted leading findings move DMI. Weight-only -> no emitted-
    # prompt change -> F6 pin stays green. Invariants (side/dimension/scoring) MUST
    # be preserved: a side change would be Option B and trip the pin.
    reg = IndicatorRegistry.load(REG)
    rpo = reg.resolve("rpoBacklog", "chips.merchant-gpu")
    vrg = reg.resolve("vendorRevenueGuidance", "chips.merchant-gpu")
    assert rpo.weight == 0.14
    assert vrg.weight == 0.16
    assert rpo.scoring is True and rpo.side == "demand" and rpo.dimension == "momentum"
    assert vrg.scoring is True and vrg.side == "demand" and vrg.dimension == "momentum"
