# F78 — Daily, change-first market-state brief (design)

- **Date:** 2026-07-08
- **Status:** Design complete, awaiting implementation plan (brainstorming → this spec → plan → SDD).
- **Provenance:** every decision below is **user-approved 2026-07-08** in an interactive session
  (not AFK-default). See §11.
- **Backlog:** this is **F78** (`docs/fix-backlog.md`). It **delivers F64 and F77**, **supersedes
  F58's window rule**, and **absorbs part of F68**. It does **not** subsume F60, F25, F65, or F66.

---

## 1. Problem

Today the system ships two products:

- a **daily monitor** — a cheap, recency-windowed (7-day) "what's new" sweep, and
- a **monthly flagship** — the full six-dimension Market-State scorecard.

The monthly flagship reads stale evidence, and it gets worse each top-up. Measured on the live
store (run ref 2026-07-08):

- **Dailies are clean** (07-02/03/05/06: zero stale open-web evidence — the 7-day window holds).
- **The monthly accumulates staleness:** stale *secondary* evidence went 5 → 5 → 8 across
  2026-07 v2 → v3 → v4; the oldest item grew 170 → **320 days** (a NVIDIA product/spec page dated
  2025-08-22, freshly pulled into v4).
- **It changes ratings.** In v4, `strategicRisk` and `unitEconomics` (both stamped **high**
  confidence) rest ENTIRELY on stale evidence; the headline `momentum` ("Very strong, improving")
  is 3-of-4 supported by ~2-month-old earnings echoes; `competitiveStructure`/`moat` lean on AMD web
  content ~174 days old.

**Two root causes, neither is the threshold value:**

1. **The gather recency window is advisory skill prose.** The gathering agent keeps old-dated
   evergreen official pages by discretion (v4 logged 0 recency drops for the kept pages). There is
   no code that drops/flags a document by its real publication date.
2. **The corpus windows on the wrong date.** `gpu_agent/corpus.py::in_window` keeps a finding when
   its *cycle stamp* (`asOf`) is recent, never looking at the evidence's real publication date — so
   old-content findings ride forward and pile up.

**Caveat (not a bug):** a large share of "stale" is quarterly filings/earnings (49–64 days) —
inherently the freshest primary that exists. A market-state read legitimately uses them; the leak
is old *secondary* content and the corpus pile-up, not the quarterly cadence.

**User reframe:** the user runs the agent **every day** and expects the brief to lead with **new**
information and show **how things changed**, not restate the same standings.

## 2. Goals

- **One brief, run every day**, that leads with *what changed* across three horizons (since
  yesterday / last week / last month). Retire the separate "monthly" product.
- **Keep both the fresh gather and the corpus.** Reframe the corpus from "don't forget" to "the
  baseline we measure change against."
- **Age facts honestly** using the existing wiki decay, so a stale price fades fast and a fresh one
  wins, without hard-dropping anything.
- **Quick-glance metrics** the reader can scan in seconds — three tiers, each showing its **move**
  and its **age**.
- Stay **deterministic and replayable**; leave the **frozen core** untouched; keep the **eval pin
  green** (no brain-prompt changes).

## 3. Non-goals / out of scope

- **F60** — the index-scoring math (`scoring.py`, which indicators move DMI/SMI). Arguably more
  important once the brief is change-first, but it ships as its own versioned migration.
- **F25** — store performance. Not built here, but flagged: the daily brief reads the store at three
  lookbacks, so it matters more now.
- **F65** ("so what for TSMC") and **F66** (post-hoc citation audit) — separate items.
- **Recalibrating the exact half-life / pacing numbers.** We ship the *calendar-day mechanism* now;
  tuning the day-thresholds is explicitly deferred ("calendar day for now, recalibrate later").
- **Share price** — left out of the quick-glance for now (fundamentals like revenue/margin stay in;
  the ticker does not).

## 4. Decisions (all user-approved 2026-07-08)

- **D1 — One daily brief.** Retire the monthly product; all runs are **day-grain** (`YYYY-MM-DD`).
- **D2 — Keep fresh gather + corpus.** Both remain; the corpus is the change-detection baseline.
- **D3 — Point-in-time comparison.** Compare today's state to the stored brief from the **nearest run
  at/before** 1, 7, and 30 calendar days ago (not weekly/monthly averages). "Nearest at/before"
  makes it robust to skipped days.
- **D4 — Corpus ages via the wiki.** Stop the flat `asOf` window; surface corpus facts by the wiki's
  **effective salience** (decay) and lifecycle state (pruned/archived excluded).
