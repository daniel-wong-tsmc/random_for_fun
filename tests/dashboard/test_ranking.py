# tests/dashboard/test_ranking.py
from gpu_agent.dashboard.glossary import load_glossary
from gpu_agent.dashboard.ranking import (
    finding_signals, importance, badges, rank_findings,
)

G = load_glossary()

def _finding(**kw):
    base = dict(id="x", statement="a shift", observed_at="2026-07-06",
                magnitude=1, impact_direction="negative", tier="secondary",
                source_name="News")
    base.update(kw)
    return base

def test_recent_primary_highmag_outranks_stale_secondary_lowmag():
    strong = _finding(id="s", tier="primary", magnitude=3,
                      observed_at="2026-07-06",
                      statement="books over $2B China revenue")
    weak = _finding(id="w", tier="secondary", magnitude=1,
                    observed_at="2026-05-01", statement="a small shift")
    ranked = rank_findings([weak, strong], as_of="2026-07-06", glossary=G)
    assert ranked[0]["id"] == "s"

def test_official_badge_when_primary():
    sig = finding_signals(_finding(tier="primary"), "2026-07-06", G)
    assert "official" in badges(sig)

def test_recency_decays_to_zero_by_six_weeks():
    fresh = finding_signals(_finding(observed_at="2026-07-06"), "2026-07-06", G)
    stale = finding_signals(_finding(observed_at="2026-05-20"), "2026-07-06", G)
    assert fresh["new"] > 0.9
    assert stale["new"] == 0.0

def test_importance_is_weighted_sum_in_unit_range():
    sig = {"new": 1.0, "official": 1.0, "impact": 1.0}
    assert abs(importance(sig) - 1.0) < 1e-9

from gpu_agent.dashboard.ranking import call_signals, rank_calls, finding_signals

def _call(**kw):
    base = dict(name="X", slug="x", status="intact", direction="reaffirmed",
                conviction="low", cycles=3, has_official=False)
    base.update(kw)
    return base

def test_call_signals_moved_official_and_conviction():
    moved = call_signals(_call(direction="strengthened", conviction="high", has_official=True))
    assert moved["new"] == 1.0 and moved["official"] == 1.0 and moved["impact"] == 1.0
    assert call_signals(_call(direction="reaffirmed", status="intact", cycles=3))["new"] == 0.3
    assert call_signals(_call(conviction="medium"))["impact"] == 0.66
    assert call_signals(_call(conviction="low"))["impact"] == 0.33
    assert call_signals(_call(status="challenged"))["new"] == 1.0
    assert call_signals(_call(cycles=0))["new"] == 1.0
    assert call_signals(_call(has_official=False))["official"] == 0.4

def test_rank_calls_orders_moved_highconviction_first():
    strong = _call(slug="s", direction="strengthened", conviction="high", has_official=True)
    weak = _call(slug="w", direction="reaffirmed", conviction="low", has_official=False, cycles=5)
    ranked = rank_calls([weak, strong])
    assert ranked[0]["slug"] == "s"
    assert "impact" in ranked[0]["_badges"] and "official" in ranked[0]["_badges"]

def test_recency_interpolates_in_midrange_and_at_boundaries():
    f = dict(id="m", statement="x", magnitude=1, tier="secondary", observed_at="2026-06-12")
    mid = finding_signals(f, "2026-07-06", G)["new"]   # age 24 days -> ~0.514
    assert 0.50 < mid < 0.53
    assert finding_signals({**f, "observed_at": "2026-06-29"}, "2026-07-06", G)["new"] == 1.0  # age 7
    assert finding_signals({**f, "observed_at": "2026-05-25"}, "2026-07-06", G)["new"] == 0.0  # age 42
