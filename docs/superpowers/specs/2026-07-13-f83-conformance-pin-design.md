# F83 (pin half) — Orchestration-prose conformance pin for unattended cycles

**Status:** approved design, ready for a lane plan.
**Decision provenance — user-approved 2026-07-13 (interactive, orchestrator session): land the
conformance pin NOW; the event-triggered wake-up is DEFERRED until the standing watchlist
poller exists** (building the trigger before the detector is scaffolding with nothing to fire
it). Form of the pin below is the assistant's lean, recorded here; unsettled forks =
QUESTION-STOP → `.superpowers/handoffs/f83-conformance-QUESTIONS.md`, end turn, wait.

## Problem

Unattended scheduled dailies went LIVE 2026-07-12 (the F83 permission flip), but the roadmap's
own precondition never shipped: `run-cycle`'s session-orchestrated behavior is skill PROSE that
no test pins (the audited soft spot in the roadmap's standing constraints). A drifted skill
edit, or a session skipping a prescribed step, currently fails silent — exactly what the F74
clobber and the F71 bypass proved happens in practice.

## The pin (lean)

A deterministic conformance suite, `tests/test_run_cycle_conformance.py`, that drives the $0
recorded path end-to-end (`pipeline --recorded*` verbs over `fixtures/recorded/*`) into a temp
store and asserts the machine-checkable prescriptions of `run-cycle/SKILL.md`:

1. **Journal shape:** the produced cycle-log entry carries `asOf`/`mode`/`capturedAt`/`gates`
   (+ the F74 no-bare-`ready` rule) — via the existing models, not hand-copied key lists.
2. **Gate order + presence:** extraction gate → judge (sufficiency evaluated) → thesis →
   report voice lint; each gate's outcome recorded in the journal; no whole-run bypass flags
   on any live verb (the F75 rule, asserted).
3. **Nothing silent:** the known-drop fixtures produce their logged drop/cap/skip lines
   (stderr contract: `DROPPED`/`UNREGISTERED-ENTITY`/sufficiency notes as applicable).
4. **Write discipline:** store writes confined to the tracked carve-outs; scratch under
   `work/` only; `store/cycle-log.json` never regresses to a plan skeleton (reuse the F74
   tripwire's models).
5. **Prose↔pin sync guard:** the checklist the test asserts is a CONSTANT in the test file
   with a doc-sync check — the SKILL.md step list section carries a fingerprint comment; if
   the skill's step list changes without the test constant changing, the suite fails loud
   (the same pattern as the compliance-matrix rot lint).

**Honest residual (must be WRITTEN into the test's docstring and the sentinel):** steps that
are genuinely session-judgment (live gather quality, brain re-dispatch reasoning, commit
etiquette) cannot be pinned by a recorded replay — enumerate them explicitly rather than
implying full coverage. The pin covers the drivable skeleton; the residual list is the honest
boundary.

## Lane ownership / hard constraints

Owns: the new test file, minimal additions under `fixtures/recorded/` if the existing fixtures
lack a needed shape (fixtures are recorded artifacts — never hand-author brain answers; reuse
committed ones), a fingerprint comment in `run-cycle/SKILL.md` (one line), a short operator
note in `docs/web-reach.md` or the autonomy section if the plan finds a natural home. Must NOT
touch: product code (if a conformance assertion FAILS against current behavior, that is a
FINDING to report via QUESTION-STOP — never "fix" product code in this lane), prompts, store/,
frozen core. Suite green at every commit (baseline 1346/5); F6 pin untouched.

## Acceptance

1. The recorded-path conformance run passes on today's main.
2. Mutation checks (temporary, in-test-dev only): deleting a journal key, reordering a gate,
   or silencing a drop line makes the suite fail loud — demonstrated red-green in the lane's
   notes.
3. The SKILL.md fingerprint desync fails loud.
4. The residual (unpinnable) step list is written and honest.

## Non-goals (deferred with the user's explicit approval)

The event-triggered wake-up and any poller; changes to scheduling; touching the Task Scheduler
job; pinning live-gather behavior.
