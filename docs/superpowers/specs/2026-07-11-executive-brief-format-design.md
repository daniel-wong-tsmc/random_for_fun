# Executive brief format (F78 §5.8 amendment) + F79 index-rebuild decision (design)

- **Date:** 2026-07-11
- **Status:** Design complete. Part A (format) lands as an amendment to the F78 stage-6 plan;
  Part B (F79) is a **decision record** — the rebuild gets its own full spec when it starts.
- **Provenance:** every decision below is **user-approved 2026-07-11** in an interactive session
  (not AFK-default). See §9. One decision (E6) went **against the assistant's recommendation**;
  recorded as such.
- **Inputs:** the user's blind-ablation verdict (2026-07-06, `docs/action-items.md`) — desk won on
  substance, lost on format ("scattered", "way too much information", "order by importance"); the
  externally authored SDEWS spec that arrived 2026-07-11
  (`docs/AI供需早期預警系統 SDEWS 規格書 v1.0.docx`, summarized + gap-mapped in
  `docs/2026-07-11-sdews-metric-extraction.md`); the approved F78 design
  (`docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md`).

---

## 1. Problem

The reader persona is a non-technical executive. The current daily `report.txt` is ~180 lines,
lists all 14 tracked calls in full, and keeps its verdict tiles (bands/arrows) mid-page under
STATE OF THE MARKET. F78's approved renderer (D7/D8) fixes the body (change-first lead,
importance-ranked capped calls, length budget) but has **no page-topping executive band** and
**no single at-a-glance severity signal**. Separately, the desk's DMI/SMI are news-flow scores
with ~5 weeks of history — no statistically defensible thresholds and no honest deep backtest —
which the user flagged as the bigger concern.

## 2. Decisions (all user-approved 2026-07-11)

- **E1 — One structure, both renders.** One executive page structure; the daily text brief and the
  HTML dashboard (`gpu_agent/dashboard/`) both render it. The two surfaces must tell the same story.
- **E2 — Top band = word tiles + alert color, no raw indices.** Three tiles (Demand / Supply / Gap)
  as five-word-band words + arrows + "(was X)", an overall alert dot (GREEN/YELLOW/ORANGE/RED with
  "(was X)"), the binding constraint, and a one-line since-yesterday count. Raw DMI/SMI/SDGI stay in
  the appendix/trust footer (standing decision: read direction, not level).
- **E3 — Body order: change-first, capped.** WHAT CHANGED (3 horizons) → TOP CALLS (top 5 by
  importance, rest one line each) → WHY (one paragraph) → trust footer → appendix. This is F78 D7
  plus an explicit top-5 cap with one-line collapse.
- **E4 — No TSMC section yet.** F65 ("so what for TSMC") stays a separate later feature; the layout
  does NOT reserve a slot.
- **E5 — Delivery = Approach 1.** Amend the F78 design (§5.8) and the stage-6 plan with additive
  tasks; no separate renderer feature, no restyle of the pre-F78 report.
- **E6 — F79: full SDEWS-style index rebuild (scoring v2.0).** The index layer is re-architected as
  monthly, vintage-stamped indicator time series scored vs. their own history (z-scores), σ-band
  alert thresholds, and a 2023→now backtest. **Assistant recommended the incremental two-layer
  option; the user chose the full rebuild** — recorded per F76 provenance discipline. Details §6.
- **E7 — Sequencing: finish F78 first.** F78 stages 2/3/6 land (and reviewed stages 4/5 merge)
  before F79 starts. The renderer ships with the rule-based alert ladder (§4); F79 later swaps the
  trigger engine to σ-bands with the page unchanged.

## 3. Part A — the executive page (one structure, both renders)

Top to bottom (text render shown; the dashboard renders the same sections in the same order,
reusing its existing tile/plain-language machinery from the 2026-07-06 dashboard design §4b/§4c):

```
MERCHANT GPU — DAILY — 2026-07-11              ● YELLOW (was GREEN)
┌─────────────┬─────────────┬──────────────────┐
│ DEMAND      │ SUPPLY      │ GAP              │
│ Strong ▲    │ Tight ▼     │ Widening ⚠       │
│ (was Firm)  │ (was Tight) │ shortage forming │
└─────────────┴─────────────┴──────────────────┘
Binding constraint: HBM memory scarcity
Since yesterday: 1 call strengthened · rest unchanged since 07-08

WHAT CHANGED                        ← F78 stage-6 Task 5, as planned
  Since yesterday …  / Since last week … / Since last month …
  (explicit "unchanged since <date>" lines)

THE TOP CALLS (5 of N, by importance)   ← F78 stage-6 Task 7, cap = 5
  ● <call>  <conviction> <arrow>  … breaks if: …
  (N−5 more, one line each)

WHY (one paragraph)

TRUST (evidence freshness, thin spots)
──────────────── APPENDIX (unchanged, below the fold) ────────────────
```

