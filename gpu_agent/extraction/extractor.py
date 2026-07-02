from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from gpu_agent.schema.finding import Finding, Kind, Value, Impact, Confidence

class DraftEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")   # tier is code-stamped; the model cannot supply it
    source: str
    url: str
    date: str
    excerpt: str

class FindingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")  # the model cannot smuggle provenance/authority fields
    statement: str
    kind: Kind
    value: Optional[Value] = None
    trend: Literal["rising", "falling", "flat", "unknown"]
    why: str
    impact: Impact
    evidence: list[DraftEvidence] = []
    reasoning: Optional[str] = None
    confidence: Confidence
    dispersion: Optional[str] = None
    indicatorId: str
    polarityDemand: Literal[-1, 0, 1]
    polaritySupply: Literal[-1, 0, 1]
    magnitude: Literal[1, 2, 3]
    entity: str
    observedAt: str

class ExtractionResult(BaseModel):
    drafts: list[FindingDraft] = []

def draft_to_finding(draft: FindingDraft, *, doc, n: int, as_of: str,
                     captured_at: str, extraction_model: str, side: str) -> Finding:
    data = draft.model_dump()
    data["evidence"] = [{**e, "tier": doc.tier} for e in data["evidence"]]   # F2d code-stamp
    return Finding(
        **data, side=side, id=f"{doc.id}-{n}", asOf=as_of, capturedAt=captured_at,
        extractionModel=extraction_model, schemaVersion="1.2",
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
                     model: str = "claude-opus-4-8",
                     registry=None, taxonomy=None) -> ExtractionOutcome:
    from gpu_agent.registry.indicators import RegistryError
    if registry is None:
        from gpu_agent.registry.indicators import IndicatorRegistry
        registry = IndicatorRegistry.load("registry/indicators.json")
    if taxonomy is None:
        from gpu_agent.registry.structure import Taxonomy
        taxonomy = Taxonomy.load("docs/taxonomy.json")
    valid_targets = frozenset(taxonomy.categories)
    folded_doc = " ".join(doc.content.split())
    result = client.complete_json(build_user_prompt(doc), SYSTEM, ExtractionResult, model)
    findings: list[Finding] = []
    dropped: list[DroppedFinding] = []
    for i, draft in enumerate(result.drafts, start=1):
        fid = f"{doc.id}-{i}"
        try:
            spec = registry.resolve(draft.indicatorId)
        except RegistryError:
            dropped.append(DroppedFinding(id=fid, violations=[f"unregistered indicator: {draft.indicatorId}"]))
            continue
        violations: list[str] = []
        for e in draft.evidence:
            if " ".join(e.excerpt.split()) not in folded_doc:
                violations.append(f"{fid}: excerpt not found in source document")
            if e.url != doc.url:
                violations.append(f"{fid}: evidence url does not match source document")
        f = draft_to_finding(draft, doc=doc, n=i, as_of=as_of, captured_at=captured_at,
                             extraction_model=extraction_model, side=spec.side or "structural")
        violations += check_finding(f, valid_targets=valid_targets)
        if violations:
            dropped.append(DroppedFinding(id=fid, violations=violations))
        else:
            findings.append(f)
    return ExtractionOutcome(findings=findings, dropped=dropped)