- **D5 — Calendar-day measurement.** Aging (wiki decay) and thesis pacing move from *counting runs*
  to *calendar days derived from the `asOf` label*. Deterministic (a date label, not wall-clock).
  Exact day-thresholds are tunable, recalibrated later.
- **D6 — Fresh gather: 7-day sweep + logged discretionary pursuit.** The round-1 net is the last 7
  days; the agent MAY chase an older lead when it judges it worth it, and **records the age + a
  one-line reason** each time. Reworks F58 (replaces its 45-day hard-drop).
- **D7 — Change-first renderer.** Lead with three horizon change lines; say "unchanged since <date>"
  explicitly; tag carried facts with their real age. Delivers F64 (trigger-first daily) and F77
  (importance-ordered, consolidated, length-capped brief).
- **D8 — Quick-glance metrics: all three tiers** (§5.6). Share price out for now.
- **D9 — Price feed.** Read the local `gpu_agent/scrape_data/` CSVs; normalize to **$/GPU-hour**,
  **on-demand** term, **USA** region, instance-family → GPU-model map derived from the data. Price
  stays **display-only** (F8) — never feeds DMI/SMI.

## 5. Architecture

Four coupled components plus the quick-glance metrics and the price feed. Existing module
boundaries are respected; the frozen core is untouched.

### 5.1 Cadence — day-grain everywhere (D1)

- All runs use a **day-grain `asOf`** (`YYYY-MM-DD`); scorecards are `store/<category>/YYYY-MM-DD-vN`.
  The month-grain `YYYY-MM-vN` flagship chain is retired (existing month-grain scorecards stay as
  immutable history; nothing is rewritten).
- The scorecard schema already supports day-grain `asOf` (dailies use it), so **no schema change**.
- The run-cycle skill collapses to a single daily path (the standard/flagship "full" run *is* the
  daily run). "Daily mode" and "standard mode" merge; the differences become dials (caps), not two
  procedures.

### 5.2 Calendar-day measurement (D5)

The behavior-sensitive core. Today, "how stale" and "how fast may a thesis move" are counted in
**runs**. We re-express them in **calendar days computed from `asOf` labels** so behavior is
independent of run frequency.

