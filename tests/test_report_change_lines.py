from __future__ import annotations
from gpu_agent.change import ChangeReport, HorizonDiff, ItemDelta
from gpu_agent.report import render_change_lines
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent import reader


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


def test_horizon_lines_lead_and_name_moves():
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="dim:momentum", changed=True, today="Very strong/improving",
                      prior="Strong/steady", direction="up"),
            ItemDelta(key="price:B200", changed=True, today="$3.75/GPU-hr",
                      prior="$3.99/GPU-hr", direction="down")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[
            ItemDelta(key="dim:moat", changed=False, today="Mixed/improving",
                      unchangedSince="2026-06-08")]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf=None, items=[]),
    ])
    out = render_change_lines(cr, _reg())
    lines = out.splitlines()
    assert lines[0] == "WHAT CHANGED"
    assert "Since yesterday" in out and "(vs 2026-07-07)" in out
    assert "Demand momentum" in out            # DIM_LABEL, not the raw id
    assert "GPU rental price" not in out       # price line uses the model token, not a registry label
    # unchanged horizon states the anchor date
    assert "unchanged since 2026-06-08" in out
    # no-run horizon is explicit, not blank
    assert "no run yet at/before" in out


def test_change_lines_pass_acronym_lint():
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="metric:vendorRevenueGuidance", changed=True,
                      today="11.2 USD_B", prior="10.0 USD_B", direction="up")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[]),
    ])
    out = render_change_lines(cr, _reg())
    assert reader.lint_acronyms(out) == []
