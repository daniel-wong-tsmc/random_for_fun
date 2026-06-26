import pathlib
import pytest
from gpu_agent.registry.structure import Taxonomy

TAX = pathlib.Path("docs/taxonomy.json")

def test_categories_in_layer_returns_sorted_layer_members():
    tax = Taxonomy.load(TAX)
    chips = tax.categories_in_layer("chips")
    assert "chips.merchant-gpu" in chips
    assert "chips.hbm-memory" in chips
    assert all(c.startswith("chips.") for c in chips)
    assert list(chips) == sorted(chips)

def test_all_categories_spans_layers_and_is_unique():
    tax = Taxonomy.load(TAX)
    allc = tax.all_categories()
    assert {"chips.merchant-gpu", "models.frontier-closed", "energy.cooling"} <= set(allc)
    assert len(allc) == len(set(allc))
    assert list(allc) == sorted(allc)

def test_categories_in_layer_unknown_raises():
    tax = Taxonomy.load(TAX)
    with pytest.raises(ValueError):
        tax.categories_in_layer("not-a-layer")
