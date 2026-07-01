from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class DroppedDoc(BaseModel):
    url: str
    reason: str                    # "seen-url" | "seen-content-hash"
    firstSeenAsOf: str


class FindingClass(BaseModel):
    findingId: str
    entity: str
    indicatorId: str
    verdict: str                   # "new" | "update" | "duplicate"
    priorFindingId: Optional[str] = None
    detail: str = ""


class DedupResult(BaseModel):
    new: list[FindingClass] = Field(default_factory=list)
    update: list[FindingClass] = Field(default_factory=list)
    duplicate: list[FindingClass] = Field(default_factory=list)


class DedupReport(BaseModel):
    asOf: str
    docsDroppedKnown: list[DroppedDoc] = Field(default_factory=list)
    findingsNew: list[FindingClass] = Field(default_factory=list)
    findingsUpdate: list[FindingClass] = Field(default_factory=list)
    findingsDuplicate: list[FindingClass] = Field(default_factory=list)


class DedupConfig(BaseModel):
    rel_tol: float = 0.01          # relative tolerance for a measured-value change
    eps: float = 1e-9              # floor so a near-zero prior can't divide-by-zero


DEFAULT_DEDUP_CONFIG = DedupConfig()
