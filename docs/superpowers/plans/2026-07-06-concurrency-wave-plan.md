# Concurrency Wave Plan — open backlog (F60, F64, F65, F66, F71–F77, F23–F25)

**Status:** DRAFT for user review. **Nothing is branched, dispatched, or committed** — dispatch is
held per the 2026-07-06 decision until this plan and the per-lane task plans are reviewed and approved.

**Date:** 2026-07-06 · **Author:** coordinator session (Opus 4.8) · **Base:** main @ `6fe1841`

---

## 1. Locked decisions (user-approved 2026-07-06)

| # | Decision | Consequence |
|---|---|---|
| D1 | Gate cluster ships as **one contract v1.4** migration bundling **F72 + F71**, with **F75** as companion doctrine on the same branch | One shadow-run, one replay, one Opus review; mirrors v1.2 coupled-stream + v1.3 companion-doctrine precedents |
| D2 | **F60 = registry-weight DATA half only** this wave; `scoring.py` side-semantics **DEFERRED** | F60 stays a fast data lane off the frozen path — but the deferred half MUST be picked up later (see §6 Deferred Ledger) |
| D3 | **F72 records the originating publisher as gather-blob metadata**, not a Finding schema field | v1.4 stays **schemaVersion 1.2** — no schema-field change, minimal migration shape like v1.3 |
| D4 | **Hold all dispatch** until this plan + per-lane task plans are reviewed and approved | No worktrees claimed, no lane agents launched, no commits, until user go |

These are user-approved decisions, not AFK-defaults.

## 2. Why the shape is forced (the four serializers)

1. **User-locked order (cannot reorder):** roadmap Phase 1 pins `F60 → F64 → F65 → F66`. Serial by lock, regardless of files.
2. **Frozen core = one Part-33 migration, user-approved, never AFK-merged.** F71, F72, and F60's (deferred) scoring half all land on this surface.
3. **The eval hash-pin is one global gate.** Prompt-changing work (F60 vocab, F64 thesis, F65 judgment) serializes through `run-eval` one at a time.
4. **One renderer (`report.py`)** — additionally contended right now by the live `dashboard-showcase` instance (see §7).

## 3. Wave structure

| Stream / worktree | Items | Class → path | Build model | Review at merge |
|---|---|---|---|---|
| **P1** `fix/coord-hygiene` | F76 | Docs/process → lane | Sonnet | Sonnet |
| **P2** `fix/eval-gate-power` | F73 | Ordinary code (eval infra) → lane | Opus | Opus |
| **P3** `fix/contract-v1.4` | F72 + F71 (+ F75 companion) | Frozen-core + doctrine → **Part-33 migration** | Opus | Opus-class + migration artifacts |
| **S1** `fix/freshness-weights` | F60 (data half) | Data → lane (+ pin re-check) | Sonnet | Sonnet |
| **S2** `fix/renderer` | F77 | Ordinary code → lane | Sonnet | Sonnet |
| **S3** sub-projects | F64, then F65 | Feature → brainstorm→spec→plan→SDD | Opus | Opus + F6 eval gate |
| **S4** `fix/citation-audit` | F66 | Ordinary/feature → lane | Sonnet | Sonnet |
| **W4** sub-projects | F24, F25 (parallel to each other), F23 (docs) | Feature/docs | mixed | tiered |

**Parallel-safe wave (up to ~4 at once):** P1, P2, P3, plus the already-live `dashboard-showcase`.
File-disjoint: docs vs `evals/harness.py` vs `gate.py`/`scoring.py`/`publisher.py`/charter vs the
dashboard worktree. This front-loads the autonomy-blocking gate cluster (P3).

**Forced-serial pipeline:** `F60 → F77 → F64 → F65 → F66` — serial three times over (user lock,
shared `report.py`, single eval pin). Not parallelizable.

## 4. Barriers

- **B1 — eval-gate stabilization:** P2 (F73) must merge **before** any product-chain rebaseline, so
  later prompt changes are judged by the improved gate.
- **B2 — the migration pivot:** P3 (contract v1.4) must merge **before S1 starts** — F60 and the
  F64/F65 trust-footer render both interact with the gate/scoring + F75 bypass-waiver surface.
- **B3 — eval pin per prompt change:** F60 (if vocab changes), F64, F65 each pass `run-eval`
  (Opus brains + Opus rubric graders) one at a time; no retry-until-green.

## 5. Merge order

`P1, P2` (any order, when green) → **`P3` (pivot)** → `S1 → S2 → S3 (F64 → F65) → S4` → `W4`.
Full suite green + eval re-gate at each step. **Every merge to main is the user's gate**; the frozen
migration cannot be merged under an AFK-default.

## 6. Deferred Ledger — MUST NOT LOSE (user-directed 2026-07-06)

- **F60 — `scoring.py` side-semantics (the "give leading indicators real DMI/SMI weight" half).**
  Deferred this wave by user direction ("do the first option, but continue with what is deferred
  later"). Rules: (a) when F60's data half merges, **do NOT tick F60 as fully done** — the scoring
  half remains open; (b) the scoring change is FROZEN-CORE and ships as a **future migration
  (v1.5)**, never a data lane; (c) mint/track it explicitly at pickup time so it does not vanish
  behind F60's checkbox. Re-surface this in the next HANDOFF and any handoff doc.

## 7. Open pre-reqs before ANY dispatch

1. **Reconcile the live `dashboard-showcase` instance** (`.worktrees/dashboard`): read its spec/diff,
   confirm whether its presentation work overlaps F77/F64/F65 before the renderer stream is shaped.
   Its uncommitted edits are already visible on the main checkout (desk-skill mods, charter, the
   dashboard spec) — coordinate via HANDOFF, do not touch its files.
2. **P3 needs its own migration spec** (via `gate-integrity-campaign` + `desk-change-control` §3)
   with user approval before the migration branch is opened — frozen core is never AFK-defaulted.
3. **Per-lane TDD task plans** for P1 (F76) and P2 (F73) finalized and reviewed.
4. **`.claude/settings.local.json` concurrent-edit-guard hook** activates on next session / `/hooks`
   reload — worth having live before multiple lanes touch the shared checkout.

## 8. On user "go" (not before)

- (a) Claim P1 + P2 in HANDOFF, then dispatch them as parallel worktree lanes (F76 Sonnet, F73 Opus).
- (b) Open the P3 v1.4 migration spec for user approval (frozen — never AFK, only the user merges).
- The serial pipeline (S1–S4) is planned per-lane **after** P3 merges.
