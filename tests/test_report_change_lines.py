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
    assert "Momentum rating" in out            # DIM_LABEL, not the raw id
    assert "GPU rental price" not in out       # price line uses the model token, not a registry label
    # unchanged horizon states the anchor date
    assert "unchanged since 2026-06-08" in out
    # no-run horizon is explicit, not blank
    assert "no run yet at/before" in out


def test_unchanged_since_uses_most_recent_date_across_items():
    # Two unchanged items with different unchangedSince: a changed-then-reverted key
    # carries a nearer date than a truly stable key. The honest whole-set stability
    # window is the most RECENT date — anything older overstates stability.
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[
            ItemDelta(key="dim:moat", changed=False, today="Mixed/improving",
                      unchangedSince="2026-06-08"),
            ItemDelta(key="dim:momentum", changed=False, today="Strong/steady",
                      unchangedSince="2026-07-01")]),
    ])
    out = render_change_lines(cr, _reg())
    assert "unchanged since 2026-07-01" in out
    assert "unchanged since 2026-06-08" not in out


def test_status_constraint_item_renders_binding_constraint_label():
    # status:constraint items used to fall through _change_item_label's default branch
    # and render the bare sub-key "constraint" instead of an exec-plain label.
    cr = ChangeReport(asOf="2026-07-08", horizons=[
        HorizonDiff(horizon="yesterday", lookbackDays=1, priorAsOf="2026-07-07", items=[
            ItemDelta(key="status:constraint", changed=True, today="HBM memory scarcity",
                      prior="export enforcement", direction="new")]),
        HorizonDiff(horizon="last week", lookbackDays=7, priorAsOf="2026-07-01", items=[]),
        HorizonDiff(horizon="last month", lookbackDays=30, priorAsOf="2026-06-08", items=[]),
    ])
    out = render_change_lines(cr, _reg())
    assert "Binding constraint" in out
    assert "constraint" not in out.replace("Binding constraint", "")


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
