from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding, Confidence

DIMENSIONS = ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]

class DimensionRating(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    confidence: Confidence
    findingIds: list[str]
    rationale: str

class DemandSupply(BaseModel):
    dmiContribution: float
    smiContribution: float
    anchors: dict[str, float] = Field(default_factory=dict)

class Scorecard(BaseModel):
    categoryId: str
    asOf: str
    findings: list[Finding] = Field(default_factory=list)
    dimensionRatings: dict[str, DimensionRating] = Field(default_factory=dict)
    demandSupply: DemandSupply
    narrative: str
    confidence: Confidence
    sources: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
