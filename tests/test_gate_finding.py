from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding

def _base(**over):
    data = {
        "id": "f", "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "because", "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05-01", "excerpt": "e", "tier": "primary"}],
        "reasoning": None, "confidence": {"level": "high", "basis": "b"}, "dispersion": None, "asOf": "2026-06",
        "indicatorId": "S9", "side": "supply", "polarityDemand": -1, "polaritySupply": 1, "magnitude": 2,
        "entity": "AMD", "observedAt": "2026-05-01", "capturedAt": "2026-06-12", "schemaVersion": "1.0",
    }
    data.update(over)
    return Finding.model_validate(data)

def test_clean_finding_passes():
    assert check_finding(_base()) == []

def test_measured_without_value_fails():
    f = _base(kind="measured", value=None)
    assert any("missing value" in e for e in check_finding(f))

def test_observed_with_value_is_invented_number():
    f = _base(kind="observed", value={"number": 5.0, "unit": "x"})
    assert any("invented value" in e for e in check_finding(f))

def test_empty_why_fails():
    f = _base(why="   ")
    assert any("missing why" in e for e in check_finding(f))

def test_hypothesis_requires_reasoning_and_capped_confidence():
    f = _base(kind="hypothesis", value=None, reasoning=None, confidence={"level": "high", "basis": "b"})
    errs = check_finding(f)
    assert any("missing reasoning" in e for e in errs)
    assert any("confidence capped" in e for e in errs)

def test_finding_affecting_neither_track_fails():
    f = _base(polarityDemand=0, polaritySupply=0)
    assert any("affects neither" in e for e in check_finding(f))
