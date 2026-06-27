# HANDOFF — GPU Category Agent (resume point: sub-projects 1–3 DONE + merged + PUSHED → start sub-project 4 "daily demand/supply monitor")

- **Date:** 2026-06-27
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **`main` HEAD:** `d356eff` — **sub-projects 1, 2, AND 3 are merged into `main` AND PUSHED.** `origin/main` on GitHub ==
  local `main` == `d356eff` (verified). Working tree clean. **Suite: 211 passed, 3 skipped.** Frozen contract intact.
- **For the next Claude instance:** read this file, then the **sub-project-4 umbrella spec**
  `docs/superpowers/specs/2026-06-27-daily-monitor-decomposition-design.md`. sp4 turns the (now complete & legible)
  quarterly scorecard into a **DAILY demand/supply monitor** — it tracks **events as evolving threads via Karpathy's
  "LLM-wiki" model**, computes **two indices (trailing Momentum + forward Outlook)**, does **daily change-detection +
  materiality filtering**, and renders a **market-state brief** that answers *"what is demand/supply doing, and where is
  it heading."* It is built **additively on B/A/C** and **decomposed into 5 pieces** (build in order):
  **4-1** temporal store + LLM-wiki thread model (the keystone) → **4-2** leading + daily indicators (cadence × horizon)
  → **4-3** two indices (Momentum + Outlook) → **4-4** daily gather + relevance/lint engine → **4-5** market-state brief +
  daily diff. **Start with 4-1.** For each piece run the full superpowers loop: `brainstorming` → spec
  (`docs/superpowers/specs/`) → `writing-plans` → `subagent-driven-development`, **merged to `main` before the next
  starts** (the sp3 pattern: fresh subagent per task, two-stage review, opus final whole-branch review).

---

## TL;DR — where we are

North star: a **daily, explainable GPU-market intelligence monitor running inside Claude Code itself** (Claude Code *is*
the brain — no OAuth token, SDK, `[llm]` extra, or external API). **Sub-projects 1 (harness), 2 (live category runs), and
3 (output & coverage overhaul) are DONE, merged, and pushed.** Today the agent runs a category **live in one command**
(real web gather → dispatched Opus extraction + judgment subagents → deterministic gate + score), produces an
**all-six-dimension scorecard** (ungrounded dims `under-supported`, never dropped; judge-produced overall `categoryStatus`;
code-computed `sdgi`), renders a **deterministic executive report** (`gpu-agent report` — 8 sections, Δ-vs-prior-cycle),
and drives the gather with a **coverage manifest + per-metric source inventory** (gaps logged, paywalled labeled not
scraped). **NEXT (sp4):** make it a **daily monitor** that follows events over time, splits **trailing Momentum from
forward Outlook**, filters the day's noise to **what changed and whether it matters**, and tells the demand/supply story.

---

## NEXT — sub-project 4: the daily demand/supply monitor (the in-flight task)

