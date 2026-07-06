#!/usr/bin/env python3
"""eval_diagnostics.py -- read-only interpretation helpers for the F6/eval-v2 harness:
the committed baseline, a verdict.json, a report.json (pre- or post-verdict), the golden
case census by seam/gateOutcome, and cross-run seam-noise measurement.

STDLIB ONLY. Read-only: never runs `gpu-agent eval ...`, never dispatches anything, never
writes fixtures/evals/baseline.json or any run dir. This is strictly a reader over files
`eval emit-brain`/`record-brain`/`emit-grade`/`record-grade`/`verdict`/`rebaseline` already
produced -- it never substitutes for running the real harness (see run-eval / eval-driver
for that).

Usage (from repo root, or pass --repo):
    .venv/Scripts/python ...\\eval_diagnostics.py baseline
    .venv/Scripts/python ...\\eval_diagnostics.py case-census
    .venv/Scripts/python ...\\eval_diagnostics.py verdict <path/to/verdict.json>
    .venv/Scripts/python ...\\eval_diagnostics.py report <path/to/report.json>
    .venv/Scripts/python ...\\eval_diagnostics.py seam-noise <dir1> <dir2> [<dir3> ...]

Exit codes: 0 = read succeeded, no gate-relevant anomaly in the file(s) read; 1 = a verdict/
report shows a real fail/crater, or seam-noise finds spread exceeding the current epsilon
(informational alarm -- re-read the F73 note this prints before treating it as news);
2 = operator error (bad path, missing baseline, etc.)
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SEAMS = ("extract", "judge", "thesis")

_F73_NOTE = (
    "Context (F73, open, docs/fix-backlog.md): this repo's own run-notes document "
    "identical-PROMPT seam swings of 6.25-7.50 on a single seam across reruns (the F62/F63 "
    "eval saga) while eval-v2's epsilon is typically 0.19-0.5 per seam -- the F63 re-gate "
    "PASSED extract by 0.042 against a bar of 6.5833, 'deep inside noise' by the backlog's "
    "own words. A pass or fail margin smaller than that is not yet strong evidence of "
    "anything; the gate has never been demonstrated to catch a REAL regression "
    "(no seeded-regression canary exists yet). Route a fix for the gate's power, not a "
    "reaction to any one verdict, through F73 / desk-change-control."
)


def find_repo_root(start: Path) -> Path | None:
    import subprocess
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                           capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── baseline ──────────────────────────────────────────────────────────────────

def cmd_baseline(repo: Path) -> int:
    path = repo / "fixtures" / "evals" / "baseline.json"
    if not path.exists():
        print("no fixtures/evals/baseline.json", file=sys.stderr)
        return 2
    b = load_json(path)
    print(f"schemaVersion={b.get('schemaVersion')}  asOf={b.get('provenance', {}).get('asOf')}"
          f"  graderModel={b.get('provenance', {}).get('graderModel')}")
    for seam in SEAMS:
        mean = b["seamMeans"][seam]
        eps = b["epsilon"][seam]
        print(f"  {seam:8s} mean={mean:.4f}  epsilon={eps:.4f}  "
              f"PASS bar (mean-eps)={mean - eps:.4f}  HARD-FAIL bar (mean-2eps)={mean - 2*eps:.4f}")
    # Grouped BY SEAM: seams have different natural score ranges (thesis mean 6.0 vs
    # extract 6.75 vs judge 7.58, each over 4 criteria x 0-2), so ranking cases by raw
    # median ACROSS seams would misleadingly flag a merely-harder seam as "weakest".
    print("  per-case medians by seam (crater line = median-3, HARD crater = median-5):")
    by_seam: dict[str, list[tuple[str, int]]] = {s: [] for s in SEAMS}
    for case_id, median in b["caseMedians"].items():
        seam = case_id.split("-", 1)[0]
        by_seam.setdefault(seam, []).append((case_id, median))
    for seam in SEAMS:
        cases = sorted(by_seam.get(seam, []), key=lambda kv: kv[1])
        for case_id, median in cases:
            print(f"    {case_id:24s} median={median}  crater<= {median-3}  "
                  f"hard-crater<= {median-5}")
        if cases:
            min_median = cases[0][1]
            tied = [c for c, m in cases if m == min_median]
            print(f"    -> weakest within {seam}: {', '.join(tied)} (median {min_median}"
                  f"{', tied' if len(tied) > 1 else ''})")
    print()
    print("  Historical note (cited, not derived from the table above): the F63 re-gate "
          "run-notes name caseId extract-2026-07-05 as 'the weakest case across every run "
          "ever recorded' (scores observed in a 4-7 band, completeness the recurring 0 "
          "criterion) -- that is a claim about repeated LOW-SCORE VOLATILITY across many "
          "runs, not the same thing as 'lowest current median' (which can point at a "
          "different case, e.g. a thesis case, simply because that seam's rubric runs "
          "lower overall). Still undiagnosed: whether the case itself or the extract "
          "prompt is at fault has never been separated (open, F73-adjacent).")
    if b["provenance"].get("forceReason"):
        print(f"  NOTE: this baseline was accepted with --force: {b['provenance']['forceReason']}")
    return 0


# ── case-census ───────────────────────────────────────────────────────────────

def cmd_case_census(repo: Path) -> int:
    """Two INDEPENDENT axes per case -- do not conflate them (an early draft of this
    script did, and printed a wrong "negative/frozen(gateOutcome=reject)" label; verified
    wrong against fixtures/evals/cases/judge-2026-07-*.json, where 3 of the 4 seam=judge
    kind=positive cases have checks.gateOutcome=reject):
      kind        = positive (a real, curated example) | negative (a frozen adversarial/
                    calibration case used only to check the grader isn't miscalibrated)
      gateOutcome = what tests/test_evals_fixture_health.py::test_frozen_answers_hold_
                    their_gate_outcome expects gate_brain_answer() to return for that
                    exact FROZEN recordedAnswer under CURRENT production gates -- pass or
                    reject. A positive judge case can legitimately expect "reject": eval's
                    judge gating runs samples=1/resample_budget=0 (no retry), so a
                    real historical case whose production judgment needed an anchor-bound
                    or voice-lint retry to land correctly will, replayed single-shot,
                    correctly re-produce a reject -- that is the case exercising a real
                    gate interaction, not a broken fixture."""
    cases_dir = repo / "fixtures" / "evals" / "cases"
    if not cases_dir.is_dir():
        print("no fixtures/evals/cases/ directory", file=sys.stderr)
        return 2
    baseline_path = repo / "fixtures" / "evals" / "baseline.json"
    medians = load_json(baseline_path).get("caseMedians", {}) if baseline_path.exists() else {}
    rows = []
    for p in sorted(cases_dir.glob("*.json")):
        d = load_json(p)
        seam = d.get("seam")
        kind = d.get("kind")
        outcome = d.get("checks", {}).get("gateOutcome")
        rows.append((d.get("caseId", p.stem), seam, kind, outcome, medians.get(d.get("caseId"))))
    print(f"{len(rows)} case(s) in fixtures/evals/cases/")
    for seam in SEAMS:
        seam_rows = [r for r in rows if r[1] == seam]
        n_pos = sum(1 for r in seam_rows if r[2] == "positive")
        n_neg = sum(1 for r in seam_rows if r[2] == "negative")
        n_pass = sum(1 for r in seam_rows if r[3] == "pass")
        n_reject = sum(1 for r in seam_rows if r[3] == "reject")
        print(f"  {seam:8s} kind: positive={n_pos} negative={n_neg}   |   "
              f"gateOutcome (independent axis): pass={n_pass} reject={n_reject}")
    print()
    print("  positive-kind cases sorted by baseline median, GROUPED BY SEAM (weakest first "
          "within each seam -- seams have different natural score ranges, so do not compare "
          "medians across seams):")
    for seam in SEAMS:
        seam_rows = sorted((r for r in rows if r[1] == seam and r[2] == "positive"
                            and r[4] is not None), key=lambda r: r[4])
        for case_id, _, kind, outcome, median in seam_rows:
            print(f"    {case_id:24s} median={median}  gateOutcome={outcome}")
    return 0


# ── verdict ───────────────────────────────────────────────────────────────────

def cmd_verdict(path: Path) -> int:
    v = load_json(path)
    decision = v.get("decision")
    print(f"{path}: decision={decision}  pass={v.get('pass')}")
    for seam, s in v.get("seams", {}).items():
        margin = s["value"] - s["bar"]
        flag = "OK" if s.get("ok") else "FAIL"
        print(f"  {seam:8s} value={s['value']:.4f}  bar={s['bar']:.4f}  "
              f"hardBar={s.get('hardBar', float('nan')):.4f}  margin={margin:+.4f}  [{flag}]")
    craters = v.get("craters", [])
    if craters:
        print(f"  CRATERS ({len(craters)}): {craters}")
    else:
        print("  craters: none")
    for r in v.get("reasons", []):
        print(f"  reason: {r}")
    print()
    print(_F73_NOTE)
    return 0 if decision == "pass" else 1


# ── report (pre-verdict, or a second opinion on an existing report.json) ─────

def cmd_report(repo: Path, path: Path, baseline_path: Path | None) -> int:
    r = load_json(path)
    if "verdict" in r:
        print(f"{path} already embeds a verdict block:")
        return cmd_verdict_dict(r["verdict"])
    baseline_path = baseline_path or (repo / "fixtures" / "evals" / "baseline.json")
    if not baseline_path.exists():
        print(f"{path}: no embedded verdict and no baseline at {baseline_path} to compare "
              f"against -- printing raw seamMeans only.")
        print(r.get("seamMeans"))
        return 0
    b = load_json(baseline_path)
    print(f"{path}  asOf={r.get('asOf')}")
    exit_code = 0
    for seam in SEAMS:
        value = r.get("seamMeans", {}).get(seam)
        if value is None:
            continue
        bar = b["seamMeans"][seam] - b["epsilon"][seam]
        ok = value >= bar - 1e-9
        print(f"  {seam:8s} value={value:.4f}  bar={bar:.4f}  [{'OK' if ok else 'BELOW BAR'}]")
        if not ok:
            exit_code = 1
    medians = b.get("caseMedians", {})
    for case_id, score in r.get("scores", {}).items():
        median = medians.get(case_id)
        if median is None:
            continue
        total = score.get("total") if isinstance(score, dict) else score
        if total is not None and total <= median - 3:
            hard = " (HARD crater, <= median-5)" if total <= median - 5 else ""
            print(f"  CRATER: {case_id} scored {total} vs median {median}{hard}")
            exit_code = 1
    print()
    print(_F73_NOTE)
    return exit_code


def cmd_verdict_dict(v: dict) -> int:
    decision = v.get("decision")
    print(f"decision={decision}  pass={v.get('pass')}")
    for seam, s in v.get("seams", {}).items():
        margin = s["value"] - s["bar"]
        print(f"  {seam:8s} value={s['value']:.4f}  bar={s['bar']:.4f}  margin={margin:+.4f}  "
              f"[{'OK' if s.get('ok') else 'FAIL'}]")
    print()
    print(_F73_NOTE)
    return 0 if decision == "pass" else 1


# ── seam-noise ────────────────────────────────────────────────────────────────

def cmd_seam_noise(dirs: list[Path]) -> int:
    """Reads report.json from each given run dir and prints per-seam spread across them --
    the same "half-range" computation eval-v2's epsilon is built from (harness.py), applied
    to whatever run dirs you point it at (a rebaseline's 3 replicates, a set of ad-hoc
    identical-prompt reruns, etc.). Retained run dirs backing the committed baseline live
    under gitignored .worktrees/<name>/work/eval-*/{r1,r2,r3}/ -- e.g.
    .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/{r1,r2,r3}; never `git
    clean` those away (CLAUDE.md)."""
    per_seam: dict[str, list[float]] = {s: [] for s in SEAMS}
    for d in dirs:
        rp = d / "report.json" if d.is_dir() else d
        if not rp.exists():
            print(f"warning: no report.json at {rp}", file=sys.stderr)
            continue
        means = load_json(rp).get("seamMeans", {})
        for seam in SEAMS:
            if seam in means:
                per_seam[seam].append(means[seam])
    exit_code = 0
    for seam in SEAMS:
        vals = per_seam[seam]
        if len(vals) < 2:
            print(f"  {seam:8s} only {len(vals)} value(s) -- need >=2 runs to measure spread")
            continue
        spread = max(vals) - min(vals)
        print(f"  {seam:8s} n={len(vals)}  values={vals}  spread={spread:.4f}  "
              f"mean={statistics.mean(vals):.4f}")
    print()
    print(_F73_NOTE)
    return exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd, auto-detected via git)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("baseline")
    sub.add_parser("case-census")
    p_verdict = sub.add_parser("verdict")
    p_verdict.add_argument("path")
    p_report = sub.add_parser("report")
    p_report.add_argument("path")
    p_report.add_argument("--baseline", default=None)
    p_noise = sub.add_parser("seam-noise")
    p_noise.add_argument("dirs", nargs="+")

    args = ap.parse_args()
    repo = find_repo_root(Path(args.repo))
    if repo is None:
        print(f"error: {args.repo} is not inside a git repo", file=sys.stderr)
        return 2

    if args.cmd == "baseline":
        return cmd_baseline(repo)
    if args.cmd == "case-census":
        return cmd_case_census(repo)
    if args.cmd == "verdict":
        p = Path(args.path)
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 2
        return cmd_verdict(p)
    if args.cmd == "report":
        p = Path(args.path)
        if not p.exists():
            print(f"error: {p} not found", file=sys.stderr)
            return 2
        bp = Path(args.baseline) if args.baseline else None
        return cmd_report(repo, p, bp)
    if args.cmd == "seam-noise":
        return cmd_seam_noise([Path(d) for d in args.dirs])
    return 2


if __name__ == "__main__":
    sys.exit(main())
