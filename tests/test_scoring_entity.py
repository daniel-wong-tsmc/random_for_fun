import pytest
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.schema.finding import Finding, Confidence, Impact


def _f(fid, entity, capturedAt, pd=1, ps=0, mag=3, indicatorId="D2"):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pd, polaritySupply=ps, magnitude=mag, entity=entity,
        observedAt="2026-05", capturedAt=capturedAt)


def test_distinct_entities_both_contribute():
    # F7: NVDA and AMD each carry a D2 finding (+1, mag 3). OLD math bucketed by
    # indicatorId only, so one erased the other -> dmi 0.1. NEW buckets per (entity,
    # indicator), so both contribute -> 0.1 + 0.1 = 0.2.
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f("nvda-1", "NVDA", "2026-06-10T00:00:00Z"),
                _f("amd-1", "AMD", "2026-06-12T00:00:00Z")]
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu")
    assert dmi == pytest.approx(0.2)


def test_same_entity_two_vintages_latest_wins():
    # one (entity, indicator) bucket collapses to the latest vintage: the +1 newer
    # finding wins over the -1 older one -> dmi 0.1 (not 0.0 from summing both).
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f("nvda-old", "NVDA", "2026-05-01T00:00:00Z", pd=-1),
                _f("nvda-new", "NVDA", "2026-06-12T00:00:00Z", pd=1)]
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu")
    assert dmi == pytest.approx(0.1)
