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


from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.llm.client import LLMClient
from gpu_agent.gate import check_finding
from gpu_agent.extraction.prompt import SYSTEM, build_user_prompt

class DroppedFinding(BaseModel):
    id: str
    violations: list[str]

class ExtractionOutcome(BaseModel):
    findings: list[Finding] = []
    dropped: list[DroppedFinding] = []

def extract_findings(doc: RawDocument, client: LLMClient, *, as_of: str,
                     captured_at: str, extraction_model: str,
                     model: str = "claude-opus-4-8") -> ExtractionOutcome:
    result = client.complete_json(build_user_prompt(doc), SYSTEM, ExtractionResult, model)
    findings: list[Finding] = []
    dropped: list[DroppedFinding] = []
    for i, draft in enumerate(result.drafts, start=1):
        f = draft_to_finding(draft, doc_id=doc.id, n=i, as_of=as_of,
                             captured_at=captured_at, extraction_model=extraction_model)
        violations = check_finding(f)
        if violations:
            dropped.append(DroppedFinding(id=f.id, violations=violations))
        else:
            findings.append(f)
    return ExtractionOutcome(findings=findings, dropped=dropped)
