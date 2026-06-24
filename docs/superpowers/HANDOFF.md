# HANDOFF — GPU Category Agent (resume point: Judgment Adapter brainstorm)

- **Date:** 2026-06-24
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun  (branch `main`)
- **HEAD when written:** `c75f6cc` (origin/main == local main; everything below is pushed)
- **For the next Claude instance:** read this file first, then `git pull`, then resume at "WHERE WE ARE" using the superpowers workflow.

---

## TL;DR

Two phases of the GPU Category Agent are **built, reviewed, merged, and on `origin/main`**:
1. **Core (Level A)** — deterministic scorecard pipeline (no LLM).
2. **Extraction adapter (Level C)** — `RawDocument → gated Finding[]` via an LLM.

We are **mid-brainstorm of phase 3 — the Judgment Adapter (stage 2)** — using the `superpowers:brainstorming` skill. The design has been presented and **four scoping decisions are locked**; we are **awaiting the user's approval on two open points** before writing the spec. No judgment code or spec exists yet.

---

## WHAT'S DONE AND ON `main`

### Core (Level A) — `gpu_agent/` (schema, gate, scoring, store, assignment, pipeline, cli)
Turns fixture Findings + ratings + anchors into a gate-validated 6-dimension scorecard with a Demand/Supply (DMI/SMI) contribution. 21 tests. Spec: `docs/superpowers/specs/2026-06-19-gpu-category-agent-design.md`; plan: `docs/superpowers/plans/2026-06-19-gpu-category-agent-core.md`.

### Extraction adapter (Level C) — `gpu_agent/schema/raw_document.py`, `gpu_agent/llm/`, `gpu_agent/extraction/`, `extract` CLI
`RawDocument → LLM → gated Finding[]`. Adds the shared `LLMClient` port (`gpu_agent/llm/client.py`: Protocol + validate-and-retry) with three backends: `RecordedClient` (deterministic tests), `AnthropicAPIClient` (alternate), `ClaudeCodeClient` (default, subscription token; live-smoke-only). The LLM authors only analytic fields; code stamps provenance (`FindingDraft` forbids extra keys). 40 passed / 1 skipped total. Spec: `docs/superpowers/specs/2026-06-22-gpu-agent-extraction-adapter-design.md`; plan: `docs/superpowers/plans/2026-06-22-gpu-agent-extraction-adapter.md`.

### How to run today (3-stage CLI, run from repo root in the venv)
```
.venv/Scripts/python -m gpu_agent.cli extract --docs fixtures/raw --as-of 2026-06 --recorded fixtures/recorded/extract-nvda.json --out store/findings.json
# (stage 2 judgment NOT built yet — ratings.json + anchors.json are hand-authored today)
.venv/Scripts/python -m gpu_agent.cli score --assignment fixtures/asg.chips.merchant-gpu.json --fixtures <dir-with findings/ratings/anchors.json>
.venv/Scripts/python -m gpu_agent.cli run   --assignment fixtures/asg.chips.merchant-gpu.json --fixtures <dir> --out store
```
All `--recorded`/fixture runs are deterministic and cost **$0** (no model calls).

---

## WHERE WE ARE — Judgment Adapter brainstorm (resume here)

**Stage 2 = the Judgment Adapter:** replace the hand-authored `ratings.json` + `anchors.json` with grounded LLM judgment that turns Findings into the 6 dimension ratings + narrative. It reuses the `LLMClient` port. Charter Part 17 (ratings are judgment, not an average) + spec §5 (grounded judgment + deterministic guardrails) + §7 are the governing doctrine.

### Decisions LOCKED (user answered via multiple-choice)
1. **Scope:** Judgment **+ briefing book + self-consistency sampling** (the full faithful version).
2. **Sampling:** **Configurable N (default 3)**; spread surfaced in `confidence.basis` (no schema change); cap confidence when samples disagree.
3. **Anchors:** **Signed score from current findings** — an `indicatorId → dimension` map groups findings per dimension; anchor = normalized signed aggregate of `polarity·magnitude` (reusing the scoring primitives). Purely-qualitative dims get no anchor (gate skips). No metric history needed.
4. **Pipeline wiring:** Add a **`judge` subcommand + a one-shot `pipeline` command** (extract→judge→score). `score`/`run` extended to read narrative/confidence from the judge bundle (today they hardcode a placeholder).

