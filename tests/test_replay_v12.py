import pathlib
import pytest
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.assignment import load_assignment

STORE = pathlib.Path("store/chips.merchant-gpu")
CATEGORY = "chips.merchant-gpu"


def _load(name):
    return Scorecard.model_validate_json((STORE / name).read_text("utf-8"))


def test_v12_is_replay_of_v6():
    v12 = _load("2026-06-v12.json")
    assert v12.provenance["replayOf"] == "2026-06-v6"
    assert v12.provenance["migration"] == "contract-v1.2"


def test_v12_dmi_smi_match_independent_entity_indicator_computation():
    v6 = _load("2026-06-v6.json")
    v12 = _load("2026-06-v12.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    weights = load_assignment("fixtures/asg.chips.merchant-gpu.json").weights
    dmi, smi = dmi_smi_contribution(v6.findings, reg, CATEGORY, weights)   # per (entity, indicator)
    assert v12.demandSupply.dmiContribution == pytest.approx(dmi)
    assert v12.demandSupply.smiContribution == pytest.approx(smi)
    assert v12.demandSupply.sdgi == pytest.approx(dmi - smi)


def test_v12_findings_are_v6_findings_verbatim():
    v6 = _load("2026-06-v6.json")
    v12 = _load("2026-06-v12.json")
    assert [f.id for f in v12.findings] == [f.id for f in v6.findings]
    # historical judgment is immutable: the replay re-runs MATH, not the gate
    assert [f.model_dump() for f in v12.findings] == [f.model_dump() for f in v6.findings]
    assert v12.narrative == v6.narrative
    assert {k: r.rating for k, r in v12.dimensionRatings.items()} == \
           {k: r.rating for k, r in v6.dimensionRatings.items()}
