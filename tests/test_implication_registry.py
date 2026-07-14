"""F65 Task 1: the per-category decision-variable registry (registry/implications.json)
loads into typed variables; a new category is pure DATA (acceptance 5)."""
from __future__ import annotations
import json
import pytest
from gpu_agent.implication import ImplicationRegistry, ImplicationError
from gpu_agent.config import IMPLICATIONS_REGISTRY_PATH


def test_seed_loads_five_variables():
    reg = ImplicationRegistry.load(IMPLICATIONS_REGISTRY_PATH)
    variables = reg.variables_for("chips.merchant-gpu")
    assert [v.id for v in variables] == [
        "waferStartsByNode", "cowosSoicAllocation", "n2CustomerMix",
        "pricingLeverage", "foundryCompetitiveEvents"]
    assert all(v.label and v.description for v in variables)


def test_unknown_category_raises():
    reg = ImplicationRegistry.load(IMPLICATIONS_REGISTRY_PATH)
    with pytest.raises(ImplicationError):
        reg.variables_for("does.not-exist")


def test_second_category_needs_only_data(tmp_path):
    # Category-agnostic: a new category entry is pure data, zero code edits (acceptance 5).
    p = tmp_path / "impl.json"
    p.write_text(json.dumps({"models.frontier-closed": {"variables": [
        {"id": "tokenPricing", "label": "Token pricing", "description": "d"}]}}), "utf-8")
    reg = ImplicationRegistry.load(p)
    assert [v.id for v in reg.variables_for("models.frontier-closed")] == ["tokenPricing"]