- **Tile content source:** the existing five-word band map (`gpu_agent/bands.py`) + scorecard
  demand/supply directions + gap phrase — all already computed; the top band is a *projection*,
  no new judgment.
- **"(was X)"** comes from the change engine's 1-day horizon (nearest stored run at/before);
  when no prior run exists, tiles render without the "(was)" clause.
- **Exec-plain rule:** everything above the appendix passes `reader.lint_acronyms` (existing
  voice-lint machinery); dimension ids map through `reader.DIM_LABEL` (stage-6 Task 5).
- **Quick-glance tiers (F78 D8/Task 6)** stay, rendered after WHAT CHANGED — they are the
  numbers-with-age block; the top band is the words-only verdict.

## 4. Part B — alert color v1 (rule-based, deterministic)

Computed in the change module from stored state only (pure projection — replayable, $0, no
brain involvement, no new stored field; the prior run's color is recomputed the same way).

- **Inputs:** the 1d/7d horizon diffs (gap band, demand/supply bands, binding constraint),
  thesis events within the 7d window (conviction/status moves, breaks/retires), and call
  co-movement counts.
- **Ladder (first match from the top wins):**
  - **RED** — reserved for a confirmed structural break: a HIGH-conviction call BROKEN *and* the
    gap band flipped within 7d. Expected never to fire in v1; defined so the state machine is total.
  - **ORANGE** — any two YELLOW triggers co-occurring (two *distinct rules*; two rules fed by the
    same single event count as two — co-occurrence is measured at the rule level, pinned by the
    truth-table tests); or a HIGH-conviction call broke/retired within 7d; or the **asymmetric
    demand-reversal rule**: demand band worsened AND the gap moved toward glut within 7d (this
    pair alone escalates — a demand reversal is the miss the reader can least afford).
  - **YELLOW** — any one of: the gap band changed within 7d; a HIGH-conviction call moved
    (strengthened/weakened/challenged) within 7d; the binding constraint rotated within 7d;
    ≥2 calls moved in the same direction within 7d.
  - **GREEN** — none of the above.
- **Anti-flapping (de-escalation):** a color may only step DOWN after 2 consecutive runs whose
  raw evaluation is lower; any single calm run keeps the prior color ("was" shows the raw move).
  Escalation is immediate.
- **Upgrade path (F79):** the ladder, page, and "(was X)" semantics are frozen here; F79 replaces
  only the trigger definitions (rule hits → σ-band crossings + ΔSDGI momentum). No renderer rework.

## 5. Delivery (E5) — amendment mechanics

1. **Amend the F78 design doc** (§5.8): add the top band + alert ladder by reference to this spec.
2. **Add tasks to the stage-6 plan** (`2026-07-08-f78-stage6-change-first-renderer.md`):
   - Task 5b `change.py::alert_color(change_report, thesis_events) -> AlertState` (ladder above,
     TDD; includes the de-escalation memory derived from recomputing prior runs).
   - Task 5c `report.py::render_top_band(state, change, alert)` (tiles + color + constraint +
     since-yesterday line; lint-clean; deterministic).
   - Task 8 amendment: page order = TOP BAND → WHAT CHANGED → QUICK GLANCE → ranked calls;
     `_ABOVE_FOLD_BUDGET` accounts for the ~9 top-band lines.
   - Task 11 (new): dashboard parity — `gpu_agent/dashboard/build.py` consumes the same
     `ChangeReport`/`AlertState` for its headline band (tiles gain the alert dot + "was";
     a WHAT CHANGED section is added above "Top signals").
3. **Safety:** renderer/code only — no emitted brain-prompt bytes change (**F6 pin stays green**);
   frozen core untouched; when `change is None` output stays byte-identical to today (stage-6
   Task 8 invariant), so all existing report tests hold.
4. **Owner note:** stage 6 is unstarted and unclaimed (no worktree). Whichever instance claims it
   executes the amended plan; stages 4/5 sit DONE awaiting the user's merge review, and stages 2/3
   remain before stage 6 can build.

## 6. Part C — F79 decision record (SDEWS-style scoring v2.0)

**Logged as F79 in `docs/fix-backlog.md`. This section records scope + constraints; the feature
gets its own brainstorm → spec → plan when it starts (after F78, E7).**

- **What it is:** re-architect the index layer per the SDEWS spec's §5: each scoring indicator
  becomes a **monthly time series** with true publication vintages (`observed_at` vs
  `captured_at` discipline — matches our F52 vintage ids); values scored as **z-scores vs the
  series' own rolling history** (36-month target window; younger series borrow same-class
  distributions until the window fills); DMI/SMI = weighted z-sums with freshness decay;
  SDGI = DMI − SMI with a **ΔSDGI momentum trigger**; alert σ-bands with SDEWS's asymmetric
  demand-reversal sensitivity; event-type signals enter as **impulses with ~8-week half-life**.
