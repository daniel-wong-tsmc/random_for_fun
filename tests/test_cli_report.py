"""CLI integration tests for `gpu-agent report`.

Uses subprocess so we test the real CLI entrypoint, not just the handler.
All tests run against committed fixture scorecards — no LLM, no network.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

V3 = "store/chips.merchant-gpu/2026-06-v3.json"
V2 = "store/chips.merchant-gpu/2026-06-v2.json"

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
    import os
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


def test_cli_report_exits_zero_with_all_section_headers():
    """Basic smoke test: exit 0, all 8 section headers in output."""
    result = _run("report", "--scorecard", V3, "--no-prior")
    assert result.returncode == 0, result.stderr
    for header in SECTION_HEADERS:
        assert header in result.stdout, f"Missing section header: {header!r}"


def test_cli_report_with_explicit_prior_shows_delta():
    """--prior causes Δ column to appear in DIMENSION RATINGS."""
    result = _run("report", "--scorecard", V3, "--prior", V2)
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout


def test_cli_report_no_prior_flag_suppresses_delta():
    """--no-prior: Δ column does not appear."""
    result = _run("report", "--scorecard", V3, "--no-prior")
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" not in result.stdout


def test_cli_report_auto_discovers_prior_via_store():
    """Without --prior or --no-prior, v2 is auto-discovered from --store."""
    result = _run("report", "--scorecard", V3, "--store", "store")
    assert result.returncode == 0, result.stderr
    # auto-discovery should find v2; delta column appears
    assert "Δ vs prior" in result.stdout


def test_cli_report_out_file_writes_and_reports_path():
    """--out <file> writes the report to a file and prints 'wrote <path>'."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    result = _run("report", "--scorecard", V3, "--no-prior", "--out", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "wrote" in result.stdout
    content = Path(tmp_path).read_text("utf-8")
    assert "CATEGORY REPORT" in content
    Path(tmp_path).unlink(missing_ok=True)


def test_cli_report_bad_scorecard_exits_nonzero():
    """Nonexistent scorecard path → non-zero exit with an error message."""
    result = _run("report", "--scorecard", "store/nonexistent/file.json", "--no-prior")
    assert result.returncode != 0
    assert result.stderr or "Error" in result.stdout or "error" in result.stdout


def test_cli_report_undersupported_dims_in_output():
    """v3 has bottleneck and strategicRisk under-supported; both appear in output."""
    result = _run("report", "--scorecard", V3, "--no-prior")
    assert result.returncode == 0, result.stderr
    assert "under-supported" in result.stdout.lower()
    assert "bottleneck" in result.stdout
    assert "strategicRisk" in result.stdout


# ── find_prior correctness tests ─────────────────────────────────────────────


def test_cli_report_correct_prior_selection_v2_picks_v1_not_v3(tmp_path):
    """In a store with v1, v2, v3: rendering v2 must pick v1 as prior, NOT v3.

    This is the critical off-by-one guard: the old find_prior(newest==current)
    heuristic would return v2 when rendering v3, but return v3 (wrong!) when
    rendering v2. The fixed implementation excludes the current file by path
    and picks the highest version strictly below it.

    v1 DMI=0.067, v2 DMI=0.140, v3 DMI=0.100
    Rendering v2 with v1 as prior → delta DMI = 0.140 - 0.067 = +0.073
    Rendering v2 with v3 as prior (wrong) → delta DMI = 0.140 - 0.100 = +0.040
    """
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    for v in ("v1", "v2", "v3"):
        src = Path("store/chips.merchant-gpu") / f"2026-06-{v}.json"
        shutil.copy(str(src), str(cat_dir / f"2026-06-{v}.json"))

    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v2.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout
    # v1 prior yields delta DMI ~ +0.073; v3 prior (wrong) yields +0.040
    assert "+0.073" in result.stdout, (
        "Expected DMI delta +0.073 (v1 as prior) but got something else — "
        "possibly v3 was incorrectly selected as prior.\n" + result.stdout[:600]
    )


def test_cli_report_correct_prior_selection_v3_picks_v2(tmp_path):
    """Rendering v3 from a store with v1/v2/v3 correctly picks v2 as prior.

    v3 DMI=0.100, v2 DMI=0.140 → delta DMI = 0.100 - 0.140 = -0.040 (shows as minus sign).
    """
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    for v in ("v1", "v2", "v3"):
        src = Path("store/chips.merchant-gpu") / f"2026-06-{v}.json"
        shutil.copy(str(src), str(cat_dir / f"2026-06-{v}.json"))

    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v3.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "Δ vs prior" in result.stdout
    # v2 prior: delta DMI = 0.100 - 0.140 = -0.040 → rendered as "−0.040"
    assert "0.040" in result.stdout, (
        "Expected DMI delta 0.040 (v2 as prior) in output.\n" + result.stdout[:600]
    )


def test_cli_report_no_prior_when_only_one_version(tmp_path):
    """Only v3 in store → no prior found → --no-prior path; renders cleanly, exit 0."""
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    src = Path("store/chips.merchant-gpu/2026-06-v3.json")
    shutil.copy(str(src), str(cat_dir / "2026-06-v3.json"))

    result = _run(
        "report",
        "--scorecard", str(cat_dir / "2026-06-v3.json"),
        "--store", str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    # No prior → delta column absent
    assert "Δ vs prior" not in result.stdout
    assert "CATEGORY REPORT" in result.stdout


def test_cli_report_explicit_prior_overrides_store_discovery(tmp_path):
    """--prior <path> overrides auto-discovery regardless of what store holds."""
    cat_dir = tmp_path / "chips.merchant-gpu"
    cat_dir.mkdir(parents=True)
    for v in ("v1", "v2", "v3"):
        src = Path("store/chips.merchant-gpu") / f"2026-06-{v}.json"
        shutil.copy(str(src), str(cat_dir / f"2026-06-{v}.json"))

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
