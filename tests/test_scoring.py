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
