import pathlib
import pytest
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan, resolve_scope

TAX = pathlib.Path("docs/taxonomy.json")

def _tax():
    return Taxonomy.load(TAX)

def test_resolve_scope_category():
    assert resolve_scope("category:chips.merchant-gpu", _tax()) == ("chips.merchant-gpu",)

def test_resolve_scope_layer():
    cats = resolve_scope("layer:chips", _tax())
    assert "chips.merchant-gpu" in cats and all(c.startswith("chips.") for c in cats)

def test_resolve_scope_all():
    cats = resolve_scope("all", _tax())
    assert {"chips.merchant-gpu", "models.frontier-closed"} <= set(cats)

def test_resolve_scope_unknown_category_raises():
    with pytest.raises(ValueError):
        resolve_scope("category:chips.not-real", _tax())

def test_resolve_scope_malformed_raises():
    with pytest.raises(ValueError):
        resolve_scope("bogus", _tax())

def test_build_cycle_plan_marks_ready_skipped_and_stages():
    plan = build_cycle_plan("layer:chips", _tax(), AssignmentProvider("fixtures"))
    by_id = {e.category_id: e for e in plan.entries}
    # the one category with a committed assignment is ready
    assert by_id["chips.merchant-gpu"].status == "ready"
    assert by_id["chips.merchant-gpu"].assignment_path is not None
    # a category with no assignment is skipped, not dropped (no silent truncation)
    assert by_id["chips.hbm-memory"].status == "skipped-no-assignment"
    assert by_id["chips.hbm-memory"].assignment_path is None
    # every selected category is present
    assert set(by_id) == set(resolve_scope("layer:chips", _tax()))
    # Category active; Layer/Main deferred
    assert {s["tier"]: s["status"] for s in plan.stages} == {
        "category": "active", "layer": "deferred", "main": "deferred"}
