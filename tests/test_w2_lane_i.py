"""Wave-2 Lane I: coverage matching (F28a/F28b) + honest LLM backends (F40).

F28a — host-aware URL matching + mirrorPatterns.
F28b — structured, auditable coverage overrides.
F40  — ClaudeCodeClient is an honest signpost (this section).
"""
import subprocess
import sys
from pathlib import Path

from gpu_agent.manifest import (
    CoverageManifest,
    CoverageOverride,
    compute_coverage_gaps,
    load_manifest,
    _url_matches,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


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


# ── F28b: structured, auditable coverage overrides ───────────────────────────

def test_positional_call_compatibility_unaffected_by_new_param():
    """Gather skill scripts call compute_coverage_gaps(manifest, blob_urls, found)
    purely positionally; this must keep working with no `overrides` arg at all."""
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    gaps = compute_coverage_gaps(manifest, ["https://unrelated.example/x"], set())
    assert any(g.id == "nvda-earnings" for g in gaps)


def test_no_overrides_arg_is_byte_identical_to_before():
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    blob_urls = ["https://unrelated.example/x"]
    without_param = compute_coverage_gaps(manifest, blob_urls, set())
    with_none = compute_coverage_gaps(manifest, blob_urls, set(), overrides=None)
    assert [g.model_dump() for g in without_param] == [g.model_dump() for g in with_none]


def test_override_on_not_covered_source_marks_it_waived_and_keeps_it_visible():
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    blob_urls = ["https://unrelated.example/x"]
    original_gaps = compute_coverage_gaps(manifest, blob_urls, set())
    original_gap = next(g for g in original_gaps if g.id == "nvda-earnings")
    override = CoverageOverride(
        type="source", id="nvda-earnings",
        reason="mirror not yet catalogued, confirmed covered manually",
        waivedBy="gather-coordinator 2026-07-02",
    )
    gaps = compute_coverage_gaps(manifest, blob_urls, set(), overrides=[override])
    waived = next(g for g in gaps if g.id == "nvda-earnings")
    assert waived.acquisitionStatus == "waived"
    assert "mirror not yet catalogued, confirmed covered manually" in waived.reason
    assert "gather-coordinator 2026-07-02" in waived.reason
    assert original_gap.reason in waived.reason  # original reason preserved, never dropped
    # still returned — waived gaps stay visible, not silently removed
    assert waived in gaps


def test_override_naming_a_covered_item_changes_nothing():
    manifest = CoverageManifest(**NVDA_MIRROR_MANIFEST)
    blob_urls = ["https://s201.q4cdn.com/141608511/files/doc_financials/10q.pdf"]
    override = CoverageOverride(
        type="source", id="nvda-earnings", reason="n/a", waivedBy="tester",
    )
    gaps = compute_coverage_gaps(manifest, blob_urls, set(), overrides=[override])
    # nvda-earnings is covered by the mirror url; no gap is manufactured for it
    assert not any(g.id == "nvda-earnings" for g in gaps)


def test_override_on_indicator_gap_marks_it_waived():
    manifest_data = {
        **NVDA_MIRROR_MANIFEST,
        "expectedIndicators": [
            {"indicatorId": "D2", "dimension": "momentum", "priority": "required",
             "sourceIds": ["nvda-earnings"]},
        ],
    }
    manifest = CoverageManifest(**manifest_data)
    override = CoverageOverride(
        type="indicator", id="D2", reason="confirmed via analyst call", waivedBy="analyst-x",
    )
    gaps = compute_coverage_gaps(manifest, [], set(), overrides=[override])
    d2_gap = next(g for g in gaps if g.type == "indicator" and g.id == "D2")
    assert d2_gap.acquisitionStatus == "waived"
    assert "confirmed via analyst call" in d2_gap.reason
    assert "analyst-x" in d2_gap.reason


def test_coverage_gap_accepts_waived_acquisition_status():
    from gpu_agent.manifest import CoverageGap
    g = CoverageGap(type="source", id="x", priority="required",
                     acquisitionStatus="waived", reason="waived: ...")
    assert g.acquisitionStatus == "waived"


# ── F40: pipeline invoked live (no --recorded-extract) fails loud, not with an
#         AttributeError deep in the claude_agent_sdk ───────────────────────

def test_pipeline_live_without_recorded_extract_fails_loud_with_session_signpost(tmp_path):
    store = tmp_path / "store"
    proc = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "pipeline",
         "--docs", "fixtures/raw",
         "--assignment", "fixtures/asg.chips.merchant-gpu.json",
         "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z",
         "--samples", "3", "--out", str(store)],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    combined = proc.stdout + proc.stderr
    assert proc.returncode != 0, combined
    assert "--emit-prompt" in combined
    assert "--recorded" in combined
    assert "AttributeError" not in combined
    assert "claude_agent_sdk" not in combined
    assert not list(store.glob("**/*.json")), "pipeline must not write a scorecard when the LLM call fails loud"
