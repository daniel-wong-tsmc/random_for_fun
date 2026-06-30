# Relevance engine — the wiki lint / early-warning pass (sub-project 4-4b) — design

- **Date:** 2026-06-30
- **Status:** Draft for review (the second piece of sub-project 4-4 — the materiality / early-warning engine)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md)
  (§2 "the daily loop — lint", §4.5 "the relevance / materiality contract"); charter **Part 4** (memory &
  temporal judgment), **Part 17** (numbers only from gated findings), **Part 20** (replayable), **Part 29**
  (nothing silent / no-silent-truncation), **Part 35** (deterministic projection), **Part 38** (code computes,
  brain curates). Builds additively on **4-1** (the wiki/finding store), **4-2** (the `cadence × horizon` tags),
  and **4-4a** (the brain ingest writer).
- **Depends on:** 4-1 (`WikiStore`/`FindingStore`/`diff`), 4-2 (`IndicatorHorizons` cadence/horizon tags),
  4-4a (entity-page writer; the brain-set `salience`; the `ingest`/contradiction signal). **Feeds:** 4-4c
  (discovery lane — consumes the materiality signal for promotion and the `stale` signal for provisional
  pruning), 4-5 (the brief renders the ranked "what moved today" + the decayed thread ranking).

---

## 0. What 4-4b is — and the decomposition that scopes it

Sub-project **4-4** is decomposed into a sequence (each its own spec → plan → SDD → merge):

- **4-4a (done, merged) — Brain ingest into the wiki:** the keystone *writer* — routes gated findings to
  entity pages (code) and lets the brain enrich them (the `--emit-prompt`→`--recorded` seam).
- **4-4b (this spec) — Relevance engine / the wiki `lint`:** the multi-factor **materiality score** + **salience
  decay** + a **structural health pass** — the early-warning engine. It *reads* what 4-4a wrote and **ranks what
  the daily `diff` surfaces**; everything dropped is logged.
- **4-4c — Discovery lane:** explore budget; theme pages + provisional off-registry topics; quarantine from
  canonical; promotion on persist+corroborate (Part 10). *Consumes* 4-4b's signals.
- **4-4d — Daily gather mode + numeric scrape sweep + dedup-vs-store:** the input firehose.

**4-4b is a pure-code, deterministic pass — NO new brain step.** The brain's one semantic judgment for this
engine (does a new finding contradict the standing thesis?) already happened at **4-4a ingest**; 4-4b is the
deterministic *computation* over what is stored, in the spirit of 4-3 (additive pure code). It ships ONLY the
lint computation; it is NOT: theme pages / explore budget / provisional discovery / quarantine / promotion / the
pruning *action* (4-4c); the gather/scrape (4-4d); the brief render (4-5).

**Locked decisions (from brainstorming):**
- **Full lint health pass, pure code.** Materiality ranking + salience decay + structural health (orphans,
  stale, cross-ref gaps, contradiction roll-up), with the one genuinely-semantic item handled structurally now.
- **Hybrid weighting.** *Relevance* = the brain's intrinsic `salience` (set at 4-4a) × code-derived factor
  weights; *persistence* (the decay half-life) = **input-derived** from 4-2's `cadence × horizon` tags. No magic
  global half-life, no new brain step. The "subjectivity" is a transparent, tunable policy table keyed on
  structured tags.
- **Decay is non-destructive.** Code computes `effective_salience` at read-time; the brain-set stored `salience`
  is never overwritten (no log churn; fully replayable).
- **Quiet-age is cycle-count**, not calendar days (granularity-agnostic — works whether `asOf` is `2026-06` or
  `2026-06-28`; matches the "across cycles" language of the Part 10 promotion test).
- **The one semantic item — *smart* "missing cross-ref suggestions"** (two pages are *about related things* and
  should link, with no textual mention) — is handled by a **cheap structural heuristic now** (asymmetric links +
  mention-without-link); the pure-semantic no-mention case is an explicit **deferred follow-up** (a future
  optional lint brain-seam). See §11.

