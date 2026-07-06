# Worked examples — desk-research-methodology

Full narratives behind the precedents cited in SKILL.md. Read SKILL.md first; this file is the
deep-dive backing it, not a substitute.

## F62 — the evidence-bar precedent in full {#f62}

Trigger: F62 added an `observed=<date>` tag to emitted judge/thesis finding rows. This drifted
the judge and thesis prompt hashes (extract's prompt was untouched), arming the eval gate.

**Attempt 1** (`work/eval-f62-2026-07-04/`): FAIL. extract 6.25 (vs. incumbent 6.62), judge 6.50
(vs. 6.75), thesis 6.00 (pass, vs. 5.50). Per-case extract deltas swung both directions on an
**unchanged prompt** (+1,-1,0,-2,+2,-2,-2,+1 → net -3) — first sign this run carries real
generation noise, not just a regression signal.

**Disposition, written before attempt 2 ran** (this is the pre-committed-disposition discipline
of SKILL.md §2, not just the evidence-bar discipline of §1): run one full replication with the
same emitted prompts; if it passes, rebaseline on it; if it fails, STOP, keep the pin red, record
BLOCKED-on-user with both runs' data. Not retry-until-green.

**Attempt 2**: FAIL, judge-seam only. extract 6.75 (now passing — confirms attempt 1's swing was
noise, not a real deficit), judge 6.25 (fails again), thesis 6.00 (passes again, improved twice).
Cross-attempt judge picture: 6.75 (baseline) → 6.50 (a1) → 6.25 (a2), below incumbent twice, with
a **consistent signature**: all 8 fresh judge generations across both attempts scored
`sensitivity-differentiation = 1` — the rubric wanted a sentence stating "where and why this read
departs from the consensus view," and the post-F67 three-sentence narrative voice budget left no
room for it. None of the deductions referenced the `observed=` dates at all — ruling out the
change actually under test as the cause of the judge deficit.

This is the full evidence-bar move: (1) one mechanism (voice-budget crowds out the
consensus-departure sentence) explained the *entire* deficit across two independent attempts and
8 generations; (2) the competing hypothesis (the observed= tag broke judge quality) was
positively ruled out by the negative evidence that extract, whose prompt never changed, showed
noise of the *same magnitude* and thesis *improved* under the same tag.

**Attempt 3** (user-approved option B): amend the judge system prompt to explicitly demand the
consensus-departure clause. This is a falsifiable prediction made before results exist: if the
mechanism is right, all four fresh judge generations should move `sensitivity-differentiation`
1→2. Result: judge 7, 8, 7, 8 — the criterion moved 1→2 on **all four**, "exactly the deficit
signature attempts 1–2 diagnosed." PASS: extract 6.75, judge 7.50, thesis 6.00. Rebaselined
without `--force`. Full suite after rebaseline: 970 passed / 3 skipped / 0 failed.

Source: `docs/superpowers/2026-07-04-f62-eval-run-notes.md`; disposition commit `b9301e8`; prompt
fix commit `b8f41f8`; rebaseline commit `f605a77`.

## F27 — the counter-example in full {#f27}

The 2026-07-02 full-repo review (three parallel deep reads: core pipeline, temporal store/brief,
ops/docs) recorded, as an accepted fact in the initial backlog draft, that `models.frontier-closed`
had "empty weights (zero indices)" — i.e., the second category's scoring indices rendered as
zero because its registry weights were unset. This reads as a completely plausible mechanism: no
weights, no contribution, zero index. It was **not checked against the actual scoring code**
before being written down.

When Wave 2 Lane H actually implemented F27 ("make frontier-closed runnable"), the note recorded
in the merged wave summary reads: *"the old empty-weights-zero-indices claim was stale, registry-
weight fallback meant indices were never zero; the real deliverables are explicit weights +
manifest + persona + runnability pins."* The scoring code had a fallback path the original review
never traced, so the diagnosed failure mode (zero indices) had never actually been true — the
real gap was elsewhere (no manifest, no persona, hardcoded merchant-gpu assumptions).

The lesson this repo draws from its own history: a mechanism sounding right, and even being
written into a structured backlog by a careful multi-reviewer process, is not the same as being
checked. The five minutes of tracing the actual fallback path would have caught it before it sat
as accepted fact for a day.

Source: `docs/fix-backlog.md` Wave-2 merge note (near top of file, dated 2026-07-02, main
`d933b7e`); F27 entry itself in the Wave-H section.

## eval-v2-in-a-day — the structural-fix-over-retry precedent {#eval-v2}

Timeline (all 2026-07-04 → 2026-07-05):

1. F63 (corroboration doctrine) finishes its 7 build tasks, mechanisms graded well in review.
2. Task 8 (run-eval) runs **twice**, both FAIL vs. the F62 incumbent bar (extract 6.75/judge
   7.50/thesis 6.00): attempt 1 = 6.38/7.00/6.00-tie; a full replication = 6.38/6.75/5.50.
3. Diagnosis in the run notes themselves: no deduction in either run traces to an F63 prompt
   change; the F63-specific mechanisms (corroboration exception, direction enum, acronym
   allowlist) all graded well. The incumbent bar itself — F62's attempt-3 "merit PASS" — had been
   privately acknowledged a day earlier as "a high draw." Identical-prompt runs were later shown
   to swing 6.25–7.50 on the judge seam alone.
4. Per pre-committed disposition: STOP, pin stays red, no rebaseline, no `--force`,
   BLOCKED-on-user.
5. Resolution was **not** "force past it" and **not** "retry a third time hoping for a better
   draw." The user approved building eval-v2 as its own feature: a 3-replicate baseline, bar =
   mean − ε (ε = max(half-range of the 3 means, one grading quantum)), a per-case crater prong at
   median − 3, and a marginal-fail band that earns exactly one replication (never a third run).
   Designed and built in roughly one calendar day, merged `c0d5dd2`.
6. F63 re-gated under eval-v2 and PASSED on the first try (r1: extract 6.625 vs. bar 6.5833 —
   margin 0.042, "deep inside noise" by the project's own later F73 finding, but a governed PASS
   under the new bar). Merged `017b592`.

This is the flagship "the bar was wrong, so rebuild the bar" episode — the team's response to two
good-faith gate failures was to fix the measurement instrument, not to lower the bar, force past
it, or keep re-rolling until a lucky draw arrived.

Sources: `docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`,
`docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md`,
`docs/superpowers/eval-notes/2026-07-05-eval-v2-migration-run-notes.md`,
`docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`.

## F74's 8-angle review — adversarial refutation after a green suite {#f74}

The F74 fix (cycle-plan must never destroy the finalized cycle journal) shipped its first pass
with a green pytest suite. Rather than treat "tests pass" as "done," a dedicated adversarial
review pass — described in the fix commit as an "8-angle review" — was run specifically to look
for ways the guard itself could be wrong or incomplete. It found and the team then *empirically
verified* (reproduced, not just argued) four real defects before shipping the hardened version
(commit `9a5f9b2`):

1. The guard's key sets (`_PLAN_TOP_KEYS`/`_PLAN_ENTRY_KEYS`) were hand-copied rather than derived
   from the `CyclePlan`/`CycleEntry` pydantic models — three independently-maintained sets could
   drift and either refuse the CLI's own legitimate bare output, or worse, silently pass a
   clobber (a false-green tripwire).
2. `entries`/`stages` were not type-checked as containers — a null or mis-typed shape raised a
   raw `TypeError` (or, worse, could be silently counted as "bare" and passed) instead of refusing
   cleanly.
3. Reading the existing `--out` target did not handle a Windows BOM (`utf-8-sig`) — a
   BOM-prefixed file could disguise a bare plan as a real journal and slip past the guard.
4. A directory passed as `--out` raised an uncaught `OSError`/`PermissionError` traceback instead
   of a clean refusal with a corrective message.

The commit records: *"Empirical verify pass confirmed all four code findings before fixing."*
That sentence is the point — the adversarial pass did not stop at spotting plausible-looking
gaps; each one was reproduced before it was trusted enough to fix. This mirrors the evidence bar
of §1 applied to a *review*, not just a diagnosis: a finding from an adversarial pass is not
accepted until it, too, is verified to actually occur.

Source: commit `9a5f9b2` ("fix(F74): harden the guard per 8-angle review - all confirmed
findings"); `docs/fix-backlog.md` F74 entry, "STATUS 2026-07-05" paragraph.

## The blind baseline ablation — pre-registration in full {#ablation}

Set up 2026-07-05, scored by the user 2026-07-06 (`docs/ablation-2026-07/`). Three artifacts on
identical scope (merchant GPU market, ~45 days, as-of 2026-07-05):

- **A** = an RSS-digest baseline: one fresh web-only subagent, zero repo context, prompted to
  summarize the last ~45 days as a one-page executive digest with a citation per item.
- **B** = the desk itself: the July 2026 monthly flagship render plus the 2026-07-05 daily
  render, verbatim projections of the committed store (scorecards `2026-07-v3` and
  `2026-07-05-v1`) — a $0 replay, not a fresh generation.
- **C** = a one-shot deep-research baseline: one fresh web-only subagent, zero repo context,
  prompted to assess demand vs. supply, the binding constraint, key risks, and what to watch,
  1–2 pages, every claim cited.

Letters were assigned by `random.shuffle` at build time; the mapping lived **only** in
`ANSWER-KEY.md`, which the user was instructed not to open until after scoring. `SCORING.md`
pre-registered the rubric before any reading happened: four 1–5 criteria (decision-usefulness,
insight beyond headlines, currency, trustworthiness with **2 mandatory citation spot-checks per
artifact**), plus a forced single "keep decision." A contamination check confirmed the two
baseline agents' citations were web-only (no repo/store paths leaked through). The scoring doc
itself flags the blinding as imperfect (visibly different house styles) and says to score anyway
— the point is the side-by-side judgment, not a perfect double-blind.

**Verdict** (recorded in `docs/action-items.md`, quoted near-verbatim from the user's read): A
(RSS) "tells me a lot but doesn't tell me what to look out for... just a bunch of news articles
put together"; B (the desk) "I quite like every single section... it tells me the implications
and what to look out for," criticized only for being scattered and voluminous; C (deep-research)
organized but stale, "I can't really take this information back to my desk."

The desk won on substance — implications and watch-items are exactly the thesis-book/trigger
machinery, and neither web-only baseline produced them even once. Every deficit named was
presentation-layer, not intelligence-layer, and became **F77** (brief hierarchy: order by
importance, consolidate sections, cap volume — a renderer-only fix, no prompt/eval impact). Note
what this ablation actually tested: it is a genuine adversarial comparison against real, currently-
available alternatives (a cheap news digest, a cheap deep-research pass), not a comparison against
a strawman — which is what makes the "desk wins on substance" result load-bearing rather than
self-congratulatory. Had the baselines won, that would have been just as valid a result under the
same pre-registration.

## The 2026-07-03 research pass — verified-claims-only method and its own limits {#research-pass}

`docs/2026-07-03-agent-best-practices-research.md` used a deep-research harness that started from
105 candidate claims about agent-system best practices and kept only 25 as verified, each
confidence-labeled. Its own §7 is a **refuted-claims list** — specific numbers and claims
(MAST per-category failure percentages, Zep/Graphiti benchmark win margins, a +10.8pp
deterministic-aggregation effect, Finnhub archive coverage depth) that the harness checked and
found did not hold up, recorded explicitly so a future pass does not cite them by memory. §8
records an open question where the research produced **zero surviving verified claims** at all
(the search/scraper-stack comparison) — an honest "we don't actually know" is itself a valid
research output here, not a failure to hide.

The pass's core verdict — that this repo's architecture (deterministic gates + LLM reasoning +
enforced citations, tool-less orchestrated workers, staying on Claude Code skills rather than a
framework) matches documented best practice, and that the single self-inflicted gap was "no eval
harness" (closed by F6) — was accepted. Its two concrete recommendations grounded in that same
verified research (SEC-EDGAR/`sec-api.io` sourcing; a search-API/scraper benchmark) were
considered and **rejected anyway**, user-approved 2026-07-03, "do not resurrect without new
evidence." The epistemics lesson this repo draws: a claim being verified and a recommendation
being well-grounded in verified claims are two different bars from a recommendation being
*adopted* — adoption is a decision about fit, cost, and priority that the research method does
not and should not make for the user.
