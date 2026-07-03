# Fix Backlog — from the 2026-07-02 full-repo review

> Source: three parallel deep reviews (core pipeline, temporal store/brief, ops/docs) plus direct
> inspection of the live `store/chips.merchant-gpu/2026-06-v6.json` scorecard. Suite green at
> review time: **417 passed / 3 skipped @ c5358bf**.
>
> **Must-have** = corrupts numbers or judgments, violates a binding doctrine rule, loses data, or
> lets fabricated/injected content reach a rating. **Should-have** = scale-out readiness,
> robustness, hygiene, presentation. Descending priority within each bucket.
>
> Execution model (lanes, waves, merge protocol) is at the bottom — fixes are tagged with their
> lane. Frozen-contract items (`gate.py` / `scoring.py` / Finding schema) ship as **one versioned
> v1.2 migration** (charter Part 33), never piecemeal.

> **Wave 2 MERGED 2026-07-02** (main d933b7e, suite 626 passed / 3 skipped): lanes F (F18, F29,
> F33, F34, F49 Price Momentum overlay, F51 per-series price dedup incl. the cross-cycle fix), G
> (F41 minus the frozen schemaVersion-default bump - explicitly skipped, F42, F50, F26-cli), H
> (F26 personas, F27 frontier-closed runnable - note: the old empty-weights-zero-indices claim was
> stale, registry-weight fallback meant indices were never zero; the real deliverables are explicit
> weights + manifest + persona + runnability pins), I (F28 host-aware matching + auditable waivers,
> F40 signpost), J (F39 rating anchors). Reviews: opus on F, sonnet on G/H/I, controller on J.
> Controller wiring: persona threads via --persona/personaLabel (d933b7e).

> **Wave 1 MERGED 2026-07-02** (main f1c0835, suite 516 passed / 3 skipped): the contract v1.2
> migration (F2, F3, F7, F8, F9, F16, F17, F21, F36, F37 - shadow-run + replay v7-v12 in
> docs/migrations/2026-07-contract-v1.2.md) and lanes C (F19, F20, F35, F38), D (F10, F11, F12,
> F13-report, F22-cli), E (F14, F15, F30, F31, F32, F13-wiki, F22-lint). Reviews: opus on the
> contract diff, sonnet on C/D/E; every stream READY-TO-MERGE with fixes applied where demanded.

## Must-have

- [x] **F1 — Protect the canonical store.** `store/` is gitignored; all history is one
  `git clean -xdf` from gone. Commit it or add a versioned backup. *(Wave 0 — DONE f7ace81:
  canonical paths tracked; scratch subtrees stay ignored)*
- [x] **F2 — Evidence-integrity gate bundle** (`gate.py`, `extraction/`): **(a)** `observed`
  requires ≥1 evidence (today `gate.py:7-14` only checks measured); **(b)** `evidence.excerpt`
  must appear in the source document content; **(c)** `evidence.url == doc.url`;
  **(d)** `evidence.tier` code-stamped from the document tier, stripped from model output;
  **(e)** secondary-only evidence → confidence ≤ medium enforced in the gate. Closes the
  fabrication/injection path. *(Lane A)*
- [x] **F3 — Enforce the Part-37 headline-protection rule.** A dimension rating resting solely on
  secondary sources must be confidence-capped + flagged. v6's `bottleneck` and `moat` each rest on
  one blog yet report `grounded` / `confidenceCap: null` (`pipeline.py:60-76`). *(Lane B)*
- [x] **F4 — Wire memory into judgment. DONE (sub-project 5-1, merged 7197226).** `gpu_agent/memory.py`
  builds the prior-state bundle (prior scorecard summary, thesis book, wiki states, price series, cycle
  chronology) and renders the fenced MEMORY block; injected additively into the judge emit path
  (`judge --emit-prompt --store`) and the thesis prompt — byte-identical prompts when absent. Verified
  live in the 2026-07-03 daily cycle: the judge received MEMORY and judged direction vs the 07-02 prior
  (category direction steady vs prior improving). *(Feature track)*
