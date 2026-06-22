from gpu_agent.store import JsonStore
from gpu_agent.schema.scorecard import Scorecard

def _sc():
    return Scorecard.model_validate({
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06", "findings": [],
        "dimensionRatings": {}, "demandSupply": {"dmiContribution": 0.0, "smiContribution": 0.0, "anchors": {}},
        "narrative": "n", "confidence": {"level": "low", "basis": "b"}, "sources": [], "provenance": {}})

def test_append_is_versioned_and_non_destructive(tmp_path):
    store = JsonStore(tmp_path)
    p1 = store.append(_sc())
    p2 = store.append(_sc())
    assert p1 != p2
    assert p1.name == "2026-06-v1.json" and p2.name == "2026-06-v2.json"
    assert len(store.versions("chips.merchant-gpu", "2026-06")) == 2
    assert p1.exists() and p2.exists()  # first not overwritten
