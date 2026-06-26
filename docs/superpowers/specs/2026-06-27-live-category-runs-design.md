# Live Category Runs — make `/run-cycle` run any scope live, in one command

- **Date:** 2026-06-27
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **References:** [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) Part 38 (the harness),
  Part 37 (the gathering swarm), Part 17 (no invented numbers) ·
  [`.claude/skills/run-cycle/SKILL.md`](../../../.claude/skills/run-cycle/SKILL.md) (the harness trigger, sub-project 1) ·
  [`.claude/skills/gather-category/SKILL.md`](../../../.claude/skills/gather-category/SKILL.md) (the Category leg) ·
  [`gpu_agent/llm/claude_code.py`](../../../gpu_agent/llm/claude_code.py) (the brain backend) ·
  [`gpu_agent/llm/factory.py`](../../../gpu_agent/llm/factory.py) · [`gpu_agent/cli.py`](../../../gpu_agent/cli.py) (`cycle-plan`, `pipeline`)

---

## 1. Context & goal

Sub-project 1 (the Claude Code harness, merged to `main` @ `69bd416`) gave us a single scope-selecting
trigger — `/run-cycle scope:<category|layer|all>` — that resolves a scope into a deterministic cycle plan
(ready vs. `skipped-no-assignment`) and runs the Category tier, reporting Layer/Main as deferred. But the
skill as shipped only documents a **recorded $0 dry-run**; it does not actually drive a **live** run, and the
live brain backend has never been exercised.

**Goal:** make it so that, in one command from an open Claude Code session, the user can run **whichever
scope they specify, live and complete** — real web gathering plus the real Opus brain — for every category in
that scope that has an assignment, with sensible cost guardrails and no surprise spend.

Today two things block that:

1. **The live brain backend is unproven.** `pipeline --backend claude_code` would call
   `ClaudeCodeClient._raw_complete`, which carries a *"BUILD-TIME VERIFICATION REQUIRED"* note, has **no test
   coverage**, and the `[llm]` extra (`claude-agent-sdk`) **is not installed**. So a live run would fail at
   the brain step.
2. **The `run-cycle` skill doesn't orchestrate a live run.** Its procedure describes resolving the plan and a
   recorded replay; it does not drive `gather-category` (live gather) → `pipeline --backend claude_code` (live
   brain) per ready category, and has no preview/confirm for a multi-category fan-out.

### Guiding principle (user)
> I want everything to live within Claude Code itself, with one interface. Make the original GPU-agent
> adjustments first — run whichever agent I specify, live and full, easily — then think about multi-tier
> agents later.

### Decisions locked in brainstorming (do not relitigate without reason)
- **Coverage = run only what has an assignment.** "Full" means every category in the scope that already has a
  `fixtures/asg.<id>.json` runs completely live; assignment-less categories stay `skipped-no-assignment`
  (today: `chips.merchant-gpu`, `models.frontier-closed`). **No** taxonomy-default assignment generator in
  this sub-project.
- **Backend = keep the GPU agent as configured: `claude_code`.** The existing default in `factory.py` and the
  CLI (`--backend claude_code`, `--model claude-opus-4-8`) — the Claude Code subscription via
  `claude-agent-sdk` + `CLAUDE_CODE_OAUTH_TOKEN`, Opus. No architecture change, no switch to the metered API.
- **Ergonomics = live default + preview/confirm on multi-category.** Live is the zero-flag default. A single
  category runs immediately; a `layer:`/`all` scope first prints the plan (how many assigned categories will
  run, the per-category doc ceiling) and waits for **one** confirmation before fanning out. A recorded $0
  replay remains available behind an explicit flag/mode for dry-runs and CI.

### Where this sits in the roadmap (decomposition)
- **This sub-project — Live Category runs.** The live brain backend works + the trigger drives a real run, in
  one command, with guardrails. The foundation every higher tier builds on.
- **Next sub-project (named, deferred) — Multi-tier Opus fan-out.** One interface in Claude Code that fans
  out a per-category Opus agent → feeds per-layer Opus agents → (optionally) Main, with nested delegation
  (session → category-agent → gatherers) — i.e. the real Tier-1→Tier-2→Tier-3 swarm. Claude Code **supports**
  nested subagents (a subagent granted the `Agent` tool can spawn its own, up to a fixed depth cap) and the
  **Workflow** tool is the idiomatic multi-tier orchestrator. Its two open decisions: **(a)** amend the
  charter's *"delegation one level deep"* invariant to permit N-level delegation; **(b)** choose the mechanism
  — nested subagents vs. a Workflow script. Out of scope here.

---

## 2. Scope