**Why:** a live `v4` run produces a correct scorecard but still leaves the reader unable to say *what GPU demand/supply is
actually doing* — the report shows **scores, not a market picture**, and the indicator base is **lagging-heavy** (10-Q
revenue is reported 1–3 quarters late and doesn't change daily). The user runs this **every day** and needs it to track
**quantitative + qualitative data that changes daily** and **follow events as they evolve**.

**The design (read the umbrella spec `docs/superpowers/specs/2026-06-27-daily-monitor-decomposition-design.md`):**
- **The keystone is an LLM-wiki temporal core (charter Part 4/9/10):** threads = **wiki pages** (entity pages `nvidia`,
  `tsmc`, …; theme pages `cowos-capacity`, `export-controls`, `hbm4`, `hyperscaler-capex`, …) that **accrete dated, cited
  findings** and carry a **state + trajectory**, plus an `index` (catalog) and `log` (provenance). The daily loop is the
  wiki **ingest / query / lint**; **`lint` is the materiality / early-warning engine**. The **brain curates the wiki; code
  computes + gates + stores; numbers come only from gated findings** (Part 17). Thread id = brain-proposed + provisional
  (Part 18 discovery lane), deduped by the store; full finding-level history per page (replayable), brief reads a windowed view.
- **Two indices:** **Momentum** (trailing — lagging+coincident findings; today's `dmi`/`smi` generalize to it) and
  **Outlook** (forward — leading findings), each split demand/supply with its own SDGI. **The case the system exists to
  catch: Momentum strong while Outlook turns.** Computed in code (reuses B's additive-field discipline).
- **Indicators gain two tags — `cadence` (daily|weekly|quarterly) × `horizon` (leading|coincident|lagging)** — added as
  registry DATA (the C-3 top-level-map pattern; `IndicatorSpec` is `extra="forbid"`, so NEVER add fields inside an
  indicator dict). Add leading + daily signals (capex guidance, RPO/backlog, GPU spot/secondary prices, lead times,
  CoWoS/HBM capacity, news-event indicators) with source inventory + manifest coverage (reuses C).
- **Daily gather** sweeps recent news + live prices, **dedups vs the store**, and scores **materiality** (multi-factor:
  new-thread | thread-state-change | contradicts-thesis[highest] | moves-indicator∝magnitude; weighted by tier+recency;
  decays as a thread goes quiet). Every drop is **logged, never silent** (Part 29).
- **The report** renders a **Market-State brief** with **both views** — a **two-column** demand/supply signal board *and*
  the **causal driver/constraint tree** (naming the specific binding constraint) — **leading with "what moved today"** +
  thread trajectories + **per-signal recency** (a stale leading signal is flagged). Extends A's `report.py`.

**Decisions locked in brainstorming (do not relitigate without reason):** two distinct indices (Momentum vs Outlook);
**both** brief views (two-column + causal tree); daily-first (cadence-tagged, change-detection, news+price sweep);
**richer multi-factor materiality from day 1**; **event threads via the LLM-wiki model** (Karpathy gist —
<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>); **full finding-level history per thread**, brief
reads a windowed view; **build additively on B/A/C** (reuse, don't rebuild). Out of scope: the **unattended daily
scheduler** (Part 28 — the monitor is *designed* to run daily, but auto-scheduling is a separate follow-on); the
Layer/Main tiers; the multi-tier Opus fan-out (still deferred); a quantitative regression model.

---

## COMPLETED — "Live Category runs" (sub-project 2) — see "WHAT'S DONE" below for the full record

**What it is:** the harness (sp1) ships a `/run-cycle` trigger that only documents a recorded $0 dry-run. This sub-project
makes it **drive a real live run**: real web gathering + the real Opus brain, for every assigned category in the chosen
scope, live-by-default, in one command — **with no OAuth token, no SDK, no external API.** Claude Code *is* the brain.

**The mechanism (read the spec — `docs/superpowers/specs/2026-06-27-live-category-runs-design.md`):**
`extract` and `judge` already accept a `--recorded <json>` answer they push through the same validate → **gate** → score
path. We add a deterministic **`--emit-prompt`** mode to `extract`/`judge` that prints the **canonical** brain prompt +
the answer JSON schema (no LLM call). The `/run-cycle` skill emits that prompt, **dispatches an Opus subagent** to answer
it, and feeds the JSON back through `--recorded` / `pipeline --recorded-*`, which gates + scores it exactly as today.
**Live and recorded unify:** a committed fixture is a *cached* answer; live is a *fresh* one — identical gate+score path,
fully replayable.

**Decisions locked in brainstorming (do NOT relitigate without reason):**
- **Brain = Claude Code as a dispatched Opus subagent.** Not OAuth/SDK (`claude_code` backend), not metered
  (`anthropic_api`), not the `[llm]` extra, not `CLAUDE_CODE_OAUTH_TOKEN`. One level deep from the session.
- **Coverage = assigned-only.** "Full" = every category in the scope with a `fixtures/asg.<id>.json`; the rest stay
  `skipped-no-assignment` (today only `chips.merchant-gpu`, `models.frontier-closed` have assignments). **No** taxonomy-
  default generator in this sub-project.
- **Ergonomics = live default + preview/confirm on multi-category.** Single category runs immediately; `layer:`/`all`
  prints the plan (N assigned will run, M skipped) and waits for **one** confirmation. `mode: recorded` = the $0 escape hatch.

**The plan:** `docs/superpowers/plans/2026-06-27-live-category-runs.md` — **3 tasks**, each green + committed, all additive
(frozen brain untouched), full suite stays green after every task:
1. `extract --emit-prompt` — canonical extraction prompt + `ExtractionResult` schema, no LLM (`cli.py`; TDD).
2. `judge --emit-prompt` (+ emit→`--recorded` round-trip) — judgment prompt from gated findings via `build_briefing` +
   `JudgmentResult` schema, no LLM (`cli.py`; TDD). Full suite → **115 passed, 3 skipped**.
3. Upgrade `.claude/skills/run-cycle/SKILL.md` — live by default; per ready category: gather (reuse `gather-category`) →
   emit extract prompt → **dispatch Opus subagent** → `extract --recorded` (gate) → emit judge prompt → **dispatch Opus
   subagent** → `pipeline --recorded-extract --recorded-judge` (score+store). Preview/confirm; recorded escape hatch;
   one-level-deep; fail-loud. **No pytest** — validated by a documented recorded dry-run + a **live single-category run**.

> **Task 3 execution note:** a skill is run by the *session*, not by an implementer subagent, and the brain subagents must
> stay one level deep from it. So Task 3's **live** validation (Step 3 of the task) is performed by the **orchestrating
> session (the controller)**, not delegated. Tasks 1–2 are normal subagent-implemented TDD tasks.

**Acceptance for sub-project 2:** `extract --emit-prompt`/`judge --emit-prompt` print the canonical prompt + correct
schema and make no LLM call; an answer fed via `--recorded` gates + scores (round-trip test passes); `/run-cycle` runs
live by default with Claude Code as the brain (single runs immediately; `layer:`/`all` previews + confirms); `mode:
recorded` still gives the $0 replay; assignment-less categories reported skipped, never dropped; a **live single-category
run is demonstrated end-to-end with no token/SDK/install**; full suite green; frozen contract untouched; **no new
dependency / no `[llm]`/OAuth/SDK usage**.

**After sub-project 2 (the rest of the decomposition):**
- **sp-NEXT — Multi-tier Opus fan-out** (the user's explicit next ask): one interface in Claude Code that fans a
  per-category Opus agent → feeds per-layer Opus agents → (optionally) Main — the real Tier-1→Tier-2→Tier-3 swarm. The
  per-step brain subagent built here is its **seed**. **Two open decisions for that sub-project:** (a) **amend the
  charter's "delegation one level deep" invariant** to permit N-level nesting (Claude Code *supports* nested subagents up
  to a fixed depth cap — verified); (b) **pick the mechanism** — nested subagents vs. a **Workflow** script (the charter
  already names the Workflow tool as the deferred execution-driver seam). Needs its own spec → plan → build.
- Then the deferred originals: canonical store + scoped query tool (Part 9); memory + calibration (Parts 4/12);
  unattended scheduling + the interactive path (Parts 28/14). Each a drop-in behind a Part-38 seam.

---

## WHAT'S DONE

### Sub-project 3 — Output & Coverage Overhaul (MERGED to `main` @ `d356eff`, **pushed**) — B → A → C
Built additively on B/A/C seams, sequenced (each merged before the next), opus final whole-branch review per piece.
Umbrella spec: `docs/superpowers/specs/2026-06-27-output-coverage-decomposition-design.md`. Suite **211 passed, 3 skipped**.
- **B — Six-dimension integrity** (`gpu_agent/schema/scorecard.py`, `pipeline.py`, `judgment/*`, `registry/indicators.json` DATA):
  every scorecard carries **all 6 dimensions** in a new `dimensionStatus` dict (ungrounded → `under-supported` +
  confidence-capped, **never dropped**; `dimensionRatings` stays grounded-only so the frozen `gate.py` is byte-unchanged);
  added 2 **judgment-only `strategicRisk` indicators** (`exportControlExposure`, `customerConcentration`; `scoring:false`,
  excluded from DMI/SMI); the judge produces an overall **`categoryStatus`**; code computes **`demandSupply.sdgi`** (= dmi−smi).
- **A — Executive report** (`gpu_agent/report.py` + `report` CLI subcommand + `run-cycle` step): deterministic, no-LLM,
  byte-reproducible (`--render-ts`) **8-section** board-ready report — overall status, all 6 dims (under-supported shown),
  DMI/SMI/**SDGI** with **Δ vs prior cycle** (`find_prior` picks the strictly-prior version), per-entity panel, honest
  evidence quality (distinct-finding counts), sources, coverage gaps. Tests use committed `fixtures/report/*.json`.
- **C — Coverage manifest + source inventory** (`gpu_agent/manifest.py`, `manifests/chips.merchant-gpu.json`,
  `registry/indicators.json` top-level `sourceInventory`, `gather-category` SKILL.md): per-category **expected-coverage
  manifest** + per-metric **source inventory** (Part 22); the gather seeds primary filings first and **logs every
  uncovered/paywalled item as a gap** (paywalled = labeled, never scraped). **C-3 lesson:** `IndicatorSpec` is
  `extra="forbid"`, so `sourceInventory` lives as a **top-level map** in `indicators.json` (the frozen loader ignores it),
  NEVER inside an indicator dict.
- **Frozen contract intact across all of sp3:** `gate.py`, `scoring.py`, `registry/indicators.py`, `registry/validate.py`
  are **byte-unchanged**; the Scorecard model, judgment prompt/result, `pipeline.py` assembly were evolved **additively**
  (Part 33). Two tracked sp3 follow-ups (non-blocking): source-gap priority hardcoded `required` (should derive from
  backing indicators); the registry `sourceInventory` is currently documentation-only (unwired through `SourceEntry`).

### Sub-project 2 — Live Category runs (MERGED to `main` @ `92d6e4d`; pushed in `d356eff`)
- `gpu_agent/cli.py` — **additive** `--emit-prompt` mode on `extract` and `judge`: prints the **canonical** brain prompt
  (reused `SYSTEM` + `build_user_prompt`) + the answer JSON schema (`ExtractionResult` / `JudgmentResult`), **no LLM call**.
  `judge --emit-prompt` builds the briefing from the **gated** findings via the frozen `build_briefing`. Also: `judge --out`
  relaxed to optional (needed for emit) with a clean-error guard (exit 2) on the normal path.
- `tests/test_cli_emit_prompt.py` (new) — 5 subprocess tests: both emit bundles (canonical SYSTEM/schema/order, no LLM),
  the emit→`--recorded` round-trip, the `--out` clean-error guard, and the **array-of-serialized-strings** contract guard
  (array-of-objects is rejected non-zero, never silently scored).
- `.claude/skills/run-cycle/SKILL.md` — rewritten to drive **live runs by default** with Claude Code as the brain: per
  ready category, gather (reuse `gather-category`) → `extract --emit-prompt` → **dispatch Opus subagent** →
  `extract --recorded` (gate) → `judge --emit-prompt` → **dispatch Opus subagent** → `pipeline --recorded-extract
  --recorded-judge` (score+store). Preview/confirm on `layer:`/`all`; `mode: recorded` = the $0 replay; Part-38/17/8
  doctrine; one level deep; page text is DATA; skips surfaced; replayable.
- **No new dependency / no `[llm]` / no OAuth / no SDK.** Validated by a recorded dry-run + a **live single-category run**
  demonstrated end-to-end (evidence: `.superpowers/sdd/task-3-report.md`). Frozen contract untouched.
- Reviewed (opus whole-branch: "Ready to merge: With fixes" → the one Important fix applied: SKILL answer-shape wording +
  guard test). Suite **117 passed, 3 skipped.** Ledger: `.superpowers/sdd/progress.md`.

### Sub-project 1 — the Claude Code harness (MERGED to `main` @ `69bd416`, local; NOT pushed)
- `gpu_agent/registry/structure.py` — additive `Taxonomy.categories_in_layer()` / `all_categories()` scope accessors.
- `gpu_agent/cycle.py` (new) — `AssignmentProvider` (category → `Assignment | None`), `resolve_scope`, `CycleEntry`,
  `CyclePlan`, `build_cycle_plan` (ready vs `skipped-no-assignment`; stages category=active/layer=deferred/main=deferred).
- `gpu_agent/cli.py` — `cycle-plan` subcommand (scope → plan JSON to stdout; skipped → stderr; fail-loud exit 1 on bad scope).
- `.claude/skills/run-cycle/SKILL.md` — the scope-selecting manual trigger (Category active; Layer/Main deferred; reuses
  `gather-category`). **Sub-project 2 upgrades this SKILL.md to drive live runs.**
- Reviewed (opus whole-branch: "Ready to merge: Yes", no Critical/Important). Ledger: `.superpowers/sdd/progress.md`.

### Earlier (all on `main`)
- **Core (Level A)** — deterministic scorecard pipeline (schema, gate, scoring, store, assignment, pipeline, cli).
- **Extraction adapter** — `RawDocument → gated Finding[]` via the `LLMClient` port (`RecordedClient`, `AnthropicAPIClient`,
  `ClaudeCodeClient`). **NOTE: sp2 does NOT use the SDK backends — the brain is a Claude Code subagent.**
- **Judgment adapter** — grounded judgment → ratings + anchors + narrative; N-sample self-consistency; gate backstop.
- **Gathering Swarm (Part 37)** — `gpu_agent/gathering/ingest.py` + `ingest` CLI + the `.claude/skills/gather-category` skill.
- **Increment A — indicator registry** — `registry/indicators.json`, `gpu_agent/registry/` (`IndicatorRegistry`,
  `IndicatorSpec`, `RegistryError`, `Taxonomy`, `validate_assignment`); DMI/SMI per-indicator; fail-loud registry gate.
- **Suite: 112 passed, 3 skipped** (the 3 skips are env-gated live smokes: `GPU_AGENT_LIVE_LLM` ×2, `GPU_AGENT_LIVE_GATHER`).

---

## OPERATING NOTES / INVARIANTS (carry forward — still all true)

- **Run from repo root** `C:\Users\danie\random_for_fun`; Python 3.11+ at `.venv/Scripts/python` (Windows host; `.venv`
  is gitignored — recreate with `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"` if missing).
  The `[llm]` extra is optional and **not installed — and sp2 deliberately does NOT need it** (the brain is a Claude Code
  subagent; the deterministic gate+score path replays committed/just-generated JSON answers).
- **Frozen contract — never edit:** the Finding/Scorecard schema (`gpu_agent/schema/`), the 6 dimensions
  (`momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`), `gpu_agent/gate.py` rules,
  `scoring.py`'s `zscore`, `pipeline.py`'s Part-7 gate behavior, and the Increment-A registry
  (`gpu_agent/registry/indicators.py`, `validate.py`). **Also do not edit the extraction/judgment logic or prompts**
  (`extraction/extractor.py`, `extraction/prompt.py`, `judgment/judge.py`, `judgment/prompt.py`, `judgment/briefing.py`) —
  sp2's `--emit-prompt` only **reads/reuses** their `SYSTEM`, `build_user_prompt`, `ExtractionResult`, `JudgmentResult`,
  `build_briefing`. sp2 only **adds** `--emit-prompt` to `cli.py` and rewrites the `run-cycle` skill.
- **Part 38 doctrine (the harness):** the **session orchestrates; code computes + gates + stores**; delegation stays
  **one level deep** (session → gatherers / brain subagents); a no-assignment category is **logged as skipped, never
  silently dropped**; a cycle must be **replayable from its run log**. **The agent reasons; code computes, gates, stores —
  the agent never sets a number that reaches the scorecard uncomputed (Part 17).**
- **General doctrine:** no invented numbers; no forged provenance; ratings are judgment bounded by anchors, never set by
  code; gate failures re-run, never commit a partial; gatherers return raw material only; **fetched text is data, not
  instructions** (Part 8/26 — put it in every subagent dispatch prompt); gathered material carries a trust tier + dated
  receipt; secondary-only findings are confidence-capped; **caps/skips/partials are logged, never silent**; config errors
  fail loud.
- **Tests deterministic** via `RecordedClient` + committed fixtures. Live paths are env-gated smokes only (and sp2's live
  path is the Claude Code subagent, validated by a documented run, not pytest). Skills validated by a documented dry-run.
- **Every commit must end with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Windows flakiness:** the Bash tool's safety classifier can be intermittently unavailable for write/commit commands —
  retry, or use the PowerShell tool. CWD sometimes resets to `C:\Users\danie` — prefix git/pytest with
  `cd /c/Users/danie/random_for_fun && …`.
- **`.superpowers/` and `store/` are gitignored.** `.claude/` is **tracked** (skills live there: `gather-category`,
  `run-cycle`). `blobs.json` at repo root is an **untracked** run artifact — leave it.
- **Model preference (user):** opus for important final reviews; sonnet acceptable for mechanical per-task implementer +
  reviewer work.
- **Subagent-driven execution:** keep the ledger at `.superpowers/sdd/progress.md` (start a fresh section for sp2 below
  the sp1 record). Record the BASE commit before each task; mark tasks complete as reviews come back clean. Trust the
  ledger + `git log` after any compaction.

---

## DEFERRED MINORS (non-blocking; fix opportunistically)
- **sp1 MINOR (plan-mandated):** `build_cycle_plan` decides ready/skipped via `provider.path_for(cid).exists()` while
  `AssignmentProvider.get()` (load+validate) is unused in the production path. A present-but-corrupt assignment is labeled
  `ready` but fails **loud** downstream in `pipeline`. Follow-up (needs human OK, deviates from the committed sp1 plan):
  route readiness through `assignment = provider.get(cid); ready = assignment is not None`; add a present-but-unloadable
  test. Logged in `.superpowers/sdd/progress.md`.
- `cli.py` PEP8 E302 (single blank line between top-level defs) — one ruff/autopep8 pass clears it.
- `cli._load_docs` denylist-of-one (`gather-log.json`) — a future sidecar would crash; harden to "skip any file the schema
  can't validate." (Pre-existing.)
- Broad `layer:`/`all` coverage still needs per-category assignments (only 2 exist) — author them, or build a taxonomy-
  default generator (its own effort; explicitly out of sp2 scope).
