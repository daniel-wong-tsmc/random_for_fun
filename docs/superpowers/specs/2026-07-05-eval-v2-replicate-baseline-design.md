# eval-v2 — replicate-based eval baseline (design)

- **Date:** 2026-07-05
- **Branch:** `eval-v2-replicate-baseline` (worktree `.worktrees/eval-v2`, base `2adaa9c` = origin/main)
- **Supersedes:** the comparison rule in `docs/superpowers/specs/2026-07-04-f6-eval-harness-design.md`
  ("per-seam mean ≥ incumbent, ties pass"). Everything else in the F6 design stands.

## Decision provenance

The user approved investigating eval-v2 implicitly by handing off with it as the recommended
disposition for F63's blocked gate; the user was AFK at every question gate this session. Per the
F52/F53/F54 AFK precedent, each pick below followed the recommended option and is relitigable
before implementation. Merges to main remain user-gated regardless.

| Decision | Pick (AFK default) | Alternatives offered |
| --- | --- | --- |
| Overall approach | Replicate baseline (N=3, ε from replicates) | fixed hand-set ε on v1 schema; statistical test |
| ε formula | max(half-range of 3 replicate means, one seam quantum) + dispersion guard | sample std dev; pooled historical constant |
| Marginal band | fail within ε below bar → one auto-replication; worse → hard fail | any fail replicates once |
| Migration baseline | archived F62 attempt-3 run + 2 fresh replicates | 3 entirely fresh runs |
| F63 fold-in (context) | yes — fold the three proven fixes into F63 before its re-gate | re-gate F63 as built |

## Problem

The v1 gate compares one fresh run's per-seam mean against one incumbent run's mean with zero
tolerance (`harness.build_report`: fail iff `new < incumbent − 1e-9`). Measured identical-prompt
noise across the five archived runs (F62 attempts 1–3, F63 runs 1–2) is larger than that margin:

| identical-bundle group | extract | judge | thesis |
| --- | --- | --- | --- |
| F62 a1/a2 (+a3 for extract & thesis — same hashes) | 6.25 / 6.75 / 6.75 | 6.50 / 6.25 (old judge prompt) | 6.00 / 6.00 / 6.00 |
| F63 r1/r2 | 6.375 / 6.375 | 7.00 / 6.75 | 6.00 / 5.50 |

Per-seam swing on identical prompts: extract 0.50, judge 0.25, thesis 0.50 — one to four grading
quanta (seam means are quantized at 1/n_cases: extract 0.125, judge 0.25, thesis 0.50). The
incumbent bar (F62 attempt-3: 6.75 / 7.50 / 6.00) is a single high draw sitting inside that noise
band, which is exactly what blocked F63 twice on deficits that traced to no F63 change. The bar
must become an estimate with a tolerance, not a single draw with a knife edge.

## Design

### 1. Baseline schema v2 (`fixtures/evals/baseline.json`)

```json
{
  "schemaVersion": 2,
  "promptHashes": {"extract": "…", "judge": "…", "thesis": "…"},
  "replicates": [
    {"asOf": "…", "runDir": "work/eval-…/",
     "seamMeans": {"extract": 6.75, "judge": 7.5, "thesis": 6.0},
     "cases": {"<caseId>": {"total": 7, "grades": {"<criterion>": 2}}}}
  ],
  "seamMeans": {"extract": 6.58, "judge": 7.17, "thesis": 6.0},
  "epsilon": {"extract": 0.25, "judge": 0.375, "thesis": 0.5},
  "caseMedians": {"<positive caseId>": 7},
  "provenance": {"asOf": "…", "graderModel": "opus", "forceReason": null, "humanReview": "…"}
}
```

- `replicates`: exactly 3 full runs of one prompt bundle, stored whole (per-run seam means +
  per-case totals and criterion grades — negatives included for the record). Numbers above are
  illustrative.
- `seamMeans`: per-seam mean of the 3 replicate seam means (key name kept from v1; meaning
  changes from "the run's means" to "the replicate mean").
- `epsilon`: per-seam tolerance, computed at rebaseline time (§2), stored so the gate never
  recomputes it from anything mutable.
- `caseMedians`: per **positive** case, the median of its 3 replicate totals (median of 3
  integers is an integer). Negatives get no median — the calibration limit governs them.
- **Replicates are unfiltered draws.** A low replicate may not be discarded or re-run. The only
  legal re-dispatch inside a replicate run remains what v1 allows: individual brain answers that
  fail `record-brain` (F38-safe, violations appended) and individual graders that fail the grade
  gate or miscalibrate on a frozen negative. Those fix invalid output, never unlucky output.

### 2. ε — deterministic, from the stored replicates

For each seam: `ε = max((max − min) / 2 over the 3 replicate seam means, quantum)` where
`quantum = 1 / (number of positive cases in the seam)` — extract 1/8, judge 1/4, thesis 1/2,
derived from the case set at rebaseline time, not hardcoded.

- The quantum floor prevents an ε = 0 knife edge when replicates tie (thesis went 6.0/6.0/6.0
  in the F62 group).
