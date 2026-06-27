"""Tests for gpu_agent.manifest — models, loader, and gap computation."""
import json
import pytest
from pathlib import Path
from gpu_agent.manifest import (
    CoverageManifest,
    CoverageGap,
    ManifestLoadError,
    load_manifest,
    compute_coverage_gaps,
)

# ── Fixtures ────────────────────────────────────────────────────────────────

MINIMAL_MANIFEST = {
    "version": "1.0",
    "categoryId": "chips.merchant-gpu",
    "asOf": "2026-06",
    "description": "Test manifest",
    "expectedIndicators": [
        {
            "indicatorId": "D2",
            "dimension": "momentum",
            "priority": "required",
            "sourceIds": ["nvda-earnings"],
        }
    ],
    "expectedSources": [
        {
            "id": "nvda-earnings",
            "label": "NVIDIA earnings filings",
            "urlPatterns": ["investor.nvidia.com"],
            "accessMethod": "filing",
            "tier": "primary",
            "costUsd": 0.0,
            "license": "public",
            "refresh": "quarterly",
            "indicators": ["D2"],
        }
    ],
}

PAYWALLED_SOURCE = {
    "id": "trendforce-gpu",
    "label": "TrendForce GPU tracker",
    "urlPatterns": ["trendforce.com"],
    "accessMethod": "licensed-api",
    "tier": "secondary",
    "costUsd": 5000.0,
    "license": "licensed",
    "refresh": "quarterly",
    "indicators": ["market-share-pct"],
    "paywalledNote": "Subscription required.",
}


# ── Model validation tests ───────────────────────────────────────────────────

def test_manifest_loads_valid_json():
    m = CoverageManifest(**MINIMAL_MANIFEST)
    assert m.categoryId == "chips.merchant-gpu"
    assert len(m.expectedIndicators) == 1
    assert len(m.expectedSources) == 1


def test_manifest_rejects_unknown_priority():
    bad = {**MINIMAL_MANIFEST}
    bad["expectedIndicators"] = [
        {**MINIMAL_MANIFEST["expectedIndicators"][0], "priority": "critical"}
    ]
    with pytest.raises(Exception):  # Pydantic ValidationError
        CoverageManifest(**bad)


def test_manifest_rejects_unknown_access_method():
    bad = {**MINIMAL_MANIFEST}
    bad["expectedSources"] = [
        {**MINIMAL_MANIFEST["expectedSources"][0], "accessMethod": "ftp"}
    ]
    with pytest.raises(Exception):
        CoverageManifest(**bad)


# ── load_manifest tests ──────────────────────────────────────────────────────

def test_load_manifest_missing_file():
    with pytest.raises(ManifestLoadError, match="not found"):
        load_manifest("/nonexistent/path/manifest.json")


def test_load_manifest_invalid_json(tmp_path):
    bad_file = tmp_path / "manifest.json"
    bad_file.write_text("not json", encoding="utf-8")
    with pytest.raises(ManifestLoadError, match="invalid JSON"):
        load_manifest(bad_file)


def test_load_manifest_schema_failure(tmp_path):
    bad = {"version": "1.0", "categoryId": "chips.merchant-gpu"}  # missing required fields
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ManifestLoadError, match="schema"):
        load_manifest(f)


def test_load_manifest_valid(tmp_path):
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps(MINIMAL_MANIFEST), encoding="utf-8")
    m = load_manifest(f)
    assert m.categoryId == "chips.merchant-gpu"


# ── compute_coverage_gaps tests ──────────────────────────────────────────────

def test_no_gaps_when_all_covered():
    manifest = CoverageManifest(**MINIMAL_MANIFEST)
    blob_urls = ["https://investor.nvidia.com/quarterly-earnings/q1-2026"]
    found = {"D2"}
    gaps = compute_coverage_gaps(manifest, blob_urls, found)
    assert gaps == []


def test_gap_when_source_url_not_matched():
    manifest = CoverageManifest(**MINIMAL_MANIFEST)
    blob_urls = ["https://some-other-site.com/article"]  # no investor.nvidia.com
    found = set()
    gaps = compute_coverage_gaps(manifest, blob_urls, found)
    source_gap = next(g for g in gaps if g.type == "source")
    assert source_gap.id == "nvda-earnings"
    assert source_gap.acquisitionStatus == "not-covered"


def test_gap_when_indicator_not_in_found_set():
    manifest = CoverageManifest(**MINIMAL_MANIFEST)
    blob_urls = ["https://investor.nvidia.com/q1-2026"]  # source covered
    found: set[str] = set()  # but no D2 finding produced
    gaps = compute_coverage_gaps(manifest, blob_urls, found)
    indicator_gap = next((g for g in gaps if g.type == "indicator"), None)
    assert indicator_gap is not None
    assert indicator_gap.id == "D2"
    assert indicator_gap.acquisitionStatus == "not-covered"


def test_paywalled_source_becomes_gap_immediately():
    manifest_data = {
        **MINIMAL_MANIFEST,
        "expectedIndicators": [
            {
                "indicatorId": "market-share-pct",
                "dimension": "moat",
                "priority": "required",
                "sourceIds": ["trendforce-gpu"],
            }
        ],
        "expectedSources": [PAYWALLED_SOURCE],
    }
    manifest = CoverageManifest(**manifest_data)
    gaps = compute_coverage_gaps(manifest, blob_urls=[], found_indicator_ids=set())
    paywalled = next(g for g in gaps if g.id == "trendforce-gpu")
    assert paywalled.acquisitionStatus == "paywalled"
    assert paywalled.type == "source"


def test_real_manifest_indicator_ids_all_resolve_in_registry():
    """Seam guard: every expectedIndicator.indicatorId in the shipped manifest
    must resolve to a real registry indicator. strategicRisk is a DIMENSION,
    not an indicator id; the real ids are exportControlExposure and
    customerConcentration."""
    from gpu_agent.registry.indicators import IndicatorRegistry

    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    for entry in manifest.expectedIndicators:
        reg.resolve(entry.indicatorId)  # must not raise


def test_required_vs_preferred_gap_priority():
    manifest_data = {
        **MINIMAL_MANIFEST,
        "expectedIndicators": [
            {"indicatorId": "D2", "dimension": "momentum", "priority": "required",
             "sourceIds": ["nvda-earnings"]},
            {"indicatorId": "grossMargin", "dimension": "unitEconomics", "priority": "preferred",
             "sourceIds": ["nvda-earnings"]},
        ],
    }
    manifest = CoverageManifest(**manifest_data)
    gaps = compute_coverage_gaps(manifest, blob_urls=[], found_indicator_ids=set())
    required_gaps = [g for g in gaps if g.priority == "required"]
    preferred_gaps = [g for g in gaps if g.priority == "preferred"]
    assert len(required_gaps) >= 1
    assert len(preferred_gaps) >= 1
