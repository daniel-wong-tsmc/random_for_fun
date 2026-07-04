# Eval run 2026-07-04 (F62) — rebaseline for the observed= vintage tag

Trigger: F62 Task 7 added `observed=<date>` to emitted judge/thesis finding rows
(judgment/prompt.py include_dates emit-only kwarg; thesis.py _finding_lines; evals/emit.py
mirror). Baseline pin red on judge+thesis hashes (extract unchanged) — expected blast radius.

Procedure: .claude/skills/run-eval/SKILL.md, all brains and graders inline tool-less Opus,
one per case, separate generations. Run root: work/eval-f62-2026-07-04/ (worktree
.worktrees/f62-flagship-store, branch f62-flagship-consumes-store).

## Brain wave (14 fresh: 8 extract, 4 judge singles, 2 thesis)

- emit-brain: 14 prompts. Judge pairs confirmed byte-identical prompts via sha256
  (judge-01≡judge-02, judge-03-01≡judge-03-02) — F38 pairs, dispatched as separate generations.
- All 14 dispatched and answered. Per-case answers in answers/<caseId>.json;
  assembled brain-answers.json.
- record-brain attempt 1: 13/14 gate-clean. ONE failure —
  judge-2026-07-01 sample 1: bottleneck.rationale acronym 'CEO' not on allowlist.
  Disposition: F38-safe re-dispatch of ONLY that brain with the violation line appended
  ("fix these violations; change nothing else"). Corrected answer ("chief executive")
  saved; record-brain attempt 2: 14/14, 0 failed. No hand edits.

## Grade wave (18 graders: 14 fresh positives + 4 frozen negatives, one per case)

- All 18 dispatched as separate tool-less Opus generations.
- TWO graders returned structurally malformed GradeResult JSON (a criterion object nested
  inside another + duplicate keys): judge-2026-07-90 and thesis-2026-07-03-01. Both
  re-dispatched with the violation described ("keep your scores/evidence; fix the shape");
  corrected answers saved. Scores unchanged by the re-dispatch.
- ONE grader (thesis-2026-07-90) wrapped valid JSON in markdown code fences; fences stripped
  on save (transport normalization only — content byte-identical).
- Calibration negatives: extract-90 = 2, judge-90 = 1, thesis-90 = 0, thesis-91 = 2 —
  ALL EXACTLY REPRODUCE the baseline scores on the frozen answers (limit 4, ok).

## Attempt 1 verdict: FAIL — diagnosed as brain-generation sampling noise

record-grade: FAIL. Seams: extract 6.25 (< incumbent 6.62), judge 6.50 (< 6.75),
thesis 6.00 (> 5.50). Per-case vs baseline:
- extract (UNCHANGED prompt, hash never drifted): +1,-1,0,-2,+2,-2,-2,+1 → net -3.
  Scatter in both directions on an identical prompt = pure generation variance; this
  calibrates the run noise floor ABOVE the judge seam's -0.25 gap.
- judge (changed prompt): 0,0,-2,+1 → the entire gap is ONE generation (judge-03-01,
  5 vs 7) whose deductions are date-unrelated slips (cross-group prose reference,
  'pricing power' overreach).
- thesis (changed prompt): +1,0,0,0 → IMPROVED.
- Graders: all four frozen negatives scored byte-identically to baseline → grader
  variance ~0; drift is on the brain side.
Conclusion: no evidence the observed= tag regresses quality; thesis suggests it helps.

Disposition (pre-committed, recorded BEFORE attempt 2): run ONE full replication —
re-dispatch all 14 fresh brains (same emitted prompts) + their 14 graders; reuse
attempt 1's four frozen-negative grades (inputs byte-identical, grader-reproduced).
If attempt 2 PASSES → rebaseline on attempt 2. If attempt 2 FAILS → STOP, keep the
pin red, record BLOCKED-on-user with both runs' data (options: --force with reason,
prompt iteration, or more replications — user's call). NOT retry-until-green.
Attempt-1 artifacts preserved: answers/ + grade-answers/ → renamed *-attempt1.

## Attempt 2 (full replication, same emitted prompts)

