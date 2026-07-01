# Per-category Market-State brief render (sub-project 4-5) — design

- **Date:** 2026-07-01
- **Status:** Draft for review (the human-facing render of the daily monitor — the first cut)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md);
  the output **design target** [`2026-06-29-human-market-brief-design-target.md`](2026-06-29-human-market-brief-design-target.md)
  (the north star this renders toward); charter **Part 35** (the surface is a projection *consumer*, not a writer),
  **Part 17** (numbers only from gated findings; plain language, no unearned magnitude), **Part 20** (replayable /
  byte-reproducible).
- **Depends on:** sp3-A `report.py` (`load_scorecard`/`find_prior`/`compute_sdgi`/`render_report` + the wording
  helpers `_momentum_word`/`_sdgi_interpretation`/`_fmt_delta`/`_signal_label`/`render_evidence_quality`/
  `render_coverage_gaps`), sp3-B (`dimensionStatus`/`categoryStatus`), 4-2 (`registry/horizon.py` `IndicatorHorizons`
  — the `cadenceHorizon` tags for the leading-signal flag), 4-3 (`Scorecard.indices`: Momentum/Outlook/Divergence).
- **Feeds:** 4-5b (the deferred store-fed sections — "what moved" + storylines — wired to the wiki store) and the
  later HTML dashboard (a second projection over the same Scorecard).

---

## 0. What 4-5 is — scope + the locked decisions

Sub-project **4-5** renders the **per-category Market-State brief** — `merchant-gpu`'s own lane — by **extending
A's `report.py`** into the brief-first human artifact the design target describes (§2's five readability rules over a
single category's data). It is a **pure deterministic projection of the `Scorecard`** — no LLM in the renderer, no
new number, byte-reproducible (Part 35 / Part 20). The full cross-cutting GPU-market brief (the design-target §3 mock)
remains a **layer-tier product** for a later arc; 4-5 renders one category's lane in the same shape.

**Locked decisions (from this session's brainstorm — don't relitigate):**
- **(a) Scope = the scorecard-derivable sections only, this cut.** The brief renders three new live sections —
  **STATE OF THE MARKET** (BLUF), the **DEMAND | SUPPLY board**, and a **TRUST & COVERAGE** caveat — plus the
  existing detailed scorecard sections as drill-down. The **store-fed** sections (**WHAT MOVED** = the 4-1 wiki
  `diff`; **STORYLINES** = wiki page state/trajectory over cycles) and the judgment **WHY** tree are **DEFERRED to
  4-5b**; this cut shows them as a one-line honest **placeholder stub** so the shape is visible. Rationale: the
  chosen sections project cleanly from today's `Scorecard` alone; the store-fed sections need a *multi-cycle* wiki
  store to be meaningful, which only accrues after repeated 4-4a/4-4d runs.
- **(b) The default `report` command is the single unified artifact — brief-first.** No new subcommand, no flag:
  typing `report` gives everything, led by the market brief (inverted-pyramid rule 1: BLUF first, detail below).
- **(c) New module `gpu_agent/brief.py` holds the new renderers; `report.py`'s `render_report` composes them at the
  top.** The brief logic lives in its own focused, independently-testable unit and **reuses** `report.py`'s pure
  helpers rather than duplicating them; `report.py` gets only a minimal additive composition edit (prepend the brief
  sections + an optional `horizons` kwarg). Both `Scorecard` and `report.py` are on the additive list, not frozen.
- **(d) Honesty: no invented magnitude words on the unscaled indices (Part 17).** `report.py` already refuses this —
  `_momentum_word` returns only `positive/negative/flat` because "the contribution has no fixed 0..1 scale, so
  'slight'/'strong' would be unearned." The brief therefore **leads with direction + change** (the Δ-vs-prior *is*
  the signal — rule 2) and takes **earned rating words only from the brain's bounded-scale judgment** fields
  (`categoryStatus` rating/direction/bottleneck; per-signal `_signal_label`). The mock's vivid "ACCELERATING/STRONG"
  on a raw DMI is **explicitly rejected** as unearned.
- **(e) Pure Scorecard projection — no wiki store read this cut.** Every live section reads only the `Scorecard`
  (`demandSupply`, `indices`, `categoryStatus`, `dimensionStatus`, `findings`, `confidence`, `sources`) + the
  `registry`/`horizons` the report already loads. The wiki store enters only in 4-5b.

---

## 1. Architecture