**In scope (additive — the frozen brain stays untouched):**
1. **Make the live `claude_code` brain backend work** — install/declare the `[llm]` extra, verify and (if
   needed) fix `ClaudeCodeClient._raw_complete` against the installed `claude-agent-sdk` call surface, give it
   real test coverage for the response-assembly/empty-response/token-missing paths, and prove the end-to-end
   live path via the existing gated smoke (`GPU_AGENT_LIVE_LLM`).
2. **Upgrade the `/run-cycle` skill** to drive a live run end-to-end (live by default), per ready category,
   reusing `gather-category` for the Category leg, with a preview/confirm gate for multi-category scopes and a
   recorded escape hatch. Validated by a documented dry-run (and a live single-category smoke if a token is
   available).

**Out of scope (unchanged or deferred):**
- The frozen contract: `gpu_agent/schema/`, the 6 dimensions, `gate.py`, `scoring.py`, `pipeline.py`'s Part-7
  gate, the Increment-A registry (`registry/indicators.py`, `validate.py`). Also unchanged: the extraction
  (`extractor.py`) and judgment (`judge.py`) adapter **signatures** — we only make the backend they call work.
- A taxonomy-default assignment generator (coverage stays "what's assigned").
- Parallel category fan-out; the Layer and Main tiers; nested/multi-tier agents (the next sub-project).
- The metered `anthropic_api` backend (exists; not the configured default; not touched).

---

## 3. Architecture

The split mirrors Part 38: **deterministic code computes + gates + stores; the session orchestrates.** This
sub-project adds **no new deterministic resolution code** — `cycle-plan` already emits the plan the skill
needs. The two work items are (1) a model-backend adapter fix (code, but an adapter, not the frozen brain),
and (2) the orchestration skill (a markdown procedure).

### 3.1 Component map

| Component | Change | Why |
|---|---|---|
| `gpu_agent/llm/claude_code.py` (`ClaudeCodeClient`) | **Fix + cover** | Make the live Opus brain actually return valid JSON via `claude-agent-sdk`; remove the "verify at build time" hazard. Adapter, **not** frozen. |
| `pyproject.toml` `[llm]` extra | **Install into `.venv`** | `claude-agent-sdk` must be importable for the live path. Already declared; just not installed. |
| `.claude/skills/run-cycle/SKILL.md` | **Upgrade** | Drive a live run end-to-end, live-by-default, with preview/confirm; reuse `gather-category`. |
| `tests/test_claude_code_client.py` (new) | **Add** | Unit coverage for chunk-assembly / empty-response / missing-token using a fake SDK (no network). |
| The gated live smoke (`GPU_AGENT_LIVE_LLM`) | **Exercise** | The only end-to-end proof of the real SDK call; run it once with a token. |

Untouched: `cycle-plan`/`pipeline`/`ingest` CLI surface, `extractor.py`, `judge.py`, `pipeline.py`, scoring,
gate, store, registry.

### 3.2 Data flow (one `/run-cycle scope:<x>` invocation, live default)

```
session (the one interface, plain driver)
  │
  1. cycle-plan --scope <x> --out store/cycle-log.json        (deterministic; ready vs skipped)
  │
  2. preview/confirm gate
       • single category            → run immediately
       • layer:/all                 → print "N assigned will run live (≤maxDocuments each); M skipped";
                                       WAIT for one confirmation before fan-out
  │
  3. for each READY category (sequential, v1):
       gather-category (live):  session subagents web_fetch → blobs.json
       ingest:                  blobs.json → docs/ (+ gather-log.json, trust tiers)
       pipeline --backend claude_code --model claude-opus-4-8 --as-of <asOf> --captured-at <ISO>
                                → store/<cat>/<asOf>-v<n>.json   (Opus extract+judge; code scores+gates)
  │
  4. Layer stage: report "deferred — not yet built (next sub-project)"
     Main stage:  report "deferred — not yet built"
  │
  5. finalize store/cycle-log.json: per-category scorecard path + DMI/SMI + tier-stage statuses
  │
  6. report: scope, categories run (paths + DMI/SMI), categories skipped (reason), deferred tiers
```

`mode: recorded` (explicit) swaps step 3's `--backend claude_code` for `--recorded-extract/--recorded-judge`
against committed fixtures — the $0 dry-run/CI path. Delegation stays **one level deep** (session →
gatherers) in this sub-project — consistent with the current charter.

### 3.3 The backend fix (detail)

`_raw_complete(prompt, system, model)` must, against the installed `claude-agent-sdk`:
- import the documented single-shot surface (`query`, `ClaudeAgentOptions`), adjusting names to the installed
  version if they differ (this is the "verify at build time" step);
- run the async query, concatenate the text chunks, and return the assembled string;
- raise `LLMError` on an empty response (so the retry/validate loop in `complete_with_retry` engages);
- surface a **clear, fail-loud** error when `CLAUDE_CODE_OAUTH_TOKEN` is absent or the `claude-agent-sdk`
  import fails — never a silent empty result.

