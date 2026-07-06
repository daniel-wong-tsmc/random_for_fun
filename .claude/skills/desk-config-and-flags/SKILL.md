---
name: desk-config-and-flags
description: Use when adding, changing, or looking up any configuration axis of this repo — CLI verbs/flags (--as-of, --backend, --recorded/--emit-prompt, --captured-at, --primary-sources, eval rebaseline --runs/--verdict), bypass flags (--no-sufficiency, --no-voice-lint), env vars (GPU_AGENT_*, ANTHROPIC_API_KEY), registry knobs (indicators/corroboration/acronyms/web-reach-tools JSON), pyproject extras, the .gitignore store whitelist, manifest/assignment fields — or when a flag "doesn't exist", a new category's store/ writes silently vanish, or a config edit turns tests/test_evals_baseline_pin.py red.
---

# Desk Config and Flags

## Overview

Every configuration axis of the GPU Category Agent lives in one of seven places: CLI flags, bypass flags, environment variables, registry JSON data, pyproject extras, the `.gitignore` store whitelist, and manifests/assignments. Code computes and gates; config data steers — and the single most important property of any config change is its **blast radius**: anything that alters emitted prompt bytes flips the F6 eval hash pin (`tests/test_evals_baseline_pin.py` goes red), and that red test is the system working, never something to "fix".

Jargon used below, defined once:
- **Verb** — an argparse subcommand of `gpu_agent.cli` (e.g. `extract`, `judge`, `eval`).
- **Seam** — one of the three LLM-facing steps (extract / judge / thesis); each has `--emit-prompt` (print the canonical prompt, no LLM call) and `--recorded` (replay a saved answer through deterministic gates).
- **F-item** — a numbered entry in `docs/fix-backlog.md` (the repo's defect ledger).
- **Eval hash pin** — SHA-256 hashes of the emitted prompt bundles stored in `fixtures/evals/baseline.json`, enforced by `tests/test_evals_baseline_pin.py`.
- **Frozen surface** — the full list per `docs/roadmap.md`'s "Standing constraints" (and matching `desk-change-control`'s FROZEN-CORE row): `gate.py`, `scoring.py`, `schema/*` (Finding schema, six dimensions, rating scale), `judgment/briefing.py`, `judge.py` aggregation, `pipeline.py`, `JsonStore`; changed only via Part-33 migrations (see desk-change-control). Do not shorten this list when citing it — a shortened copy is how this exact list has drifted between skills before.

## When to use

- You need the exact flags of a CLI verb, or a flag you expected "doesn't exist".
- You are adding a flag, env var, registry field, category, or any other config axis.
- A config-adjacent edit turned the suite red (usually the eval hash pin).
- You are deciding whether a knob is production, experimental, or forbidden.
- Store writes for a category silently don't show up in `git status`.

## When NOT to use

| Instead use | For |
|---|---|
| **desk-run-and-operate** | Running a cycle; the emit → dispatch → recorded choreography; artifact landing map |
| **desk-change-control** | Whether a change is allowed at all; Part-33 migrations; eval-gate governance; wave/lane process |
| **market-state-reference** | What registry values MEAN (dimensions, anchors, corroboration doctrine, indicator semantics) |
| **desk-build-and-env** | Recreating the environment, venv, Windows traps, web-reach bootstrap internals |
| **gate-integrity-campaign** | Executing the F74/F71/F75/F72 fixes |
| **desk-debugging-playbook** | Diagnosing a failing run (rejection strings, exit codes) |

## The seven config axes — map

| # | Axis | Where | Mutability |
|---|---|---|---|
| 1 | CLI verbs + flags | `gpu_agent/cli.py` `main()` (lines ~933–1099) | Code change; additive-only defaults |
| 2 | Bypass flags | `--no-sufficiency`, `--no-voice-lint` on `judge`/`pipeline` | FORBIDDEN without logged reason (F75) |
| 3 | Env vars | `gpu_agent/config.py` (+ test files) | Per-process; read-once traps |
| 4 | Registry data | `registry/*.json` | DATA — editable, but label/id edits flip the eval pin |
| 5 | Packaging extras | `pyproject.toml` | `[dev]` required; `[llm]` never installed live |
| 6 | `.gitignore` store whitelist | `.gitignore` lines 7–15 | De-facto config: defines what run history is canonical |
| 7 | Manifests + assignments | `manifests/*.json`, `fixtures/asg.*.json` | DATA with schema traps |

