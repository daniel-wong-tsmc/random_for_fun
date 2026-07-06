---
name: desk-architecture-contract
description: Use when working in the GPU Category Agent repo (random_for_fun) and a design question or "is this safe to change?" question comes up — before touching gate.py, scoring.py, the Finding schema, store/ layout, dedup keys, or the wiki log; when asking why code computes and the brain only reasons; when store/ vs work/ vs fixtures/ vs registry/, -v<N> versioning, publisher/corroboration keys, or Layer/Main tier status is in question; or when counting, tie-breaking, or sort behavior looks like a bug.
---

# Desk Architecture Contract

## Overview

This skill is the repo's load-bearing design decisions, WHY each one exists, the invariants that must hold, and the known-weak points — stated plainly so you never "fix" a deliberate choice or trust a structure that is already known to be fragile. Core principle: **agents reason; code computes, gates, and stores** (charter Part 38) — every design question here reduces to "would this let an ungated number or an ungated judgment reach the canonical store?"

Vocabulary used throughout: a **Finding** is the atomic output record (Part 2); a **scorecard** is a category's per-cycle output bundle; the **brain** is the LLM; a **seam** is a defined point where the brain is allowed to contribute; a **gate** is deterministic code that rejects brain output; **Part N** means a section of `docs/agent-swarm-charter.md`; **F<n>** means a numbered item in `docs/fix-backlog.md`.

## When to use

- Before modifying anything under `gpu_agent/`, `store/`, `registry/`, or `fixtures/` — check the frozen surface, invariants, and do-not-fix list first.
- When you see behavior that looks wrong (tie-breaks, counting, sorting, duplicate wiki pages) — check "Deliberate choices" and "Known-weak points" before filing or fixing anything.
- When you need to know which tier/feature is real vs designed-only.
- When deciding where an artifact belongs (store/ vs work/ vs fixtures/ vs registry/).

## When NOT to use