- **Dispersion guard:** rebaseline refuses if any seam's replicate range (max − min) exceeds
  1.0 — replicates that disagree by more than a point per seam indicate breakage (a flaky gate,
  a drifted grader), not sampling noise. `--force` can override; the reason is stored permanently.

### 3. Gate decision

A shared decision function (`harness.py`) consumes the v2 baseline plus one or two run reports
and returns a typed verdict. Exposed two ways: `eval record-grade` embeds the single-run verdict
in `report.json` as today, and a new pure verb `eval verdict --runs <dir> [<dir2>]` computes the
(re-)decision from stored reports — the two-run form is how a replication resolves.

Prongs, single run:

- **Seam prong:** for each seam, pass iff `fresh ≥ seamMean − ε`. Boundary passes (v1's
  ties-pass generalizes to bar-touch passes).
- **Crater prong:** a positive case craters iff `total ≤ caseMedian − 3`. Catches a case-level
  collapse the seam mean can absorb (one 8→4 case inside an otherwise-lucky run). Historical
  false-positive check: max per-case swing between identical-prompt runs in the archive is 2.

Verdict classes:

- **PASS** — both prongs clean.
- **MARGINAL FAIL** — every failing seam is within one ε below its bar
  (`fresh ≥ seamMean − 2ε`) and every cratered case is within 1 beyond the crater line
  (`total ≥ caseMedian − 4`). Triggers **exactly one** replication: a fresh full run in a new
  run dir, then `eval verdict --runs <run1> <run2>`.
- **HARD FAIL** — anything worse (any seam below `seamMean − 2ε`, or any case at
  `caseMedian − 5` or lower). Stop immediately; no replication.

Two-run decision (after a marginal fail): recompute both prongs on two-run means — per seam the
mean of the two runs' seam means vs the same `seamMean − ε` bar; per case the mean of the two
totals vs the same `caseMedian − 3` line (fail iff `mean ≤ caseMedian − 3`). Result is final:
PASS or FAIL, never a third run. This is deterministic given the two reports; there is no
retry-until-green path.

