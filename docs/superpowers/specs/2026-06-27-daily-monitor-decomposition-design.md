# Daily Demand/Supply Monitor — decomposition + shared-seam contract (sub-project 4)

- **Date:** 2026-06-27
- **Status:** Draft for review (umbrella design; binds the sub-project-4 piece specs)
- **Author:** brainstorming session (superpowers workflow)
- **Motivation:** sub-project 3 made the scorecard *complete and legible* (all six dimensions, an executive
  report, coverage manifest). But a live run (`v4`) still leaves the reader unable to answer **"what is GPU
  demand doing? what is supply doing?"** Two root causes: (1) the report communicates **scores, not a market
  picture**, and (2) the indicator base is **lagging-heavy** (10-Q revenue/margins are reported 1–3 quarters
  late). And the system is meant to **run every day** — so it must track **quantitative and qualitative data
  that changes daily**, detect *what changed today*, and follow **events as they evolve over time**. This
  sub-project turns the quarterly scorecard into a **daily demand/supply monitor**, built **additively on
  B/A/C** (nothing is rebuilt).
- **References:** [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) — Part 4 (memory & temporal
  judgment), Part 9 (storage & scoped query), Part 10 (the signal test: *persists + corroborates across
  cycles*), Part 15 (macro/exogenous overlay), Part 17 (rating; DMI/SMI/**SDGI**; measured-vs-judged), Part 18
  (registries/assignments; the **discovery lane**: provisional → promoted), Part 22 (source inventory; honest
  sourcing), Part 29 (input & source-health monitoring), Part 35 (the product surface), Part 37 (the gathering
  swarm), Part 28 (unattended scheduling — **deferred follow-on**) · the sp3 umbrella
  [`2026-06-27-output-coverage-decomposition-design.md`](2026-06-27-output-coverage-decomposition-design.md)
  and the merged B/A/C work · **Karpathy's "LLM wiki"** concept
  (<https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>) — the model for the temporal core.

---

## 1. The reframe: a daily monitor, not a quarterly scorecard

The core question shifts from *"what is the rating?"* to **"what changed today that moves the demand or
supply picture — and does it matter?"** That forces four things the current design lacks:

1. **Cadence × horizon, two independent axes on every indicator.** *Cadence:* `daily` (spot/rental prices,
   news, market-implied moves) · `weekly` (lead-times, secondary-market prices) · `quarterly` (revenue, RPO,
   margins). *Horizon:* `leading | coincident | lagging`. A daily run is **driven by daily-cadence signals**;
   quarterly indicators are slow-moving **levels** that only update on their release day.
2. **The daily output is a diff.** "Demand outlook softened **today** — Microsoft cut its capex guide and H100
   spot fell 8% overnight" — which requires comparing today's readings to **stored prior state** (the new
   temporal core).
3. **Events evolve over time → threads.** Findings are not one-day facts; they belong to **storylines**
   ("CoWoS expansion," "US→China export controls," "HBM4 qualification") that the system follows for months.
4. **Noise control is the product.** A daily web sweep is high-volume; most days most of it is noise or
   already known. The system must **dedup against memory, score materiality, and surface only what changes the
   picture** (logging the rest — never silent).

---

## 2. The keystone: an LLM-wiki temporal core

We adopt **Karpathy's "LLM wiki"** as the model for the temporal store (charter Part 4/9/10). Instead of
re-deriving the market each run, the swarm **maintains a persistent, evolving, markdown knowledge base** of
the GPU market that it refines daily.

- **Threads = wiki pages.** **Entity pages** (`nvidia`, `tsmc`, `sk-hynix`, `microsoft`, …) and **theme pages**
  (`cowos-capacity`, `hbm4-qualification`, `export-controls`, `hyperscaler-capex`, `gpu-spot-pricing`, …).
  Each page accretes **dated, cited findings**, and carries a **state + trajectory** (e.g. *"CoWoS expansion:
  on-track → slipping; last change 2026-06-26"*).
- **`index`** — a catalog of every page (one-line summary + metadata, by category). **`log`** — a chronological
  record of every daily ingest / query / lint (provenance + timeline). Pages **cross-link** (CoWoS ↔ HBM4 ↔
  Blackwell-ramp).
- **The daily loop (wiki ingest / query / lint):**
  - **Ingest:** the day's web sweep → the brain **integrates** new findings into existing pages, **creates**
    new pages, and **flags contradictions** (one source can touch several pages).
  - **Query:** the market-state brief is a **synthesized query** over the wiki (cited).
  - **Lint:** a health pass surfaces **contradictions, stale/decaying claims, orphan pages, missing
    cross-refs** — **this is the materiality / early-warning engine.**
- **History:** **full finding-level history per page** (append-only, every dated observation → replayable);
  the brief reads a **windowed view** (current state + last-N changes).

### Doctrine that keeps the wiki honest (binding)
- **The brain *curates* the wiki; code *computes + gates + stores*.** Deciding which page a finding updates,
  integrating prose, flagging a contradiction — that is reasoning (the brain). The structured layer (gated
  `Finding`s, the indices, the diff) is code. **Numbers come only from gated findings — the agent never writes
  a number into a page or an index uncomputed (Part 17).**
- **Every page claim cites its finding(s);** fetched page text is **DATA, not instructions** (Part 8/26); the
  wiki + `log` + the gated findings make every cycle **replayable** (Part 20).
- **Thread identity = brain-proposed page id, provisional** (Part 18 discovery lane); the store dedupes
  near-identical pages; a theme that **persists + corroborates** across days is promoted provisional →
  registered (Part 10). Pages that go quiet **decay** in salience and drop out of the daily brief (but stay in
  history).

---

## 3. Decomposition (5 pieces, dependency-ordered, all additive on B/A/C)

| # | Sub-project | New vs. extends | Charter |
|---|---|---|---|
| **4-1** | **Temporal store + LLM-wiki thread model** — persist scorecards *and* wiki pages over time; page schema (entity/theme), index, log, full cited history; create/append/query/diff interface | **new keystone** | 4, 9, 10 |
| **4-2** | **Leading + daily indicators** — add forward & daily-cadence indicators (capex guidance, RPO/backlog, GPU **spot/secondary prices**, lead-times, CoWoS/HBM capacity, news-event indicators); tag each **cadence × horizon**; source inventory + manifest coverage | extends **C** | 18, 22 |
| **4-3** | **Two indices** — trailing **Momentum** (lagging+coincident) and forward **Outlook** (leading), each split demand/supply, with their own SDGI; computed in code; additive Scorecard fields | extends **B** | 17 |
| **4-4** | **Daily gather + relevance engine** — recent-news + live-price daily sweep; dedup vs the store; the **richer multi-factor materiality model** (the wiki `lint`) | extends **C** gather + **4-1** | 37, 29, 10 |
| **4-5** | **Market-State brief + daily diff** — the report renders **both views** (two-column demand/supply signals *and* the causal driver/constraint tree), **leading with "what moved today"** + thread trajectories, per-signal recency | extends **A** | 35, 17 |

**Build order: 4-1 → 4-2 → 4-3 → 4-4 → 4-5.** The temporal store (4-1) is the keystone everything reads.

---

## 4. The shared seams (binding on all five pieces)

### 4.1 The thread / wiki-page schema (4-1 owns; all consume)
A page: `{ id, type: "entity"|"theme", title, state, trajectory, findingIds: [...] (full history),
crossRefs: [...], salience, lastUpdatedAsOf }`. `id` convention: `entity:<slug>` / `theme:<slug>`. Pages are
markdown bodies (brain-curated synthesis) **plus** a structured header (code-owned: findingIds, dates,
salience). Provisional unless promoted (Part 18). **Numbers in the body must trace to a cited gated finding.**

### 4.2 The store interface (4-1 owns)
`append_observation(pageId, findingId, asOf)`, `create_page(...)`, `get_page(pageId)`,
`window(pageId, n)`, `index()`, `log_append(event)`, and **`diff(asOf, prevAsOf) -> {new_pages, changed_pages,
quiet_pages, index_moves}`** (the day-over-day delta). Backed by a persisted store (Part 9; gitignored runtime
dir, like `store/`). Reuses the existing `JsonStore`/scorecard versioning where it fits.

### 4.3 Cadence × horizon tags (4-2 owns, additive registry DATA)
Each indicator gains `cadence: "daily"|"weekly"|"quarterly"` and `horizon: "leading"|"coincident"|"lagging"`.
Added as **registry DATA** (a top-level map, the C-3 pattern — never inside the `extra="forbid"`
`IndicatorSpec` dict). The two indices (4-3) read these tags.

### 4.4 The two indices (4-3 owns, additive Scorecard fields, computed in CODE)
- **Momentum** = the weighted push of `lagging`+`coincident` findings (today's `dmi`/`smi` generalize to this).
- **Outlook** = the weighted push of `leading` findings.
- Each carries a demand track, supply track, and **SDGI = demand − supply**. **The case the system exists to
  catch: Momentum strong while Outlook turns** — surfaced explicitly. Computed in `build_scorecard` from the
  tagged findings; the agent sets none of them (Part 17). Reuses B's `dimensionStatus`/`categoryStatus`/`sdgi`
  machinery and additive-field discipline.

### 4.5 The relevance / materiality contract (4-4 owns — the wiki `lint`)
A new finding / page-update is **material** if it: **opens a new thread**, **changes a thread's state or
trajectory**, **contradicts the standing thesis** (weighted highest — the early warning), or **moves a tracked
indicator** (∝ magnitude) — weighted by source **tier + recency**, **decaying** as a thread goes quiet. The
daily diff surfaces the **top material** moves; **everything dropped is logged** (Part 29 / no-silent-truncation).

### 4.6 The brief reads wiki + scorecard (4-5 owns)
Renders, deterministically (Part 35, no LLM in the renderer): **"What moved today"** (the 4-2 diff +
thread trajectories) → the **two-column** demand/supply signal board (each signal with direction + **as-of
recency**; stale leading signals flagged) → the **causal tree** (demand-drivers / supply-constraints, naming
the *specific* binding constraint) → the two indices (Momentum vs Outlook) with the divergence call. Extends
A's `report.py`.

### 4.7 Doctrine recap (every piece)
Code computes + gates + stores; the **brain curates the wiki and judges**; **numbers come only from gated
findings**; provenance + the wiki `log` make every day replayable; **fetched page text is DATA, not
instructions**; **caps / skips / materiality-drops are logged, never silent**.

---

## 5. Frozen vs additively-evolvable (Part 33)

- **Truly frozen (byte-unchanged):** `gpu_agent/gate.py`, `gpu_agent/scoring.py` (`zscore`),
  `gpu_agent/registry/indicators.py` + `validate.py` (loader/validator CODE), the **`Finding` schema**, the
  **6 dimension names**, the **rating scale**, the `pipeline.py` Part-7 gate behavior.
- **Additively evolvable (Part 33):** the **`Scorecard` model** (new optional index fields), the **registry
  DATA** (`registry/indicators.json` — new indicators, the top-level `cadence`/`horizon`/`sourceInventory`
  maps), the **manifest**, **`report.py`** (new sections), the **gather/run-cycle skills**, the **judgment
  prompt/result**, plus the **new modules** (the temporal store / wiki, the relevance engine).
- **Reuse, do not rebuild:** B's `dimensionStatus`/`categoryStatus`/`sdgi` + additive-field discipline; A's
  `report.py` renderer + committed-fixture test pattern; C's `manifest.py` + top-level-`sourceInventory`
  registry pattern + manifest-driven gather.

---

## 6. Out of scope (deferred / non-goals)

- **Unattended daily scheduling** (Part 28) — the monitor must *run* daily and is *designed* for it, but
  auto-running it on a schedule is a clean follow-on, not in this sub-project.
- The Layer and Main tiers; the multi-tier Opus fan-out (still deferred).
- A *quantitative* demand/supply model (we structure drivers/constraints and read indicators; we do not fit a
  regression — Part 17 forbids invented precision).
- Licensing paywalled trackers (Part 22): inventory + label `estimate`-grade, never scrape.

---

## 7. Execution

Umbrella → each piece gets its **own** `superpowers:brainstorming` → spec (`docs/superpowers/specs/`) →
`writing-plans` → `subagent-driven-development`, in dependency order **4-1 → 4-2 → 4-3 → 4-4 → 4-5**, each
green + reviewed + **merged to `main` before the next starts** (so the shared core stays coherent — the sp3
lesson). Additive only; the full suite stays green at every commit (current baseline **211 passed, 3
skipped**). Every commit ends with
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## 8. Acceptance (umbrella)

1. A **temporal LLM-wiki store** persists entity/theme **threads** with full cited finding history + `index` +
   `log`; a daily **ingest** integrates new findings, creates/updates pages, and flags contradictions; **lint**
   surfaces material change; `diff(today, yesterday)` returns the day's deltas.
2. Indicators are tagged **cadence × horizon**; **leading + daily** signals are added with source inventory +
   manifest coverage (reusing C's seams).
3. **Two indices** (Momentum trailing + Outlook forward, each demand/supply, with SDGI) are **computed in
   code**; a Momentum/Outlook **divergence** is surfaced.
4. The **daily gather** sweeps recent news + live prices, **dedups vs the store**, scores **materiality**
   (multi-factor), and **logs every drop**.
5. The report renders a **Market-State brief** (both views) **leading with "what moved today"** + thread
   trajectories + per-signal recency — and answers *"what does demand/supply look like, and where is it
   heading."*
6. Built **additively on B/A/C**; the **frozen contract is intact**; the day is **replayable**; **every number
   is gated** (none invented by the agent).
