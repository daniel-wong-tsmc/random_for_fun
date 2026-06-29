import math
from gpu_agent.scoring import zscore, dmi_smi_contribution
from gpu_agent.schema.finding import Finding
from gpu_agent.registry.indicators import IndicatorRegistry

def test_zscore_basic():
    assert zscore(12.0, [10.0, 10.0, 10.0, 10.0]) == 0.0  # stdev 0 -> 0.0
    z = zscore(4.0, [0.0, 2.0, 4.0])  # mean 2, pstdev ~1.633
    assert math.isclose(z, (4.0 - 2.0) / 1.632993, rel_tol=1e-4)

def test_zscore_thin_history_is_zero():
    assert zscore(5.0, [1.0]) == 0.0

def _f(ind, pd, ps, mag):
    return Finding.model_validate({
        "id": ind, "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "secondary"}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
        "indicatorId": ind, "side": "demand", "polarityDemand": pd, "polaritySupply": ps,
        "magnitude": mag, "entity": "E", "observedAt": "2026-05", "capturedAt": "2026-06-12",
    })

def test_dmi_smi_contribution():
    findings = [_f("D2", 1, 0, 3), _f("S9", -1, 1, 3)]
    weights = {"D2": 0.10, "S9": 0.04}
    reg = IndicatorRegistry.load("registry/indicators.json")
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu", weights)
    assert math.isclose(dmi, 0.10 * 1 * 1.0 + 0.04 * -1 * 1.0)  # 0.06   (unchanged)
    assert math.isclose(smi, 0.04 * 1 * 1.0)                    # 0.04   (unchanged)

def test_strategic_risk_findings_excluded_from_dmi_smi():
    from gpu_agent.schema.finding import Finding, Confidence, Impact
    reg = IndicatorRegistry.load("registry/indicators.json")
    f = Finding(id="r1", statement="export-control exposure rising", kind="observed",
                trend="flat", why="w",
                impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
                confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
                indicatorId="exportControlExposure", side="structural",
                polarityDemand=-1, polaritySupply=0, magnitude=2, entity="nvidia",
                observedAt="2026-06", capturedAt="2026-06-12T00:00:00Z")
    dmi, smi = dmi_smi_contribution([f], reg, "chips.merchant-gpu")
    assert dmi == 0.0 and smi == 0.0  # scoring:false -> excluded

def test_new_overlay_indicators_excluded_from_dmi_smi():
    reg = IndicatorRegistry.load("registry/indicators.json")
    # designWins is structural; gpuSpotPrice is price — both auto-excluded.
    findings = [_f("designWins", 1, 0, 3), _f("gpuSpotPrice", 1, 0, 3)]
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu")
    assert dmi == 0.0 and smi == 0.0


def test_new_scoring_indicators_contribute_to_dmi_smi():
    reg = IndicatorRegistry.load("registry/indicators.json")
    # rpoBacklog (demand) + leadTimes (supply) both flow into the index.
    findings = [_f("rpoBacklog", 1, 0, 3), _f("leadTimes", 0, -1, 3)]
    weights = {"rpoBacklog": 0.10, "leadTimes": 0.08}
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu", weights)
    assert math.isclose(dmi, 0.10 * 1 * 1.0)   # rpoBacklog demand contribution
    assert math.isclose(smi, 0.08 * -1 * 1.0)  # leadTimes supply contribution
