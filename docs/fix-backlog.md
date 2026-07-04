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
  id, digit, or quarter/qtr/month/week/cycle). BUILT on branch f6-eval-harness: harness (gpu_agent/evals/ + eval CLI), 18-case golden set, hash-pin gate test, run-eval skill; spec docs/superpowers/specs/2026-07-04-f6-eval-harness-design.md; pending ONLY the Task-10 live baseline run (held until F67 lands). *(Feature track)*
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
- [x] **F52 — Vintage-scoped finding ids** (born from the sub-project-5 integration gate,
  2026-07-03 daily cycle). Finding ids are `docId-<n>` and docIds derive from the URL, so a URL
  re-gathered on a later day (a daily price page, a re-excerpted news article) reuses prior-cycle
  finding ids; when content differs, the append-only FindingStore's collision check fails loud in
  `route_findings` (observed: `www-digitimes-com-f88ca4e6-1`, `lambda-ai-845323fc-1`). L1's
  url+hash known-check cannot catch it because gatherer excerpts vary run-to-run. Scope the finding
  id (or docId) by asOf/vintage, or make L1 url-aware for static-content sources. The 2026-07-03
  cycle worked around it with a logged wiki-ingest exclusion (`work/daily-2026-07-03/
  ingest-exclusions.json`); scorecard path unaffected. *(DONE 2026-07-03: vintage-scoped
  docIds at the gather seam — `{slug}-{digest}-{asOf}`; `ingest --as-of` now required;
  finding ids inherit via the existing `{docId}-{n}` stamp; L1 url+hash unchanged, so
  unchanged content is still skipped cross-day. Spec
  docs/superpowers/specs/2026-07-03-f52-f53-f54-small-fixes-design.md)*
