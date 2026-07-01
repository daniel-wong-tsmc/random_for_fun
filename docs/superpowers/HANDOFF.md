# HANDOFF — GPU Category Agent (resume point: sp4-4d SPEC+PLAN written → run subagent-driven-development next)

- **Date:** 2026-07-01
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **`main` (`fad9203`):** 4-1 `3a0a9c5`; 4-2 `2e3ba83`; 4-3 `3f776a8`; 4-4a `bccc16e`; **4-4b `8cee8a3`** (all merged,
  local). **4-4b is BUILT + merged, suite 332 passed / 3 skipped** (opus final review "Ready to merge: Yes").
  **4-4d is brainstormed, spec'd, and planned — spec + plan committed on `main`** (`3b1f216` spec, `fad9203` plan);
  **not yet built.** **NOT pushed** — `origin/main` is at `aabc4c8`; local `main` is **18 commits ahead** (8 prior +
  6 × 4-4b impl + spec-§8 fix `8cee8a3` + handoff `08f1eda` + 4-4d spec `3b1f216` + 4-4d plan `fad9203`); push only
  when the user asks. Working tree clean. **Truly-frozen core** (gate/scoring/registry code/Finding schema/pipeline
  Part-7 gate/JsonStore/FindingStore/wiki `log.py`+`page.py`+`lint.py`, `gathering/ingest.py` `normalize_documents`)
  byte-unchanged vs origin baseline `aabc4c8`; `wiki/store.py` changed only by 4-4a's `set_body`; `wiki/ingest.py`
  modified additively/behavior-preserving by 4-4a + 4-4b.
- **THE SEQUENCE WAS REORDERED THIS SESSION:** discovery (4-4c) needs gathered raw material to "notice the off-list
  topic," and the gather firehose is 4-4d — so **4-4d is now built BEFORE 4-4c**. New order:
  **4-1 → 4-2 → 4-3 → 4-4a → 4-4b → 4-4d → 4-4c → 4-5.**
- **For the next Claude instance:** read this file, then the **4-4d plan**
  `docs/superpowers/plans/2026-07-01-daily-gather-scrape-dedup.md` and its **spec**
  `docs/superpowers/specs/2026-07-01-daily-gather-scrape-dedup-design.md` (§0 has the locked decisions + the reorder;
  §10 the 4-4d↔4-4c seam). Skim the existing Part-37 ingest seam `gpu_agent/gathering/ingest.py` (`normalize_documents`
  — 4-4d's L1 runs *after* it, frozen), the merged **4-4a/4-4b** (`2026-06-29-wiki-ingest*`, `2026-06-30-wiki-lint*`
  — 4-4d feeds 4-4a `wiki-ingest` and its UPDATEs become 4-4b material moves), and the **4-2** `sourceInventory` +
  `cadenceHorizon` (the scrape sources + cadence prioritization). Check the SDD ledger `.superpowers/sdd/progress.md`
  + `git log` so you don't redo finished work. The immediate task is to **execute the 4-4d plan via SDD.**

---

## IMMEDIATE NEXT TASK — execute sub-project 4-4d (the input firehose) via subagent-driven-development

