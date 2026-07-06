#!/usr/bin/env python
"""measure_seam_noise.py -- reproduce eval-v2's noise math over ANY set of retained
eval `report.json` files, without touching the store, the CLI's baseline, or any gate.

Read-only diagnostic. Stdlib only (json, pathlib, statistics, argparse) -- no repo
imports, so it runs even from outside a configured .venv.

WHY THIS EXISTS (desk-proof-and-analysis-toolkit, recipe 1): the eval-v2 bar
(gpu_agent/evals/harness.py: seam_quanta/compute_epsilon/evaluate_v2) is derived from
exactly 3 stored replicates at rebaseline time and then frozen into fixtures/evals/
baseline.json. This script lets you recompute that same math -- mean, half-range,
epsilon-vs-quantum, per-case swing -- over ANY N report.json files you still have on
disk (a retained worktree's work/ dir, a fresh set of top-up runs, a hypothetical
seeded-regression canary run), so you can sanity-check "is this seam's swing normal or
is something broken?" BEFORE trusting a verdict, and so you can measure your own
machine's noise floor instead of trusting a stale number from a doc.

This script does NOT decide PASS/FAIL and does NOT write a baseline -- it only prints
the descriptive statistics a human (or a session) needs to make that call. The actual
gate decision is `gpu_agent.evals.harness.evaluate_v2` via the `run-eval` skill; do not
let this script's output substitute for that -- it has no baseline, no crater prong,
and no calibration check.

Usage (from repo root or anywhere; paths are read literally):
    .venv/Scripts/python .claude/skills/desk-proof-and-analysis-toolkit/scripts/measure_seam_noise.py \
        .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r1/report.json \
        .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r2/report.json \
        .worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r3/report.json

Optional: --quantum extract=0.125 judge=0.25 thesis=0.5   (defaults match the current
18-case golden set: 1/8 extract-positive, 1/4 judge-positive, 1/2 thesis-positive --
recompute these yourself if the golden set's positive-case counts ever change; see
gpu_agent/evals/harness.py:seam_quanta for the authoritative formula).

Worked-example sanity check (2026-07-06, re-verified against the committed
fixtures/evals/baseline.json): running this against the three retained
eval-f63-regate-2026-07-05/{r1,r2,r3}/report.json files reproduces the committed
baseline exactly -- extract mean 6.75 / eps 0.3125, judge mean 7.5833 / eps 0.25,
thesis mean 6.0 / eps 0.5.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

DEFAULT_QUANTA = {"extract": 0.125, "judge": 0.25, "thesis": 0.5}


def load_reports(paths: list[str]) -> list[dict]:
    reports = []
    for p in paths:
        path = pathlib.Path(p)
        if not path.is_file():
            sys.exit(f"error: not a file: {p}")
        reports.append(json.loads(path.read_text(encoding="utf-8")))
    return reports


def parse_quanta(pairs: list[str]) -> dict[str, float]:
    quanta = dict(DEFAULT_QUANTA)
    for pair in pairs:
        seam, _, value = pair.partition("=")
        if not value:
            sys.exit(f"error: --quantum expects seam=value, got {pair!r}")
        quanta[seam] = float(value)
    return quanta


def seam_stats(reports: list[dict], quanta: dict[str, float]) -> None:
    seams: dict[str, list[float]] = {}
    for rep in reports:
        for seam, value in rep.get("seamMeans", {}).items():
            seams.setdefault(seam, []).append(value)

    print(f"# Seam means across {len(reports)} report(s)")
    print(f"{'seam':<10} {'n':>3} {'mean':>8} {'min':>8} {'max':>8} "
          f"{'half-range':>11} {'quantum':>8} {'epsilon':>8}")
    for seam, vals in sorted(seams.items()):
        n = len(vals)
        mean = statistics.fmean(vals)
        lo, hi = min(vals), max(vals)
        half_range = (hi - lo) / 2
        quantum = quanta.get(seam)
        eps = max(half_range, quantum) if quantum is not None else None
        eps_str = f"{eps:.4f}" if eps is not None else "  n/a  "
        q_str = f"{quantum:.4f}" if quantum is not None else "  n/a  "
        print(f"{seam:<10} {n:>3} {mean:>8.4f} {lo:>8.4f} {hi:>8.4f} "
              f"{half_range:>11.4f} {q_str:>8} {eps_str:>8}")
        if n < 3:
            print(f"  NOTE: only {n} report(s) for '{seam}' -- eval-v2 baselines always "
                  f"use exactly 3; treat this half-range as a lower bound on real noise, "
                  f"not the eps the gate would use.")


def case_swing(reports: list[dict], top_n: int = 10) -> None:
    cases: dict[str, list[int]] = {}
    for rep in reports:
        for cid, entry in rep.get("scores", {}).items():
            cases.setdefault(cid, []).append(entry["total"])

    rows = []
    for cid, totals in cases.items():
        if len(totals) < 2:
            continue
        rows.append((max(totals) - min(totals), cid, totals))
    rows.sort(reverse=True)

    print(f"\n# Per-case swing across the same {len(reports)} report(s) "
          f"(top {top_n} by range)")
    print(f"{'range':>5}  {'caseId':<28} totals")
    for rng, cid, totals in rows[:top_n]:
        print(f"{rng:>5}  {cid:<28} {totals}")
    if rows:
        max_row = rows[0]
        print(f"\nMax observed per-case swing here: {max_row[0]} (case {max_row[1]}).")
        print("The eval-v2 spec's own historical false-positive check found a max "
              "per-case swing of 2 across the F62/F63 archive; a swing bigger than "
              "that here is worth a second look before trusting a crater verdict.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reports", nargs="+", help="paths to report.json files (2 or more)")
    ap.add_argument("--quantum", action="append", default=[],
                     metavar="seam=value", help="override a seam's grading quantum")
    args = ap.parse_args()

    if len(args.reports) < 2:
        sys.exit("error: need at least 2 report.json files to measure any swing at all "
                  "(eval-v2 rebaselines need exactly 3)")

    reports = load_reports(args.reports)
    quanta = parse_quanta(args.quantum)
    seam_stats(reports, quanta)
    case_swing(reports)


if __name__ == "__main__":
    main()
