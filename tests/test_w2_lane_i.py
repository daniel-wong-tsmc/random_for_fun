"""Wave-2 Lane I: coverage matching (F28a/F28b) + honest LLM backends (F40).

F28a — host-aware URL matching + mirrorPatterns (this section).
F28b — structured, auditable coverage overrides (added by Task 2).
F40  — ClaudeCodeClient is an honest signpost (added by Task 3).
"""
from gpu_agent.manifest import (
    CoverageManifest,
    compute_coverage_gaps,
    load_manifest,
    _url_matches,
)


# ── F28a: _url_matches (pure helper) ─────────────────────────────────────────

def test_url_matches_bare_host_pattern_exact_host():
    assert _url_matches("https://sec.gov/Archives/x", "sec.gov")


def test_url_matches_bare_host_pattern_subdomain():
    assert _url_matches("https://www.sec.gov/Archives/edgar/data/x", "sec.gov")


def test_url_matches_bare_host_pattern_does_not_over_match_query_string():
    # host is evil.com; "sec.gov" only appears in the query string, not the host.
    assert not _url_matches("https://evil.com/?ref=sec.gov", "sec.gov")


def test_url_matches_bare_host_pattern_does_not_match_unrelated_host():
    assert not _url_matches("https://some-other-site.com/article", "investor.nvidia.com")


def test_url_matches_path_pattern_keeps_substring_semantics():
    assert _url_matches(
        "https://investor.nvidia.com/annual-reports/2026-10k",
        "investor.nvidia.com/annual-reports",
    )
    assert not _url_matches(
        "https://investor.nvidia.com/quarterly-earnings/q1-2026",
        "investor.nvidia.com/annual-reports",
    )


# ── F28a: compute_coverage_gaps + mirrorPatterns ─────────────────────────────

NVDA_MIRROR_MANIFEST = {
    "version": "1.0",
    "categoryId": "chips.merchant-gpu",
    "asOf": "2026-06",
    "expectedIndicators": [],
    "expectedSources": [
        {
            "id": "nvda-earnings",
            "label": "NVIDIA earnings",
            "urlPatterns": ["investor.nvidia.com", "sec.gov"],
            "mirrorPatterns": ["s201.q4cdn.com"],
            "accessMethod": "filing",
            "tier": "primary",
            "refresh": "quarterly",
        }
    ],
}


def test_mirror_pattern_covers_source_when_only_mirror_url_present():
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    blob_urls = ["https://s201.q4cdn.com/141608511/files/doc_financials/10q.pdf"]
    gaps = compute_coverage_gaps(manifest, blob_urls, set())
    assert not any(g.type == "source" and g.id == "nvda-earnings" for g in gaps)


def test_source_still_gaps_when_neither_pattern_nor_mirror_present():
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    gaps = compute_coverage_gaps(manifest, ["https://unrelated.example/x"], set())
    assert any(g.type == "source" and g.id == "nvda-earnings" for g in gaps)


def test_expected_source_mirror_patterns_default_to_empty_list():
    from gpu_agent.manifest import ExpectedSource
    src = ExpectedSource(
        id="x", label="X", accessMethod="free-web", tier="secondary", refresh="daily",
    )
    assert src.mirrorPatterns == []


# ── F28a: shipped manifest pins the review's exact false gaps ───────────────

def test_shipped_manifest_nvda_earnings_has_q4cdn_mirror():
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    src = manifest.source_by_id("nvda-earnings")
    assert "s201.q4cdn.com" in src.mirrorPatterns


def test_shipped_manifest_nvda_10k_risk_factors_has_q4cdn_mirror():
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    src = manifest.source_by_id("nvda-10k-risk-factors")
    assert "s201.q4cdn.com" in src.mirrorPatterns


def test_shipped_manifest_bis_export_controls_has_www_bis_gov_mirror():
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    src = manifest.source_by_id("bis-export-controls")
    assert "www.bis.gov" in src.mirrorPatterns


def test_shipped_manifest_nvda_10q_via_q4cdn_covers_nvda_earnings():
    """Pin the review's exact false gap: the 10-Q served from NVIDIA's q4cdn mirror
    must count as coverage for nvda-earnings."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    blob_urls = ["https://s201.q4cdn.com/141608511/files/doc_financials/10q.pdf"]
    gaps = compute_coverage_gaps(manifest, blob_urls, set())
    assert not any(g.type == "source" and g.id == "nvda-earnings" for g in gaps)


def test_shipped_manifest_bis_press_release_via_www_bis_gov_covers_bis_export_controls():
    """Pin the review's exact false gap: BIS press releases served from www.bis.gov
    must count as coverage for bis-export-controls."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    blob_urls = ["https://www.bis.gov/press-release/x"]
    gaps = compute_coverage_gaps(manifest, blob_urls, set())
    assert not any(g.type == "source" and g.id == "bis-export-controls" for g in gaps)


def test_shipped_manifest_host_matching_does_not_over_match_evil_host():
    """evil.com/?ref=sec.gov must NOT be treated as covering any sec.gov-patterned source:
    the host is evil.com, not sec.gov."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    blob_urls = ["https://evil.com/?ref=sec.gov"]
    gaps = compute_coverage_gaps(manifest, blob_urls, set())
    assert any(g.type == "source" and g.id == "nvda-earnings" for g in gaps)


def test_shipped_manifest_path_bearing_pattern_keeps_substring_semantics():
    """investor.nvidia.com/annual-reports is a path-bearing pattern on nvda-10k-risk-factors;
    it must still match via substring, not host equality."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    blob_urls = ["https://investor.nvidia.com/annual-reports/2026-10k.pdf"]
    gaps = compute_coverage_gaps(manifest, blob_urls, set())
    assert not any(g.type == "source" and g.id == "nvda-10k-risk-factors" for g in gaps)
