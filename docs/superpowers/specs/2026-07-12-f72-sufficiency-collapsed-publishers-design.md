# F72 follow-up — Sufficiency gate counts collapsed publishers (contract v1.4.1 micro-migration)

**Status:** approved design, ready for a lane plan.
**Decision provenance: user-approved 2026-07-12 (interactive AskUserQuestion, orchestrator
session — NOT AFK): fix now as its own small Part-33 migration with a read-only shadow-check,
rather than bundling into F79.** Any question/fork the lane agent hits is a QUESTION-STOP per
repo CLAUDE.md "Orchestrated lane agents" — write
`.superpowers/handoffs/f72-sufficiency-QUESTIONS.md` + recommendation, end the turn, wait.

## Problem

Contract v1.4 (F72, merged `e16672a`) made publisher distinctness syndication-aware —
`registry/syndicators.json` + L1 near-dup collapse — but `sufficiency.py::_sufficient` still
counts raw `publisher_key` netlocs (flagged at the v1.4 merge as an explicit follow-up). Today
one press release republished on 3 domains passes the evidence-sufficiency gate's
distinct-publisher bar while the F2e gate would collapse it. Same hole, one gate left open.

## The change

- `gpu_agent/sufficiency.py::_sufficient` counts publishers over the SAME collapsed-publisher
  set the F2e gate machinery uses — reuse the existing collapse helper (locate it in
  `gpu_agent/publisher.py` / the F72 delivery; **shared helper, zero duplicated collapse
  logic**). If the existing helper is not cleanly reusable from sufficiency's call site,
  QUESTION-STOP.
- **This is the ONLY frozen-core edit sanctioned for this lane**, and only the counting seam —
  no other sufficiency semantics move. Ships as **contract v1.4.1** with a migration note
  `docs/migrations/2026-07-contract-v1.4.1.md` (what changed, why, shadow-check result).

## Shadow-check (read-only, goes in the migration note)

Recompute the sufficiency verdicts for stored past cycles wherever their inputs are
reconstructable from committed store data (cycle logs, scorecards, findings), and report
whether any past verdict would have flipped under collapsed counting. REPORT ONLY — no store
file is edited, no scorecard re-issued. If inputs are not reconstructable, say so honestly in
the note rather than approximating; that is an acceptable outcome, not a blocker
(QUESTION-STOP only if partial reconstruction forces a methodology choice).

## Hard constraints

- No emitted-prompt changes (F6 pin stays green). No store/ edits. No schema changes.
- Frozen core: ONLY `sufficiency.py`'s counting seam, per above. Everything else untouched.
- File-disjoint from the F24 / F87 / F25 / stage-6 lanes.
- Suite green at every commit (baseline 1200/5). Windows + repo conventions per CLAUDE.md.

## Acceptance (each pinned by a test)

1. One story with near-identical bodies / known syndicator domains across 3 netlocs counts as
   ONE publisher for sufficiency → fails a ≥3 bar it previously passed.
2. Three genuinely distinct publishers still pass.
3. Boundary: collapsed count exactly at the bar passes; one below fails.
4. Sufficiency ↔ F2e agreement: both gates see the same collapsed count for the same evidence
   set (shared-helper test).
5. Migration note exists, names v1.4.1, and carries the shadow-check result.
6. F6 pin green; full suite green.

## Non-goals

Changing the sufficiency thresholds, the F71 anchor-exemption semantics, or any prompt; fixing
other consumers of `publisher_key` (wiki promotion and thesis rule-6 already inherited the
collapse via the shared key in v1.4 — verify, don't rebuild; if that verification FAILS,
QUESTION-STOP with evidence).
