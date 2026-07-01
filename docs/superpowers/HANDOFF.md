# HANDOFF — GPU Category Agent (resume point: 4-5 SPEC+PLAN written + user-approved + PUSHED → run subagent-driven-development on the 4-5 plan next)

- **Date:** 2026-07-01
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **`main` (`3f0b37f`) — PUSHED:** `origin/main == local main == 3f0b37f` (0 ahead, working tree clean). This is the
  first push since baseline `aabc4c8`; all 4-4a→4-4c feature work + docs + the 4-5 spec/plan are now on GitHub.
  Merged pieces: 4-1 `3a0a9c5`; 4-2 `2e3ba83`; 4-3 `3f776a8`; 4-4a `bccc16e`; 4-4b `8cee8a3`; 4-4d `f5f585c`;
  **4-4c `6758e9f`** (all merged local fast-forward, now pushed). **4-4c is BUILT + merged, suite 382 passed /
  3 skipped** (opus final review "Ready to merge: With fixes" — one test-only fix applied; preview-confirmed LIVE):
  the pure-code provisional lifecycle engine `gpu_agent/wiki/lifecycle.py` + the additive `wiki-lifecycle` CLI.
  **4-5 SPEC `f95baa3` (USER-APPROVED) + PLAN `3f0b37f` written + committed + pushed; not yet built.** Frozen core
  (gate/scoring/registry code/Finding+Scorecard schema/pipeline Part-7 gate/JsonStore/FindingStore/all `wiki/`
  modules/`gathering/`) byte-unchanged vs baseline `aabc4c8` except the documented additive edits (4-4a `set_body`;
  4-4a/4-4b `wiki/ingest.py`). **Push freely now — the user has authorized pushing; keep `main` and `origin/main`
  in sync** (prior sessions deferred the push; that changed this session).
- **Sequence (built in this order):** **4-1 → 4-2 → 4-3 → 4-4a → 4-4b → 4-4d → 4-4c → 4-5** (4-4d was reordered
  before 4-4c because discovery needs gathered material). 4-4 is fully done; **4-5 is the current piece.**
- **For the next Claude instance:** read this file, then the **4-5 plan**
  `docs/superpowers/plans/2026-07-01-per-category-brief-render.md` and its **spec**
  `docs/superpowers/specs/2026-07-01-per-category-brief-render-design.md` (§0 has the locked scope split + the 4
  decisions; §10 the acceptance) and the **design target** it renders toward
  `docs/superpowers/specs/2026-06-29-human-market-brief-design-target.md` (§2 the five readability rules; §3 the mock).
  Skim A's `gpu_agent/report.py` (4-5 extends its `render_report` + reuses its wording helpers `_momentum_word`/
  `_sdgi_interpretation`/`_fmt_delta`/`compute_sdgi`/`_signal_label`), the 4-3 `Scorecard.indices` (Momentum/Outlook/
  Divergence — the NOW/NEXT source), and the 4-2 `registry/horizon.py` `IndicatorHorizons` (the leading-signal tag).
  Check the SDD ledger `.superpowers/sdd/progress.md` (the `sp4-4c` section is complete; a `sp4-5` section is not yet
  created — the SDD skill will add it) + `git log` so you don't redo finished work. The immediate task is to
  **execute the 4-5 plan via subagent-driven-development.**

---

## IMMEDIATE NEXT TASK — execute sub-project 4-5 (per-category Market-State brief render) via subagent-driven-development

