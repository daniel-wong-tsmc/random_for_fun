# F79 — SDEWS-style scoring v2.0 (series layer, z-scored indices, backtest; frozen-core migration)

**Status:** approved design, ready for a lane plan.
**Decision provenance — all forks user-approved 2026-07-13 (interactive AskUserQuestion,
orchestrator session):** (1) **series set = FULL SIX** — S1, S2, D1, D9, D4, X5 — user chose
against the assistant's core-four lean (consistent with the 2026-07-11 full-rebuild choice);
(2) **one bundled v2.0 migration with ONE eval re-gate** at the end; (3) **shadow-first
cutover** — v2 computes silently beside v1 until the user approves the cut; (4) **pre-committed
backtest bar** written into this spec before anyone runs it. Parameters below marked
*doc-settled* come from the exec-format spec §6 and `docs/2026-07-11-sdews-metric-extraction.md`
(user-approved 2026-07-11) and are NOT re-litigated. Any fork this spec does not settle is a
QUESTION-STOP (repo CLAUDE.md "Orchestrated lane agents") →
`.superpowers/handoffs/f79-scoring-v2-QUESTIONS.md`, end turn, wait.

## What it is

Each scoring indicator becomes a monthly, vintage-stamped time series (2023→now backfilled);
values are z-scored against the series' own rolling history; DMI/SMI become weighted z-sums
with freshness decay; SDGI = DMI − SMI with a ΔSDGI momentum trigger and asymmetric
demand-reversal sensitivity; event signals enter as decaying impulses. The news-flow machinery
(gates/findings/thesis book) is NOT deleted — it becomes the event channel + qualitative
overlay. Brains stay Claude; no brain-prompt semantics change except the indicator-vocabulary
additions that ride the bundled re-gate.

## The six new series (user-approved: full six)