---

## 1. The lint pass + CLI seam

A new module **`gpu_agent/wiki/lint.py`** with one entry point:

```python
def lint(store: WikiStore, *, as_of: str, prev_as_of: str | None = None,
         registry: IndicatorRegistry, horizons: IndicatorHorizons,
         config: LintConfig = DEFAULT_LINT_CONFIG) -> LintReport: ...
```

- Reads only: `WikiStore` (`index`, `state_history`, `observations`, `diff`, `log`, `get_page`),
  `FindingStore` (via `store.findings.get` — `magnitude`, evidence `tier`, `observedAt`/`asOf`),
  `IndicatorRegistry` (is an `indicatorId` a **scoring** indicator?), `IndicatorHorizons` (cadence/horizon).
- `prev_as_of` defaults to the **most recent distinct `asOf` in the log strictly before `as_of`** (so the daily
  diff window is automatic; `None` and no prior cycle → an all-`new_pages` first cycle).
- `config` is a `LintConfig` of tunable constants (weights, half-lives, thresholds) with sensible defaults
  (§7) — the policy table.

A new CLI subcommand **`wiki-lint`** (additive, mirrors `wiki-ingest`; **no** `--emit-prompt`/`--recorded` —
there is no brain call):

```
gpu-agent wiki-lint --store <dir> --as-of <date> [--prev-as-of <date>] [--out <file>]
```

Prints the `LintReport` JSON to stdout (or `--out`); emits one idempotent `lint` `LogEvent` per `as_of` (§6).

---

## 2. The materiality score (relevance) — per page-move

**Unit of materiality = the page-move:** one entry per page in the **move-set** for the cycle, aggregating that
page's findings/events. The move-set = the daily `WikiDiff` pages (`new_pages ∪ changed_pages ∪ index_moves`,
de-duplicated by `pageId`) **plus any page flagged `contradictsThesis` this cycle** (a contradiction is always
material even if the diff did not otherwise surface that page). (The diff is page-keyed and the brief surfaces
*threads*.)

For each page in the move-set, the score is an additive factor-base scaled by multipliers:

```
base  = W_new   · [page ∈ diff.new_pages]
      + W_state · [page state or trajectory changed this cycle]
      + W_contra· [page flagged contradictsThesis this cycle]            # the early warning, highest
      + W_ind   · Σ magnitude over the page's NEW findings whose indicatorId is a scoring indicator

score = base · tier_mult · recency_mult · (1 + horizon_boost) · salience_weight
```

- A move can fire several factors; they **add**, then the multipliers scale the sum.
- **Per-page aggregation across the page's contributing (this-cycle) findings:**
  - `tier_mult` — the **best** evidence tier among them: `tier_primary` if any is primary, else `tier_secondary`
    (a page with no this-cycle findings — e.g. a state-only move — uses `tier_secondary`).
  - `recency_mult` — `recency_full` if **any** contributing finding was observed in this cycle, else
    `recency_decayed` (binary; values in §7).
  - `horizon_boost` — `horizon_boost_leading` if **any** contributing finding is `leading`-horizon, else `0`
    (the early-warning case the system exists to catch).
- `salience_weight = max(salience_floor, intrinsic_salience)` — the brain's relevance call lifts a high-salience
  thread's moves, but a brand-new thread (`salience == 0.0`, not yet brain-enriched) still scores on `W_new`.

`score ≥ material_threshold` → the move is **material** (ranked, descending); below → **dropped**. Dropped moves
are **kept in `LintReport.dropped` and counted in the lint log event — never silently truncated** (Part 29).

**Contradiction source.** The `contradictsThesis` flag is the brain's (4-4a). It is read from the `ingest` log
event(s) for the cycle via the shared parser in §5 — never re-derived, never scraped as raw free text.

