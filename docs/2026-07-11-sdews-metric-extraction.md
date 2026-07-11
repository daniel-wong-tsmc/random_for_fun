# SDEWS spec → merchant-gpu agent: metric extraction (2026-07-11)

Source: `docs/AI供需早期預警系統 SDEWS 規格書 v1.0.docx` ("AI Supply-Demand Early Warning
System, spec v1.0", dated 2026-06-10, Draft for Review). A Google-Docs-exported .docx whose
entire body text sits in `word/footer1.xml` (the visible document body is empty) — extracted
2026-07-11; plain-text copy retained in the session scratchpad. Traditional Chinese; scoped to
the NVIDIA Vera Rubin supply chain for an operations-planning audience.

**Why it maps cleanly:** SDEWS uses the same core index design as this agent — a demand
momentum index (DMI), a supply momentum index (SMI), their gap (SDGI = DMI − SMI), z-scored
inputs, freshness decay `exp(-λ·age)`, and price kept OUT of the index as a confirmation
overlay (its §5.2 confirmation-layer rule is our F8 doctrine, independently arrived at).
Its indicator catalog (10 demand, 10 supply, 6 price, 5 structural) is therefore directly
comparable to `registry/indicators.json`.

**Gate note:** everything below is analysis only. `registry/indicators.json` is
prompt-affecting DATA — any adoption goes through brainstorming → spec → the F6 eval gate
(run-eval → rebaseline), one change at a time. Nothing has been changed.

---

## 1. Already covered (validation, no action)

| SDEWS | Ours | Note |
|---|---|---|
| D2 NVIDIA DC revenue structure | `D2` | same code, same read (QoQ slope) |
| D3 NVIDIA purchase commitments | `rpoBacklog` (0.14) | SDEWS adds: commitment growth *slowing* leads revenue by 2–4 quarters — a sharper read of a metric we already hold |
| D5 AI application revenue | `apiArr` (0.20) | |
| D6 GPU cloud rental price | `D6` (price overlay) | |
| D8 model release cadence | `releaseCadence` (0.10) | SDEWS adds the funding half — see X5 below |
| P3 second-hand GPU price | `gpuSpotPrice` (price overlay) | SDEWS adds **listing volume**: sell-listings surging while price dives = strongest early glut signal. Cheap comparability-note upgrade |
| S9 alternative supply | `S9` (0.04) | same code |
| S10 whole-chain inventory | `S10` (0.08) | SDEWS reads it as a *weighted chain* (vendor DIO + ODM WIP + channel), not one 10-Q line |
| X3 export controls | `exportControlExposure` (overlay) | |
| price-as-confirmation-layer | F8 doctrine | independent convergence — validates the design |
| freshness decay | `decayLambda` (F60 data half) | same formula |

## 2. Extracted — fills the F60 leading-supply gap (highest value)

HANDOFF's standing F60 residual: `smiContribution: 0.0` — the agent has **no leading supply
indicator** (leadTimes is coincident, S10 confirms after the fact). SDEWS's supply family is
built around exactly this. Candidates, in recommended order:

1. **S1 — Advanced-packaging capacity ramp vs. order growth** (CoWoS/SoIC wafers/month).
   The spec's single highest-weighted supply input (0.20), lead 2–4 quarters. Trigger read:
   *capacity growth rate overtaking order growth rate* = the core shortage→glut reversal
   signal. News-sourced (foundry statements, tool-maker orders, trade press) → fits the
   Option-C "news-sourced leading supply indicator" shape F60 asked for. Lane note: capacity
   *levels* belong to chips.foundry-packaging; what merchant-gpu ingests is the **ramp-vs-order
   spread as merchant-GPU supply outlook**.
2. **S2 — HBM bit-supply growth + memory-maker capex guidance** (SK hynix/Samsung/Micron),
   lead 2–4 quarters. "Collectively rational, aggregately excess" memory expansion is the
   canonical cycle-turn mechanism. Same lane note vs. chips.hbm-memory.
3. **S4 — Long-lead component lead-time index** (optics/CPO, liquid-cooling CDU, 800V power,
   high-end PCB/CCL), lead 1–2 quarters. Complements our `leadTimes` (finished-GPU channel,
   coincident) with the *upstream* view; any single item's lead time peaking and rolling over
   = that bottleneck clearing.
4. **S6 — WFE book-to-bill** (ASML/AMAT/KLA/LAM/TEL; SEMI monthly stats), lead 2–4 quarters.
   "Equipment is the supply of supply." Furthest upstream, most out-of-lane — better suited
   to the layer tier unless 1–3 prove insufficient.

## 3. Extracted — demand-side additions worth adopting

5. **D1 — Hyperscaler capex-revision direction** (MSFT/GOOGL/AMZN/META/ORCL guidance, QoQ
   revision direction + neoclouds as marginal buyers). SDEWS's highest-weighted demand input
   (0.20), lead 6–12 months. **Genuine blind spot:** we track the vendor's own guidance
   (`vendorRevenueGuidance`) but not the *buyers'* budgets. Two consecutive down-revisions =
   strong reversal signal. Quarterly, filings/calls — matches our gather reach.
6. **D9 — Taiwan ODM monthly AI-server revenue** (Hon Hai, Quanta, Wistron, Wiwynn, SMCI).
   SDEWS #2 demand weight (0.18), lead 1–2 quarters, and the **only monthly-frequency hard
   demand number in the entire space** (TWSE publishes by the 10th). Our scoring demand set
   is currently all-quarterly; this is also the best freshness fit for F78's daily
   change-first brief.
7. **D4 — Token economics** (inference $/M-tokens decline rate vs. token-volume growth rate).
   Weekly/monthly, lead 3–6 months. Reads demand *health*: price falling faster than usage
   grows = revenue deflation = saturation precursor; the reverse = healthy Jevons expansion.
   Directly feeds the standing thesis book (e.g. rising-memory-costs / capex-sustainability
   theses).
8. **X5 — Financing environment for marginal buyers** (neocloud debt terms, GPU-collateral
   loan conditions, AI credit spreads). Lead 2–4 quarters. Mechanism: funding cost squeezes
   the marginal buyer first — neocloud orders vanish before hyperscaler ones. Event/monthly,
   news-sourced; pairs with the existing customerConcentration overlay.

## 4. Extracted — mechanisms (not metrics) worth stealing

- **ΔSDGI momentum trigger:** alert when the gap moves the same direction two consecutive
  periods with cumulative move > 0.5σ, *even while the level is still "green."* The spec's
  stated lesson: at cycle turns the level looks healthy while momentum has already flipped.
  Natural fit for F78's change-first brief (F64's trigger logic).
