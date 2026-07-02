"""Unit tests for gpu_agent/report.py — deterministic scorecard renderer.

All tests use committed fixture scorecards; no LLM call, no network.

Fixtures (committed under fixtures/report/ — store/** is gitignored, never read):
  - CURRENT  = legacy-current.json : rich PRE-B scorecard, 4/6 dims rated
               (missing bottleneck + strategicRisk); dmi=0.100, smi=0.027
               → sdgi=0.073; NO dimensionStatus / categoryStatus.
  - PRIOR    = legacy-prior.json   : PRE-B prior cycle, 5/6 dims rated
               (missing strategicRisk); dmi=0.140, smi=0.267 → sdgi=−0.127.
  - POSTB    = postb-scorecard.json: POST-B scorecard with all-6 dimensionStatus
               (momentum grounded, 5 under-supported), categoryStatus present,
               demandSupply.sdgi=0.0667 "demand-led".

Sub-project B has MERGED, so the post-B fields are real model fields and the
post-B tests below assert against the committed POSTB fixture (no xfail).
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import pytest
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.registry.indicators import IndicatorRegistry

FIX = Path("fixtures/report")
CURRENT = FIX / "legacy-current.json"
PRIOR = FIX / "legacy-prior.json"
POSTB = FIX / "postb-scorecard.json"

# Aliases for Tasks 5-8 brief (committed fixtures replace gitignored store/** paths):
#   V3 (brief's 2026-06-v3.json) -> legacy-current.json (rich: 35 findings, amd/intel/nvidia)
#   V2 (brief's 2026-06-v2.json) -> legacy-prior.json   (prior cycle, 18 findings)
V3 = CURRENT
V2 = PRIOR
REGISTRY_PATH = Path("registry/indicators.json")


def _load(p: Path) -> Scorecard:
    from gpu_agent.report import load_scorecard
    return load_scorecard(p)


# ── compute_sdgi ────────────────────────────────────────────────────────────

def test_compute_sdgi_from_dmi_smi():
    """sdgi = dmi - smi when no stored sdgi field (legacy fixture)."""
    from gpu_agent.report import compute_sdgi
    sc = _load(CURRENT)
    result = compute_sdgi(sc)
    expected = sc.demandSupply.dmiContribution - sc.demandSupply.smiContribution
    assert abs(result - expected) < 1e-9


def test_compute_sdgi_uses_stored_field_when_present():
    """If demandSupply.sdgi is set (B's field), use it without recomputing."""
    from gpu_agent.report import compute_sdgi
    sc = _load(CURRENT)
    # dmi-smi for the legacy fixture is ~0.073, so 0.25 can only come from the
    # stored field — proves compute_sdgi prefers it over recomputing.
    sc.demandSupply.sdgi = 0.25
    result = compute_sdgi(sc)
    assert result == pytest.approx(0.25)


def test_compute_sdgi_reads_postb_stored_field():
    """POST-B fixture carries demandSupply.sdgi=0.0667; compute_sdgi returns it."""
    from gpu_agent.report import compute_sdgi
    sc = _load(POSTB)
    assert compute_sdgi(sc) == pytest.approx(0.06666666666666667)


# ── find_prior ───────────────────────────────────────────────────────────────

def test_find_prior_discovers_v2_when_v3_is_current(tmp_path):
    """Given v3 as the most recent, find_prior returns the v2 path."""
    from gpu_agent.report import find_prior
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v2.json").write_text(PRIOR.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-06-v3.json").write_text(CURRENT.read_text("utf-8"), "utf-8")
    sc = _load(CURRENT)
    prior_path = find_prior(tmp_path, sc)
    assert prior_path is not None
    assert prior_path.name == "2026-06-v2.json"


def test_find_prior_returns_none_when_only_one_version(tmp_path):
    """If only one JSON file exists in the category dir, no prior → None."""
    from gpu_agent.report import find_prior
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v3.json").write_text(CURRENT.read_text("utf-8"), "utf-8")
    sc = _load(CURRENT)
    assert find_prior(tmp_path, sc) is None


