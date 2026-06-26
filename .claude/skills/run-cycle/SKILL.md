---
name: run-cycle
description: Use to run the GPU Category Agent swarm for a chosen scope — a specific category, a whole layer (all its categories), or the entire market. Manual-trigger; the session is the coordinator (charter Part 38). v1 runs the Category tier; Layer and Main are deferred stages.
---

# Run Cycle (the Claude Code harness — charter Part 38)

You are the **plain driver** for a swarm cycle. You turn a **scope** into a set of category runs, run the
Category tier over them via the existing gathering swarm + frozen brain, write a replayable cycle log, and
report each tier-stage's status. v1 executes **Category**; **Layer and Main are deferred** stages you report,
not run.

## Invariants (charter Part 38 — do not violate)
- **The session orchestrates; code computes + gates + stores.** You drive; the deterministic CLI does the
  scoring, gating, and persistence. You never invent a number or edit the frozen brain.
- **Delegation one level deep.** You (the session) are each category's coordinator; gatherers are your only
  sub-level (charter Part 37). Do not nest coordinators.
- **No silent truncation.** A selected category with no assignment is reported as skipped, with the reason —
  never dropped quietly.
- **Replayable.** Every run writes a cycle log; a cycle you can't replay from it did not happen.

## Inputs
- `scope` — one of: `category:<id>` (e.g. `category:chips.merchant-gpu`), `layer:<id>` (e.g. `layer:chips`),
  or `all` / `market`.
- `asOf` (e.g. `2026-06`), and the model backend choice: in-session/recorded (default, $0) or a metered
  backend (`--backend claude_code`, requires the `[llm]` extra + a token).

## Procedure
1. **Resolve the scope to a cycle plan** (deterministic — no LLM):
   ```
   .venv/Scripts/python -m gpu_agent.cli cycle-plan --scope <scope> --out store/cycle-log.json
   ```
   This prints the plan and writes the initial cycle log. Categories with no assignment are printed to
   stderr as `SKIPPED <id>: skipped-no-assignment` — report these; do not chase them.
2. **Run each `ready` category (Category tier), sequentially.** For each `ready` entry, run that category
   through the gathering swarm + frozen brain by following the **`gather-category`** skill for its
   `assignment_path` and `asOf` (gather → ingest → `pipeline`). For a deterministic dry-run, use the
   recorded fixtures instead of live gathering (see the dry-run below). Record the written scorecard path
   (`store/<categoryId>/<asOf>-v<n>.json`) and its DMI/SMI.
3. **Layer stage — deferred.** Do not run it. Report: "Layer assessment: deferred — not yet built
   (sub-project 3)." For a `layer:` or `all` scope, name which layer(s) would be assessed.
4. **Main stage — deferred.** Report: "Main / market-state: deferred — not yet built (sub-project 4)."
5. **Finalize the cycle log.** Update `store/cycle-log.json` with, per ready category, its scorecard path +
   DMI/SMI, and the tier-stage statuses (`category: done`, `layer: deferred`, `main: deferred`).
6. **Report:** the scope, categories run (with scorecard paths + DMI/SMI), categories skipped (with reason),
   and the deferred Layer/Main stages.

## Caps & safety
- A live `all` run fans out gatherers across ~34 categories — honor any budget/`maxDocuments` the user gives,
  and log anything skipped. If no backend/token is available for a metered run, say so and use the in-session
  recorded path; never silently produce an empty or partial cycle as if it were complete.
- If zero categories are `ready`, report "nothing to run (no assignments for this scope)" and stop — do not
  write empty scorecards.

## Snapshot / determinism
`store/cycle-log.json` + the per-category gather snapshots + scorecards are the saved artifacts; the cycle
replays from them. A cycle that can't be replayed from its log did not happen.
