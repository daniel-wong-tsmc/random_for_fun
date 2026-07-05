# Artifact C — Merchant GPU market state (as of 2026-07-05)

# Merchant GPU Market — Executive Brief (as of July 5, 2026)

*Prepared for a TSMC executive audience. All claims cited; sources listed at end. Verification method: 5-angle web sweep (~75 claims), then 3-vote adversarial fact-check on the 12 load-bearing claims — all survived, with minor numeric corrections applied.*

## 1. Demand vs. supply: demand still exceeds supply at the leading edge, but the market has split into two tiers

Demand remains unfilled at every level of disclosure. NVIDIA's Q1 FY2027 (reported May 20, 2026) delivered $81.6B revenue (+85% YoY) with data center revenue of $75.2B (+92% YoY), and guided Q2 to ~$91B while assuming **zero** China data-center compute revenue [1][2]. At GTC in March 2026 Jensen Huang raised his visibility claim to "at least $1 trillion" in cumulative Blackwell + Vera Rubin orders through 2027 — double the $500B-through-2026 figure he gave in October 2025 [3][4]. As of June 2026 he still described NVIDIA as "supply constrained" despite having secured capacity for "very, very robust growth" [5]. Vera Rubin entered full production (announced June 1, 2026, Taipei) with production shipments from fall 2026, and all three HBM vendors qualified on HBM4 [6][7]. AMD is now a credible second source at gigawatt scale: record Q1 2026 data-center revenue of $5.8B (+57% YoY), with MI450 ramping in 2H26 against two 6GW-class commitments — OpenAI (Oct 2025) and Meta (Feb 2026) [8][9][10].

The buy side corroborates: the four largest hyperscalers guided roughly **$700-725B of combined 2026 capex, up ~77% YoY** (Microsoft ~$190B, Amazon ~$200B, Alphabet $180-190B, Meta $125-145B — the latter three all *raised* guidance in late April 2026), and every one of them describes itself as capacity-constrained, not demand-constrained [11][12][13][14]. Alphabet's cloud backlog nearly doubled in one quarter to $462B [13].

The nuance: this is a **leading-edge-only** shortage. H100-class cloud rental prices have fallen ~64-75% from peak, while B200/B300-class pricing holds firm [15][16]. Scarcity value now lives entirely in the newest silicon — the segment TSMC monopolizes.

## 2. The binding constraint: a moving queue — HBM/memory tightest upstream, power tightest downstream, CoWoS easing but not resolved

- **Advanced packaging:** CoWoS is sold out through 2026; TrendForce (June 15, 2026) puts the supply-demand gap at ~20%, narrowing to ~10% by year-end as TSMC capacity reaches 120-140k wpm, with real relief only in 2027 [17]. C.C. Wei has said supply will lag AI demand "for years" [18].
- **Memory has arguably overtaken packaging as the tightest upstream link.** SK hynix's entire 2026 output is sold out, and its April 2026 call said customer HBM requests exceed planned capacity *for the next three years* [19][20]. Conventional DRAM contract prices rose a record ~90-98% QoQ in 1Q26 with another +58-63% expected in 2Q26 [21], as HBM absorbs a rising share of DRAM wafer starts (~18% end-2025 → ~30% end-2027) [22]. Microsoft attributed ~$25B of its capex increase to component prices; Meta cited the same [11][14].
- **Power is the binding constraint on deployment.** Satya Nadella (Nov 2025): the problem is "not a compute glut, but power... a bunch of chips sitting in inventory that I can't plug in" [23]. US large-transformer lead times run ~2-4 years [24]; GE Vernova's gas turbines are effectively sold out into 2029-2030 on an ~80GW backlog [25]; median US grid-interconnection waits are ~55 months [26]. Stargate had only ~0.3GW operational in early 2026 against a ~10GW target [27].

**Net read for TSMC:** through 2026 the system is constrained *simultaneously* upstream (HBM, CoWoS, reportedly N2 and ABF re-tightening [28][29]) and downstream (power/shells). No node of the chain shows slack; wafer demand signals remain uncapped by end-demand. TSMC's own guidance reflects this — 2026 capex of $52-56B, full-year growth raised to >30%, and the 2024-29 AI-accelerator CAGR raised to the mid-to-high-50s% [30][31].

## 3. Key risks