| id (new, registry) | SDEWS | What | Cadence / lead | Source honesty |
|---|---|---|---|---|
| `pkgCapacityOrderSpread` | S1 | CoWoS/SoIC capacity-ramp rate vs order-growth rate (as merchant-GPU supply outlook — the ramp-vs-order SPREAD, not capacity levels, which belong to foundry-packaging's lane) | monthly / 2–4Q | foundry statements, tool-maker orders, trade press |
| `hbmSupplyCapex` | S2 | HBM bit-supply growth + memory-maker capex guidance | monthly / 2–4Q | SK hynix/Samsung/Micron filings + official statements |
| `hyperscalerCapexRevision` | D1 | Buyer-budget revision direction (MSFT/GOOGL/AMZN/META/ORCL, QoQ) | quarterly, monthly-carried / 6–12mo | filings + earnings calls |
| `odmMonthlyAiRevenue` | D9 | Taiwan ODM monthly AI-server revenue (Hon Hai, Quanta, Wistron, Wiwynn, SMCI) | monthly (TWSE by the 10th) / 1–2Q | TWSE monthly revenue archive |
| `tokenEconomics` | D4 | Inference $/M-token decline rate vs token-volume growth | monthly / 3–6mo | **estimate-grade** where archives are thin — mark per-point |
| `marginalBuyerFinancing` | X5 | Neocloud debt terms / GPU-collateral conditions / AI credit spreads | monthly-event / 2–4Q | **estimate-grade** where archives are thin — mark per-point |

D4/X5 points reconstructed from news must carry `estimateGrade: true` and render honestly if
ever surfaced. S1/S2 side = supply (closes the F60 `smiContribution: 0.0` residual); D1/D9/D4
demand; X5 structural-demand overlay — final side/weight table is a plan task, seeded from the
SDEWS weights in the extraction doc, adjusted to our registry conventions.

## Doc-settled parameters (2026-07-11 — do not re-open)

36-month rolling z-window; younger series borrow same-class distributions until the window
fills; freshness decay `exp(-λ·age)` reusing `decayLambda`; SDGI = DMI − SMI; **ΔSDGI momentum
trigger** (two consecutive same-direction periods, cumulative move > 0.5σ, fires even at green);
**asymmetric thresholds** (demand-reversal alerts trip at lower σ than shortage);
**event impulses with ~8-week half-life**; **platform-changeover down-weighting** (~50% for one
quarter on generation-sensitive series); **dual polarity per signal** and **indicator lifecycle**
(`active/degraded/retired`, source-dark-3-months → weight 0) ride this migration as registry/
schema-adjacent data. Backfill is **strictly by publication vintage — no look-ahead** (per-point
`publishedAt` vs `capturedAt`, F52 discipline).

## Architecture

- **Series store (new carve-out):** `store/series/<indicatorId>.jsonl` — append-only monthly
  points `{indicatorId, period(YYYY-MM), value, unit, publishedAt, capturedAt, source{url,
  title}, estimateGrade?, note?}`. Tracked (gitignore whitelist extended). Deterministic reads;
  revisions append (never rewrite) with the later vintage winning at read-time for a given
  as-of.
- **Engine (new module(s), e.g. `gpu_agent/series.py`):** z-scores, window borrowing, decay,
  index composition, ΔSDGI, impulses. `scoring.py` changes ship ONLY as the **versioned v2.0
  migration (Part 33)** — a version dispatch where v1.x paths remain byte-identical:
  **replay fidelity for every stored v1.x scorecard is pinned by test** (F60 weight-freeze
  precedent). Absorbs the deferred F60 scoring half; the v1.5 slot is superseded.
- **Alert bands:** swap the rule-based v1 triggers in `gpu_agent/change.py` for σ-bands,
  keeping the `AlertState`/fold interface intact (stage-6 plan anticipated exactly this swap).
- **Registry:** six new indicators + lifecycle/dual-polarity fields in
  `registry/indicators.json`. Prompt vocabulary changes ride the ONE bundled re-gate (below).
- **Shadow mode:** each live cycle computes v2 indices alongside v1 and records them in the
  scorecard's free-form `provenance` dict (additive — NOT a schema change); only v1 renders
  until cutover. **Do NOT render v2 anywhere user-facing before the cut.**
- **Backtest harness:** replays the six series by capture vintage over 2023–2025, emits
  recall / false-alarm(orange+) / lead-time per named turn.

## Pre-committed backtest bar (user-approved posture; numbers finalized at the stage gate)

PASS = catches **≥2 of the 3 named turns** (H100 crunch onset, CoWoS bottleneck, HBM squeeze)
with **≥1 quarter of lead time each**, AND **≤1 false orange-or-worse alarm per backtest
year**. Written BEFORE the harness runs; a miss = STOP and redesign — **no weight tweaks off a
single miss** (SDEWS §10.2 / F73 instinct). The verdict gate is USER-SIGNED.

## Mandatory user gates (each = stop, report, wait — never AFK)

G1 backfill review: all six series assembled with per-point provenance → user reviews charts +
provenance summary before the backtest treats them as truth. G2 backtest verdict sign-off
against the pre-committed bar. G3 the bundled eval re-gate (run-eval governance; **fold the F73
canary live-capture into this run** — it must not be hand-authored). G4 cutover approval after
a shadow soak of ≥5 live cycles; the brief notes the methodology change once at cut.

## Lane ownership / hard constraints

Owns: `gpu_agent/scoring.py` (v2.0 migration ONLY), new series/backtest modules,
`registry/indicators.json`, `gpu_agent/change.py` alert definitions, `store/series/` (new),
migration note `docs/migrations/2026-07-scoring-v2.md`, its tests. Must NOT touch:
`report.py`/`reader.py` (F65's surface), `wiki/`, `sufficiency.py`, `gate.py`, `schema/*`
(dual-polarity/lifecycle land as registry data, not Finding-schema fields — if that proves
impossible, QUESTION-STOP), `docs/taxonomy.json` (F24-s2 owns it; missing entity → coordinate
via orchestrator), `extraction/`. `cli.py` additions append-only (new verbs only; F65 also
adds a verb — trivial rebase expected). Defer run-cycle SKILL.md prose edits to the final
stage. **Eval-re-gate serialization: F65's re-gate runs first; coordinate through the
orchestrator before starting G3.** Suite green at every commit (baseline 1346/5); F6 pin
stays green until G3 by construction (no prompt bytes move before the registry additions).

## Non-goals

Layer-tier rollups; subscription-source series (TrendForce/DRAMeXchange — inventoried, never
scraped); reconstructing news-flow deep history (hindsight bias — the series layer IS the
backtest spine); rendering v2 pre-cutover; removing the news-flow machinery.
