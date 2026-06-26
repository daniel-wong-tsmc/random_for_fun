import math
import pathlib
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG = pathlib.Path("registry/indicators.json")

def _f(fid, indicatorId, pol_d, pol_s, mag, observedAt):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity="nvidia",
        observedAt=observedAt, capturedAt="2026-06-25T00:00:00Z")

def test_duplicate_findings_do_not_scale_the_index():
    reg = IndicatorRegistry.load(REG)
    one = dmi_smi_contribution([_f("a", "D2", 1, 0, 3, "2026-05")], reg, "chips.merchant-gpu")
    three = dmi_smi_contribution(
        [_f("a", "D2", 1, 0, 3, "2026-05"), _f("b", "D2", 1, 0, 3, "2026-02"),
         _f("c", "D2", 1, 0, 3, "2025-11")], reg, "chips.merchant-gpu")
    assert one == three  # per-indicator collapse: count-independent

def test_latest_vintage_wins_within_indicator():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("old", "D2", -1, 0, 3, "2025-11"), _f("new", "D2", 1, 0, 3, "2026-05")],
        reg, "chips.merchant-gpu")
    assert math.isclose(dmi, 0.10)  # uses the +1 latest finding: 0.10 * 1 * 3/3

def test_moat_and_unit_economics_now_carry_weight():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("m", "market-share-pct", 1, 0, 3, "2026-06")], reg, "chips.merchant-gpu")
    assert math.isclose(dmi, 0.10)  # 0.10 weight, was 0.0 before

def test_weight_override_takes_precedence():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("d", "D2", 1, 0, 3, "2026-05")], reg, "chips.merchant-gpu",
        weight_overrides={"D2": 0.50})
    assert math.isclose(dmi, 0.50)
