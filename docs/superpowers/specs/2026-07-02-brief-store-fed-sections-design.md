# Per-category brief — store-fed sections (sub-project 4-5b) — design

- **Date:** 2026-07-02
- **Status:** Draft for review (the wiki-store-fed half of the per-category Market-State brief)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md); the
  per-category render it extends [`2026-07-01-per-category-brief-render-design.md`](2026-07-01-per-category-brief-render-design.md)
  (4-5 — §7 names this seam) and the output **design target**
  [`2026-06-29-human-market-brief-design-target.md`](2026-06-29-human-market-brief-design-target.md) (rules 4 "lead
  with what moved" + 5 "every line cited + honest"; §3 the mock's WHAT MOVED + STORYLINES blocks). Charter **Part 35**
  (the surface is a projection *consumer*, not a writer), **Part 17** (numbers only from gated findings; plain
  language), **Part 20** (replayable / byte-reproducible), **Part 29** (nothing silent).
- **Depends on:** 4-5 `gpu_agent/brief.py` (the brief-first `render_report` + the two stub anchors) and its
  `render_deferred_stubs` seam; 4-1 `WikiStore.diff`/`index` + `FindingStore`; 4-4b `wiki/lint.py` `score_moves`
  (the read-only materiality ranker) + `MaterialMove`; 4-4c `wiki/lifecycle.py` `partition_canonical` (registered vs
  provisional); the CLI `_report` handler's existing `registry` + `horizons` loads (4-5).
- **Feeds:** the later WHY (driver→constraint) tree, the HTML dashboard, and the layer-tier arc — all a second
  projection over the same store.

---

## 0. What 4-5b is — scope + the locked decisions

4-5 shipped the brief-first per-category artifact with the two **store-fed** sections rendered as honest one-line
stubs ("rendered in 4-5b — needs a multi-cycle wiki store"). **4-5b replaces those two stubs** with real renders read
from the wiki store: **WHAT MOVED SINCE LAST RUN** (the day's material diff) and **STORYLINES** (thread
state/trajectory over time). It is a **pure, deterministic, read-only projection** of the wiki store + the
`Scorecard` — no LLM, no store *writes*, byte-reproducible (Part 35 / Part 20). Because 4-5 already fixed the
brief-first shape and the two stub anchors, 4-5b is a **drop-in of two renderers plus a read-only collector**, no
restructuring.

**Locked decisions (from this session's brainstorm — don't relitigate):**
- **(a) Scope = exactly the two store-fed sections.** WHAT MOVED + STORYLINES replace the stubs. The **WHY**
  (driver→constraint) tree stays deferred (it needs a judgment structure beyond `categoryStatus.reason`), and so do
  the HTML dashboard and the layer-tier arc.
- **(b) Seam = precompute-and-pass; the renderer stays a pure projection (Part 35).** A new **read-only collector**
  reads the store and returns a plain `MarketMovement` value; the CLI `_report` handler calls it and threads it into
  `render_report(..., movement=…)`; the new `brief.py` renderers are **pure functions over `MarketMovement`** (no
  store handle, no I/O). `movement=None` → an honest **empty-state note** (`(no wiki store yet — needs a multi-cycle
  store from daily cycles)`), the same shape as the other degradations — this **supersedes** the 4-5 "rendered in
  4-5b" stub, which is no longer accurate once 4-5b ships. Backward-compatible in shape (the sections + headers stay),
  exactly like 4-5's `horizons` kwarg. The renderer never touches the store; the CLI owns the I/O.
- **(c) The collector is a new file in the wiki package — `gpu_agent/wiki/movement.py`.** It reuses the existing
  read-only seams (`store.diff`, `score_moves`, `store.index`, `partition_canonical`, the in-package
  `_contradictions_for`) and returns `MarketMovement`. Placing it in the wiki package keeps every *existing* wiki
  module **byte-unchanged** and avoids a cross-package private import. `brief.py` imports only the `MarketMovement`
  data type — it gains no store dependency.
- **(d) Read-only — never `lint()`.** WHAT MOVED ranks via `score_moves(...)` (read-only), **not** `lint(...)` (which
  appends an idempotent provenance event). Rendering a `report` must write nothing to the store (Part 35).
- **(e) The store is read from the existing `--store` root.** `report --store <dir>` already holds `<dir>/wiki` and
  `<dir>/findings` (the same layout every `wiki-*` CLI uses). No new CLI flag (4-5 decision b — the default `report`
  is the single unified artifact). When `<dir>/wiki` is absent/empty → `movement=None` → the stubs. Backward-compatible.

---

## 1. Architecture

```
CLI _report ── loads ──▶ WikiStore(<store>/wiki, FindingStore(<store>/findings))
            ── calls ──▶ collect_movement(store, as_of=sc.asOf, prev_as_of=prior.asOf,
                                          registry=registry, horizons=horizons) → MarketMovement | None
            ── passes ─▶ render_report(sc, prior, registry, render_ts=…, horizons=…, movement=…)
                             ├─▶ brief.render_what_moved(movement)   # pure; None → stub
                             └─▶ brief.render_storylines(movement)   # pure; None → stub
```

Three units, one job each:
1. **The collector** — `gpu_agent/wiki/movement.py` `collect_movement(store, *, as_of, prev_as_of, registry,
   horizons) -> MarketMovement`. Read-only. Computes WHAT MOVED via `diff` + `_contradictions_for` + `score_moves`
   (→ ranked `material` + `dropped`) and STORYLINES via `index` + `partition_canonical`. Joins each moved page's
   `oneLine` from the index. Returns plain data; no store handle escapes; **zero writes**.
2. **The renderers** — `brief.render_what_moved(movement)` and `brief.render_storylines(movement)`, pure functions
   over `MarketMovement`. `movement is None` → the existing stub strings (unchanged from 4-5).
3. **The CLI wiring** — `_report` checks `<store>/wiki`: **absent** → `movement=None` (the collector is not called; the
   two sections render their honest empty-state note). **Present** → `collect_movement(...) → MarketMovement` (with
   `prevAsOf=None` when there is no prior cycle). It threads `movement=` into `render_report`. `registry` (4-5) and
   `horizons` (4-5) are already loaded in `_report` — `score_moves` needs both.

`render_report` gains one optional keyword `*, movement=None` and replaces the single `render_deferred_stubs()` call
with the two new renderers (`render_what_moved(movement)` then `render_storylines(movement)`, in the stubs' brief-first
positions); the eight detailed sections and the overall order are otherwise **unchanged**. `render_deferred_stubs` is
**retired** (superseded by the two renderers' empty-state path); `render_market_caveat` is unchanged.

**The `MarketMovement` model** (in `wiki/movement.py`; presentation-neutral plain fields so `brief.py` needs no wiki
model import beyond this type):

```python
class MovedRow(BaseModel):
    title: str                     # the moved page's oneLine (fallback: page title)
    findingIds: list[str]          # contributingFindingIds — the [f-###] citation
    tier: Literal["primary", "secondary"]   # derived from MaterialMove.tierMult
    provisional: bool              # MaterialMove.status != "registered"
    newThread: bool                # factors.newThread
    contradiction: bool            # factors.contradiction
    contradictionNote: str = ""    # factors.contradictionNote
    stateFrom: Optional[str] = None  # factors.stateTransition["from"], when present
    stateTo: Optional[str] = None    # factors.stateTransition["to"]
    score: float                   # materiality (ranking; carried for transparency)

class StorylineRow(BaseModel):
    title: str
    state: str
    trajectory: str
    lastUpdatedAsOf: str
    salience: float
    provisional: bool              # in the confidence-capped group

class MarketMovement(BaseModel):
    prevAsOf: Optional[str]        # None → WHAT MOVED renders the "no prior cycle" note
    moved: list[MovedRow]          # ranked score desc, then pageId (byte-stable tiebreak)
    foldedCount: int               # len(dropped) — the below-threshold moves (Part 29)
    storylines: list[StorylineRow] # both groups; the `provisional` flag separates them
```

---

## 2. The two sections

### ① WHAT MOVED SINCE LAST RUN — `render_what_moved(movement)`
Renders `movement.moved` (ranked); the tag + arrow are derived from each `MovedRow` by a small deterministic
mapping, in this precedence:

| Condition | Tag | Arrow |
|---|---|---|
| `newThread` | `NEW` | ▲ |
| `contradiction` | `WATCH` | ▼ (append the `contradictionNote`) |
| `stateFrom`/`stateTo` present, `stateTo` is an improving keyword | `UP` | ▲ |
| `stateFrom`/`stateTo` present, `stateTo` is a worsening keyword | `DOWN` | ▼ |
| `stateFrom`/`stateTo` present, neutral/unknown keyword | `CHANGED` | = |
| otherwise (indicator move only) | `MOVED` | = |

The improving/worsening test for UP/DOWN **reuses the same trajectory keyword table** STORYLINES uses (§2②) applied to
`stateTo` — one shared deterministic map, no separate state-ordering to maintain.

Row: `<tag> <arrow>  <title>  [<findingIds>] <tier>` — plus a trailing `(provisional)` when `row.provisional`, and
the `contradictionNote` (or `stateFrom → stateTo`) as a short suffix where present. A footer
`(<foldedCount> lower-materiality items folded — see wiki-lint)` when `foldedCount > 0`.

```
WHAT MOVED SINCE LAST RUN  (vs 2026-06)
  ▲ NEW    AMD MI450/Helios ramp pulled into Q3            [f-217] primary
  ▼ WATCH  Hyperscaler capex guide trimmed ~5%            [f-241] secondary  (contradicts thesis)
  ▲ UP     RPO backlog steady → accelerating              [f-203] primary
  (3 lower-materiality items folded — see wiki-lint)
```

**Degradation (honest, never a crash):**
- `movement is None` (no `<store>/wiki`) → `(no wiki store yet — needs a multi-cycle store from daily cycles)`.
- `movement.prevAsOf is None` (no prior cycle: `--no-prior`, or the first tracked cycle) → a single honest line
  `(no prior cycle to compare — first tracked cycle)`. STORYLINES still renders (it needs no prior).
- prior present but `movement.moved` empty → `(no material moves this cycle)` + the folded footer when `foldedCount > 0`.

### ② STORYLINES — `render_storylines(movement)`
Renders `movement.storylines` split by the `provisional` flag into two honestly-labeled groups — **REGISTERED
(canonical)** then **PROVISIONAL (confidence-capped)** — each ordered by `salience` desc then `title`. Row:
`• <title>  <state> → <trajectory>  (last updated <lastUpdatedAsOf>)  <arrow>`, where the arrow maps `trajectory`
via a deterministic keyword table (accelerating/improving/rising → ▲; eroding/worsening/decelerating/falling → ▼;
steady/flat → =; quiet/unknown/other → ·). Trajectory is brain-authored free text, so the arrow is a best-effort
keyword match falling back to `·`.

```
STORYLINES (tracked over time)
  REGISTERED (canonical)
    • AMD inflection      on-track → accelerating   (last updated 2026-07)  ▲
    • NVIDIA moat         intact → slowly eroding    (last updated 2026-06)  ▼
    • CoWoS capacity      tight → tight              (last updated 2026-06)  =
  PROVISIONAL (confidence-capped)
    • Export controls     quiet                      (last updated 2026-05)  ·
```

**Degradation:** `movement is None` → `(no wiki store yet — needs a multi-cycle store from daily cycles)`; empty index
→ `(no tracked storylines yet)`; one group empty → render the other with an honest note for the empty one.

---

## 3. Determinism (Part 20)

Byte-reproducible: same store + `Scorecard` (+ prior) + `render_ts` → same brief. No wall-clock anywhere in
`wiki/movement.py` or `brief.py`; recency is data-derived — WHAT MOVED shows `(vs <prevAsOf>)`, STORYLINES shows
`(last updated <lastUpdatedAsOf>)` — **never** the design-target mock's "no change 11d" (that needs "now"; same
clock-free choice 4-5 made for `⚠carried`). Every ordering has an explicit tiebreak: `moved` by `score` desc then
`pageId`; `storylines` by `salience` desc then `title`. `tier` is derived from `tierMult` by a fixed threshold.

---

## 4. Frozen vs additive (Part 33)

- **Byte-unchanged (frozen):** `gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the `Finding` and
  `Scorecard` schemas, the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `store.py`, and **every
  *existing* module under `gpu_agent/wiki/`** (`lint.py`, `lifecycle.py`, `page.py`, `log.py`, `ingest.py`,
  `dedup.py`), `gpu_agent/gathering/`. No `fixtures/` change. **No new `Scorecard` field.** No new dependency.
- **Additive:** the new file `gpu_agent/wiki/movement.py` (the collector + `MarketMovement`/`MovedRow`/`StorylineRow`);
  two new renderers in `gpu_agent/brief.py` (`render_what_moved`, `render_storylines`) replacing the single
  `render_deferred_stubs()` call in `render_report`; the `render_report` signature gains `*, movement=None`; the
  `_report` handler builds the store + calls the collector + threads `movement=`. `render_deferred_stubs` is **retired**
  (its two-line stub is superseded by the two renderers' honest empty-state path); `render_market_caveat` is
  **unchanged**. The 4-5 `test_brief_stubs.py` stub test is updated to the new empty-state text (our own test — a
  legitimate update, not a weakening); no other 4-5 test changes (the section headers are preserved).
- **Reuses, does not rebuild:** `WikiStore.diff`/`index`, `score_moves`/`_contradictions_for`/`MaterialMove` (4-4b),
  `partition_canonical` (4-4c), `FindingStore`, and the `_report` handler's existing `registry`/`horizons` loads.

---

## 5. Doctrine

Pure projection — the renderer and collector write **no store event and no number** (Part 35/17); WHAT MOVED ranks
via the read-only `score_moves`, never `lint()`. **Honest** (Part 17): every WHAT MOVED row is cited (`[f-###]`) and
tiered; provisional moves + storylines are marked confidence-capped; the folded count is always shown (Part 29 —
nothing silent); all degradations are honest one-line notes, never a silent omission or a crash. **Replayable**
(Part 20): byte-reproducible, clock injected. A store-less `report` (`movement=None`) still emits both section headers
with an honest empty-state note — the same brief-first shape as today, only with accurate text (no promissory
"rendered in 4-5b").

---

## 6. The 4-5b → later seam

4-5b renders the two store-fed sections. Still deferred (later cuts, each a further projection over the same store):
the **WHY** (driver→constraint) tree — needs a judgment structure beyond `categoryStatus.reason`; the **`⚠single-source`**
decoration on WHAT MOVED rows — needs counting distinct evidence sources across a move's contributing findings (extra
`FindingStore` reads), deferred to keep this cut tight (tier primary/secondary already ships; the deferral is logged);
the **HTML dashboard** (a second projection over the same Scorecard + store); and the cross-cutting **layer-tier**
brief. Because 4-5b keeps `MarketMovement` a plain value and the renderers pure, each later cut is additive.

---

## 7. Test strategy (deterministic; in-code stores, no committed `fixtures/wiki`)

- **Collector** (`test_brief_movement*.py`) — build a small **2-cycle** `WikiStore` in-code in `tmp_path` (the wiki-test
  convention: `WikiStore(tmp/"wiki", FindingStore(tmp/"findings"))`, seed findings + pages across two `asOf` cycles so
  `diff` yields new/changed pages, `score_moves` yields material + dropped, and `index`/`partition_canonical` yield
  registered + provisional threads). Assert the `MarketMovement`: ranked `moved` (order + tiebreak), the derived
  fields (tier from tierMult, provisional from status, newThread/contradiction/stateTransition passthrough,
  findingIds, oneLine join), `foldedCount == len(dropped)`, `prevAsOf`, the registered/provisional storyline split +
  salience-desc order. Assert the collector performs **no write** (log length unchanged before/after).
- **Renderers** (`test_brief_moved.py`, `test_brief_storylines.py`) — build `MarketMovement` in-code (plain data);
  assert WHAT MOVED (tag/arrow precedence, citation, tier, provisional marker, contradiction/state suffix, folded
  footer, the three degradations) and STORYLINES (two groups, trajectory→arrow map, last-updated, ordering, empty
  notes); `movement=None` → the honest empty-state note (both section headers present).
- **Composition** (`test_brief_report` extension) — `render_report(..., movement=…)` places the two real sections in
  the stubs' positions (brief-first order preserved: STATE → board → WHAT MOVED → STORYLINES → detailed → caveat);
  `movement=None` → both section headers with the honest empty-state note. The 4-5 report-order tests (which assert
  header presence + brief-first order) stay green; the one 4-5 stub-text test is updated to the new empty-state text.
- **CLI e2e** — build a store in `tmp_path` (wiki + findings + a scorecard JSON), `report --scorecard <sc> --store <tmp>`
  → real WHAT MOVED + STORYLINES; a run whose `--store` has no `wiki/` → the honest empty-state note; `--render-ts`
  makes it byte-stable.
- **Throwaway preview** — hand-build a 2-cycle store + scorecard, run the CLI, confirm the LIVE brief-first output
  (real moved rows + storyline groups, provisional confidence-capped, folded count).
- **Guards** — frozen-contract `git diff` empty (gate/scoring/schemas/registry code/pipeline/store/**existing** wiki
  modules/gathering); no `fixtures/` change; the full suite stays green (baseline **399 passed, 3 skipped** + the new
  tests).

---

## 8. Out of scope (deferred)

- **The WHY / driver→constraint tree** → later (needs a judgment structure beyond `categoryStatus.reason`).
- **The `⚠single-source` flag** on WHAT MOVED rows → a fast-follow (needs distinct-source counting per move).
- **The HTML dashboard** → a later projection over the same Scorecard + store.
- **The cross-cutting LAYER/market brief** → the deferred layer-tier arc.
- **Populating a real multi-cycle store** → accrues from repeated live 4-4a/4-4d runs; 4-5b is built/tested against
  in-code stores and a throwaway preview store, matching every prior wiki piece.
- **Any new `Scorecard` field, any wiki-module edit, any store write from `report`** → not needed.

---

## 9. Acceptance (4-5b)

1. **The two stubs are replaced by real renders** when `report --store <dir>` finds a populated `<dir>/wiki`: WHAT
   MOVED SINCE LAST RUN and STORYLINES appear in the stubs' brief-first positions (STATE → board → WHAT MOVED →
   STORYLINES → detailed sections → TRUST caveat).
2. **WHAT MOVED** renders the materiality-ranked moves (reusing 4-4b `score_moves`), each row tagged
   NEW/WATCH/UP/DOWN/MOVED with an arrow, cited (`[f-###]`) and tiered, provisional moves marked confidence-capped,
   with the folded below-threshold count shown; honest degradation when there is no prior cycle or no moves.
3. **STORYLINES** renders `index()` split by `partition_canonical` into REGISTERED (canonical) and PROVISIONAL
   (confidence-capped), each row `state → trajectory (last updated <asOf>) <arrow>`, deterministically ordered; honest
   empty notes.
4. **Pure, read-only, additive:** the collector and renderers perform **no store write** (never `lint()`); `brief.py`
   stays free of store I/O; `render_report` gains only `*, movement=None`; every *existing* wiki module + the frozen
   contract byte-unchanged; no `fixtures/` change; no new dependency; no new `Scorecard` field.
5. **Deterministic (Part 20):** byte-reproducible (clock injected via `render_ts`); recency data-derived; all
   orderings tiebroken; `movement=None` → both section headers with the honest empty-state note (the brief-first
   shape unchanged; the 4-5 order tests stay green, the single 4-5 stub-text test updated).
6. **Feeds the sequence:** `MarketMovement` stays a plain value and the renderers stay pure, so the WHY tree, the
   `⚠single-source` flag, and the HTML dashboard drop in additively later.
