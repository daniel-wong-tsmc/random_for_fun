# tests/dashboard/test_render.py
from gpu_agent.dashboard.render import render_html, svg_sparkline, svg_line_chart, SECTION_IDS

def _model():
    return {
        "category_label": "Merchant-GPU Market",
        "latest_date": "2026-07-06", "run_count": 4,
        "generated_at": "2026-07-06 09:20",
        "headline": {"rating": "Strong", "direction": "worsening",
                     "limiting_factor": "shortage of specialized AI memory",
                     "state_of_market": "Demand keeps outrunning supply.",
                     "state_pending": False},
        "tiles": [{"label": "Demand momentum", "value": "0.04", "delta": "+0.00",
                   "spark": [0.0, 0.02, 0.03, 0.04]}],
        "trend": {"dates": ["07-02", "07-03", "07-05", "07-06"],
                  "dmi": [0.0, 0.02, 0.03, 0.04], "smi": [0.0, 0.0, -0.01, -0.03],
                  "sdgi": [0.0, 0.02, 0.05, 0.07]},
        "top_signals": [{"plain": "Memory is getting scarcer.", "pending": False,
                         "_badges": ["new", "official", "impact"], "observed_at": "2026-07-06",
                         "source_name": "SEC", "impact_direction": "negative"}],
        "calls": [{"name": "Export control exposure", "plain": "US rules cap how many chips can be sold.",
                   "pending": True, "status": "intact", "direction": "reaffirmed",
                   "conviction": "high", "cycles": 2, "source_count": 1,
                   "_badges": ["official"], "breaks_if": "rules are lifted"}],
        "demand_supply": {"dmi": 0.04, "smi": -0.03, "sdgi": 0.07, "sdgi_direction": "demand-led"},
        "dimensions": [{"label": "Supply bottleneck", "rating": "Weak",
                        "direction": "worsening", "evidence_status": "grounded"}],
        "runs": [{"date": "2026-07-06", "findings": 15, "sources": 10}],
        "glossary_rows": [{"term": "HBM", "plain": "high-bandwidth memory"}],
        "slop_denylist": ["delve", "leverage", "seamless", "boasts", "robust"],
    }

def test_renders_all_sections_and_is_self_contained():
    html = render_html(_model())
    for sid in SECTION_IDS:
        assert f'id="{sid}"' in html
    assert "<!doctype html>" in html.lower()
    assert "http://" not in html and "https://" not in html   # no external assets
    assert "prefers-color-scheme" in html

def test_no_slop_words_in_output():
    html = render_html(_model()).lower()
    for w in _model()["slop_denylist"]:
        assert w not in html

def test_pending_items_are_flagged():
    html = render_html(_model())
    assert "pending human rewrite" in html.lower()

def test_svg_helpers_return_svg():
    assert svg_sparkline([0, 1, 2, 3]).startswith("<svg")
    assert svg_line_chart({"dmi": [0, 1]}, ["a", "b"]).startswith("<svg")

def test_svg_helpers_handle_degenerate_and_none_input():
    assert svg_sparkline([]).startswith("<svg")
    assert svg_sparkline([5, 5, 5]).startswith("<svg")      # min==max
    assert svg_sparkline([1]).startswith("<svg")
    assert svg_line_chart({"dmi": []}, []).startswith("<svg")
    assert svg_sparkline([0.0, None, 0.2]).startswith("<svg")                       # None must not crash
    assert svg_line_chart({"dmi": [0.0, None, 0.2]}, ["a", "b", "c"]).startswith("<svg")

def test_chart_line_labels_are_plain_not_acronyms():
    svg = svg_line_chart({"dmi": [0, 1], "smi": [0, -1], "sdgi": [0, 1]}, ["a", "b"])
    assert "Demand" in svg and "Supply" in svg and "Gap" in svg
    assert ">DMI<" not in svg and ">SMI<" not in svg and ">SDGI<" not in svg

def test_render_tolerates_unknown_badge():
    m = _model()
    m["top_signals"][0]["_badges"] = ["new", "bogus"]
    html = render_html(m)                 # must not raise
    assert 'id="top-signals"' in html
