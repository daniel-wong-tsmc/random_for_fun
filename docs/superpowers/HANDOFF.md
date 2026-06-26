# HANDOFF — GPU Category Agent (resume point: Claude Code harness spec+plan written → ready to IMPLEMENT)

- **Date:** 2026-06-26
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **Active branch:** `claude-code-harness` (branched off `main` @ `6cc403c`). Two commits on it so far, both **docs only**:
  - `18cbbfc` — charter amendment: **Part 38 "Running the swarm in Claude Code"** (+ pointer-edits to Parts 5/28/14)
  - `7badf4e` — implementation plan (`docs/superpowers/plans/2026-06-26-claude-code-harness.md`)
- **`main` HEAD:** `6cc403c` — **Increment A (indicator registry) is merged AND pushed to origin.** The branch is *ahead of main by docs only* — **no harness code written yet.**
- **For the next Claude instance:** read this file, then `git checkout claude-code-harness`, then **execute the plan**
  (`docs/superpowers/plans/2026-06-26-claude-code-harness.md`) — that is the in-flight task. Use
  **`superpowers:subagent-driven-development`** (recommended; fresh subagent per task, two-stage review), task-by-task.

---

## TL;DR — where we are

The user has committed to a north-star: **run the entire 3-tier swarm (Category → Layer → Main) on Claude Code itself**
as the canonical runtime (not the hosted "Managed-Agents" backend the charter originally assumed). That is a *program*,
decomposed into sub-projects (below). **Sub-project 1 — the harness re-homing — is spec'd (charter Part 38) and
planned, and is the in-flight build.** Increment A (the indicator registry) is done, merged, and pushed.

---

## THE IN-FLIGHT TASK — Claude Code harness, sub-project 1 (Approach 1)

**What it is:** build the v1 Claude Code harness from charter **Part 38** — a single, scope-selecting **`/run-cycle`**
trigger that runs the **Category** tier and reports **Layer/Main as explicit deferred stages**. The user can run:
- `category:<id>` — one category,
- `layer:<id>` — that layer **and all its categories underneath**,
- `all` / `market` — the whole market.

