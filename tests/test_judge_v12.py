import json
import pytest
from gpu_agent.judgment.briefing import Briefing
from gpu_agent.judgment.judge import JudgmentResult, DimensionJudgment, aggregate, judge_findings, JudgmentError
from gpu_agent.schema.scorecard import CategoryStatus, DimensionRating
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.llm.recorded import RecordedClient


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


# --- Task 3: F20 — propagate finding-level confidence caps to the dimension rating ---

def _finding(fid: str, level: str) -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level=level, basis="b"), asOf="2026-06",
        evidence=[Evidence(source="src", url="https://x.example/a", date="2026-06-12",
                           excerpt="e", tier="primary")],
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="E", observedAt="2026-06-12", capturedAt="2026-06-12T00:00:00Z")


def _result_with_findings(rating: str, finding_ids: list[str], narrative: str = "n") -> JudgmentResult:
    return JudgmentResult(
        dimensions={"momentum": DimensionJudgment(
            rating=rating, direction="steady", findingIds=finding_ids, rationale="r")},
        categoryStatus=CategoryStatus(
            rating=rating, direction="steady", bottleneck="momentum", reason="r"),
        narrative=narrative)


def test_confidence_capped_by_worst_cited_finding_confidence():
    # Vote is unanimous, full coverage -> vote-derived level "high" -- but the only cited
    # finding is "medium" -> the rating cannot be more confident than its best evidence.
    results = [_result_with_findings("Strong", ["f1"])] * 3
    findings_by_id = {"f1": _finding("f1", "medium")}
    bundle = aggregate(results, _briefing(), findings_by_id=findings_by_id)
    r = bundle.ratings["momentum"]
    assert r.confidence.level == "medium"
    assert "capped by finding confidence" in r.confidence.basis


def test_confidence_ceiling_high_when_any_cited_finding_high():
    results = [_result_with_findings("Strong", ["f1", "f2"])] * 3
    findings_by_id = {"f1": _finding("f1", "medium"), "f2": _finding("f2", "high")}
    bundle = aggregate(results, _briefing(), findings_by_id=findings_by_id)
    assert bundle.ratings["momentum"].confidence.level == "high"


def test_confidence_capped_to_low_when_all_cited_findings_low():
    results = [_result_with_findings("Strong", ["f1"])] * 3
    findings_by_id = {"f1": _finding("f1", "low")}
    bundle = aggregate(results, _briefing(), findings_by_id=findings_by_id)
    assert bundle.ratings["momentum"].confidence.level == "low"


def test_confidence_cap_not_applied_when_findings_by_id_omitted():
    # Legacy call (no findings_by_id) -> behavior unchanged, no cap applied.
    results = [_result_with_findings("Strong", ["f1"])] * 3
    bundle = aggregate(results, _briefing())
    assert bundle.ratings["momentum"].confidence.level == "high"


# --- Task 4: F35 — citation coherence: cited findings must belong to the dimension's group ---

def _v12_finding(fid: str, indicator: str) -> Finding:
    # D2 -> momentum, market-share-pct -> moat (real registry indicator ids).
    return Finding(
        id=fid, statement="s", kind="observed", trend="flat", why="w",
        impact=Impact(targets=["t"], direction="positive", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        evidence=[Evidence(source="src", url="https://x.example/a", date="2026-06-12",
                           excerpt="e", tier="primary")],
        indicatorId=indicator, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="E", observedAt="2026-06-12", capturedAt="2026-06-12T00:00:00Z")


def _v12_judgment(moat_cites: list[str]) -> str:
    return json.dumps({
        "dimensions": {
            "momentum": {"rating": "Strong", "direction": "steady",
                        "findingIds": ["mom-1"], "rationale": "r"},
            "moat": {"rating": "Strong", "direction": "steady",
                    "findingIds": moat_cites, "rationale": "r"},
        },
        "categoryStatus": {"rating": "Strong", "direction": "steady",
                           "bottleneck": "momentum", "reason": "r"},
        "narrative": "n"})


def test_citation_outside_dimension_group_raises():
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_v12_finding("mom-1", "D2"), _v12_finding("moat-1", "market-share-pct")]
    # "moat" dimension incorrectly cites the momentum finding "mom-1".
    client = RecordedClient([_v12_judgment(["mom-1"])])
    with pytest.raises(JudgmentError) as exc:
        judge_findings(findings, client, reg, "chips.merchant-gpu", samples=1, resample_budget=0)
    assert "not in its indicator group" in str(exc.value)


def test_coherent_citations_pass():
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_v12_finding("mom-1", "D2"), _v12_finding("moat-1", "market-share-pct")]
    client = RecordedClient([_v12_judgment(["moat-1"])])
    bundle = judge_findings(findings, client, reg, "chips.merchant-gpu", samples=1, resample_budget=0)
    assert bundle.ratings["moat"].rating == "Strong"