The **4-5 spec + plan are written, committed, pushed, and the spec was user-approved.** They still need the build:
1. **`superpowers:subagent-driven-development`** on `docs/superpowers/plans/2026-07-01-per-category-brief-render.md`
   — fresh **sonnet** implementer per task, two-stage **sonnet** review between tasks, **opus final whole-branch
   review**, on a branch `sp4-5-…` off `main`. The plan is **4 TDD tasks** ending at **399 passed, 3 skipped**:
   (1) new `gpu_agent/brief.py` + `render_state_of_market` (the BLUF — demand/supply momentum as direction+Δ, gap,
   NOW/NEXT from `indices`, divergence, `categoryStatus` headline + binding constraint); (2) `render_demand_supply_
   board` (findings grouped by side, collapsed to latest vintage, `_signal_label` word + trend arrow, `leading` tag
   from `horizons`, `⚠carried` flag); (3) `render_deferred_stubs` + `render_market_caveat` (honest "in 4-5b" stubs +
   the read-DIRECTION-not-level caveat); (4) compose the brief sections **brief-first** into `render_report` +
   optional `horizons` kwarg + the CLI `_report` `horizons` wiring + the honesty-invariant guard test + the frozen
   guard.
2. **Merge to `main`** (local fast-forward, like every prior piece) and **push** (the user authorized pushing this
   session — keep `origin/main` in sync). Keep the ledger `.superpowers/sdd/progress.md` (add a `sp4-5` section;
   the SDD skill does this — append each task line as its review comes back clean).
3. **Throwaway preview-render** — build an in-code `Scorecard` (with `indices` + `categoryStatus` + a few findings),
   run `report --scorecard <it>` and confirm the brief-first output (STATE OF THE MARKET → DEMAND|SUPPLY board →
   the 4-5b stubs → the existing detailed sections → the trust caveat), Outlook honestly "insufficient coverage".
4. Then the **DEFERRED follow-ups:** **4-5b** (wire the wiki store into `report` for the two store-fed sections —
   WHAT MOVED = the 4-1 `diff`'s `new_pages ∪ index_moves` ranked by 4-4b materiality; STORYLINES = wiki page
   `state`/`trajectory`/last-change, filtered by 4-4c's `partition_canonical` so `registered` = canonical coverage,
   `provisional` = confidence-capped — replacing the two stub lines), then the HTML dashboard, then the **discovery
   half** (brain-driven theme / off-registry discovery + `explore` budget + bounded rabbit-holing) as its own
   sub-project (4-4c is page-type agnostic, so promotion/pruning/quarantine apply to its provisional `theme` pages
   for free), then the **layer-tier arc** (the cross-cutting GPU-market brief; deferred Layer/Main tiers, Part 38).

**The 4 locked 4-5 design decisions (from this session's brainstorm — don't relitigate):** (a) **scope = the
scorecard-derivable sections only this cut** (STATE OF THE MARKET + DEMAND|SUPPLY board + a TRUST & COVERAGE caveat,
plus the existing detailed sections as drill-down); the store-fed WHAT-MOVED/STORYLINES + the judgment WHY tree are
**DEFERRED to 4-5b** and shown this cut as one-line honest stubs. (b) **the default `report` command is the single
unified artifact — brief-first** (no new subcommand, no flag; typing `report` gives everything, BLUF first). (c) **new
`gpu_agent/brief.py`** holds the new renderers and **reuses** `report.py`'s helpers; `report.py`'s `render_report`
gets a **minimal additive edit** (prepend the brief sections + append the caveat + an optional `horizons` kwarg —
existing helpers/order below the brief untouched); `report.py`+`Scorecard` are on the additive list, not frozen.
(d) **honesty (Part 17): no invented magnitude word on the unscaled DMI/SMI** — lead with direction (`positive/
negative/flat`) + the Δ-vs-prior (the *change* is the signal); earned rating words come only from the brain's
bounded-scale judgment (`categoryStatus`, per-signal `_signal_label`); Outlook honestly reads "insufficient coverage"
until 4-4 feeds leading findings. A test **locks** this honesty invariant. **Pure Scorecard projection — no wiki-store
read this cut** (the store enters only in 4-5b).

## WHAT 4-4c DELIVERED (DONE, merged `6758e9f`, suite 382/3 — acceptance spec §12 all met)