1. **Custom ASIC substitution (share shift, not demand loss).** Broadcom's AI revenue hit $10.8B in FQ2-26 (+143% YoY), guided to $16B next quarter and ~$56B for FY26, with >$100B reiterated for FY27 and >$30B of new AI bookings in a single quarter [32][33]. Amazon discloses >$225B of Trainium revenue commitments on a ~$20B custom-silicon run rate [34]; Anthropic contracted up to 1M Google TPUs (>1GW in 2026) [35]. ASIC-based systems reach ~27.8% of 2026 AI-server shipments vs ~69.7% GPU [36]. For TSMC this is customer diversification (all are TSMC customers); the risk is concentrated on NVIDIA's pricing power and on any single-customer capacity bets.
2. **Capex sustainability and financing quality.** Spending is increasingly debt-financed (Meta-Blue Owl's $27B private-credit deal [37]) and partially circular (NVIDIA's OpenAI commitment — since walked back from $100B to ~$30B [38]; NVIDIA/Microsoft stakes in Anthropic tied to compute purchases [39]). OpenAI carries ~$1.4T of compute commitments against ~$20B ARR [40]. Bear evidence: MIT's finding that ~95% of enterprise GenAI pilots show no P&L impact [41], Bain's $800B revenue-shortfall estimate [42], and depreciation-life criticism (Burry) that NVIDIA felt compelled to rebut [43]. Investors punished Meta's April capex raise (-6%) — the market's tolerance is thinning [14].
3. **China is structurally closing.** Beijing barred foreign AI chips from state-funded data centers (Nov 2025) [44]; even after BIS moved H200/MI325X to case-by-case licensing with a 25% revenue share (mid-Jan 2026) [45], Commerce Secretary Lutnick testified that **zero** H200s had been sold into China as of late April 2026 because Beijing blocks purchases [46]. A drafted ~$295B national computing grid would mandate ≥80% domestic technology [47]. Huawei's ramp is real but HBM-gated (CXMT ~2M stacks in 2026 supports only ~250-300k Ascend 910Cs) [48][49] — China will stay compute-short, but that demand is lost to the merchant (and TSMC) ecosystem either way. Tariff risk was largely defused for TSMC: the Jan 2026 Section 232 25% semiconductor tariff carries broad exemptions plus a US-Taiwan framework tied to US fab investment [50].
4. **Deployment lag → digestion risk.** If power/shell buildout keeps trailing silicon shipments (chips already "sitting in inventory" [23]), the industry could face an air pocket in *orders* even with healthy end-demand — the main mechanism by which today's backlog-driven visibility could disappoint.

## 4. What to watch next

- **TSMC Q2 call (mid-July 2026) and NVIDIA Q2 FY27 (late Aug):** first Rubin revenue, whether the ~$91B guide holds, any update to the "$1T through 2027" order book [1][3].
- **CoWoS gap trajectory** toward ~10% by end-2026 and 2027 capacity adds — the signal for when packaging stops rationing demand [17].
- **HBM4 pricing and allocation** (12-hi stacks >$600; SK hynix ~two-thirds of Rubin volume) and whether memory inflation starts eroding accelerator order economics [51].
- **Hyperscaler late-July earnings:** capex language, "capacity-constrained" phrasing, component-cost pass-through [11][13][14].
- **Power milestones:** Meta's ~1GW Prometheus online in 2026 [52], Stargate site progress [27], turbine/transformer backlogs [24][25] — the truest leading indicator of 2027 chip demand.
- **China policy:** any Beijing relent on H200, B30A disposition, finalization of the 80%-domestic grid mandate [46][47].
- **ASIC checkpoints:** Broadcom's $16B FQ3 guide execution (Sept 2026) and external Google TPU placements [32][33].

**Bottom line:** demand is verified as exceeding supply everywhere it can be measured; the binding constraint through 2026 is the HBM-plus-CoWoS silicon complex, with power as the successor constraint already visible; the dominant risks are financing quality and deployment lag, not end-demand — and nearly every risk scenario reallocates rather than removes TSMC wafer demand, except China, which is already largely excluded.

---

