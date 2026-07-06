#!/usr/bin/env python3
"""f74_guard.py -- does the working tree's store/cycle-log.json still hold the
committed, enriched run journal, or has it been clobbered back to a bare cycle-plan
skeleton?

Background (F74, resolved in code at commit 9a5f9b2 / merged 257cf1b, 2026-07-05):
`cycle-plan --out store/cycle-log.json` used to unconditionally overwrite the tracked
journal with a fresh plan skeleton on every run start, silently erasing the previous
run's session-authored journal (once for real, including the F71 sufficiency-bypass
record -- recovered only from git history). The CLI now refuses that overwrite
(gpu_agent/cli.py::_is_bare_plan / _cycle_plan) and a suite tripwire
(tests/test_store_cycle_log_integrity.py) fails the build if a bare skeleton is ever
committed. This script is the standing monitor: it re-checks the CURRENT working tree
independently of whether the code guard or the test happened to run, because (a) a
hand-edit or a stray script can still write the file directly, bypassing cycle-plan
entirely, and (b) an operator on an older branch/worktree without the F74 fix can still
hit the original bug.

STDLIB ONLY. Read-only: never writes, never runs cycle-plan, never touches git state.
Shells out to `git` (must be on PATH) and, best-effort, to `.venv`'s python -m pytest
for a second opinion from the real tripwire test (skipped gracefully if unavailable).

Usage (from repo root, or pass --repo):
    .venv/Scripts/python .claude/skills/desk-diagnostics-and-tooling/scripts/f74_guard.py
    .venv/Scripts/python ...\\f74_guard.py --repo C:\\path\\to\\random_for_fun
    .venv/Scripts/python ...\\f74_guard.py --no-pytest     # skip the pytest cross-check

Exit codes:
    0 = no clobber detected (working tree matches or exceeds HEAD's enrichment)
    1 = ALARM -- working tree holds a bare/degraded journal where HEAD (or the prior
        state) holds an enriched one; do NOT commit store/ until this is resolved
    2 = operator error (not a git repo, git not found, etc.)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

CYCLE_LOG_REL = "store/cycle-log.json"

# Mirrors gpu_agent/cli.py::_is_bare_plan and tests/test_store_cycle_log_integrity.py as of
# commit 9a5f9b2 (2026-07-05). If the CyclePlan/CycleEntry pydantic models ever change
# their field set, THIS constant drifts out of sync with the real guard (the real guard
# derives its key sets from the models themselves precisely to avoid that) -- re-verify
# with: `git show HEAD:gpu_agent/cli.py | grep -A3 _PLAN_TOP_KEYS`.
_PLAN_TOP_KEYS = {"scope", "entries", "stages"}
_PLAN_ENTRY_KEYS = {"category_id", "assignment_path", "status"}


def run(repo: Path, *args: str) -> tuple[int, str, str]:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout, proc.stderr


def find_repo_root(start: Path) -> Path | None:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                           capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def classify(payload) -> str:
    """Returns 'bare', 'enriched', or 'unrecognized'. A bare plan is a dict whose keys are
    a subset of _PLAN_TOP_KEYS (or that plus asOf/mode/capturedAt IF none carry real
    content) where every 'ready' entry's keys are a subset of _PLAN_ENTRY_KEYS. Anything
    else -- extra top-level keys (asOf with a real value, gather/gates/thesis/report blocks,
    a 'ready' entry with a scorecard/gates key) -- is enriched. Content that doesn't parse
    as the expected shapes at all is 'unrecognized' (refuse to guess; that's also what the
    real guard does -- unparseable content is refused, not silently treated as safe-to-replan)."""
    if not isinstance(payload, dict):
        return "unrecognized"
    entries = payload.get("entries")
    stages = payload.get("stages")
    if not isinstance(entries, list) or not isinstance(stages, list):
        return "unrecognized"
    has_asof = bool(payload.get("asOf"))
    extra_top = set(payload) - _PLAN_TOP_KEYS - {"asOf", "mode", "capturedAt"}
    if extra_top:
        return "enriched"
    if has_asof:
        return "enriched"
    for e in entries:
        if not isinstance(e, dict):
            return "unrecognized"
        if e.get("status") == "ready" and (set(e) - _PLAN_ENTRY_KEYS):
            return "enriched"
    return "bare"


def load_json_text(text: str):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def pytest_tripwire(repo: Path) -> str:
    """Best-effort second opinion from the real suite tripwire. Returns 'pass', 'fail',
    or 'unavailable' (no venv / pytest / test file found -- not an error, just no extra
    signal to report)."""
    py_candidates = [repo / ".venv" / "Scripts" / "python.exe", repo / ".venv" / "bin" / "python"]
    py = next((p for p in py_candidates if p.exists()), None)
    test_file = repo / "tests" / "test_store_cycle_log_integrity.py"
    if py is None or not test_file.exists():
        return "unavailable"
    proc = subprocess.run([str(py), "-m", "pytest", str(test_file), "-q"],
                          cwd=str(repo), capture_output=True, encoding="utf-8", errors="replace")
    return "pass" if proc.returncode == 0 else "fail"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd, auto-detected via git)")
    ap.add_argument("--no-pytest", action="store_true", help="skip the pytest cross-check")
    args = ap.parse_args()

    repo = find_repo_root(Path(args.repo))
    if repo is None:
        print(f"error: {args.repo} is not inside a git repo", file=sys.stderr)
        return 2

    path = repo / CYCLE_LOG_REL
    if not path.exists():
        print(f"OK: {CYCLE_LOG_REL} does not exist in the working tree -- nothing to guard "
              f"yet (fresh checkout or category never run).")
        return 0

    working_text = path.read_text(encoding="utf-8-sig", errors="replace")
    working_payload = load_json_text(working_text)
    working_class = classify(working_payload)

    code, head_text, _ = run(repo, "show", f"HEAD:{CYCLE_LOG_REL}")
    tracked = (code == 0)
    head_class = classify(load_json_text(head_text)) if tracked else "not-tracked"

    print(f"working tree: {CYCLE_LOG_REL} -> {working_class}")
    print(f"HEAD:         {CYCLE_LOG_REL} -> {head_class}")

    alarm = tracked and head_class == "enriched" and working_class == "bare"

    if alarm:
        print()
        print("ALARM: HEAD holds an enriched run journal but the working tree holds a bare "
              "cycle-plan skeleton -- this is the exact F74 clobber shape. Do NOT run "
              "`git add store/` or commit. Remediate: `git restore store/cycle-log.json` "
              "(after confirming no live/other instance owns the in-progress change), or "
              "diagnose what wrote the skeleton (the code guard in gpu_agent/cli.py should "
              "have refused this -- if it didn't, something bypassed cycle-plan or the guard "
              "itself regressed).")
    elif working_class == "unrecognized" or head_class == "unrecognized":
        print()
        print("NOTE: could not classify one side (unparseable JSON, unexpected shape, or a "
              "Windows BOM / directory at that path) -- inspect by hand: "
              f"`git diff {CYCLE_LOG_REL}`.")
    else:
        print()
        print("OK: no clobber pattern detected.")

    if not args.no_pytest:
        tw = pytest_tripwire(repo)
        if tw == "unavailable":
            print("(pytest cross-check: unavailable -- no .venv or test file found)")
        else:
            print(f"(pytest cross-check tests/test_store_cycle_log_integrity.py: {tw.upper()})")
            if tw == "fail":
                alarm = True

    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
