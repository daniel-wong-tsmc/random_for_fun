import pytest
from pydantic import ValidationError
from gpu_agent.schema.scorecard import (
    Divergence, MarketIndices, DemandSupply, Scorecard)
from gpu_agent.schema.finding import Confidence


def _ds(dmi, smi, sdgi, direction):
    return DemandSupply(dmiContribution=dmi, smiContribution=smi, sdgi=sdgi, sdgiDirection=direction)


def test_divergence_model_roundtrips():
    d = Divergence(state="diverging-weakening", sdgiGap=-0.2,
                   outlookFindingCount=2, momentumFindingCount=5, note="")
    assert d.state == "diverging-weakening" and d.sdgiGap == -0.2
    assert d.outlookFindingCount == 2 and d.momentumFindingCount == 5


def test_divergence_rejects_unknown_state():
    with pytest.raises(ValidationError):
        Divergence(state="exploding", sdgiGap=0.0, outlookFindingCount=0, momentumFindingCount=0)


def test_market_indices_holds_two_demandsupply_and_a_divergence():
    mi = MarketIndices(
        momentum=_ds(0.07, 0.05, 0.02, "balanced"),
        outlook=_ds(0.0, 0.0, 0.0, "balanced"),
        divergence=Divergence(state="insufficient-coverage", sdgiGap=-0.02,
                              outlookFindingCount=0, momentumFindingCount=4,
                              note="no leading findings; Outlook deferred to 4-4"))
    assert mi.momentum.dmiContribution == 0.07
    assert mi.divergence.state == "insufficient-coverage"


def test_scorecard_indices_defaults_none():
    sc = Scorecard(
        categoryId="chips.merchant-gpu", asOf="2026-06",
        demandSupply=_ds(0.0, 0.0, 0.0, "balanced"),
        narrative="n", confidence=Confidence(level="medium", basis="b"))
    assert sc.indices is None