- [x] **F5 — Anti-whipsaw check. DONE (sub-project 5-1, merged 7197226).** Code-owned in
  `gpu_agent/thesis.py` apply engine: a secondary-only reversal defers as a pendingChallenge
  (`CHALLENGED — pending confirmation ⚠` in THE CALLS); primary evidence or a second consecutive
  same-direction signal applies; conviction moves ≤1 level per applied cycle; applied `broken` retires.
  All branches test-pinned (scenarios a–k). *(Feature track)*
- [ ] **F6 — Depth Rubric + Golden Set** (recorded Action Item 1). **HALF DONE (sub-project 5-1):**
  depth fields (mechanism / falsifiableTrigger / sensitivity) are now carried on every thesis judgment
  and GATE-ENFORCED (non-empty + trigger must name an observable — v1 heuristic: registered indicator
  id, digit, or quarter/qtr/month/week/cycle). REMAINING: the rubric-grading golden set + regression
  gate for every prompt change (charter Part 24) — a separate later sub-project. *(Feature track)*
- [x] **F7 — DMI/SMI entity shadowing.** `scoring.py:25-30` buckets by `indicatorId` only; NVDA and
  AMD erase each other per indicator. Bucket by `(entity, indicatorId)`. *(Lane B, contract v1.2)*
- [x] **F8 — Price-indicator handling — DECIDED 2026-07-02: overlay-only.** Flip D6 to
  `scoring: false` (price findings never feed DMI/SMI, per charter v1.1); static levels with
  `trend: unknown` carry polarity 0 — levels without a baseline are not momentum. Follow-ups:
  visible Price Momentum Index = **F49** (Wave 2); change-based price scoring deferred until F12
  provides price history and F6 can grade the judgment. *(Lane B + extraction guidance in Lane A)*
- [x] **F9 — Deterministic anchor polarity track.** `briefing.py:23` lets the last finding's
  indicator pick the dimension's track (order-dependent gate outcomes). Define per dimension at
  registry level. *(Lane B, contract v1.2)*
- [x] **F10 — Corroboration merge + dispersion emission.** Same (entity, indicator, value, period)
  from two sources = one finding with two evidence entries (v6 stores NVIDIA's $75.2B twice);
  conflicting same-key findings must set `dispersion` instead of recency-collapse
  (`gathering/dedup.py:171-189`). *(Lane D)*
- [x] **F11 — Recorded-replay alignment.** The live path IS `--recorded`; a failed validation
  consumes the *next* document's answer → silent cross-attribution (`llm/recorded.py:11-14` +
  `cli.py:209-214`). Pair answers to docs explicitly; hard-fail on length mismatch. *(Lane D)*
- [x] **F12 — L1 dedup: content-hash before URL; record "seen" only after extraction commits.**
  Stable-URL price pages are dropped forever after first sight (`dedup.py:74-79`); crash
  pre-extraction permanently loses docs (`dedup.py:105`). *(Lane D)*
- [x] **F13 — Fix the asOf-grain trap.** Month grain drops a second same-month ingest's
  contradictions (`wiki/ingest.py:142-145`) and empties intra-month diffs; day grain silently breaks
  `find_prior`'s regex (`report.py:37`). Validate the grain, key ingest events by run, make
  `find_prior` fail loud. *(Lane D + Lane E)*
- [x] **F14 — Gate the wiki enrichment channel.** `apply_enrichment` (`wiki/ingest.py:125-146`)
  writes LLM body/state/salience with no check that cited `[f-...]` ids exist and no numeric gate —
  the one path where un-gated claims reach the brief. *(Lane E)*
- [x] **F15 — Salience computed in code, never brain-invented.** The 4-1 spec forbids exactly what
  the shipped prompt asks (`wiki/ingest.py:11`); model salience currently drives materiality, decay,
  pruning, STORYLINES order. *(Lane E)*
- [x] **F16 — Injection hardening at extraction.** Escape/robustly delimit document content in the
  prompt fence (`extraction/prompt.py:32-34`); never fold system into user; dispatch extraction
  subagents tool-less. *(Lane A)*
