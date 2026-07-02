from gpu_agent.judgment.briefing import Briefing
from gpu_agent.judgment.judge import JudgmentResult, DimensionJudgment, aggregate
from gpu_agent.schema.scorecard import CategoryStatus, DimensionRating
from gpu_agent.schema.finding import Confidence


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


# --- Task 2: F38 (code half) — vote spread out of confidence.basis, into its own field ---

def test_vote_spread_moves_out_of_confidence_basis():
    results = [
        _result({"momentum": "Strong"}),
        _result({"momentum": "Strong"}),
        _result({"momentum": "Mixed"}),
    ]
    bundle = aggregate(results, _briefing())
    r = bundle.ratings["momentum"]
    assert r.voteSpread == "2/3 Strong, 1/3 Mixed"
    assert "Strong," not in r.confidence.basis
    assert r.confidence.basis == "majority of 3/3 samples"


def test_dimension_rating_without_vote_spread_still_validates():
    # Old stored scorecards predate voteSpread -> field must be additive/optional.
    r = DimensionRating(
        rating="Strong", direction="steady", findingIds=["a"], rationale="r",
        confidence=Confidence(level="high", basis="b"))
    assert r.voteSpread is None
