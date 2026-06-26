import pathlib
from types import SimpleNamespace
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment

REG = pathlib.Path("registry/indicators.json")
TAX = pathlib.Path("docs/taxonomy.json")

def _asg(category, metrics):
    return SimpleNamespace(category=category, metrics=metrics)

def test_clean_assignment_has_no_violations():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["D2", "D6", "S9", "S10", "market-share-pct", "grossMargin"])
    assert validate_assignment(asg, reg, tax) == []

def test_unregistered_metric_is_flagged():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["D2", "totallyMadeUp"])
    violations = validate_assignment(asg, reg, tax)
    assert any("totallyMadeUp" in v for v in violations)

def test_unknown_category_is_flagged():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.not-real", ["D2"])
    violations = validate_assignment(asg, reg, tax)
    assert any("chips.not-real" in v for v in violations)

def test_non_scoring_metric_passes():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["perfPerWatt"])
    assert validate_assignment(asg, reg, tax) == []