- [x] **F17 — Vintage honesty validation.** `evidence.date` = publication date, not fetch date (v6
  is full of `2026-07-02` fetch stamps in a June scorecard); validate `observedAt`/date formats;
  flag future-dated evidence relative to `asOf`. *(Lane A)*
- [x] **F18 — `_traj_arrow` keyword bug.** "supply glut worsening" renders UP ▲ because
  `"up" ⊂ "supply"` (`brief.py:123-139`); make trajectory a constrained enum. *(Lane F)*
- [x] **F19 — Single-sample "unanimity."** A dimension in 1 of 3 samples gets high confidence with
  basis "1/1" (`judge.py:64-74`); require a real quorum. *(Lane C)*
- [x] **F20 — Propagate confidence caps upward.** A dimension driven by hypothesis/capped findings
  must inherit the cap; finding-level confidence is never consulted at aggregation. *(Lane C)*
- [x] **F21 — Impact quality gate.** Empty `targets`/`mechanism` pass; require non-empty and
  taxonomy-valid targets. v6's impacts are 100% self-referential — starving the future
  recommendation layer. *(Lane A)*
- [x] **F22 — Kill the silent drops.** `_pipeline` discards gate-dropped findings unlogged
  (`cli.py:277-280`); lint discards untagged-indicator lists and swallows exceptions
  (`lint.py:98-99,164-165,200,225`); report silently skips unreadable priors. *(Lane D + Lane E)*

## Should-have

- [ ] **F23 — Charter compliance matrix.** Clause → enforcement point → test; stops "binding"
  drifting into aspiration (would have caught F2/F3/F5). *(Feature track)*
- [ ] **F24 — Entity canonicalization + per-category namespacing.** `NVDA` vs `nvidia` fragments
  pages; `entity:amd` is global across future categories. Part 18/21 registry with aliases +
  category scoping before fan-out. *(Feature track)*
- [ ] **F25 — Wiki store performance + concurrency.** O(N) full-log re-reads per operation,
  O(pages²) health scans, `seq = len(read())` TOCTOU race — fatal at 34 concurrent categories.
  *(Feature track)*
- [x] **F26 — De-GPU the template.** "GPU market analyst" persona hardcoded for every category;
  `judge --category` defaults to merchant-gpu; `--primary-sources` defaults to sec.gov; skills
  hardcode the merchant-gpu assignment. Parameterize by assignment. *(Lane H)*
- [x] **F27 — Make `frontier-closed` runnable.** Empty weights (zero indices), no manifest, flat
  indicator namespace. Second category = the generalization proof. *(Lane H)*
- [x] **F28 — Coverage-gap matching.** Substring URL patterns produced false "required gaps"
  (10-Q via s201.q4cdn.com, BIS via www.bis.gov) that were waved off in free text. Indicator-level
  credit or mirror patterns; overrides become a structured, auditable field. *(Lane I)*
- [x] **F29 — Single-source ⚠ flag in the brief** (deferred 4-5 item) — v6 shows it can't stay
  deferred. *(Lane F)*
- [x] **F30 — Log lifecycle promotions.** `update_header` writes no event; registered/provisional
  flips are invisible to replayable history (`wiki/store.py:107-114`). *(Lane E)*
- [x] **F31 — Real corroboration for promotion.** Distinct free-text `evidence.source` strings count
  the same publisher twice (`lifecycle.py:56-65`); key by domain/publisher. *(Lane E)*
- [x] **F32 — Read paths must not write.** `wiki-lifecycle` propose calls `lint()` which appends a
  log event and can mint a "cycle," aging every page (`cli.py:152`); provenance-only events must not
  count as cycles for decay (`lint.py:127-128`). *(Lane E)*
- [x] **F33 — Bound brief growth.** STORYLINES renders every page forever; pruned pages never
  archive. Add an archived state or render cap. *(Lane F)*
