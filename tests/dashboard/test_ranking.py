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