- [x] **F53 — Cross-cycle indicator consistency for price rows** (born from the same gate). The
  07-02 extraction labeled marketplace price levels `D6`; 07-03's labeled them `gpuSpotPrice` —
  both registered price indicators, so the F49/F51 per-series price track finds 0 matched series
  across the two cycles and PMI renders `—`. Pin ONE indicator id per price-source class in
  extraction guidance (or normalize at price-track level) so day-over-day deltas can ever compute.
  *(DONE 2026-07-03: both halves — the extractor seam rejects a measured price-side row whose
  value.unit != the registered canonical unit (catches the mislabel AND free-text unit drift,
  loud → re-dispatch), and `extract --emit-prompt` lists the registry's price-side ids +
  canonical units, F55 pattern. tests/test_extractor_price_unit.py)*
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
- [x] **F54 — Seed thesis triggers should pass the gate heuristic they will be judged under**
  (born from the same gate). Two committed seed triggers (`supply-constraint-binding`,
  `custom-asic-substitution`) name no observable under the thesis gate's v1 heuristic; the brain
  echoing them back verbatim was correctly rejected and had to reword (e.g. "lead times" does not
  match the id `leadTimes`). Either upgrade the seed data's trigger prose to heuristic-passing
  form, or document that seeds are grandfathered DATA and only judgments are gated. One-file data
  fix + a seed-lint test. *(DONE 2026-07-03: the two triggers reworded to heuristic-passing form
  — semantics preserved, observables named ("2 consecutive quarters");
  tests/test_seed_thesis_lint.py locks every seed trigger + depth field. Live store book
  untouched: history.jsonl's seeded event embeds the entries.)*
- [ ] **F56 — Validate `--as-of` shape at the seams** (born from the F52/F53/F54 final review,
  2026-07-03). `--as-of` is required everywhere but any non-empty string is accepted, and F52 now
  embeds it in doc ids → snapshot + FindingStore filenames; a fat-fingered `2026/07/03` would mint
  a path-unsafe id. Pre-existing convention (asOf already flowed unvalidated into the dedup index
  and wiki stamps; the skills always pass ISO dates), so defense-in-depth only: validate
  `^\d{4}-\d{2}(-\d{2})?$` once at the seam. Also fold in two deferred cosmetic minors from the
  same review: the seed-lint depth-fields comment overclaims "mirrors gate rule 3" (rule 3 doesn't
  check statement), and `build_system(price_indicators=[])` renders a malformed trailing "shown: ."
  sentence (unreachable while the registry has price-side indicators). *(Next wave — tiny)*

---

## From the 2026-07-03 freshness & exec-gap review (F57–F65)

> Source: three parallel deep explorations (design docs, live-output source audit, gather
> fan-out trace) prompted by the observation that briefs lean on lagging 10-Q data. Evidence,
> verified against the live store:
>
> - Flagship `store/chips.merchant-gpu/2026-07-v1.json`: 72 findings, **32 (44%) from the
>   Apr–May Q1 earnings cycle** (10-Q + releases + transcripts, 6–10 weeks stale at run time).
>   The only sub-week evidence is 12 weight-0 vendor price levels. Zero fresh headlines back any
>   of the six dimensions; the Apr-26 NVDA 10-Q is the sole primary/high-confidence evidence.
> - `work/live-2026-07/gather-log.json`: the 20-doc cap tripped in round 2 with 60+ fresh leads
>   logged "not chased" (TechCrunch Anthropic–Samsung 2nm, Tom's Hardware ASIC roundup, NVIDIA
>   blog posts); `open-web-asic` and `open-web-gpu-share` ended "not-covered".
> - The standard live gather has **no news/headline slice at all** ("news" appears once in the
>   skills, inside Daily mode) and seeds filing URLs first; the recency window is Daily-only.
> - The daily runs DO capture fresh signal (`store/findings/`: Anthropic–Samsung 2nm, NVIDIA
>   vendor-financing, Digitimes 2H26 order boom) — but the standard live path never reads the
>   wiki/findings store back (`run-cycle/SKILL.md:219`), so the flagship re-derives from its own
>   ≤20 docs and discards it. Smoking gun: `vendor-financed-demand-circularity` was proposed
>   from the July-1 NVIDIA newsroom announcement in the morning daily and demoted to conviction
>   low by the evening flagship **the same day** ("no primary support") — even though the
>   evidence is NVIDIA's own official post, stamped secondary because the primary allowlist is
>   just `sec.gov,investor.nvidia.com`, narrower than the charter's "filings, official posts".
>
> Exec-lens verdict: the brief reads as a well-organized summary of last quarter's earnings
> season, not an intelligence product. F57–F61 make it **current**; F62–F65 make it a
> **product**. Priority order (user-approved 2026-07-03, amended same day after report
> reconciliation): **step 0 = the F6-second-half rubric eval → F62 → F63 → F57/F58/F59 → F60 →
> F64 → F65 → F66**, with F61 shippable immediately (cheap, independent). Roadmap items
> surfaced by the same review (more categories, layer tier, Main roll-up) are not re-logged
> here — they are the existing deferred build.
>
> **Reconciled 2026-07-03 with the deep-research report**
> (`docs/2026-07-03-agent-best-practices-research.md`), which independently converged on the
> same gather-aim diagnosis. Adopted: **step 0 is the eval harness** (F6 second half / Action
> Item 1's Depth Bar, scoped as ~20 recorded-cycle cases graded by a brief rubric — it gates
> every prompt change in F57/F58); the evidence-sufficiency gate folds into F63; Brier scoring
> folds into F64; the citation-audit pass is F66. Graphiti = architecture reference for F24
> when it runs (its benchmark claims are refuted — see report §7). **Considered and REJECTED
> (user-approved 2026-07-03 — do not resurrect without new evidence):** (a) the SEC EDGAR
> structured pipeline / sec-api.io spend — it deepens the filings strength while the leading
> pipeline is the weakness; only F59's tier-classifier fix survives; (b) the
> search-API/scraper-stack benchmark (Tavily/Exa/Firecrawl…) — the headline gap is aim +
> doctrine, not fetch tech (the gatherers found the right stories; the system didn't chase or
> use them); revisit only if fetch failures remain the binding constraint after F57/F58.

### Fixes (bounded — lane-style)

- [ ] **F57 — Headline + forward-signal slices in the standard gather.** Round-1 seeds in
  `.claude/skills/gather-category/SKILL.md` contain no news angle; the only open-web query is
  one `"<entity-names> <source.label>"` per free-web source, and the entity×metric slices
  append "latest official filing / 10-Q / 10-K / investor relations". Add per-entity headline
  slices ("<entity> news / announcements past N days") and forward-signal slices (guidance
  revisions, lead-time drift, design wins), **interleaved with — not after — the filing URL
  seeds**, and partition `maxDocuments` into per-class floors (filing / news / forward) so
  filings cannot starve the open web. Skill prose + manifest data; the gather-log's coverage
  classes prove the fix. Two additions adopted from the research report's companion diagnosis:
  **cap price-page fetches at 2–3 per cycle** (the class floors set news/forward minimums; this
  sets the price-class maximum — dailies currently burn ~half their findings on weight-0 price
  scrapes), and **stop re-fetching already-seen filings mid-quarter** (thread the L1 seen-doc
  filter, today daily-only, into the standard live path for filing URLs, or skip known-hash
  filing seeds).
- [ ] **F58 — Recency window in live mode.** `recencyDays`, "since <date> / past week"
  qualifiers, and the date-window lead drop exist only in Daily mode; the standard live path
  has no freshness bias at all — which is how a 2026-07 flagship's freshest substantive doc was
  an April filing. Add a live-mode recency dial (wider than daily's 7, e.g. 45 days; filing
  seeds exempt) applied to seed queries and the on-topic filter.
- [ ] **F59 — Primary allowlist matches the charter's definition of primary.** Charter says
  primary = "filings, **official posts**", but ingest stamps primary only for
  `--primary-sources sec.gov,investor.nvidia.com` (gather-category SKILL.md:114; `cli.py:590`
  defaults to `sec.gov`). So `blogs.nvidia.com`, `nvidianews.nvidia.com`, `ir.amd.com`,
  `intc.com` — the vendors' own announcements — land secondary → confidence-capped → "no
  primary support" demotions for claims the vendor itself made. Extend the allowlist to
  official IR/newsroom domains, driven per-category from the manifest's source inventory
  instead of a hardcoded flag value. Regression case: the July-1 vendor-financing announcement.
- [ ] **F60 — Let fresh signal score.** Every fresh-cadence indicator is excluded from
  DMI/SMI: `gpuSpotPrice`/`D6` are `side:"price"`, `designWins` is `side:"structural"` (both
  skipped by `scoring.py`'s dmi_smi_contribution); `leadTimes` scores but its deep source is
  paywalled; and the two "leading" scoring indicators (`rpoBacklog`, `vendorRevenueGuidance`)
  are themselves 10-Q/earnings-sourced. Result in the flagship: outlook ran 5 findings vs
  momentum's 34 with `smiContribution: 0.0`. Give the leading set real weight in
  `registry/indicators.json` and/or admit a news-sourced leading indicator. **Frozen-contract
  caveat:** registry-weight changes are DATA and safe; any `scoring.py`/side-semantics change
  ships only as a versioned migration (Part 33), never piecemeal.
- [ ] **F61 — Staleness & coverage banner; honest confidence label.** The brief renders
  "confidence: high (self-consistency over 3 samples)" — vote agreement, not evidence currency
  — atop evidence with a ~6-week median age, while the gather-log quietly records
  TrendForce / SemiAnalysis / channel-checks as not-covered. Render an evidence-vintage line
  (median + oldest evidence date vs `asOf`, share older than N weeks) and the coverage gaps in
  the brief header, and relabel the confidence basis. `report.py` only — pure projection,
  replayable for $0.

### Features (per repo convention: brainstorming → spec → plan, own sub-project — not lane work)

- [ ] **F62 — Flagship consumes the daily store.** Daily mode WRITES fresh findings into the
  wiki (`wiki-ingest`, run-cycle SKILL.md:209) but the standard path never READS the wiki or
  `store/findings/` back (SKILL.md:219): the monthly brief is a projection of one cycle's ≤20
  docs, so everything the dailies learn is discarded at exactly the moment someone reads the
  output. Make the accumulated store a first-class input corpus to flagship extraction /
  judgment / thesis, demoting the web gather to top-up. **Highest-leverage item of this
  review.** Interacts with F52 (vintage-scoped ids) and L2 dedup.
- [ ] **F63 — Corroboration doctrine for secondary evidence.** Secondary evidence is
  confidence-capped at medium (extraction prompt + gate F2e) and secondary-only findings may
  not move headline status (Part 37) — so no quantity of independent open-web reporting can
  move status or conviction until a filing confirms it. The desk resolves at filing cadence;
  the exec decides at headline cadence. Amend the doctrine: **N independent secondary sources
  (distinct publishers, not syndication) within the window may move status/conviction one
  bounded step**, logged with the corroboration set; the next filing remains the confirm/deny
  checkpoint. Touches charter Part 37, gate rule F2e, thesis judging — a charter amendment,
  handled with migration discipline. **Counterweight (adopted from the research report §3,
  MAST Insight 3 — same spec, ships together):** a deterministic **evidence-sufficiency gate**
  — "is there enough fresh, corroborated evidence to justify *changing* the binding constraint
  / a dimension rating this cycle?" — so corroborated news can move ratings and insufficient
  news cannot. Loosening without the tightening half reintroduces the whipsaw the anti-whipsaw
  machinery exists to prevent.
- [ ] **F64 — Trigger-first daily brief.** The thesis book's falsifiable triggers are the one
  asset an exec cannot get from a news terminal, but the daily output leads with findings and
  trigger matching stays implicit inside judging. Lead the daily brief with a trigger-watch:
  which standing theses' `falsifiableTrigger`s did today's findings touch, which conviction
  moved, and why. Render + a thesis-engine step. **Include Brier discipline (adopted from the
  research report §5):** log every thesis judgment as a probabilistic call and Brier-score it
  as triggers resolve — conviction language earns a track record instead of assuming the
  judgment is calibrated.
- [ ] **F65 — "So what for TSMC" section.** The charter's north star is a prioritized
  recommendation, but the brief states everything market-facing and draws no implication even
  where it concludes TSMC is the binding constraint of the category. Add a judgment step +
  render section translating category state into TSMC decision variables (wafer starts by
  node, CoWoS/SoIC allocation, N2 customer mix, pricing leverage, foundry-competitive events —
  e.g. Anthropic–Samsung 2nm). Per-category now; becomes the Main-tier roll-up input later.
- [ ] **F66 — Post-hoc citation audit pass (low priority).** Adopted from the research report
  §1: citation integrity is enforced at write time (the gate checks findingIds/excerpts), but
  nothing re-verifies the *finished* brief's claims against the findings they cite — the
  production pattern (Anthropic's Research system) runs a dedicated citation-verification
  stage after generation. Add a tool-less audit subagent (or deterministic excerpt-match where
  the claim is numeric) over the rendered brief that flags claims whose cited finding does not
  actually support them. Pairs naturally with F61's render surface. Do after the higher items —
  our write-time gating already covers the worst failure mode.
- [x] **F67 — The output contract: renderer structure + analyst voice. DONE (merged to main
  `b0e8061`, 2026-07-04; suite 828→873/3).** Executed via subagent-driven development from plan
  `docs/superpowers/plans/2026-07-03-f67-output-contract.md` (9 tasks, all task-reviewed; final
  whole-branch review found 1 Critical + 5 Important, all fixed and re-review-verified against
  LIVE store renders — daily and monthly both clean above the `── APPENDIX ──` divider).
  Delivered: `gpu_agent/reader.py` + `registry/acronyms.json` (label maps, allowlist, prose
  lint), `constraintLabel` (additive-optional), voice lint on `judge --recorded` AND
  `pipeline --recorded-judge` (live path) with per-sample indexing + `--no-voice-lint`,
  staleness banner + vote-agreement confidence label, single-reason BLUF with constraint noun,
  calls/why/board/what-moved speak statements + source counts + registry labels,
  `reader.label_ids_in_text` maps indicator ids to labels in "breaks if" display (book keeps
  ids per F54), section reorder + appendix fold + citation map + raw-index table below the
  fold, price dead-metric fold, `report --daily`, run-cycle session-output rule (F38-safe
  re-dispatch, composes with Step 7). Deviations recorded in the spec's 2026-07-04 section.
  Execution ledger + per-task reports: `.superpowers/sdd-f67/` (untracked scratch).
  Original scope, for reference: (1) `report.py` renders one fixed
  inverted-pyramid section order (staleness-banner header → ≤8-line BLUF with the constraint
  *named* via a new additive-optional `constraintLabel` → what-moved with honest empty states →
  compressed calls → why-tree → human-labeled demand/supply board → F65 slot → trust footer →
  appendix), no raw ids above the appendix, no duplicated paragraphs, dead metrics folded;
  (2) an analyst-voice guideline in the judgment/thesis prompt builders (3-sentence narrative =
  state/crux/watch-item, ≤2-sentence rationales, banned-id + sentence-cap **deterministic
  lint**, one re-dispatch then fail loud); plus a run-cycle session rule (final message = brief
  verbatim + ≤3-line run-health footer, logs by path only) and a shared daily shell (daily
  leads with what-moved; calls section becomes F64's trigger-watch when it lands). Absorbs
  **F61**; reserves **F65**'s slot. **Reader contract (user-directed 2026-07-03):** the reader
  is a TSMC executive — internal/doctrine/repo vocabulary is banned above the appendix (label
  map for tier/status jargon; index acronyms words-first), an industry-standard acronym
  allowlist is lint-enforced, brain prompts embed the stop-slop pattern rules (tool-less
  brains can't invoke skills), and the session runs stop-slop on its final message.
- [ ] **F68 — F67 follow-ups (born from the F67 final review, 2026-07-04).** Bundle of small
  deferred items, none merge-blocking: **(a)** thesis-prose deterministic lint (spec §2b thesis
  slice ships as prompt rules only; add a lint symmetrical to the judgment one — statement ≤1
  sentence, mechanism ≤1, ids only in `falsifiableTrigger`); **(b)** citation map renders only
  each finding's first evidence item — render all; **(c)** BLUF reconciliation note keys off
  `rating + smiContribution < 0` — key off `sdgiDirection`; **(d)** what-moved empty state
  duplicates the folded count with the pre-existing "lower-materiality items folded" line when
  both render — collapse to one; **(e)** `reader.label_ids_in_text` iterative substitution has
  a latent chaining fragility if a future registry label contains another id as a token (no
  collision today — add a registry lint or single-pass substitution); **(f)** pre-existing live
  thesis-store prose carries off-allowlist tokens (`MI`, `GB300`) — cleans up as entries are
  re-judged under the new prompts, or allowlist them if they persist.
- [ ] **F69 — The web-reach layer: pluggable external fetchers for the gather swarm.** Spec
  `docs/superpowers/specs/2026-07-04-web-reach-layer-design.md`, plan
  `docs/superpowers/plans/2026-07-04-web-reach-layer.md`. Data-driven registry
  `registry/web-reach-tools.json` (first tool `agent-reach`; the second github drops in as a
  data entry), a health-check preamble + gatherer-contract additions in `gather-category`
  (complementary to WebSearch/web_fetch; secondary tier; chase-to-primary + cross-reference),
  doctrine appended to charter **Part 37**, operator doc `docs/web-reach.md`. Frozen core
  untouched; **no scoring change** (the "N publishers → one bounded step" corroboration math
  stays **F63**). User-approved 2026-07-04 (4 AskUserQuestion forks; charter home = append to
  Part 37, not a new Part).

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
