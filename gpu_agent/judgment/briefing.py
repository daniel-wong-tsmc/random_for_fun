from __future__ import annotations
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.tracks import DimensionTracks

class Briefing(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    anchors: dict[str, float] = Field(default_factory=dict)
    grouped: dict[str, list[str]] = Field(default_factory=dict)

def _polarity(f: Finding, track: str) -> int:
    return f.polarityDemand if track == "demand" else f.polaritySupply

def build_briefing(findings: list[Finding], registry: IndicatorRegistry,
                   category_id: str, tracks: DimensionTracks | None = None) -> Briefing:
    if tracks is None:
        tracks = DimensionTracks.load("registry/indicators.json")
    grouped: dict[str, list[Finding]] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        if spec.dimension is None:
            continue
        grouped.setdefault(spec.dimension, []).append(f)
    anchors: dict[str, float] = {}
    grouped_ids: dict[str, list[str]] = {}
    for dim, fs in grouped.items():
        track = tracks.for_dimension(dim)          # F9: registry authority, order-independent
        anchors[dim] = sum(_polarity(f, track) * f.magnitude / 3 for f in fs) / len(fs)
        grouped_ids[dim] = [f.id for f in fs]
    return Briefing(findings=findings, anchors=anchors, grouped=grouped_ids)
