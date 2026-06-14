# AI Market State Map — Layer-by-Layer Synthesis

> Founding spec for a platform that shows the live **state of the AI market**, organized
> around **Jensen Huang's 5-layer AI "cake"** (Energy → Chips → Infrastructure → Models →
> Applications). This is the *taxonomy + metric design* that the future Software 3.0 agent
> swarm will be programmed against. Data is seeded from deep research as of **June 2026**.

## Why this exists

Each layer of the AI stack is decomposed into MECE sub-categories. Every sub-category has:
- a **constituent set** — the companies/technologies that live in it, and
- an **evaluation rubric** — quantitative + qualitative metrics that let us rate "how is this category doing."

**Software 3.0 framing (Karpathy):** 1.0 = code, 2.0 = neural-net weights, 3.0 =
natural-language-programmed LLM agents. The end-state is **one research/rating agent per leaf
category**, rolling up into layer-agents, rolling up into a market-state orchestrator.

> **Overall market frame:** Global AI market ~**$602B (2026) → ~$3.64T (2033), ~29% CAGR**.
> The thesis behind the cake: every layer must scale *together* — "the largest infrastructure
> buildout in human history." So the market's status should be driven by the **worst bottleneck**
> (the weakest link), not just headline growth.

---

## North star: from state → recommendation

**The deliverable is not the dashboard — it is the recommendation.** This platform exists to
answer one executive question: *"so what should TSMC do?"* The 5-layer state map, the scorecards,
and the indices are the **evidence base**; the product is the **prioritized, defensible
recommendation** that the evidence supports.

Every recommendation maps to a real TSMC decision:

| Decision area | The "so what" it answers |
|---|---|
| **Capacity & capex** | How much N2/N3 + CoWoS/SoIC to build, and when — sized off derived demand from the layers above |
| **Pricing** | Where TSMC is the binding bottleneck (→ pricing leverage) vs. where it is not |
| **Account strategy** | Which customers' demand is inflecting (NVIDIA vs. custom-ASIC programs vs. Apple) |
| **Risk posture** | Substitution (Samsung/Intel), geopolitics/export controls, and AI-demand-shock exposure |

So the dashboard **leads with the recommendation** and lets the user drill *down* into the state
that justifies it — never the reverse. A recommendation with no traceable evidence chain, or market
state with no "so what," is an incomplete product. (How each agent tier builds a recommendation up
from Findings is specified in `agent-swarm-charter.md`.)

---

## The common rating rubric (applies to every leaf category)

Each category is rated on 6 reusable dimensions so layers are comparable:

1. **Momentum** — growth rate of the category's core quantity (revenue, GW, capacity, share).
2. **Unit economics** — margin / cost-per-unit trajectory ($/MWh, $/token, $/GPU-hr, NRR).
3. **Competitive structure** — concentration (HHI / share of #1), number of credible players.
4. **Moat & defensibility** — switching cost, ecosystem lock-in, data/network effects.
5. **Bottleneck / supply constraint** — is this the gating layer right now? (lead times, queues).
6. **Strategic risk** — geopolitical / regulatory / capital-intensity / circular-financing exposure.

Each dimension gets a plain **rating** (Very strong / Strong / Mixed / Weak / Very weak) with a
direction and a confidence — not a 0–100 score (see charter Part 17). Roll-up: category ratings →
**layer rating** (by weakest link) → one plain **AI market status** (*Accelerating / Healthy /
Constrained / Frothy / At-risk*), reported with the bottleneck, the direction, and the one-line
reason. No composite number on the cover.

---

## Layer 1 — ENERGY (the foundation)

> 2026 datacenter power: **~132 GW** (up from ~104 GW in 2025), **~565 TWh** (+26% YoY,
> Gartner); IEA's aggressive case >1,000 TWh. **AI servers ≈ 31% of DC power in 2026.**
> US DCs went 4.4% of grid (2023) → projected **6.7–12% by 2028.**

| Sub-category | Leading constituents | 2026 state snapshot |
|---|---|---|
| **Power generation** (gas, nuclear/SMR, renewables+storage, geothermal/fusion frontier) | Vistra, Constellation, GE Vernova; SMRs: Oklo, Kairos, TerraPower, X-energy | **10 GW+ nuclear contracted** by big tech. Meta 6.6 GW (Vistra/Oklo/TerraPower); Meta–Oklo 1.2 GW / 16 Aurora reactors (Pike Cty OH, Jan 2026); MSFT Three Mile Island 835 MW/$16B; Amazon $20B+ Susquehanna + Energy Northwest 4 SMRs (320 MWe); Google–Kairos 500 MW SMR |
| **Grid & transmission / interconnection** | Utilities, ISOs/RTOs, transmission developers | Interconnection queues are the gating constraint; multi-year waits; "time-to-power" now the scarce resource |
| **On-site / behind-the-meter gen + storage** | Bloom Energy (fuel cells), gas turbines, BESS | Behind-the-meter gas + batteries used to bypass grid waits |
| **Cooling** (air, direct-to-chip liquid, immersion) | Vertiv, Schneider, Boyd, LiquidStack | **Liquid cooling ≈37% adoption in 2026** (was ~3% in 2021); PUE: air 1.5–1.8, D2C 1.15–1.30, immersion 1.02–1.08 |
| **Energy procurement & markets** (PPAs, $/MWh) | Hyperscaler energy teams, IPPs | PPAs + nuclear restarts; $/MWh rising in constrained regions |
| **Electrical equipment supply chain** (transformers, switchgear, UPS) | Eaton, Siemens, ABB | Transformer/switchgear lead times a hidden bottleneck |
| **Efficiency & sustainability** (PUE/WUE, carbon) | All operators | PUE/WUE + carbon intensity under regulatory scrutiny |

**Evaluation metrics:** GW added/yr & GW under contract; TWh demand & % of regional grid;
$/MWh and PPA price trend; interconnection queue wait (months); % liquid-cooled & fleet PUE/WUE;
nuclear/SMR MW contracted; transformer/turbine lead times *(qual)*; permitting & regulatory risk *(qual)*;
carbon intensity / curtailment exposure *(qual)*.

---

## Layer 2 — CHIPS / COMPUTE

> **NVIDIA** DC revenue **$115.2B FY2025 (+142%)**; AI-accelerator share **~86% → ~75% by 2026**
> as custom ASICs scale (**40–65% TCO advantage** claimed). **CoWoS** packaging is *the* supply
> bottleneck.

| Sub-category | Leading constituents | 2026 state snapshot |
|---|---|---|
| **Merchant GPUs** | NVIDIA (Blackwell B200/GB200), AMD (MI3xx), Intel (Gaudi) | NVIDIA still dominant but share eroding; AMD the credible #2 |
| **Hyperscaler custom ASICs** | Google TPU, AWS Trainium/Inferentia, Microsoft Maia, Meta MTIA, OpenAI–Broadcom | Fastest-shifting sub-category; in-house silicon to cut TCO & NVIDIA dependence |
| **AI-silicon startups** | Cerebras, Groq, SambaNova, Tenstorrent, Etched | Inference-speed / wafer-scale niches; design-win durability unproven |
| **HBM / memory** | SK Hynix (~53–62%), Micron (~21%), Samsung (~17–35%) | **HBM3E ≈ ⅔ of 2026 shipments**; HBM4 ramping (SK Hynix +40% power-eff, 10 Gbps; Micron 11 Gbps samples) |
| **Foundry & advanced packaging** | TSMC (leading-node + CoWoS), Samsung, Intel Foundry | **CoWoS 35k → 130k wafers/mo by end-2026** (~80% CAGR); NVIDIA reserves the majority; ASE/Amkor overflow |
| **Networking / interconnect silicon** | NVIDIA (NVLink), Broadcom, Marvell | Broadcom AI rev **$10.8B Q2 (+143%)**, **$73B backlog**, ~70% custom-ASIC share; Marvell up to $11B 2026; **Broadcom+Marvell ≈95%** of custom co-design |
| **EDA & IP** | Synopsys, Cadence, Arm | Picks-and-shovels; AI-assisted design; export-control sensitive |

**Evaluation metrics:** market share % & share-trend; perf/watt and FLOPS/$; revenue growth & gross
margin; CoWoS wafer capacity & HBM bit-growth; design-win backlog ($); lead times; **CUDA/software
lock-in** *(qual)*; supply-chain concentration (TSMC/Taiwan) *(qual)*; export-control / geopolitical
exposure *(qual)*.

---

## Layer 3 — INFRASTRUCTURE (clusters between chips and models)

> **Hyperscaler capex 2026 ≈ $600–725B** (vs ~$388B in 2025, +62–77%): Amazon ~$200B, Google
> ~$175–185B, Meta ~$115–135B, Microsoft ~$110–120B; **~75% AI-tied**. **Ethernet has overtaken
> InfiniBand** in AI back-end networks.

| Sub-category | Leading constituents | 2026 state snapshot |
|---|---|---|
| **Hyperscale cloud** | AWS, Microsoft Azure, Google Cloud, Oracle OCI | The capex engine; OCI surging on AI backlog |
| **Neoclouds / GPU-as-a-Service** | CoreWeave, Nebius, Crusoe, Lambda, IREN, Together | CoreWeave Q1'26 rev **$2.08B**, backlog **$99.4B**, 2026 capex ≤$35B, **$21B Meta deal**; Nebius Q1 rev $399M (+684%); Crusoe $1.375B Series E @ $10B+ |
| **Data-center developers / colo / REITs** | Equinix, Digital Realty, Vantage, QTS, Switch | GW-scale campuses; "power wars" replace "GPU race" |
| **Networking fabric** | NVIDIA (InfiniBand/NVLink/Spectrum-X) vs Ethernet/UEC (Broadcom, Arista) | **Ethernet ≈⅔ of AI back-end switch sales Q1'26** (was ~80% InfiniBand two yrs ago) |
| **Cluster & orchestration software** | CUDA, Slurm/Kubernetes, Ray, vLLM/TensorRT, SkyPilot | CUDA moat at this layer; inference-serving stack consolidating |
| **AI storage & data platforms** | VAST Data, WEKA, Pure, object stores | Feeding 100k-GPU clusters; checkpoint/throughput bound |

> Largest clusters: OpenAI multi-partner build **~150k GB200** (phased). B200 cloud **$/GPU-hr ≈ $3–27**
> depending on provider/commitment.

**Evaluation metrics:** capex $ & GW deployed/under-construction; fleet GPU count; utilization %;
$/GPU-hr trend; revenue backlog & contract duration; cluster scale (max GPUs); fabric mix (IB vs
Ethernet); **customer concentration** *(qual)*; **circular-financing / capital-intensity risk** *(qual)*;
software/switching lock-in *(qual)*; time-to-power *(qual)*.

---

## Layer 4 — MODELS

> Frontier (mid-2026): **Gemini 3.1 Pro** SWE-bench Verified **78.8%**, ARC-AGI-2 **77.1%**, GPQA
> **94.3%**; **GPT-5.4** family & **Claude Opus 4.6** trade #1s by benchmark. **Token prices fell ~80%
> early-2025→early-2026** (GPT-4 $30→$2.50/M, ~12x in 3 yrs); range now **$0.10–$30/M**. **OpenAI ~$25B
> ARR (Feb'26, $2B/mo); Anthropic ~$30B ARR (Apr'26, 30x in 15 mo, enterprise-led).**

| Sub-category | Leading constituents | 2026 state snapshot |
|---|---|---|
| **Frontier closed labs** | OpenAI (GPT-5.x), Anthropic (Claude Opus/Sonnet 4.x), Google DeepMind (Gemini 3.x), xAI (Grok 4) | No single leader across all benchmarks; reasoning + agentic is the battleground |
| **Open-weight models** | Meta Llama, Mistral, DeepSeek (V3/R1), Alibaba Qwen, Z.AI (GLM-5) | DeepSeek proved cost-parity is possible; open closing the gap |
| **Reasoning / agentic models** | o-series, Claude "thinking," Gemini reasoning | Test-time compute scaling; agentic eval (OSWorld, GDPval, BrowseComp) |
| **Multimodal / media models** | Image/video: Midjourney, Black Forest Labs, Runway, Google Veo; audio: ElevenLabs; world/robotics models | Fast-commoditizing; distribution-led |
| **Small / on-device models** | Phi, Gemma, Llama-small, quantization (llama.cpp) | Edge/latency/cost niche |
| **Embeddings & retrieval models** | OpenAI, Cohere, Voyage, open embeds | RAG backbone; quiet but sticky |
| **Eval / benchmark / model-hub infra** | Hugging Face, LMArena, Scale, Artificial Analysis | The "scorekeepers" — useful as data sources for *this very platform* |

**Evaluation metrics:** benchmark scores (SWE-bench, GPQA, ARC-AGI, agentic suites); $/M tokens
(in/out) & price-decline rate; context length; tokens/sec latency; API revenue / ARR & growth;
release cadence; open-weight downloads/adoption; **capability-frontier leadership** *(qual)*;
**safety/alignment posture** *(qual)*; developer-ecosystem strength *(qual)*; data moat *(qual)*.

---

## Layer 5 — APPLICATIONS

> AI coding alone ≈ **$12.8B revenue in 2026** (2x 2024's $5.1B). **Cursor/Anysphere ~$3B ARR (May'26)**,
> raising at ~$50–60B. **ChatGPT 900M WAU (Mar'26) → 1B MAU (Jun'26).** Vertical AI multiples are frothy
> (avg ~52x ARR; CX agents ~127x).

| Sub-category | Leading constituents | 2026 state snapshot |
|---|---|---|
| **AI coding** | Cursor/Anysphere, GitHub Copilot, Claude Code, Cognition/Devin, Replit, Windsurf | Cursor ~$3B ARR; Devin ~$492M ARR (~$26B val); Claude Code 57% dev awareness / 18% workplace use; hyperscaler pressure (Amazon Q, Gemini Code Assist) |
| **Horizontal enterprise copilots / knowledge** | M365 Copilot (~20M seats), Glean (~$300M ARR, 3x in 15 mo), Gemini Enterprise | Distribution = incumbents' edge; but Copilot weekly *usage* still <5% of seats — adoption ≠ usage |
| **Customer-experience agents** | Sierra (~$200M ARR), Decagon (~$35M ARR), Intercom Fin | Outcome/consumption pricing; CX agents priced ~127x ARR |
| **Vertical AI SaaS** | Legal: Harvey ($11B val, ~$190M ARR, 1,300 firms, 100k+ lawyers), Legora; Defense: Palantir, Anduril (~$60B), Shield AI ($12.7B); healthcare/finance | Vertical AI "breaking through" in 2026; high multiples |
| **Consumer AI** | ChatGPT, Gemini, Perplexity (45M MAU, ~$450M ARR), companion AI | ChatGPT ~77% chatbot web share; consumer = scale + brand |
| **Creative / media generation** | Synthesia (~$150M ARR), Midjourney, ElevenLabs, Runway (~$265M ARR) | Marketing/video; "wrapper" durability risk |
| **Agent platforms & dev tooling** | LangChain, vector DBs (Pinecone), eval/observability | The "AI middleware" picks-and-shovels of the app layer |

**Evaluation metrics:** ARR & growth rate; DAU/MAU & stickiness; net revenue retention; paid
conversion; valuation/ARR multiple; funding & valuation; **defensibility vs model commoditization /
"wrapper risk"** *(qual)*; distribution advantage *(qual)*; workflow lock-in / switching cost *(qual)*;
data network effects *(qual)*; regulatory exposure *(qual)*.

> **App-layer reality check (the signal the market status must capture):** this is the frothiest, least-durable
> layer. AI-native median **GRR ~40%** (vs ~63% for B2B SaaS); pricing tier predicts survival —
> **sub-$50/mo ≈ 23% GRR vs $250+/mo ≈ 70%**. EV/Revenue multiples have compressed to **~12.5x** (from
> 15–20x in 2024), and analysts forecast **~80% of AI app startups fail by 2027** on compute cost +
> model commoditization. Even leaders burn: **OpenAI ran ~−122% operating margin in Q1'26** with ChatGPT
> growth plateauing. → The app layer should be scored heavily on **retention/unit-economics and
> wrapper-risk**, not headline ARR.

---

## The Software 3.0 agent architecture (target end-state)

A three-tier agent swarm, programmed in natural language against the taxonomy above:

- **Leaf "Category Agent" (one per sub-category, ~40 total).** Inputs: this category's metric
  schema. Does: (1) pull quantitative metrics from data sources / APIs (earnings, TrendForce,
  Dell'Oro, Artificial Analysis, LMArena, funding trackers, energy/grid data), (2) run a scoped
  deep-research sweep for qualitative dimensions, (3) emit a **scorecard** (the 6-dimension rubric)
  as structured JSON + a short cited narrative + confidence.
- **Layer Agent (5).** Aggregates its leaf scorecards → a **layer rating** (by weakest link), flags the
  binding bottleneck, writes the layer brief.
- **Market-State Orchestrator (1).** Rolls the 5 layers into one plain **AI market status**, detects
  cross-layer tensions (e.g., chips ready but energy/grid gating), produces the top-level dashboard.

**Data model:** `layers[] → categories[] → { seedConstituents[], metrics{schema}, scorecard, sources[], asOf }`
(`taxonomy.json` is the durable contract — structure is human-governed; constituents and live metric
values are swarm-maintained seeds, see charter Part 16.)
(see [`taxonomy.json`](./taxonomy.json)).

**Refresh model:** **on-demand CLI first** (`refresh <category|layer|all>`), **cron wrapper later**
(GitHub Actions commits updated state; dashboard reads the committed JSON).

---

## Status & next passes (deferred)

This document is the *brainstorming / taxonomy* pass — **no application code, agents, or infra yet**.
Future passes, in order:
1. Encode `taxonomy.json` as the machine-readable contract.
2. Build the on-demand **Category Agent** (one reference agent end-to-end) + the scorecard schema.
3. Fan out agents to all ~40 leaf categories; add the Layer + Orchestrator roll-ups.
4. Dashboard to visualize the 5-layer cake + AI market status.
5. GitHub Actions cron to keep state fresh.

Sources for every seeded figure are in [`sources.md`](./sources.md).