- [x] **F34 — Recalibrate the materiality fold.** New secondary threads score 0.27 &lt; 0.3 threshold —
  structurally hides the discovery class the lifecycle exists to catch. Retune or document. *(Lane F)*
- [x] **F35 — Judgment citation coherence.** The judge can cite a momentum finding for a moat rating
  (`gate.py:43-47` checks existence only); validate `findingIds` against the dimension's indicator
  group. *(Lane C)*
- [x] **F36 — Tighten the anchor band; fix its label.** ±0.5 tolerance allows "Very strong" at
  −0.49 (`gate.py:30-35`); the "z=" message references a z-score that doesn't exist (`zscore()` is
  dead code — use it for trend-vs-blip or delete it). *(Lane A, contract v1.2)*
- [x] **F37 — Check `Finding.side` against the registry** — currently decorative; silent
  contradictions persist in stored data. *(Lane B)*
- [x] **F38 — Honest self-consistency.** All 3 judgment samples come from one subagent generation
  (correlated); sample independently, and move the vote spread out of `confidence.basis` into its
  own field. *(Lane C)*
- [x] **F39 — Per-dimension rating anchor definitions.** "Weak" bottleneck (built) vs "Very strong
  choke point" (charter Part 17 example): write the five-word definitions per dimension so two
  analysts pick the same word. *(Lane J)*
- [x] **F40 — Fix or delete `ClaudeCodeClient`.** Reads `message.text` (SDK uses content blocks),
  leaves tools enabled, zero coverage, not the path the skills use. *(Lane I)*
- [x] **F41 — Input robustness bundle.** Reject NaN; parse timestamps (lexical compare misorders
  mixed offsets, `scoring.py:14`); bump `Finding.schemaVersion` default to 1.1; validate wiki page
  ids/slugs (path escape, `wiki/store.py:82-84`); crash-recoverable `route_findings`. *(Lane G)*
- [x] **F42 — Hardcoded paths → config.** `registry/indicators.json` / `docs/taxonomy.json` are
  cwd-relative literals across the CLI. *(Lane G)*
