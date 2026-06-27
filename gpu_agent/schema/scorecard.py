from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding, Confidence

DIMENSIONS = ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]

class DimensionRating(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    confidence: Confidence
    findingIds: list[str]
    rationale: str

class DimensionStatus(BaseModel):
    evidenceStatus: Literal["grounded", "under-supported"]
    findingCount: int = 0
    confidenceCap: Optional[Literal["low", "medium"]] = None
    note: str = ""

class CategoryStatus(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    bottleneck: str
    reason: str

class DemandSupply(BaseModel):
    dmiContribution: float
    smiContribution: float
    anchors: dict[str, float] = Field(default_factory=dict)
    sdgi: Optional[float] = None
    sdgiDirection: Optional[Literal["demand-led", "supply-led", "balanced"]] = None

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
    dimensionStatus: dict[str, DimensionStatus] = Field(default_factory=dict)
    categoryStatus: Optional[CategoryStatus] = None
