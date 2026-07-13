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
- **S2 `hbmSupplyCapex`** — value = mean per earnings month of per-company HBM
  supply-growth readings, valued row-by-row by a recorded overlay (basis quoted per point
  in the store note): a STATED annual-basis multiple maps exactly (double=+100,
  threefold=+200, 3.5x=+250, five-fold=+400, "+330% YoY"=+330); qualitative wording maps
  to a documented scale (strong expansion — new fab / "substantially" / sold-out-driven
  ramp / sub-annual multiple ≥2x — = +50; mild = +25; hold = 0; mild cut = −25; deep cut
  = −50). Unit `pct_yoy`. ALL points estimateGrade = true (prose-derived). *Amended
  during backfill from the planned 25·capexDirection fallback: all three companies spoke
  in multiples, never literal percents — `supplyGrowthPct` came back null in all 42 rows.*
- **S1 `pkgCapacityOrderSpread`** — value = a five-class quantized spread reading
  {−50, −25, 0, +25, +50} (pct-points/yr equivalent) classified per dated statement:
  −50 shortage (explicit shortfall / excess-demand wording), −25 tight (tight/fully-booked
  wording without explicit shortfall), 0 balanced/narrowing, +25 loosening, +50 glut.
  Negative = orders outrunning capacity (tightening). The classification (value +
  rationale + quote) rides each store point's note. ALL points estimateGrade = true;
  wording variance implies ±1 class noise. *Amended during backfill from the planned
  two-rate numeric spread: stated capacity-growth and order-growth numbers measure
  different bases, the both-sides-numeric rule kept only 5 of 24 dated statements, and
  the series went dark after 2025-04 — discarding exactly the inflections that are the
  signal (2023 crunch onset, 2025 softening, late-2025 re-tightening).*
- **D4 `tokenEconomics`** — value = median annualized LOG token-volume growth %/yr +
  median annualized LOG $/M-token price change %/yr over the trailing 9 months (log rates
  are exactly additive for the revenue = volume × price proxy: positive = healthy Jevons
  expansion, negative = revenue deflation / saturation precursor). Rates are computed
  between consecutive observations within a stable comparable TRACK (flagship-input
  price, cheap-tier price, Google all-surfaces volume, OpenRouter volume, …) assigned per
  row. Unit `price_vs_volume_rate`. estimateGrade = true on every point (spec-mandated).
  *Amended during backfill from the planned freshest-single-pair rule: raw metric labels
  are per-SKU (80 distinct labels / 86 rows), so same-label pairing found nothing and a
  single freshest pair would bounce across model families month to month.*
- **X5 `marginalBuyerFinancing`** — value = Σ easingOrTightening over the month's events,
  clamped to [-3, +3] (positive = easier financing for marginal buyers). Unit
  `credit_condition_index`. Event months only. estimateGrade = true (spec-mandated).

## Backtest bar (pre-committed — copied from the spec, written before any harness run)

PASS = catches ≥2 of the 3 named turns (H100 crunch onset, CoWoS bottleneck, HBM squeeze)
with ≥1 quarter of lead time each, AND ≤1 false orange-or-worse alarm per backtest year.
A miss = STOP and redesign; no weight tweaks off a single miss.

## Backfill results (Stage 2, 2026-07-13 — reviewed at G1)

156 points across the six series, all vintage-stamped with per-point source URL +
publishedAt. Raw research: six parallel agents (WebSearch/WebFetch), ~430 tool uses;
per-source verification by the researchers plus 8 independent lane-agent spot-checks
(3× D9 against MOPS to the TWD thousand; one high-leverage claim per other series) —
all exact.

| series | points | span | estimate-grade | verification highlight |
|---|---|---|---|---|
| `odmMonthlyAiRevenue` | 42 | 2023-01..2026-06, no gaps | 0/42 | 9 figures exact vs MOPS |
| `hyperscalerCapexRevision` | 27 | 2023-01..2026-06 | 0/27 | META 2023-02 cut vs Meta IR |
| `hbmSupplyCapex` | 29 | 2023-01..2026-06 | 29/29 | Samsung "threefold" vs KED Global |
| `pkgCapacityOrderSpread` | 17 | 2023-04..2026-04 | 17/17 | Liu "80% of needs" vs SiliconANGLE |
| `tokenEconomics` | 14 | 2024-12..2026-06 | 14/14 | GPT-4 $30/M vs 2023-06 snapshot |
| `marginalBuyerFinancing` | 27 | 2023-03..2026-06 | 27/27 | CoreWeave $2.3B vs PRNewswire |

Known honest limits (disclosed at G1): D4 starts 2024-12 (no 2023 token-volume
disclosures exist anywhere — the researcher checked); D9 announce dates use the TWSE
10th-of-following-month deadline (archive pages carry no per-company release dates);
D1's staggered earnings dates split one buyer cycle across adjacent months; S1/S2
values quantize executive prose onto documented scales (all estimate-marked, quote per
point); one Quanta 2024-12 revision kept as-announced; the CoWoS gap months are
quarters between earnings statements (event-cadence, not missing data).
