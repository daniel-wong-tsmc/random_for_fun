# F65 implication re-gate — run notes (2026-07-13)

**LATEST: user-approved F73 pooled-dispersion remedy → QUESTION-STOP (no legitimate harness
path exists for the append). The two-run FAIL below stands unmodified; baseline untouched.**

**Two-run outcome: FAIL on the two-run mean (judge seam) → STOP FINAL per the pre-committed
replication disposition. No third attempt.**
No rebaseline was performed; `fixtures/evals/baseline.json` is untouched; the F6 pin stays green
on the committed tree. Chronology: run 1 HARD-FAIL → hard stop, BLOCKED-on-user (below) →
user disposition, relayed by the coordinator as the user's explicit override of the hard stop:
ONE authorized replication, the TWO-RUN MEAN decides per the eval-v2 marginal machinery; if it
fails or the judge seam sags again in isolation, STOP FINAL with grader-drift evidence — no
third attempt. Run 2 was executed under that authorization; the two-run verdict is FAIL.

## F73 pooling remedy (user-approved 2026-07-13, interactive) → QUESTION-STOP

The user approved (governance signature, relayed by the coordinator) the F73 pooled-dispersion
remedy: append BOTH runs' seam scores to the baseline's stored noise history through the
harness's legitimate path, recompute ε from the enlarged history, and re-evaluate the SAME
two-run verdict — zero new runs, zero score changes. Rationale signed with it: byte-identical
judge prompt, calibration held, ε at quantum floor from a 3-run history (the F73 failure
class). Constraint attached: a real harness mechanism only; never hand-edit baseline.json;
if no mechanism exists, QUESTION-STOP.

Findings (verified in `gpu_agent/evals/harness.py` and `gpu_agent/cli.py`):

- F73's pooling machinery shipped: `pooled_epsilon` (ε = max(2·stdev of the seam's run
  history, quantum floor)) and `append_run_to_history` (appends a run's seamMeans to
  `seamHistory`, recomputes ε; for a pre-F73 baseline like ours — no seamHistory/quanta
  fields — it seeds the pool from the 3 stored replicate seam means).
- `append_run_to_history` enforces the NON-POISONING invariant (explicit F73 review fix,
  pinned by `tests/test_evals_v2.py`): it refuses any run whose verdict decision is not
  pass/marginal-pass — "a regression can never widen epsilon and hide itself". Our runs
  (hard-fail, marginal-fail, two-run fail) are all refused.
- No CLI/governance surface exposes pooling: `eval` actions are emit-brain, record-brain,
  emit-grade, record-grade, verdict, rebaseline only.
- Conclusion: the requested append has no legitimate path. Hand-editing baseline.json is
  forbidden; calling the library function with a spoofed verdict would bypass the invariant
  (a hand-edit with extra steps); editing the guard is worse. None of these was done —
  QUESTION-STOP per the disposition's own constraint branch.

Read-only projection (real harness functions `_seed_history` + `pooled_epsilon`, true quanta
from the cases, bars anchored at the stored seamMeans — `append_run_to_history` does not move
means; nothing written):

- extract: pool [6.625, 6.5, 7.125] + [7.0, 6.875] → ε 0.5184, bar 6.2316; two-run 6.9375 PASS
- judge:   pool [7.75, 7.5, 7.5] + [7.0, 7.25]     → ε 0.5701, bar 7.0132; two-run 7.1250 PASS
- thesis:  pool [6.0, 6.0, 6.0] + [6.0, 6.5]       → ε 0.5000, bar 5.5000; two-run 6.2500 PASS

The remedy would flip the verdict to PASS on every seam; the blocker is solely the missing
signed mechanism. Recommended minimal mechanism and the conservative alternative are filed in
`.superpowers/handoffs/f65-tsmc-QUESTIONS.md` (Option A: governance-signed `--force-reason`
override on `append_run_to_history` + an `eval pool` CLI action with the override
audit-stamped into the baseline, mirroring `rebaseline_v2`'s existing force_reason idiom;
Option B: fresh 3-run rebaseline at current grader strictness, invariant kept absolute).

## Two-run verdict (`work/eval-2026-07-13-r2/verdict.json`, authoritative)

- Decision: **FAIL** (`eval verdict --runs work/eval-2026-07-13-r1 work/eval-2026-07-13-r2`)
- Reason: regression on 'judge': 7.125 < bar 7.333 (replicate mean 7.583 − eps 0.250)
- Two-run seam means vs bars: extract 6.9375 (bar 6.4375 — pass), judge 7.125 (bar 7.333 —
  FAIL; hard bar 7.083 — cleared), thesis 6.25 (bar 5.50 — pass). Craters: none.
- The judge seam sagged again in isolation: it is the only failing seam in both runs, which is
  the second STOP-FINAL condition in the disposition independently of the mean.

## Run 2 (`work/eval-2026-07-13-r2/`, single-run report MARGINAL-FAIL)

