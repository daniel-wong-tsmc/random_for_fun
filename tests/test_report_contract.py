"""F67 output-contract integration tests over committed fixtures (no store/, no LLM)."""
from gpu_agent import reader
from gpu_agent.report import load_scorecard, render_report
from gpu_agent.registry.indicators import IndicatorRegistry

REG = IndicatorRegistry.load("registry/indicators.json")
SC = load_scorecard("fixtures/report/postb-scorecard.json")
TS = "2026-07-03T00:00:00+00:00"


def _above_appendix(out: str) -> str:
    assert reader.APPENDIX_DIVIDER in out
    return out.split(reader.APPENDIX_DIVIDER)[0]


def test_section_order_standard():
    out = render_report(SC, None, REG, render_ts=TS)
    order = ["STATE OF THE MARKET", "WHAT MOVED", "THE CALLS", "WHY",
             "DEMAND | SUPPLY", "TRUST & COVERAGE", reader.APPENDIX_DIVIDER,
             "OVERALL CATEGORY STATUS", "DIMENSION RATINGS"]
    idx = [out.index(s) for s in order]
    assert idx == sorted(idx)


def test_daily_leads_with_what_moved():
    out = render_report(SC, None, REG, render_ts=TS, daily=True)
    assert out.index("WHAT MOVED") < out.index("STATE OF THE MARKET")


def test_no_jargon_above_appendix():
    top = _above_appendix(render_report(SC, None, REG, render_ts=TS))
    for banned in ("under-supported", "grounded", "(provisional)", "provisional",
                   "single-source", "PMI", "SDGI", "DMI", "SMI"):
        if banned in ("DMI", "SMI"):
            import re
            assert re.search(rf"\b{banned}\b", top) is None, banned
        else:
            assert banned not in top, banned
    assert reader.lint_acronyms(top) == []


def test_dead_price_metrics_fold():
    # postb fixture has no matched prior series -> the fold line, not dash rows
    out = render_report(SC, None, REG, render_ts=TS)
    assert "Δ vs prior: —" not in out
    if "PRICE TRACK" in out:
        assert "needs two matched cycles" in out


def test_empty_state_lines_are_honest():
    out = render_report(SC, None, REG, render_ts=TS)   # no movement passed
    assert "(no wiki store yet" in out or "no prior cycle" in out
    assert "\n  (none)\n" not in _above_appendix(out)


def test_citation_map_below_divider_has_known_finding_id():
    out = render_report(SC, None, REG, render_ts=TS)
    below = out.split(reader.APPENDIX_DIVIDER)[1]
    assert "doc-nvda-1" in below
    assert "CITATION MAP" in below