- **What happens to the news-flow machinery:** gates/findings/thesis book are NOT deleted — they
  become the event-signal channel (impulses + qualitative overlay + the thesis book), no longer
  the index backbone. Extraction/judgment stay Claude-brained (standing decision #3 unchanged).
- **Data is the long pole:** 4–6 series backfilled 2023→now from dated archives (EDGAR filings,
  TWSE monthly revenue, official statements). Indicator shortlist = the adoption order in
  `docs/2026-07-11-sdews-metric-extraction.md` §6 (leading supply S1/S2 first, then D1 hyperscaler
  capex revisions, D9 ODM monthly revenue…). Known limits recorded honestly: subscription series
  (TrendForce/DRAMeXchange contract pricing) are out — inventoried, never scraped (charter);
  the news-flow layer's own deep history cannot be reconstructed without hindsight bias, which is
  WHY the series layer becomes the backtest spine.
- **Backtest discipline (acceptance shape, to be finalized in the F79 spec):** replay strictly by
  capture vintage (no look-ahead); score recall on the known 2023–2025 turning points (H100
  crunch onset, CoWoS bottleneck, HBM squeeze), false-alarm rate at orange+, and average lead
  time; **no weight tweaks off a single miss** (SDEWS §10.2) — recalibration is periodic and
  backtest-gated, mirroring our F73 eval-governance instinct.
- **Contract mechanics:** a **frozen-core versioned migration (Part 33) — scoring v2.0**. It
  **absorbs the deferred F60 scoring half** (the reserved v1.5 side-semantics slot is superseded);
  replay fidelity for every stored v1.x scorecard must be preserved (the F60 weight-freeze test is
  the precedent). Schema changes, if any, ride the same migration. Every gate is user-signed —
  never AFK.
- **Also resolves:** the F60 `smiContribution: 0.0` residual (leading supply series exist in the
  new layer); the alert ladder's σ upgrade (§4); SDEWS mechanisms adopted en route (dual polarity
  per signal, indicator lifecycle status, platform-changeover down-weighting — per the extraction
  doc §4).

## 7. Non-goals

- **F65** ("so what for TSMC") — excluded (E4), no layout slot reserved.
- **Raw indices at the top of the page** — explicitly rejected again (E2).
- **Recorded/demo-mode changes, gather changes, brain-prompt changes** — none here.
- **F79 implementation detail** (series store schema, exact z-window mechanics, backfill tooling) —
  deferred to the F79 spec by design.

## 8. Testing (Part A; F79 tests live in its own spec)

- **Unit (TDD, per amended stage-6 tasks):** alert ladder truth table (each trigger, combinations,
  RED reserved case, first-match precedence); de-escalation memory (2-calm-run rule, immediate
  escalation); top-band renderer (tiles, "(was)" presence/absence with/without prior run, lint
  clean, deterministic byte output); dashboard parity (same AlertState → same color/labels).
- **Invariants held:** `change is None` → byte-identical legacy output; suite green at merge;
  eval pin green (no prompt bytes); no wall-clock anywhere (all day-math via `asOf` labels).

## 9. Decision provenance

E1–E7 were answered by the user in an interactive session on 2026-07-11 (AskUserQuestion choices
+ explicit "go ahead" on the design). E6 (full rebuild) was chosen **against the assistant's
recommendation** (incremental two-layer option) — per F76 vocabulary this is `user-approved`,
with the disagreement noted for the record. The SDEWS source document remains **untracked** in
`docs/` pending the user's call on committing a third party-authored file.

## 10. Backlog impact

- **F78**: stage-6 plan grows Tasks 5b/5c/8-amendment/11; design doc §5.8 amended by reference.
- **F79**: NEW entry (this spec §6 is the record). Absorbs F60's deferred scoring half;
  supersedes the "v1.5 side-semantics migration" slot (v1.5 → v2.0).
- **F60**: stays open until F79 lands its supply series + side-semantics; cross-referenced.
- **F64/F77**: unchanged — still delivered by F78 stage 6 (now including the top band).
- **F65/F66**: unchanged, separate.