- Brains: all 14 re-dispatched as fresh independent generations. record-brain: ONE
  violation again — judge-2026-07-02 (the OTHER member of the monthly F38 pair this
  time) used 'CEO' in bottleneck.rationale; F38-safe re-dispatch ("fix this violation;
  change nothing else") → "chief executive"; re-gate 14/14, 0 failed. No hand edits.
- Graders: 14 fresh positives dispatched; 4 frozen-negative grades REUSED from
  attempt 1 (inputs byte-identical, attempt-1 graders reproduced baseline exactly).
  TWO graders returned the same malformed-nesting GradeResult shape seen in attempt 1
  (judge-01, judge-03-02 graders this time); both re-dispatched shape-only ("keep your
  scores/evidence exactly; fix the structure"), scores unchanged.

## Attempt 2 verdict: FAIL — judge seam only; STOP per pre-commitment

record-grade (as-of 2026-07-04): FAIL.
Seams: extract 6.75 (PASS ≥ 6.62), judge 6.25 (FAIL < 6.75), thesis 6.00 (PASS ≥ 5.50).
Calibration negatives 2/1/0/2 — all ok (limit 4).

Per-case attempt 2: extract 6,6,8,7,8,7,6,6 (mean 6.75); judge 6,6,6,7 (mean 6.25);
thesis 7,5 (mean 6.00).

Cross-attempt picture (baseline → a1 → a2 seam means):
- extract (prompt UNCHANGED): 6.62 → 6.25 → 6.75. Swings both sides of incumbent on an
  identical prompt — confirms attempt 1's read that ±0.4 is within generation noise.
- thesis (prompt CHANGED): 5.50 → 6.00 → 6.00. Improved twice. The observed= tag is
  not hurting thesis; it plausibly helps (dated rows ground delta-discipline).
- judge (prompt CHANGED): 6.75 → 6.50 → 6.25. Below incumbent twice. The deficit has a
  consistent signature: ALL 8 fresh judge generations across both attempts scored
  sensitivity-differentiation = 1 (flip condition stated, consensus-departure sentence
  absent), plus small evidence-discipline slips (moat prose slightly outrunning the
  90%-AIB-share citation). None of the graded deductions reference the observed= dates.
  The frozen baseline answer earns its 2 on sensitivity-differentiation from a
  consensus-departure sentence the current post-F67 voice prompt (3-sentence narrative
  budget) leaves little room for.

Honest read: this is NOT clean noise (two consecutive judge shortfalls with the same
criterion signature), but the deductions are stylistic-rubric misses orthogonal to the
F62 observed= change (extract, whose prompt never changed, shows the same-magnitude
swings). Deciding between (a) --force rebaseline with reason "judge deficit is a
pre-existing rubric/voice tension, not an observed= regression", (b) iterating the
judge prompt to ask for a consensus-departure clause (its own eval-gated change), or
(c) more replications, is a JUDGMENT CALL ON THE GATE ITSELF → BLOCKED-on-user.

STATE: baseline pin stays RED (test_evals_baseline_pin: judge+thesis hashes) until the
user decides. Both attempts' full data preserved: attempt 1 in answers-attempt1/,
grade-answers-attempt1/, brain-answers-attempt1.json, grade-answers-attempt1.json,
report-attempt1.json; attempt 2 in answers/, grade-answers/, brain-answers.json,
grade-answers.json, report.json (FAIL), brain-gates.json.

## Attempt 3 (option B, user-approved): consensus-departure clause + combined validation — PASS

User reviewed both failed attempts and chose option B: fix the prompt/rubric mismatch on the
prompt side. Commit b8f41f8 amends the judge narrative spec sentence (2) to demand "where and
why this read departs from the consensus view" (three-sentence budget unchanged; deterministic
lint untouched; TDD pin test added in tests/test_judgment_prompt.py).

Run shape: emit-brain confirmed the amendment's blast radius is judge-only (extract/thesis
prompts byte-identical to attempt 2, sha-verified; F38 pairs still identical within pair).
Therefore attempt 2's extract (8) and thesis (2) generations and their grades carry over;
the 4 judge cases were regenerated fresh under the amended prompt and freshly graded; the 4
frozen-negative grades reused (grader-reproduced twice). record-brain: one violation again —
judge-2026-07-02 used 'CEO' (third occurrence of this exact slip across attempts, always the
monthly pair); F38-safe re-dispatch -> "chief executive"; re-gate 14/14 clean.

All four fresh judge narratives now state an explicit consensus departure (e.g. "erodes
merchant share faster than a consensus that still treats that loss as gradual"; "against the
consensus that custom silicon stays a sideshow"). Grades: judge 7, 8, 7, 8 — the
sensitivity-differentiation criterion moved 1 -> 2 on ALL four cases, exactly the deficit
signature attempts 1-2 diagnosed.

record-grade (as-of 2026-07-04): PASS. Seams: extract 6.75 (>= 6.62), judge 7.50 (>= 6.75),
thesis 6.00 (>= 5.50). Calibration negatives 2/1/0/2, all ok. NO --force needed.

rebaseline: fixtures/evals/baseline.json rewritten with the full reason + human-review
provenance. Full suite after rebaseline: 970 passed / 3 skipped / 0 failed — the F6 pin now
passes against the new baseline. Attempt-3 artifacts: answers/ + grade-answers/ (current);
attempts 1 and 2 preserved in *-attempt1/ and *-attempt2/ files.