The **4-4d spec + plan are written and committed.** They still need the build:
1. **`superpowers:subagent-driven-development`** on `docs/superpowers/plans/2026-07-01-daily-gather-scrape-dedup.md`
   — fresh **sonnet** implementer per task, two-stage **sonnet** review between tasks, **opus final whole-branch
   review**, on a branch `sp4-4d-…` off `main`. The plan is **6 TDD tasks** ending at **357 passed, 3 skipped**:
   (1) dedup data models + `DedupConfig`; (2) `SeenDocIndex` + L1 pre-brain document dedup (URL + content-hash);
   (3) prior-vintage lookup (via the entity page's observations — `FindingStore` has no iteration) + the
   tolerance-based change test; (4) L2 `classify_findings` — NEW/UPDATE/DUPLICATE + intra-batch collapse;
   (5) CLI wiring — `ingest --dedup-store` (L1) + the new `wiki-dedup` subcommand (L2) + frozen guard; (6) the
   daily gather mode + numeric scrape skill edits (`gather-category`/`run-cycle` — **session-run, dry-run validated**,
   like sp2 Task 3 / sp3-A Task 10, no pytest).
2. **Merge to `main`** (local fast-forward, like 4-1/4-2/4-3/4-4a/4-4b); keep the ledger `.superpowers/sdd/progress.md`
   (append an `sp4-4d` section; mark each task complete when its review is clean).
3. **Throwaway preview-render** (seed a store, run `ingest --dedup-store` twice to show L1 drop known docs, then
   `wiki-dedup` to show the NEW/UPDATE/DUPLICATE split + the `DedupReport` going live).
4. Then **4-4c** (discovery lane on live gather input) — its own brainstorm → spec → **user-review gate** → plan →
   SDD → merge; then **4-5** (per-category Market-State brief render, extends A's `report.py`).

**What 4-4d builds (acceptance = spec §13):** the daily **input firehose**. A pure-code **cross-run dedup-vs-store**
engine (`gpu_agent/gathering/dedup.py`): **L1** a persistent `SeenDocIndex` (URL + content-hash → first-seen `asOf`)
that drops already-seen documents **before** extraction; **L2** a finding-level classifier that, per
`(entity, indicatorId)` vs the store's latest vintage, splits gated findings into **NEW / UPDATE / DUPLICATE**
(NEW+UPDATE ingest via 4-4a; DUPLICATE logged + dropped) — tolerance-based (1% default) with an intra-batch collapse;
a `DedupReport` counts everything (**nothing silent**). Wired additively into the CLI (`ingest --dedup-store` L1;
new `wiki-dedup` subcommand L2). Plus the **daily gather mode** (recency-windowed Part-37 loop, cadence-prioritized,
caps logged) + the **numeric scrape sweep** — a permissive daily source (e.g. `gpuSpotPrice`) is a gatherer snapshot
→ the **FROZEN** `extract → gate` → a measured Finding (no code number-path; **Part 22**: paywalled labeled
`estimate`, never fetched). Frozen contract + `normalize_documents` + all wiki modules byte-unchanged; additive only;
no new dependency.

**The 4 locked 4-4d design decisions (from this session's brainstorm — don't relitigate):** (a) **reorder** 4-4d
before 4-4c; (b) **full firehose** — all three pieces in one sub-project; (c) **hybrid dedup** — L1 doc URL/hash
pre-brain + L2 finding-level NEW/UPDATE/DUPLICATE post-gate; (d) numeric scrape rides the **frozen brain**
(gatherer-snapshot → extract→gate, no new code number-source path). Plus: L1 memory = a new persistent seen-doc
index; L2 "changed" = tolerance-based; one 4-4d spec (code core via SDD/pytest + skill edits via dry-run) on one
branch.

**Plan realizations pinned (the plan is the authority):** the module is `gpu_agent/gathering/dedup.py` (the
*existing* `gathering/` package, not a new `gather/`); `DedupReport` carries the finding-level verdicts while L1's
doc drops fold into the `ingest` gather-log (`droppedKnown`) — the two run at different pipeline stages; the current
`ingest` subparser has only `--blobs`/`--out`/`--primary-sources`, so Task 5 adds `--dedup-store` **and** `--as-of`.

**What 4-4b delivered (DONE, merged `8cee8a3`, suite 332/3):** a pure-code `wiki-lint` pass
(`gpu_agent/wiki/lint.py` + CLI, **no new brain step**) that ranks the daily `diff`'s **material moves** (new-thread
| state/trajectory change | contradicts-thesis[highest] | moves-scoring-indicator∝magnitude, × tier × recency ×
leading-boost × the brain's intrinsic `salience`; below-threshold moves **dropped + logged**), applies
**non-destructive salience decay** (per-thread half-life input-derived from 4-2's `cadence × horizon` tags;
`quiet_age` by cycle-count; `effective_salience = intrinsic × 0.5^(quiet_age/half_life)`; a `stale` flag), and a
**structural health** pass (orphans / stale / asymmetric + mention-without-link cross-ref gaps / contradiction
roll-up). The contradiction is read via a **shared `format`/`parse` helper in `ingest.py`**; emits one **idempotent
`lint` log event** per `asOf`. Folded in the 4-4a deferred Minor (`PageEnrichment.salience` `[0,1]` bound). Opus
final review "Ready to merge: Yes" (no Critical/Important); the one pre-merge item was a doc fix (spec §8 CrossRefGap
field names → shipped `source`/`target`). **Preview-confirmed LIVE:** ranked material moves (contradiction as the
highest factor), non-destructive decay (stored salience unchanged), the `stale` signal, the health report.
**The 4-4b↔4-4c boundary is locked (4-4b spec §11):** 4-4b produces signals; **4-4c consumes them** (materiality →
promotion; `stale` → provisional pruning). 4-4b honors 5 design-for-4-4c constraints (page-type agnostic, status
carried, no lifecycle mutation, emits `lint` events, produces `stale`). **4-4b deferred follow-ups** (logged in the
ledger, non-blocking): the optional precise W_state guard (`im.oldState!=im.newState or im.oldTrajectory!=…`) for the
cosmetic salience-only over-fire; `_is_scoring` ignoring per-category overrides (latent); `mention-without-link`
substring vs spec §4 "token match"; dangling-crossRef silently skipped in the asymmetric check.

**What 4-4a delivered (DONE, acceptance spec §9 all met):** a `wiki-ingest` CLI that (Phase 1, code) routes each
gated finding to `entity:<slug(finding.entity)>` idempotently (auto-create provisional pages, append observations,
fail loud on empty entity), then (Phase 2, brain via `--emit-prompt`→`--recorded`) enriches *existing entity pages
only* — prose body, state/trajectory/salience, crossRefs, contradiction notes, one `ingest` log event per run.
Added the additive `WikiStore.set_body`; everything else reuses the 4-1 store API. Frozen contract + existing 4-1
wiki/store members byte-unchanged; committed fixtures unchanged; numbers only from gated findings; nothing silent.
**Preview-confirmed:** golden findings → `entity:{nvda,amd,intc}`; recorded apply made `entity:nvda` live (state
`accelerating`, trajectory `steady -> accelerating`, salience 0.9, crossRefs `[entity:amd]`, body cites
`[f-nvda-d2]`); log = create/append per finding + one `state-change` + exactly one `ingest`.

**4-4 decomposition (locked in the 4-4a spec §0; 4-4c/4-4d REORDERED this session):** **4-4a** ingest writer (done)
→ **4-4b** relevance engine / lint (done) → **4-4d** daily gather + numeric scrape + cross-run dedup-vs-store
(spec+plan written, next to build) → **4-4c** discovery lane (explore budget + theme pages + provisional off-registry
topics + quarantine + promotion on persist+corroborate, Part 10 — consumes 4-4d's de-noised stream + 4-4b's
materiality/`stale` signals). 4-5 (the brief render) comes after 4-4. **Why the reorder:** 4-4c's brain discovery
needs gathered raw material to notice off-list topics — that is exactly what 4-4d produces, so the firehose is built
first (decided this session with the user).

**Deferred follow-ups to fold in where they fit** (logged in the ledger): from 4-2 — `gpuSpotPrice` dimension is
`null` in registry vs `"momentum"` in the manifest `ExpectedIndicator` (add a manifest↔registry consistency test
or document the exception); `validate_coverage` guards only *scoring* indicators (extend to tagged overlays if
they get fed). From 4-3 — `_partition_by_horizon` calls `horizon()` on every finding incl. overlays (fail-loud,
but broader than `validate_coverage`'s scoring-only guarantee; fold a tagged-ness check into `validate_coverage`
when overlays start carrying findings); no dedicated test for the cli `_pipeline` path (identical to tested `_build`).

---

## WHAT'S DONE — sub-project 4-3 (two indices: Momentum vs Outlook) — MERGED `3f776a8`, suite 282/3

Spec `2026-06-29-two-indices-momentum-outlook-design.md`, plan `2026-06-29-two-indices-momentum-outlook.md`
(4 TDD tasks). Built via SDD (fresh sonnet implementer/reviewer per task, **opus final = "Ready to merge: Yes"**,
no Critical/Important). Deliverables:
- New optional `Scorecard.indices: MarketIndices` — `momentum` (lagging+coincident) + `outlook` (leading), each a
  reused `DemandSupply` (dmi/smi/sdgi/direction), + a `Divergence` (cross-sectional 4-state verdict).
- Computed in `build_scorecard` by partitioning findings on the 4-2 horizon tags and reusing the **frozen**
  `dmi_smi_contribution` per bucket (same `assignment.weights`). Structural invariant: `demandSupply == momentum
  + outlook`. `build_scorecard` gained an optional `horizons=` kwarg (None → indices stay None; existing callers
  unaffected); cli `run`/`extract` pass it so real runs populate `indices`.
- `Divergence` = `_divergence` pure helper: `aligned | diverging-weakening | diverging-strengthening |
  insufficient-coverage`, boundary on categorical SDGI direction, `insufficient-coverage` first (floor = 1
  contributing leading finding; counts are scoring findings only). Temporal "turned vs last cycle" deferred to 4-5.
- **Outlook is `insufficient-coverage` until 4-4 feeds leading findings** (honest, logged note). A throwaway
  preview confirmed the warning case fires: Momentum demand-led while Outlook turns supply-led → `diverging-weakening`.
- Frozen contract + committed fixtures byte-unchanged; additive only.

---

## WHAT'S DONE — sub-project 4-2 (leading + daily indicators) — MERGED `2e3ba83`, suite 268/3

Spec `2026-06-29-leading-daily-indicators-design.md`, plan `2026-06-29-leading-daily-indicators.md` (3 TDD tasks).
Built via SDD (fresh subagent/task, two-stage sonnet review, **opus final = "Ready to merge: Yes"**, no
Critical/Important). Deliverables:
- 5 new merchant-gpu in-lane indicators in `registry/indicators.json`: `rpoBacklog` (momentum/demand, leading),
  `vendorRevenueGuidance` (momentum/demand, leading), `leadTimes` (bottleneck/supply, coincident) — **scoring**;
  `designWins` (competitiveStructure/**structural**, leading) + `gpuSpotPrice` (**price**, coincident/daily) —
  **scoring:false overlays**, auto-excluded from the index by the frozen `dmi_smi_contribution`.
- A top-level **`cadenceHorizon`** map tagging **all 17** indicators (C-3 top-level-map pattern; frozen
  `indicators.py`/`validate.py` byte-unchanged — loader ignores the new key).
- New accessor **`gpu_agent/registry/horizon.py`** (`IndicatorHorizons`: `get`/`cadence`/`horizon` +
  `validate_coverage` that fails loud on untagged scoring indicators, invalid values, or orphan tags) + tests.
- `sourceInventory` entries (incl. SemiAnalysis inventoried as `licensed-api`/paywalled, labeled, never scraped)
  + `manifests/chips.merchant-gpu.json` coverage for the 5 new (reused `nvda-earnings`/`amd-earnings`/
  `channel-checks`; added `vendor-pr-trade-press`/`semianalysis`/`gpu-marketplaces`).
- DMI/SMI on committed fixtures **unchanged** (new indicators inert until 4-4 feeds them); frozen contract intact.

---

## THE BIG ARCHITECTURAL DECISIONS MADE THIS SESSION (do not relitigate without reason)

1. **The output goal is a human-readable "GPU Market Brief"** — a deterministic Markdown/terminal brief (pure
   projection of the canonical store, **no LLM in the renderer**), then an HTML dashboard as a follow-up. The
   design target is committed: `docs/superpowers/specs/2026-06-29-human-market-brief-design-target.md` (BLUF;
   demand|supply|gap as **words+direction**, number second; NOW-vs-NEXT divergence; lead with **what moved**;
   every line cited + honest). This is what 4-2→4-5 build toward.

2. **Lane discipline (Part 21 "counted once"; the 5-layer cake).** `merchant-gpu` owns only the merchant GPU
   **vendors** (NVIDIA/AMD/Intel) — their demand momentum, unit economics, competitive position *within
   merchant GPUs*, product lead-times/pricing, strategic risk. The deep **supply constraints** (CoWoS, HBM,
   wafers, networking, power) and broad **demand drivers** (hyperscaler capex, inference, buildouts, the ASIC
   threat) are **owned by sibling/adjacent category agents** and reach merchant-gpu only as cited adjacent
   context via the (deferred) Layer rollup. **4-2 does NOT annex them.** (This corrected an earlier over-broad
   indicator proposal — the taxonomy has ~33 leaf categories across 5 layers; see `docs/taxonomy.json`.)

3. **The cross-cutting "state of the GPU market" brief is a LAYER-TIER product**, not a single category's
   output — the chips-layer agent reconciling `foundry-packaging + hbm-memory + hyperscaler-asic +
   networking-silicon + merchant-gpu`, reading energy (supply) + infra/models (demand). This is the **named
   future arc** after sp4's per-category mechanics are proven (the deferred Layer/Main tiers, Part 38). The
   §3 mock in the design target is really this layer/market brief (see its §0).

4. **Discovery of UNDEFINED topics + bounded rabbit-holing → 4-4.** The user wants the agent to research both
   the topics we define (the registry — 4-2) AND topics we didn't, going down rabbit holes to the bottom. That
   capability = the **discovery lane** (Part 18: provisional entity/theme threads for undefined topics,
   confidence-capped + quarantined from canonical, promoted only on persist+corroborate) + **follow-the-trail**
   gather with brakes (Part 37) + an `explore` budget. It is assigned to **4-4** (its substrate exists: 4-1's
   provisional threads + the Part-37 gather that already trails leads). **Not pulled into 4-2.**

5. **4-4 and 4-5 are back in the active sequence** (charter Part 39 re-scoped, commit `cd8e007`). Full order:
   **4-1 (done) → 4-2 (spec written) → 4-3 → 4-4 → 4-5.** 4-4 is elevated from "deferred" to the headline
   discovery/deep-investigation engine; 4-5 is the per-category brief render.

---

## TL;DR — where we are

North star: a **daily, explainable GPU-market intelligence monitor running inside Claude Code itself** (Claude
Code *is* the brain — no OAuth token, SDK, `[llm]` extra, or external API). sp1–3 (harness, live runs, output &
coverage) are DONE+merged+pushed. **sp4 = turn the quarterly scorecard into a daily demand/supply monitor.**

**sp4 progress:**
- **4-1 — Temporal store + LLM-wiki thread model: DONE, merged to `main` (`3a0a9c5`), PUSHED.** A standalone
  append-only `FindingStore` + `gpu_agent/wiki/` (page.py no-dep `key:<json>` frontmatter; log.py append-only
  temporal log; store.py `WikiStore` create/append/record_state/update_header/observations/state_history/
  window/index/`diff`). Pure code + diff; brain ingest deferred to 4-4. Suite 248/3.
- **4-2 — Leading + daily indicators: DONE, merged to `main` (`2e3ba83`, pushed).** Suite 268/3.
- **4-3 — Two indices Momentum/Outlook split by horizon: DONE, merged to `main` (`3f776a8`, pushed).** Suite 282/3.
- **4-4 — decomposed into 4-4a→4-4b→4-4d→4-4c** (REORDERED: gather firehose before discovery):
  - **4-4a — Brain ingest into the wiki: DONE, merged to `main` (`bccc16e`, local).** Suite 300/3. The keystone
    wiki *writer*: `wiki-ingest` CLI (Phase-1 deterministic entity routing + Phase-2 brain enrichment via
    `--emit-prompt`→`--recorded`), additive `WikiStore.set_body`, `gpu_agent/wiki/ingest.py`. Opus final review
    "Ready to merge: Yes" (no Critical/Important). Preview-confirmed entity pages going live. ← **4-4 keystone done.**
  - **4-4b — Relevance engine / wiki lint: DONE, merged to `main` (`8cee8a3`, local).** Suite 332/3. Pure-code,
    no new brain step: `gpu_agent/wiki/lint.py` (materiality scorer — 4 factors × hybrid multipliers; non-
    destructive salience decay — tag-derived half-life + cycle-count quiet-age; structural health — orphans/stale/
    cross-ref gaps/contradiction roll-up; `lint()` + `LintReport`/`LintConfig`), the contradiction `format`/`parse`
    seam + `PageEnrichment.salience` `[0,1]` bound in `ingest.py` (behavior-preserving), the `wiki-lint` CLI, one
    idempotent `lint` event/cycle. Opus final review "Ready to merge: Yes". Preview-confirmed LIVE (ranked material
    moves, contradiction as highest factor, non-destructive decay, `stale` signal, health). ← **4-4 relevance done.**
  - **4-4d — resume here (SPEC + PLAN written/committed `3b1f216`/`fad9203`, not yet built).** ← **run SDD on the
    4-4d plan `2026-07-01-daily-gather-scrape-dedup.md`.** 6 TDD tasks → 357/3. The input firehose: cross-run
    dedup-vs-store (L1 `SeenDocIndex` pre-brain doc dedup + L2 finding-level NEW/UPDATE/DUPLICATE post-gate,
    tolerance-based) in `gpu_agent/gathering/dedup.py`; CLI wiring (`ingest --dedup-store` + `wiki-dedup`); daily
    gather mode + numeric scrape (skill, Part 22 honest — gatherer→frozen extract/gate). Additive; frozen +
    `normalize_documents` + all wiki modules byte-unchanged.
  - **4-4c — after 4-4d.** Discovery lane on live gather input: explore budget + theme pages + provisional off-
    registry topics + quarantine + promotion on persist+corroborate (consumes 4-4b materiality + 4-4d's NEW
    candidates) + provisional pruning (consumes 4-4b `stale`). NOT yet spec'd — brainstorm → spec → user-review
    gate → plan → SDD → merge.
- **4-5 — not started.** (Per-category Market-State brief in Markdown, extends A's `report.py`; renders the two
  indices + the divergence + "what moved" + storylines per the design target.)

---

## OPERATING NOTES / INVARIANTS (carry forward — still all true)

- **Run from repo root** `C:\Users\danie\random_for_fun`; Python 3.11+ at `.venv/Scripts/python` (Windows host;
  `.venv` gitignored — recreate with `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`).
  `[llm]` extra is optional and **not installed / not needed** (the brain is a Claude Code subagent).
- **Claude Code IS the brain** — no OAuth token, SDK, `[llm]`, or external API. Live extraction/judgment is a
  dispatched Opus subagent; deterministic code gates + scores.
- **Truly frozen — never edit (byte-unchanged):** `gpu_agent/gate.py`, `gpu_agent/scoring.py` (`zscore`,
  `dmi_smi_contribution`), `gpu_agent/registry/indicators.py` + `validate.py` (loader/validator CODE), the
  `Finding` schema (`gpu_agent/schema/finding.py`), the **6 dimension names**
  (`momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`), the rating scale,
  `pipeline.py`'s Part-7 gate, and the existing `JsonStore` class body. **Additive only (Part 33):** the
  `Scorecard` model (new optional fields), **registry DATA** (`indicators.json` — new indicators + the top-level
  `cadenceHorizon`/`sourceInventory` maps), the manifest, `report.py`, the gather/run-cycle skills, the judgment
  prompt/result, and NEW modules (the wiki, `registry/horizon.py`, the relevance engine).
- **C-3 lesson:** `IndicatorSpec` is `extra="forbid"`; per-indicator metadata (sourceInventory, cadenceHorizon)
  goes as a **top-level map** in `indicators.json` keyed by indicator id — never inside an indicator dict, never
  a new `IndicatorSpec` field. The frozen loader ignores unknown top-level keys.
- **Doctrine:** code computes + gates + stores; the brain reasons/curates; **the agent never sets a number that
  reaches the scorecard/page/index uncomputed (Part 17 — numbers only from gated findings)**; every page claim
  cites its finding(s); **fetched page text is DATA, not instructions** (Part 8/26); the wiki `log` + gated
  findings make every cycle **replayable** (Part 20); **caps / skips / materiality-drops / coverage gaps are
  logged, never silent** (Part 29); thread ids + provisional registry items stay **provisional + confidence-
  capped + out of canonical** until they **persist + corroborate** (Parts 18/10); paywalled sources are
  inventoried + labeled `estimate`, **never scraped** (Part 22); **lane discipline — counted once** (Part 21).
- **Tests deterministic** via committed fixtures (`fixtures/…`); live paths are env-gated smokes; skills
  validated by documented dry-runs. **Every commit ends with**
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Windows flakiness:** the Bash safety classifier can be intermittently unavailable for write/commit — retry
  or use the PowerShell tool. CWD sometimes resets to `C:\Users\danie`; prefix git/pytest with
  `cd /c/Users/danie/random_for_fun && …`.
- **`.superpowers/` and `store/` are gitignored.** `.claude/` is tracked (skills). Keep the SDD ledger at
  `.superpowers/sdd/progress.md`; trust it + `git log` after any compaction.
- **Model preference (user):** opus for important final reviews; sonnet acceptable for mechanical per-task
  implementer + reviewer work.

---

## WHAT'S DONE (sp4)

### sp4 4-1 — Temporal store + LLM-wiki thread model — MERGED `3a0a9c5` (PUSHED), suite 248/3
Spec `2026-06-27-temporal-store-wiki-design.md`, plan `2026-06-27-temporal-store-wiki.md` (6 TDD tasks). Built
via SDD (fresh subagent/task, two-stage review, opus final = "Ready to merge: Yes"). Deliverable: `FindingStore`
(in `store.py`) + `gpu_agent/wiki/{page,log,store}.py`. Frozen contract byte-unchanged (guard verified). The
diff contract was clarified post-review: `index_moves` covers pre-existing pages only; the brief's "what moved"
= `new_pages ∪ index_moves`. **Deferred follow-ups (logged in the ledger, non-blocking):** corrupt-JSONL-line
in `WikiLog.read` raises raw pydantic error (fails loud; could wrap to `WikiFormatError`); `record_state`
`finding_id` not validated vs FindingStore; `window` double-reads the page; untyped public signatures; missing-
page tests for log_append/window/state_history; a committed `fixtures/wiki/` on-disk fixture.

### sp1–sp3 — see git history (all merged to `main` and pushed at `d356eff` baseline)
Harness (sp1), live category runs (sp2), output & coverage overhaul B/A/C (sp3). Suite was 211/3 at sp3; 248/3
after 4-1.

---

## ROADMAP (post-4-2)

- **4-3 — Two indices:** trailing **Momentum** (lagging+coincident) + forward **Outlook** (leading), each
  split demand/supply with its own SDGI, computed in code (reuse B's additive-field discipline). Reads the
  `cadenceHorizon` tags via `registry/horizon.py`. Surface the **Momentum-strong-while-Outlook-turns**
  divergence. (Generalizes today's dmi/smi.)
- **4-4 — Daily gather + scrape cron + relevance/lint + brain ingest + DISCOVERY engine:** the materiality
  model (new-thread | thread-state-change | contradicts-thesis[highest] | moves-indicator∝magnitude; weighted
  by tier+recency; decays as a thread goes quiet); salience-decay; the `--emit-prompt` wiki-ingest seam; the
  discovery lane (provisional threads for undefined topics) + follow-the-trail with brakes + explore budget; a
  daily numeric **scrape sweep** for daily-cadence indicators (e.g. `gpuSpotPrice`) — respect Part 22 ToS/
  licensing, label `estimate`. Every drop logged.
- **4-5 — Per-category Market-State brief (Markdown):** extends A's `report.py` into the per-category brief per
  the design target (merchant-gpu's own lane); HTML dashboard follow-up.
- **THE LAYER-TIER ARC (the real "GPU market state" brief):** stand up the key sibling category agents
  (`foundry-packaging`, `hbm-memory`, `hyperscaler-asic`, …) + the **chips-Layer rollup** that reconciles them
  and reads adjacent layers (energy supply, infra/models demand). This is what actually answers "what is the
  GPU market doing" end-to-end. Larger program; after sp4's per-category mechanics are proven. (Deferred
  Layer/Main tiers, Part 38.)
- **Then:** the unattended daily **scheduler** (Part 28) — the monitor is *designed* to run daily; auto-running
  it is a clean follow-on.
