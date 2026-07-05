# Artifact A — Merchant GPU market state (as of 2026-07-05)

# Merchant GPU Market — Executive Digest (May 21 – July 5, 2026)

**Bottom line:** Demand still outruns supply. NVIDIA's Rubin generation entered full production with memory, not customers, as the binding constraint; HBM/DRAM pricing is now the dominant cost driver; and China is effectively a closed market for US GPU vendors, with restrictions tightening from both Washington and Beijing.

## Demand

- **NVIDIA Q1 FY27 (rep. May 20):** revenue **$81.6B (+85% YoY)**, data center **$75.2B (+92%)**; Q2 guided to **$91B ±2%** assuming zero China DC revenue. *(NVIDIA 8-K / press release, May 20, 2026 — sec.gov/Archives/edgar/data/0001045810/000104581026000051/q1fy27pr.htm)*
- Huang reiterated ~**$1T cumulative Blackwell+Rubin order visibility through 2027** at GTC Taipei; cloud GPUs described as sold out. *(Forbes, Jun 1, 2026)*
- Top-4 US hyperscalers are guiding to roughly **$725B combined 2026 capex** per analyst tallies, with GB200/GB300 systems the single largest line item. *(Value Add VC, Jun 11, 2026 — analyst aggregation, medium confidence)*
- **AMD:** Rackspace signed a definitive agreement for an initial **30 MW of MI355X/MI350P** compute (late 2026–2028). *(AMD press release + Rackspace 8-K, Jun 16, 2026)* Oracle's FQ4 report (FY27 capex guided ~$70B) reaffirmed the first public **MI450 supercluster — 50,000 GPUs starting Q3 2026**. *(Yahoo Finance/Motley Fool, ~Jun 26, 2026)*

## Supply and product

- **Vera Rubin entered full production** (GTC Taipei, Jun 1); first customer shipments Q3/fall 2026 with 8 cloud partners. *(NVIDIA newsroom, Jun 1, 2026)*
- **AMD Helios** (72x MI455X rack, up to 2.9 EF FP4) reached market via Supermicro at Computex; first MI355X systems debuted on the June TOP500 (AMD powers 4 of the top 10; China's CPU-based LineShine took No. 1 from El Capitan). *(Supermicro IR, Jun 2; TOP500.org, Jun 23, 2026)*
- Upstream running hot: **TSMC May revenue NT$417B, +30.1% YoY** *(TSMC monthly report, Jun 10)*; **Foxconn record May NT$859B, +39.6%** on AI racks *(DigiTimes, Jun 5)*. The **CoWoS packaging gap is reportedly narrowing from ~20% to ~10%** by end-2026. *(TrendForce, Jun 15, 2026)*

## Pricing and HBM

- Memory is the cost story: conventional **DRAM contract prices +58–63% QoQ in Q2, decelerating to +13–18% in Q3**. *(TrendForce, Jul 3, 2026)*
- All three memory makers **(SK hynix, Samsung, Micron) qualified on HBM4 for Rubin**; SK hynix estimated at **60–70% of allocation**. *(Bloomberg via Investing.com, Jun 5, 2026)* SK hynix briefly overtook Samsung as Korea's most valuable listed company (Jun 22). *(Korea Economic Daily, Jun 22, 2026)*
- **Micron FQ3: $41.5B revenue, $50B Q4 guide; HBM3E+HBM4 sold out through calendar 2027.** *(Micron IR/8-K, Jun 24, 2026)*
- Cost pass-through beginning: Bernstein pegs a Rubin NVL72 rack at **~$9.1M** with HBM4 headed to ~$53/GB *(Wccftech citing Bernstein, ~Jun 20)*; Nebius raised on-demand GPU cloud prices ~30% *(BigGo citing The Information, Jul 4)*; AMD raised client GPU+GDDR kit prices ~10% for July *(TrendForce, Jul 3 — partner-reported)*.

## Export controls and China

- NVIDIA booked **zero China DC revenue** (vs. $4.6B a year ago); Huang says NVIDIA has **"largely conceded" China to Huawei**. *(CNBC, May 21, 2026)* Bernstein sees NVIDIA's China AI-chip share falling ~40%→~8% as Huawei nears ~50%. *(AP via ABC News, Jun 29, 2026)*
- **BIS closed the offshore-subsidiary loophole** (May 31/Jun 1): the AI-chip license requirement now follows the ultimate Chinese/Macau parent regardless of where the buying entity sits (Singapore, Malaysia, UAE). *(Al Jazeera/Reuters, Jun 1, 2026)*
- Beijing escalated in kind: customs **blocked imports of NVIDIA's China-only RTX 5090D V2** (mid-May) *(Semafor, May 22, 2026)*, and on Jun 22 added US firms to its export-control and procurement blacklists *(CNBC, Jun 22, 2026)*. No B30A/Blackwell-for-China approval occurred in the window.

**Watch next:** AMD Advancing AI keynote (Jul 22–23, Helios/MI455X vs. Rubin), NVIDIA Q2 FY27 earnings (late Aug), Q3 Rubin ramp vs. HBM4/CoWoS availability, any US decision on Blackwell-class China SKUs.

---

**Method note for the caller:** produced via the deep-research workflow — 5 parallel search agents (demand, AMD, supply chain, HBM, export controls), then 3 independent adversarial verifiers over the 14 anchor claims; all 14 were confirmed 3/3 against primary sources (SEC filings, company IR, TSMC/TOP500/TrendForce, CNBC/AP/Bloomberg). Items marked "reported/analyst" (hyperscaler capex tally, Bernstein BOM, Nebius hike, AMD kit pricing, HBM4 allocation split) are supply-chain or analyst estimates rather than company-confirmed figures.