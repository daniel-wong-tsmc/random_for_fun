import pathlib
import pytest
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.registry.indicators import IndicatorRegistry

STORE = pathlib.Path("store/chips.merchant-gpu")
CATEGORY = "chips.merchant-gpu"

# Weights in force when the 2026-06 v1.2 replay scorecard was generated: the
# assignment overrides {D2, D6, S9, S10} plus the registry defaults for every
# other scoring indicator present in v6. Frozen here on purpose — this is a
# HISTORICAL-fidelity check, so it must NOT track live registry evolution
# (F60 reweighted rpoBacklog 0.10->0.14 and vendorRevenueGuidance 0.12->0.16 in
# 2026-07, long after this replay). Verified to reproduce the stored scorecard
# exactly: dmi 0.506667 / smi -0.073333 / sdgi 0.58. (D6 is side:price and is
# excluded by scoring.py regardless; kept for a faithful record of the vector.)
_WEIGHTS_AS_OF_2026_06 = {
    "D2": 0.10, "D6": 0.12, "S9": 0.04, "S10": 0.08,
    "market-share-pct": 0.10, "grossMargin": 0.10, "leadTimes": 0.08,
    "rpoBacklog": 0.10, "vendorRevenueGuidance": 0.12,
}


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
    dmi, smi = dmi_smi_contribution(v6.findings, reg, CATEGORY, _WEIGHTS_AS_OF_2026_06)   # per (entity, indicator)
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
