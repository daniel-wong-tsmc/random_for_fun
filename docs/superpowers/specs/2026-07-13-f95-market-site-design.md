# F95 — Three-tier market site on Cloudflare Pages (design)

- **Date:** 2026-07-13
- **Status:** Design complete, user-approved in an interactive session. Category tier is
  **build-now**; layer and market tiers are **contract-only** (pinned here, built later).
- **Provenance:** every decision below (S1–S8) is **user-approved 2026-07-13** in an interactive
  brainstorm (AskUserQuestion answers + per-part design approval). No AFK-defaults. See §11.
- **Inputs:** the F78/E1–E7 executive-brief format spec
  (`2026-07-11-executive-brief-format-design.md` — the top band, alert ladder, "words not raw
  indices" E2 decision); the 2026-07-06 dashboard design (`2026-07-06-merchant-gpu-dashboard-design.md`
  — plain-language machinery, scorecard loaders); `docs/taxonomy.json` (5 layers, 34 categories,
  category → layer → market rollup end-state); the F65 implication lane (FOR TSMC section,
  currently parked on its eval re-gate).

---

## 1. Problem

The desk's outputs (daily brief, one-file dashboard) serve one category and live in the repo.
The reader persona is a non-technical executive (TSMC). There is no web surface, no page for the
layer or whole-market tiers, and no way for a reader to follow a verdict back through the
calculation to the evidence. The user wants: a Cloudflare Pages site; on each page (category,
layer, market) one or more KPIs at the top (categorical or numerical); at the bottom an
explanation of why each KPI reads the way it does; and a drill-down from any KPI to how the
calculation came to be.

## 2. Decisions (all user-approved 2026-07-13)

- **S1 — Scope split.** Category page: designed AND built now. Layer + market pages: computed
  rollups (no new brains), **designed/pinned here, not built now**. Real layer/market agent
  brains explicitly rejected for now (1 of 34 categories live).
- **S2 — Top band = E2 tiles + ONE number.** The category page top carries the brief's E2 band
  (alert dot with "(was X)", Demand/Supply/Gap word tiles, binding-constraint line) **plus one
  numerical tile** — the featured metric (S3). One structure, both renders (E1) extends to this
  site: page and text brief must tell the same story.
- **S3 — Featured metric is dynamic, library-backed, deterministically selected.** A registry
  of candidate metrics; each build picks ONE by a pure projection rule (§4). No brain call. The
  page always states why the shown metric was picked.
- **S4 — Drill-down = full trail to evidence.** Every KPI links to a "how this was computed"
  page: components + rule/weights → the findings that moved each component → each finding's
  evidence (publisher, date, primary/secondary tier, one-line statement, source link when one
  exists). Three levels, all pre-rendered from stored artifacts.
- **S5 — Public URL.** Plain public Cloudflare Pages site (gating via Cloudflare Access
  considered and declined). **Launch precondition:** the open "repo rename before TSMC-branded
  exposure" gate must be settled before first deploy (§7). The repo itself may stay private —
  Pages deploys from private repos; it is the *content* that becomes public.
- **S6 — Architecture: static, pre-rendered, commit-then-serve.** The existing deterministic
  Python generator (`gpu_agent/dashboard/`) grows a multi-page site builder emitting a `site/`
  folder. run-cycle rebuilds and commits `site/` with the run's artifacts; Cloudflare Pages
  serves the committed folder with **no build step**. Browser-rendered app and Pages-CI builds
  considered and declined.
