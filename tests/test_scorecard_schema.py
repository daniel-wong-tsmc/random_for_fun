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

from gpu_agent.schema.scorecard import (
    DimensionStatus, CategoryStatus, DemandSupply, Scorecard)

def test_dimension_status_defaults():
    s = DimensionStatus(evidenceStatus="under-supported")
    assert s.findingCount == 0
    assert s.confidenceCap is None
    assert s.note == ""

def test_category_status_roundtrips():
    cs = CategoryStatus(rating="Mixed", direction="steady",
                        bottleneck="bottleneck", reason="supply is the binding constraint")
    assert cs.bottleneck == "bottleneck"

def test_demandsupply_sdgi_optional_and_defaults_none():
    ds = DemandSupply(dmiContribution=0.1, smiContribution=0.03)
    assert ds.sdgi is None and ds.sdgiDirection is None
    ds2 = DemandSupply(dmiContribution=0.1, smiContribution=0.03,
                       sdgi=0.07, sdgiDirection="demand-led")
    assert ds2.sdgi == 0.07

def test_pre_b_scorecard_still_validates_without_new_fields():
    # A scorecard written before B (no dimensionStatus / categoryStatus / sdgi) must load.
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06", "findings": [],
        "dimensionRatings": {}, "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.0},
        "narrative": "n", "confidence": {"level": "medium", "basis": "x"}}
    sc = Scorecard.model_validate(data)
    assert sc.dimensionStatus == {} and sc.categoryStatus is None

def test_scorecard_carries_six_dimension_status():
    sc = Scorecard.model_validate({
        "categoryId": "c", "asOf": "2026-06", "findings": [], "dimensionRatings": {},
        "demandSupply": {"dmiContribution": 0.0, "smiContribution": 0.0},
        "narrative": "n", "confidence": {"level": "low", "basis": "x"},
        "dimensionStatus": {"strategicRisk": {"evidenceStatus": "under-supported",
                                              "confidenceCap": "low", "note": "no findings"}},
        "categoryStatus": {"rating": "Mixed", "direction": "steady",
                           "bottleneck": "bottleneck", "reason": "r"}})
    assert sc.dimensionStatus["strategicRisk"].evidenceStatus == "under-supported"
    assert sc.categoryStatus.rating == "Mixed"
