# Scoring v2.0 migration — F79 (SDEWS-style series layer)

The fourth sanctioned frozen-core migration (charter Part 33) and the flagship of the
2026-07-13 wave: the index layer becomes monthly, vintage-stamped indicator time series
z-scored against their own rolling history, with σ-band alerts and a 2023→now backtest.
Spec: `docs/superpowers/specs/2026-07-13-f79-scoring-v2-design.md` (user-approved
2026-07-13). Plan: `docs/superpowers/plans/2026-07-13-f79-scoring-v2.md`. Four
user-signed gates (G1 backfill, G2 backtest, G3 bundled eval re-gate, G4 cutover) —
**only the user advances a gate, never AFK**. v1.x scoring paths stay byte-identical;
replay fidelity is pinned by test before any v2 path ships.

Status ledger lives in the plan. This note records the DATA layer: where every backfilled
point comes from and how each series value is constructed.

## Absorptions

- Absorbs the deferred **F60 scoring half**: S1/S2 are the leading supply series that close
  the standing `smiContribution: 0.0` residual. The reserved v1.5 side-semantics slot is
  **superseded** by this v2.0 migration.

## Backfill discipline (F52 vintage rules, applied per point)

- `publishedAt` = the REAL historical publication date of the source (article dateline,
  press-release date, filing date, or archive-snapshot date). Never the capture date.
- `capturedAt` = the date we recorded the point (2026-07 backfill session).
- No look-ahead: the backtest reads series via `latest_by_period(..., as_of=month)`, which
  hides every point whose `publishedAt` is after the replay month.
- Where an archive table proves a value but not its exact announcement date, the point uses
  the regulatory/conventional deadline (noted per point, e.g. TWSE's 10th-of-following-month
  rule) and the note says `date approximated`.
- D4/X5 points reconstructed from news carry `estimateGrade: true` (spec-mandated); any
  OTHER series point whose value is a quantified estimate from qualitative statements is
  ALSO estimate-marked (honesty over minimum compliance).
- A month with no honest source is an honest gap — never interpolated in the store. (The
  engine, not the store, decides how gaps are carried; that is Stage 3's freshness decay.)

## Source map (Task 2.1)

| series | anchor sources | cadence of raw evidence |
|---|---|---|
| `pkgCapacityOrderSpread` (S1) | TSMC earnings statements; OSAT/tool-maker signals; free trade press (Reuters, Tom's Hardware, Nikkei free, DigiTimes-derived free coverage) | quarterly + event statements |
| `hbmSupplyCapex` (S2) | SK hynix / Samsung / Micron earnings releases + official statements; Micron via EDGAR; free coverage (Reuters, Business Korea) | quarterly |
| `hyperscalerCapexRevision` (D1) | MSFT/GOOGL/AMZN/META/ORCL earnings calls + filings (EDGAR); free coverage (CNBC, Reuters) | quarterly, monthly-carried |
| `odmMonthlyAiRevenue` (D9) | TWSE monthly revenue announcements via company IR (Wiwynn 6669, Quanta 2382, Wistron 3231); MOPS archive | monthly (by the 10th) |
| `tokenEconomics` (D4) | official API pricing announcements + web.archive.org pricing-page snapshots (snapshot date = vintage); token-volume disclosures (Google I/O, OpenRouter public stats) | sparse/event — estimate-grade |
| `marginalBuyerFinancing` (X5) | dated financing-event coverage (CoreWeave/Lambda/Crusoe/Nebius debt + equity), credit-market commentary in free press | event — estimate-grade |

Subscription sources (TrendForce, DRAMeXchange, WSJ, FT, The Information) are inventoried,
never scraped (charter rule) — excluded from every series above.

## Series construction rules (deterministic composition over raw dated observations)

These rules are applied by code/session over the raw per-source observations; the per-point
`note` carries the inputs so every value is re-derivable. **User reviews these at G1.**

- **D9 `odmMonthlyAiRevenue`** — value = YoY % growth of the SUMMED monthly revenue of
  Wiwynn + Quanta + Wistron (the server-pure/-heavy TWSE trio; Hon Hai excluded as
  iPhone-diluted, SMCI excluded as non-TWSE/quarterly — noted deviation from SDEWS's
  five-name list, reviewed at G1). Unit `pct_yoy`. Point period = revenue month;
  publishedAt = announcement date (or the 10th-of-following-month deadline, marked).
  NOT estimate-grade (hard TWSE numbers; the AI-proxy nature is a note, not an estimate).
- **D1 `hyperscalerCapexRevision`** — value = net revision direction across the five
  buyers reporting in that earnings cycle: Σ sign(revision) ∈ [-5, +5]. Unit
  `revision_direction`. Point period = earnings-call month; one point per cycle month;
  publishedAt = the LATEST earnings date contributing to that point. Note carries the
  per-company directions + evidence sentences.
- **S2 `hbmSupplyCapex`** — value = mean of available per-company signals for the quarter,
  where a company's signal = stated bit/capacity growth % when a number was given, else
  25·capexDirection (a coarse mapping of raised/maintained/lowered onto the same % scale,
  marked estimate in the note). Unit `pct_yoy`. Point period = earnings month.
- **S1 `pkgCapacityOrderSpread`** — value = capacityGrowthPct − orderGrowthPct for the
  nearest-in-time capacity and order observations (each ≤ 2 quarters old at the point's
  period). Negative = orders outrunning capacity (tightening); positive = capacity
  outrunning orders (loosening — the SDEWS reversal signal). Unit
  `ramp_minus_order_rate_pct`. Points only in months where BOTH sides have a usable
  observation. estimateGrade = true whenever either side is a quantified estimate from a
  qualitative statement.
- **D4 `tokenEconomics`** — value = annualized token-volume growth % + annualized
  benchmark $/M-token price change % (price change is negative when prices fall; the sum
  is an inference-revenue-growth proxy: positive = healthy Jevons expansion, negative =
  revenue deflation / saturation precursor). Unit `price_vs_volume_rate`.
  estimateGrade = true on every reconstructed point (spec-mandated).
- **X5 `marginalBuyerFinancing`** — value = Σ easingOrTightening over the month's events,
  clamped to [-3, +3] (positive = easier financing for marginal buyers). Unit
  `credit_condition_index`. Event months only. estimateGrade = true (spec-mandated).

## Backtest bar (pre-committed — copied from the spec, written before any harness run)

PASS = catches ≥2 of the 3 named turns (H100 crunch onset, CoWoS bottleneck, HBM squeeze)
with ≥1 quarter of lead time each, AND ≤1 false orange-or-worse alarm per backtest year.
A miss = STOP and redesign; no weight tweaks off a single miss.

## Backfill results (filled at the end of Stage 2, reviewed at G1)

*(pending — per-series point counts, spans, estimate-grade fractions, gap lists)*
