from __future__ import annotations
from collections import Counter
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from gpu_agent.schema.finding import Confidence, Finding
from gpu_agent.schema.scorecard import DimensionRating, Scorecard, DemandSupply, CategoryStatus, DIMENSIONS
from gpu_agent.judgment.briefing import Briefing, build_briefing
from gpu_agent.judgment.prompt import SYSTEM, build_user_prompt
from gpu_agent.gate import _rating_consistent_with_anchor, check_scorecard
from gpu_agent.llm.client import LLMClient

RATING_ORDER = ["Very weak", "Weak", "Mixed", "Strong", "Very strong"]

class DimensionJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the model cannot smuggle extra fields
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    findingIds: list[str]
    rationale: str

class JudgmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimensions: dict[str, DimensionJudgment]
    categoryStatus: CategoryStatus
    narrative: str

class JudgmentBundle(BaseModel):
    ratings: dict[str, DimensionRating] = Field(default_factory=dict)
    anchors: dict[str, float] = Field(default_factory=dict)
    narrative: str
    confidence: Confidence
    categoryStatus: CategoryStatus | None = None
    belowQuorum: list[str] = Field(default_factory=list)

class JudgmentError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))

def _majority(ratings: list[str]) -> tuple[str, str]:
    counts = Counter(ratings)
    top = max(counts.values())
    winner = min((r for r, c in counts.items() if c == top), key=RATING_ORDER.index)
    n = len(ratings)
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], RATING_ORDER.index(kv[0])))
    basis = ", ".join(f"{c}/{n} {r}" for r, c in ordered)
    return winner, basis

_LEVELS = {"low": 0, "medium": 1, "high": 2}

def _confidence_ceiling(finding_ids: list[str], findings_by_id: dict[str, Finding]) -> str:
    """The rating cannot be more confident than its best cited evidence."""
    cited = [findings_by_id[i] for i in finding_ids if i in findings_by_id]
    if not cited:
        return "high"
    return max((f.confidence.level for f in cited), key=_LEVELS.__getitem__)

def _representative_index(results: list[JudgmentResult], winners: dict[str, str]) -> int:
    """Index of the sample whose ratings agree with the most majority winners; earliest on tie."""
    best_i, best_score = 0, -1
    for i, r in enumerate(results):
        score = sum(1 for d, w in winners.items()
                    if d in r.dimensions and r.dimensions[d].rating == w)
        if score > best_score:
            best_score, best_i = score, i
    return best_i

def aggregate(results: list[JudgmentResult], briefing: Briefing,
             findings_by_id: dict[str, Finding] | None = None) -> JudgmentBundle:
    dims = {d for r in results for d in r.dimensions}
    n = len(results)
    quorum = n // 2 + 1
    ratings: dict[str, DimensionRating] = {}
    winners: dict[str, str] = {}
    below_quorum: list[str] = []
    all_unanimous = True
    for d in sorted(dims):
        votes = [r.dimensions[d].rating for r in results if d in r.dimensions]
        if len(votes) < quorum:
            below_quorum.append(d)          # F19: 1-of-3 is not unanimity, it is absence
            continue
        winner, basis = _majority(votes)
        winners[d] = winner
        unanimous = len(votes) == n and len(set(votes)) == 1
        all_unanimous = all_unanimous and unanimous
        rep = next(r.dimensions[d] for r in results
                   if d in r.dimensions and r.dimensions[d].rating == winner)
        conf = Confidence(level="high" if unanimous else "medium",
                          basis=f"majority of {len(votes)}/{n} samples")
        if findings_by_id is not None:
            ceiling = _confidence_ceiling(rep.findingIds, findings_by_id)
            if _LEVELS[ceiling] < _LEVELS[conf.level]:
                conf = Confidence(level=ceiling,
                                  basis=f"{conf.basis}; capped by finding confidence ({ceiling})")
        ratings[d] = DimensionRating(
            rating=winner, direction=rep.direction, findingIds=rep.findingIds,
            rationale=rep.rationale, voteSpread=basis, confidence=conf)
    confidence = Confidence(
        level="high" if all_unanimous else "medium",
        basis=f"self-consistency over {len(results)} samples")
    rep_i = _representative_index(results, winners)
    return JudgmentBundle(ratings=ratings, anchors=dict(briefing.anchors),
                          narrative=results[rep_i].narrative,
                          categoryStatus=results[rep_i].categoryStatus,
                          confidence=confidence,
                          belowQuorum=below_quorum)


def _conflicts(bundle: JudgmentBundle) -> list[str]:
    bad: list[str] = []
    for d, r in bundle.ratings.items():
        a = bundle.anchors.get(d)
        if a is not None and not _rating_consistent_with_anchor(r.rating, a):
            bad.append(f"{d}: rating {r.rating} contradicts anchor {a:.2f}")
    return bad

def _gate_backstop(bundle: JudgmentBundle, findings: list[Finding]) -> None:
    sc = Scorecard(
        categoryId="_judge_check", asOf=findings[0].asOf if findings else "",
        findings=findings, dimensionRatings=bundle.ratings,
        demandSupply=DemandSupply(dmiContribution=0.0, smiContribution=0.0, anchors=bundle.anchors),
        narrative=bundle.narrative, confidence=bundle.confidence)
    violations = check_scorecard(sc)
    if violations:
        raise JudgmentError(violations)

def judge_findings(findings: list[Finding], client: LLMClient, registry, category_id: str,
                   *, samples: int = 3,
                   resample_budget: int = 2, model: str = "claude-opus-4-8") -> JudgmentBundle:
    briefing = build_briefing(findings, registry, category_id)
    prompt = build_user_prompt(briefing)
    findings_by_id = {f.id: f for f in findings}
    last_conflicts: list[str] = []
    for _ in range(1 + resample_budget):
        results = [client.complete_json(prompt, SYSTEM, JudgmentResult, model)
                   for _ in range(samples)]
        bundle = aggregate(results, briefing, findings_by_id=findings_by_id)
        last_conflicts = _conflicts(bundle)
        if not last_conflicts:
            _gate_backstop(bundle, findings)   # raises JudgmentError on any gate violation
            cs = bundle.categoryStatus
            if cs is not None and cs.bottleneck not in DIMENSIONS:
                raise JudgmentError([f"categoryStatus.bottleneck '{cs.bottleneck}' not a dimension"])
            return bundle
    raise JudgmentError(last_conflicts)
