# F65 implication re-gate — run notes (2026-07-13)

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
