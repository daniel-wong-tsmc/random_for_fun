# START HERE — building the GPU Category Agent

Entry point for the implementation phase. **The design is finished and committed** — do not
re-design, re-plan, or re-edit the charter. Read the artifacts below and build to the plan.

## Status (all done, all on `main`)
- ✅ Design spec, implementation plan, and `category-agent-guide.md` committed.
- ✅ Charter reconciled (Finding **schema v1.1** — demand/supply polarity + the bias-guardrail gate).
- ⬜ **Next: write the code** — the deterministic core (this is the only thing left to start).

## Read first, in order
1. **`plans/2026-06-19-gpu-category-agent-core.md`** — the 9-task TDD plan you execute.
2. **`specs/2026-06-19-gpu-category-agent-design.md`** — the design; see **§10** (runs via Claude Code)
   and **§13** (modularity & extensibility contract).
3. **`../agent-swarm-charter.md`**, Parts **2 / 7 / 17** — the binding doctrine the code implements.
4. `../category-agent-guide.md` — demand/supply background (optional).

## How to start
1. Create a fresh branch off `main`: `git checkout -b gpu-agent-core-impl` — **do not commit to `main`.**
2. Execute the plan task-by-task with the **`superpowers:subagent-driven-development`** skill
   (fresh subagent per task, review between). Start at **Task 1** (scaffold + `Finding` model).

## Context not obvious from the files
- The **deterministic core needs NO API key and NO network** — it runs on fixtures.
- LLM steps (later, the adapter plan) reach Claude through an `LLMClient` port; default backend is
  **Claude Code subscription tokens** (`CLAUDE_CODE_OAUTH_TOKEN`), API key as alternate — see spec §10.
- The **superpowers plugin is installed**; the plan header names the execution skill.
- Tasks run **`pip` / `pytest` / `git`** locally — expect permission prompts.
- If something seems missing, prefer the plan/spec over inventing; flag genuine gaps rather than
  re-opening settled design decisions.

## Repo
`C:\Users\danie\random_for_fun` (local) · `https://github.com/daniel-wong-tsmc/random_for_fun.git`
