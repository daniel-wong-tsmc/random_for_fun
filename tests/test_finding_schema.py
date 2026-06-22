from gpu_agent.schema.finding import Finding

def test_measured_finding_roundtrips():
    data = {
        "id": "f-001", "statement": "NVIDIA DC revenue growth slope flattened.",
        "kind": "measured", "value": {"number": 8.0, "unit": "% QoQ"},
        "trend": "rising", "why": "Blackwell ramp digesting.",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "slope flattening caps DMI"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "http://x", "date": "2026-05", "excerpt": "...", "tier": "primary"}],
        "reasoning": None,
        "confidence": {"level": "high", "basis": "primary filing"},
        "dispersion": None, "asOf": "2026-06",
        "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12",
        "extractionModel": None, "schemaVersion": "1.0",
    }
    f = Finding.model_validate(data)
    assert f.value.number == 8.0
    assert f.polarityDemand == 1 and f.polaritySupply == 0
    assert Finding.model_validate(f.model_dump()).id == "f-001"
