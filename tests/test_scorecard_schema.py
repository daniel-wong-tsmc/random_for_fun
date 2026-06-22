from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS

def test_dimensions_are_the_six_fixed_ones():
    assert DIMENSIONS == ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]

def test_minimal_scorecard_roundtrips():
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06", "findings": [],
        "dimensionRatings": {
            "momentum": {"rating": "Strong", "direction": "worsening",
                         "confidence": {"level": "high", "basis": "x"},
                         "findingIds": ["f-001"], "rationale": "slope flattening"}},
        "demandSupply": {"dmiContribution": 0.4, "smiContribution": 0.6, "anchors": {"momentum": 0.4}},
        "narrative": "Strong but softening.", "confidence": {"level": "medium", "basis": "x"},
        "sources": ["NVIDIA 10-Q"], "provenance": {"runId": "r1"},
    }
    sc = Scorecard.model_validate(data)
    assert sc.dimensionRatings["momentum"].rating == "Strong"
    assert sc.demandSupply.smiContribution == 0.6
