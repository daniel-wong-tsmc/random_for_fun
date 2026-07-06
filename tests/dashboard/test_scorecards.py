import json
from gpu_agent.dashboard.scorecards import load_scorecards, trend_series
from gpu_agent.dashboard.scorecards import _best_tier, _norm_finding

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

def test_findings_null_does_not_crash(tmp_path):
    (tmp_path / "2099-01-01-v1.json").write_text(json.dumps({
        "asOf": "2099-01-01", "findings": None,
        "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.0, "sdgi": 0.1},
    }), encoding="utf-8")
    recs = load_scorecards("chips.merchant-gpu", str(tmp_path))
    assert recs[0]["findings"] == [] and recs[0]["findings_count"] == 0

def test_latest_version_wins_one_record_per_date(tmp_path):
    (tmp_path / "2099-02-02-v1.json").write_text(json.dumps({
        "asOf": "2099-02-02",
        "findings": [{"id": "a", "evidence": [{"tier": "secondary"}]}],
    }), encoding="utf-8")
    (tmp_path / "2099-02-02-v2.json").write_text(json.dumps({
        "asOf": "2099-02-02",
        "findings": [{"id": "a", "evidence": []}, {"id": "b", "evidence": []}],
    }), encoding="utf-8")
    recs = load_scorecards("chips.merchant-gpu", str(tmp_path))
    assert len(recs) == 1 and recs[0]["findings_count"] == 2   # v2 wins

def test_best_tier_prefers_primary_and_defaults_secondary():
    assert _best_tier([{"tier": "secondary"}, {"tier": "primary"}]) == "primary"
    assert _best_tier([]) == "secondary"
