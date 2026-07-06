# Eval-v2 mechanics — worked numeric example and the saga that produced it

This is the reference companion to SKILL.md §4. It exists so a reader can hand-verify the bar
arithmetic instead of trusting the prose, and so the F62/F63 saga — the best teaching case in
the repo for "the gate is measuring noise vs. the gate found a regression" — is preserved in
full rather than compressed to one line.

## Why eval-v2 exists (the v1 gate it replaced)

The original (v1) gate was a single-draw, zero-tolerance bar: a candidate prompt's one eval run
had to score `>= incumbent - 1e-9` on every seam, where the incumbent was itself a single prior
run's score. This works only if a single run's score is a stable measurement. It is not:

- **F62 (2026-07-04), 3 attempts.** Attempt 1 FAILED with the extraction prompt completely
  UNCHANGED from the incumbent — extract scored 6.25 vs the incumbent's 6.62, a swing of ~0.4
  attributable to nothing but brain-generation sampling noise. Attempt 2 FAILED the judge seam
  only (6.25) with a *consistent signature*: all 8 fresh judge generations scored
  `sensitivity-differentiation=1` because the post-F67 3-sentence voice budget left no room for
  a consensus-departure sentence the rubric rewarded — a real prompt deficiency, correctly
  caught. User-approved option B: amend the judge prompt to explicitly demand "where and why
  this read departs from the consensus view" (commit `b8f41f8`, pinned today by
  `tests/test_judgment_prompt.py:73-80`). Attempt 3 PASSED (extract 6.75 / judge 7.50 /
  thesis 6.00) and was rebaselined WITHOUT `--force` (commit `f605a77`).
- **F63 (2026-07-04), v1 gate, FAILED TWICE.** Two independent, fully separate eval runs both
  landed extract at **exactly 6.38** against the incumbent bar of 6.75 (F62's own attempt-3
  score — itself later acknowledged as "a high draw"). No deduction in either run traced to an
  actual F63 prompt change, and the F63-specific mechanisms (the corroboration-scope fold-in,
  the direction-enum fix) graded WELL in both runs. Per the pre-committed disposition, the run
  **STOPPED**: pin stays red, no rebaseline, no `--force`. The diagnosis: the incumbent bar was
  noise-contaminated (F62's own identical-prompt runs had swung 6.25 → 6.88 → 7.50 — a wider
  range than the margin the v1 gate was trying to resolve).

The user-approved fix was not "force past the bar" — it was to rebuild the bar. Eval-v2
(merged `c0d5dd2`, 2026-07-05; charter Part 24 amendment commit `9f891c9`) replaced the
single-draw bar with a 3-replicate baseline, `ε = max(half-range, quantum)`, and a per-case
crater prong. The migration baseline folded in the archived F62 attempt-3 plus 2 fresh
replicates (commit `7b79846`) — the known-high draw was **kept and disclosed**, not quietly
dropped or corrected for; the run notes state this explicitly.

