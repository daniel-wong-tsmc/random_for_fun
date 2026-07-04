# Eval run 2026-07-05 (eval-v2 migration) — first schema-v2 baseline for the incumbent bundle

Trigger: eval-v2 (replicate baseline) replaces the single-run baseline. The current main
prompt bundle (hashes 07ae0992… / ae9a6a7a… / 3204bcc4…) gets its v2 baseline from 3
replicates: the archived F62 attempt-3 run + two fresh unfiltered runs. No prompt changed;
the hash pin stayed green throughout.

Procedure: .claude/skills/run-eval/SKILL.md (v2). All brains and graders dispatched as
tool-less Opus subagents, one per case, separate generations; each subagent read exactly its
own materialized prompt file (`brains/<caseId>.txt` / `graders/<caseId>.txt`, byte-identical
to the canonical emit output — verified against `brain-prompts.json` and, for r2, verified
byte-identical to the archived a3 materialization modulo that archive's CRLF line endings).
Run root: work/eval-v2-migration/ (worktree .worktrees/eval-v2, branch
eval-v2-replicate-baseline). Migration replicates are measurement runs (record-grade printed
NO-COMPARISON against the then-v1 baseline, as expected); they are unfiltered draws and were
kept regardless of score.

## Replicates

| replicate | provenance | extract | judge | thesis |
| --- | --- | --- | --- | --- |
| r1 | archived F62 attempt-3 (`.worktrees/f62-flagship-store/work/eval-f62-2026-07-04/`, copied in; promptHashes verified equal to current main) | 6.75 | 7.50 | 6.00 |
| r2 | fresh full run, 2026-07-05 | 6.75 | 7.75 | 6.00 |
| r3 | fresh full run, 2026-07-05 | 6.625 | 7.50 | 6.50 |

Per-case (r2): extract 7,6,7,7,8,7,6,6 (01,02,03,03-01,03-02,04,05,06); judge 8,8,7,8;
thesis 7,5. Per-case (r3): extract 6,7,7,7,8,6,5,7; judge 8,8,8,6; thesis 7,6.

## Gate waves and re-dispatches (every one logged)

- r2 record-brain: 14/14 clean on the first attempt (no re-dispatches).
- r2 graders: 14 fresh positives; the four frozen-negative grade prompts verified
  byte-identical to r1's (JSON-normalized comparison) → their r1 grades carried over
  (F62/F63 precedent). Calibration clean.
- r3 record-brain: 14/14 clean on the first attempt (no re-dispatches).
- r3 graders: one gate rejection — judge-2026-07-01's grader emitted a stray
  `score_note` key (extra_forbidden). F38-safe re-dispatch with the verbatim violation
  appended; the re-dispatched generation self-corrected mid-message (first emitted another
  extra key, wrote "Let me re-emit cleanly", then produced a clean GradeResult) — the final
  complete JSON object was saved (transport normalization, same class as the F63 run's
  fenced-JSON strip). Re-gate clean. Negatives carried as in r2. Calibration clean.
- No brain or grader output was hand-edited at any point.

## New v2 baseline (fixtures/evals/baseline.json, committed with this note)

- seamMeans (mean of 3): extract 6.7083, judge 7.5833, thesis 6.1667
- ε (max(half-range, quantum)): extract 0.125 (quantum floor; half-range 0.0625),
  judge 0.25 (quantum floor; half-range 0.125), thesis 0.5 (floor; half-range 0.25)
- Bars (mean − ε): extract 6.5833, judge 7.3333, thesis 5.6667
  (hard-fail lines at mean − 2ε: 6.4583 / 7.0833 / 5.1667)
- caseMedians: extract 6,6,7,7,8,7,6,6; judge 8,8,7,8; thesis 7,5 (crater line = median − 3)
- Dispersion guard: max seam range 0.5 (thesis) ≤ 1.0 — clean.
- Governance path: same hashes + existing v1 baseline = the sanctioned migration path
  (no --force; forceReason null).

## Observations

- The three replicates landed unusually tight (extract range 0.125 vs the 0.5 historical
  identical-bundle swing), so every ε sits at its quantum floor — the bar is as strict as
  v2 allows for this bundle. r2's judge seam (7.75) came in ABOVE the old v1 incumbent bar
  (7.50), a live demonstration of the single-run-draw noise eval-v2 exists to damp.
- a3 remains a high draw for extract (6.75/6.75/6.625 keeps the mean near it), so the
  extract bar (6.5833) is materially lower than the old knife edge (6.75) while staying
  honest to the measured dispersion.
- The r3 judge-01 grader failure is the only anomaly; the F38 re-dispatch handled it in one
  round.