- **Wiki decay** (`gpu_agent/wiki/lint.py`): `quiet_age` currently returns the count of distinct
  `asOf` cycles since a page's last material event; `half_life` returns a value in *cycles* from the
  indicator's cadence tag. Convert both to **days**: `quiet_age_days = period_end(as_of) −
  period_end(last_material_asOf)`; `half_life_days` mapped from cadence (daily → short, weekly →
  med, quarterly → long, in days). The decay formula `0.5 ** (quiet_age / half_life)` and
  `effective_salience = intrinsic × decay` are unchanged — only the **units** become days.
- **Thesis pacing** (`gpu_agent/thesis.py`): the `streak`/consecutive-signal logic and rule-5
  promotion persistence are per-record (per-cycle) today. Re-express "consecutive" and "persistence"
  in **calendar days**: a same-direction signal only advances the streak / counts toward promotion
  when it is separated from the prior counted signal by at least a **minimum day-gap** (a dial), so
  a daily cadence cannot promote a thesis or swing conviction (low↔high on the 3-level scale) faster
  than the intended cross-period pace. Provisional defaults chosen to approximate today's behavior;
  exact values deferred (D5).
- **Determinism:** all day-math derives from `asOf` labels via `corpus.period_end` (already the
  project's label-based, never-wall-clock convention). Replays are byte-stable.

### 5.3 Corpus ages via the wiki (D4)

- `corpus.enumerate_store` stops filtering with `in_window(f.asOf, …)`. Instead it ages **each
  finding by its evidence's real publication date** (`observedAt`) through the wiki decay curve —
  `effective_salience(intrinsic, days_between(as_of, observedAt), half_life([finding]))` — and keeps
  the finding only if the result clears a **salience floor**. The flat `asOf` `window_days` filter is
  **removed**; pruned pages (scored-then-floored in the lifecycle) are excluded whole. `assemble()`
  still unions the aged store corpus with this cycle's fresh gated findings.
- **Why per-finding `observedAt`, not page `quiet_age` (user-confirmed 2026-07-08):** on the live
  store every wiki page was last touched this cycle (salience 0.0, no state-change events), so
  page-level `quiet_age` ≈ 0 and page decay would drop nothing — the staleness lives entirely in the
  findings' `observedAt` (spanning 2025-08 → 2026-07). The decay *curve* is unchanged (this is still
  the wiki methodology, D4); only the age it measures is the evidence's real date. Salience floor =
  the wiki's own `stale_threshold` (0.1), so the corpus drop-line matches where the rest of the wiki
  already calls a fact faded.
- **Shadow-check:** before/after finding sets are diffed over the stored scorecards (§7) to confirm
  the aged corpus drops the pile-up (e.g. the 174-day AMD content) without dropping legitimately
  live fundamentals.

### 5.4 Fresh gather rework (D6) — reworks F58

- `gather-category/SKILL.md`: the standard/live "Recency window" changes from **`recencyDays = 45`
  + hard-drop of old non-filing leads** to a **7-day initial sweep** whose round-1 seeds carry the
  last-7-days qualifiers, plus an explicit **discretionary-pursuit** rule: the agent may chase a
  lead whose document is older than 7 days when it judges the content materially worth it.
- Each kept document older than the 7-day sweep is **logged** in `gather-log.json` with its age and
  a one-line justification (a `pursuedDespiteAge[]` list, symmetric to `skipped[]`). This closes the
  v4 gap where old pages entered with **no** recency record — discretion becomes auditable, never
  silent (Part 29 doctrine).
- Filing-URL seeds remain exempt (a fresh 10-K legitimately discusses older periods).

### 5.5 Change engine (D3)

- A code step computes today's **state vector** — the six dimension ratings, the demand/supply index
  directions, the thesis convictions/watch-items, and the headline metrics (§5.6) — and compares it
  to the **state vector of the nearest stored run at/before** `asOf − 1d`, `asOf − 7d`, `asOf − 30d`.
- Output per horizon: the set of changed items with direction and magnitude, and an explicit
  **unchanged** verdict per item that did not move ("unchanged since <date>"). Pure projection over
  stored scorecards — replayable for $0.

### 5.6 Quick-glance metrics — three tiers (D8)

Every metric renders with **its move** (↑/↓/=) across the three horizons and **its age**.

- **Tier 1 — the verdict (computed, free):** demand momentum, supply momentum, the gap direction,
  and the six dimension ratings, as words + arrows. This is the headline glance and already exists
  in the scorecard.
- **Tier 2 — physical scarcity (gathered / local feed):** GPU rental price (§5.7), lead times
  (`leadTimes`), packaging + memory capacity (CoWoS / HBM). The real supply/demand heartbeat.
- **Tier 3 — money / fundamentals (quarterly, age-tagged):** data-center revenue guidance
  (`vendorRevenueGuidance`), order backlog (`rpoBacklog`), gross margin (`grossMargin`). Always
  carries an age tag because it moves on earnings.
- **Optional — competitive snapshot:** market share, notable design wins, and **custom-silicon
  price** (AWS Trainium — the current price feed has no TPU, confirmed 2026-07-08) as a
  substitution signal.
- **Share price: excluded** for now.

### 5.7 Price feed (D9)

- Source: `gpu_agent/scrape_data/{aws,coreweave,gcp,oracle}_gpu_price.csv` — gitignored, ~20 MB,
  daily columns `YYMMDD` from 2025-02 through the present. Schema: `instance, term, region,
  <YYMMDD…>`.
- A read-only reader module produces representative prices:
  - **normalize to $/GPU-hour** (instance price ÷ GPU count for that instance family),
  - **on-demand** term only,
  - **USA** region (a US region, e.g. US-East; if multiple US regions exist, a documented pick or
    average — decided in the plan),
  - **instance-family → GPU-model** map derived from the data (e.g. AWS `p5*` → H100/H200; Trainium
    `trn*` classified as custom-silicon, **not** a GPU).
- The reader is **`asOf`-driven**: it reads the column for the run's date label (and the 1/7/30-day
  lookback columns for the deltas), never `Date.now()` — so it is deterministic and replayable.
- **Display-only (F8):** price appears as a confirmation/overlay track (the existing PMI surface),
  never blended into DMI/SMI. No scoring change.

### 5.8 Renderer (D7) — delivers F64 + F77

- `report.py` leads with the three horizon change lines (§5.5) and the Tier-1/2/3 quick-glance
  (§5.6), then the ranked calls (highest-conviction / most-moved first), then the supporting detail,
  appendix below the fold. Explicit "unchanged" states; real-age tags on carried facts; a length
  budget above the appendix.
- This subsumes **F64** (the change lines *are* the trigger-first daily lead — which theses moved and
  why) and **F77** (importance-ordered, consolidated, length-capped). F64's optional Brier-scoring
  add-on folds in later or defers.

## 6. Data flow — one day, end to end

1. **Fresh gather** — 7-day sweep + logged discretionary older-lead pursuit (§5.4).
2. **Corpus** — assemble the aged store corpus (wiki decay + lifecycle, §5.3) ∪ this cycle's fresh
   gated findings.
3. **Brain** — extract → gate → judge → thesis (frozen core, unchanged) over the corpus.
4. **Compute state** — ratings, index directions, thesis convictions, headline metrics (incl. the
   price feed §5.7).
5. **Diff** — today's state vs the nearest stored runs at −1d / −7d / −30d (§5.5).
6. **Render** — change-first brief with the three-tier quick-glance (§5.8).
7. **Persist** — write `store/<category>/YYYY-MM-DD-vN`, wiki/thesis updates, cycle log.

## 7. Testing strategy

- **Unit (TDD):** calendar-day `quiet_age`/`half_life` and decay parity; thesis day-gap streak /
  promotion; corpus aged-enumeration (a decayed old page drops out, a refreshed one stays); the
  price-feed reader (normalization, USA region, instance→GPU map, `asOf`-column selection); the diff
  engine (point-in-time, nearest-at/before, unchanged states); the renderer (change lines, age tags,
  length budget).
- **Shadow-check (behavior change):** run the new corpus/decay/pacing over the stored 2026-07 v1–v4
  and the recent dailies; diff the surfaced findings and thesis moves vs the committed scorecards;
  confirm the pile-up drops (174-day AMD content, 320-day NVIDIA page) while live fundamentals stay.
  No stored scorecard is edited.
- **Determinism:** replay a day twice → byte-identical (price reader keyed on `asOf`, not wall-clock).
- **Eval pin:** `tests/test_evals_baseline_pin.py` **stays green** — no emitted brain-prompt bytes
  change (this feature is code + skill prose + data, not prompt text).

## 8. Risks & mitigations

- **Cycle → calendar conversion is behavior-sensitive** (wiki decay, thesis pacing). Mitigation:
  strict TDD, the shadow-check (§7), and provisional defaults tuned to approximate today's behavior;
  exact values recalibrated later (D5).
- **Instance → GPU mapping** (Trainium is not a GPU; per-GPU normalization needs GPU counts).
  Mitigation: derive and pin the map from the data in a tested table; classify custom silicon
  separately.
- **Frozen core:** `scoring.py`, `gate.py`, `schema/*`, `judgment/*` aggregation, `pipeline.py` are
  **not touched**. The behavior-sensitive files (`wiki/lint.py`, `thesis.py`, `corpus.py`) are not
  frozen core but are heavily test-pinned — treated with migration-grade care (shadow-check + review).
- **Determinism regression** if any new step reads wall-clock. Mitigation: all day-math from `asOf`
  labels via `period_end`.

## 9. Build order (the plan will finalize)

1. **Calendar-day measurement** in wiki decay + thesis pacing (§5.2) — foundational; shadow-checked.
2. **Corpus ages via the wiki** (§5.3) — depends on (1).
3. **Fresh-gather rework** (§5.4) — largely skill prose + the `pursuedDespiteAge` log; independent.
4. **Price feed reader** (§5.7) — independent; feeds the renderer.
5. **Change engine + change-first renderer + quick-glance tiers** (§5.5–5.8) — depends on (1)–(4)
   producing comparable daily snapshots; delivers F64 + F77.

Cadence day-grain (§5.1) rides with (1)/(5). Large feature → built and reviewed in stages, not one
shot.

## 10. Backlog impact

- **Delivers F64 and F77** (tick when this ships).
- **Supersedes F58's window rule** (F58's implementation stays merged; its 45-day hard-drop is
  replaced by D6).
- **Absorbs part of F68** (brief/render cleanups done during the renderer rework).
- **Does not subsume** F60 (index scoring), F25 (store speed — more important now), F65, F66.

## 11. Decision provenance

All decisions D1–D9 were made by the user in an interactive session on **2026-07-08** — genuine
`user-approved`, not AFK-default (F76 vocabulary). The session began as "retune F58 to a 7-day
window," and the design grew as the live-v4 investigation showed the staleness was structural
(advisory gather window + cycle-stamp corpus window), not a threshold value. If any decision here is
wrong, correct it in this file.