The F63 re-gate then ran under eval-v2 and PASSED first try (`ef52790`): r1 extract 6.625 vs
bar 6.5833 — a margin of **0.042**, "deep inside noise" by the project's own later admission
(this margin is exactly what F73 points at as evidence the gate's power is unproven).

## Hand-verifying the current baseline's arithmetic

Pull the three replicate seam means directly from `fixtures/evals/baseline.json` (each
`replicates[i]["seamMeans"]`) and recompute by hand:

```
extract means: r1=6.625, r2=6.5, r3=7.125
  half-range = (max - min) / 2 = (7.125 - 6.5) / 2 = 0.3125
  quantum = 1/8 = 0.125 (8 positive extract cases)
  epsilon = max(0.3125, 0.125) = 0.3125   <- matches baseline.json epsilon.extract
  seamMean = (6.625 + 6.5 + 7.125) / 3 = 6.75   <- matches seamMeans.extract
  bar = 6.75 - 0.3125 = 6.4375

judge means: r1=7.75, r2=7.5, r3=7.5
  half-range = (7.75 - 7.5) / 2 = 0.125
  quantum = 1/4 = 0.25 (4 positive judge cases)
  epsilon = max(0.125, 0.25) = 0.25   <- the QUANTUM wins here, not the spread
  seamMean = 7.5833...
  bar = 7.5833 - 0.25 = 7.3333

thesis means: r1=6.0, r2=6.0, r3=6.0
  half-range = 0 (zero spread across all 3 replicates)
  quantum = 1/2 = 0.5 (2 positive thesis cases)
  epsilon = max(0, 0.5) = 0.5   <- the QUANTUM wins again; a thin seam (2 cases) has a
                                    coarse quantum floor even when replicates agree exactly
  bar = 6.0 - 0.5 = 5.50
```

Two things this reveals that are easy to miss reading the code alone:

1. **The quantum floor dominates for thin seams.** Thesis has only 2 positive cases, so its
   quantum (0.5) is large — even a perfectly reproducible 6.0/6.0/6.0 replicate set gets a
   0.5-point bar cushion, not a razor-thin one. A seam only gets a tight, empirically-earned
   epsilon once it has enough positive cases that `1/n` drops below the observed half-range.
2. **`epsilon` is per-seam, never global.** A prompt change can comfortably clear judge's
   0.25-wide bar while barely clearing extract's 0.3125-wide one, or vice versa — read
   `verdict.json`'s per-seam breakdown, not a single pass/fail bit.

## The verdict ladder, traced end to end

```
run 1 (the "gate run")
  |
  v
evaluate_v2(baseline, [report1])
  |
  +-- no seam fails, no crater  -> decision="pass"
  |     -> mint verdict.json (gpu-agent eval verdict --runs <run1>)
  |     -> top up 2 MORE unfiltered replicates of the SAME bundle (no verdict needed on these)
  |     -> eval rebaseline --runs <run1> <run2> <run3> --verdict <run1>/verdict.json
  |
  +-- a seam fails but none hits the hard bar (value < bar but >= hardBar), no hard crater
  |     -> decision="marginal-fail"
  |     -> run steps 1-6 ONE more time (run2) in a fresh dir
  |     -> evaluate_v2(baseline, [report1, report2])  # TWO-RUN MEAN decides, same bars
  |          +-- no fail on the two-run mean -> decision="pass" (proceed as above, run2
  |          |     counts as the first of the 3 replicates needed for rebaseline)
  |          +-- still fails -> decision="fail" (FINAL - never a third run)
  |                -> hard stop; pin stays red; record BLOCKED-on-user
  |
  +-- a seam hits its hard bar (value < bar - eps), or a crater hits median-5
        -> decision="hard-fail"
        -> stop immediately; this is treated as a real regression, not noise
```

`invalid-run` can occur at either stage (1-report or 2-report) and short-circuits the whole
ladder before any bar math runs: a grader miscalibrated on a frozen negative (scored above
`max_score(seam)//2`), a seam with a baseline mean but zero freshly-scored positives, a
baseline case that scored in no supplied report, or (2-report case only) the two reports'
`promptHashes` disagreeing — meaning they are not actually replicates of the same bundle.

## Grader shape instability (recurring, unresolved as pattern)

Across the F62/F63/eval-v2 runs, graders repeatedly returned malformed `GradeResult` shapes:
nested criterion objects, duplicate keys, and stray extra keys (`score_note`, `verdict`) that
trip `extra="forbid"`. This happened 3 times on 2026-07-05 alone. Every occurrence was handled
by F38-safe shape-only re-dispatch ("keep your scores/evidence; fix the structure") — never by
loosening the schema. A transport-normalization rule (auto-strip known-bad extra keys before
validation) has been discussed in run notes but is **not built** — it remains a manual
dispatch-instruction mitigation only. If you find yourself writing that normalization layer,
it is new machinery (feature path, not a lane fix) — check with `desk-change-control` first.
