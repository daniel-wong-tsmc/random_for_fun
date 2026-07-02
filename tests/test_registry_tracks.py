import json, pytest
from gpu_agent.registry.tracks import DimensionTracks, TracksError
from gpu_agent.registry.indicators import IndicatorRegistry

REG = "registry/indicators.json"

def test_load_and_lookup():
    t = DimensionTracks.load(REG)
    assert t.for_dimension("momentum") == "demand"
    assert t.for_dimension("bottleneck") == "supply"

def test_unmapped_dimension_fails_loud():
    t = DimensionTracks(mapping={"momentum": "demand"})
    with pytest.raises(TracksError):
        t.for_dimension("moat")

def test_invalid_track_value_fails_loud():
    t = DimensionTracks(mapping={"momentum": "sideways"})
    with pytest.raises(TracksError):
        t.for_dimension("momentum")

def test_validate_covers_every_scoring_dimension():
    t = DimensionTracks.load(REG)
    t.validate(IndicatorRegistry.load(REG))  # shipped data must be clean

def test_shipped_d6_is_overlay_only():
    data = json.loads(open(REG, encoding="utf-8").read())
    d6 = data["indicators"]["D6"]
    assert d6["scoring"] is False
    assert d6["side"] == "price"
    assert d6.get("dimension") is None
    assert d6.get("weight", 0.0) == 0.0
