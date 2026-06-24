from __future__ import annotations
from collections import Counter
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from gpu_agent.schema.finding import Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.judgment.briefing import Briefing

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
    narrative: str

class JudgmentBundle(BaseModel):
    ratings: dict[str, DimensionRating] = Field(default_factory=dict)
    anchors: dict[str, float] = Field(default_factory=dict)
    narrative: str
    confidence: Confidence

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

def aggregate(results: list[JudgmentResult], briefing: Briefing) -> JudgmentBundle:
    dims = {d for r in results for d in r.dimensions}
    ratings: dict[str, DimensionRating] = {}
    all_unanimous = True
    for d in sorted(dims):
        votes = [r.dimensions[d].rating for r in results if d in r.dimensions]
        winner, basis = _majority(votes)
        unanimous = len(set(votes)) == 1
        all_unanimous = all_unanimous and unanimous
        rep = next(r.dimensions[d] for r in results
                   if d in r.dimensions and r.dimensions[d].rating == winner)
        ratings[d] = DimensionRating(
            rating=winner, direction=rep.direction, findingIds=rep.findingIds,
            rationale=rep.rationale,
            confidence=Confidence(level="high" if unanimous else "medium", basis=basis))
    confidence = Confidence(
        level="high" if all_unanimous else "medium",
        basis=f"self-consistency over {len(results)} samples")
    return JudgmentBundle(ratings=ratings, anchors=dict(briefing.anchors),
                          narrative=results[0].narrative, confidence=confidence)
