from __future__ import annotations
from gpu_agent.change import StateVector, DimCell, MetricCell, PriceCell, ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_quick_glance
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def _state():
    return StateVector(
        asOf="2026-07-08",
        dimensions={"momentum": DimCell(rating="Very strong", direction="improving"),
                    "moat": DimCell(rating="Mixed", direction="improving")},
        demand=0.57, supply=0.29, sdgi=0.28,
        metrics={
            "leadTimes": MetricCell(indicatorId="leadTimes", statement="lead times ~40 weeks",
                                    observedAt="2026-06-30", tier="scarcity"),
            "grossMargin": MetricCell(indicatorId="grossMargin", value=75.0, unit="pct",
                                      statement="gm 75%", observedAt="2026-05-20", tier="money"),
        },
        prices=[PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-08")])


def _change():
    return ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="index:demand", changed=False, direction="same", unchangedSince="2026-06-08"),
            ItemDelta(key="metric:grossMargin", changed=False, direction="same"),
            ItemDelta(key="price:B200", changed=True, direction="down")])])


def test_three_tiers_present_with_arrows_and_age():
    out = render_quick_glance(_state(), _change(), _reg())
    assert "QUICK GLANCE" in out
    assert "Verdict" in out and "Scarcity" in out and "Money" in out
    assert "Demand momentum" in out            # Tier 1 uses DIM_LABEL
    assert "B200 rental" in out and "$3.99" in out
    # Tier 3 money row carries an age tag (asOf 2026-07-08 vs observed 2026-05-20 = 49 days)
    assert "49 days old" in out


def test_quick_glance_passes_acronym_lint():
    out = render_quick_glance(_state(), _change(), _reg())
    assert reader.lint_acronyms(out) == []


def test_numeric_lead_times_render_with_weeks_unit():
    # Live store carries numeric leadTimes findings (unit "weeks" in registry/indicators.json);
    # a bare "52" with no unit above the fold would be a dishonest number.
    state = _state()
    state.metrics["leadTimes"] = MetricCell(indicatorId="leadTimes", value=52.0, unit="weeks",
                                            statement="lead times ~52 weeks",
                                            observedAt="2026-06-30", tier="scarcity")
    out = render_quick_glance(state, _change(), _reg())
    assert "52 weeks" in out
    assert reader.lint_acronyms(out) == []