The JSON-validity guarantee already lives upstream in `complete_with_retry` (2 retries → `LLMError`); the fix
must not duplicate or weaken it. `complete_json` stays a thin pass-through to `complete_with_retry`.

---

## 4. Error handling (all fail-loud — Part 38 no-silent-truncation)

| Condition | Behavior |
|---|---|
| `[llm]` not installed / `CLAUDE_CODE_OAUTH_TOKEN` unset (live run) | Stop with: *"live backend unavailable: install the `[llm]` extra and set `CLAUDE_CODE_OAUTH_TOKEN`, or re-run with `mode: recorded`."* **Never** silently fall back to recorded. |
| A ready category gathers **zero** documents | Skip it with a logged reason; no empty scorecard (existing `gather-category` rule). |
| Backend returns invalid JSON | Existing `complete_with_retry` (2 retries) handles it; if exhausted → `LLMError`. That **one** category fails loud and is logged in the cycle log; the cycle continues to the next ready category. |
| Bad scope string | `cycle-plan` exits 1 with `CYCLE SCOPE ERROR:` (already built). |
| `layer:`/`all` with **zero** assigned categories | Report "nothing to run (no assignments for this scope)" and stop — no empty scorecards (existing skill rule). |

A partial cycle (some categories failed/skipped) is **reported as partial with reasons**, never presented as
complete. The cycle log records the outcome per category so the run is replayable and the coverage gap is
visible.

---

## 5. Testing strategy

- **Deterministic suite stays green** (baseline 112 passed, 3 skipped) after every change. The `claude_code`
  fix must not alter recorded-path behavior.
- **New unit coverage** (`tests/test_claude_code_client.py`, no network): inject a fake SDK
  (monkeypatch/import shim) and assert: (a) multi-chunk responses concatenate correctly; (b) an empty response
  raises `LLMError`; (c) a missing `CLAUDE_CODE_OAUTH_TOKEN` / missing `claude-agent-sdk` fails loud with the
  documented message. This retires the "no unit coverage" hazard so the backend isn't wholly smoke-gated.
- **Gated live smoke** (`GPU_AGENT_LIVE_LLM`, already in the suite as a skip): run once with a real token to
  prove the actual `claude-agent-sdk` call surface end-to-end. Document the observed output in the task
  report. (Remains env-gated/skipped in normal CI.)
- **Skill validation (no pytest, documented dry-run — the `gather-category`/`run-cycle` precedent):**
  - `mode: recorded` single-category run → scorecard written, DMI/SMI reported.
  - `layer:chips` → preview lists assigned vs skipped; confirm gate visible; skips surfaced (no silent
    truncation).
  - If a token is available: one **live** single-category run (`category:chips.merchant-gpu`) end-to-end,
    output recorded in the report.

### Honest dependency
The live smoke and the live skill validation require `CLAUDE_CODE_OAUTH_TOKEN` in the environment. The backend
fix, the `[llm]` install, the unit tests, and the recorded-path skill validation do **not** — they can be
completed and proven without a token. If the token isn't exposed to the implementer, the live end-to-end proof
is run by the user (e.g. via `! <command>`) and recorded; the sub-project is otherwise complete and green.

---

## 6. Acceptance criteria

1. `pip install -e ".[llm]"` succeeds in `.venv`; `import claude_agent_sdk` works.
2. `ClaudeCodeClient._raw_complete` is verified against the installed SDK (no "verify at build time" hazard
   remains) and has unit coverage for chunk-assembly, empty-response (`LLMError`), and missing-token/missing-SDK
   fail-loud paths.
3. The full deterministic suite stays green (112 passed, 3 skipped); the `GPU_AGENT_LIVE_LLM` smoke passes when
   run with a token (documented).
4. `/run-cycle scope:<x>` runs **live by default**: a single category runs immediately end-to-end
   (gather → ingest → Opus brain → scorecard); a `layer:`/`all` scope prints a preview and waits for one
   confirmation before fanning out; assignment-less categories are reported skipped, never dropped.
5. `mode: recorded` still produces the $0 replay; missing backend/token **fails loud** with guidance, never a
   silent recorded fallback.
6. Frozen contract untouched (schema, 6 dimensions, gate, scoring, pipeline gate, registry); extraction/
   judgment adapter **signatures** unchanged. `git diff main..HEAD` shows changes only in
   `gpu_agent/llm/claude_code.py`, `pyproject.toml` (if the extra needs adjustment), the new backend test, and
   `.claude/skills/run-cycle/SKILL.md` (+ this spec/plan).
7. The multi-tier Opus fan-out is recorded as the named next sub-project (with the charter delegation-depth
   amendment + Workflow-vs-nested mechanism as its open decisions).
