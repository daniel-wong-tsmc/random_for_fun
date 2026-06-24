from gpu_agent.judgment.briefing import Briefing
from gpu_agent.judgment.judge import JudgmentResult, DimensionJudgment, aggregate, _majority

def _result(rating: str, narrative: str = "n") -> JudgmentResult:
    return JudgmentResult(
        dimensions={"momentum": DimensionJudgment(
            rating=rating, direction="steady", findingIds=["a"], rationale="r")},
        narrative=narrative)

def test_majority_winner_and_spread_basis():
    winner, basis = _majority(["Strong", "Strong", "Mixed"])
    assert winner == "Strong"
    assert basis == "2/3 Strong, 1/3 Mixed"

def test_majority_tie_breaks_to_more_conservative():
    # 1 each: Strong/Weak/Mixed -> all tied -> pick lowest on the scale (Weak)
    winner, _ = _majority(["Strong", "Weak", "Mixed"])
    assert winner == "Weak"

def test_aggregate_caps_confidence_when_split():
    b = Briefing(findings=[], anchors={"momentum": 0.5}, grouped={})
    bundle = aggregate([_result("Strong"), _result("Strong"), _result("Mixed")], b)
    r = bundle.ratings["momentum"]
    assert r.rating == "Strong"
    assert r.confidence.level == "medium"           # split -> capped
    assert r.confidence.basis == "2/3 Strong, 1/3 Mixed"
    assert bundle.anchors == {"momentum": 0.5}      # anchors copied from briefing, untouched

def test_aggregate_unanimous_keeps_high_confidence():
    b = Briefing(findings=[], anchors={}, grouped={})
    bundle = aggregate([_result("Strong", "narr-0"), _result("Strong", "x")], b)
    assert bundle.ratings["momentum"].confidence.level == "high"
    assert bundle.narrative == "narr-0"             # narrative from the first (representative) sample
