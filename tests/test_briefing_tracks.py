import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.tracks import DimensionTracks, TracksError
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG = pathlib.Path("registry/indicators.json")


def _f(fid, indicatorId, pol_d, pol_s, mag):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity="nvidia",
        observedAt="2026-06", capturedAt="2026-06-25T00:00:00Z")


def test_anchor_is_order_independent_on_registry_track():
    # competitiveStructure holds S9 (per-indicator polarityTrack=supply) and releaseCadence
    # (per-indicator polarityTrack=demand). dimensionTracks pins the dimension to DEMAND, so
    # the anchor is the demand-track mean regardless of finding order.
    reg = IndicatorRegistry.load(REG)
    s9 = _f("s9", "S9", 1, -1, 3)             # demand +1.0, supply -1.0
    rc = _f("rc", "releaseCadence", 1, 0, 3)  # demand +1.0
    a = build_briefing([s9, rc], reg, "chips.merchant-gpu")
    b = build_briefing([rc, s9], reg, "chips.merchant-gpu")
    assert a.anchors["competitiveStructure"] == pytest.approx(b.anchors["competitiveStructure"])
    assert a.anchors["competitiveStructure"] == pytest.approx(1.0)  # (1.0 + 1.0) / 2, demand track


def test_missing_track_fails_loud():
    reg = IndicatorRegistry.load(REG)
    with pytest.raises(TracksError):
        build_briefing([_f("s9", "S9", 1, -1, 3)], reg, "chips.merchant-gpu",
                       tracks=DimensionTracks(mapping={}))
