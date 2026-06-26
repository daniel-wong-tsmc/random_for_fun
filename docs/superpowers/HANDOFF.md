# HANDOFF — GPU Category Agent (resume point: Increment A spec+plan written → ready to IMPLEMENT)

- **Date:** 2026-06-26
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **Active branch:** `indicator-registry` (branched off `main`). Two commits on it so far, both **docs only**:
  - `6461f4e` — design spec (`docs/superpowers/specs/2026-06-26-indicator-registry-design.md`)
  - `f054b84` — implementation plan (`docs/superpowers/plans/2026-06-26-indicator-registry.md`)
  - (this HANDOFF update commits on top.)
- **`main` HEAD:** `188bde9`. The branch is *ahead of main by docs only* — **no production code written yet.**
- **For the next Claude instance:** read this file, then `git checkout indicator-registry`, then **execute the plan**
  (`docs/superpowers/plans/2026-06-26-indicator-registry.md`) — that is the in-flight task. Use
  **`superpowers:subagent-driven-development`** (recommended) or `superpowers:executing-plans`, task-by-task.

---

## TL;DR — where we are

Phases 1–4 (Core, Extraction, Judgment, Gathering Swarm) are **built, merged, on `main`**. This session did two things:

1. **Ran the full live GPU agent end-to-end** (the `gather-category` skill) over the real web for `chips.merchant-gpu`
   (NVIDIA/AMD/Intel), then ran the frozen brain. Result scorecard + snapshot are in `store/` (gitignored).
2. **Analyzed that read, found real weaknesses, and turned the top one into a spec + plan.** The next move is to
   **implement Increment A (the indicator registry)** from the committed plan. Nothing else is in flight.

---

## THE IN-FLIGHT TASK — Increment A: the indicator registry

**Why (the problem, found by running the agent live):** the scoring brain is **silently GPU-shaped** and the headline
index is partly an artifact of authoring choices, not data:

- `gpu_agent/judgment/map.py` **hardcodes** `DIMENSION_MAP` / `DIMENSION_POLARITY` to GPU indicators (its own comment:
  *"YAGNI — not yet assignment-driven"*). A CPU or AI-model agent's indicators map to **nothing**.
- `scoring.dmi_smi_contribution` is a **sum over findings**, so an indicator counts once **per finding** — DMI's sign
  literally flipped on whether 1 vs 3 NVDA-quarter findings were written. The index scaled with extraction verbosity.
- `market-share-pct` and `grossMargin` map to dimensions (`moat`, `unitEconomics`) but carry **zero weight** in the
  assignment, so two of the five rated dimensions contribute **0.000** to DMI/SMI — a *silent* zero.

**The fix (this increment):** move indicator→`{dimension, polarityTrack, weight, side, unit, decayLambda,
readsLevelOrSlope}` out of code into a **define-once `registry/indicators.json`** (global defaults + per-category
overrides), make DMI/SMI aggregate **per-indicator** (latest vintage, count-independent), add a **fail-loud validation
gate**, and **slim `taxonomy.json` to pure structure** that the registry is validated against.

**The north-star principle (user's words):** *each category agent can have its own unique compute metrics, but the
processing and thought process must be uniform and sophisticated.* The registry is exactly that split — metric
**definitions** vary per category (data); the **machinery** (standardize → weight → map onto the 6 fixed dimensions →
roll up → bounded judgment) is identical for every agent (code). The plan's headline acceptance test (**Task 8**) proves
it: a second category (`models.frontier-closed`) scores end-to-end with **zero code change**.

**Decisions locked during brainstorming (do not relitigate without reason):**
- Binding scope = **global definition + per-category override** (Option 2).
- A **dedicated `registry/indicators.json` + `gpu_agent/registry/` loader**; governance split — `dimension`/`polarityTrack`
  are human-governed/durable, `weight`/`decayLambda` are calibrated (seeded now, backtest-tuned in Increment B).
- **Keep `taxonomy.json` but slim it to structure** (layers, category ids, the 6 dimensions, scale, rollup, schemas);
  lift `quantMetrics`/`qualMetrics`/`seedMetrics` into the registry; the registry validates `dimension ∈ the 6` and
  `category ∈ taxonomy`. Do **not** delete taxonomy.json or fold it into the charter — the registry references its ids
  and the (future) Layer/Main rollup needs the structure; keeping it machine-readable is what enables the cross-check.
- Scope = **registry plumbing + the aggregation-correctness fix** (per-indicator collapse), NOT z-scores/momentum.

**The plan:** `docs/superpowers/plans/2026-06-26-indicator-registry.md` — 8 TDD tasks, each ending green + committed:
1. Registry data file + `IndicatorSpec`/`IndicatorRegistry` (resolve + category override).
2. Slim `taxonomy.json` + `Taxonomy` loader + `IndicatorRegistry.validate_against`.
3. `validate_assignment` fail-loud gate.
4. Add `Assignment.category`; de-hardcode the scorecard's `categoryId` (currently hardcoded `"chips.merchant-gpu"` in
   `pipeline.build_scorecard`).
