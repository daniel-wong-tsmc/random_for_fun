# F24 Stage 1 — Entity Resolver (canonical identity for new data)

**Status:** approved design, ready for a lane plan.
**Decision provenance: every pick below is user-approved 2026-07-12 (interactive AskUserQuestion,
orchestrator session — NOT AFK).** The lane agent builds to this spec; any question or fork it
hits is a QUESTION-STOP per repo CLAUDE.md "Orchestrated lane agents" — write
`.superpowers/handoffs/f24-entities-QUESTIONS.md` + recommendation, end the turn, wait.

## Problem

`NVDA` and `nvidia` are two different entities everywhere in the pipeline: wiki pages split
(`store/wiki/entity/nvda.md` vs `nvidia.md` exist today), scoring buckets by `(entity,
indicatorId)` so aliases fragment DMI/SMI mass, and multi-category entities will double-count
the moment desk #2 exists. The compliance matrix (F23) rates Part 21 "counted once" as
NOT-ENFORCED — the top aspiration gap. Entity data with `aliases` / `appearsIn` /
`primaryCategory` already exists in `docs/taxonomy.json` `seedEntities` but no code consumes it.

## User-approved decisions (2026-07-12)

1. **Scope = stage 1 only: new data.** The resolver applies where NEW findings enter the
   system. Historical consolidation of already-split wiki pages / stored findings is a separate
   follow-up with its own store-repair sign-off (stage 2, not this lane).
2. **Unknown entities pass through, flagged.** Known aliases normalize to canonical ids;
   unregistered names are NOT rejected — they pass, marked and counted per cycle in run logs
   (discovery-lane compatible).
3. **Data home = `docs/taxonomy.json` `seedEntities`, consumed in place.** No new registry
   file, no data duplication. Resolver reads it via the `gpu_agent/config.py` path convention.

## Architecture

- **New module `gpu_agent/entities.py`** — the single resolver:
  - loads `seedEntities` from the taxonomy (via `config`), builds a case-insensitive
    alias→canonical-id map (canonical id, tickers, name variants);
  - `resolve(name) -> (canonical_id, registered: bool)` — unregistered names return the
    normalized-slug form of the input with `registered=False`;
  - accessors for `primaryCategory` / `appearsIn` (stage 1 ships the accessors + tests;
    cross-category counted-once logic becomes live at desk #2);
  - deterministic: same input → same output; no I/O beyond the one taxonomy read (cached).
- **Seam A — finding creation (extraction side, NOT the frozen gate):** normalize
  `Finding.entity` in code immediately after brain-output validation, before gate/routing.
  The plan pins the exact function; if Finding construction turns out to live inside frozen
  core, that is a QUESTION-STOP.
- **Seam B — wiki entity-page keying (`gpu_agent/wiki/ingest.py`):** entity page slugs derive
  from the resolved canonical id, so no NEW nvda-vs-nvidia splits are minted. Existing split
  pages are untouched (stage 2).
- **Flagging (no schema change):** per-cycle counts + names of unregistered entities land in
  the run's cycle-log entry / gather-log surface the plan identifies — never a new Finding
  field.

## Hard constraints

- **Zero emitted-prompt byte changes.** `tests/test_evals_baseline_pin.py` must stay green. If
  the agent concludes prompt vocabulary is needed (e.g. listing canonical entity ids to the
  brain), QUESTION-STOP — that rides the F6 gate and is the user's call.
- **Frozen core untouched:** `gate.py`, `scoring.py`, `schema/*` (Finding schema frozen — no
  new fields), `judgment/briefing.py`, `judge.py` aggregation, `pipeline.py`,
  `sufficiency.py`, JsonStore.
- **No store/ data edits.** Stage 1 is code + tests only.
- **Merge-independence from F25:** do not touch `gpu_agent/wiki/{log,store,lint,textscan,
  bench}.py` (F25's reviewed, unmerged surface). `wiki/ingest.py` is free.
- Windows + repo conventions per CLAUDE.md; suite green at every commit (baseline 1200/5).

## Acceptance (each pinned by a test)

1. Alias resolution: `NVDA`/`Nvidia`/`nvidia` → one canonical id; case-insensitive; ticker and
   name variants from seedEntities all land on the same id.
2. Seam A: a validated brain answer carrying an alias stores a finding under the canonical id.
3. Seam B: wiki ingest of findings for an alias writes/updates the canonical entity page slug.
4. Unregistered pass-through: an unknown name is stored un-rejected, `registered=False`, and
   appears in the cycle's unregistered-entities count.
5. `primaryCategory`/`appearsIn` accessors return taxonomy truth.
6. F6 pin green; full suite green.

## Non-goals (stage 2+, do not build)

Historical wiki-page/store consolidation; strict rejection mode; prompt vocabulary; new
registry file; cross-category dedup logic beyond the accessors.