- Seam means: extract 6.88, judge 7.25, thesis 6.50, implication 7.00 (new seam, informational).
- Per-case: extract 8/7/8/6/8/8/4/6 (01,02,03,03-01,03-02,04,05,06); judge 7/7/8/7
  (01,02,03-01,03-02); thesis 6/7 (01,03-01); implication-01 7.
- Grader calibration held: all 5 negatives ≤ 4 (extract-90 = 2, judge-90 = 1, thesis-90 = 0,
  thesis-91 = 2, implication-90 = 1).
- record-brain gated 15/15 clean; record-grade accepted all 20 grades; both runs' reports carry
  identical 4-seam promptHashes (pin-join applied to the working tree for both record-grade steps).

## Grader-drift evidence (why the judge sag reads as grader strictness, not prompt regression)

1. The judge PROMPT is byte-identical to the baseline bundle in both runs — the pin's judge hash
   (31cd7bd9…) never moved; only the additive implication seam was being joined. Nothing the
   brains were shown changed.
2. The sag is concentrated on ONE rubric criterion. In run 2, three of four judge cases lost
   exactly one point each on evidence-discipline (judge-01, judge-02, judge-03-02 all 7/8 with
   evidence-discipline = 1; judge-03-01 clean 8/8); run 1 showed the same uniform ~1-point
   pattern (7/7/8/6 vs baseline medians 8/8/8/7). Fresh Opus graders now apply the anchor-1
   reading "grounded overall but one claim outruns its citation" to marginal attribution
   nuances (e.g. a year added to "HBM3E sold out", demand-vs-capacity framing of a wafer-count
   finding) that baseline graders passed at 2.
3. Calibration did not drift: judge-90 scored 1 in both runs (limit 4), and all ten negative
   grades across the two runs are calibrated. The graders are not broken; the strictness of the
   marginal anchor moved.
4. The two-run judge mean (7.125) clears the HARD bar (7.083) and misses only the epsilon bar
   (7.333), where the judge epsilon (0.250) sits at its quantum floor from a 3-run baseline
   history — the F73 seam-noise / epsilon-too-tight class. This is a marginal-band sag, not a
   crater: no case dropped below its negative-calibration band and no seam regressed anywhere
   else.

## Disposition trail

- Run 1 HARD-FAIL → hard stop per pre-committed eval-v2 disposition; branch parked green;
  reported BLOCKED-on-user (sections below preserved verbatim from the run-1 notes).
- User disposition (relayed by the coordinator as the user's explicit decision; not an
  AFK-default): one authorized replication; two-run mean decides; pass → governance rebaseline,
  commit, push; fail or judge-in-isolation sag → STOP FINAL, no third attempt, grader-drift
  evidence into run notes + sentinel, report BLOCKED.
- Run 2 executed 2026-07-13 under that authorization; two-run verdict FAIL (above) → STOP FINAL
  actions taken: pin-join reverted from the working tree (patch remains committed for one-step
  reapply), baseline untouched, run notes + sentinel updated, branch left green.

## Run 2 protocol notes (nothing silent)

- Same protocol as run 1: tool-less Opus subagents (harness model option `opus`; repo model
  stamp `claude-opus-4-8`), one generation per case, no --force, no hand-edited answers or
  baseline. Run 2 brain prompts verified byte-identical to run 1's (emit is deterministic).
- Brain re-dispatches: thesis-03-01 (first dispatch used 1 tool — protocol-invalid,
  content-blind fresh re-dispatch); implication-01 (first emit wrapped in code fences — re-emit
  requested; the clean re-emit completed out-of-band and its answer was relayed verbatim by the
  coordinator, persisted exactly as relayed, and passed the deterministic gate — documented
  deviation: the relay hop, not the harness notification, carried the final bytes).
- Grader re-dispatches/continuations, all for schema/format violations, never for scores:
  extract-03 ×1 and extract-90 ×1 (prose + second JSON), extract-05 ×1, judge-01 ×1, judge-02 ×1,
  judge-03-01 ×1, thesis-91 ×1 (extra keys such as score_note / padding keys), implication-90 ×1.
- Documented deviations carried over from run 1: fixed tool-less instruction wrapper around every
  canonical bundle; the three negative-case graders (extract-90, judge-90 + thesis-90/91) reused
  the run-1 compressed TASK-context dispatch text — for thesis-90/91 the dispatch bytes were
  recovered from the run-1 session transcript and verified: embedded frozen answers and curator
  notes byte-equal to the canonical r2 grade prompts before dispatch.
- Context-compaction recovery: this session was compacted mid-grading; the extract-03 and
  extract-90 clean re-emits were recovered verbatim from the session transcript JSONL (last
  matching completion result per agent), transport XML escaping mechanically inverted, JSON
  schema-validated, then persisted. No grade content was reconstructed from memory.

---

# Run 1 notes (preserved verbatim)