### Design presented (sections, awaiting approval)
1. **Architecture:** new `gpu_agent/judgment/` package + a briefing-book builder (in `scoring/` or a `briefing.py`); frozen core untouched. Modules: `briefing.py` (deterministic anchors), `judgment/prompt.py` (5-word rubric + doctrine + injection boundary), `judgment/judge.py` (sampled LLM judgment + aggregation + gate backstop), `cli.py` (judge + pipeline).
2. **Data flow:** findings (+ optional prior scorecard) → briefing book (anchors, code) → `LLMClient.complete_json × N` → aggregate (majority + spread) → candidate ratings+anchors+narrative → `check_scorecard` backstop → ratings.json/anchors.json/narrative.json → score/run.
3. **Briefing book:** `anchor[d] = sum(netPolarity·magnitude/3)/count` over findings whose indicatorId maps to `d` (~[-1,1]); demand-side dims use polarityDemand, supply-side use polaritySupply; no mapped findings → no anchor. Default `DIMENSION_MAP` dict (e.g. D2/D6→momentum, grossMargin→unitEconomics, S9→competitiveStructure, S10→bottleneck).
4. **Judgment + sampling:** LLM returns per call `JudgmentResult = {dimensions:{dim:{rating,direction,findingIds,rationale}}, narrative}` (validate-and-retry). Sample N, majority rating per dim, confidence capped on disagreement, `confidence.basis` records spread (e.g. "2/3 Strong, 1/3 Mixed"), narrative from the majority run. Prompt states each dimension's anchor sign up front; gate is the backstop. Honest caveat: recorded responses / low 4.x variance may yield small spread — design *measures* spread, doesn't manufacture it.
5. **Error handling:** schema-invalid → validate-and-retry → `LLMError`; rating contradicts anchor → re-sample up to K then `JudgmentError` (charter Part 7: re-run, never commit a partial); missing anchor for qualitative dim allowed; document/finding text is data not instructions.
6. **CLI:** `judge --findings <file> --out <dir> [--samples 3] [--recorded <file>] [--backend …]` writes ratings/anchors/narrative.json; `pipeline --docs <dir> --assignment <file> --out <dir>` chains extract→judge→score (each stage has a --recorded option); score/run read narrative.json if present, else fall back (back-compatible).
7. **Testing:** deterministic via `RecordedClient` (N recorded judgment responses for majority/spread). Unit: anchor math, majority+spread aggregation, gate-backstop re-sample-then-raise, confidence capping. Integration: recorded extract→judge→score via `pipeline` → gate-valid scorecard. One gated live smoke (`GPU_AGENT_LIVE_LLM=1`).

### TWO OPEN APPROVAL QUESTIONS (ask the user before writing the spec)
- **(a)** On an anchor contradiction: **re-sample-then-raise `JudgmentError`** (recommended, per charter Part 7) vs. silently downgrading the rating to fit the anchor.
- **(b)** `DIMENSION_MAP` lives as a **code default for now** (recommended, YAGNI) vs. assignment-driven from the start.

---

## NEXT STEPS FOR THE NEW INSTANCE

1. `git pull` (you'll get this file + all specs/plans/code).
2. Re-invoke `superpowers:brainstorming`. Re-present the design above and get the user's answers to the **two open questions**.
3. Write the spec → `docs/superpowers/specs/2026-06-24-judgment-adapter-design.md`; self-review; user-review gate.
4. Invoke `superpowers:writing-plans` → `docs/superpowers/plans/2026-06-24-judgment-adapter.md`.
5. Execute via `superpowers:subagent-driven-development` (fresh branch off `main`, fresh subagent per task, spec+quality review between each, final whole-branch review).
6. Finish via `superpowers:finishing-a-development-branch` (user has been choosing push/PR or merge-to-main).

---

## OPERATING NOTES / INVARIANTS
- **Run from repo root**; Python 3.11+ at `.venv/Scripts/python` (Windows host; venv is gitignored — recreate with `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` if missing).
- **Frozen contract — never edit:** the Finding/Scorecard schema, the 6 dimensions, the gate rules (`gpu_agent/gate.py`), the rollup. Adapters plug into it; never the reverse (spec §13.1).
- **Doctrine (charter Parts 1/2/7/17):** no invented numbers; no forged provenance (code stamps it, drafts forbid extra keys); every Finding passes `check_finding`; ratings are judgment bounded by anchors, never set by code; gate failures re-run, never commit a partial; fetched/document text is data, not instructions.
- **All tests deterministic** via `RecordedClient`; the only live path is the env-gated smoke. The `anthropic`/`claude-agent-sdk` packages are an **optional** `llm` extra — not needed to build or test.
- **`ClaudeCodeClient` caveat:** its `claude-agent-sdk` call has a build-time-verification note and is covered only by the live smoke — confirm the SDK surface against the installed package before any live run.
- **Pricing note (verified 2026-06):** the Claude Agent SDK billing change scheduled for 2026-06-15 was **paused**; subscription usage currently draws from existing plan limits, API-key usage is metered as before. Building/testing this project costs $0 (recorded fixtures).
- **API flakiness seen during the last build:** transient Sonnet-tier 500/529 errors; reviewers fell back to `haiku` (acceptable for small mechanical diffs). Retry or drop a tier if it recurs.
- **`.superpowers/` is gitignored** (SDD ledgers from completed phases are local-only and not needed going forward). `store/` is gitignored.