---

## Axis 1 — CLI verbs and flags

16 verbs (verified live 2026-07-05 via `--help`): `run, score, extract, ingest, wiki-ingest, wiki-dedup, wiki-lint, wiki-lifecycle, corpus, judge, thesis, eval, pipeline, cycle-plan, report, web-reach-ensure`.

Full verb-by-verb flag tables with defaults and hazards: **references/cli-verbs.md**. The load-bearing facts:

### `--as-of` shape validation (F56) — and its two gaps

`cli.py:56–60` defines `_AS_OF_RE = ^\d{4}-\d{2}(-\d{2})?$` (accepts `YYYY-MM` month grain or `YYYY-MM-DD` day grain, nothing else). It is wired as `type=_as_of` on: `extract`, `ingest`, `wiki-ingest`, `wiki-dedup`, `wiki-lint`, `wiki-lifecycle`, `thesis`, `pipeline`.

**Open gap:** two verbs take `--as-of` WITHOUT the validator:
- `corpus --as-of` (`cli.py:1026` as of the F74-merged tree, 2026-07-06 — re-grep before citing, `grep -n '"--as-of"' gpu_agent/cli.py`; line numbers shift with every cli.py edit) — a malformed vintage passes the CLI seam here.
- `eval --as-of` (`cli.py:1071`, used for record-grade provenance) — same.

Do not "just fix" these: adding the validator is a behavior change to a verb the live cycle scripts against — file/route it through desk-change-control. Grain semantics: month grain = monthly flagship, day grain = daily sweep; the grain is embedded verbatim in doc/finding ids (F52), which is why the shape check exists at all.

### `cycle-plan --out` — the F74 clobber hazard (CLOSED 2026-07-05, guard now live)

**F74 is CLOSED — merged `257cf1b` on 2026-07-05** (backlog ticked same day, `1a9eb33`; the fix branch/worktree `.worktrees/f74-cycle-log` is deleted, not retained). History: `cycle-plan --out store/cycle-log.json` used to do a plain `write_text` (`cli.py:811–812` on the pre-fix tree) that **overwrote** whatever was there — including a session-enriched run journal that hadn't been committed. On 2026-07-05 that erased the 2026-07-v3 journal including the only record of the F71 sufficiency bypass (recovered from commit `99ca522`); that same-day merge closed it.

**Current behavior:** `cycle-plan --out` now refuses to overwrite anything richer than a bare, regenerable plan skeleton — see `_is_bare_plan`/`_cycle_plan` in `gpu_agent/cli.py` (currently ~lines 813–848; re-grep by name, not line number, since it drifts). The refusal fails loud, naming F74 in its own error text.

