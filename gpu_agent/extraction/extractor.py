from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from gpu_agent.schema.finding import Finding, Kind, Value, Impact, Evidence, Confidence

class FindingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the model cannot smuggle provenance fields
    statement: str
    kind: Kind
    value: Optional[Value] = None
    trend: Literal["rising", "falling", "flat", "unknown"]
    why: str
    impact: Impact
    evidence: list[Evidence] = []
    reasoning: Optional[str] = None
    confidence: Confidence
    dispersion: Optional[str] = None
    indicatorId: str
    side: Literal["demand", "supply", "price", "structural"]
    polarityDemand: Literal[-1, 0, 1]
    polaritySupply: Literal[-1, 0, 1]
    magnitude: Literal[1, 2, 3]
    entity: str
    observedAt: str

class ExtractionResult(BaseModel):
    drafts: list[FindingDraft] = []

def draft_to_finding(draft: FindingDraft, *, doc_id: str, n: int, as_of: str,
                     captured_at: str, extraction_model: str) -> Finding:
    return Finding(
        **draft.model_dump(),
        id=f"{doc_id}-{n}", asOf=as_of, capturedAt=captured_at,
        extractionModel=extraction_model, schemaVersion="1.1",
    )
