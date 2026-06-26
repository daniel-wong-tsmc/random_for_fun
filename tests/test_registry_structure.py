import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.structure import Taxonomy

TAX = pathlib.Path("docs/taxonomy.json")
REG = pathlib.Path("registry/indicators.json")

def test_taxonomy_exposes_six_dimensions():
    tax = Taxonomy.load(TAX)
    assert tax.dimensions == frozenset(
        {"momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"})

def test_taxonomy_composes_layer_dot_category_ids():
    tax = Taxonomy.load(TAX)
    assert "chips.merchant-gpu" in tax.categories
    assert "chips.hbm-memory" in tax.categories

def test_registry_validates_clean_against_taxonomy():
    reg = IndicatorRegistry.load(REG)
    tax = Taxonomy.load(TAX)
    reg.validate_against(tax)  # must not raise

def test_validate_against_rejects_bad_dimension():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry({"x": {"dimension": "notADimension", "weight": 0.1, "scoring": True}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)

def test_validate_against_rejects_zero_weight_scoring_indicator():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry({"x": {"dimension": "moat", "weight": 0.0, "scoring": True}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)

def test_validate_against_rejects_unknown_override_category():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry(
        {"market-share-pct": {"dimension": "moat", "weight": 0.1, "scoring": True}},
        {"chips.not-a-category": {"market-share-pct": {"weight": 0.2}}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)
