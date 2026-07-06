from gpu_agent.dashboard.scorecards import load_scorecards, trend_series

FIX = "tests/dashboard/fixtures"

def test_loads_all_cycles_sorted_ascending():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    assert [r["as_of"] for r in recs] == ["2026-07-02", "2026-07-03", "2026-07-05", "2026-07-06"]

def test_latest_record_headline_fields():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    latest = recs[-1]
    assert latest["rating"] == "Strong"
    assert latest["direction"] == "worsening"
    assert round(latest["dmi"], 3) == 0.04
    assert round(latest["smi"], 3) == -0.027
    assert round(latest["sdgi"], 3) == 0.067
    assert latest["findings_count"] == 15

def test_findings_are_normalized():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    f = recs[-1]["findings"][0]
    assert set(["id", "statement", "observed_at", "magnitude",
                "impact_direction", "tier", "source_name"]).issubset(f)
    assert f["tier"] in ("primary", "secondary")

def test_trend_series_shape():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    ts = trend_series(recs)
    assert len(ts["dates"]) == 4
    assert len(ts["dmi"]) == 4 and len(ts["smi"]) == 4 and len(ts["sdgi"]) == 4
