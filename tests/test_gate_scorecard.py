from gpu_agent.gate import check_scorecard
from gpu_agent.schema.scorecard import Scorecard

def _sc(**over):
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06",
        "findings": [{
            "id": "f-001", "statement": "s", "kind": "measured", "value": {"number": 8.0, "unit": "%"},
            "trend": "rising", "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
            "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "primary"}],
            "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": "D2",
            "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
            "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12",
        }],
        "dimensionRatings": {"momentum": {"rating": "Strong", "direction": "worsening",
            "confidence": {"level": "high", "basis": "b"}, "findingIds": ["f-001"], "rationale": "r"}},
        "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": 0.4}},
        "narrative": "n", "confidence": {"level": "medium", "basis": "b"}, "sources": ["NVIDIA 10-Q"], "provenance": {},
    }
    data.update(over)
    return Scorecard.model_validate(data)

def test_clean_scorecard_passes():
    assert check_scorecard(_sc()) == []

def test_rating_with_no_citations_fails():
    sc = _sc(dimensionRatings={"momentum": {"rating": "Strong", "direction": "steady",
        "confidence": {"level": "high", "basis": "b"}, "findingIds": [], "rationale": "r"}})
    assert any("cites no findings" in e for e in check_scorecard(sc))

def test_rating_contradicting_anchor_fails():
    # "Very strong" momentum while the anchor z-score is deeply negative
    sc = _sc(dimensionRatings={"momentum": {"rating": "Very strong", "direction": "steady",
        "confidence": {"level": "high", "basis": "b"}, "findingIds": ["f-001"], "rationale": "r"}},
        demandSupply={"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": -1.8}})
    assert any("contradicts anchor" in e for e in check_scorecard(sc))

def test_self_reference_fails():
    sc = _sc()
    sc.findings[0].evidence[0].source = "AI Market State dashboard"
    assert any("self-reference" in e for e in check_scorecard(sc))
