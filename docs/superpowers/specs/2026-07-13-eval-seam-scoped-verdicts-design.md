# Eval seam-scoped verdicts — design note (2026-07-13)

**Governance record.** USER DECISION (user-approved, interactive, 2026-07-13, relayed by the
orchestrator): build SEAM-SCOPED VERDICTS in the eval harness. The user chose this over the
assistant's recommended hash-guard-bridge (the governance-signed `--force-reason` pooling
override proposed in the F65 question-stop) — provenance recorded per the question-stop rule.
The F65 lane's scope was formally extended by the orchestrator under this decision to cover
`gpu_agent/evals/harness.py` verdict logic, its tests, and the verdict CLI output. The eval
harness is not frozen core; F73's lane precedent applies.

## Semantics (all four are the user's decision, verbatim in substance)

1. **A seam's bar applies ONLY if that seam's emitted-prompt hash in the run differs from the
   baseline's recorded hash** (the seam was actually changed). Hash-identical seams are
   INFORMATIONAL: scored, recorded, pooled into their noise history when the harness's existing
   rules allow, displayed in the verdict — but they cannot fail the run.
2. **A NEW seam** (no baseline entry) **has no bar**; it is recorded and becomes gated at its
   first rebaseline. This formalizes the existing implication-seam behavior.
3. **Grader-calibration negatives remain enforced UNCONDITIONALLY** — they test the graders,
   not the change — so a calibration breach still fails any run, even one whose every seam is
   hash-identical.
4. **If run directories don't carry the per-seam prompt hashes needed for the comparison,
   QUESTION-STOP rather than approximate.** (In the library the equivalent rule is fail-closed:
   a seam with missing hash info on either side is treated as gated, preserving the old,
   stricter behavior for legacy artifacts.)

Implementation extensions of the same principle (mechanical, recorded here as decision
provenance): the case-level crater check is scoped the same way — a crater in a hash-identical
seam's case is recorded and displayed with an `informational` flag but cannot fail the run;
a case that cannot be mapped to a seam is fail-closed (treated as gated). The F73b marginal-pass
band likewise only triggers replication for gated seams.

## Why (the byte-identical-judge episode)

The F65 re-gate (2026-07-13, runs r1+r2) failed on the judge seam — 7.125 two-run mean vs bar
7.333 — with the judge prompt byte-identical to the baseline bundle: the pin's judge hash never
moved; only the additive implication seam was being joined. Grader calibration held in both
runs (all 10 negatives in bounds) and the sag concentrated on one rubric criterion
(evidence-discipline). Nothing the judge brain was shown changed, so the bar was measuring
grader-population drift, not the change under test. The orchestrator transcript's framing: a
restaurant inspection should fail the dish whose recipe changed, not re-litigate dishes cooked
from the unchanged recipe. Verdict bars exist to catch regressions caused by the change being
gated; a hash-identical seam cannot, by construction, have been regressed by that change.

## What this dissolves, and what it does not

- The failed-run pooling question from the F65 question-stop is **DISSOLVED for this case**:
  under seam-scoped verdicts the byte-identical judge seam is informational, so the two-run
  verdict no longer needs a widened epsilon to reach the correct answer. No pooling changes are
  built; `append_run_to_history`'s non-poisoning invariant stands untouched.
- **Residual observation for a future backlog mint (do not build now):** the noise pool only
  ever accumulates seam means from accepted runs, so epsilon converges on the dispersion of
  runs that passed — a survivorship bias that systematically understates true grader noise
  (the r1/r2 judge scores, real observations of the unchanged judge seam's noise, are excluded
  from the pool by the same rule). Worth a dedicated F-item; out of scope here.

## Consequences for the F65 re-gate

Recomputed from the frozen r1/r2 data (no new runs, no score changes): extract and thesis are
hash-identical (informational; both clear their bars anyway), judge is hash-identical
(informational; its 7.125 vs 7.333 is recorded but non-binding), implication is new (no bar).
Projection: **PASS** → the pass path resumes (r3 top-up, governance rebaseline joining the
implication seam, pin-join reapply).
