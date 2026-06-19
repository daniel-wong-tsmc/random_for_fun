# Category Agent Development Guide — Demand / Supply Signal Instrumentation

> The build-spec for the **Category Agent** (charter Part 3, Tier 1) re-framed around an
> **early-warning** mission: detect demand- or supply-side inflection in the AI hardware market
> **1–2 quarters before consensus**. Derived from the *AI Supply-Demand Early Warning System
> (SDEWS) v1.0* spec (NVIDIA Vera Rubin supply chain, June 2026) and folded back into the
> [`agent-swarm-charter.md`](./agent-swarm-charter.md) so it obeys the same doctrine, schema, and
> tiers.
>
> **The one new idea this guide adds to the charter:** every signal, indicator, and index is
> explicitly tagged **demand-side** or **supply-side**, organized per layer of the 5-layer cake, so
> each layer carries a **Demand Momentum (DMI)**, a **Supply Momentum (SMI)**, and the gap between
> them (**SDGI**). The charter already rates a layer by its *weakest link* (Part 17); this guide
> tells the agent **which side of the market that weak link is on** — a shortage forming (supply
> can't keep up) reads very differently from a reversal forming (demand rolling over), and the
> operator's response is the opposite in each case.

---

## 0. How this maps to the charter (read this first)

SDEWS is not a new system — it is the Category Agent doing its job with a demand/supply lens. Every
SDEWS concept already has a home in the charter; this guide only **extends** the existing parts, it
does not replace them.

| SDEWS concept | Charter equivalent | What this guide adds |
|---|---|---|
| **Signal** (a structured datapoint) | **Finding** (Part 2 — the atomic explainable unit) | two new fields: `polarityDemand` / `polaritySupply`, plus `magnitude` and a separate `capturedAt` |
| **Indicator** (D1…X5) | a **registered metric** (Part 18 metric registry) | a `side` tag (demand / supply / price / structural) and a `leadMonths` on every metric |
| **DMI / SMI / SDGI** (the indices) | a **roll-up** (Part 17: category → layer → market) | the roll-up is **decomposed into a demand track and a supply track**, then differenced |
| **Four-quadrant state / alert tiers** | the **market status** word + the **human-in-the-loop gate** (Parts 8, 17, 23, 32) | a demand/supply quadrant behind each status word, and asymmetric (demand-biased) thresholds |
| **Cross-validation rule** (≥2 families, ≥3 indicators) | the **signal-vs-noise triage** (Part 10) | the resonance test *is* the corroboration/persistence bar, stated numerically |
| **`captured_at` ≠ `observed_at`** | the **backtest harness** (Part 24) / vintage honesty (Part 8) | makes look-ahead-bias-free replay a schema guarantee, not a convention |
| **Confusion matrix / recall / false-alarm** | **calibration & track record** (Part 12) | concrete eval targets (recall ≥ 80%, false-alarm ≤ 30%, lead ≥ 60 days) |
| **Neo4j Indicator/Signal/Alert nodes** | the **canonical store** (Part 9), graph projection | an optional graph layer for "which suppliers does this alert touch?" |

**Binding inheritance.** Everything in the Explainability Doctrine (Part 1) still holds: no naked
numbers, never fabricate a figure, state the why + impact + source, label hypotheses, report
dispersion. A demand/supply tag is *additional* structure on a Finding — it never licenses an
invented number.

---

## 1. Purpose & scope

### 1.1 Mission
The AI hardware supply chain exposes the operator to two opposite risks: a **supply-side break**
(component shortage, packaging bottleneck, geopolitics) and a **demand-side reversal** (AI capex
cooling, inference-price deflation outrunning usage growth, overcapacity). History (the memory
cycle, the crypto-GPU glut, pandemic long/short-material whips) shows the turn shows up in **leading
indicators 2–4 quarters before it is confirmed in earnings** — but scattered across heterogeneous
sources no human can track continuously. The Category Agent's job is to converge those scattered
signals into **quantifiable, backtestable, action-triggering** Findings and roll them into indices
that flag the **direction and strength** of the demand/supply shift early.

### 1.2 Position in the swarm
This is the **Tier-1 Category Agent** of the charter (Part 3) — the desk analyst that faces the web.
It feeds the Layer agents and the Main orchestrator unchanged. As in the charter, the demand/supply
**indices and roll-ups are computed in code** and handed *up* to the Layer/Main agents as a briefing
book (Part 5) — the agent interprets, code does the arithmetic.

It also slots into the broader operating picture: a **Red** alert (§5) is exactly the charter's
**high-stakes human-in-the-loop gate** (Parts 8, 23) and the **fast-break escalation** path (Part
32) — a strong, mechanistic signal raises its hand early as a confidence-capped hypothesis without
whipsawing the headline status.

### 1.3 Design principles (inherited + sharpened)
- **Comprehensive** — demand, supply, price, and structural signal families run in parallel; no
  single-lens blind spot. Every indicator carries a stated **lead time** and a **failure condition**.
- **Quantifiable** — every indicator is standardized to a **z-score** before it enters an index;
  narrative intelligence must be structured into a *direction + magnitude* first. "Narrative with no
  number" never enters scoring (this is doctrine Rule 2 applied to the index layer).
- **Backtestable** — every signal is timestamped with `capturedAt`; thresholds and weights are valid
  only after they survive a 2023–2026 historical backtest (Part 24).
- **Actionable** — every alert level maps to a pre-approved playbook. A warning with no response is
  worthless (Parts 10–11).
- **Sustainable / low-maintenance** — prefer stable APIs and structured sources; scrapers are a
  supplement, and every scraper ships with break-detection + a manual fallback (Part 29). The most
  dangerous failure is *"the system looks fine but the data stopped flowing."*

### 1.4 In / out of scope
**In:** demand/supply monitoring of the AI compute supply chain (GPU/CPU/ASIC, HBM, advanced
packaging, rack systems, liquid cooling, power, optical, PCB/CCL); hyperscaler & neocloud capex; AI
application commercialization; the related price and capital-market signals.
**Out:** individual-supplier crisis response (handled by existing T2 risk intel); geopolitical
scenario war-gaming (this agent only *consumes* that module's output as structural signal X3); any
investment/trading decision (output is **operational planning intelligence only**).

---

## 2. The core reframe — three mappings

### 2.1 Signal → Finding (extended)

A SDEWS Signal **is** a charter Finding (Part 2) with four additions. The crucial two are
`polarityDemand` and `polaritySupply` — **the dual-polarity design**: one observation can move both
sides of the market at once (e.g. *HBM contract price +435%* is simultaneously evidence of supply
tightness **and** a downstream cost pressure). Recording the two polarities separately is what lets
the same Finding feed both the demand track and the supply track of the index.

```json
{
  // ── inherited Finding fields (Part 2) ───────────────────────────────
  "id": "uuid",
  "statement": "plain-language claim a human reads in one sentence",
  "kind": "measured | observed | hypothesis",
  "value": { "number": 24.5, "unit": "USD_B | wpm | pct | days | index" }, // null unless measured
  "trend": "rising | falling | flat | unknown",
  "why": "the causal reason this is true / is moving",
  "impact": { "targets": ["layerId | categoryId | indexId"], "direction": "positive | negative | mixed",
              "mechanism": "how the effect propagates" },
  "evidence": [{ "source": "name", "url": "...", "date": "YYYY-MM", "excerpt": "...", "tier": "primary | secondary" }],
  "reasoning": "required for hypothesis",
  "confidence": { "level": "low | medium | high", "basis": "source-credibility × extraction-certainty" },
  "dispersion": "range + note when sources conflict; else null",
  "asOf": "YYYY-MM",

  // ── early-warning extensions (new in this guide) ────────────────────
  "indicatorId": "D1 | D2 | ... | S1 | ... | P1 | ... | X5",  // a registered metric (Part 18)
  "side": "demand | supply | price | structural",            // which track it feeds
  "polarityDemand": -1 | 0 | 1,   // effect on Demand Momentum (DMI)
  "polaritySupply": -1 | 0 | 1,   // effect on Supply Momentum (SMI)
  "magnitude": 1 | 2 | 3,         // slight / significant / severe
  "observedAt": "ISO-8601",       // when the fact occurred
  "capturedAt": "ISO-8601",       // when WE ingested it — used for backtest, kills look-ahead bias
  "entity": "MSFT | NVDA | SK_HYNIX | ...",   // resolves to a registry entity (Part 21)
  "extractionModel": "model_id",
  "schemaVersion": "1.0"
}
```

> **Why `capturedAt` is separate from `observedAt`.** Backtests (Part 24) must reconstruct *"what
> was knowable at the time."* Replaying on `observedAt` leaks the future into the past (look-ahead
> bias) and makes the backtest worthless. Always replay on `capturedAt`.

**Extraction rules (extend Part 7's pre-commit gate):**
- **Dual polarity is mandatory** for any Finding that bears on both sides; default to `0` only when
  a side is genuinely unaffected.
- **Confidence prior by source tier:** A-tier (structured API) `0.9`, named research house `0.7`,
  trade media `0.5`, unattributed channel chatter `0.3`. Multi-source confirmation raises it (union,
  capped at `0.95`).
- **Forced human review:** a Finding with `confidence < 0.5` **and** `magnitude = 3` (low-confidence,
  high-impact) does **not** auto-enter scoring — it routes to the review queue (Part 30).
- **Anchor on behavior and numbers, not tone.** Supply-chain narrative is managed (earnings-call
  language is engineered). Extract the action/figure; treat tone as secondary (§8 known-limit).

### 2.2 Indicator → registered metric (Part 18)

Each indicator (D1…X5) is one entry in the **metric registry** — defined once, referenced by id, so
two agents can't quietly mean different things by the same word. The registry entry gains two
early-warning fields:

```json
{ "id": "S1", "label": "CoWoS/SoIC capacity cadence", "kind": "measured", "unit": "wpm",
  "definition": "Advanced-packaging monthly capacity (wafers/month) expansion trajectory vs. order growth.",
  "comparability": "capacity, not utilization — don't compare to units shipped",
  "side": "supply",            // NEW: which track this metric feeds
  "leadMonths": "2-4 quarters", // NEW: how far ahead it reads
  "weight": 0.20,              // index weight (calibrated by backtest, §4.3)
  "decayLambda": 0.4,          // freshness decay (set by update frequency)
  "status": "active | degraded | retired",
  "defaultSourceHint": ["company earnings calls", "equipment-supplier orders", "industry research"] }
```

### 2.3 Indices (DMI / SMI / SDGI) → charter roll-ups, decomposed by side

The charter rolls **category → layer → market** (Part 17). This guide runs that roll-up **twice in
parallel** — once over demand-side Findings, once over supply-side Findings — and differences them:

```
DMI(layer) = Σ wᵢ · z(demand indicatorᵢ) · freshnessᵢ  +  Σ demand impulses     ← Demand Momentum
SMI(layer) = Σ wⱼ · z(supply indicatorⱼ) · freshnessⱼ  +  Σ supply impulses     ← Supply Momentum
SDGI(layer) = DMI − SMI                                                         ← the gap (the headline)
```

- `freshness = exp(−λ · months_since_last_update)` — a stale indicator is discounted, never silently
  carried at full weight.
- **SDGI ≫ 0** → demand outrunning supply → **shortage intensifying** (price up, lead times stretch,
  allocation). **SDGI ≈ 0** → balanced. **SDGI ≪ 0** → supply outrunning demand → **glut forming**
  (price cuts, inventory build, order cuts).
- Watch the **level *and* the momentum** `ΔSDGI`: two consecutive same-direction moves totaling
  > 0.5σ trips a Yellow alert *even if the level is still green*. The recurring lesson of every cycle
  reversal: **the level still looks healthy long after the momentum has already turned.**

This decomposition is what answers the operator's real question — not just *"is this layer
constrained?"* but *"is it constrained because demand is surging or because supply broke, and is
that gap widening or closing?"*

---

## 3. The demand / supply denotation, by layer (the heart of this guide)

Every indicator is assigned to **one charter layer** (its primary read) and tagged by **side**.
Indicators that genuinely span layers (e.g. the long-lead-time index S4) are noted in each layer
they touch but **owned once** for roll-up (Part 21, count-once rule). The structural (X) family and
the equity-sentiment signal (P5) are **cross-cutting** — they map to the charter's macro/exogenous
overlay (Part 15), owned by Main and handed down to the affected layer.

**Legend:** 🟦 demand-side · 🟥 supply-side · 🟨 price/confirmation (does not enter DMI/SMI directly,
see §4.4) · ⬛ structural overlay (impulse, Part 15).

### Layer 1 — ENERGY
The hard ceiling above the whole cake; almost entirely a **supply-constraint** story.

| ID | Indicator | Side | Charter category | Lead | Read |
|---|---|---|---|---|---|
| **D7** | Datacenter construction & power | 🟦 demand | `energy.power-generation`, `infrastructure.datacenter-colo` | 12–24 mo | New DC approvals/starts (MW), PPA signings, grid-interconnection applications — physical investment leads IT-gear orders by 12–24 mo |
| **X2** | Power & grid bottleneck | ⬛ structural (supply) | `energy.grid-transmission` | 12–36 mo | Interconnection-queue years, large-transformer lead times, AI-campus power approvals. **Power is now a harder ceiling than chips** — a power bottleneck *defers* chip demand, it doesn't destroy it |
| **S4ᵉ** | Power-equipment lead times (slice of S4) | 🟥 supply | `energy.electrical-equipment` | 1–2 q | 800V power sidecar + large-transformer lead times; a peak-and-rollover means that bottleneck is easing |

**Layer read:** Energy's SMI is dominated by X2/S4ᵉ (can power be hooked up?); its DMI by D7
(buildout pull). A *constrained* market whose binding layer is Energy means **chips and money are
flowing but power can't be connected fast enough** — the canonical charter example (Part 17).

### Layer 2 — CHIPS / COMPUTE
The richest layer — most of the supply-side instrumentation lives here.

| ID | Indicator | Side | Charter category | Lead | Read |
|---|---|---|---|---|---|
| **D2** | NVIDIA DC revenue structure | 🟦 demand | `chips.merchant-gpu` | sync–1 q | DC-revenue QoQ growth slope, hyperscaler concentration (~>50%, diversifying). Falling concentration = healthier demand; slope turning negative = early warning |
| **D3** | NVIDIA purchase commitments | 🟦 demand | `chips.foundry-packaging` | 2–4 q | 10-Q purchase-commitment / supply-obligation $ changes — NVIDIA's "real-money" vote on future demand; a slowdown leads revenue by 2–4 q |
| **S1** | CoWoS/SoIC capacity cadence | 🟥 supply | `chips.foundry-packaging` | 2–4 q | Advanced-packaging wpm trajectory vs. order growth (~35K wpm 2024 → 120–140K by end-2026). **When capacity growth starts to exceed order growth → the core reversal warning** |
| **S2** | HBM capacity & capex | 🟥 supply | `chips.hbm-memory` | 2–4 q | SK hynix/Samsung/Micron HBM4 bit-supply growth, capex guidance, TSV conversion. "Collective rationality, aggregate glut" is the classic memory-cycle trigger |
| **S3** | HBM/DRAM contract price & lead time | 🟥 supply | `chips.hbm-memory` | 1–2 q | HBM4 contract-price slope + lead-time days. Classic reversal path: gains converge → flat → roll over. Memory is ~26% of the Vera Rubin BoM, so this hits both cost and supply reads |
| **S6** | WFE book-to-bill | 🟥 supply | `chips.foundry-packaging` | 2–4 q | ASML/AMAT/KLA/LAM/TEL B:B + SEMI shipments — equipment is the *supply of supply*, leads wafer capacity by 2–4 q |
| **S7** | T2/T3 order visibility | 🟥 supply | `chips.foundry-packaging` | 2–6 q | Expansion announcements / visibility at chokepoint suppliers (Entegris, Parker Hannifin, Coherent, ATI). A single-point supplier's completion date *is* the supply-release date |
| **S8** | Critical materials & gases | 🟥 supply | `chips.foundry-packaging` | 1–3 q | Silicon-wafer shipment area, He/Ne gas price & supply, specialty chemicals. Low-frequency, high-impact — monitor by exception |
| **S9** | Alternative supply | 🟥 supply | `chips.merchant-gpu`, `chips.hyperscaler-asic` | 2–4 q | AMD MI400 shipments, Google TPU / AWS Trainium / MSFT in-house deployment, Huawei China substitution. **Every unit of in-house silicon erodes one unit of merchant-GPU marginal demand** |
| **S10** | Whole-chain inventory index | 🟥 supply | `chips.merchant-gpu` | 1–2 q | NVIDIA DIO + commitments, ODM raw/WIP inventory, channel inventory. Chain-wide simultaneous build = glut confirmation |
| **P1** | HBM contract-price 2nd derivative | 🟨 price | `chips.hbm-memory` | 1–2 q | The *rate of change* of the price gain; 1st-deriv still positive but 2nd-deriv turning negative is the **earliest** price-reversal tell, ~1–2 q ahead of the actual roll-over |
| **P4** | Memory spot/contract spread | 🟨 price | `chips.hbm-memory` | 1–2 q | Spot premium/discount vs. contract; spot turning discount = channel demand already weaker than locked-in contract volume |
| **P6** | BoM cost structure | 🟨 price (structural) | `chips.foundry-packaging` | structural | Module cost-share shifts in the rack BoM (~memory 26%, ~$7.8M/rack). Re-weights bargaining power & risk across the chain |
| **X1** | Workload structural shift | ⬛ structural | `chips.merchant-gpu`, `models.reasoning-agentic` | structural | Training → Inference → Agentic mix; CPU/GPU attach; inference-specific silicon (Groq-class) share. Re-distributes value and **relocates the bottleneck** |
| **X3** | Export controls & geopolitics | ⬛ structural | `chips.*` (+ TSMC's own risk) | event | China-control scope, Huawei's ~$12B gap, Taiwan-Strait, entity-list/KYC. **Consumes** the existing geopolitics module's output — do not rebuild (Part 15) |
| **S4ᶜ** | Optical/PCB lead times (slice of S4) | 🟥 supply | `chips.networking-silicon` | 1–2 q | CPO / 1.6T optical modules, high-end PCB (M8/M9 CCL) lead times |

**Layer read:** Chips carries the densest supply instrumentation. The headline supply warnings are
**S1** (packaging capacity outrunning orders) and **S3/P1** (HBM price gain rolling over); the demand
warnings are **D2/D3** (NVIDIA revenue slope + commitment slowdown). S9 is the structural demand
erosion (custom silicon eating merchant GPU).

### Layer 3 — INFRASTRUCTURE
Where demand is *expressed as money* (capex, rental price) and supply as *throughput* (ODM/OSAT
utilization, channel inventory).

| ID | Indicator | Side | Charter category | Lead | Read |
|---|---|---|---|---|---|
| **D1** | Hyperscaler CapEx revisions | 🟦 demand | `infrastructure.hyperscale-cloud` | 6–12 mo | MSFT/GOOGL/AMZN/META/ORCL capex-guidance QoQ revision direction. Absolute level doesn't matter — **two consecutive downward revisions = strong reversal signal**. Track neoclouds (CoreWeave, Nebius) to catch the marginal buyer |
| **D6** | GPU cloud rental price | 🟦 demand | `infrastructure.neocloud` | 0–3 mo | H100/H200/B200 spot & on-demand $/GPU-hr — the most immediate market-clearing price; speed of old-gen rent collapse after a new launch reveals overall slack |
| **D9** | ODM monthly revenue & guidance | 🟦 demand | `infrastructure.hyperscale-cloud` | 1–2 q | Foxconn/Quanta/Wistron/Wiwynn/Supermicro AI-server revenue. **Taiwan monthly revenue is the world's only monthly-frequency hard AI-hardware demand datapoint — the highest-value mid-lead indicator in the system** |
| **S5** | ODM/OSAT utilization | 🟥 supply | `infrastructure.hyperscale-cloud` | 1–2 q | AI-server assembly + test utilization, overtime/hiring. Utilization falling from peak while revenue still flat = early confirmation of shipping-momentum decay |
| **S4ⁱ** | Liquid-cooling lead times (slice of S4) | 🟥 supply | `energy.cooling` | 1–2 q | CDU + UQD (quick-disconnect) lead times |
| **S10ⁱ** | Channel inventory (slice of S10) | 🟥 supply | `infrastructure.hyperscale-cloud` | 1–2 q | Channel-side inventory build |
| **P2** | GPU rental spot price (technical) | 🟨 price | `infrastructure.neocloud` | 0–3 mo | Same series as D6, treated technically: 90-day MA + Bollinger bands to detect trend breaks |
| **P3** | Used-GPU market price | 🟨 price | `infrastructure.neocloud` | 0–3 mo | H100/A100 secondary-market clearing price + listing volume. **Glut shows up in the used market first** — listing volume spiking + price crashing = strong glut signal |
| **P5** | Supply-chain relative strength | 🟨 price (cross-cutting) | macro overlay (Part 15) | 1–2 q | A self-built 30-name equal-weight AI-supply-chain index (TW/US/JP/KR) vs. the broad market + valuation percentile. 60 consecutive days of underperformance corroborates a consensus turn |
| **X5** | Financing environment | ⬛ structural | `infrastructure.neocloud` | 2–4 q | AI-corp credit spreads, convertible terms, private-valuation moves, neocloud GPU-collateral loan terms. **Rising cost of capital squeezes the marginal buyer (neoclouds) first — their orders vanish earliest** |

**Layer read:** Infrastructure's DMI is driven by **D1** (capex) and **D9** (the monthly ODM hard
data — the system's single most valuable mid-lead signal); its SMI by **S5** (assembly utilization).
The price family (P2/P3) is the fastest glut tripwire, and **X5** is the structural demand-erosion
channel (financing drying up at the margin).

### Layer 4 — MODELS
Pure demand and structural — no supply-side hardware instrumentation lives here.

| ID | Indicator | Side | Charter category | Lead | Read |
|---|---|---|---|---|---|
| **D4** | Token economics | 🟦 demand | `models.frontier-closed` | 3–6 mo | Inference unit price ($/M tokens) decline rate **vs.** token-consumption growth rate. If price falls faster than usage grows → revenue-side deflation → demand-saturation precursor. If usage outpaces → healthy Jevons effect |
| **D8** | Model-release & funding cadence | 🟦 demand | `models.frontier-closed` | 3–9 mo | Frontier-lab flagship release interval, training-compute scale claims, private-raise size & valuation. A tightening funding window shows up in compute orders 1–2 q later |
| **X1** | Workload structural shift | ⬛ structural | `models.reasoning-agentic` | structural | (see Chips) Training → Inference → Agentic mix — the demand-mix driver behind the chip read |
| **X4** | Algorithmic-efficiency jumps | ⬛ structural | `models.open-weight` | event | DeepSeek-class step-changes. Short-term: suppresses compute-demand expectations. Medium-term: amplifies demand via Jevons. **Must verify direction with 2-quarters-post token-usage data — do not react on the announcement alone** |

**Layer read:** Models is the *leading edge of demand*. **D4** is the canary for revenue-side
deflation; **X4** is the highest-variance structural shock (a single efficiency event can whipsaw
the whole demand expectation — hence the explicit "wait two quarters, verify with usage" rule, which
is the charter's anti-whipsaw discipline, Part 10).

### Layer 5 — APPLICATIONS
The ultimate demand test — does the demand self-fund?

| ID | Indicator | Side | Charter category | Lead | Read |
|---|---|---|---|---|---|
| **D5** | AI application revenue | 🟦 demand | `applications.enterprise-copilots` | 6–12 mo | Enterprise AI software/API revenue growth (MSFT AI run-rate, model-maker ARR, SaaS AI-attach). **Tests whether demand can self-fund — the ultimate basis for capex sustainability** |
| **D10** | Enterprise adoption penetration | 🟦 demand | `applications.enterprise-copilots`, `applications.consumer-ai` | 6–12 mo | Adoption-rate surveys, AI-product MAU/paid-conversion, agentic-deployment counts. Tells you whether demand is *broadening* or *concentrated in a few buyers* |

**Layer read:** Applications is the deepest-lead demand signal (6–12 mo) and the one the charter
already flags as the **frothiest, least-durable layer** (retention ~40%). A weak, decelerating D5/D10
is the top of the derived-demand chain whose air-pocket reaches wafer orders 2–3 quarters later
(charter Part 2, worked hypothesis example).

### Cross-cutting macro overlay (Part 15)
**X2, X3, X4, X5, P5, P6** are not owned by a single layer — they are the exogenous forces the Main
agent overlays on the whole cake. Each is tracked as a Finding under the same doctrine, with
`impact.targets` naming which layers/decisions it bends. The overlay's job is to tell the
orchestrator **when an external force, not internal AI dynamics, is the dominant driver this cycle**
("demand signal strong, but an export-control escalation is the binding risk").

### 3.x Quick index — all indicators by side
- **Demand (🟦, feed DMI):** D1 D2 D3 D4 D5 D6 D7 D8 D9 D10
- **Supply (🟥, feed SMI):** S1 S2 S3 S4 S5 S6 S7 S8 S9 S10
- **Price / confirmation (🟨, §4.4 — do *not* enter DMI/SMI):** P1 P2 P3 P4 P5 P6
- **Structural (⬛, impulse overlay, Part 15):** X1 X2 X3 X4 X5

---

## 4. The Category Agent pipeline (data → signal → score)

### 4.1 Data ingestion (Part 9 canonical store; Part 22 source reality)

Sources are tiered by how machine-ready they are; the doctrine's "primary over secondary" (Part 1
rule 5) maps onto this:

| Tier | Definition | Examples | Handling |
|---|---|---|---|
| **A — structured** | stable API, machine-readable, direct to store | SEC EDGAR API, TWSE monthly-revenue OpenAPI, market-quote API, SEMI stats | scheduled API connector |
| **B — semi-structured** | fixed-format web/PDF, needs parsing | earnings decks, TrendForce reports, press releases | scraper + LLM/VLM extraction |
| **C — unstructured** | narrative text, needs comprehension + quantification | earnings-call transcripts, news, research, channel checks | LLM extraction pipeline (§4.2) |
| **D — human intel** | channel checks, internal cross-dept | supplier lead-time reports, customer-side rumor | standardized manual form, same schema |

**Core source list** (→ indicators served): SEC EDGAR (D1,D2,D3,S2,S10) · TWSE/MOPS OpenAPI (D9) ·
existing earnings-call system (D1,D2,D5,S1,S2,S5) · TrendForce/DRAMeXchange (S3,P1,P4) · GPU-rental
comparison sites (D6,P2) · SEMI/SEAJ (S6,S8) · industry-media RSS (15–20 feeds: DigiTimes, SemiAnalysis,
Tom's Hardware, Reuters semis) for event detection across all families · market-quote API (P5) ·
BIS/Federal Register (X3) · secondary-equipment markets (P3).

**Ingestion design:**
- **Scheduler** — Airflow (or lightweight cron + queue); one DAG per source; auto-retry ×3 then alert.
- **Connector contract** — every connector emits a uniform `RawDocument {source_id, fetched_at, url,
  content, content_hash}`; hash-dedupe into the raw zone.
- **Scraper resilience** — B-tier sources carry a DOM-snapshot diff; a layout change alerts and
  **degrades to manual capture** rather than silently dropping data (Part 29 canaries).
- **Four data-quality checks** — timeliness (overdue source alerts), completeness (field-miss rate),
  consistency (same indicator across sources beyond tolerance → human review), plausibility (values
  beyond historical 6σ are quarantined first).

### 4.2 Signal extraction (Parts 5, 7, 8)

Pipeline: `RawDocument → relevance filter (cheap model drops ~80% noise) → structured extraction (LLM
emits Finding JSON per the §2.1 schema) → validation (schema + value-plausibility + source-credibility
rating) → dedupe & reconcile (merge multi-source reports of one event, keep highest-tier value) →
store (time-series DB + graph)`.

This is the charter's category-agent harness (Part 5) with two **doctrine guardrails** front and
center:
- **Fetched content is data, not instructions** (Part 8) — a page never redirects the agent's task.
- **The relevance filter is the cost control** — a small model on the front saves ~80% of tokens
  (Part 27 cost model); the large model is reserved for the structured extraction that matters.

### 4.3 Scoring & indices (computed in code — Part 5)

1. **Standardize each indicator** to a monthly series (high-freq → monthly mean; quarterly → step-hold
   with a staleness-decay flag), then a **36-month rolling z-score**: `z = (x − μ₃₆)/σ₃₆`. Series with
   < 36 months borrow an initializing distribution from a same-family indicator, then switch at full
   window.
2. **Event-type indicators (X3, X4, D8)** do *not* enter the continuous series — they apply as an
   **impulse** added to the current index, decaying with an **8-week half-life**.
3. **Compute DMI, SMI, SDGI** per §2.3, with `freshness` weighting.
4. **Initial weights** (calibrated by backtest, never hand-tuned to the last event):

   | Demand | w | Supply | w |
   |---|---|---|---|
   | D1 | 0.20 | S1 | 0.20 |
   | D9 | 0.18 | S3 | 0.16 |
   | D3 | 0.14 | S2 | 0.14 |
   | D6 | 0.12 | S4 | 0.12 |
   | D4 | 0.10 | S6 | 0.10 |
   | D2 | 0.10 | S5 | 0.08 |
   | D7 | 0.08 | S10 | 0.08 |
   | D5 | 0.05 | S7 | 0.06 |
   | D8 | 0.015 | S9 | 0.04 |
   | D10 | 0.015 | S8 | 0.02 |

5. **Four-quadrant state machine** — maps directly onto the charter's market-status word (Part 17):

   | Quadrant (DMI, SMI) | Market state | → Charter status | Operator meaning |
   |---|---|---|---|
   | DMI high / SMI low | **shortage intensifying** | Constrained | allocation & long-contract leverage; risk = anchoring long-term capacity on a shortage peak |
   | DMI high / SMI high | **fast balanced expansion** | Healthy → Accelerating | most comfortable but most dangerous — supply is catching up; watch for ΔSDGI turning negative |
   | DMI low / SMI high | **glut forming** | Frothy → At-risk | immediately review capex commitments, take-or-pay exposure, inventory |
   | DMI low / SMI low | **contraction rebalance** | At-risk | preserve flexible capacity, counter-cyclically position for the next platform |

### 4.4 Confirmation layer (the price family)

The **P-family (P1–P6) does not enter DMI/SMI directly.** Price is the *result* of supply/demand —
fastest to react but noisiest. It runs as an independent **confirmation layer**: when a physical
index fires *and* the price layer agrees in direction, **escalate the alert one level**; when the
price layer **diverges**, hold the level and flag the divergence. This is the charter's dispersion
discipline (Part 1) applied to the demand/supply read.

### 4.5 Cross-validation = the signal/noise triage (Part 10)

No single indicator is a conclusion. A **high-confidence signal** is defined as **≥ 2 signal families
and ≥ 3 indicators resonating in the same direction within one month**. This is exactly the charter's
Part 10 bar (persistent + corroborated + material + mechanistic), stated numerically — and it is what
the recommendation skill triages on before any action.

---

## 5. Alerting & action (Parts 8, 17, 23, 30, 32)

### 5.1 Alert tiers (asymmetric, demand-biased thresholds)

| Level | Trigger | Cadence |
|---|---|---|
| 🟢 **Green** | `|SDGI| ≤ 1.0σ` and `|ΔSDGI| < 0.5σ` | routine bi-weekly |
| 🟡 **Yellow** | `1.0σ < |SDGI| ≤ 1.5σ`; or ΔSDGI two same-direction periods totaling > 0.5σ; or any indicator with weight ≥ 0.12 breaching 2σ alone | weekly; refresh scenario model |
| 🟠 **Orange** | `1.5σ < |SDGI| ≤ 2.0σ` **and** price layer confirms; or ≥ 2 families / 3 indicators resonating. **Demand-reversal direction trips Orange at 1.3σ** (asymmetric — downside tolerance is lower) | start countermeasure assessment; contract & inventory exposure audit |
| 🔴 **Red** | `|SDGI| > 2.0σ`; or a confirmed structural (X) event rated *severe* | → Digital War Brain / **OODA** (= charter high-stakes human gate, Part 23); decision memo in 96 h |

> **The asymmetry is deliberate and is the key domain judgment.** A **supply shortage** is, for the
> operator, a *scheduling* problem (allocate, second-source). A **demand reversal** is a *capex and
> inventory* problem (stranded commitments, take-or-pay exposure, write-downs) — far more damaging.
> So demand-reversal signals trip a higher alert at a *lower* threshold (1.3σ vs 1.5σ for Orange).
> This is why the demand/supply tagging in §3 is not cosmetic — **the same |SDGI| means different
> things and triggers different actions depending on which side is moving.**

### 5.2 Playbook (direction × level)

| Level | Shortage direction (SDGI rising) | Glut direction (SDGI falling) |
|---|---|---|
| 🟡 | inventory-check long-lead parts; confirm supplier capacity-reservation clauses; update allocation-priority sim | freeze new long-contract share; tally take-or-pay exposure; model inventory burn-down |
| 🟠 | accelerate second-source qualification; lock bottleneck parts on contract but **never beyond demand visibility**; submit capacity plan to leadership | open contract-flexibility renegotiation; phase/milestone capex; lower safety-stock targets; review neocloud-class marginal-customer exposure |
| 🔴 | OODA P1; cross-functional war room; customer-allocation & revenue-protection plan in 96 h | OODA P1; freeze non-essential capex; worst-case cashflow & impairment run |

### 5.3 Notification SLA & de-escalation
- 🟢 bi-weekly one-pager · 🟡 weekly + deep-dive attachment, scenario update in 5 business days · 🟠
  countermeasure meeting within 48 h, named owner + action tracker · 🔴 immediate push + phone tree,
  decision memo in 96 h, daily standup until downgrade.
- **De-escalation rule (anti-chatter):** must spend **two consecutive observation periods** back in
  the lower band before downgrading — the charter's anti-whipsaw stability rule (Part 10).

---

## 6. Knowledge-graph projection (optional — Neo4j)

A graph projection of the canonical store (Part 9) that makes "which suppliers does this alert touch?"
a one-hop query. New node types hang off the existing `:Company`/`:Supplier`/`:Event` graph:

```cypher
(:Indicator  {id, name, family:"D|S|P|X", side, weight, leadMonths, freq, decayLambda, status})
(:Signal     {signalId, observedAt, capturedAt, value, unit, direction, magnitude, confidence,
              polarityDemand, polaritySupply})
(:IndexValue {index:"DMI|SMI|SDGI", t, value, regime})
(:Alert      {alertId, level:"Y|O|R", openedAt, closedAt, resolution})

(s:Signal)-[:MEASURES]->(i:Indicator)
(s:Signal)-[:ABOUT]->(c:Company)        // hangs off the existing supplier nodes
(s:Signal)-[:FROM_SOURCE]->(d:DataSource)
(i:Indicator)-[:FEEDS {weight}]->(x:IndexValue)
(a:Alert)-[:TRIGGERED_BY]->(s:Signal)
(a:Alert)-[:ESCALATED_TO]->(e:Event)    // Red → OODA event
```

Chokepoint suppliers are marked `critical=true`; their signals get a **×1.5 magnitude weight**.
Example — recent supply-contraction signals touching any critical supplier:

```cypher
MATCH (s:Signal)-[:ABOUT]->(c:Company {critical:true})
WHERE s.capturedAt > datetime() - duration("P30D")
  AND s.polaritySupply = -1 AND s.confidence >= 0.6
RETURN c.name, s.excerptSummary, s.magnitude
ORDER BY s.magnitude DESC, s.capturedAt DESC;
```

---

## 7. Development roadmap (reframes the charter's pilot-first / cold-start, Parts 27 & 34)

Build **one reference Category Agent end-to-end before fanning out** — this *is* the charter's
pilot-first rule (Part 27): one layer's worth of indicators, costed and backtested, is the go/no-go
for the rest.

| Phase | Span | Deliverable | Acceptance |
|---|---|---|---|
| **Phase 1 — MVP** | wk 0–6 | 15 core indicators (D1,D2,D3,D6,D9 / S1,S2,S3,S4,S6 / P1,P2,P4 / X2,X3) semi-automated: EDGAR + TWSE connectors live, rest manual-monthly; spreadsheet SDGI; bi-weekly report template | first SDGI produced + rough 2023–2026 backtest; report enters the existing exec meeting |
| **Phase 2 — Automation** | wk 6–16 | earnings-call system integrated; LLM extraction + Finding schema live; TimescaleDB + Neo4j writes; alert state machine + push; Grafana dashboard | 80% of signals auto-ingested; Yellow-alert end-to-end latency < 24 h; backtest recall ≥ 80% |
| **Phase 3 — Depth** | wk 16+ | all indicators covered; playbook engine; OODA integration; scenario simulator (weight sensitivity, hypothesis injection); false-alarm tuning | Orange false-alarm ≤ 30%; one Red-alert tabletop exercise completed |

**Resourcing:** Phase 1 ≈ 1 analyst + 0.5 engineer; Phase 2 ≈ 1 full-time engineer; external data
subscriptions (TrendForce etc.) are the main cash cost (the licensing call is leadership's, per Part
22).

**Cold-start (Part 34):** seed the baseline from the June-2026 market-state map as the `asOf` 2026-06
canonical snapshot, and **backfill via replay** over 2023 Q1–2026 Q2 (on `capturedAt`) so the
temporal logic and calibration record have a starting series — flagged **reconstructed** and
confidence-discounted until live cycles accrue.

---

## 8. Governance, lifecycle & known limits

### 8.1 Indicator lifecycle (Parts 12, 16, 18)
- Every indicator carries `status` (active / degraded / retired) and a **failure condition**. A source
  dark for 3 months, or whose correlation with its family collapses, drops to `degraded` with weight
  zeroed; a backup indicator fills in.
- **Platform-transition de-weighting:** in the quarter before/after a generation change (Rubin → Rubin
  Ultra → Feynman), generation-sensitive indicators (D6, P3) auto-de-weight 50% so a transition jump
  isn't misread as a cycle signal.

### 8.2 False-positive / false-negative management (Part 12 calibration)
- Every Orange+ alert, on close, **must record a `resolution`** (real turn / false alarm / inconclusive)
  → accumulates into a **confusion matrix** → drives the **semi-annual weight recalibration**.
- **Recalibration is gated:** weights re-tune at most every 6 months, only after a backtest comparison
  of old vs. new; **never** ad-hoc after a single false alarm (anti-overfitting).
- **Backtest targets:** recall on major turns **≥ 80%**, Orange+ false-alarm **≤ 30%**, mean lead
  **≥ 60 days**.

### 8.3 Known limits (state them plainly — doctrine honesty)
- **Structural breaks are unpredictable.** The system detects *momentum change*; a no-warning policy
  black swan (sudden control, war) it can only react to faster, not foresee — that stays with the
  geopolitics module.
- **Reflexivity.** When everyone (including this system) watches the same indicators, their lead
  decays. Treat weights and the indicator set as a **dynamic asset, not settled truth.**
- **Data bias.** Supply-chain messaging is managed (earnings-call language is engineered). Extraction
  **anchors on behavior and numbers**; tone is auxiliary only.
- **Operational intelligence, not investment advice.** Output informs operational planning; any
  contract action passes legal + finance review first (Part 23).

---

## Appendix A — Alert dashboard (one-page layout)
- **Top:** live SDGI + 12-month trend, current alert color, four-quadrant position.
- **Middle:** DMI / SMI decomposition waterfall (which indicators drove this period's move), price
  confirmation-layer traffic light.
- **Bottom:** top-10 signals of the last 14 days (summary + confidence + link to the supplier subgraph),
  data-source health bar.

## Appendix B — Immediate Phase-1 tasks
- Secure EDGAR, TWSE OpenAPI, and market-quote API access; assemble the 15–20-source RSS list.
- Map the existing AI-demand-saturation monitor's indicators & history onto this metric registry (the
  D-family inherits directly).
- Hand-build the SDGI prototype series over 2023 Q1–2026 Q2 and verify the four-quadrant narrative
  against the known events (2023 H100 shortage, 2024 CoWoS bottleneck, 2025 HBM4 scramble).

---

> **The completeness test, inherited unchanged (charter close):** for any number on screen, a TSMC
> executive can ask *"how do you know that, and is it demand or supply moving?"* — and find the
> Finding, its polarity, its source, and its confidence already written. If not, it does not ship.
