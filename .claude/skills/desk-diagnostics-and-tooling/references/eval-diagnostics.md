# eval_diagnostics.py -- field-by-field reference

Verified against the committed baseline (`fixtures/evals/baseline.json`, schemaVersion 2) and
the real retained-worktree run dirs backing it, on main @ `f7c83f0` (2026-07-06).

## Reading a `verdict.json` / `report.json`'s embedded verdict block

Shape (from a real retained run,
`.worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/r1/verdict.json`):

```json
{
  "craters": [],
  "decision": "pass",
  "pass": true,
  "promptHashes": {"extract": "...", "judge": "...", "thesis": "..."},
  "reasons": [],
  "runs": ["work/eval-f63-regate-2026-07-05/r1"],
  "seams": {
    "extract": {"bar": 6.5833, "hardBar": 6.4583, "ok": true, "value": 6.625},
    "judge":   {"bar": 7.3333, "hardBar": 7.0833, "ok": true, "value": 7.75},
    "thesis":  {"bar": 5.6667, "hardBar": 5.1667, "ok": true, "value": 6.0}
  }
}
```

- `bar` = `seamMean_baseline - epsilon` (the PASS line). `hardBar` = `seamMean_baseline -
  2*epsilon` (below this, the item auto-fails regardless of the marginal-replication rule).
- `value` = this run's (or this run's mean, for a 2-run marginal resolution) seam total.
- `craters[]` lists any POSITIVE case whose own total fell to `baseline_median - 3` or below,
  independent of the seam mean passing -- a single bad case can fail the gate even when the
  seam average looks fine.
- `decision` ladder: `pass` / `marginal-fail` (earns exactly one replication, decided on the
  two-run mean, never a third run) / `hard-fail` (stop, the regression is presumed real) /
  `invalid-run` (grader miscalibration, hash mismatch, or a baseline case missing from every
  run -- fix the grader/brain, not the score).

`eval_diagnostics.py verdict <path>` prints exactly these fields plus the F73 noise-context
note (see below); `report <path>` does the same starting from a `report.json` that may not
have an embedded verdict yet, recomputing the comparison against the current committed
baseline.

## The F63 re-gate, reproduced live

Running `eval_diagnostics.py verdict` against the real r1 verdict for the F63 re-gate
reproduces exactly the documented numbers: extract `value=6.625` vs `bar=6.5833`, margin
`+0.0417` -- i.e. the backlog's own "the F63 re-gate passed extract by 0.042... deep inside
noise" claim, to the fourth decimal. This is the single best concrete illustration in this repo
of why F73 (the eval gate's power is unproven) is a live methodological concern and not
academic: the actual PASS/FAIL boundary that shipped a real corroboration-doctrine change was
decided by four one-hundredths of a point.

## `seam-noise`, and the historical 6.25-7.50 precedent

`eval_diagnostics.py seam-noise <dir1> <dir2> ...` reads `seamMeans` out of each dir's
`report.json` and reports `max - min` per seam -- the same half-range computation
`gpu_agent/evals/harness.py` uses to derive epsilon (`epsilon = max(half-range of 3 replicate
means, one grading quantum)`). Pointed at the actual baseline replicates
(`.worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/{r1,r2,r3}`), it reproduces
`extract spread=0.625` -- half of that, 0.3125, is exactly the committed `epsilon.extract`.

The oft-cited "6.25-7.50" figure is a DIFFERENT, larger precedent from earlier in the same
saga: `docs/fix-backlog.md`'s F73 entry documents identical-prompt seam swings observed across
the F62/F63 attempts as 6.25 to 7.50 on a single seam (not the tighter 3-replicate spread
epsilon is built from). Both are real, both are cited by `eval_diagnostics.py`'s printed F73
note; the gap between "the noise this repo has actually observed across its whole eval history"
(6.25-7.50) and "the noise epsilon is calibrated from" (a same-day 3-run spread, typically much
smaller) is the crux of F73's open concern -- three replicates on one day may understate the
true noise floor.

## `case-census`: `kind` and `gateOutcome` are independent axes

Verified census (18 cases total, 2026-07-06):

| seam | kind=positive | kind=negative | gateOutcome=pass | gateOutcome=reject |
|---|---|---|---|---|
| extract | 8 | 1 | 9 | 0 |
| judge | 4 | 1 | 2 | 3 |
| thesis | 2 | 2 | 4 | 0 |

The judge row is the one that looks wrong until you understand why it isn't: **3 of judge's 4
`kind=positive`** cases (`judge-2026-07-01`, `judge-2026-07-02`, `judge-2026-07-03-02`) have
`checks.gateOutcome: "reject"`. This is correct and intentional, not a data error --
`gpu_agent/evals/emit.py`'s own documented deviation from live is that judge emits for
`samples=1, resample_budget=0` (no retry loop), whereas the LIVE judge path resamples/retries
on a gate contest (anchor-bound vs sufficiency, voice-lint). These three golden cases were
curated from real historical judge answers whose PRODUCTION judgment needed exactly that kind
of retry to land cleanly; replayed single-shot in eval mode (no retry available), the same
gate correctly reproduces a reject. The case is still a valid, curated example of good
REASONING (which is what the grader scores) -- `gateOutcome` and grading quality are separate
questions.

An earlier draft of `case_census`'s implementation assumed `gateOutcome=reject` was a synonym
for "this is one of the frozen negative-kind cases" and printed a `negative/frozen
(gateOutcome=reject)` label. That is factually wrong (verified above) and was corrected before
shipping. If you extend this script, keep the two axes in two separate columns.

## Per-seam medians, and why "weakest case overall" is a category error

`fixtures/evals/baseline.json`'s `caseMedians` mixes case ids from all three seams in one flat
dict. Comparing them directly (e.g. sorting the whole dict by value to find "the weakest
case") will point at whichever seam's rubric happens to score lowest overall -- verified today:
`thesis-2026-07-03-01` has the single lowest raw median (5) in the whole baseline, simply
because the `thesis` seam's mean (6.0) runs a full point below `judge`'s (7.58), not because
that thesis case is somehow worse than every extract case. `eval_diagnostics.py baseline` and
`case-census` both group by seam before ranking, specifically to avoid this trap.

Within its own seam, **extract-2026-07-05** is the case with actual historical significance:
the F63 re-gate run-notes name it verbatim as "the weakest case across every run ever
recorded" (a 4-7 score band across every run it's appeared in, with `completeness` the
recurring 0-scoring criterion) -- a claim about repeated volatility across MANY runs, not the
same claim as "lowest median in the CURRENT baseline snapshot" (today it's tied with
extract-2026-07-04 and extract-2026-07-06 at median 6, not uniquely lowest). Whether the case
itself (a specific document/extraction target) or the extract prompt is at fault has never
been separated -- open, and a good first target for **desk-proof-and-analysis-toolkit**'s
methodology if anyone picks it up.
