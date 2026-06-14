# Sources — AI Market State Map (June 2026)

All figures in [`ai-market-state-map.md`](./ai-market-state-map.md) are seeded from the deep-research
sweep below. Where multiple sources conflicted (e.g., Anthropic ARR, hyperscaler capex totals), the
map uses the most consistently-cited figure and shows a range.

## Framework & overall market
- Jensen Huang's 5-layer "cake" (Davos/WEF 2026) — https://blogs.nvidia.com/blog/davos-wef-blackrock-ceo-larry-fink-jensen-huang
- AI market size $602B (2026) → $3.64T (2033), ~29.3% CAGR — MarketsandMarkets; VanEck "Top AI Companies to Watch 2026"; McKinsey "next era of semiconductor value"
- Software 3.0 framing — Andrej Karpathy (1.0 code / 2.0 weights / 3.0 NL-programmed agents)

## Layer 1 — Energy
- DC power 132 GW (2026) / 565 TWh (+26%) — Gartner (2026-06-10 release); InfotechLead
- IEA aggressive case >1,000 TWh — tech-insider.org
- AI ≈ 31% of DC power 2026 — Gartner / CIOL
- US DC 4.4% (2023) → 6.7–12% by 2028 — Belfer Center; S&P Global Commodity Insights
- Nuclear/SMR deals — latitudemedia (Meta 6.6 GW); smrintel.com; introl.com; Meta–Oklo 1.2 GW Pike County (Jan 2026); MSFT Three Mile Island 835 MW/$16B; Amazon Susquehanna + Energy Northwest 4 SMRs; Google–Kairos 500 MW
- Liquid cooling ~37% (2026) vs ~3% (2021); PUE bands — MarketsandMarkets; Schneider Electric blog; Tom's Hardware "cooling state of play"

## Layer 2 — Chips
- NVIDIA DC revenue $115.2B FY2025 (+142%), share 86%→~75% by 2026, custom ASIC 40–65% TCO — IDC; VanEck; hashrateindex
- HBM share SK Hynix ~53–62% / Micron ~21% / Samsung ~17–35%; HBM3E ≈⅔ of 2026; HBM4 ramp — Astute Group; TrendForce; Counterpoint Research
- TSMC CoWoS 35k→130k wafers/mo by end-2026 (~80% CAGR) — DigiTimes; CNBC (2026-04-08); FinancialContent
- Broadcom AI rev $10.8B Q2 (+143%), $73B backlog, ~70% custom-ASIC share; Marvell up to $11B; Broadcom+Marvell ~95% — Broadcom/Marvell SEC 8-Ks (FY2026); Tom's Hardware; cryptobriefing

## Layer 3 — Infrastructure
- Hyperscaler capex 2026 ~$600–725B (vs ~$388B 2025), ~75% AI-tied; per-co breakdown — Tom's Hardware; IEEE ComSoc Technology Blog; Futurum; datacenterrichness
- CoreWeave Q1'26 rev $2.08B, backlog $99.4B, capex ≤$35B, $21B Meta deal — CoreWeave Q1'26 results; brandergroup; io-fund
- Nebius Q1 rev $399M (+684%); Crusoe $1.375B Series E @ $10B+ — Yahoo Finance; DataCenterKnowledge
- $/GPU-hr B200 ~$3–27 — getdeploying; DeployBase; Northflank
- Ethernet overtakes InfiniBand (~⅔ of AI back-end switch sales Q1'26) — Dell'Oro Group; SDxCentral; IEEE ComSoc
- OpenAI ~150k GB200 multi-partner cluster — avanzaenergy; Neowin

## Layer 4 — Models
- Frontier benchmarks (Gemini 3.1 Pro SWE-bench 78.8% / ARC-AGI-2 77.1% / GPQA 94.3%; GPT-5.4; Claude Opus 4.6) — AgentMarketCap (ARC-AGI-2 leaderboard); llm-stats.com; DataLearner
- Token price decline ~80% early-2025→early-2026; $0.10–$30/M range — CloudZero; Featherless; iternal.ai
- OpenAI ~$25B ARR (Feb'26, $2B/mo); Anthropic ~$30B ARR (Apr'26, 30x/15mo) — Epoch AI; SaaStr; the-ai-corner; tipranks
- ChatGPT 900M WAU (Mar'26) → 1B MAU (Jun'26) — Reuters via ALM Corp; DemandSage

## Layer 5 — Applications
- AI coding ~$12.8B revenue 2026 (2x 2024) — letsdatascience; getpanto
- Cursor/Anysphere ~$3B ARR (May'26), ~$50–60B raise — TrendingTopics; TheNextWeb; tech-insider
- Devin (Cognition) ~$492M ARR, ~$26B val — Winbuzzer
- Claude Code 57% dev awareness / 18% workplace use — getpanto (Anthropic stats)
- Glean ~$300M ARR (3x in 15 mo); M365 Copilot ~20M seats — mlq.ai; Redress Compliance
- Sierra ~$200M ARR; Decagon ~$35M ARR — getlatka; company reports
- Harvey $11B val / ~$190M ARR / 1,300 firms — CNBC (2026-03-25); Sacra
- Perplexity 45M MAU / ~$450M ARR — DemandSage; getpanto
- Anduril ~$60B raise; Shield AI $12.7B — AI funding trackers; opus.pro
- Synthesia ~$150M ARR ($4B val); Runway ~$265M ARR — Synthesia; Fueler
- App-layer unit economics: AI-native GRR ~40% vs SaaS ~63%; sub-$50/mo ~23% GRR vs $250+/mo ~70%; EV/Rev ~12.5x (down from 15–20x); ~80% startup-failure forecast; OpenAI −122% op margin Q1'26 — Userpilot; Qubit Capital; ideaproof.io; wheresyoured.at

> Note: startup ARR/valuation figures move fast and several rely on secondary trackers rather than
> audited filings. Treat single-sourced private-company numbers as estimates; the future Category
> Agents should attach a confidence score and prefer primary sources (filings, official posts).

## Method & harness engineering (referenced in the charter)
- Meta-Harness: End-to-End Optimization of Model Harnesses — Lee, Nair, Zhang, Lee, Khattab, Finn
  (Stanford / KRAFTON / MIT), arXiv:2603.28052, Mar 2026 — https://arxiv.org/abs/2603.28052
  (project: https://yoonholee.com/meta-harness/). Basis for charter Part 36.
