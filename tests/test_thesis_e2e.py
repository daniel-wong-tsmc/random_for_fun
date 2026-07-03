"""Task 5 (sub-project 5-2, output surgery): the end-to-end acceptance render.

A full cycle, driven only through the real CLI (subprocess pattern per
tests/test_cli_thesis.py / tests/test_report_surgery.py -- no monkeypatching,
no calling internals directly):

  1. copy the committed scorecard `store/chips.merchant-gpu/2026-07-02-v1.json`
     into a tmp store (this file is checked in -- see the `git ls-files` assertion
     below; if it were ever removed, fixtures/report/postb-scorecard.json is the
     documented fallback used by tests/test_report_surgery.py).
  2. seed a thesis store + apply the committed clean-answer fixture via
     `gpu-agent thesis --recorded` (the same fixture consumed by test_cli_thesis.py;
     it cites golden finding ids and reaffirms all six seed theses).
  3. render `gpu-agent report` over that tmp store.
  4. assert the spec-§4 acceptance shape in one place: THE CALLS carries all six
     seed theses with verdicts (the all-reaffirmed "Nothing changed" compact path
     IS that rendering for this cycle shape); STATE speaks band words; WHY carries
     all three group headers; the raw DMI value is demoted below TRUST & COVERAGE;
     exit codes are 0 throughout.
  5. byte-determinism across two report invocations with a fixed --render-ts.

No source changes are expected here (Task 5's brief: this test adds no new
behavior). A failure here means Tasks 1-4 left a real integration gap that must
be fixed there, not patched from this file.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PY = sys.executable

CATEGORY = "chips.merchant-gpu"
AS_OF = "2026-07-02"
GOLDEN_FINDINGS = "fixtures/golden/findings.json"
CLEAN_ANSWER = Path("tests/fixtures/thesis-answer-clean.json")
COMMITTED_SCORECARD = Path("store/chips.merchant-gpu/2026-07-02-v1.json")
FALLBACK_SCORECARD = Path("fixtures/report/postb-scorecard.json")

SEED_IDS = [
    "nvda-demand-durability",
    "supply-constraint-binding",
    "amd-credible-second-source",
    "custom-asic-substitution",
    "pricing-power-persistence",
    "export-control-exposure",
]

BAND_WORDS = ("ACCELERATING", "FIRM", "FLAT", "SOFTENING", "CONTRACTING")


def _run(*args: str):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True,
                          text=True, encoding="utf-8", env=env)


def _find_all(haystack: str, needle: str) -> list[int]:
    idxs, start = [], 0
    while True:
        i = haystack.find(needle, start)
        if i == -1:
            return idxs
        idxs.append(i)
        start = i + 1


def _build_tmp_store(tmp_path: Path) -> tuple[Path, Path]:
    """tmp store with the committed scorecard copied in under the real store layout,
    plus a thesis book seeded + judged via the real CLI (`thesis --recorded` auto-seeds
    the store on first use, per gpu_agent.cli._thesis, then gates + applies in one call --
    the same shape as tests/test_cli_thesis.py's clean-answer scenario)."""
    scorecard_src = COMMITTED_SCORECARD if COMMITTED_SCORECARD.exists() else FALLBACK_SCORECARD
    assert scorecard_src.exists(), "neither the committed nor the fallback scorecard exists"

    store = tmp_path / "store"
    cat_dir = store / CATEGORY
    cat_dir.mkdir(parents=True)
    scorecard_path = cat_dir / scorecard_src.name
    scorecard_path.write_text(scorecard_src.read_text("utf-8"), "utf-8")

    applied = _run("thesis", "--recorded", str(CLEAN_ANSWER),
                   "--findings", GOLDEN_FINDINGS, "--store", str(store),
                   "--category", CATEGORY, "--as-of", AS_OF)
    assert applied.returncode == 0, applied.stderr
    for thesis_id in SEED_IDS:
        assert any(
            line.startswith(f"{thesis_id}: reaffirmed applied=")
            for line in applied.stdout.splitlines()
        ), applied.stdout

    return store, scorecard_path


def test_committed_scorecard_fixture_is_tracked_in_git():
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(COMMITTED_SCORECARD)],
        capture_output=True, text=True,
    )
    assert out.returncode == 0, (
        f"{COMMITTED_SCORECARD} is expected to be committed; "
        f"falling back to {FALLBACK_SCORECARD} for the render scenarios below"
    )


def test_full_cycle_report_leads_with_the_thesis_book(tmp_path):
    store, scorecard_path = _build_tmp_store(tmp_path)

    result = _run("report", "--scorecard", str(scorecard_path), "--store", str(store),
                  "--no-prior", "--render-ts", "2026-07-02T00:00:00Z")
    assert result.returncode == 0, result.stderr
    out = result.stdout

    # --- THE CALLS: all six seed theses, each with a verdict -------------------------
    # Every judgment in the clean-answer fixture reaffirms -- the all-reaffirmed cycle
    # brief.render_the_calls names with its compact "Nothing changed" path. That path
    # (headline + one book line per standing thesis) IS the six-theses-with-verdicts
    # rendering for this cycle shape; it replaces, not omits, the per-thesis detail.
    assert "Nothing changed this cycle. (6 theses reaffirmed)" in out

    i_calls = out.index("THE CALLS")
    i_state = out.index("STATE OF THE MARKET")
    calls_section = out[i_calls:i_state]
    compact_lines = [ln for ln in calls_section.splitlines() if ln.startswith("  ● ")]
    assert len(compact_lines) == 6, calls_section

    book = json.loads((store / "theses" / CATEGORY / "book.json").read_text("utf-8"))
    assert {e["id"] for e in book["entries"]} == set(SEED_IDS)
    for entry in book["entries"]:
        assert entry["lastVerdict"] == "reaffirmed", entry
        assert any(
            entry["title"] in ln and "reaffirmed =" in ln for ln in compact_lines
        ), (entry["id"], calls_section)

    # --- STATE OF THE MARKET: words-first band, not a raw number ---------------------
    i_why = out.index("WHY")
    state_section = out[i_state:i_why]
    assert "Demand: " in state_section
    assert any(marker in state_section for marker in ("(was ", "(no prior)"))
    demand_line = next(ln for ln in state_section.splitlines() if "Demand: " in ln)
    assert any(word in demand_line for word in BAND_WORDS), demand_line
    assert "DMI" not in demand_line

    # --- WHY: all three group headers present -----------------------------------------
    i_what_moved = out.index("WHAT MOVED")
    why_section = out[i_why:i_what_moved]
    assert "Pulling demand:" in why_section
    assert "Capping supply:" in why_section
    assert "Contested:" in why_section

    # --- raw DMI value demoted below the fold: only after TRUST & COVERAGE ------------
    i_trust = out.index("TRUST & COVERAGE")
    dmi_occurrences = _find_all(out, "DMI 0.")
    assert dmi_occurrences, "expected the raw DMI value in the trust footer table"
    for idx in dmi_occurrences:
        assert idx > i_trust, (
            f"raw 'DMI 0.' value leaked before the TRUST & COVERAGE heading at index {idx}"
        )


def test_report_is_byte_deterministic_across_two_runs(tmp_path):
    store, scorecard_path = _build_tmp_store(tmp_path)

    args = ["report", "--scorecard", str(scorecard_path), "--store", str(store),
            "--no-prior", "--render-ts", "2026-07-02T00:00:00Z"]
    first = _run(*args)
    second = _run(*args)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
