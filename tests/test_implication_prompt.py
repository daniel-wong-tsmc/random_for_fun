"""F65 Task 2: registry-driven, category-agnostic implication prompt template.
Acceptance 1 (adding a variable changes the emitted prompt; no hardcoded variable list)
and acceptance 5 (category-agnostic — zero merchant-gpu idioms in the frozen system)."""
from __future__ import annotations
import pytest
from pydantic import ValidationError

from gpu_agent.implication import (
    build_implication_user_prompt, IMPLICATION_SYSTEM, DecisionVariable, ImplicationAnswer)
from gpu_agent.thesis import ThesisBook
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence


def _sc():
    return Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                     demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                     narrative="n", confidence=Confidence(level="medium", basis="b"))


def _vars():
    return [DecisionVariable(id="waferStartsByNode", label="Wafer starts by node", description="d1"),
            DecisionVariable(id="pricingLeverage", label="Pricing leverage", description="d2")]


def _book():
    return ThesisBook(categoryId="chips.merchant-gpu")


def test_user_prompt_lists_registry_variables():
    p = build_implication_user_prompt(_vars(), _sc(), _book(), None)
    assert "Wafer starts by node" in p and "Pricing leverage" in p


def test_adding_a_variable_changes_the_prompt():
    base = build_implication_user_prompt(_vars(), _sc(), _book(), None)
    more = _vars() + [DecisionVariable(id="x", label="Foundry competitive events", description="d3")]
    changed = build_implication_user_prompt(more, _sc(), _book(), None)
    assert changed != base
    assert "Foundry competitive events" in changed


def test_memory_block_is_optional_and_present_when_given():
    assert "<memory>" not in build_implication_user_prompt(_vars(), _sc(), _book(), None)
    assert "<memory>" in build_implication_user_prompt(_vars(), _sc(), _book(), "PRIOR STATE")


def test_system_is_category_agnostic():
    # Zero merchant-gpu idioms in the frozen system template (F26/F27).
    low = IMPLICATION_SYSTEM.lower()
    for idiom in ("merchant-gpu", "nvidia", "cowos", "wafer", "n2"):
        assert idiom not in low
    assert "TSMC" in IMPLICATION_SYSTEM  # the beneficiary is the fixed reader persona


def test_answer_schema_forbids_extra():
    with pytest.raises(ValidationError):
        ImplicationAnswer.model_validate({"lines": [{"watchItem": "x", "bogus": 1}]})
