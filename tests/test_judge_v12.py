from gpu_agent.judgment.briefing import Briefing
from gpu_agent.judgment.judge import JudgmentResult, DimensionJudgment, aggregate
from gpu_agent.schema.scorecard import CategoryStatus


def _result(dims: dict[str, str], narrative: str = "n") -> JudgmentResult:
    """dims: {dimension: rating} — builds a JudgmentResult with one DimensionJudgment per entry."""
    dimensions = {
        d: DimensionJudgment(rating=r, direction="steady", findingIds=["a"], rationale="r")
        for d, r in dims.items()
    }
    any_rating = next(iter(dims.values())) if dims else "Mixed"
    return JudgmentResult(
        dimensions=dimensions,
        categoryStatus=CategoryStatus(
            rating=any_rating, direction="steady", bottleneck="momentum", reason="r"),
        narrative=narrative)


def _briefing(anchors: dict[str, float] | None = None) -> Briefing:
    return Briefing(findings=[], anchors=anchors or {}, grouped={})


def test_dimension_below_quorum_is_not_rated():
    # "moat" present in only 1 of 3 samples -> quorum = 3//2+1 = 2 -> not rated.
    results = [
        _result({"momentum": "Strong", "moat": "Strong"}),
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
    ]
    bundle = aggregate(results, _briefing())
    assert "moat" not in bundle.ratings
    assert "moat" in bundle.belowQuorum


def test_dimension_meets_quorum_but_not_full_coverage_is_medium_confidence():
    # "momentum" present in 2 of 3 samples, both "Strong" -> quorum met (2 >= 2), rated "Strong",
    # but confidence is "medium" (not full-sample coverage).
    results = [
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
        _result({}),
    ]
    bundle = aggregate(results, _briefing())
    assert bundle.ratings["momentum"].rating == "Strong"
    assert bundle.ratings["momentum"].confidence.level == "medium"
    assert "momentum" not in bundle.belowQuorum


def test_dimension_full_coverage_unanimous_is_high_confidence():
    results = [
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
    ]
    bundle = aggregate(results, _briefing())
    assert bundle.ratings["momentum"].rating == "Strong"
    assert bundle.ratings["momentum"].confidence.level == "high"


def test_dimension_full_coverage_split_vote_is_medium_confidence():
    results = [
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
        _result({"momentum": "Mixed"}),
    ]
    bundle = aggregate(results, _briefing())
    assert bundle.ratings["momentum"].rating == "Strong"
    assert bundle.ratings["momentum"].confidence.level == "medium"
