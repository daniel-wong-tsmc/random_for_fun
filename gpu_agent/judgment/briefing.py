from __future__ import annotations
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.judgment.map import DIMENSION_MAP, DIMENSION_POLARITY

class Briefing(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    anchors: dict[str, float] = Field(default_factory=dict)
    grouped: dict[str, list[str]] = Field(default_factory=dict)

def _polarity(f: Finding, dimension: str) -> int:
    track = DIMENSION_POLARITY.get(dimension, "demand")
    return f.polarityDemand if track == "demand" else f.polaritySupply

def build_briefing(findings: list[Finding]) -> Briefing:
    grouped: dict[str, list[Finding]] = {}
    for f in findings:
        dim = DIMENSION_MAP.get(f.indicatorId)
        if dim is None:
            continue
        grouped.setdefault(dim, []).append(f)
    anchors: dict[str, float] = {}
    grouped_ids: dict[str, list[str]] = {}
    for dim, fs in grouped.items():
        anchors[dim] = sum(_polarity(f, dim) * f.magnitude / 3 for f in fs) / len(fs)
        grouped_ids[dim] = [f.id for f in fs]
    return Briefing(findings=findings, anchors=anchors, grouped=grouped_ids)