A new pure module **`gpu_agent/brief.py`** (additive, imports `report.py`'s helpers) provides the new section
renderers. `report.py`'s `render_report` is edited additively to compose them brief-first and to accept the optional
`horizons` the board needs; the existing eight `render_*` helpers and their order below the brief are unchanged.

```python
# gpu_agent/brief.py  (new)
def render_state_of_market(sc: Scorecard, prior: Optional[Scorecard]) -> str: ...     # BLUF
def render_demand_supply_board(sc: Scorecard, horizons: Optional[IndicatorHorizons]) -> str: ...
def render_deferred_stubs() -> str: ...                                                # what-moved/storylines stubs
def render_market_caveat(sc: Scorecard) -> str: ...                                    # trust footer caveat
```

```python
# gpu_agent/report.py  (additive edit to render_report only)
def render_report(sc, prior, registry, render_ts=None, *, horizons=None) -> str:
    sections = [
        render_header(sc, render_ts),
        brief.render_state_of_market(sc, prior),        # NEW  ── BLUF
        brief.render_demand_supply_board(sc, horizons), # NEW
        brief.render_deferred_stubs(),                  # NEW  ── "in 4-5b" stubs
        render_overall_status(sc),                      # existing detail (drill-down) …
        render_dimensions(sc, prior),
        render_dmi_smi_sdgi(sc, prior),
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
        brief.render_market_caveat(sc),                 # NEW  ── trust footer
    ]
    return "\n\n".join(sections)
```

- **Data flow:** the CLI `_report` handler already loads `sc` + optional `prior` + `registry`; it additionally loads
  `horizons = IndicatorHorizons.load("registry/indicators.json")` (the same call `wiki-lint`/`run` use) and passes it
  to `render_report(..., horizons=horizons)`. When `horizons` is `None` (a caller that doesn't supply it), the board
  degrades gracefully — it omits the leading-signal tag rather than failing.
- **Backward compatibility:** `horizons` is a new **optional keyword**; every existing `render_report` caller keeps
  working unchanged (the brief sections still render; only the leading tag is absent without `horizons`).

---

## 2. The three live sections

### ① STATE OF THE MARKET (BLUF) — `render_state_of_market(sc, prior)`
Projects `demandSupply` + `indices` + `categoryStatus`:
```
STATE OF THE MARKET
  <categoryStatus.rating>, <categoryStatus.direction> — <categoryStatus.reason>   ◀ brain-earned headline (if present)
  Demand momentum: <positive|negative|flat> <▲|▼|=>   (DMI <dmi>, Δ <±d> vs <prior.asOf>)
  Supply momentum: <positive|negative|flat> <▲|▼|=>   (SMI <smi>, Δ <±d>)
  Gap:             <_sdgi_interpretation(SDGI)>        (SDGI <sdgi>, Δ <±d>)
  NOW (Momentum): <word> <arrow>     NEXT (Outlook): <word|"insufficient coverage">
  ⚠ DIVERGENCE: <indices.divergence.note>              (omitted / "aligned" when state == aligned)
  BINDING CONSTRAINT: <categoryStatus.bottleneck>      (omitted when categoryStatus is None)
```
- **Words** come from `_momentum_word` (direction only) + `_fmt_delta` (the change) + `_sdgi_interpretation`
  (existing gap wording) + `categoryStatus` (the earned rating/direction/bottleneck/reason). **No magnitude adjective
  is ever derived from DMI/SMI.**
- **NOW / NEXT** read `indices.momentum` and `indices.outlook` (each a `DemandSupply`) via the same direction-word
  mapping; **Outlook honestly reads "insufficient coverage"** when `indices.divergence.state ==
  "insufficient-coverage"` (the expected state until 4-4 feeds leading findings — 4-3 already reports this).
- **Divergence** reads `indices.divergence` (the 4-state verdict + note); a leading `⚠` only when diverging.
- Every optional field degrades: no `categoryStatus` → drop the headline + BINDING CONSTRAINT lines; no `indices` →
  drop NOW/NEXT + DIVERGENCE. The section never invents a value it doesn't have.

### ② DEMAND | SUPPLY board — `render_demand_supply_board(sc, horizons)`
Two columns from `sc.findings` grouped by `finding.side` (`demand` | `supply`):
- **Collapse to latest vintage per `indicatorId`** (max by `(capturedAt, observedAt, magnitude)` — the *same*
  collapse the frozen `dmi_smi_contribution` uses), so each indicator shows once.
- Each row: `<indicator label>  <_signal_label(score)>  <direction arrow from finding.trend>` where **`score`
  reuses the exact per-finding scoring `render_entity_panel` already uses** — `polarityDemand * magnitude` in the
  demand column, `polaritySupply * magnitude` in the supply column (fed to the existing `_signal_label`). When
  `horizons` is present and the indicator's horizon is `leading`, add a **`leading`** tag; add a **`⚠carried`** flag
  when the collapsed finding's `asOf` predates `sc.asOf` (a stale carry-over, not a fresh read — no fragile day-math).
  The trend→arrow map is a small deterministic lookup over `finding.trend`.
- Rows ordered deterministically (by `indicatorId`); an empty side prints an honest "(no demand/supply findings)".

### ③ Deferred stubs — `render_deferred_stubs()`
Two fixed lines, honest about the seam:
```
WHAT MOVED SINCE LAST RUN
  (rendered in 4-5b — needs a multi-cycle wiki store)
STORYLINES
  (rendered in 4-5b — needs a multi-cycle wiki store)
```

---

## 3. Trust & Coverage footer

The existing `render_evidence_quality` (finding counts, primary/secondary split, under-supported dimensions from
`dimensionStatus`) and `render_coverage_gaps` (paywalled/estimate-grade + missing-indicator gaps) already carry the
trust content — **reused unchanged** as the footer body. 4-5 adds one honest **caveat** line
(`render_market_caveat`): *"index level varies run-to-run until the 4-4 memory stabilizes it — read DIRECTION, not
level"* (design-target §3). No content is duplicated; the caveat is the only new trust element.

---

## 4. Determinism (Part 20)

Byte-reproducible: same `Scorecard` (+ prior) → same brief. No wall-clock in `brief.py`; the only clock read stays in
`render_report` behind the injected `render_ts` (existing `--render-ts` flag). Recency/carry-over is derived from
data (`finding.asOf` vs `sc.asOf`), never from "now". Section order is fixed; board rows and board columns are
ordered by `indicatorId`.

---

## 5. Frozen vs additive (Part 33)

- **Byte-unchanged (frozen):** `gate.py`, `scoring.py`, `registry/indicators.py`/`validate.py`, the `Finding` schema,
  the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, `store.py`, all `gpu_agent/wiki/` modules,
  `gpu_agent/gathering/`. 4-5 only *reads* the `Scorecard` and *reuses* `report.py`/`horizon.py`.
- **Additive:** the new module `gpu_agent/brief.py`; a minimal additive edit to `report.py`'s `render_report`
  (prepend the brief sections + append the caveat + accept the optional `horizons` kwarg — the existing eight
  `render_*` helpers and their relative order are untouched); the CLI `_report` handler loads `horizons` and passes
  it. **No new dependency** (pydantic + stdlib). **No new `Scorecard` field** (this cut reads existing fields only).
- **Reuses, does not rebuild:** `load_scorecard`/`find_prior`/`compute_sdgi`/`_momentum_word`/`_sdgi_interpretation`/
  `_fmt_delta`/`_signal_label`/`render_evidence_quality`/`render_coverage_gaps`; 4-2's `IndicatorHorizons`; 4-3's
  `Scorecard.indices`; the frozen scorer's latest-vintage collapse rule (re-expressed, read-only).

---

## 6. Doctrine

Pure projection — the renderer writes no number (Part 35/17). **Honest** (Part 17): magnitude words come only from
the brain's bounded-scale judgment (`categoryStatus`/`_signal_label`); the unscaled DMI/SMI carry direction + change
only; Outlook says "insufficient coverage" rather than faking a forward read; single-source / carried / stale signals
are flagged. **Replayable** (Part 20): byte-reproducible, clock injected. **Nothing silent** (Part 29): every
finding side is grouped and shown; deferred sections are stubbed, not omitted; degraded/absent optional data prints an
honest note rather than vanishing.

---

## 7. The 4-5 → 4-5b seam

4-5 ships the scorecard-derivable brief. The deferred **4-5b** will wire the **wiki store** into the render for the
two store-fed sections — **WHAT MOVED** (the 4-1 `diff`'s `new_pages ∪ index_moves`, ranked by 4-4b materiality) and
**STORYLINES** (wiki page `state`/`trajectory`/last-change recency, filtered by 4-4c's `partition_canonical` so
`registered` pages are canonical coverage and `provisional` pages render "confidence-capped") — replacing the two
stub lines. Because 4-5 already fixes the brief-first shape and the stub anchors, 4-5b is a drop-in of two renderers,
no restructuring. The **WHY** tree (judgment prose) is a later refinement once the judgment carries a driver→constraint
structure.

---

## 8. Test strategy (deterministic; committed-fixture)

- **Fixtures:** reuse/extend the committed `fixtures/report/` scorecards; ensure one carries `indices` (Momentum/
  Outlook/Divergence) and `categoryStatus` so the BLUF + NOW/NEXT render (add a small committed fixture if the
  existing ones lack `indices`).
- **STATE header:** demand/supply lines show `positive/negative/flat` + the Δ-vs-prior; the gap line reuses
  `_sdgi_interpretation`; NOW/NEXT read `indices`; Outlook renders "insufficient coverage" for that divergence state;
  BINDING CONSTRAINT reads `categoryStatus.bottleneck`; each optional field's absence degrades cleanly (no
  `categoryStatus`/`indices` → those lines drop, no crash).
- **Honesty invariant (the locked test):** for a scorecard whose `categoryStatus.rating` is e.g. "Strong", the words
  `strong`/`accelerating`/`weak` appear **only** on the `categoryStatus` headline line — the DMI/SMI momentum lines
  carry no magnitude adjective (only `positive`/`negative`/`flat`). Locks decision (d) against a future regression.
- **DEMAND|SUPPLY board:** findings group by side; multiple vintages of one indicator collapse to the latest; the
  `leading` tag appears only for `horizon=="leading"` indicators when `horizons` is supplied and is absent when it is
  not; a finding with `asOf < sc.asOf` shows `⚠carried`; an empty side prints the honest note.
- **Deferred stubs:** both stub lines present and name 4-5b.
- **Composition + determinism:** `render_report` emits the sections in the brief-first order; two renders with the
  same inputs + `render_ts` are byte-identical; existing `report` tests still pass (the detailed sections are
  unchanged, just preceded by the brief).
- **CLI end-to-end:** `report <fixture>` prints brief-first output; `--render-ts` makes it byte-stable.
- **Guards:** frozen-contract `git diff` empty (gate/scoring/schema/registry code/pipeline/store/wiki/gathering);
  committed fixtures byte-unchanged except any new `fixtures/report/` addition; full suite stays green (baseline
  **382 passed, 3 skipped** + the new tests).

---

## 9. Out of scope (deferred)

- **WHAT MOVED + STORYLINES from the wiki store** → 4-5b (this cut stubs them).
- **The WHY / driver→constraint tree** → later (needs a judgment structure beyond `categoryStatus.reason`).
- **The HTML dashboard** → a later projection over the same Scorecard (design-target §1).
- **The cross-cutting LAYER/market brief (the §3 mock's cross-category signals)** → the deferred layer-tier arc
  (design-target §0); 4-5 is one category's lane.
- **A new `Scorecard` field** → not needed; 4-5 reads existing fields only.

---

## 10. Acceptance (4-5)

1. **Brief-first unified `report`:** the default `report` command emits, top-to-bottom, the header → STATE OF THE
   MARKET → DEMAND|SUPPLY board → WHAT-MOVED/STORYLINES stubs → the existing detailed sections → TRUST & COVERAGE
   footer (with the caveat). No new subcommand/flag.
2. **STATE header** projects `demandSupply` + `indices` + `categoryStatus` with direction + Δ-vs-prior, the earned
   `categoryStatus` headline + BINDING CONSTRAINT, NOW/NEXT from the two indices, and Divergence; Outlook honestly
   reads "insufficient coverage" when that is the state; absent optional fields degrade cleanly.
3. **DEMAND|SUPPLY board** groups findings by side, collapses to latest vintage per indicator, tags leading signals
   (when `horizons` supplied) and flags carried/stale findings; deterministic order.
4. **Honesty invariant** locked by test: no magnitude adjective is derived from the unscaled DMI/SMI; magnitude words
   come only from `categoryStatus`/`_signal_label`.
5. **Deferred sections** appear as honest one-line stubs naming 4-5b (nothing silently omitted).
6. **Pure, deterministic, additive:** no wiki-store read; byte-reproducible (clock injected); frozen contract
   byte-unchanged; new `brief.py` + additive `render_report`/CLI edits only; no new dependency; the full suite stays
   green.
7. **Feeds the sequence:** the stub anchors + brief-first shape let 4-5b drop in the two store-fed renderers with no
   restructuring; the same Scorecard projection later backs the HTML dashboard.
