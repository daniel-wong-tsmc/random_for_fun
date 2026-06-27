"""Coverage manifest models and gap computation for sub-project C.

Defines:
  CoverageManifest  — the per-category expected-coverage declaration
  CoverageGap       — a not-covered expected item (source or indicator)
  load_manifest()   — typed loader with clear error messages
  compute_coverage_gaps() — pure gap checker (no I/O)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


# ── Source entry (also used in per-indicator sourceInventory in indicators.json) ──

class SourceEntry(BaseModel):
    name: str
    accessMethod: Literal["free-web", "filing", "licensed-api", "mcp", "manual"]
    tier: Literal["primary", "secondary"]
    costUsd: float = 0.0
    license: Literal["public", "licensed", "confidential", "unknown"] = "public"
    refresh: Literal["realtime", "daily", "weekly", "quarterly", "annual", "on-demand"]


# ── Manifest components ───────────────────────────────────────────────────────

class ExpectedSource(BaseModel):
    id: str
    label: str
    urlPatterns: list[str] = Field(default_factory=list)
    accessMethod: Literal["free-web", "filing", "licensed-api", "mcp", "manual"]
    tier: Literal["primary", "secondary"]
    costUsd: float = 0.0
    license: Literal["public", "licensed", "confidential", "unknown"] = "public"
    refresh: Literal["realtime", "daily", "weekly", "quarterly", "annual", "on-demand"]
    indicators: list[str] = Field(default_factory=list)
    paywalledNote: str | None = None

    @property
    def is_paywalled(self) -> bool:
        """True if this source requires a paid license we do not hold."""
        return self.costUsd > 0 or self.accessMethod == "licensed-api"


class ExpectedIndicator(BaseModel):
    indicatorId: str
    dimension: str
    priority: Literal["required", "preferred", "optional"]
    sourceIds: list[str] = Field(default_factory=list)


class CoverageManifest(BaseModel):
    version: str
    categoryId: str
    asOf: str
    description: str = ""
    expectedIndicators: list[ExpectedIndicator] = Field(default_factory=list)
    expectedSources: list[ExpectedSource] = Field(default_factory=list)

    def source_by_id(self, source_id: str) -> ExpectedSource | None:
        return next((s for s in self.expectedSources if s.id == source_id), None)


# ── Coverage gap ──────────────────────────────────────────────────────────────

class CoverageGap(BaseModel):
    type: Literal["indicator", "source"]
    id: str
    priority: Literal["required", "preferred", "optional"]
    acquisitionStatus: Literal[
        "paywalled", "not-covered", "cap-truncated",
        "manual-upload-required", "mcp-unavailable"
    ]
    reason: str
    paywalledNote: str | None = None


# ── Loader ────────────────────────────────────────────────────────────────────

class ManifestLoadError(Exception):
    pass


def load_manifest(path: str | Path) -> CoverageManifest:
    """Load and validate a coverage manifest from a JSON file.

    Raises ManifestLoadError with a plain-language message on:
      - file not found
      - invalid JSON
      - schema validation failure
    """
    p = Path(path)
    if not p.exists():
        raise ManifestLoadError(f"Manifest file not found: {p}")
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestLoadError(f"Manifest at {p} contains invalid JSON: {exc}") from exc
    try:
        return CoverageManifest(**raw)
    except Exception as exc:
        raise ManifestLoadError(f"Manifest at {p} failed schema validation: {exc}") from exc


# ── Gap computation (pure — no I/O) ──────────────────────────────────────────

def compute_coverage_gaps(
    manifest: CoverageManifest,
    blob_urls: list[str],
    found_indicator_ids: set[str],
) -> list[CoverageGap]:
    """Return a gap record for each expected item not covered by the gather run.

    Args:
        manifest: the loaded CoverageManifest for this category.
        blob_urls: normalized URLs of all blobs the gather collected.
        found_indicator_ids: set of indicatorIds that appear in at least one
            collected blob (i.e., the coordinator matched an on-topic blob to
            this indicator).

    Returns:
        A list of CoverageGap records. An empty list means full coverage.
    """
    gaps: list[CoverageGap] = []
    covered_source_ids: set[str] = set()

    # 1. Source coverage pass
    for src in manifest.expectedSources:
        if src.is_paywalled:
            gaps.append(CoverageGap(
                type="source",
                id=src.id,
                priority="required",  # paywalled sources default to required
                acquisitionStatus="paywalled",
                reason=f"Source '{src.label}' requires a paid license (costUsd={src.costUsd}).",
                paywalledNote=src.paywalledNote,
            ))
            continue  # do not attempt URL match for paywalled sources

        matched = any(
            any(pattern in url for pattern in src.urlPatterns)
            for url in blob_urls
        )
        if matched:
            covered_source_ids.add(src.id)
        else:
            gaps.append(CoverageGap(
                type="source",
                id=src.id,
                priority="required",
                acquisitionStatus="not-covered",
                reason=(
                    f"Source '{src.label}' was not fetched. "
                    f"URL patterns: {src.urlPatterns}"
                ),
            ))

    # 2. Indicator coverage pass
    for ind in manifest.expectedIndicators:
        # An indicator is covered only if its indicatorId explicitly appears in
        # found_indicator_ids.  Source-URL coverage is necessary but not
        # sufficient: if the gather fetched the source but the coordinator
        # never produced a finding for this indicator, that is still a gap.
        indicator_found = ind.indicatorId in found_indicator_ids

        if indicator_found:
            continue

        gaps.append(CoverageGap(
            type="indicator",
            id=ind.indicatorId,
            priority=ind.priority,
            acquisitionStatus="not-covered",
            reason=(
                f"Indicator '{ind.indicatorId}' (dimension: {ind.dimension}) "
                f"was not covered. Expected sources: {ind.sourceIds}."
            ),
        ))

    return gaps