**Indicator-move "scoring" test.** `W_ind` counts only findings whose `indicatorId` resolves to a **scoring**
indicator in the registry (the same scoring/overlay split the frozen `dmi_smi_contribution` uses) — overlays
(`designWins`, `gpuSpotPrice`) do not inflate materiality through this factor (they may still drive a state
change, which fires `W_state`).

---

## 3. Salience decay (persistence) — per page, non-destructive

The decay reflects **how long a thread has been quiet**, at a rate set by **what kind of signal the thread
carries** (the hybrid: persistence is input-derived; relevance is the brain's `salience`).

```
quiet_age          = number of DISTINCT asOf cycles in the log with prev_material < asOf ≤ as_of,
                     where "material activity" = an append-observation OR a state-change event on the page.
                     (A body-only re-curation does NOT reset quietness — "going quiet" = no new substance.)
half_life(page)    = the LONGEST persistence class among the page's findings (so an important slow signal is
                     not decayed away by the mere absence of daily noise):
                       persistence is keyed on the finding's 4-2 tags —
                         cadence: daily → H_short ; weekly → H_med ; quarterly → H_long
                       with a leading-horizon FLOOR: a leading finding's class is floored at H_med
                       (a forward early-warning signal must not decay at daily speed).
                     An untagged indicatorId → H_med default, and the fallback is LOGGED (Part 29).
decay              = 0.5 ** (quiet_age / half_life)        # asymptotes toward 0, never 0 → page stays in history
effective_salience = intrinsic_salience · decay
stale              ⇔ effective_salience < stale_threshold  # 4-5 fades it from the brief; 4-4c may prune provisionals
```

- **Non-destructive:** `effective_salience` is computed at read-time and reported; the stored brain-set
  `salience` is never rewritten (no `record_state`, no log churn — the run stays replayable).
- **Two complementary outputs.** Materiality ranks *"what moved today"* — a move resets the thread's quietness,
  so a fresh move uses `intrinsic_salience` (its `quiet_age == 0`, `decay == 1.0`). `effective_salience` is the
  decayed steady-state ranking that drives the `stale` flag and 4-5's "fade from brief." Both are in the report.

---

## 4. Structural health checks (pure code)

- **orphans** — pages with no inbound `crossRef` from any other page (computed across `index()`).
- **stale** — pages with `effective_salience < stale_threshold` (from §3).
- **crossRefGaps** — the structural half of the deferred-semantic line:
  - **asymmetric** — page A lists B in `crossRefs` but B does not list A.
  - **mention-without-link** — a page's markdown body contains another page's `title` (token match) but the page
    does not list that page in `crossRefs`.
  - (The pure-semantic *no-mention* case is the deferred follow-up, §11.)
- **contradictions roll-up** — `{pageId, note, asOf}` parsed (via §5) from the `ingest` events in the window.

---

## 5. The contradiction seam (shared helper in `ingest.py`)

4-4a recorded contradictions only as free text in the `ingest` `LogEvent.detail`, and `LogEvent` is frozen
(no new field). The clean seam is a **shared format/parse pair in our own `gpu_agent/wiki/ingest.py`**:

```python
def format_contradiction_detail(enriched_count: int, contradictions: list[tuple[str, str]]) -> str: ...
def parse_contradiction_detail(detail: str) -> dict:   # -> {"count": int, "contradictions": [{"pageId","note"}]}
```

- 4-4a's `apply_enrichment` is refactored to **build its ingest-event detail via `format_contradiction_detail`**
  — one source of format truth, round-trip tested. **Behavior-preserving:** the detail still contains
  `"enriched N page(s)"` and each `"<pageId>: <note>"`, so every existing 4-4a apply test stays green.
- The lint pass reads the cycle's `ingest` event(s) and parses contradictions via `parse_contradiction_detail`
  — never scraping fragile ad-hoc text.
- `LogEvent` (`wiki/log.py`) is untouched (frozen); only the detail *string* construction and our own
  `ingest.py` change.

---

## 6. Provenance & replayability

The lint run appends **one idempotent `lint` `LogEvent` per `as_of`** (the `lint` kind is already reserved in
the 4-1 `LogEvent` literal), with a `detail` summarizing counts (`#material / #dropped / #stale / #orphans /
#contradictions`). It is skipped if a `lint` event for that `asOf` already exists (re-running a cycle is a
no-op, like 4-4a's one-`ingest`-per-`asOf` guard). This keeps the cycle replayable (Part 20) and gives 4-4c a
per-cycle substrate to aggregate for the promotion test. The rich per-page detail lives in the returned
`LintReport` (printed / `--out`), not in the log.

---

## 7. The policy table (`LintConfig`) — tunable defaults

A frozen-by-default config object (a `pydantic` model or dataclass of constants), overridable for tuning/tests:

| Field | Default | Meaning |
|---|---|---|
| `w_contra` | `1.0` | contradiction factor weight (highest — early warning) |
| `w_state` | `0.6` | state/trajectory-change factor weight |
| `w_new` | `0.5` | new-thread factor weight |
| `w_ind` | `0.3` | per-magnitude-point weight for scoring-indicator moves |
| `tier_primary` / `tier_secondary` | `1.0` / `0.6` | evidence-tier multiplier |
| `recency_full` / `recency_decayed` | `1.0` / `0.7` | this-cycle vs older `observedAt` multiplier |
| `horizon_boost_leading` | `0.5` | leading-horizon early-warning boost (else `0`) |
| `salience_floor` | `0.5` | floor in `salience_weight` so new threads still score |
| `material_threshold` | `0.3` | at/above = material; below = dropped (logged) |
| `h_short` / `h_med` / `h_long` | `1` / `3` / `6` | decay half-lives (cycles) by cadence class |
| `stale_threshold` | `0.1` | `effective_salience` below this ⇒ stale |

All numbers are tunable; the score and decay are **explainable** from the per-move factor breakdown and the
per-page decay inputs.

---

## 8. Data model (pydantic, additive)

```python
class IndicatorMove(BaseModel):
    indicatorId: str
    magnitude: int
    scoring: bool

class MoveFactors(BaseModel):
    newThread: bool = False
    stateTransition: Optional[dict] = None      # {"from","to"} when state/trajectory changed
    contradiction: bool = False
    contradictionNote: str = ""
    indicatorMoves: list[IndicatorMove] = []

class MaterialMove(BaseModel):
    pageId: str
    title: str
    type: str                                    # "entity" | "theme" (page-type agnostic)
    status: str                                  # "provisional" | "registered" (carried through, not acted on)
    score: float
    factors: MoveFactors
    contributingFindingIds: list[str] = []
    tierMult: float
    recencyMult: float
    effectiveSalience: float

class CrossRefGap(BaseModel):
    frm: str                                     # serialized as "from"
    to: str
    reason: str                                  # "asymmetric" | "mention-without-link"

class ContradictionEntry(BaseModel):
    pageId: str
    note: str
    asOf: str

class StaleEntry(BaseModel):
    pageId: str
    effectiveSalience: float

class HealthReport(BaseModel):
    orphans: list[str] = []
    stale: list[StaleEntry] = []
    crossRefGaps: list[CrossRefGap] = []
    contradictions: list[ContradictionEntry] = []

class LintReport(BaseModel):
    asOf: str
    prevAsOf: Optional[str] = None
    material: list[MaterialMove] = []            # ranked, descending score
    dropped: list[MaterialMove] = []             # below material_threshold (logged, never silently truncated)
    health: HealthReport
```

(`CrossRefGap.frm` carries a `from`-named serialization alias since `from` is a Python keyword.)

---

## 9. Frozen vs additive (Part 33)

- **Byte-unchanged:** `gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the `Finding` schema, the
  6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, the existing `JsonStore`/`FindingStore`,
  `gpu_agent/wiki/log.py`, `gpu_agent/wiki/page.py`, **every existing member of `gpu_agent/wiki/store.py`**
  (incl. 4-4a's `set_body`), and 4-4a's `slug`/`route_findings`/`build_bundle`/`IngestResult`/`INGEST_SYSTEM`
  in `ingest.py`.
- **Modified (additive / behavior-preserving) in `ingest.py`:** `PageEnrichment` gains the `salience` range
  bound (§10); `apply_enrichment` builds its ingest-event `detail` via the new `format_contradiction_detail`
  (§5) — the emitted detail still contains `"enriched N page(s)"` and each `"<pageId>: <note>"`, so every
  existing 4-4a test stays green. `LogEvent` (`wiki/log.py`) is untouched.
- **Additive:** `gpu_agent/wiki/lint.py` (the lint pass + `LintReport`/`MaterialMove`/`HealthReport`/`LintConfig`);
  the `wiki-lint` CLI subcommand; `format_contradiction_detail`/`parse_contradiction_detail` in `ingest.py`;
  new fixtures + tests. **No new dependency** (pydantic + stdlib).
- **Reuses, does not rebuild:** `WikiStore.diff/index/state_history/observations/log/get_page`,
  `FindingStore.get`, `IndicatorRegistry` (scoring check) + `IndicatorHorizons` (cadence/horizon).

---

## 10. Doctrine

Code computes + gates + stores; the brain already curated (4-4a). **Numbers come only from gated findings**
(Part 17): the materiality factors read structured `Finding`/diff/registry values; 4-4b invents no measured
value and writes none to a page or index. Every materiality score and decay value is **explainable** from its
factor/decay breakdown. **Nothing is silent** (Part 29): dropped (below-threshold) moves are reported and
counted; an untagged indicator's half-life fallback is logged; the cross-ref-gap and stale lists surface health,
they don't hide it. The `lint` log event + non-destructive read-time computation make every cycle **replayable**
(Part 20). 4-4b **mutates no page lifecycle** — it computes and flags; promotion/pruning is 4-4c.

**Folded-in 4-4a deferred Minor:** since 4-4b owns the salience model, add the bound
`PageEnrichment.salience: float = Field(ge=0.0, le=1.0)` + a test (the opus 4-4a review flagged the unbounded
field as a Part-29 silent-acceptance gap; existing recorded fixtures use `0.8`/`0.9`, still valid). The other
4-4a minors (CLI mutually-exclusive flags, file-read `try/except`, test-quality nits) are not 4-4b-relevant and
stay logged.

---

## 11. The 4-4b ↔ 4-4c seam (locked) + design-for-4-4c constraints

**The boundary:** 4-4b produces deterministic **signals**; 4-4c is the **brain discovery + lifecycle** that
*consumes* them — 4-4c's promotion test ("persists + corroborated across cycles", Part 10) reads 4-4b's
per-cycle materiality; 4-4c's pruning of quiet provisionals reads 4-4b's `stale` flag. No harmful overlap.

**The one gap the deferral creates (logged, not silently dropped):** purely-semantic **entity↔entity** cross-ref
suggestions where neither page textually mentions the other are caught by neither 4-4b's structural heuristic nor
4-4c's theme-discovery. **Resolution:** the structural heuristic (§4) covers the common *mention* case; the rare
pure-semantic case is a **deferred follow-up — a future optional lint brain-seam** (an `--emit-prompt`/`--recorded`
seam over the index, like `wiki-ingest`).

**Five constraints 4-4b honors now so 4-4c forces no rework:**
1. **Page-type agnostic** — the lint operates on *all* pages (`entity` *and* `theme`); when 4-4c adds theme
   pages they get materiality/decay/health for free. (The 4-4a *writer* was entity-only by design; this *reader*
   is not.)
2. **Status-agnostic scoring, status carried through** — score `provisional` and `registered` alike; surface
   `status` on each `MaterialMove` so 4-5/4-4c can act on it.
3. **No lifecycle mutation** — 4-4b never promotes/prunes/demotes.
4. **Emit `lint` `LogEvent`s** — a replayable, aggregatable corroboration substrate for 4-4c.
5. **Decay emits the `stale` signal** that 4-4c's provisional-pruning consumes.

---

## 12. Test strategy (deterministic; committed-fixture pattern)

- **Decay:** `quiet_age` counts distinct `asOf` cycles since the last *material* event (a body-only edit does not
  reset it); half-life class selection from `cadence × horizon` (daily→short, quarterly→long, leading floored at
  med; longest-class-wins on a mixed thread; untagged→med + logged); `decay = 0.5**(age/H)` values;
  `effective_salience`; `stale` threshold.
- **Materiality:** each factor fires correctly (new / state / contradiction / indicator ∝ magnitude, scoring-only);
  multipliers (tier, recency, leading horizon boost, `salience_floor`); `material_threshold` → material vs
  **dropped** (dropped present in the report).
- **Contradiction seam:** `format`/`parse` round-trip; the lint pass reads the contradiction from the `ingest`
  detail; the existing 4-4a `apply_enrichment` tests stay green after the detail refactor.
- **Health:** orphans; stale; asymmetric crossRef; mention-without-link.
- **Page-type agnostic:** a theme-page case (built via the store API even though 4-4a writes only entities) is
  scored + decayed + health-checked.
- **CLI:** `wiki-lint` end-to-end on a seeded store (route + ingest, then lint) → a well-formed `LintReport`;
  exactly one idempotent `lint` `LogEvent` per `asOf`.
- **Salience bound:** `PageEnrichment(salience=5.0)` is rejected; `0.0`/`1.0` accepted.
- **Guards:** frozen-contract `git diff` empty; committed golden/recorded fixtures byte-unchanged; full suite
  green (baseline after 4-4a: **300 passed, 3 skipped**, plus the new tests).

---

## 13. Out of scope (later 4-4 pieces / arcs)

- **Semantic (no-mention) cross-ref suggestions** → a future optional lint brain-seam (§11 deferred follow-up).
- **Theme pages, the `explore` budget, provisional off-registry discovery, quarantine, promotion/pruning
  actions** → 4-4c.
- **Daily gather mode, the numeric scrape sweep, cross-run dedup-vs-store** → 4-4d.
- **The brief render** of the ranked materiality + decayed ranking → 4-5.
- **Rewriting (decaying) the stored `salience`** — decay stays read-time / non-destructive.

---

## 14. Acceptance (4-4b)

1. `lint(...)` produces a **ranked `material` list** over the daily diff (the 4 factors with the hybrid
   weighting), and a **`dropped` list** of below-threshold moves — nothing silently truncated.
2. **Salience decay:** per-thread half-life **input-derived** from the 4-2 `cadence × horizon` tags
   (longest-class-wins; leading floored; untagged→default+logged), `quiet_age` by cycle-count, **non-destructive**
   `effective_salience`, and a `stale` flag.
3. **Structural health:** orphans, stale, asymmetric + mention-without-link cross-ref gaps, contradiction roll-up.
4. **Contradiction read via the shared `ingest` helper** (round-trip tested); 4-4a's `apply_enrichment` refactored
   to share the formatter, all existing 4-4a tests green.
5. **Page-type & status agnostic; no lifecycle mutation;** one **idempotent `lint` provenance event** per `asOf`.
6. **`PageEnrichment.salience` bounded `[0,1]`** (folded 4-4a Minor).
7. **`wiki-lint` CLI** prints/persists a `LintReport`. Frozen contract + committed fixtures byte-unchanged; pure
   code, **no new brain step**, no new dependency; full suite green.