Unchanged from v1: frozen negatives and the calibration limit (negative total ≤ max/2 per run);
a miscalibrated grader makes the run invalid-for-decision and is fixed by re-dispatching that
grader, exactly as today — calibration is a validity check, not a verdict input. Likewise a seam
that has a baseline but no scored positive cases in the fresh run makes the run
invalid-for-decision (v1's existing check, carried forward). The prompt-hash pin
(`test_prompt_hashes_match_baseline`) is untouched in spirit and code.

Artifacts and exit codes: `eval verdict` writes `verdict.json` (decision class, per-prong detail,
constituent run dirs and their hashes, reasons) into the last run dir passed and prints the
class; both `record-grade` and `verdict` exit 0 only on PASS.

### 4. Accepting a change — rebaseline v2

`eval rebaseline --runs <d1> <d2> <d3> [--verdict <verdict.json>] [--force --reason "…"]
[--human-review "…"]`

Validation (all deterministic, all refusals printed with the failing fact):

1. Exactly 3 run dirs, each containing a `report.json`.
2. `promptHashes` identical across all 3 reports **and** equal to the hashes computed from the
   current working tree (guards against baselining stale or mixed-bundle runs).
3. Every run calibration-clean.
4. Dispersion guard (§2).
5. Governance (the v2 analogue of v1's refuse-failing-run rule):
   - Hashes **differ** from the existing baseline (a prompt change is being accepted): require
     `--verdict` pointing at a verdict.json whose decision is PASS and whose constituent run
     dirs carry the same hashes — or `--force`.
   - Hashes **equal** the existing baseline: allowed only when the existing baseline is
     schema v1 (the migration path) — otherwise `--force` (re-baselining the same bundle is a
     judgment call by definition).
   - No existing baseline: bootstrap, allowed.

After a gate PASS, the gate run(s) count toward the 3 replicates: a clean pass tops up with 2
more runs, a marginal-then-pass with 1 more. Top-up runs are unfiltered draws like any replicate
(no verdict is computed for them; they only need record-brain-clean and calibration-clean).
Standing cost per accepted prompt change: **3 full runs** (each ≈ 14 brains + 18 graders,
session-level tool-less Opus dispatches).

`rebaseline`'s v1 form (`--out <dir>`, single run) is removed in the same change; the run-eval
skill is the only consumer and is rewritten in the same branch.

### 5. Migration — first v2 baseline (final task on this branch, session-level)

The current main bundle (hashes 07ae0992… / ae9a6a7a… / 3204bcc4…) gets its v2 baseline from:

- **Replicate 1:** the archived F62 attempt-3 run
  (`.worktrees/f62-flagship-store/work/eval-f62-2026-07-04/`, `report.json`; its promptHashes
  verified equal to current main's). Copied into this worktree's `work/` for provenance.
- **Replicates 2–3:** two fresh full runs of the current bundle, run per the run-eval skill
  (emit-brain → dispatch → record-brain → emit-grade → dispatch → record-grade), no verdict
  needed. Run-eval is session-level work — never delegated to an implementer subagent.

Then `eval rebaseline --runs <r1> <r2> <r3>` (same-hash + existing-v1 ⇒ migration path, no
force), commit the v2 baseline, full suite green. The branch merges with the v2 baseline in
place so the suite never straddles formats. Note: attempt-3 is a known-high draw (it survived a
three-attempt sequence); including it raises the mean and correspondingly widens ε — reflected
honestly, not corrected for.

The two fresh migration runs may individually score below the old v1 bar; that is expected and
irrelevant — they are measurements, not gate attempts.

### 6. Surface changes

| Surface | Change |
| --- | --- |
| `gpu_agent/evals/harness.py` | ε/median math, typed verdict function (1–2 runs), `build_report` embeds single-run v2 verdict, `rebaseline` rewritten (validation + v2 writer), v1-baseline detection |
| `gpu_agent/cli.py` eval driver | new `verdict` action; `rebaseline` args (`--runs`, `--verdict`); `record-grade` prints v2 verdict class, or a no-comparison notice when the baseline is v1/absent |
| `tests/test_evals_baseline_pin.py` | `test_baseline_integrity` updated for v2 keys (schemaVersion, replicates ×3, epsilon, caseMedians); hash-pin test unchanged |
| `tests/` (new/updated) | unit tests on synthetic reports: ε formula (half-range, floor, guard), medians, verdict boundaries (bar-touch passes; `−2ε` and `median−4/−5` edges), two-run decision, rebaseline validations 1–5, CLI plumbing (`test_cli_eval.py`, `test_evals_harness_baseline.py`) |
| `.claude/skills/run-eval/SKILL.md` | rewritten flow: verdict classes, marginal → one replication → `eval verdict --runs`, top-up to 3, `rebaseline --runs`, unfiltered-replicates invariant |
| `docs/agent-swarm-charter.md` Part 24 | one clarifying amendment: the incumbent bar is the mean of 3 stored replicates minus a replicate-derived ε; a marginal fail earns exactly one replication decided on the two-run mean; any case cratering ≥3 below its baseline median fails independently of the seam mean |
| `docs/fix-backlog.md` | mark the "Eval infra — multi-attempt bar" item in-progress→done when merged |

**Not touched:** emitted brain prompts (`emit.py`, prompt files, registry vocab — the pin stays
green throughout; eval-v2 must not re-arm it), `rubric.py`, `cases.py`, `prompt_hash.py`, the
golden set and frozen negatives, and all frozen-core files (`gate.py`, `scoring.py`, `schema/*`,
`judgment/briefing.py`, `judgment/judge.py` aggregation, `pipeline.py`, `JsonStore` — empty diff
vs main).

### 7. Worked example (hypothetical replicate values)

Suppose migration replicates land at extract 6.75 / 6.375 / 6.5, judge 7.5 / 7.0 / 7.0, thesis
6.0 / 6.0 / 5.5:

- extract: mean 6.542, half-range 0.1875 → ε = max(0.1875, 0.125) = 0.1875 → bar 6.354;
  hard-fail line 6.167.
- judge: mean 7.167, half-range 0.25 → ε = 0.25 → bar 6.917; hard-fail line 6.667.
- thesis: mean 5.833, half-range 0.25 → ε = max(0.25, 0.5) = 0.5 → bar 5.333.

F63's two archived runs (extract 6.375 both; judge 7.0, 6.75; thesis 6.0, 5.5) would then gate:
run 1 PASS on all seams; run 2 marginal on judge (6.75 ≥ 6.667) → one replication → a replicate
judge mean of 7.0 gives a two-run mean of 6.875 < 6.917 (still FAIL); 7.25 or higher gives
≥ 7.0 (PASS). The rule is not rigged to pass F63 —
it is derived from measured noise, and F63 still has to clear it with fresh runs of its amended
bundle (the fold-in changes the extract hash, so its archived runs cannot be reused).

### 8. F63 consumption path (context, out of scope for this branch)

After eval-v2 merges: F63 rebases onto main (picking up the v2 harness + migrated baseline),
folds in the three proven fixes (corroboration "across separately fetched documents";
`impact.direction` enum stated; `CEO` allowlisted in `registry/acronyms.json`), then gates: one
fresh run vs the v2 baseline → marginal ⇒ one replication → on PASS top up to 3 replicates of
F63's bundle → `rebaseline --verdict …` on the F63 branch → pin green → final whole-branch opus
review → rebase → **user go** to merge.

## Testing strategy

All decision math is pure functions over dicts/reports — unit-tested with synthetic fixtures, no
dispatches. CLI tests drive the verbs over tmp-dir run layouts (existing `test_cli_eval.py`
pattern). The migration run is the live validation, exactly as F6 Task 10 was for v1. Suite must
be green at every commit on this branch; the baseline-pin test stays green throughout because no
emitted prompt changes.

## Error handling

Every refusal path (missing report, hash mismatch, stale hashes, dirty calibration, dispersion,
governance, wrong run count, v1-baseline comparison attempt) prints the failing fact and exits
non-zero; nothing silently proceeds. `--force` overrides only governance and dispersion — never
hash equality across runs, run count, or calibration — and stores its reason permanently in
provenance, as in v1.