- **Platform-changeover down-weighting:** generation-sensitive series (rental price, used
  price) auto down-weight ~50% for one quarter around a platform transition — precisely the
  logged F51 artifact (lambda.ai day-over-day delta comparing different GPU models).
- **Asymmetric thresholds:** demand-*reversal* alerts trip at lower σ than shortage alerts
  (downside risk tolerated less). Cheap doctrine line for the judge/thesis prompts when
  alerting ships.
- **Dual polarity per signal** (`polarity_demand` + `polarity_supply` on the same finding —
  e.g. HBM price spike = supply-tightness evidence AND downstream cost pressure). Our schema
  has one polarityTrack per indicator. Schema-touching → v1.5+ migration territory only.
- **Indicator lifecycle** (`active/degraded/retired` + explicit failure conditions; source
  dark 3 months → weight 0, backup promoted). Fits the registry as data fields.
- **Impulse events with half-life** (event-type signals decay over ~8 weeks instead of
  entering the continuous series). Relevant to how X3-type events age in the corpus (F78's
  real-publication-date aging is the same instinct).

## 5. Noted, NOT recommended for this category (lane discipline, Part 21)

- **S3/P1/P4 HBM contract-price family** → chips.hbm-memory's lane (P1's second-derivative
  read — "price still rising but more slowly = earliest reversal signal" — is a good trick
  for any price series we ever score).
- **D7 datacenter starts/power + X2 grid bottleneck** → infrastructure layer (12–36 mo lead;
  the spec's "power is a harder cap than chips; demand gets deferred, not destroyed" is a
  useful judge framing but not a category input).
- **S7 T2/T3 supplier visibility, S8 materials/gases** → supplier-graph products, not a
  category momentum input.
- **P5 supply-chain equity relative strength** → market-price signal; sits outside this
  desk's evidence doctrine.
- **P6 BoM cost structure, X1 workload-structure shift, D10 enterprise adoption** → layer-tier
  context.

## 6. Suggested adoption order (each step = its own gated feature)

1. **One leading supply indicator** (S1 ramp-vs-orders, or S1+S2 as a pair) — closes the F60
   residual, the oldest open gap.
2. **D1 hyperscaler capex revisions** — biggest demand blind spot, source-cheap.
3. **D9 ODM monthly revenue** — monthly cadence uniquely serves F78's daily brief.
4. **Overlay upgrades** (P3 listing volume on gpuSpotPrice; changeover down-weighting;
   ΔSDGI momentum trigger inside F78).
5. **D4 / X5** as capacity allows.

Each touches `registry/indicators.json` (+ possibly prompt vocab) → F6 pin goes red by
design → full run-eval → rebaseline, one at a time, per the standing rule.