- **S7 — Rollup honesty.** Every rolled-up KPI carries a coverage chip ("computed from N of M
  categories"); below 50% coverage the page shows an "early — most of this isn't measured yet"
  banner. Member disagreement is shown ("Mixed across categories"), never averaged away.
- **S8 — Degrade honestly, never error.** Missing inputs shrink the page (§8); a rendering
  problem fails the build/tests before commit, never the live page.

## 3. Part A — the category page (build now)

Anatomy, top to bottom (breadcrumb `MERCHANT GPU · Chips layer · AI market` links up when those
pages exist; until then plain text):

```
MERCHANT GPU · Chips layer · AI market          as of 2026-07-13
● YELLOW (was GREEN)                    [How was this decided?]

┌──────────────┬──────────────┬──────────────┬───────────────────┐
│ DEMAND       │ SUPPLY       │ GAP          │ WORTH WATCHING    │
│ Strong ▲     │ Tight ▼     │ Widening ⚠   │ GPU rent $2.31/hr │
│ (was Firm)   │              │              │ ▼ 8% this month ~ │
└──────────────┴──────────────┴──────────────┴───────────────────┘
  [how?]         [how?]         [how?]         [why this number?]
Main limiting factor: HBM memory scarcity

WHAT CHANGED            since yesterday / last week / last month
FOR TSMC                rendered from the F65 implication artifact when present
THE TOP CALLS           top 5 by importance; the rest one line each
WHY IT READS THIS WAY   the bottom explanation block (§3a)
Appendix links          raw indices · all findings · run history
```

- **Sources are existing artifacts only:** the scorecard (`store/<category>/`), the change
  report / AlertState (F78 stage 6), the thesis calls, the price feed, and the F65 implication
  artifact (`store/implications/`) when present. The site builder is a pure renderer — no new
  judgment, no LLM calls, no wall-clock (all dates from `asOf`).
- **FOR TSMC:** E4 excluded this from the *text brief's* 2026-07-11 layout; F65 has since added
  a FOR TSMC section to the brief renderer on its branch. This page includes the section when
  the artifact exists and omits it otherwise. F95 does not depend on F65 landing.
- **Exec-plain rule:** everything above the appendix passes the existing acronym/voice lint;
  labels go through the dashboard plain-language dictionary.

### 3a. WHY IT READS THIS WAY (the bottom explanation block)

One short plain-English paragraph per top-band element, in tile order:

- **Alert dot:** which ladder rule fired (rendered from AlertState's rule hits), what event
  tripped it, prior color, and the anti-flapping note when it applies.
- **Each word tile:** why the band word is what it is — the band scale position plus the
  dimension/categoryStatus rationale already stored on the scorecard.
- **Featured metric:** the selection reason (§4) and a one-line "how to read this" from the
  metric library.
- **Trust notes:** evidence freshness and thin spots (the brief's trust footer, same source).

## 4. Featured metric — library + deterministic selector

- **Library:** new data file `registry/featured-metrics.json`. Entry shape:
  `{id, label, plainLabel, unit, source, howToRead, staticPriority, alertRuleTags[]}` where
  `source` names a stored-artifact path (price feed series, index legs, scorecard fields).
  v1 entries: `$/GPU-hr` (price feed), gap score (with an explicit "early — about 5 weeks of
  history" honesty label until F79 lands), demand momentum, supply momentum.
- **Selector (pure projection, replayable, $0), first match wins:**
  1. an alert-ladder rule fired this cycle AND a library metric carries that rule's tag → that
     metric;
  2. else the library metric with the largest normalized change vs the prior cycle — each
     library entry declares a `scale` denominator; normalized change = |current − prior| /
     `scale` (ties → staticPriority);
  3. else staticPriority order (price first).
- The chosen metric id + reason are recorded in the built page ("shown because it moved the
  most this week" / "tied to today's alert") and in the build manifest, so every build is
  explainable and reproducible.
- **F79 note:** the library is data, not scoring — when F79's v2 indices land, entries update;
  the selector and page do not change.

## 5. Drill-down pages ("how was this computed?")

One small pre-rendered page per KPI per build, under `site/<category>/how/`:

- **Alert dot →** the four-color ladder in plain English; the rule(s) that fired with the
  triggering events and dates; prior color; the 2-calm-runs de-escalation rule when relevant.
- **Word tile →** the five-word band scale (marker on it) → the index leg behind it → what
  pulled it up/down: per-indicator contributions with their registry weights → the findings
  behind each contribution (statement, observedAt, direction, magnitude, mechanism) → each
  finding's evidence rows: publisher, date, primary/secondary tier, one-line statement, link
  when a URL exists.
- **Featured metric →** its source (e.g. the four rental-price providers), short history
  table, and the §4 selection trace.

All content comes from the scorecard + change report + registries. Wide tables scroll inside
their own container; pages are self-contained static HTML with only inline expand/collapse JS.

## 6. Part B — layer & market pages (contract-only, pinned)

Same skeleton as §3 at both tiers, plus a **member table** (one row per member with mini
dot + tiles, linking down). Reader's path: market → hot layer → driving category → evidence.

- **Rollup rules (computed, no brains):** alert dot = worst member color
  (RED>ORANGE>YELLOW>GREEN); Demand/Supply/Gap words = the modal band word among measured
  members, and when no strict majority exists the tile renders "Mixed across categories"
  (never averaged); binding constraint = the constraint named by
  the most members (ties → the worst-color member's); featured metric = the member pick with
  the strongest selection score (rule-hit beats biggest-move beats priority).
- **Coverage honesty (S7):** mandatory chip on every rolled KPI; <50% coverage → the "early"
  banner. Today: chips = 1 of 7, market = 1 of 34.
- **Consumed shape:** a rollup page consumes only members' built page-data (the same values
  their own pages render) — category output needs **no rework** when these tiers are built.
- **WHY block at these tiers** explains the rollup mechanically ("YELLOW because merchant GPU
  is YELLOW and it is the worst of the 1 measured member").
- Build trigger: when ≥2 categories run, or on user go.

## 7. Build & deploy

1. **Site builder:** extend `gpu_agent/dashboard/` with a multi-page emitter (new module,
   reusing `scorecards.py` loaders, `plain_language.py`, `glossary.json`). CLI verb appended
   (append-only `cli.py`, same pattern as F65/F79). Output: `site/` at repo root —
   `site/index.html` (market placeholder → category redirect until Part B builds),
   `site/chips.merchant-gpu/index.html`, `site/chips.merchant-gpu/how/*.html`, shared CSS.
2. **`.gitignore`:** whitelist `!site/` (same pattern as `!store/implications/`).
3. **run-cycle:** one appended step — rebuild `site/`, commit with the run's artifacts ("a
   cycle that isn't committed didn't happen" already covers it). **Lane collision flag:** F88
   declares run-cycle SKILL prose ownership and "goes LAST of the prose-touchers"; F65 also
   touches run-cycle prose. F95's prose edit lands before F88 merges, or F88 rebases over it
   per its own rule — coordinate at merge time.
4. **Cloudflare Pages:** project connected to the GitHub repo; production branch `main`;
   build command **none**; output directory `site/`. Push → live in under a minute. The
   `*.pages.dev` subdomain name is part of the exposure decision below.
5. **Launch preconditions (user gates, before FIRST deploy — the site can be built and
   committed before these are settled):** (a) the open repo-rename / TSMC-branded-exposure
   decision (public site content includes the FOR TSMC framing); (b) the Pages project +
   subdomain naming call.

## 8. Degradation (never error, never pretend)

- No prior run → tiles render without "(was …)".
- Price feed absent → the selector falls down the library; library empty → the featured tile
  is omitted (band renders 3 tiles).
- FOR TSMC artifact absent → section omitted.
- Older scorecards missing fields → "not recorded this cycle" (existing dashboard pattern).
- Rollup with zero live members → the page renders the coverage banner and member table only,
  no fabricated tiles.

## 9. Testing

- **Golden pages:** byte-identical renders from fixture scorecards (category page + each `how/`
  page class), including the no-prior-run / no-price / no-implication degradations.
- **Selector truth table:** rule-tag hit beats biggest-move beats priority; tie-breaks; empty
  library.
- **Rollup truth table (written now, exercised when Part B builds):** worst-color-wins,
  disagreement rendering, coverage chip/banner thresholds, zero-member case.
- **Link integrity:** every `[how?]` href resolves to an emitted file.
- **Lint:** all above-appendix text passes the acronym/voice lint.
- **Invariants:** no wall-clock; renderer-only — **no emitted brain-prompt bytes change (F6 pin
  stays green)**; frozen core untouched; existing `docs/dashboard.html` builder keeps working
  until the site supersedes it (its retirement is a later, separate call).

## 10. Non-goals

- Real layer/market agent brains (rejected for now, S1).
- Ask-the-desk query box / any backend or Workers code.
- Client-side rendering framework (rejected, S6).
- Changes to the text-brief renderer, gather, scoring, or any brain prompt.
- Building Part B now; retiring the one-file dashboard now.
- Waiting on F65 or F79 — the page degrades/upgrades around both.

## 11. Decision provenance

S1–S8 answered by the user 2026-07-13 via AskUserQuestion in an interactive brainstorm
(rollup-source, top-band, featured-metric-dynamic, drill-depth, access, architecture), plus
per-part design approvals ("Part 1 looks right", "Part 2 — write the spec"). The featured-metric
selector mechanics and rollup rule details are the assistant's proposal accepted within those
part approvals. Public-URL (S5) was chosen over the assistant's gated-access recommendation —
recorded per F76 vocabulary as user-approved, with the rename-gate precondition attached.

## 12. Backlog impact

- **F95:** NEW entry (this spec is the record). Category tier build-now; Part B contract pinned.
- **F65:** unchanged (parked on its eval re-gate decision); this page consumes its artifact
  opportunistically.
- **F79:** unchanged; featured-metric library entries update when v2 indices land.
- **F88:** sequencing note only (§7.3) — F95's run-cycle prose edit precedes F88's merge.
- **Repo-rename gate:** now blocks F95's first deploy specifically (was general housekeeping).