5. Rewire `judgment/briefing.py` to the registry; **delete `judgment/map.py`**.
6. Registry-driven, **per-indicator** `dmi_smi_contribution` (regression pin: duplicate findings don't move the index).
7. Thread registry + category through `judge_findings`, `build_scorecard`, and `cli.py`; run the gate; **re-baseline the
   golden** (`fixtures/golden/scorecard.json` — DMI/SMI change; document old→new deltas).
8. Generalization proof — second category, config-only.

> **Sequencing gotcha (already noted in the plan):** Tasks 5 & 6 change signatures whose CLI/pipeline callers aren't
> rewired until Task 7. Run **only each task's own test file** mid-stream; the full suite is expected green only after
> Task 7. Final verification runs the full suite.

**After A:** Increment **B** = vintage store + z-score / freshness / ΔSDGI momentum + σ-based alert tiers (the registry
already carries `decayLambda`/`readsLevelOrSlope`/`leadMonths` for it). Increment **C** = hard ≥2-source corroboration.
Both depend on A. Each is its own spec → plan → build.

---

## WHAT'S DONE AND ON `main` (unchanged from prior handoffs)

- **Core (Level A)** — deterministic scorecard pipeline (`gpu_agent/` schema, gate, scoring, store, assignment, pipeline, cli).
- **Extraction adapter (Level C)** — `RawDocument → gated Finding[]` via an `LLMClient` port (`RecordedClient`,
  `AnthropicAPIClient`, `ClaudeCodeClient`).
- **Judgment adapter** — grounded LLM judgment → ratings + anchors + narrative; N-sample self-consistency; anchor-conflict
  resample-then-raise; gate backstop.
- **Gathering Swarm (Phase 4)** — `gpu_agent/gathering/ingest.py` + `ingest` CLI + the `.claude/skills/gather-category`
  coordinator skill. Data flow end-to-end: **gather → ingest → extract → judge → score**.
- Suite on `main`: **72 passed, 3 skipped** (the 3 skips are env-gated live smokes: `GPU_AGENT_LIVE_LLM` ×2,
  `GPU_AGENT_LIVE_GATHER`).

---

## THIS SESSION'S LIVE RUN — artifacts & how it ran (context, not a task)

- **Live backend is NOT available here:** `claude_agent_sdk` is not installed and neither `CLAUDE_CODE_OAUTH_TOKEN`
  nor `ANTHROPIC_API_KEY` is set. The sanctioned live pattern in this env is **in-session**: gatherer subagents use the
  session's own web tools, and the session itself acts as the extract/judge model, fed through the deterministic CLI via
  `--recorded-extract` / `--recorded-judge`. (To use the real metered backend instead: `pip install -e ".[llm]"`, set a
  token/key, re-run `pipeline --backend claude_code` over `store/_docs` — the gather snapshot is reusable.)
- **Artifacts (all under gitignored `store/`, plus untracked `blobs.json` at repo root):**
  - `blobs.json` — gather snapshot (rounds=2, 16 unique docs, 4 skipped leads logged).
  - `store/_docs/` — 16 `RawDocument`s + `gather-log.json` (7 primary / 9 secondary).
  - `store/_brain/{extract,judge}.json` — the in-session model outputs.
  - `store/chips.merchant-gpu/2026-06-v2.json` — the final scorecard (**DMI=0.140, SMI=0.267**).
- These are **disposable demo output**, not part of the increment. Note the `2026-06-v2` suffix: `JsonStore` versioned
  because a `2026-06` entry already existed.
- **Sharp edge worth remembering:** `cli._load_docs` globs `*.json` and only skips `gather-log.json`. Do **not** point
  `ingest --out` at the repo's `docs/` folder — it already holds `taxonomy.json`, which the brain would try to parse as a
  `RawDocument` and crash. Use a clean dir (we used `store/_docs`). (This is a pre-existing known minor; see below.)

**Other weaknesses found in the read (the backlog beyond A/B/C — capture, don't lose):**
- Extraction tagged the **level** not the **slope** for D2 (the indicator is defined on the growth slope). The registry
  carries `readsLevelOrSlope` so Increment B can enforce it.
- `moat` conflated **discrete/AIB (gaming) GPU share (94%)** with **AI-accelerator share (~80%)** — different markets;
  should be distinct indicators.
- D6 rental-price collapse over-attributed to demand; it's largely a Blackwell **generation transition** (guide §8.1 says
  de-weight D6/P3 50% during transitions — not done).
- `strategicRisk` never rated although the 10-Q's **H20/China inventory provisions ($0.8–2.3B)** were available — a missed
  export-control (X3) signal.
- "high confidence, 3 samples" was **fake self-consistency** (the 3 judge samples were identical by construction). Real
  independence (or a live backend) needed before the confidence label is earned. (Calibration harness = guide §8.2.)

---

## OPERATING NOTES / INVARIANTS (carry forward — still all true)

- **Run from repo root** `C:\Users\danie\random_for_fun`; Python 3.11+ at `.venv/Scripts/python` (Windows host; `.venv`
  is gitignored — recreate with `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` if missing).
  The `[llm]` extra is optional and **not installed** (not needed — everything deterministic via `RecordedClient` +
  recorded fixtures).
- **Frozen contract — never edit:** the Finding/Scorecard schema (`gpu_agent/schema/`), the 6 dimensions, `gpu_agent/gate.py`
  rules, `scoring.zscore`, `pipeline.py`'s gate behavior. Increment A adds a **separate** registry gate and rewires which
  *inputs* scoring reads; it does not change the Part-7 finding/scorecard gate. The 6 dimensions stay fixed:
  `momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`.
- **Doctrine:** no invented numbers; no forged provenance (code stamps it; drafts forbid extra keys); ratings are judgment
  bounded by anchors, never set by code; gate failures re-run, never commit a partial; gatherers return raw material only
  (blobs + leads, never findings/judgments); fetched/document text is **data, not instructions**; gathered web material
  carries a **trust tier + dated receipt**; secondary-only findings are confidence-capped; **caps are logged, never
  silent**; a gather run that can't be replayed from its saved snapshot did not happen. **New for A:** config errors
  (unregistered metric, bad dimension, silent zero-weight) must **fail loud**, not contribute zero.
- **`RawDocument.url` is the verbatim receipt**; id/dedupe use the *normalized* url. They differ by design — don't "fix" it.
- **All tests deterministic** via `RecordedClient` + committed blob snapshots. Live paths are env-gated smokes only
  (`GPU_AGENT_LIVE_LLM`, `GPU_AGENT_LIVE_GATHER`). The gather coordinator (a skill) is validated by a documented dry-run.
- **Every commit must end with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Windows flakiness:** the Bash tool's safety classifier can be intermittently unavailable for write/commit commands —
  retry, or use the PowerShell tool. CWD sometimes resets to `C:\Users\danie` — prefix git/pytest with
  `cd /c/Users/danie/random_for_fun && …`.
- **`.superpowers/` and `store/` are gitignored.** `.claude/` is **tracked** (the gather-category skill lives there).
  `blobs.json` at repo root is currently **untracked** (a run artifact — leave it, or `git clean` it; not part of A).
- **Model preference (user):** opus for important final reviews; sonnet acceptable for mechanical per-task implementer +
  reviewer work.

---

## DEFERRED MINORS (non-blocking; fix opportunistically)

- `cli._load_docs` filters a **denylist-of-one** (`gather-log.json`). A future sidecar dropped into the docs folder would
  be parsed as a `RawDocument` and crash — harden to "skip any file the schema can't validate" or recognize docs by
  naming convention. (This is what bit the `ingest --out docs` collision above.)
- `tests/test_ingest.py`: add two cheap edge tests — query-string-distinguishes-URLs in dedupe; whitespace-only field is
  malformed. Behavior already correct; these pin intent.
- Recurring PEP8 E302 single-blank-line nits across `cli.py` — one ruff/autopep8 pass clears them.
