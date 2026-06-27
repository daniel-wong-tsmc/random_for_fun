"""CLI integration tests for `gpu-agent report`.

Uses subprocess so we test the real CLI entrypoint, not just the handler.
All tests run against COMMITTED fixture scorecards under fixtures/report/ —
no LLM, no network, and nothing under the gitignored store/** tree (so these
pass on a fresh clone / CI).

Fixtures:
  - legacy-current.json : rich PRE-B scorecard (35 findings; amd/intel/nvidia;
                          bottleneck + strategicRisk under-supported); DMI=0.100, SMI=0.027.
  - legacy-prior.json   : PRE-B prior cycle; DMI=0.140, SMI=0.267.
  - postb-scorecard.json: POST-B scorecard with categoryStatus + dimensionStatus.
  - prior-chain/2026-06-v{1,2,3}.json : a versioned chain for find_prior selection
                          (v1 DMI=0.067, v2 DMI=0.140, v3 DMI=0.100).
"""
from __future__ import annotations
import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FIX = "fixtures/report"
CURRENT = f"{FIX}/legacy-current.json"   # rich current cycle (was store v3)
PRIOR = f"{FIX}/legacy-prior.json"       # prior cycle (was store v2)
POSTB = f"{FIX}/postb-scorecard.json"
PRIOR_CHAIN = Path(FIX) / "prior-chain"  # 2026-06-v{1,2,3}.json (categoryless dir)

SECTION_HEADERS = [
    "CATEGORY REPORT",
    "OVERALL CATEGORY STATUS",
    "DIMENSION RATINGS",
    "DEMAND / SUPPLY MOMENTUM",
    "ENTITY PANEL",
    "EVIDENCE QUALITY",
    "SOURCES",
    "COVERAGE / SKIP GAPS",
]


def _run(*args: str):
    # Keep PYTHONIOENCODING for the subprocess decode, but the handler itself
    # reconfigures stdout to UTF-8 (the real production fix — see the direct
    # in-process encoding guard test below, which exercises a cp1252 stream).
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=".",  # repo root
    )


def _make_chain_store(tmp_path, versions):
    """Build a store dir <tmp>/chips.merchant-gpu/2026-06-v<N>.json from the
    committed prior-chain fixtures (NOT from store/**). Returns the category dir."""
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    for v in versions:
        src = PRIOR_CHAIN / f"2026-06-{v}.json"
        shutil.copy(str(src), str(cat_dir / f"2026-06-{v}.json"))
    return cat_dir


def test_cli_report_exits_zero_with_all_section_headers():
    """Basic smoke test: exit 0, all 8 section headers in output."""
    result = _run("report", "--scorecard", CURRENT, "--no-prior")
    assert result.returncode == 0, result.stderr
    for header in SECTION_HEADERS:
        assert header in result.stdout, f"Missing section header: {header!r}"


def test_cli_report_with_explicit_prior_shows_delta():
    """--prior causes Δ column to appear in DIMENSION RATINGS."""
    result = _run("report", "--scorecard", CURRENT, "--prior", PRIOR)
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout


def test_cli_report_no_prior_flag_suppresses_delta():
    """--no-prior: Δ column does not appear."""
    result = _run("report", "--scorecard", CURRENT, "--no-prior")
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" not in result.stdout