- [x] **F43 — Move gather outputs out of `docs/`; reconcile `ingested/`.** 20 scraped JSONs beside
  the charter (the skill's `--out docs` example is the cause); duplicate folder missing
  `coverageGaps`; gitignore the artifacts. *(Wave 0 — DONE 839113b: skill writes to work/;
  artifacts archived under work/gather-2026-07-02/)*
- [x] **F44 — Refresh continuity docs.** HANDOFF.md instructs redoing the merged 4-5b;
  START-HERE.md describes the dead OAuth backend. *(Wave 0 — DONE 7b93be3)*
- [x] **F45 — Honesty overlay on `swarm-graph.html`.** Mark built vs deferred; today it presents
  all 34 agents + 3 tiers as existing. *(Wave 0 — DONE f173165: build-status overlay,
  BUILT/PARTIAL/DEFERRED badges + panel status + legend)*
- [x] **F46 — Run a real second cycle.** Sub-project 4's machinery has never executed against real
  state (no `store/wiki/`, no `seen_docs.jsonl`; v1–v6 are same-month reruns). Cheapest integration
  test available. *(Validation gate after Wave 1 — DONE 2026-07-02: live daily cycle →
  `store/chips.merchant-gpu/2026-07-02-v1.json` DMI +0.227/SMI +0.053, Δ vs the v1.2-replayed
  2026-06-v12; L1 index seeded, L2 dedup 9 new/8 dup, wiki 3 entity pages, lint 3 material.
  Surfaced F50 + F51 below.)*
- [x] **F47 — Retire or sync the stale doc tree** in `Documents\TSMC\ai4bi\ai_state_of_the_market`;
  pull `action-items.md` into this repo. *(Wave 0 — DONE c83ae83: action-items.md in-repo;
  external tree got a RETIRED.md pointer, nothing deleted)*
- [x] **F48 — Front door.** Real readme (and consider the repo name before anything is shown under
  TSMC branding). *(Wave 0 — DONE 86d0224: real readme with honest build status; repo RENAME
  remains a user call, flagged in the readme)*
- [x] **F50 — Run asOf must own the scorecard label** (born from the F46 gate). `Scorecard.asOf`
  comes from `assignment.asOf` (a committed fixture pinning `2026-06`), not the run's `--as-of` —
  the F46 daily cycle first wrote its scorecard as `2026-06-v13` (removed; re-run with a
  run-scoped assignment copy). Make the pipeline's `--as-of` override the assignment's, or
  fail-loud on mismatch. *(Wave 2, Lane G — cross-cutting robustness)*
- [x] **F51 — Finer dedup key for price series** (born from the F46 gate). L2 keys by
  `(entity, indicatorId)`, so every NVDA D6 row across providers and SKUs (B200 vs H100; Lambda vs
  CoreWeave vs Runpod) collapses to one rep + dispersion. The F49 price track needs a per-series
  key (SKU/provider) before it can chart anything. *(Wave 2, with F49 in Lane F)*
- [x] **F49 — Price Momentum Index overlay** (born from the F8 decision). Compute the price-side
  rollup in code as a third, clearly-labeled confirmation track beside DMI/SMI — displayed, never
  blended (charter Part 17's overlay, formalized). Needs the F8 polarity-0 rule already in.
  *(Wave 2, Lane F)*
- [ ] **F52 — Vintage-scoped finding ids** (born from the sub-project-5 integration gate,
  2026-07-03 daily cycle). Finding ids are `docId-<n>` and docIds derive from the URL, so a URL
  re-gathered on a later day (a daily price page, a re-excerpted news article) reuses prior-cycle
  finding ids; when content differs, the append-only FindingStore's collision check fails loud in
  `route_findings` (observed: `www-digitimes-com-f88ca4e6-1`, `lambda-ai-845323fc-1`). L1's
  url+hash known-check cannot catch it because gatherer excerpts vary run-to-run. Scope the finding
  id (or docId) by asOf/vintage, or make L1 url-aware for static-content sources. The 2026-07-03
  cycle worked around it with a logged wiki-ingest exclusion (`work/daily-2026-07-03/
  ingest-exclusions.json`); scorecard path unaffected. *(Next wave)*
- [ ] **F53 — Cross-cycle indicator consistency for price rows** (born from the same gate). The
  07-02 extraction labeled marketplace price levels `D6`; 07-03's labeled them `gpuSpotPrice` —
  both registered price indicators, so the F49/F51 per-series price track finds 0 matched series
  across the two cycles and PMI renders `—`. Pin ONE indicator id per price-source class in
  extraction guidance (or normalize at price-track level) so day-over-day deltas can ever compute.
  *(Next wave)*
- [x] **F55 — Emitted prompts carry the id vocabularies the gates enforce. DONE (session,
  2026-07-03).** Born from BOTH live cycles on the sp5 stack: each coordinating session had to
  hand the brains the valid taxonomy ids (extraction impact.targets) and the judge citation
  groups out-of-band, and each got them wrong first try — one full re-dispatch wave per cycle.
  Now `extract --emit-prompt` appends the taxonomy's category ids to the system prompt
  (`build_system(valid_targets=...)`, sourced from the same `taxonomy.categories` the gate
  checks), `judge --emit-prompt` appends a `<citationGroups>` block (code-computed per-dimension
  id groups + the six DIMENSIONS names, `build_user_prompt(include_groups=True)`), and the
  thesis SYSTEM states the v1 observable heuristic verbatim instead of letting the brain
  discover it by rejection. All default paths byte-identical (F26/F4 additive pattern);
  `judge_findings`' frozen internal path untouched. tests/test_prompt_vocab.py. *(DONE)*
- [ ] **F54 — Seed thesis triggers should pass the gate heuristic they will be judged under**
  (born from the same gate). Two committed seed triggers (`supply-constraint-binding`,
  `custom-asic-substitution`) name no observable under the thesis gate's v1 heuristic; the brain
  echoing them back verbatim was correctly rejected and had to reword (e.g. "lead times" does not
  match the id `leadTimes`). Either upgrade the seed data's trigger prose to heuristic-passing
  form, or document that seeds are grandfathered DATA and only judgments are gated. One-file data
  fix + a seed-lint test. *(Next wave — small)*

---

## Execution model — parallel lanes, 5 at a time

**The constraint that shapes everything:** superpowers' subagent-driven-development forbids
parallel implementers on one branch, and dispatching-parallel-agents requires disjoint domains with
no shared files. So parallelism comes from **file-ownership lanes, each in its own git worktree**,
each lane internally sequential.

**Decisions recorded 2026-07-02 (user-approved — do not re-ask):** (1) F8 = overlay-only now, F49
price track in Wave 2, change-based scoring later. (2) **Contract v1.2 approved as ONE migration:
Lanes A+B are a single coupled stream** (one worktree, `fix/contract-v1.2`) — so Wave 1 runs as
**four concurrent streams** (A+B, C, D, E). The migration must include a one-shot **shadow-run**
(old vs new scoring over the same stored findings; diff in the migration note) and a **replay**
(recompute the stored 2026-06 scorecards' indices under v1.2 as new versions, originals immutable,
so vs-prior comparisons stay continuous).

### Lane map

| Lane | Owns (no other lane touches) | Fixes |
|---|---|---|
| **Wave 0** (ops/docs, no code — run first, fully parallel) | docs, .gitignore, app/ | F1, F43, F44, F45, F47, F48 |
| **A — Evidence integrity** (contract v1.2 part 1) | `gate.py`, `extraction/`, `schema/finding.py` | F2, F16, F17, F21, F36 |
| **B — Index math** (contract v1.2 part 2) | `scoring.py`, `judgment/briefing.py`, `pipeline.py`, `registry/` | F3, F7, F8, F9, F37 |
| **C — Judgment aggregation** | `judgment/judge.py`, `judgment/prompt.py` | F19, F20, F35, F38 |
| **D — Gather/dedup/CLI robustness** | `gathering/`, `cli.py`, `report.py:find_prior` | F10, F11, F12, F13, F22 |
| **E — Wiki integrity** | `wiki/` | F14, F15, F30, F31, F32 |
| **F — Brief/report** (wave 2) | `brief.py`, `report.py` | F18, F29, F33, F34 |
| **G — Robustness bundle** (wave 2) | cross-cutting small fixes | F41, F42 |
| **H — Generalization** (wave 2) | prompts params, assignments, manifests | F26, F27 |
| **I — Coverage + backends** (wave 2) | `manifest.py`, `llm/claude_code.py` | F28, F40 |
| **J — Method docs** (wave 2) | rating anchor definitions | F39 |

### Protocol per wave

1. **Plan per lane** (superpowers:writing-plans): one short implementation plan per lane in
   `docs/superpowers/plans/`, tasks ordered, tests named. Lanes A+B jointly declare the
   **contract v1.2 migration** (Part 33): schema version bump, golden-fixture regeneration, one
   migration note.
2. **Worktree per lane** (superpowers:using-git-worktrees): branch `fix/lane-a` … `fix/lane-e`.
3. **Dispatch all 5 lane agents in one message** (dispatching-parallel-agents) — each agent
   executes its lane's plan sequentially inside its worktree: TDD, self-review, commit per task.
4. **Merge gate, sequential:** merge order A → B → C → D → E; rebase each onto the accumulated
   result; **full suite (417+) green before the next merge**; task-review each lane's diff at merge
   time (subagent-driven-development's reviewer step, applied per lane).
5. **Validation:** after Wave 1 merges, run F46 (a real live cycle) before starting Wave 2.

### What does NOT go in a lane

F4+F5 (memory + anti-whipsaw), F6 (depth rubric + golden set), F23 (compliance matrix), F24
(entity registry), F25 (storage scaling) are **features, not fixes** — each starts with
superpowers:brainstorming → a spec → a plan, executed with subagent-driven-development as its own
sub-project (the repo's existing sp1–sp4 pattern). Do not let a lane agent improvise these.