**Defense-in-depth (still worth doing, even with the guard live):** before running `cycle-plan --out store/cycle-log.json`, run `git status --short store/cycle-log.json` and `git diff store/cycle-log.json` anyway. The guard is pytest/write-time only — a store commit made without a suite run, or a stale staged blob, can still slip through (a documented residual, out of F74's closed scope). Never blanket `git add store/` without diffing the cycle log.

### `--backend` — default is a deliberate dead end

Default `claude_code` on `extract`/`judge`/`pipeline`. Its `complete_json` **always raises** `LLMError` pointing you to `--emit-prompt` + dispatched subagent + `--recorded`. That error is doctrine (charter Part 38), not a bug — never "fix" it by switching backends.

`--backend anthropic_api` exists in code (`gpu_agent/llm/anthropic_api.py`: anthropic SDK, `ANTHROPIC_API_KEY`, max_tokens 16000). It is a **dormant, doctrine-forbidden alternate** for the live path. "No API/SDK path" is true of the LIVE path only — do not claim the code path doesn't exist, and do not use it on live runs.

### `--primary-sources` (ingest) — fallback vs manifest

CLI default is `sec.gov` — a filings-only **fallback**. The gather flow supplies the real per-category set from the manifest JSON's top-level `primaryDomains` (comma-joined). Two traps:
- `primaryDomains` exists only in the **raw manifest JSON** — the typed `CoverageManifest` model has no such field (`gpu_agent/manifest.py:58–64`), so `load_manifest()` output silently drops it. Read it from the raw JSON.
- `manifests/models.frontier-closed.json` has **no `primaryDomains` key at all** (verified 2026-07-05) — a frontier-closed ingest would tier everything against the `sec.gov` fallback unless the operator supplies domains. Flag this before that category's first live run.

### `--captured-at` — one value per category run

Default is now-UTC at each invocation. The live cycle must pin ONE identical value across `extract --recorded` and `pipeline` for a category (F62: the corpus merge runs in both places; differing values desync the emitted prompt's anchors from the gate's). Choreography details: desk-run-and-operate.

### `eval` verbs — the v2 grammar

`eval <action>` with action ∈ `{emit-brain, record-brain, emit-grade, record-grade, verdict, rebaseline}`.
- `verdict --runs <d1> [<d2>]` — 1 or 2 run dirs; writes `verdict.json` into the LAST run dir; requires a schema-v2 baseline.
- `rebaseline --runs <d1> <d2> <d3> --verdict <run>/verdict.json` — **exactly 3** replicate run dirs enforced in `gpu_agent/evals/harness.py:276–277`; `--verdict` is the governance proof of a PASS.
- **The old v1 `rebaseline --out` form is GONE** — the CLI error message itself says "the v1 --out form is gone". Any doc showing it is stale.
- `--force` + `--reason` — user-only escape hatch; the reason is stored permanently in the baseline. Never use without explicit user instruction.
- Procedure and verdict ladder: the repo `run-eval` skill + desk-validation-and-qa.

### `--persona` / `personaLabel` — additive prompt swap

`--persona` on `extract`/`judge`/`thesis` (default None = byte-identical legacy "GPU market" prompt); `pipeline` reads it from the assignment's `personaLabel` (F26). `fixtures/asg.models.frontier-closed.json` carries `personaLabel: "frontier AI model market"`; the chips assignment has none. Any persona default change alters prompt bytes → eval pin flips.

### Production vs experimental vs forbidden

| Class | Members |
|---|---|
| **Production** (documented live path) | `--emit-prompt`/`--recorded`(`-extract`/`-judge`), `--corpus-store` + `--corpus-report`, `--captured-at`, `--as-of`, `--samples` (3), `--dedup-store` (daily), `--daily`, `--render-ts`, `--prior`/`--no-prior`, `--primary-sources` (from manifest), eval `emit-*`/`record-*`/`verdict`/`rebaseline` |
| **Legacy/fixture** (works, not the live path) | `run`, `score` (fixture-driven MVP verbs), `--seed` (thesis first-run), `--no-prior` on old renders |
| **Governance-restricted** | eval `--force --reason` (user-only), `rebaseline` at all (only after a minted PASS verdict) |
| **Forbidden on live runs** | `--backend anthropic_api` (doctrine); `--no-sufficiency`/`--no-voice-lint` without the one-rewrite-first + logged-bypass protocol (Axis 2) |

---

## Axis 2 — Bypass flags (red box)

> **`--no-sufficiency` and `--no-voice-lint` are WHOLE-RUN gate bypasses.** They exist on `judge` (`cli.py:1043,1045` as of the F74-merged tree, 2026-07-06) and `pipeline` (`cli.py:1091,1093`), nominally for "legacy recorded fixtures". Re-grep before citing (`grep -n "no-sufficiency\|no-voice-lint" gpu_agent/cli.py`) — every cli.py line citation in this file shifted by ~35 lines after the F74 merge added its overwrite-refusal guard, and will shift again on the next merge. F75 (OPEN as of 2026-07-06) targets their removal from live paths: "before ANY unattended loop, every whole-run bypass becomes per-item + required reason + logged, or is removed."

Facts you must carry:
- **One live use exists**: the 2026-07-v3 flagship ran under `--no-sufficiency` after the F71 anchor-vs-sufficiency deadlock (moat Weak→Mixed forced by a +0.50 anchor; evidence was 2 secondary publishers < 3). The log record survives at `git show 99ca522:store/cycle-log.json` (line 41). The 2026-07-05 daily cycle passed both gates with NO bypass (commit `d9cfb3f`).
- **The sanctioned protocol** (run-cycle SKILL.md, "neither check ever blocks a scorecard"): on `voice-lint:`/`sufficiency:` stderr lines, re-dispatch ONLY the violating sample(s) once; on a second failure, rerun with the matching bypass flag and log `voice-lint: bypassed` / `sufficiency: bypassed` (with the reason) in the cycle log. Using a bypass without that logged record is a doctrine violation and lands squarely in the F75 problem space.
- Legacy `fixtures/recorded/*` predating F67/F63 genuinely need these flags for replay — that is their only unremarkable use.
- **Never add a new `--no-<gate>` flag.** F75 forbids the pattern. If a gate needs an escape, design per-item + reason + logged, and route through desk-change-control / gate-integrity-campaign.

---

## Axis 3 — Environment variables

Only three env vars exist in package code (verified by grep over `gpu_agent/` 2026-07-05); the rest are test-only gates.

| Var | Default | Read semantics | Purpose |
|---|---|---|---|
| `GPU_AGENT_REGISTRY` | `registry/indicators.json` | Once, at import of `gpu_agent/config.py` | Indicator registry path (F42) |
| `GPU_AGENT_TAXONOMY` | `docs/taxonomy.json` | Once, at import | Taxonomy path |
| `GPU_AGENT_CORROBORATION` | `registry/corroboration.json` | Path at import; value `lru_cache(maxsize=1)` per process; missing file → fallback 3 | Corroboration bar (F63) |
| `GPU_AGENT_LIVE_LLM=1` | unset | pytest skipif | Unskips live LLM smokes (`tests/test_extraction_integration.py:32`, `test_pipeline_integration.py:27`). Default-off; NOT a production gate |
| `GPU_AGENT_LLM_BACKEND` | `claude_code` | test-only | Backend for those live smokes |
| `GPU_AGENT_LIVE_GATHER=1` / `GPU_AGENT_GATHER_BLOBS` | unset | pytest skipif / path | Unskip/point live gather smoke (`tests/test_gather_integration.py:67–74`) |
| `ANTHROPIC_API_KEY` | unset | anthropic SDK, lazily | ONLY consumed by the doctrine-forbidden `anthropic_api` backend. Its absence on this machine is correct |

Traps (all verified in source):
- `min_distinct_publishers()` is lru_cached — changing the env var or the JSON mid-process has no effect. Restart the process.
- `gpu_agent/reader.py` reads `registry/acronyms.json` and `registry/indicators.json` via **relative `Path` literals** (`reader.py:41,56`) — it ignores `GPU_AGENT_REGISTRY` entirely and only works with CWD = repo root.
- `gpu_agent/web_reach_ensure.py:13` resolves `registry/web-reach-tools.json` relative to CWD — invoke via `scripts\web-reach-ensure.cmd` / `sh scripts/web-reach-ensure`, which cd to repo root.
- Report output emits non-ASCII glyphs; the CLI reconfigures stdout to UTF-8 (`cli.py` report handler). Subprocess callers capturing output should set `PYTHONIOENCODING=utf-8`.

---

## Axis 4 — Registry knobs (config-as-data)

### `registry/indicators.json` (counts as of 2026-07-05)

Top-level keys: `version, indicators, overrides, sourceInventory, cadenceHorizon, dimensionTracks`. 17 indicators; 10 scoring (`D2, S9, S10, apiArr, grossMargin, leadTimes, market-share-pct, releaseCadence, rpoBacklog, vendorRevenueGuidance`); scoring weights sum **1.02** (nothing normalizes — do not assume a partition); 2 price-side (`D6`, `gpuSpotPrice`), 3 structural (`exportControlExposure`, `customerConcentration`, `designWins`); 3 leading-horizon (`rpoBacklog`, `vendorRevenueGuidance`, `designWins`).

Per-indicator fields (`IndicatorSpec`, `gpu_agent/registry/indicators.py:11–25`): `id, label, dimension, polarityTrack, side, weight, unit, kind, comparability, scoring, readsLevelOrSlope, decayLambda, leadMonths` — **`model_config = extra="forbid"`**.

**The additive-metadata rule (load-bearing):** the frozen `IndicatorRegistry.load` ignores top-level `cadenceHorizon` and `dimensionTracks`; they have their own fail-loud accessors (`IndicatorHorizons` raises `HorizonError`, `DimensionTracks` raises `TracksError`, each with coverage validation). **New registry metadata goes TOP-LEVEL with its own accessor — never as a new field inside an indicator entry**, which `extra="forbid"` would reject loudly for every caller of the frozen loader.

Other knobs here: `overrides` (per-category partial spec merge — currently `chips.hbm-memory: market-share-pct weight 0.04`) and `sourceInventory` (paywalled/licensed sources inventoried, never fetched — semantics owned by market-state-reference).

**Blast radius warning:** indicator `label`/`id` strings are baked into emitted prompt vocabularies (F55/F53) — editing them flips the eval hash pin. `weight` edits don't touch prompts but change DMI/SMI outputs; weights are hand-set user decisions — escalate, don't tune.

### `registry/corroboration.json`

`{"minDistinctPublishers": 3}` — one tunable feeding gate F2e, the F63 sufficiency gate, and thesis rule 6. The SYSTEM prompts **hardcode the same "3"**; `tests/test_corroboration_config.py` guards the coupling — changing the value forces prompt-text changes, which flip the eval pin, which requires the run-eval flow. This is a user-level decision; never a casual edit.

### `registry/acronyms.json`

`{"allowed": [...]}` — 100 entries as of 2026-07-05. Bounds all-caps tokens in exec-facing prose (F67 voice lint). Extending it is the SANCTIONED fix when the lint rejects a legitimate acronym (precedents: CEO post-F63; CFO/CUDA/ZLUDA/SDNY re-dispatched on 2026-07-05) — extend the DATA list, never weaken `reader.py`.

### `registry/web-reach-tools.json`

Per-tool: `enabled` (bool gate), `role` (`fetch` = gatherers may use it, e.g. agent-reach; `discovery` = coordinator-only leads, output NEVER ingested, e.g. last30days), per-OS `healthCmd`/`install`, `defaultTier: secondary`. Health truth on Windows is `agent-reach --version` (the `doctor` verb exits 120 — known trap). A **new role value** requires a one-time doctrine update to gather-category + charter Part 37 — route through desk-change-control.

---

## Axis 5 — pyproject extras

```
dependencies = ["pydantic>=2,<3"]        # the ONLY runtime dep
dev = ["pytest>=8"]                       # required for the operational path
llm = ["anthropic>=0.40", "claude-agent-sdk>=0.1"]   # NEVER installed on the live path
```

Install: `pip install -e ".[dev]"`. The `[llm]` extra exists solely for the dormant `anthropic_api` backend; the run-gpu-market launcher states it is "NOT needed". Installing it is not itself a violation — using it live is.

---

## Axis 6 — the `.gitignore` store whitelist (de-facto config)

`.gitignore` lines 7–15 define what run history is canonical:

```
store/*
!store/chips.merchant-gpu/
!store/cycle-log.json
!store/wiki/
!store/findings/
!store/seen_docs.jsonl
!store/theses/
```

- The carve-outs are **category-hardcoded**. There is NO `!store/models.frontier-closed/` line (verified 2026-07-05), and **no test guards this**. Running category #2 without first amending `.gitignore` writes scorecards into an ignored directory — silently violating "a cycle that isn't committed didn't happen". **Adding any category REQUIRES a new `!store/<categoryId>/` negation line first.**
- Also ignored: `work/`, `.superpowers/`, `.worktrees/`, `.venv/`, and **`blobs.json` by bare name anywhere in the tree** — a path like `store/x/blobs.json` will never commit.
- Eight legacy ignored scratch subtrees live under `store/` (`live`, `live_run`, `live_sc`, `_docs`, `_demo`, `_demo_docs`, `_dryrun_docs`, `_brain`) — never read state from them.

---

## Axis 7 — manifests and assignments

### `manifests/<categoryId>.json` (CoverageManifest)

Typed fields (`gpu_agent/manifest.py`): `version, categoryId, asOf, description, expectedIndicators[{indicatorId, dimension, priority, sourceIds}], expectedSources[{id, label, urlPatterns, mirrorPatterns, accessMethod free-web|filing|licensed-api|mcp|manual, tier, costUsd, license, refresh, indicators, paywalledNote}]`. `is_paywalled = costUsd > 0 or accessMethod == "licensed-api"` → logged as a coverage gap immediately, NEVER fetched (paywall doctrine: market-state-reference).

Raw-JSON-only field: **`primaryDomains`** (see Axis 1, `--primary-sources`). As of 2026-07-05: chips manifest has 8 primaryDomains, 13 expectedIndicators, 14 expectedSources (2 paywalled); frontier-closed manifest has 6 expectedSources (1 paywalled: theinformation) and **no primaryDomains**.

### `fixtures/asg.<categoryId>.json` (Assignment)

Keys observed: `id, category, template, mode, entities, metrics, weights, manifestRef, version, asOf` (+ optional `personaLabel`). `weights` is a per-run override dict passed into scoring as `weight_overrides` — but it only affects indicators that pass the scoring filter (`spec.scoring` true and `spec.side` not price/structural, `gpu_agent/scoring.py`). The chips assignment's `D6: 0.12` entry is therefore **inert** for indices (D6 is price-side, scoring:false) — a historical leftover, not evidence that price scores.

Assignments are discovered by `cycle-plan` as `<assignments-root>/asg.<categoryId>.json` (default root `fixtures`); a category without one reports `skipped-no-assignment`, never fails silently. Two exist today: `chips.merchant-gpu`, `models.frontier-closed` (the latter is runnable-per-pins, never yet run live).

---

## HOW TO ADD A CONFIG AXIS — checklist

Work top to bottom; stop and escalate at any ✋.

1. **Classify it.** Run-shaping CLI flag → Axis 1. Deterministic data → Axis 4/7. Env override → Axis 3. Packaging → Axis 5. New category → Axis 6 + 7 both.
2. ✋ **Gate check:** does it touch `gate.py`, `scoring.py`, `schema/*` (Finding schema, six dimensions, rating scale), `judgment/briefing.py`, `judge.py` aggregation, `pipeline.py`, or `JsonStore` (the full frozen-surface list, `docs/roadmap.md` "Standing constraints") → STOP: Part-33 migration via desk-change-control. Does it add a gate bypass? → STOP: F75 forbids new whole-run bypasses.
3. **Design additive.** New CLI flags default to byte-identical legacy behavior (None/False default — precedents: `--persona` F26, `include_groups` F55). New registry metadata goes top-level with a fail-loud accessor (precedent: `cadenceHorizon`/`dimensionTracks`) — never into `IndicatorSpec`. New env vars centralize in `gpu_agent/config.py` (F42 precedent) and document their read-once semantics.
4. **Prompt-byte impact check (the big one).** Ask: can this change any byte of an emitted prompt bundle — flag defaults, vocab content or ordering, registry labels/ids, taxonomy labels, whitespace? Then verify, don't guess:
   ```powershell
   .venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q
   ```
   Red = you changed prompt bytes = the change now requires the full run-eval qualification + governed `rebaseline` (desk-change-control owns the gate; the repo `run-eval` skill executes it). Never hand-edit `fixtures/evals/baseline.json` — maintainer-confirmed law.
5. **Test expectations.** Add a test for the new axis's default AND its set behavior. If it is a coupling (like `minDistinctPublishers` ↔ prompt text), add a coupling guard test (`tests/test_corroboration_config.py` is the template). If it is a `.gitignore` carve-out, note that today NOTHING tests the whitelist — adding the first guard test is welcome (route via desk-change-control).
6. **New category specifically:** (a) `.gitignore` negation line; (b) `fixtures/asg.<id>.json`; (c) `manifests/<id>.json` WITH `primaryDomains`; (d) registry `overrides` if weights differ; (e) confirm `cycle-plan --scope category:<id>` reports `ready`.
7. **Docs.** Update the operator skill that surfaces the axis (`run-cycle` / `gather-category` / `run-eval`), the F-item if this closes one, and HANDOFF (templates: desk-docs-and-writing).
8. **Full suite green** before merge: `.venv/Scripts/python -m pytest` (expect 3–4 env-gated skips).

---

## Common mistakes

| Mistake | Reality |
|---|---|
| "Fixing" the `claude_code` backend's raise, or switching to `anthropic_api` | The raise is doctrine (Part 38). Live = emit-prompt → tool-less subagent → --recorded, only |
| Hand-editing `fixtures/evals/baseline.json` after the pin goes red | Maintainer-confirmed forbidden. Run-eval + `rebaseline --runs x3 --verdict` is the only unlock |
| Using `--no-sufficiency`/`--no-voice-lint` as a convenience flag | One rewrite attempt first, then bypass WITH a logged reason in the cycle log — anything else is an F75-class violation |
| Running `cycle-plan --out store/cycle-log.json` over an uncommitted enriched journal | F74 (closed 2026-07-05): the CLI now refuses this itself. Diffing the cycle log first is still good hygiene — the guard is pytest/write-time only |
| Adding a field to an indicator entry in `indicators.json` | `IndicatorSpec` is `extra="forbid"` — every load breaks. Top-level key + accessor instead |
| Editing a registry `label` "cosmetically" | Labels are in emitted prompt vocab → eval pin flips → full re-qualification |
| Trusting `load_manifest()` for `primaryDomains` | Not on the typed model; raw JSON only |
| Launching category #2 without a `.gitignore` negation | Scorecards land ignored; nothing warns; no test guards it |
| Setting `GPU_AGENT_CORROBORATION` mid-process to retune the bar | lru_cached; and the bar is hardcoded in prompts too (coupling test will catch the half-change) |
| Assuming assignment `weights` reweight anything they name | Only scoring, non-price/structural indicators are affected; the chips `D6` override is inert |
| Expecting `eval rebaseline --out` to work | v1 form removed; `--runs <d1> <d2> <d3> --verdict ...` with exactly 3 dirs |
| Validating `--as-of` everywhere by assumption | `corpus` and `eval` lack the regex — open gap, don't rely on the seam there |

## Provenance and maintenance

Authored 2026-07-05 for the desk skill library (library baseline main @ `a8ec757`; every fact above re-verified against main @ `639c00d`, same day — 4 commits later, which committed CLAUDE.md/session-orient, the 2026-07-05 daily run, and claimed the F74 lane). Volatile facts and their re-verification one-liners (PowerShell 5.1, repo root):

| Fact class | Re-verify with |
|---|---|
| Verb list (16) | `.venv/Scripts/python -m gpu_agent.cli --help` |
| Any verb's flags | `.venv/Scripts/python -m gpu_agent.cli <verb> --help` |
| `--as-of` validation + gaps | `Select-String -Path gpu_agent/cli.py -Pattern '_AS_OF_RE|type=_as_of|"--as-of"'` |
| Bypass flags still present (F75 open) | `Select-String -Path gpu_agent/cli.py -Pattern 'no-sufficiency|no-voice-lint'` |
| F74/F75 status | `Select-String -Path docs/fix-backlog.md -Pattern '\[.\] \*\*F7[45]'` and `git log --oneline --grep=F74` |
| Env vars in package | `Get-ChildItem gpu_agent -Recurse -Filter *.py | Select-String -Pattern 'GPU_AGENT_'` |
| Indicator counts / top-level keys | `.venv/Scripts/python -c "import json; r = json.load(open('registry/indicators.json', encoding='utf-8')); print(list(r), len(r['indicators']), sum(1 for v in r['indicators'].values() if v['scoring']))"` |
| Corroboration bar | `Get-Content registry/corroboration.json` |
| Acronym count | `.venv/Scripts/python -c "import json; print(len(json.load(open('registry/acronyms.json', encoding='utf-8'))['allowed']))"` |
| Store whitelist | `Get-Content .gitignore` |
| Manifest primaryDomains presence | `.venv/Scripts/python -c "import json; [print(p, 'primaryDomains' in json.load(open('manifests/'+p, encoding='utf-8'))) for p in ('chips.merchant-gpu.json','models.frontier-closed.json')]"` |
| Extras | `Get-Content pyproject.toml` |
| Eval pin green/red | `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q` |
| Baseline schema/epsilon | `.venv/Scripts/python -c "import json; b = json.load(open('fixtures/evals/baseline.json', encoding='utf-8')); print(b['schemaVersion'], b['epsilon'])"` |
| Historic bypass record | `git show 99ca522:store/cycle-log.json | Select-String bypassed` |

Nothing in this skill authorizes a change to anything gated — classification and approval always route through desk-change-control.