**Outcome: HARD-FAIL on run 1 → hard stop per the pre-committed eval-v2 disposition. BLOCKED-on-user.**
No rebaseline was performed; `fixtures/evals/baseline.json` is untouched; the F6 pin stays green
on the committed tree. No retry was attempted (coordinator instruction: the disposition is
pre-committed, not negotiable).

## Verdict (run 1, `work/eval-2026-07-13-r1/verdict.json`)

- Decision: **HARD-FAIL**
- Reason: regression on 'judge': 7.000 < bar 7.333 (baseline replicate mean 7.583 − eps 0.250;
  hard bar 7.083 — missed by 0.083)
- Seam means (run vs baseline): extract 7.00 (base 6.75, bar 6.44 — pass),
  judge 7.00 (base 7.583, bar 7.333 — HARD-FAIL), thesis 6.00 (base 6.00, bar 5.50 — pass),
  implication 7.00 (new seam — no baseline bar; informational)
- Craters: none. Grader calibration: all 5 negatives calibrated
  (extract-90 = 2, judge-90 = 1, thesis-90 = 0, thesis-91 = 2, implication-90 = 1; limit 4).

Per-case (run vs baseline median): extract 6/8/8/8/8/7/4/7 (meds 7/7/7/8/8/6/6/6);
judge 7/7/8/6 (meds 8/8/8/7); thesis 7/5 (meds 7/5); implication-01 7 (new).

## Read of the failure (for the user's decision — not acted on)

The judge PROMPT is byte-identical to the baseline bundle (only the implication seam was being
added; the pin's judge hash is unchanged). The fail is a uniform ~1-point sag on 3 of 4 judge
cases with fresh Opus graders — the seam-noise / epsilon-too-tight class F73 flags: the judge
epsilon (0.250) sits at its quantum floor from a 3-run history. Options are the user's:
(a) treat as grader noise → authorize a fresh re-gate attempt (re-run from step 1);
(b) treat as real → investigate grader strictness drift before any rebaseline;
(c) widen the noise pool first (F73 pooled-epsilon needs accepted runs, which this cannot be).

## State parked

- The 4-seam pin-join changes (prompt_hash seam tuple, emit load_hash_input, hash-input.json
  implication entry, pin/hash/census test updates, negative golden case
  `implication-2026-07-90.json`) were REVERTED from the working tree to keep every commit green,
  and preserved verbatim in `docs/superpowers/evals/2026-07-13-f65-regate-pin-join.patch`
  (`git apply` from the worktree root reapplies them in one step).
- Run 1 artifacts preserved under `work/eval-2026-07-13-r1/` (brain-prompts/answers/gates,
  grade-prompts/answers, report.json, verdict.json, per-case dispatch + answer + grade files).
  work/ is gitignored — do not clean.
- The committed F65 feature (registry, implication.py, gate, store, FOR TSMC renderer, CLI verb,
  run-cycle step, positive golden case, seam wiring in cases/emit/harness/rubric) is unaffected
  and remains green: the seam wiring is additive and the pin still hashes {extract, judge, thesis}.

## Protocol notes (nothing silent)

- All brains and graders were dispatched as tool-less Opus subagents (harness model option
  `opus`; the repo's model stamp for Opus is `claude-opus-4-8`). One generation per case; judge
  cases sharing a briefing were separate generations (F38).
- Re-dispatches, all for invalid output or protocol violations, never for unlucky scores:
  - implication brain: 1 re-dispatch (voice-lint: banned word 'leverage' — the brain echoed the
    registry label "Pricing leverage" into prose; prompt-data tension worth a registry-label
    rethink at the next design touch).
  - judge-03-02 brain: 1 re-dispatch (first dispatch used 1 tool — protocol-invalid, content-blind).
  - Graders re-dispatched for schema/format violations (extra keys like score_note/reasoning,
    prose+multiple JSON objects, malformed nesting): implication-90 ×3, extract-90 ×1,
    judge-01 ×1 (continuation), judge-02 ×1 (continuation), judge-90 ×1 (continuation),
    judge-03-02 ×2 (first used 1 tool; second emitted clean with compressed context).
- Documented deviations: (1) every dispatch prepends a fixed instruction wrapper (tool-less,
  JSON-only) around the canonical emitted bundle; (2) for judge-03-02's final grader dispatch and
  the three negative-case graders, the TASK-context section was a faithful compression of the
  canonical briefing rather than verbatim bytes (context-budget recovery); one evidence sub-claim
  in judge-03-02's grade ("Indonesia" not in the finding) is an artifact of that compression —
  the criterion's score is independently grounded and matches the discarded full-context grade
  (6/8 either way). (3) Subagent transcripts are not persisted by the harness, so answers were
  relayed via completion notifications and re-persisted verbatim; XML transport escaping
  (&amp;/&lt;/&gt;) was mechanically inverted at assembly — verified against the source document
  text (e.g. "Compute & Networking" in the SEC excerpt).
- record-brain gated 15/15 clean after the two brain re-dispatches; record-grade accepted all
  20 grades; the verdict machinery validated the run (no invalid-run reasons).
