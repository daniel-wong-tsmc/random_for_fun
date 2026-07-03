from __future__ import annotations
import math
from datetime import datetime, timezone
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

def _normalize_timestamp(value: str) -> str:
    """F41a: re-emit a full timestamp as UTC 'YYYY-MM-DDTHH:MM:SSZ' so the frozen scoring's
    lexical (capturedAt, ...) comparison is safe against mixed offsets. Bare dates
    (no 'T', e.g. 'YYYY-MM-DD') and unparseable strings pass through unchanged — the gate's
    ISO-prefix check (F17) still catches the latter loud."""
    if not value or "T" not in value:
        return value
    iso = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def draft_to_finding(draft: FindingDraft, *, doc, n: int, as_of: str,
                     captured_at: str, extraction_model: str, side: str) -> Finding:
    data = draft.model_dump()
    data["evidence"] = [{**e, "tier": doc.tier} for e in data["evidence"]]   # F2d code-stamp
    data["observedAt"] = _normalize_timestamp(data["observedAt"])
    return Finding(
        **data, side=side, id=f"{doc.id}-{n}", asOf=as_of,
        capturedAt=_normalize_timestamp(captured_at),
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
        from gpu_agent.config import REGISTRY_PATH
        registry = IndicatorRegistry.load(REGISTRY_PATH)
    if taxonomy is None:
        from gpu_agent.registry.structure import Taxonomy
        from gpu_agent.config import TAXONOMY_PATH
        taxonomy = Taxonomy.load(TAXONOMY_PATH)
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
        if (spec.side == "price" and draft.value is not None and spec.unit
                and draft.value.unit != spec.unit):
            # F53: price series match cross-cycle on (indicatorId, publisher, unit) —
            # a drifting unit string (or a mislabeled indicator, whose canonical unit
            # then mismatches) silently kills the PMI. Reject loud -> re-dispatch.
            violations.append(
                f"{fid}: price unit '{draft.value.unit}' != registered unit "
                f"'{spec.unit}' for {draft.indicatorId}")
        if draft.value is not None and not math.isfinite(draft.value.number):
            violations.append(f"{fid}: non-finite value")
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
