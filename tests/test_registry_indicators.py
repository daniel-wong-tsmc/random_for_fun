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