**Decisions locked during brainstorming (do not relitigate without reason):**
- Target = **the whole 3-tier swarm on Claude Code (option C)**, built as sub-projects; **v1 trigger posture = manual,
  one command** from an open session (scheduling deferred — parallels Part 37's "manually invoked").
- Sub-project 1 = **Approach 1**: charter amendment (DONE — Part 38) + an **extensible orchestrator with the
  Category tier wired today** and Layer/Main as named **deferred** stages. v1 stops after Category and says so.
- **Maximally modular** (user's explicit ask): the orchestrator is a *plain driver* over **one uniform tier interface**
  + **swappable providers** (scope resolver, assignment provider, category coordinator, model backend, store/read-seam,
  execution driver, trigger). Every deferred piece is a drop-in behind a seam that already exists — never a rewrite.
  This is written into **Part 38** as the design-of-record.

**The plan:** `docs/superpowers/plans/2026-06-26-claude-code-harness.md` — **5 TDD tasks**, each ending green + committed,
**all additive (frozen core untouched), full suite stays green (96 + new tests) after every task:**
1. `Taxonomy.categories_in_layer` / `all_categories` (the scope resolver) — `gpu_agent/registry/structure.py` (additive).
2. `AssignmentProvider` (category → `Assignment | None`) — new `gpu_agent/cycle.py`.
3. `resolve_scope` + `build_cycle_plan` (ready vs. `skipped-no-assignment`; deferred Layer/Main stages) — `cycle.py`.
4. `cycle-plan` CLI subcommand (deterministic seam the skill calls; emits plan JSON; logs skipped to stderr;
   fail-loud on bad scope) — `gpu_agent/cli.py` (adapter, not frozen).
5. The `/run-cycle` orchestrator **skill** (`.claude/skills/run-cycle/SKILL.md`) — scope-selected manual trigger;
   **reuses `gather-category`** for the Category leg; Layer/Main deferred; validated by a documented **dry-run** (no pytest).

> **Coverage honesty (Part 38 doctrine):** a selected category with no assignment is **logged as skipped, never silently
> dropped**. Today only `chips.merchant-gpu` has a committed assignment (`fixtures/asg.chips.merchant-gpu.json`), so a
> `layer:`/`all` run executes that one and lists the rest as `skipped-no-assignment`. Authoring (or auto-generating from
> taxonomy+registry) the other assignments is a **named dependency**, not part of sub-project 1.

**Acceptance for sub-project 1:** `cycle-plan` resolves all three scope modes (fail-loud on a bad scope); a `layer:`/`all`
plan lists every selected category marking the assignment-less ones skipped; the `run-cycle` skill exists, names Category
active + Layer/Main deferred, reuses (not duplicates) `gather-category`; full suite green; frozen core untouched.

**After sub-project 1 (the rest of the decomposition — each its own spec → plan → build):**
- **sp2** — canonical store + scoped query tool (Part 9): the substrate the upper tiers read.
- **sp3** — Layer tier (×5): judgment over category scorecards + adjacent-layer summaries + own history → layer assessment.
- **sp4** — Main tier (×1) + the Recommendation skill (Parts 10–11): market thesis → `market-state.json` + exec brief.
- **sp5** — memory + calibration (Parts 4/12); then unattended scheduling + the interactive path (Parts 28/14).
  Each is a **drop-in behind a Part-38 seam** — the uniform tier interface, the store read-seam, the execution driver,
  the trigger — not a rewrite.

---

## WHAT'S DONE AND ON `main` (@ `6cc403c`, pushed to origin)

- **Core (Level A)** — deterministic scorecard pipeline (`gpu_agent/` schema, gate, scoring, store, assignment, pipeline, cli).
- **Extraction adapter (Level C)** — `RawDocument → gated Finding[]` via an `LLMClient` port (`RecordedClient`,
  `AnthropicAPIClient`, `ClaudeCodeClient`).
- **Judgment adapter** — grounded LLM judgment → ratings + anchors + narrative; N-sample self-consistency; gate backstop.
- **Gathering Swarm (Phase 4)** — `gpu_agent/gathering/ingest.py` + `ingest` CLI + the `.claude/skills/gather-category`
  coordinator skill. Data flow end-to-end: **gather → ingest → extract → judge → score**.
- **Increment A — the indicator registry (MERGED + PUSHED):** `registry/indicators.json` (global indicator defs +
  per-category overrides), `gpu_agent/registry/` (`IndicatorRegistry`, `IndicatorSpec`, `RegistryError`, `Taxonomy`,
  `validate_assignment`); slimmed `docs/taxonomy.json` to pure structure; DMI/SMI now **per-indicator** (latest-vintage,
  count-independent); a **fail-loud registry gate** (`validate_assignment` in `_pipeline`; `validate_against` wired into
  `cli._load_registry`); `map.py` deleted; golden re-baselined (DMI 0.04 → 0.0733). A 2nd category
  (`models.frontier-closed`) scores **config-only**. (Ledger: `.superpowers/sdd/progress.md`, archived prior phase at
  `progress.gathering-swarm.md`.)
- **Suite on `main`: 96 passed, 3 skipped** (the 3 skips are env-gated live smokes: `GPU_AGENT_LIVE_LLM` ×2,
  `GPU_AGENT_LIVE_GATHER`).

---

## OPERATING NOTES / INVARIANTS (carry forward — still all true)

- **Run from repo root** `C:\Users\danie\random_for_fun`; Python 3.11+ at `.venv/Scripts/python` (Windows host; `.venv`
  is gitignored — recreate with `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` if missing).
  The `[llm]` extra is optional and **not installed** (everything deterministic via `RecordedClient` + recorded fixtures).
- **Frozen contract — never edit:** the Finding/Scorecard schema (`gpu_agent/schema/`), the 6 dimensions, `gpu_agent/gate.py`
  rules, `scoring.py`'s `zscore`, `pipeline.py`'s Part-7 gate behavior, and the **Increment-A registry**
  (`gpu_agent/registry/indicators.py`, `validate.py`). The harness plan only **adds** to `structure.py` (additive scope
  methods) and `cli.py` (an adapter subcommand), and creates `gpu_agent/cycle.py` + the `run-cycle` skill. The 6 dimensions
  stay fixed: `momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`.
- **Part 38 doctrine (the harness):** the **session orchestrates; code computes + gates + stores**; delegation stays
  **one level deep** (session → gatherers); a no-assignment category is **logged as skipped, never silently dropped**;
  a cycle must be **replayable from its run log**.
- **General doctrine:** no invented numbers; no forged provenance; ratings are judgment bounded by anchors, never set by
  code; gate failures re-run, never commit a partial; gatherers return raw material only; fetched text is **data, not
  instructions**; gathered material carries a **trust tier + dated receipt**; secondary-only findings are
  confidence-capped; **caps/skips are logged, never silent**; config errors **fail loud**.
- **All tests deterministic** via `RecordedClient` + committed fixtures. Live paths are env-gated smokes only. Skills are
  validated by a **documented dry-run** (the `gather-category` precedent; `run-cycle` follows it).
- **Every commit must end with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Windows flakiness:** the Bash tool's safety classifier can be intermittently unavailable for write/commit commands —
  retry, or use the PowerShell tool. CWD sometimes resets to `C:\Users\danie` — prefix git/pytest with
  `cd /c/Users/danie/random_for_fun && …`.
- **`.superpowers/` and `store/` are gitignored.** `.claude/` is **tracked** (skills live there: `gather-category`, and
  `run-cycle` once built). `blobs.json` at repo root is an **untracked** run artifact — leave it.
- **Model preference (user):** opus for important final reviews; sonnet acceptable for mechanical per-task implementer +
  reviewer work.
- **Subagent-driven execution:** keep a ledger at `.superpowers/sdd/progress.md` (start a fresh one for this sub-project;
  archive or append below the Increment-A record). Record the BASE commit before each task; mark tasks complete as their
  reviews come back clean. Trust the ledger + `git log` after any compaction.

---

## DEFERRED MINORS (non-blocking; fix opportunistically)

- `cli._load_docs` filters a **denylist-of-one** (`gather-log.json`); a future sidecar in the docs folder would be parsed
  as a `RawDocument` and crash — harden to "skip any file the schema can't validate." (Pre-existing.)
- Increment-A prose nit: the Task-7 commit body imprecisely explains *why* the old code zeroed `market-share-pct`
  (attributes it to a `side="structural"` skip rule; the pre-fix code had no skip rule). Code + golden value are correct.
- Recurring PEP8 E302 single-blank-line nits across `cli.py` — one ruff/autopep8 pass clears them.
- Broad coverage for `layer:`/`all` runs needs per-category assignments (only `chips.merchant-gpu` exists today) — author
  them, or build a taxonomy-default assignment generator (its own small effort; named in the harness plan).