def test_cli_report_auto_discovers_prior_via_store(tmp_path):
    """Without --prior or --no-prior, the prior is auto-discovered from --store.

    Render v3 from a v1/v2/v3 chain → prior=v2 (DMI 0.140), delta column appears.
    """
    _make_chain_store(tmp_path, ("v1", "v2", "v3"))
    result = _run(
        "report",
        "--scorecard", str(tmp_path / "chips.merchant-gpu" / "2026-06-v3.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout


def test_cli_report_out_file_writes_and_reports_path():
    """--out <file> writes the report to a file and prints 'wrote <path>'."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    result = _run("report", "--scorecard", CURRENT, "--no-prior", "--out", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "wrote" in result.stdout
    content = Path(tmp_path).read_text("utf-8")
    assert "CATEGORY REPORT" in content
    Path(tmp_path).unlink(missing_ok=True)


def test_cli_report_bad_scorecard_exits_nonzero():
    """Nonexistent scorecard path → non-zero exit with an error message."""
    result = _run("report", "--scorecard", f"{FIX}/nonexistent-file.json", "--no-prior")
    assert result.returncode != 0
    assert result.stderr or "Error" in result.stdout or "error" in result.stdout


def test_cli_report_undersupported_dims_in_output():
    """legacy-current has bottleneck and strategicRisk under-supported; both appear."""
    result = _run("report", "--scorecard", CURRENT, "--no-prior")
    assert result.returncode == 0, result.stderr
    assert "under-supported" in result.stdout.lower()
    assert "bottleneck" in result.stdout
    assert "strategicRisk" in result.stdout


def test_cli_report_prior_and_no_prior_are_mutually_exclusive():
    """Passing both --prior and --no-prior is a clean argparse usage error (exit 2)."""
    result = _run(
        "report", "--scorecard", CURRENT, "--prior", PRIOR, "--no-prior",
    )
    assert result.returncode == 2
    assert "not allowed with" in result.stderr or "usage" in result.stderr.lower()


# ── find_prior correctness tests (prior-chain fixtures, NOT store/) ───────────


def test_cli_report_correct_prior_selection_v2_picks_v1_not_v3(tmp_path):
    """In a store with v1, v2, v3: rendering v2 must pick v1 as prior, NOT v3.

    This is the critical off-by-one guard: the old find_prior(newest==current)
    heuristic would return v3 (wrong!) when rendering v2. The fix excludes the
    current file by (asOf, version) and picks the highest version strictly below.

    v1 DMI=0.067, v2 DMI=0.140, v3 DMI=0.100
    Rendering v2 with v1 as prior → delta DMI = 0.140 - 0.067 = +0.073
    Rendering v2 with v3 as prior (wrong) → delta DMI = 0.140 - 0.100 = +0.040
    """
    cat_dir = _make_chain_store(tmp_path, ("v1", "v2", "v3"))
    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v2.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout
    assert "+0.073" in result.stdout, (
        "Expected DMI delta +0.073 (v1 as prior) but got something else — "
        "possibly v3 was incorrectly selected as prior.\n" + result.stdout[:600]
    )


def test_cli_report_correct_prior_selection_v3_picks_v2(tmp_path):
    """Rendering v3 from a v1/v2/v3 store correctly picks v2 as prior.

    v3 DMI=0.100, v2 DMI=0.140 → delta DMI = 0.100 - 0.140 = -0.040.
    """
    cat_dir = _make_chain_store(tmp_path, ("v1", "v2", "v3"))
    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v3.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout
    assert "0.040" in result.stdout, (
        "Expected DMI delta 0.040 (v2 as prior) in output.\n" + result.stdout[:600]
    )


def test_cli_report_no_prior_when_only_one_version(tmp_path):
    """Only v3 in store → no prior found → renders cleanly with no delta, exit 0."""
    cat_dir = _make_chain_store(tmp_path, ("v3",))
    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v3.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" not in result.stdout
    assert "CATEGORY REPORT" in result.stdout


def test_cli_report_explicit_prior_overrides_store_discovery(tmp_path):
    """--prior <path> overrides auto-discovery regardless of what store holds."""
    cat_dir = _make_chain_store(tmp_path, ("v1", "v2", "v3"))
    # Explicitly pass v1 as prior while rendering v3 (auto would pick v2)
    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v3.json"),
        "--prior", str(cat_dir / "2026-06-v1.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout
    # v1 prior: delta DMI = 0.100 - 0.067 = +0.033
    # v2 prior (auto, wrong): delta DMI = 0.100 - 0.140 = -0.040
    assert "+0.033" in result.stdout, (
        "Expected DMI delta +0.033 (explicit v1 prior) but store auto-discovery "
        "may have overridden the explicit --prior.\n" + result.stdout[:600]
    )


# ── encoding guard (CRITICAL 1): handler must not crash on a cp1252 stdout ────


def test_report_string_round_trips_to_utf8():
    """The rendered report contains non-ASCII glyphs (↑↓→ — Δ) yet encodes
    cleanly to UTF-8 — the bytes the handler must be able to write."""
    from gpu_agent.report import load_scorecard, render_report
    from gpu_agent.registry.indicators import IndicatorRegistry
    registry = IndicatorRegistry.load("registry/indicators.json")
    sc = load_scorecard(Path(CURRENT))
    prior = load_scorecard(Path(PRIOR))
    text = render_report(sc, prior, registry, render_ts="2026-06-27T00:00:00Z")
    assert text
    assert text.encode("utf-8")  # round-trips without raising
    # Sanity: glyphs that crash cp1252 really are present.
    assert any(g in text for g in ("↑", "↓", "→", "—", "Δ"))


def test_report_handler_does_not_crash_on_cp1252_stdout(monkeypatch):
    """_report must reconfigure stdout to UTF-8 so it does NOT raise
    UnicodeEncodeError when stdout is a cp1252-backed stream (the user's
    default Windows terminal). Without the reconfigure fix, print() raises.
    """
    from gpu_agent import cli
    buf = io.BytesIO()
    # Simulate a default Windows console: text stdout encoding cp1252.
    cp1252_stdout = io.TextIOWrapper(buf, encoding="cp1252", newline="")
    monkeypatch.setattr(sys, "stdout", cp1252_stdout)

    args = argparse.Namespace(
        scorecard=CURRENT, prior=None, no_prior=True, store=FIX,
        registry="registry/indicators.json", out=None,
    )
    rc = cli._report(args)  # must not raise
    cp1252_stdout.flush()
    assert rc == 0
    written = buf.getvalue()
    assert written, "handler produced no output"
    # The handler forced UTF-8, so the bytes decode as UTF-8 with the report.
    decoded = written.decode("utf-8")
    assert "CATEGORY REPORT" in decoded
