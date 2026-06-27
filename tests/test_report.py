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
from pathlib import Path
import pytest
from gpu_agent.schema.scorecard import Scorecard

FIX = Path("fixtures/report")
CURRENT = FIX / "legacy-current.json"
PRIOR = FIX / "legacy-prior.json"
POSTB = FIX / "postb-scorecard.json"


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
