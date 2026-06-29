# The human "GPU Market Brief" — output design target (drives 4-2 → 4-5)

- **Date:** 2026-06-29
- **Status:** Agreed design target (not a piece spec). Binds the **4-5** brief and is the **north-star
  requirement** that 4-2 / 4-3 / 4-4 are built to satisfy. Captured now so the output goal is fixed before the
  upstream pieces are built.
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md);
  charter Part 35 (the product surface), Part 17 (numbers; plain language).
- **Why this exists:** a live `v5` run still reads as *scores, not a market picture* — a reader can't say
  "what is demand doing, what is supply doing, where is it heading." This note pins the **human-facing output**
  we are building toward so each piece delivers exactly the data the brief needs.

---

## 1. Decision: medium

- **First (4-5):** a **deterministic Markdown / terminal brief** that **extends A's `report.py`** — pure
  projection, no LLM in the renderer, byte-reproducible (same store → same brief). This is the canonical human
  artifact.
- **Follow-up (after 4-5):** an **HTML dashboard** (collapsible storylines, color, click-a-claim-to-see-the
  finding, drill-down) — the Part-35 *pull* surface, a projection over the **same** store. Not built until the
  Markdown content model is proven.

Two views, by design:
- **Canonical / agent-facing (exists):** the JSON `Scorecard` + the wiki store + `log` — complete, machine-
  readable, replayable, every number gated. The source of truth.
- **Human-facing (new):** the brief below is a **pure projection** of that canonical data — **no new numbers,
  no LLM in the renderer** (Part 35: "the surface is a projection consumer, not a writer").

---

## 2. The five rules that make it readable

1. **Inverted pyramid / BLUF** — the state of the market in the first ~5 lines; everything below is drill-down.
2. **Demand | Supply | Gap as words + direction first, number second** — "Demand: accelerating ▲", not
   "DMI 0.147"; the raw index rides in parentheses for the analyst, never leads. Every index is mapped to the
   five-word band + a direction + a "was X last cycle" so the **change** is the signal.
3. **NOW vs NEXT side by side** — trailing **Momentum** and forward **Outlook**, with the **divergence** called
   out explicitly (Momentum strong while Outlook turns is the case the system exists to catch).
4. **Lead with what moved** — a daily monitor's headline is the *diff*, not the snapshot.
5. **Every line cited + honest** — `[f-###] primary/secondary` on each claim; stale leading signals flagged;
   single-source flagged; coverage gaps, under-supported dimensions, and degraded inputs shown.

---

## 3. The target layout (mock — using v5 / chips.merchant-gpu data)

```
══════════════════════════════════════════════════════════════════
 GPU MARKET BRIEF — Merchant GPU (data-center accelerators)
 As of 2026-06-29 · vs prior 2026-06-28 · confidence MEDIUM
══════════════════════════════════════════════════════════════════
STATE OF THE MARKET
  Demand:  ACCELERATING ▲          Supply:  TIGHT, easing slowly ▲
  Gap:     DEMAND-LED — shortage persisting, slowly narrowing  (SDGI +0.12)
  NOW (Momentum): STRONG ▲     NEXT (Outlook): STRONG — but watch ▼
  ⚠ DIVERGENCE: trailing demand strong; one forward signal
     (a hyperscaler capex guide) softened — single-source, unconfirmed.
  BINDING CONSTRAINT: advanced packaging (CoWoS) — not raw wafers.

WHAT MOVED SINCE LAST RUN
  ▲ NEW    AMD MI450/Helios ramp pulled into Q3 (Meta/OpenAI 6GW)  [f-217] primary
  ▲ UP     AMD DC-AI revenue CAGR target >80% (Analyst Day)        [f-203] primary
  ▼ WATCH  A hyperscaler trimmed FY capex guide ~5%                [f-241] secondary ⚠1-src
  =  FLAT  NVIDIA share eroding gradually, not abruptly            [f-198]
  (3 lower-materiality items folded — see full log)

DEMAND ▲                            │ SUPPLY ↔
  Hyperscaler capex       strong ▲  │  CoWoS packaging   tight  ▲  ◀ binding
  Backlog / RPO           strong ▲  │  HBM4 supply       easing ▲
  AMD design wins         rising ▲  │  Foundry wafers    ample  =
  Spot / secondary price  firm   =  │  Lead times 8–10wk improving ▼
   (leading signals ≤14d old unless ⚠stale)

WHY  (drivers → constraints)
  Pulling demand: frontier-training scale-up; hyperscaler buildouts;
                  AMD now a credible 2nd source (eases single-vendor risk).
  Capping supply: CoWoS is the bottleneck; HBM easing; wafers not the limit.
  Net:            demand outruns the packaging ramp → shortage holds.

STORYLINES (tracked over time)
  • AMD inflection      on-track → accelerating   (last change 06-28) ▲
  • NVIDIA moat         intact → slowly eroding    (last change 06-27) ▼
  • CoWoS capacity      tight → tight              (no change 11d)     =
  • Export controls     quiet                      (no change 24d)     ·

TRUST & COVERAGE
  Evidence: 38 findings (24 primary / 14 secondary). Moat under-supported.
  Gaps: TrendForce share data paywalled (estimate-grade).
  Caveat: index level varies run-to-run until memory (4-4) stabilizes it —
          read DIRECTION, not level.
```

The whole market on ~one screen; depth available by reading down or drilling into a cited finding.

---

## 4. Section → which piece must feed it (the build contract)

| Brief section | Data it needs | Owning piece |
|---|---|---|
| State header (demand/supply/gap **as words**) | DMI/SMI/SDGI + a wording/band layer | B (exists) + 4-5 render |
| **NOW vs NEXT + divergence** | trailing **Momentum** + forward **Outlook** indices | **4-3** (needs **4-2** tags) |
| Demand/Supply board w/ **leading signals + recency** | cadence×horizon tags; daily/leading indicators; per-signal as-of | **4-2** |
| **Binding constraint named** | physical-capacity indicators (CoWoS/HBM/lead-times) + judgment | **4-2** + judgment |
| **WHAT MOVED since last run** | the wiki `diff` over a store **populated across runs** | 4-1 `diff` (done) + **4-4** |
| **STORYLINES** (state + trajectory) | wiki pages curated over time | 4-1 store (done) + **4-4** |
| Trust & coverage footer | dimensionStatus + coverage manifest | B + C (exist) |
| The render itself (Markdown brief) | a pure projection of all the above | **4-5** |

**Build order stays 4-2 → 4-3 → 4-4 → 4-5** (the brief is the consumer; built once against the final data
model to avoid re-writing the renderer three times). At the end of each piece, render a **throwaway preview**
of the brief so progress is visible.

---

## 5. What this fixes (vs the current `v5` output)

- "Scores, not a picture" → the two-column board + causal tree + words-first indices.
- "Can't see where it's heading" → the **Outlook** column and the NOW/NEXT divergence.
- "Run-to-run noise, no memory" → "what moved" + storylines read from the persistent store; the brief reads
  **direction** and **change**, not a re-derived level.
- "No events" → storylines with state + trajectory + last-change recency.
- "No named constraint" → the WHY tree names the *specific* binding constraint.