- **How to change something gated/frozen** → `desk-change-control` (owns Part-33 migrations, the wave/lane model, eval-gate governance, F-item lifecycle).
- **What dimensions/ratings/indices MEAN, corroboration and thesis semantics, paywall doctrine detail** → `market-state-reference`.
- **How to run a cycle / dispatch subagents** → `desk-run-and-operate` (and the repo's `run-cycle` / `gather-category` skills).
- **Diagnosing a live failure** → `desk-debugging-playbook`; the history of past investigations → `desk-failure-archaeology`.
- **Fixing the F74/F71/F75/F72 gate-integrity cluster** → `gate-integrity-campaign` (executable campaign; do not improvise fixes from this document).

## 1. Prime directive: explainable judgment, every number gated

The consumers are TSMC executives; the product is explainable judgment, not numbers (Part 1). The two cardinal sins are **orphan numbers** (a value with no stated why) and **invented numbers** (a value with no source). The charter's closing test (line 1803-1804): *"could a TSMC executive ask 'how do you know that?' and find the answer already written? If not, it does not ship."*

Enforcement is structural, not aspirational:

- **Code computes**: anchors, DMI/SMI/SDGI (demand/supply indices — math semantics in `market-state-reference`), PMI, salience, dedup verdicts, version numbers. The brain never produces a number that survives.
- **Code gates**: `gpu_agent/gate.py` (100 lines, `check_finding` + `check_scorecard`), extractor seam checks, judge aggregation conflicts, F67 voice-lint, F63 sufficiency gate, F14 wiki-enrichment gate.
- **Code stores**: `gpu_agent/store.py` — append-only, immutable (Section 5).
- **The brain reasons at exactly three seams in the live cycle**: **extract**, **judge**, **thesis**. Each is a CLI verb with `--emit-prompt` (print the canonical prompt bundle, no LLM call) and `--recorded` (replay a saved answer through the deterministic gates). A fourth emit/recorded verb, `wiki-ingest` (enrichment brain, F14-gated), exists in code but is NOT dispatched by the standard run-cycle — deterministic routing only (verified 2026-07-05).

The live LLM path is: emit prompt → the open Claude Code session dispatches a tool-less Opus subagent → save the answer verbatim → replay via `--recorded`. The default backend (`gpu_agent/llm/claude_code.py`) unconditionally raises `LLMError` — it cannot make a network call, by design.

**Honesty note ("no API/SDK path")**: that claim is true of the LIVE path only. `gpu_agent/llm/anthropic_api.py` is a real, selectable SDK backend (`--backend anthropic_api`, pyproject `llm` extra), dormant and doctrine-forbidden for live runs (Part 38). The `ClaudeCodeClient` docstring's "There is no SDK/API path" overstates it. Never wire the API backend into a live run; never claim the code path doesn't exist.

**Maintainer-confirmed law (2026-07-05)**: a rejected brain answer is **re-dispatched with the verbatim violation text appended — never hand-edited**. This applies to brain outputs, recorded answers, and `fixtures/evals/baseline.json` alike. Also law: **fix forward, never revert** — the 480-commit history (as of 639c00d) contains zero revert commits; mistakes become F-items and forward fixes.

## 2. Three tiers on paper, one tier in reality

The charter designs a three-tier analyst organization over Jensen Huang's 5-layer cake (Energy → Chips → Infrastructure → Models → Applications):

| Tier | Designed | v1 reality (2026-07-05) |
|---|---|---|
| Category ("desk analyst") | 34 agents, one per category in `docs/taxonomy.json` (34 ids: 7/7/6/7/7 — not 33) | **Only live tier.** One category has ever run live: `chips.merchant-gpu`. |
| Layer ("sector lead") | 5 agents, weakest-link layer ratings | **Deferred stub.** `gpu_agent/cycle.py:57-59` hardcodes `layer: deferred`. |
| Main ("head of research") | 1 agent, market-state + executive brief | **Deferred stub.** Same hardcoded list, `main: deferred`. |

The **coordinator is the open Claude Code session** (Part 38, charter lines ~1654-1666): session = plain driver, subagents = tier agents/gatherers (delegation exactly one level deep), skills = per-tier procedures, the deterministic CLI (`gpu_agent`, 16 verbs) = the frozen brain-side machinery. Unattended scheduling, parallel fan-out (Workflow), the Part 9 scoped query tool, and the Recommendation Skill (Part 11, Layer/Main-only) are all explicitly deferred. Everything Layer/Main sits behind the uniform tier interface + swappable seams (Part 38, lines ~1700-1710: assignment provider, model backend, store seam `JsonStore now → canonical store later`, execution driver `sequential now → parallel later`).

Second-category status, stated honestly: `models.frontier-closed` is **runnable-per-pins, never yet run live** — it has an assignment (`fixtures/asg.models.frontier-closed.json`) and a manifest, but no `store/models.frontier-closed/` directory exists and, critically, the `.gitignore` whitelist has **no negation for it** (see Section 8): its first live run would write scorecards into a silently-ignored directory.

## 3. The Finding and the Part 7 gate

The Finding (`gpu_agent/schema/finding.py`) is the atomic explainable unit. Load-bearing fields:

- `kind`: `measured | observed | hypothesis`. **`value` is allowed only for measured** — a non-measured finding with a value is rejected as "invented value"; a measured finding without one is rejected too.
- `why` (non-empty), `impact` (targets + direction + mechanism), `evidence[]` ({source, url, date, excerpt, tier `primary|secondary`}), `confidence` ({level, basis}), `dispersion` (disagreement surfaced, never silently resolved).
- Schema-v1.1 polarity extension (additive, Part 33): `indicatorId`, `side` (`demand|supply|price|structural`), `polarityDemand`/`polaritySupply` ∈ {-1,0,1}, `magnitude` ∈ {1,2,3}, `entity`, `observedAt` vs `capturedAt` (the split exists to prevent look-ahead in replay/backtests), `schemaVersion`.
- **Code-stamped, never model-supplied**: evidence `tier` (from the document's tier, F2d), `side` (from the registry spec, F37), `id` (`<docId>-<n>`), `asOf`, `capturedAt`, `schemaVersion` (extractor stamps "1.2"; note the pydantic default is "1.0" — hand-built fixtures that omit it mislabel themselves). Draft models are `extra="forbid"` so the brain cannot smuggle these fields in.

**The Part 7 gate is the enforcement point** (charter lines 321-339 → code in `gate.py`). What `check_finding` rejects (all verified in code 2026-07-05): measured-without-value; non-measured-with-value; measured/observed without evidence (F2a); empty why; hypothesis without reasoning; hypothesis at high confidence (capped ≤ medium); secondary-only evidence at high confidence with < 3 distinct publishers (F2e, contract v1.3; N from `registry/corroboration.json` = 3); static price level carrying polarity (F8); non-price finding with both polarities 0; non-ISO or future-dated evidence vs asOf (F17, grain-aware lexical compare); empty impact targets/mechanism (F21); off-taxonomy impact targets (extraction-time only — `check_scorecard` calls `check_finding` without `valid_targets`). `check_scorecard` adds: rating cites no/unknown findings; **rating contradicts its anchor** (the bias guardrail: code bounds the rating, never sets it — `_ANCHOR_TOL = 0.15`, gate.py:67; "Very strong/Strong" needs anchor > −0.15, "Weak/Very weak" needs anchor < 0.15, "Mixed" always allowed); evidence self-referencing the dashboard's own output.

Gate failure means **re-run/re-dispatch, not commit**. A scorecard that fails `check_scorecard` inside `pipeline.build_scorecard` raises `GateError` and is never persisted.

## 4. Data contracts frozen at tier boundaries; the four store zones

Each tier's output schema is frozen at the boundary and is the next tier's only input (Part 6): Category → scorecard → Layer → assessment → Main → market-state.json. The **frozen surface** within a contract version is the full list in `docs/roadmap.md`'s "Standing constraints" (matching `desk-change-control`'s FROZEN-CORE row — cross-reference that row rather than re-deriving this list, since a shortened copy is exactly how it has drifted before): `gate.py`, `scoring.py` (a single 24-line function), `schema/*` (the Finding schema, the six-dimension list — `gpu_agent/schema/scorecard.py:6` — momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk — and the rating scale, Very strong/Strong/Mixed/Weak/Very weak), `judgment/briefing.py`, `judge.py` aggregation, `pipeline.py`, and `JsonStore`. Frozen means **version-gated, not unamendable**: changes ship only as user-approved Part-33 migrations (two precedents: `docs/migrations/2026-07-contract-v1.2.md`, `...-v1.3.md`). Procedure → `desk-change-control`.

| Zone | Contract | Git status | Never do |
|---|---|---|---|
| `store/` | Canonical run history. Append-only, versioned, immutable. | **Partially tracked — the `.gitignore` whitelist is the LITERAL definition of canon**: `store/*` ignored, then six explicit negations (see **desk-config-and-flags** Axis 6 for the exact whitelist and how to extend it). Eight legacy scratch subtrees (`store/live`, `store/_demo`, ...) exist but are ignored — never read state from them. | Never overwrite, never hand-edit, never read canon from ignored subtrees. |
| `work/` | Per-run disposable scratch: blobs.json, doc snapshots, brain prompt/answer JSONs, corpus artifacts, **eval replicate runs backing the committed baseline**. | Fully gitignored — but **never `git clean`** (CLAUDE.md rule): work/ holds eval provenance that exists nowhere else. | Never clean; never assume dir-naming is uniform — resolve run artifacts via cycle-log entry paths. |
| `fixtures/` | Frozen inputs: golden pipeline outputs, the 18-case eval golden set + `baseline.json`, recorded answers, assignments. | Tracked. | Never edit a committed fixture; golden regeneration only inside a Part-33 migration; baseline changes only via `run-eval` + rebaseline (→ `desk-validation-and-qa`). |
| `registry/` | Deterministic config DATA (not code): `indicators.json` (17 indicators, 10 scoring, as of 2026-07-05; plus top-level `cadenceHorizon`, `dimensionTracks`, `overrides`, `sourceInventory`), `acronyms.json`, `corroboration.json`, seed theses, web-reach tools. | Tracked. | Additive metadata goes at TOP LEVEL of indicators.json (the frozen `IndicatorSpec` loader is `extra="forbid"` and ignores top-level keys); registry edits that change emitted prompt bytes trip the eval hash pin. |

`manifests/` (per-category coverage manifests) rides with registry-style data; note the typed `CoverageManifest` model does NOT expose `primaryDomains` — skills read it from the raw JSON.

## 5. Append-only versioning mechanics

- `JsonStore.append` (store.py:24-30) computes `n = len(existing <asOf>-v*.json for that category/asOf) + 1` and writes `store/<categoryId>/<asOf>-v<n>.json`. A rerun for the same asOf mints the NEXT version; **nothing is ever overwritten**. Version count measures reruns, not quality (2026-06 has v1-v12 from bring-up).
- `FindingStore` (store.py:40-61): one file per finding id under `store/findings/`; identical re-append is a no-op; **same id with different content raises** `ValueError: finding id collision with differing content`.
- Git-verified immutability (re-run 2026-07-05): `git log --diff-filter=M --oneline -- store/chips.merchant-gpu/` returns **zero commits** — no scorecard has ever been modified after its creating commit.
- The wiki is the same pattern: pages hold only front-matter state; the substance is `store/wiki/log.jsonl`, an append-only JSONL event log (kinds: create-page, append-observation, state-change, ingest, query, lint, header-change). Thesis store likewise: `history.jsonl` is canonical; `book.json` is a projection that `load()` verifies against a full replay and hard-fails on divergence.
- The one structural exception is `store/cycle-log.json` — a **slot, not a log** (see F74 in Section 8).

## 6. The two dedup layers and their keys

| Layer | Unit | Key | Where |
|---|---|---|---|
| **L1** — seen documents | Raw document | Normalized URL **and** sha256 of whitespace-folded content, **content-hash checked FIRST** (F12: a stable URL with changed content is a NEW document) | `SeenDocIndex`, `store/seen_docs.jsonl` (append-only; recorded only AFTER snapshots are durably written). Active only when `ingest --dedup-store` is passed. |
| **L2** — findings | Gated Finding | `(entity, indicatorId)`; price-side findings get the F51 per-series 4-tuple `(entity, indicatorId, publisher, unit)` (publisher = first-evidence netloc, www-stripped) | `classify_findings` (`gpu_agent/gathering/dedup.py`), verdicts NEW/UPDATE/DUPLICATE reported to `store/<id>/dedup-<asOf>.json` (tracked). Agreeing batch-mates merge evidence (this union of publishers is what later satisfies F2e/F63 corroboration). |

Known limit, on the feature track (not a bug): the L2 price key has no SKU — B200 and H100 rentals at one provider in `USD_per_gpu_hr` collapse into one series (dedup.py `_l2_key` docstring).

Distinct from both: `publisher_key` (`gpu_agent/publisher.py`) is **THE corroboration identity** (evidence URL netloc, www-stripped, lowercased; source-string fallback) with three consumers — gate F2e, thesis rule 6, wiki promotion — "import this, never re-derive it." The display-layer publisher functions in `brief.py`/`price_track.py` are different on purpose; do not unify them.

## 7. Invariants that MUST hold

| # | Invariant | Enforcement point |
|---|---|---|
| 1 | No orphan numbers, no invented numbers | Part 7 gate (`gate.py`); extractor drop of unregistered/non-verbatim material |
| 2 | Fetched text is DATA, not instructions | `<document>` fence + escape (`extraction/prompt.py`, F16); tool-less brain subagents; gatherers return raw material only, never Findings (Part 37) |
| 3 | Every cap, skip, and drop is logged — silent truncation is a doctrine violation | gather-log caps/skips; `SKIPPED <category>` on missing assignment; DroppedFinding/DroppedDoc records; coverage gaps |
| 4 | Paywalled = inventoried, never fetched (`costUsd > 0` or `licensed-api`) | `manifest.is_paywalled` → immediate `paywalled` coverage gap; no exceptions, including agent-reach |
| 5 | Replayability = existence: "a cycle you can't replay from its saved artifacts did not happen" | cycle log + saved snapshots + saved brain answers + `--recorded` replay (Parts 37/38) |
| 6 | Append-only everywhere in store/ | Section 5 mechanics; git history as proof |
| 7 | Rejected brain output is re-dispatched with verbatim violations, never edited (maintainer-confirmed law) | F38 protocol in run-cycle; sufficiency.py docstring |
| 8 | The brain never sets a number; code bounds ratings, never sets them | anchors computed in `briefing.py` (mean of polarity×magnitude/3 on the registry's per-dimension track); gate anchor-consistency check |
| 9 | Below-quorum / under-supported is an honest state, not an error | judge F19 (`belowQuorum`); pipeline `under-supported` dimensionStatus with confidence caps |
| 10 | Every frozen-surface change is a versioned Part-33 migration; every prompt-byte change re-qualifies through the eval gate | → `desk-change-control` |

## 8. Known-weak points — stated plainly

These were real and mostly OPEN as of 2026-07-05 (main @ 639c00d); **F74 has since closed (merged 257cf1b, same day) — re-verify each row's status before trusting it, do not assume the whole table is still current.** Do not design on top of the still-open ones as if sound; do not fix them ad hoc — F-item fixes route through `desk-change-control` (the F74/F71/F75/F72 cluster specifically through `gate-integrity-campaign`, which owns the live WHERE-ARE-WE check for this cluster).

| Weakness | What actually breaks | Status 2026-07-05 |
|---|---|---|
| **F71 — anchor-vs-sufficiency precedence undefined** | Two gates demand contradictory outcomes: the anchor bound forces a rating move (e.g. moat Weak→Mixed at anchor +0.50) that the F63 sufficiency gate then forbids (2 secondary publishers < 3). First live firing (2026-07 v3 flagship) was resolved with a whole-run `--no-sufficiency` bypass. | OPEN (backlog line 463). Fix = Part-33 migration. "Must land before any unattended loop." |
| **F72 — publisher distinctness is netloc-only** | One wire press release syndicated on 3 domains (e.g. stocktitan.net / markets.financialcontent.com / finance.yahoo.com — all already in the store) counts as 3 "distinct publishers", silently unlocking F2e high confidence + thesis reversals + wiki promotion at once. | OPEN (line 567). Must-have caliber. |
| **F74 — `cycle-log.json` is a slot, not a log** | The clobber vulnerability itself is now CLOSED — merged `257cf1b` on 2026-07-05, backlog ticked same day (`1a9eb33`); `cycle-plan --out` now refuses to overwrite anything richer than a bare plan skeleton (`_is_bare_plan`/`_cycle_plan`, `gpu_agent/cli.py`). One-line history: lane claimed 2026-07-05 (`d84f3b9`, worktree `f74-cycle-log`) after a post-run writer had clobbered the 2026-07 v3 journal (erasing the F71 bypass record — it survives only at commit 99ca522); fixed and merged the same day. The worktree/branch are now deleted, not retained. The **structural characterization survives the fix**: `cycle-log.json` is still architecturally a slot, not an archive — git history remains the only archive of prior runs; the fix only stops the slot from silently swallowing a richer journal than a bare plan. | **CLOSED** — merged `257cf1b`, backlog ticked `1a9eb33` (verify: `git log --oneline --grep=F74`). Full chronicle: `desk-failure-archaeology` fight 12. |
| **F75 — whole-run gate bypass flags** | `--no-sufficiency` / `--no-voice-lint` bypass an entire run; a bypassed cycle can still stamp `ready` with no trust-footer disclosure. The first post-F63 flagship ran in exactly the configuration the F63 spec forbade. | OPEN (line 620). Policy: per-item + reason + logged, before any unattended loop. |
| **F25 — wiki log O(N) re-reads** | `WikiLog.append` computes `seq = len(self.read())` — full-log re-read per append, O(pages²) health scans, TOCTOU race under concurrency. Fine at one category; fatal at 34. | OPEN (line 121). Phase-4 prerequisite. |
| **F24 — entity fragmentation, live in the store** | `store/wiki/entity/` holds BOTH `nvda.md` and `nvidia.md` plus a degenerate `multi.md` (verified 2026-07-05) — one company's thread split across pages. No alias canonicalization exists yet. | OPEN (line 118). Binding at desk #2. Never treat the wiki as one-page-per-entity. |
| **Mixed-grain lexical sorting** | Month and day grains share one directory and sort lexically: `'2026-07' < '2026-07-02'`, so the monthly flagship v3 is NOT the max-sorting file in its own directory. `find_prior` handles it via (asOf, N) parsing, but naive "latest file" logic is wrong. | Permanent subtlety; only partially test-pinned. |
| **CWD-dependent registry reads** | `reader.py` reads `registry/acronyms.json` / `registry/indicators.json` via relative `Path` literals (env-var-blind, cached in module globals); `briefing.py` defaults `DimensionTracks.load("registry/indicators.json")`. The CLI only works from repo root. | Latent portability bug; unfixed. |
| **Category-hardcoded gitignore whitelist** | The whitelist negates `!store/chips.merchant-gpu/` only. A `models.frontier-closed` live run would mint scorecards into an IGNORED directory — silently untracked, violating "a cycle that isn't committed didn't happen". No test guards this. | OPEN trap; amend `.gitignore` BEFORE any second-category run (change routes through `desk-change-control`). |

Also flag, don't resolve: **charter Part 37 contradicts itself** — lines 1637-1639 say "Not yet (deferred, by decision): hard corroboration + a hard secondary-confidence cap" while the F63 amendment ~60 lines above (lines 1574-1587) says hard multi-source corroboration "landed as F63 (contract v1.3)". Which reading governs is undecided (maintainer ruling pending); quote neither line as the whole truth.

## 9. Deliberate choices — do NOT "fix"

Each of these looks like a bug to fresh eyes. Each is documented as intentional, most with an in-code warning. Changing any of them is a frozen-surface or contract change → `desk-change-control`.

| Choice | Where documented | Why |
|---|---|---|
| Coverage-floor counts contributing FINDINGS while the index collapses to latest-per-(entity,indicator) — an apparent counting asymmetry | `pipeline.py` `_index_for` comment: "Count contributing FINDINGS (not distinct indicators) — this is the coverage-floor unit the spec specifies" | Findings are the coverage-evidence unit; indicators are the scoring unit. |
| Judge majority ties break toward the WEAKEST rating | `judge.py:12,43` — `RATING_ORDER` starts at "Very weak"; `min(..., key=RATING_ORDER.index)` | Conservatism under disagreement; never let a tie inflate a rating. |
| `label_ids_in_text` is a SINGLE `re.sub` pass | `reader.py` F68e docstring: "Do not rewrite this as a loop of per-id re.sub calls; that reintroduces the chaining bug this function exists to prevent" | One pass means inserted labels are never re-scanned — no substitution chaining. |
| L1 dedup matches content-hash BEFORE URL; the same URL recurs in seen_docs.jsonl with new hashes | `dedup.py` F12 docstring | A stable URL whose content changed is a NEW document (stable price pages survive). |
| Scoring weights sum to 1.02, unnormalized | `registry/indicators.json`; nothing enforces a partition | Weights are hand-set registry data; DMI/SMI have no fixed scale (Part 17 forbids magnitude words on them). |
| Two publisher-identity functions coexist (corroboration key vs display keys) | `publisher.py` F31 docstring vs `brief.py`/`price_track.py` | Corroboration identity must never drift; display grouping has different needs. |
| Structural-side findings still need nonzero polarity; only price is exempt | `gate.py:40-44` | Structural signals must still declare which track they inform, even though scoring excludes them. |
| Missing dimension rating = honest under-supported state | `judge.py` F19; `pipeline.py` dimensionStatus | "1-of-3 is not unanimity, it is absence." |

## Common mistakes

- **Hand-editing anything the brain produced, or `baseline.json`** — categorically forbidden (Section 1 law). Re-dispatch with the verbatim violation; baseline changes only via `run-eval` rebaseline.
- **"Fixing" an item from Section 9** — check the do-not-fix table before touching tie-breaks, counting, dedup keys, or `label_ids_in_text`.
- **Treating checked/unchecked backlog boxes as status** — several F-items are merged-but-unticked. Resolution order: HANDOFF top block → `git log --grep=F<n>` → backlog entry text. (Details → `desk-docs-and-writing`.)
- **Trusting `store/cycle-log.json` as run history** — it holds only the latest run (F74). Prior journals live only in git history.
- **Reading canon from ignored `store/` scratch subtrees or from `work/`** — the `.gitignore` whitelist defines canon.
- **Stating "no API/SDK path exists in the codebase"** — false; state "the live path has no API/SDK; a dormant, doctrine-forbidden `anthropic_api` backend exists in code."
- **Hardcoding "33 categories"** — the taxonomy has 34 (verified by count).
- **Assuming Layer/Main, scheduling, the scoped query tool, or Recommendations are live** — all deferred stubs (Section 2).
- **Running a second category without amending the gitignore whitelist** — its scorecards vanish from git silently (Section 8).
- **Trusting charter line numbers without re-checking** — the charter is amended frequently (verify with the commands below).

## Provenance and maintenance

Authored 2026-07-05 against discovery baseline main @ `a8ec757`; every fact above re-verified same day at main @ `639c00d` (post-daily-#1 commit `d9cfb3f`, post-F74-lane-claim `d84f3b9`). All commands run from repo root (`C:\Users\danie\random_for_fun`), Windows PowerShell 5.1 unless noted. Re-verify volatile facts before repeating them:

| Volatile fact | Re-verify with |
|---|---|
| HEAD / date | `git log -1 --format="%h %ad %s" --date=short` |
| Working-tree store drift (F74 check) | `git status --short store/; git diff --stat store/cycle-log.json` |
| F-item open/closed truth | `Select-String -Path docs/fix-backlog.md -Pattern '\*\*F7[1-6]'` then `git log --oneline -i --grep="F74"` (checkboxes lag git) |
| Scorecard immutability | `git log --diff-filter=M --oneline -- store/chips.merchant-gpu/` (expect empty) |
| Fix-forward (zero reverts) | `git log --oneline -i --grep="revert"` (expect empty) |
| Gitignore whitelist (canon definition) | `Select-String -Path .gitignore -Pattern 'store'` |
| Tier stubs still deferred | `Select-String -Path gpu_agent/cycle.py -Pattern 'deferred'` |
| Indicator/scoring/category counts (17/10/34) | `.venv/Scripts/python -c "import json; r=json.load(open('registry/indicators.json',encoding='utf-8')); t=json.load(open('docs/taxonomy.json',encoding='utf-8')); print(len(r['indicators']), sum(1 for v in r['indicators'].values() if v.get('scoring')), sum(len(l['categories']) for l in t['layers']))"` |
| CLI verb list (16) | `.venv/Scripts/python -m gpu_agent.cli --help` |
| Anchor tolerance / corroboration bar | `Select-String -Path gpu_agent/gate.py -Pattern '_ANCHOR_TOL'; Get-Content registry/corroboration.json` |
| Wiki entity fragmentation (F24) | `Get-ChildItem store/wiki/entity/` (nvda.md + nvidia.md coexisting = still open) |
| Charter key lines (drift with amendments) | `(Get-Content docs/agent-swarm-charter.md)[1636..1638]` (PowerShell is 0-indexed: this prints file lines 1637-1639, the "Not yet" list) and `Select-String -Path docs/agent-swarm-charter.md -Pattern 'contract v1.3'` |
| Second-category store dir still absent | `Test-Path store/models.frontier-closed` (False = never run live) |
| Frozen-surface size sanity | `Get-Content gpu_agent/scoring.py | Measure-Object -Line` (24 lines at authoring) |

If any re-verification contradicts this document, trust the repo, then update this skill via the process in `desk-change-control`.