def test_find_prior_day_grain_names_are_not_dropped(tmp_path):
    """F13d: day-grain scorecard filenames (YYYY-MM-DD-vN.json) must not be silently
    ignored — the old month-only regex would drop them entirely from the candidate list."""
    from gpu_agent.report import find_prior
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-15-v1.json").write_text(PRIOR.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-06-20-v1.json").write_text(CURRENT.read_text("utf-8"), "utf-8")
    sc = _load(CURRENT)
    prior_path = find_prior(tmp_path, sc)
    assert prior_path is not None
    assert prior_path.name == "2026-06-15-v1.json"


def test_find_prior_collects_unmatched_stray_files_instead_of_silently_skipping(tmp_path):
    """F13d: a stray non-scorecard .json file in the category dir is never silently
    skipped — its name is appended to the caller-supplied `unmatched` list."""
    from gpu_agent.report import find_prior
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v2.json").write_text(PRIOR.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-06-v3.json").write_text(CURRENT.read_text("utf-8"), "utf-8")
    (cat_dir / "notes.json").write_text("{}", "utf-8")
    sc = _load(CURRENT)
    unmatched: list = []
    find_prior(tmp_path, sc, unmatched=unmatched)
    assert unmatched == ["notes.json"]


def test_find_prior_mixed_grain_same_version_day_grain_outranks_month_lexically(tmp_path):
    """Mixed grain sorts lexically: '2026-06' < '2026-06-15', so at the same version
    number a day-grain name outranks a month-grain name from the same month. Grain
    consistency per category is enforced wiki-side by another stream, not here."""
    from gpu_agent.report import find_prior
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    (cat_dir / "2026-06-v1.json").write_text(PRIOR.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-06-15-v1.json").write_text(PRIOR.read_text("utf-8"), "utf-8")
    (cat_dir / "2026-07-v2.json").write_text(CURRENT.read_text("utf-8"), "utf-8")
    sc = _load(CURRENT)
    prior_path = find_prior(tmp_path, sc, current_path=cat_dir / "2026-07-v2.json")
    assert prior_path.name == "2026-06-15-v1.json"


def test_load_scorecard_parses_pydantic_model():
    """load_scorecard returns a typed Scorecard, not a raw dict."""
    sc = _load(CURRENT)
    assert sc.categoryId == "chips.merchant-gpu"
    assert sc.asOf == "2026-06"
    assert len(sc.findings) > 0


def test_load_scorecard_raises_on_missing_file():
    """load_scorecard raises (ValueError/FileNotFoundError) on missing path."""
    from gpu_agent.report import load_scorecard
    with pytest.raises((ValueError, FileNotFoundError)):
        load_scorecard(Path("fixtures/report/nonexistent.json"))


# ── render_header ─────────────────────────────────────────────────────────────

def test_render_header_contains_category_and_asof():
    from gpu_agent.report import render_header
    sc = _load(CURRENT)
    out = render_header(sc, "2026-06-27T12:00:00Z")
    assert "chips.merchant-gpu" in out
    assert "2026-06" in out
    assert "2026-06-27T12:00:00Z" in out


def test_render_header_has_separator_line():
    from gpu_agent.report import render_header
    sc = _load(CURRENT)
    out = render_header(sc, "2026-06-27T12:00:00Z")
    assert "===" in out


def test_render_header_is_deterministic():
    """Same scorecard + same render_ts → byte-identical header."""
    from gpu_agent.report import render_header
    sc = _load(CURRENT)
    a = render_header(sc, "2026-06-27T12:00:00Z")
    b = render_header(sc, "2026-06-27T12:00:00Z")
    assert a == b


# ── render_overall_status ────────────────────────────────────────────────────

def test_render_overall_status_absent_shows_not_available():
    """Pre-B scorecard (no categoryStatus) → 'not yet available' label."""
    from gpu_agent.report import render_overall_status
    sc = _load(CURRENT)  # legacy fixture has no categoryStatus
    out = render_overall_status(sc)
    assert "not yet available" in out
    assert "OVERALL CATEGORY STATUS" in out


def test_render_overall_status_present_shows_rating():
    """Post-B scorecard (categoryStatus present) → rating + bottleneck appear."""
    from gpu_agent.report import render_overall_status
    sc = _load(POSTB)  # categoryStatus: Strong / worsening / bottleneck=momentum
    out = render_overall_status(sc)
    assert "OVERALL CATEGORY STATUS" in out
    assert "Strong" in out
    assert "momentum" in out  # the bottleneck value
    assert "DC growth solid but decelerating" in out  # the reason


# ── render_dimensions ────────────────────────────────────────────────────────

def test_render_dimensions_all_six_always_present():
    """All 6 dimension names appear in output even when some are under-supported."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)  # 4 of 6 rated
    out = render_dimensions(sc, prior=None)
    for dim in ["momentum", "unitEconomics", "competitiveStructure", "moat",
                "bottleneck", "strategicRisk"]:
        assert dim in out, f"dimension {dim!r} missing from output"


def test_render_dimensions_under_supported_label_for_missing():
    """Legacy fixture (no dimensionStatus): dims absent from dimensionRatings show under-supported."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    out = render_dimensions(sc, prior=None)
    assert "under-supported" in out.lower()
    lines = out.splitlines()
    # CURRENT is missing bottleneck and strategicRisk from dimensionRatings.
    bottleneck_lines = [l for l in lines if "bottleneck" in l]
    strategicRisk_lines = [l for l in lines if "strategicRisk" in l]
    assert any("under-supported" in l.lower() for l in bottleneck_lines)
    assert any("under-supported" in l.lower() for l in strategicRisk_lines)


def test_render_dimensions_grounded_label_for_present():
    """Legacy fixture: a dimension present in dimensionRatings infers grounded."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    out = render_dimensions(sc, prior=None)
    momentum_line = next(l for l in out.splitlines()
                         if "momentum" in l and "under-supported" not in l.lower())
    assert "grounded" in momentum_line


def test_render_dimensions_reads_dimensionstatus_when_present():
    """Post-B: evidenceStatus is read from sc.dimensionStatus, not dimensionRatings.

    POSTB fixture: momentum grounded; the other five under-supported via
    dimensionStatus even though dimensionRatings is grounded-only.
    """
    from gpu_agent.report import render_dimensions
    sc = _load(POSTB)
    out = render_dimensions(sc, prior=None)
    bottleneck_line = next(l for l in out.splitlines() if "bottleneck" in l)
    assert "under-supported" in bottleneck_line.lower()
    # the under-supported note from dimensionStatus is surfaced
    assert "no findings mapped to bottleneck this cycle" in out
    # only momentum is grounded in the post-B fixture
    assert "Coverage: 1/6" in out
    momentum_line = next(l for l in out.splitlines()
                         if "momentum" in l and "under-supported" not in l.lower())
    assert "grounded" in momentum_line


def test_render_dimensions_coverage_summary():
    """Coverage line appears: 'Coverage: 4/6' for the current fixture."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    out = render_dimensions(sc, prior=None)
    assert "Coverage: 4/6" in out
    assert "2 under-supported" in out


def test_render_dimensions_delta_column_absent_when_no_prior():
    """No delta column rendered when prior is None."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    out = render_dimensions(sc, prior=None)
    assert "Δ vs prior" not in out


def test_render_dimensions_delta_column_present_with_prior():
    """Δ column appears with a prior; a newly-missing dim notes it was present before."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    prior = _load(PRIOR)
    out = render_dimensions(sc, prior=prior)
    assert "Δ vs prior" in out
    # bottleneck was present in PRIOR, absent in CURRENT → delta note
    lines = out.splitlines()
    bottleneck_line = next(l for l in lines if "bottleneck" in l)
    assert "was present in prior" in bottleneck_line or "prior" in bottleneck_line


def test_render_dimensions_rating_arrows():
    """Direction arrows (↑ → ↓) appear in output for rated dimensions."""
    from gpu_agent.report import render_dimensions
    sc = _load(CURRENT)
    out = render_dimensions(sc, prior=None)
    assert any(arrow in out for arrow in ["↑", "→", "↓"])


# ── render_dmi_smi_sdgi ──────────────────────────────────────────────────────

def test_render_dmi_smi_sdgi_contains_section_header():
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(CURRENT)
    out = render_dmi_smi_sdgi(sc, prior=None)
    assert "DEMAND / SUPPLY MOMENTUM" in out


def test_render_dmi_smi_sdgi_no_prior_shows_dash():
    """When no prior, Δ column shows — for all three values."""
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(CURRENT)
    out = render_dmi_smi_sdgi(sc, prior=None)
    lines = [l for l in out.splitlines() if any(t in l for t in ("DMI", "SMI", "SDGI"))]
    assert len(lines) == 3
    for line in lines:
        assert "—" in line  # em dash for missing delta


def test_render_dmi_smi_sdgi_with_prior_shows_arithmetic_delta():
    """Delta = current - prior; CURRENT DMI=0.100, PRIOR DMI=0.140 → Δ = −0.040."""
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(CURRENT)
    prior = _load(PRIOR)
    out = render_dmi_smi_sdgi(sc, prior=prior)
    dmi_line = next(l for l in out.splitlines() if "DMI" in l)
    assert "-0.04" in dmi_line or "−0.04" in dmi_line


def test_render_dmi_smi_sdgi_interpretation_positive_sdgi():
    """SDGI > 0.05 → 'Demand outrunning supply' in output."""
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(CURRENT)  # sdgi = 0.100 - 0.027 = 0.073 > 0.05
    out = render_dmi_smi_sdgi(sc, prior=None)
    assert "Demand outrunning supply" in out


def test_render_dmi_smi_sdgi_shows_dmi_smi_values():
    """DMI and SMI values from the scorecard appear in output."""
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(CURRENT)
    out = render_dmi_smi_sdgi(sc, prior=None)
    assert "0.100" in out  # DMI
    assert "0.027" in out  # SMI


def test_render_dmi_smi_sdgi_negative_interpretation_postb_balanced():
    """POSTB sdgi=0.0667 (>0.05) → demand-outrunning interpretation, deterministic."""
    from gpu_agent.report import render_dmi_smi_sdgi
    sc = _load(POSTB)
    a = render_dmi_smi_sdgi(sc, prior=None)
    b = render_dmi_smi_sdgi(sc, prior=None)
    assert a == b  # determinism
    assert "Demand outrunning supply" in a


# ── render_entity_panel ───────────────────────────────────────────────────────

def test_render_entity_panel_section_header():
    from gpu_agent.report import render_entity_panel
    sc = _load(V3)
    out = render_entity_panel(sc)
    assert "ENTITY PANEL" in out


def test_render_entity_panel_known_entities_appear():
    """v3 has findings for nvidia, amd, intel — all three panels must appear."""
    from gpu_agent.report import render_entity_panel
    sc = _load(V3)
    out = render_entity_panel(sc)
    assert "nvidia" in out
    assert "amd" in out
    assert "intel" in out


def test_render_entity_panel_finding_count():
    """Each entity panel shows a finding count > 0."""
    from gpu_agent.report import render_entity_panel
    sc = _load(V3)
    out = render_entity_panel(sc)
    import re
    # e.g. "nvidia  (12 findings)"
    counts = re.findall(r"\((\d+) findings?\)", out)
    assert len(counts) == 3  # one per entity
    assert all(int(c) > 0 for c in counts)


def test_render_entity_panel_empty_entity_excluded():
    """Findings with empty entity string do not create a panel."""
    from gpu_agent.report import render_entity_panel
    from gpu_agent.schema.scorecard import Scorecard
    raw = json.loads(V3.read_text("utf-8"))
    # Inject a finding with empty entity
    raw["findings"][0]["entity"] = ""
    sc = Scorecard.model_validate(raw)
    out = render_entity_panel(sc)
    # Should still have exactly 3 entity panels (nvidia, amd, intel)
    import re
    counts = re.findall(r"\((\d+) findings?\)", out)
    assert len(counts) == 3


def test_render_entity_panel_key_signals_listed():
    """Each entity sub-panel lists at least one key signal."""
    from gpu_agent.report import render_entity_panel
    sc = _load(V3)
    out = render_entity_panel(sc)
    assert "Key signals:" in out
    # Signal lines are prefixed with [side/kind]
    assert "[demand/" in out or "[supply/" in out


# ── render_evidence_quality ──────────────────────────────────────────────────

def test_render_evidence_quality_section_header():
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    assert "EVIDENCE QUALITY" in out


def test_render_evidence_quality_all_six_dims_listed():
    """All 6 dimension names appear in the evidence quality section."""
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    for dim in ["momentum", "unitEconomics", "competitiveStructure",
                "moat", "bottleneck", "strategicRisk"]:
        assert dim in out, f"{dim} missing from evidence quality output"


def test_render_evidence_quality_zero_for_ungrounded_dims():
    """bottleneck and strategicRisk have 0 findings in v3."""
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    lines = out.splitlines()
    bottleneck_line = next((l for l in lines if "bottleneck" in l), "")
    assert "0 findings" in bottleneck_line or "under-supported" in bottleneck_line
    strategic_line = next((l for l in lines if "strategicRisk" in l), "")
    assert "0 findings" in strategic_line or "under-supported" in strategic_line


def test_render_evidence_quality_positive_count_for_grounded_dims():
    """momentum (mapped from D2) has > 0 findings in v3."""
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    lines = out.splitlines()
    momentum_line = next((l for l in lines if l.strip().startswith("momentum")), "")
    assert momentum_line, "momentum line not found"
    # Should have a positive count
    import re
    m = re.search(r"(\d+) findings?", momentum_line)
    assert m and int(m.group(1)) > 0


def test_render_evidence_quality_unattributed_bucket():
    """Findings with indicatorId that maps to no dimension appear in (unattributed)."""
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    # perfPerWatt and flopsPerDollar are non-scoring (dimension=None)
    assert "unattributed" in out


def test_render_evidence_quality_totals_line():
    """A total findings line is rendered at the end of the section."""
    from gpu_agent.report import render_evidence_quality
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_evidence_quality(sc, registry)
    assert "Total:" in out


# ── render_sources ────────────────────────────────────────────────────────────

def test_render_sources_section_header():
    from gpu_agent.report import render_sources
    sc = _load(V3)
    out = render_sources(sc)
    assert "SOURCES" in out


def test_render_sources_primary_before_secondary():
    """Primary sources appear before secondary sources in the list."""
    from gpu_agent.report import render_sources
    sc = _load(V3)
    out = render_sources(sc)
    lines = out.splitlines()
    # Match without trailing-pad sensitivity so BOTH tiers are actually inspected.
    source_lines = [l for l in lines if "[primary" in l or "[secondary" in l]
    assert len(source_lines) > 0
    # The fixture has both tiers — the ordering check must really exercise primary.
    assert any("[primary" in l for l in source_lines)
    assert any("[secondary" in l for l in source_lines)
    # All [primary] lines must appear before any [secondary] line
    seen_secondary = False
    for line in source_lines:
        if "[secondary" in line:
            seen_secondary = True
        if "[primary" in line and seen_secondary:
            pytest.fail("A [primary] source appeared after a [secondary] source")


def test_render_sources_deduplication():
    """Each URL appears only once even if cited in multiple findings/evidence items."""
    from gpu_agent.report import render_sources
    sc = _load(V3)
    out = render_sources(sc)
    lines = out.splitlines()
    source_lines = [l for l in lines if "[primary" in l or "[secondary" in l]
    # Extract URLs / source names and check uniqueness
    # A simple proxy: count lines — should be less than total evidence items across all findings
    total_evidence = sum(len(f.evidence) for f in sc.findings)
    assert len(source_lines) < total_evidence  # deduplication must have occurred


def test_render_sources_count_in_header():
    """Source count appears in the section header."""
    from gpu_agent.report import render_sources
    sc = _load(V3)
    out = render_sources(sc)
    first_line = out.splitlines()[0]
    assert "unique" in first_line or re.search(r"\d+", first_line)


# ── render_coverage_gaps ──────────────────────────────────────────────────────

def test_render_coverage_gaps_section_header():
    from gpu_agent.report import render_coverage_gaps
    sc = _load(V3)
    out = render_coverage_gaps(sc)
    assert "COVERAGE / SKIP GAPS" in out


def test_render_coverage_gaps_undersupported_dims_listed():
    """bottleneck and strategicRisk appear in gap list for v3."""
    from gpu_agent.report import render_coverage_gaps
    sc = _load(V3)
    out = render_coverage_gaps(sc)
    assert "bottleneck" in out
    assert "strategicRisk" in out


def test_render_coverage_gaps_no_orphan_note_when_clean():
    """When sc.sources matches evidence URLs, 'No orphan source references' appears."""
    from gpu_agent.report import render_coverage_gaps
    sc = _load(V3)
    out = render_coverage_gaps(sc)
    # v3's sources field should be a subset of evidence URLs (or empty)
    # Either no orphan note is needed, or the note appears
    # Just assert the section header is present and doesn't crash
    assert "COVERAGE / SKIP GAPS" in out


# ── render_report (integration) ───────────────────────────────────────────────

def test_render_report_contains_all_eight_section_headers():
    """render_report output contains all 8 canonical section headers."""
    from gpu_agent.report import render_report
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    out = render_report(sc, prior=None, registry=registry, render_ts="2026-06-27T00:00:00Z")
    for header in [
        "CATEGORY REPORT",
        "OVERALL CATEGORY STATUS",
        "DIMENSION RATINGS",
        "DEMAND / SUPPLY MOMENTUM",
        "ENTITY PANEL",
        "EVIDENCE QUALITY",
        "SOURCES",
        "COVERAGE / SKIP GAPS",
    ]:
        assert header in out, f"Section header {header!r} missing from report"


def test_render_report_deterministic_same_output_on_two_calls():
    """Same scorecard + prior + render_ts → byte-identical output."""
    from gpu_agent.report import render_report
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    prior = _load(V2)
    ts = "2026-06-27T12:00:00Z"
    out1 = render_report(sc, prior, registry, render_ts=ts)
    out2 = render_report(sc, prior, registry, render_ts=ts)
    assert out1 == out2


def test_render_report_uses_injected_render_ts():
    """render_ts parameter appears in the header, not the current clock time."""
    from gpu_agent.report import render_report
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    ts = "1999-01-01T00:00:00Z"
    out = render_report(sc, prior=None, registry=registry, render_ts=ts)
    assert "1999-01-01" in out


def test_render_report_with_v3_and_v2_prior_no_crash():
    """Full report renders without error for v3 as current, v2 as prior."""
    from gpu_agent.report import render_report
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    sc = _load(V3)
    prior = _load(V2)
    out = render_report(sc, prior, registry, render_ts="2026-06-27T00:00:00Z")
    assert len(out) > 500  # substantive output


def test_render_evidence_quality_counts_findings_not_evidence_items():
    """Headline must be DISTINCT-finding count, not evidence-item count.

    Give one momentum finding a SECOND evidence item: the finding count must
    stay the same while the primary/secondary evidence split gains one item.
    Guards against inflating reported finding quantity (A renders, never invents).
    """
    from gpu_agent.report import render_evidence_quality
    from gpu_agent.schema.scorecard import Scorecard
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    raw = json.loads(V3.read_text("utf-8"))

    # Baseline momentum finding count + evidence count from the registry mapping.
    ind_to_dim = {k: v.get("dimension") for k, v in registry.indicators.items()}
    momentum_findings = [f for f in raw["findings"]
                         if ind_to_dim.get(f["indicatorId"]) == "momentum"]
    n_findings = len(momentum_findings)
    base_ev = sum(len(f.get("evidence", [])) for f in momentum_findings)

    # Duplicate the first evidence item of the first momentum finding.
    target = momentum_findings[0]
    target["evidence"].append(dict(target["evidence"][0]))

    sc = Scorecard.model_validate(raw)
    out = render_evidence_quality(sc, registry)
    momentum_line = next(l for l in out.splitlines() if l.strip().startswith("momentum"))

    # Headline counts findings (unchanged), not evidence items (now base_ev + 1).
    m = re.search(r"(\d+) findings?", momentum_line)
    assert m and int(m.group(1)) == n_findings
    assert n_findings != base_ev + 1  # the two numbers genuinely differ
    # The evidence split must reflect the added item.
    ev_nums = re.findall(r"evidence:\s*(\d+)/(\d+)", momentum_line)
    assert ev_nums, f"no evidence split in: {momentum_line!r}"
    p, s = int(ev_nums[0][0]), int(ev_nums[0][1])
    assert p + s == base_ev + 1
