"""F67 banner: evidence vintage + honest confidence label in the header."""
from gpu_agent.report import load_scorecard, render_header, evidence_vintage

SC = load_scorecard("fixtures/report/postb-scorecard.json")


def test_evidence_vintage_math():
    median, oldest, stale_share = evidence_vintage(SC)
    assert median is not None and oldest is not None
    assert oldest <= median
    assert 0.0 <= stale_share <= 1.0


def test_header_carries_banner_and_relabeled_confidence():
    out = render_header(SC, "2026-07-03T00:00:00+00:00")
    assert "Evidence:" in out                      # vintage line
    assert "vote agreement" in out                 # confidence relabel
    assert "self-consistency" not in out           # jargon gone
