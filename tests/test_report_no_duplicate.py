"""F67: the status reason renders exactly once in the whole report."""
from gpu_agent.report import load_scorecard, render_report
from gpu_agent.registry.indicators import IndicatorRegistry


def test_reason_appears_once():
    sc = load_scorecard("fixtures/report/postb-scorecard.json")
    out = render_report(sc, None, IndicatorRegistry.load("registry/indicators.json"),
                        render_ts="2026-07-03T00:00:00+00:00")
    assert out.count(sc.categoryStatus.reason) == 1
