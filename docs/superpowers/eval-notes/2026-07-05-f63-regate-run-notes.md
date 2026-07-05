# Eval run 2026-07-05 (F63 re-gate) — first gate under eval-v2, and F63's acceptance

Trigger: F63's amended bundle (corroboration doctrine + the two fold-in extraction-prompt
clarifications + `CEO` allowlist) gated against the migrated schema-v2 incumbent baseline
(bars: extract ≥ 6.5833, judge ≥ 7.3333, thesis ≥ 5.6667; crater line = case median − 3).
This replaces the two 2026-07-04 knife-edge failures (extract 6.38 both runs vs a 6.75
single-draw bar) that the eval-v2 spec diagnosed as baseline noise.

Pre-committed disposition (v2 makes it mechanical): PASS → mint verdict.json → top up to 3
replicates → `rebaseline --runs … --verdict …`; MARGINAL-FAIL → exactly one replication,
two-run mean decides, hard stop; HARD-FAIL → stop immediately. Not retry-until-green.

Procedure: run-eval SKILL.md (v2). All brains and graders tool-less Opus, one per case,
separate generations, each reading only its canonical materialized prompt file (byte-verified
against emit output). Run root: work/eval-f63-regate-2026-07-05/{r1,r2,r3} (worktree
.worktrees/f63-corroboration, branch f63-corroboration-doctrine, post-merge of main c0d5dd2).
Only the 8 extract bundles changed vs the 2026-07-04 F63 runs (the fold-ins); judge/thesis
bundles identical — but v2 gate runs are full-bundle units, so all 14 cases ran fresh in
every replicate. The four frozen-negative grade prompts were verified byte-identical to the
2026-07-04 F63 run (grade prompts embed only the unchanged USER prompt, not the amended
SYSTEM) → their grades carried (2/1/0/2, the F62-lineage grades reproduced 3×).

## Gate run r1 — PASS

Seams: extract 6.625 ≥ 6.5833, judge 7.75 ≥ 7.3333, thesis 6.00 ≥ 5.6667. No craters;
calibration clean. Verdict minted: r1/verdict.json (decision pass).
Per-case: extract 7,6,7,6,8,7,6,6; judge 8,8,8,7; thesis 7,5.

Re-dispatches (all logged): record-brain — thesis-01 wrapped its object in a JSON array
(F38 re-dispatch, clean second generation). Grade gate — judge-01 grader emitted a stray
`score_note` key and judge-02 grader stray `verdict` keys (extra_forbidden); both F38
re-dispatched with verbatim violations, clean. No craters, no hand edits.

**The fold-ins worked as designed:** unlike BOTH 2026-07-04 runs, no extract-04 generation
claimed within-document corroboration (the fresh brains explicitly reasoned "outlets quoted
inside it do not count as separately fetched publishers"), and zero impact.direction enum
schema failures occurred in any of the three replicates (2026-07-04 r2 had 8/8 fail).
record-brain went 14/14 clean on the first attempt in r2 and r3, and 13/14 in r1.

## Top-up replicates (unfiltered, kept regardless of score)

| replicate | extract | judge | thesis | notes |
| --- | --- | --- | --- | --- |
| r1 (gate) | 6.625 | 7.75 | 6.00 | PASS vs incumbent |
| r2 | 6.50 | 7.50 | 6.00 | record-grade printed MARGINAL-FAIL vs the incumbent baseline — informational only for a top-up; kept unfiltered |
| r3 | 7.125 | 7.50 | 6.00 | incidentally PASSED the incumbent bar on its own |

r2 per-case: extract 6,7,7,8,8,6,4,6; judge 8,8,7,7; thesis 7,5.
r3 per-case: extract 8,7,7,8,8,6,7,6; judge 7,8,8,7; thesis 7,5.
r2/r3 grader waves: clean on first attempt (the dispatch instruction now names the
no-extra-keys constraint explicitly after the r1/r3-migration grader anomalies).

## New F63 baseline (fixtures/evals/baseline.json, committed with this note)

- Replicates: r1/r2/r3 above. seamMeans: extract 6.75, judge 7.5833, thesis 6.00.
- ε: extract 0.3125 (half-range (7.125−6.5)/2), judge 0.25 (quantum floor), thesis 0.5 (floor).
- Bars (mean − ε): extract 6.4375, judge 7.3333, thesis 5.50.
- Dispersion guard: max seam range 0.625 (extract) ≤ 1.0 — clean.
- Governance: prompt change vs incumbent baseline → accepted via `--verdict r1/verdict.json`
  (decision pass, hashes match); forceReason null. First real exercise of the v2
  prompt-change acceptance path, end to end.

## Observations

- The v2 verdict resolved F63 exactly as the noise diagnosis predicted: the same doctrine
  mechanisms that lost twice to a single high-draw bar cleared a replicate-derived bar on
  the first fresh run, with the judge seam (7.75) beating even the old incumbent (7.50).
- extract-05 remains the weakest case across every run ever recorded (4–7 band, completeness
  the recurring 0); its baseline median is now 6 with the crater line at 3.
- Grader extra-key emissions (score_note/verdict) appeared 3× across the two 2026-07-05
  sessions — worth a future note in the grader dispatch template (now included) or a
  transport-normalization rule; logged as an observation, not acted on beyond the dispatch
  instruction.