**Sources:**
[1] NVIDIA Q1 FY2027 results, May 20, 2026 — nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2027
[2] CNBC, NVIDIA Q1 FY27, May 20, 2026 — cnbc.com/2026/05/20/nvidia-nvda-earnings-report-q1-2027.html
[3] CNBC, GTC 2026 keynote, Mar 16, 2026 — cnbc.com/2026/03/16/nvidia-gtc-2026-ceo-jensen-huang-keynote-blackwell-vera-rubin.html
[4] TrendForce, $500B projection, Oct 29, 2025 — trendforce.com/news/2025/10/29/
[5] TechRadar Pro, Huang supply comments, June 2026 — techradar.com/pro/
[6] NVIDIA Newsroom, Vera Rubin full production, May 31/Jun 1, 2026 — nvidianews.nvidia.com/news/vera-rubin-full-production-agentic-ai-factory
[7] TechTimes, HBM4 all three suppliers, Jun 5, 2026
[8] AMD Q1 2026 results, May 5, 2026 — ir.amd.com (release #1284)
[9] AMD-OpenAI 6GW partnership, Oct 6, 2025 — ir.amd.com (release #1260)
[10] AMD-Meta 6GW partnership, Feb 24, 2026 — amd.com/en/newsroom
[11] CNBC, Microsoft FQ3 2026, Apr 29, 2026 — cnbc.com/2026/04/29/microsoft-msft-q3-earnings-report-2026.html
[12] Tom's Hardware / CNBC, big-4 capex ~$725B, Feb 2026
[13] CNBC + Alphabet 10-Q, Apr 29, 2026 — cnbc.com/2026/04/29/alphabet-googl-q1-2026-earnings.html
[14] Fortune, Meta capex raise, Apr 29, 2026 — fortune.com/2026/04/29/meta-zuckerberg-145-billion-ai-spending-roi/
[15] Introl, GPU cloud price collapse, Dec 2025; Thunder Compute, Jul 2026
[16] Spheron, GPU cloud pricing comparison 2026
[17] TrendForce, CoWoS gap 20%→10%, Jun 15, 2026 — trendforce.com/news/2026/06/15/
[18] TechTimes, TSMC AGM "shortage for years," Jun 5, 2026
[19] TechSpot, SK hynix 2026 sold out, Oct 2025
[20] CNBC, SK hynix Q1 2026, Apr 23, 2026 — cnbc.com/2026/04/23/sk-hynix-earnings-ai-memory-shortage-hbm-demand.html
[21] TrendForce, DRAM contract prices, Jun 1, 2026 — trendforce.com/presscenter/news/20260601-13070.html
[22] TrendForce, HBM share of DRAM wafer starts, Jun 2, 2026
[23] Data Center Dynamics, Nadella Bg2 Pod comments, Nov 2025
[24] pv magazine USA, transformer lead times, May 11, 2026
[25] Utility Dive, GE Vernova 80GW backlog — utilitydive.com/news/ge-vernova-gas-turbine-investor/807662/
[26] Works in Progress, US interconnection queues, 2026
[27] Epoch AI, Stargate site status, 2026
[28] Dataconomy, TSMC N2 booked through 2028 (reported), Mar 31, 2026
[29] DigiTimes, ABF substrate tightening, Dec 2025 / May 2026
[30] TSMC Q4 2025 call coverage (capex $52-56B; AI CAGR raise), Jan 2026 — Futurum Group
[31] CNBC, TSMC Q1 2026, Apr 16, 2026 — cnbc.com/2026/04/16/tsmc-q1-profit-58-percent-ai-chip-demand-record.html
[32] Broadcom FQ2 2026 results, Jun 3, 2026 — prnewswire.com (302790698)
[33] Motley Fool, Broadcom FQ2 2026 transcript, Jun 3, 2026
[34] About Amazon, Jassy on chips business, Q1 2026 earnings
[35] Anthropic, Google TPU expansion, Oct 23, 2025 — anthropic.com/news
[36] TrendForce, 2026 AI server forecast, Jan 20, 2026 — trendforce.com/presscenter/news/20260120-12887.html
[37] Fortune / Meta press release, Hyperion-Blue Owl $27B+$2.5B, Oct 2025
[38] Bloomberg, Huang rules out $100B OpenAI investment, Mar 4, 2026
[39] Microsoft blog, Microsoft-NVIDIA-Anthropic partnerships, Nov 18, 2025
[40] TechCrunch, Altman $1.4T commitments vs $20B ARR, Nov 6, 2025
[41] Fortune, MIT NANDA 95% study, Aug 18, 2025
[42] Bain Global Technology Report, Sept 2025
[43] CNBC, NVIDIA rebuts Burry, Nov 25, 2025
[44] Bloomberg/Reuters, China state-datacenter ban, Nov 5, 2025
[45] BIS press release Jan 13, 2026 + Federal Register Jan 15, 2026 (2026-00789)
[46] SCMP/CNBC, Lutnick Senate testimony, late Apr/May 1, 2026
[47] Bloomberg, China $295B national AI grid, Jun 9, 2026
[48] SemiAnalysis, Huawei Ascend production ramp, Sept 8, 2025
[49] CEIAS, China AI chip supply chain 2026, Jun 11, 2026
[50] White & Case, Section 232 semiconductor tariff, Jan 2026
[51] TrendForce, HBM4 pricing/SK hynix allocation, Jan 28, 2026
[52] NBC4/WCMH, Meta Prometheus ~1GW in 2026