The pure-code **provisional lifecycle engine**, built via SDD (5 TDD tasks, fresh sonnet impl/reviewer per task,
**opus final review "Ready to merge: With fixes"** — one test-only fix applied; no Critical, one Important that was
the fix). Deliverables:
- **`gpu_agent/wiki/lifecycle.py`** (new, pure code, +139): models (`PromotionCandidate`/`PruneCandidate`/
  `QuarantineEntry`/`LifecycleReport`/`AppliedSummary`) + `LifecycleConfig` (`min_persist_cycles=2`/`min_sources=2`/
  `stale_threshold=0.1`/`prune_salience_floor=0.0`); **promotion** — `persistence` (distinct `asOf` cycles) +
  `corroboration` (distinct `evidence.source`) + `promotion_candidates` (both bars, provisional-only, ordered by
  pageId); **pruning** — `prune_candidates` (provisional∩`stale` from 4-4b's `lint().health.stale`); **quarantine** —
  `partition_canonical(index) → (registered, provisional)` + a guard test locking that `build_scorecard` takes no
  wiki/page input; the `lifecycle()` propose assembler (read-only; `provisionalConsidered == len(quarantined)`
  structural) + `apply_lifecycle()` (promote via `update_header(status="registered")`; prune via a non-destructive
  `record_state` salience floor; idempotent). Reads only; writes only via existing `WikiStore` methods behind `--apply`.
- **CLI (additive):** new **`wiki-lifecycle`** subcommand — `--store DIR --as-of D [--apply] [--report R]`; propose
  (default) prints the `LifecycleReport`, mutates nothing; `--apply` promotes/prunes + prints `promoted N, pruned M`;
  reads 4-4b's `stale` via `lint(...).health.stale` (computed in the handler like `wiki-lint`).
- Frozen contract + all wiki modules + `gathering` byte-unchanged (guard EMPTY); additive only; no new `status`
  value, no new `LogEvent.kind`, no new dependency. **Preview-confirmed LIVE:** NVDA (persist 2 / corroborate 2)
  proposed → `--apply` flipped `registered` (2nd apply idempotent), stale AMD proposed → `--apply` floored salience
  0.1→0.0 non-destructively (state/trajectory preserved, no delete/new status), propose a pure read-only no-op,
  `provisionalConsidered == len(quarantined)` throughout, promoted NVDA graduated out of the quarantine list.
- **4-4c deferred follow-ups** (logged in the ledger `sp4-4c` section, non-blocking): mutable `DEFAULT_LIFECYCLE_CONFIG`
  singleton (mirrors `DEFAULT_LINT_CONFIG` house style); narrow `test_models_construct`; no multi-candidate
  promotion-ordering test; `partition_canonical` missing its return annotation; no test for an absent-stale-pageId
  (code None-guards it); prune test doesn't assert `trajectory` survives (impl correct). By-design (no change): CLI
  propose calls `lint()` which appends its own idempotent 4-4b provenance event on a fresh `as_of` (the engine
  `lifecycle()` itself is pure); the quarantine guard is a denylist backed by the structural findings-driven scorer;
  promotion writes no log event (locked decision — provenance = `LifecycleReport` + page `status`/`lastUpdatedAsOf`).

**What 4-4c builds (acceptance = spec §12):** the pure-code **provisional lifecycle engine**
(`gpu_agent/wiki/lifecycle.py`): **promotion** — a provisional page observed across ≥`min_persist_cycles` distinct
`asOf` cycles AND citing ≥`min_sources` distinct evidence sources is *proposed* for promotion; `--apply` flips
`status=registered` idempotently (charter's "reviewed → promoted" gate; nothing auto-promoted). **Pruning** —
a provisional+`stale` (4-4b signal) page is *proposed* for prune; `--apply` floors salience via the existing
`record_state` (non-destructive; no delete, no new status). **Quarantine** — `partition_canonical(index) →
(registered, provisional)` is the reusable filter seam; provisionals are surfaced as `confidence-capped`
`QuarantineEntry`s; a guard test locks that `build_scorecard` takes no wiki/page input (provisional can't move
DMI/SMI). A `LifecycleReport` counts + lists everything (`provisionalConsidered == len(quarantined)`). Additive:
the new module + the `wiki-lifecycle` CLI. Frozen core (incl. all wiki modules + `gathering`) byte-unchanged; no new
`status` value, no new `LogEvent.kind`, no new dependency.

**The 4 locked 4-4c design decisions (from this session's brainstorm — don't relitigate):** (a) **scope = the
pure-code lifecycle engine only** — the brain discovery step + `explore` budget are a DEFERRED later sub-project;
(b) **promotion = persist (observations across ≥2 distinct `asOf`) + corroborate (≥2 distinct evidence sources)** —
read from persisted state (the per-cycle `lint` event has `pageId=None`, so the material-per-cycle history is NOT
persisted; and post-4-4d a new-cycle observation already implies a NEW/UPDATE material fact); (c) **propose-don't-
auto-register** — `status` flip only behind `--apply`; (d) **non-destructive pruning** — salience floor, no delete,
no new `status`/`LogEvent.kind` (`page.py`/`log.py` stay frozen); the `LifecycleReport` + page `status`/
`lastUpdatedAsOf` are the replayable audit trail. Quarantine = a reusable `partition_canonical` filter + report +
guard test. Module = `gpu_agent/wiki/lifecycle.py` (existing wiki package). CLI reads 4-4b's `stale` via
`lint(...).health.stale` (computed in the handler like `wiki-lint`).

**Why the discovery half is deferred (decided with the user this session):** 4-4c originally spanned ~6 greenfield
capabilities. The lifecycle half (promotion/pruning/quarantine) is pure code, testable over the provisional pages
that already exist (4-4a auto-creates provisional entity pages; 4-4d UPDATEs keep them moving) — matching the
4-4b/4-4d rhythm. The brain-driven *discovery* half (theme-page **creation**, `explore` budget, off-registry topic
definition, bounded rabbit-holing — a new `--emit-prompt` seam) is a larger, separate design and is its own future
sub-project. Because 4-4c is **page-type agnostic** (reads only `status`), the moment the discovery half writes
provisional `theme` pages, promotion/pruning/quarantine apply to them for free.

## WHAT 4-4d DELIVERED (DONE, merged `f5f585c`, suite 357/3 — acceptance spec §13 all met)

The daily **input firehose**, built via SDD (6 TDD tasks, fresh sonnet impl/reviewer per task, **opus final review
"Ready to merge: Yes"**, no Critical/Important). Deliverables:
- **`gpu_agent/gathering/dedup.py`** (new, pure code): **L1** `content_hash` + a persistent `SeenDocIndex` (append-only
  JSONL keyed by normalized URL **and** content-hash → first-seen `asOf`) + `filter_seen_documents` (drops
  cross-run-known docs **before** extraction, within-batch dedup, records survivors); **L2** `prior_vintage` (reads
  the store's latest vintage per `(entity, indicatorId)` via the entity page's observations — `FindingStore` has no
  iteration — max by `(capturedAt, observedAt, magnitude)`, the *same* collapse the frozen `dmi_smi_contribution`
  uses), `changed`/`delta_detail` (tolerance-based, 1% default via `DedupConfig`), and `classify_findings`
  (**NEW / UPDATE / DUPLICATE** partition + **intra-batch collapse** to latest vintage; deterministic order); a
  `DedupReport` counts + lists everything (**nothing silent**). It **reads** structured Finding/RawDocument values
  and **writes no page and no number** — NEW/UPDATE ingest is delegated to the existing 4-4a `wiki-ingest` writer.
- **CLI (additive):** `ingest` gained `--dedup-store DIR` (L1; folds `droppedKnown`/`droppedKnownDetail` into the
  gather-log + stderr; behavior-preserving when absent) **and** `--as-of`; a new **`wiki-dedup`** subcommand (L2;
  `--out-findings` receives only NEW+UPDATE, the `DedupReport` goes to `--report`/stdout).
- **Skills:** additive **daily mode** in `gather-category` (recency window + cadence prioritization via
  `registry/horizon.py` + numeric scrape sweep, **Part 22** paywalled labeled `estimate`/never fetched + logged as a
  gap, daily caps logged) and `run-cycle` (`mode=daily` threading `ingest --dedup-store` → extract/gate →
  `wiki-dedup --out-findings` → `wiki-ingest` → `wiki-lint`; reports `DedupReport` counts + `droppedKnown`).
- **Numeric scrape rides the FROZEN brain:** a permissive daily source (e.g. `gpuSpotPrice`) is a gatherer snapshot →
  the FROZEN `extract → gate` → a measured `Finding` (no code number-path; Part 17).
- Frozen contract + `normalize_documents` + all wiki modules byte-unchanged (guard EMPTY); additive only; no new
  dependency; gitignored runtime `store/seen_docs.jsonl`. **Preview-confirmed LIVE:** L1 run-2 dropped both docs
  `seen-url` (first-seen asOf retained); L2 split the July batch NEW `f-intc` / UPDATE `f-nvda` "value 2.5→2.95
  (tol 1%)" / DUPLICATE `f-amd` "unchanged within tolerance" + `f-nvda-early` "superseded by intra-batch latest
  vintage"; deduped = {nvda,intc}; the idempotent re-run classified all DUPLICATE.

**4-4d deferred follow-ups** (logged in the ledger `sp4-4d` section, non-blocking): `prior_vintage`'s broad
`except Exception` around `store.findings.get` could mask a corrupt stored finding into a wrong NEW verdict (narrow
it / fail loud); `delta_detail` imprecise on the value-appeared/disappeared + magnitude-only cases (human string
only) + no test for the `changed` value-appear/disappear branch; `SeenDocIndex` JSONL load/record has no
malformed-line guard/comment (self-written gitignored store; fail-loud defensible); the `ingest` stdout summary
always appends "0 known" (plan's own template; machine artifact preserved); `DedupReport` omits spec §4's `docsSeen`
(plan's explicit realization — folds L1 doc-counts into the gather-log; trivially derivable).

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
  - **4-4d — Daily gather + numeric scrape + cross-run dedup: DONE, merged to `main` (`f5f585c`, local).** Suite
    357/3. The input firehose: cross-run dedup-vs-store (L1 `SeenDocIndex` pre-brain doc dedup by URL+content-hash +
    L2 finding-level NEW/UPDATE/DUPLICATE post-gate, tolerance-based, intra-batch collapse) in
    `gpu_agent/gathering/dedup.py` (reads only, writes no page/number); CLI wiring (`ingest --dedup-store`+`--as-of`
    L1; new `wiki-dedup` subcommand L2); daily gather mode + numeric scrape skill edits (Part 22 honest —
    gatherer→frozen extract/gate; paywalled labeled `estimate`/never fetched). Opus final "Ready to merge: Yes";
    preview-confirmed LIVE. Additive; frozen + `normalize_documents` + all wiki modules byte-unchanged. ← **firehose done.**
  - **4-4c — resume here (SPEC + PLAN written/committed `7473ff3`/`256d4df`, spec USER-APPROVED, not yet built).**
    ← **run SDD on the 4-4c plan `2026-07-01-discovery-lifecycle.md`.** 5 TDD tasks → 381/3. **Scope split this
    session:** 4-4c = the **pure-code lifecycle engine** only (promotion via persist+corroborate + non-destructive
    pruning of `stale` provisionals + quarantine filter/report/guard) in `gpu_agent/wiki/lifecycle.py` + a
    `wiki-lifecycle` CLI. The **brain-driven discovery half** (theme-page creation + `explore` budget + off-registry
    discovery + bounded rabbit-holing) is **DEFERRED to its own later sub-project.** Additive; frozen + all wiki
    modules byte-unchanged; no new `status`/`LogEvent.kind`.
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
