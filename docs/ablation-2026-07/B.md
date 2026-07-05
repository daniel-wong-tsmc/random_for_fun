# Artifact B — Merchant GPU market state (as of 2026-07-05)

## Monthly market-state brief (July 2026 flagship)

```
===============================================================================================
CATEGORY REPORT: chips.merchant-gpu  |  Cycle: 2026-07  |  2026-07-05T13:36:32.525588+00:00
===============================================================================================
 Evidence: median 2026-06-24 · oldest 2026-01-15 · 36% older than 6 weeks
 Confidence: vote agreement high (3 votes) — agreement between raters, not evidence freshness

STATE OF THE MARKET
  Strong, improving — Demand, pricing, and vendor margins all run strong, so the one lever that caps how much merchant GPU ships is memory: Micron has sold HBM3E and HBM4 out through 2027 with order books into 2028 and no catch-up in sight.
  Demand: ACCELERATING = (was ACCELERATING)
  Supply: FIRM = (was FIRM)
  Gap: Demand outrunning supply — shortage pressure forming
  NOW (Momentum): demand positive ▲ / supply positive ▲    NEXT (Outlook): demand positive ▲ / supply flat =
  BINDING CONSTRAINT: HBM3E/HBM4 memory supply allocation

WHAT MOVED SINCE LAST RUN  (vs 2026-07)
  (no material moves vs 2026-07 — nothing new cleared the materiality bar)

THE CALLS
  ● AMD credible second source   CHALLENGED — pending confirmation ⚠, strengthened ▲  (high, 3 cycles)
      AMD converts its Instinct roadmap into material datacenter share.  (1 source)
      breaks if: AMD Data Center revenue per DC revenue structure grows below 20% YoY with no new named hyperscaler deployment for 2 consecutive quarters, or Instinct Market share stalls below 6%.
  ● Export control exposure   INTACT, strengthened ▲  (high, 1 cycles)
      Export-control policy materially constrains addressable merchant-GPU demand.  (3 sources)
      breaks if: Commerce removes H200 China case-by-case licensing and the 25% tariff and NVIDIA books over $2B China Data Center compute revenue per Export-control / China-revenue exposure for 2 consecutive quarters.
  ● NVDA demand durability   INTACT, reaffirmed =  (high, 5 cycles)
      Datacenter GPU demand continues to outrun NVIDIA's ability to serve it.  (3 sources)
      breaks if: Backlog / purchase commitments stops growing while Merchant-GPU product lead times fall below 26 weeks for 2 consecutive quarters as Data Center revenue keeps rising.
  ● Supply constraint binding   INTACT, strengthened ▲  (high, 4 cycles)
      Advanced packaging + HBM — not wafers or demand — cap realizable merchant-GPU revenue.  (2 sources)
      breaks if: CoWoS Merchant-GPU product lead times fall below 26 weeks and HBM per Whole-chain inventory returns to available supply for 2 consecutive quarters while demand stays positive.
  ● Vendor-financed demand circularity   INTACT, strengthened ▲  (high, 1 cycles)
      NVIDIA's own revenue-sharing and credit-support financing increasingly underwrites its accelerator demand, coupling reported demand strength to NVIDIA-extended credit and adding circularity risk to buildout durability.  (1 source)
      breaks if: NVIDIA's 10-Q shows customer financing or notes receivable rising for 2 consecutive quarters, or a named financed neocloud customer fails to convert its financed commitment to cash revenue within 1 quarter.
  ● Customer concentration risk   INTACT, reaffirmed =  (medium, 3 cycles)
      NVIDIA's data-center revenue is increasingly concentrated in a few direct customers, raising demand-durability risk if any single hyperscaler slows orders or shifts to in-house silicon.  (1 source)
      breaks if: NVIDIA top-3 direct-customer concentration falls below 40% of total revenue for 2 consecutive quarters per Customer & supplier concentration disclosure.
  ● Pricing power persistence   INTACT, reaffirmed =  (medium, 5 cycles)
      GPU rental/spot price levels hold up despite added supply.  (3 sources)
      breaks if: GPU rental price H100 median falls below $2.50 per GPU-hour for 2 consecutive quarters, or B200 rental declines at least 15% at two or more providers within one quarter.
  ● Cheaper inference pulls in demand   INTACT, reaffirmed =  (low, 2 cycles)
      NVIDIA's each-generation drop in cost per token pulls more inference workloads onto its GPUs and widens the market it can serve.  (1 source)
      breaks if: NVIDIA cost per token fails to improve for 2 consecutive product cycles, or Data Center revenue per DC revenue structure growth turns negative for 2 consecutive quarters.
  ● Custom ASIC substitution   INTACT, reaffirmed =  (low, 2 cycles)
      Hyperscaler custom silicon meaningfully displaces merchant-GPU demand growth.  (2 sources)
      breaks if: NVIDIA Data Center revenue per DC revenue structure grows above 20% YoY for 2 consecutive quarters while GPUs hold above 50% of hyperscaler build-out per Market share.
  ● Networking attach as systems moat   INTACT, reaffirmed =  (low, 3 cycles)
      NVIDIA now leads the data-center Ethernet switch market and sells that networking bundled with its GPUs, deepening a full-system moat that raises switching costs versus standalone accelerators and custom chips. NVIDIA took the top revenue spot in data-center Ethernet switching in Q1 2026 by pairing Spectrum-X and Quantum with Blackwell and GB300, and its NVLink systems cut cost per token, but no finding compares networking growth against compute growth, so the sharper claim that networking scales faster than compute is not supported.  (1 source)
      breaks if: NVIDIA networking revenue grows slower than Data Center compute revenue for 2 consecutive quarters, or networking falls below 15% of Data Center revenue per Market share.
  ● Conditional China re-opening with a capped ceiling   INTACT, reaffirmed =  (low, 1 cycles)  (early — not yet corroborated)
      U.S. regulators now allow case-by-case China sales of H200 and MI325X-class chips, but a 25% tariff, security conditions, and a volume cap keep any China revenue recovery small.  (3 sources)
      breaks if: NVIDIA books over $2B China Data Center compute revenue per Export-control / China-revenue exposure for 2 consecutive quarters despite the tariff and volume cap.
  ● CUDA software lock-in sustains the moat   INTACT, not yet judged  (low, 0 cycles)  (early — not yet corroborated)
      The difficulty of running existing AI software on non-Nvidia chips keeps customers on Nvidia even when rivals cut hardware prices.  (sources in history)
      breaks if: A funded compatibility layer or a rival software stack reaches parity such that two or more named hyperscalers move production inference off Nvidia within 2 consecutive quarters.
  ● Prepaid HBM take-or-pay locks in accelerator demand   INTACT, reaffirmed =  (low, 1 cycles)  (early — not yet corroborated)
      Non-cancelable multi-year HBM contracts backed by billions in customer deposits lock a large share of future accelerator demand into place and reduce the chance that today's buildout is speculative.  (1 source)
      breaks if: Micron or its memory peers report cancellations or renegotiations of these take-or-pay agreements, or Backlog / purchase commitments tied to the deposits falls for 2 consecutive quarters.

WHY (drivers -> constraints)
  Pulling demand:
    • Advanced packaging and memory output cap how many GPUs Nvidia can ship while orders and rent-back financing keep buyers lined up.  (NVDA demand durability)  (3 sources)
    • Tight supply keeps rental prices for Nvidia GPUs elevated even as new capacity comes online.  (Pricing power persistence)  (3 sources)
  Capping supply:
    • Foundry packaging and stacked-memory output, not silicon wafers or order books, set the ceiling on how many accelerators can be built and sold.  (Supply constraint binding)  (2 sources)
  Contested:
    • Named hyperscaler wins and 57% data-center revenue growth show AMD is taking a growing slice of accelerator spending.  (AMD credible second source — CHALLENGED ⚠)  (1 source)
    • Case-by-case licensing paired with a tariff, security terms, and heavy enforcement against diversion keeps the legal China channel small.  (Conditional China re-opening with a capped ceiling — early — not yet corroborated)  (3 sources)
    • As open-source compatibility layers lose funding and rival chips still hit software limits, buyers stay on Nvidia to avoid rewriting their software stacks.  (CUDA software lock-in sustains the moat — early — not yet corroborated)  (sources in history)
    • Hyperscalers and Chinese firms build their own or domestic accelerators for some workloads, but this adds to total AI silicon demand rather than cutting Nvidia GPU orders.  (Custom ASIC substitution — low conviction)  (2 sources)
    • Nvidia sells its switching and interconnect bundled with its GPUs, so buyers adopt the whole system and face higher costs to switch away.  (Networking attach as systems moat — low conviction)  (1 source)
    • Customers prepay billions on non-cancelable multi-year memory supply, so a large share of future accelerator output is already committed.  (Prepaid HBM take-or-pay locks in accelerator demand — early — not yet corroborated)  (1 source)

DEMAND | SUPPLY
  DEMAND
    DC revenue structure      +strong ▲  [⚠ one source]
    Gross margin              neutral ▲  [⚠ one source]
    Market share              +moderate ▲  [⚠ one source]
    Model release cadence     neutral ▲  [⚠ one source]
    Backlog / purchase commitments  +strong ▲  [leading, ⚠ one source]
    Vendor DC-GPU revenue guidance  +strong ▲  [leading, ⚠ one source]
  SUPPLY
    Whole-chain inventory     −strong ▲  [⚠ one source]
    Alternative supply        +strong ▲  [⚠ one source]
    Merchant-GPU product lead times  −strong ▲  [⚠ one source]

STORYLINES (tracked over time)
  ESTABLISHED
    (none tracked yet)
  EARLY (not yet corroborated)
    • AMD   →   (last updated 2026-07)  ·
    • NVDA   →   (last updated 2026-07-02)  ·
    • market   →   (last updated 2026-07-02)  ·
    • multi   →   (last updated 2026-07)  ·
    • nvidia   →   (last updated 2026-07-05)  ·

TRUST & COVERAGE (caveat)
  the index level varies run to run until longer history accumulates — read direction, not level
  Evidence: 28 findings — 7 evidence items from company filing / official post, 21 from press / analyst report

──────────────────────────── APPENDIX ────────────────────────────

OVERALL CATEGORY STATUS
  Status:     Strong  ↑ improving
  Bottleneck: bottleneck
  Reason:     see State of the Market above

DIMENSION RATINGS  (Δ vs prior cycle: 2026-07 (prior))
  momentum                Very strong   ↑ improving     medium    grounded  Δ: = same
  unitEconomics           Strong        → steady        high      grounded  Δ: = same
  competitiveStructure    Mixed         ↑ improving     high      grounded  Δ: = same
  moat                    Mixed         → steady        medium    grounded  Δ: ↓ worsened
  bottleneck              Weak          ↓ worsening     medium    grounded  Δ: = same
  strategicRisk           Mixed         ↓ worsening     high      grounded  Δ: = same

  Coverage: 6/6 dimensions grounded; 0 under-supported

Raw indices (DMI/SMI/SDGI):
    DMI 0.700  Δ −0.033  (was ACCELERATING)
    SMI 0.060  Δ −0.047  (was FIRM)
    SDGI 0.640  Δ +0.013  (was ACCELERATING)

PRICE TRACK  (overlay — displayed, never blended into DMI/SMI)
  D6 [lambda.ai] 6.69 USD_per_gpu_hr   Δ vs prior: +0.00
  D6 [runpod.io] 3.29 USD_per_gpu_hr   Δ vs prior: +0.00
  gpuSpotPrice [ebay.com] 799 USD_per_card   Δ vs prior: +0.00
  PMI: +0.00 =   (3 matched series)

ENTITY PANEL
  amd  (10 findings)
    Demand signal: +moderate   Supply signal: +slight
    Key signals:
      [demand/measured]  AMD Q1 2026 Data Center segment revenue was $5.8 billion, up 57% year over year and about 7% sequent...
      [structural/observed]  AMD Instinct won broad deployment: OpenAI named AMD a core strategic compute partner starting with M...
      [demand/observed]  AMD MI450 is sampling in Q1 2026 with production shipments expected H2 2026, MI400 (CDNA 5) was deta...
  NVDA  (5 findings)
    Demand signal: +moderate   Supply signal: neutral
    Key signals:
      [demand/observed]  NVIDIA is launching a new revenue-sharing and credit-support business model that lets AI clouds proc...
      [demand/observed]  NVIDIA became the revenue leader in the global data center Ethernet switch market for the first time...
      [structural/observed]  Anthropic's Claude models are now generally available in Microsoft Foundry, running in production on...
  multi  (5 findings)
    Demand signal: +strong   Supply signal: −moderate
    Key signals:
      [demand/measured]  Micron has signed 16 non-cancelable five-year take-or-pay agreements backed by more than $22 billion...
      [supply/observed]  Micron says HBM shipment growth is capped by supply, not end demand, and does not yet see when indus...
      [supply/observed]  Micron says DRAM and NAND supply-demand conditions will remain tight beyond calendar 2027 driven by ...
  nvidia  (4 findings)
    Demand signal: neutral   Supply signal: +moderate
    Key signals:
      [demand/measured]  NVIDIA Q1 fiscal 2027 gross margins were 74.9% GAAP and 75.0% non-GAAP, up 14.4 points year-over-yea...
      [structural/observed]  NVIDIA recorded no Data Center Hopper shipments to China in Q1 fiscal 2027 versus $4.6 billion a yea...
      [structural/observed]  NVIDIA is offering fast-growing startups compute access in exchange for a share of future revenue, w...
  AMD  (2 findings)
    Demand signal: +moderate   Supply signal: +moderate
    Key signals:
      [supply/observed]  Cantor Fitzgerald raised its AMD price target to $700 from $500 (maintaining Overweight), citing AMD...
      [structural/hypothesis]  AMD's MI450/Helios customer engagement may be strengthening, per same-week secondary coverage that i...
  market  (2 findings)
    Demand signal: +moderate   Supply signal: +moderate
    Key signals:
      [demand/observed]  Server supply-chain players report an AI infrastructure order boom spilling into 2H26, with demand s...
      [supply/observed]  Next-generation accelerators — NVIDIA Vera Rubin, AMD Helios (MI400-series), AWS Trainium 3 and Goog...

EVIDENCE QUALITY  (per dimension)
  momentum                  5 findings  (primary/secondary evidence: 0/5)  [grounded]
  unitEconomics             3 findings  (primary/secondary evidence: 2/1)  [grounded]
  competitiveStructure      7 findings  (primary/secondary evidence: 1/6)  [grounded]
  moat                      2 findings  (primary/secondary evidence: 0/2)  [grounded]
  bottleneck                2 findings  (primary/secondary evidence: 0/2)  [grounded]
  strategicRisk             5 findings  (primary/secondary evidence: 4/1)  [grounded]
  (unattributed)            4 findings  (primary/secondary evidence: 0/4)

  Total: 28 findings  (primary/secondary evidence: 7/21)

SOURCES  (20 unique; primary first, then by date descending)
  [primary]     s201.q4cdn.com                  2026-05-27   NVIDIA SEC Form 10-Q
  [primary]     nvidianews.nvidia.com           2026-05-20   NVIDIA Q1 FY2027 financial results
  [primary]     ir.amd.com                      2026-05-06   AMD SEC Form 10-Q
  [primary]     ir.amd.com                      2026-05-05   AMD Q1 2026 financial results
  [primary]     www.bis.gov                     2026-01-15   U.S. Dept of Commerce, BIS press release
  [secondary]   www.runpod.io                   2026-07-05   RunPod NVIDIA B200 spec guide
  [secondary]   www.runpod.io                   2026-07-05   RunPod pricing
  [secondary]   lambda.ai                       2026-07-02   Lambda (lambda.ai)
  [secondary]   www.cnbc.com                    2026-07-02   CNBC
  [secondary]   www.ebay.com                    2026-07-02   eBay (via web search aggregation)
  [secondary]   blogs.nvidia.com                2026-07-01   NVIDIA Blog / Newsroom
  [secondary]   www.digitimes.com               2026-07-01   Digitimes
  [secondary]   www.digitimes.com               2026-06-30   Digitimes
  [secondary]   nvidianews.nvidia.com           2026-06-29   NVIDIA Newsroom
  [secondary]   www.investing.com               2026-06-29   Investing.com
  [secondary]   finance.yahoo.com               2026-06-24   Micron fiscal Q3 2026 earnings call via Yahoo Finance
  [secondary]   www.investing.com               2026-06-24   Micron Q3 FY2026 slides via Investing.com
  [secondary]   www.spheron.network             2026-06-10   Spheron Blog - GPU Cloud News 2026 (release cadence + lead t
  [secondary]   www.stocktitan.net              2026-05-05   AMD Q1 2026 financial results press release (Form 8-K)
  [secondary]   www.amd.com                     2026-01-15   AMD Blogs - Instinct MI350 Series / Advancing AI (design win

COVERAGE / SKIP GAPS
  (No orphan source references detected)
  All 6 dimensions grounded; no coverage gaps this cycle.

CITATION MAP
  blogs-nvidia-com-817f7ea6-1  secondary  2026-07-01  NVIDIA Blog / Newsroom
  finance-yahoo-com-ea29a8bf-2026-07-1  secondary  2026-06-24  Micron fiscal Q3 2026 earnings call via Yahoo Finance
  finance-yahoo-com-ea29a8bf-2026-07-2  secondary  2026-06-24  Micron fiscal Q3 2026 earnings call via Yahoo Finance
  ir-amd-com-c9dc9d6e-2026-07-1  primary  2026-05-06  AMD SEC Form 10-Q
  ir-amd-com-c9dc9d6e-2026-07-2  primary  2026-05-06  AMD SEC Form 10-Q
  ir-amd-com-f416295d-2026-07-2  primary  2026-05-05  AMD Q1 2026 financial results
  ir-amd-com-f416295d-2026-07-4  primary  2026-05-05  AMD Q1 2026 financial results
  lambda-ai-845323fc-1  secondary  2026-07-02  Lambda (lambda.ai)
  nvidianews-nvidia-com-2de12e3b-1  secondary  2026-06-29  NVIDIA Newsroom
  nvidianews-nvidia-com-7b7a02ff-2026-07-2  primary  2026-05-20  NVIDIA Q1 FY2027 financial results
  s201-q4cdn-com-f9f138ac-2026-07-2  primary  2026-05-27  NVIDIA SEC Form 10-Q
  www-amd-com-49475e6c-2026-07-1  secondary  2026-01-15  AMD Blogs - Instinct MI350 Series / Advancing AI (design win
  www-amd-com-49475e6c-2026-07-2  secondary  2026-01-15  AMD Blogs - Instinct MI350 Series / Advancing AI (design win
  www-bis-gov-dbeede91-2026-07-1  primary  2026-01-15  U.S. Dept of Commerce, BIS press release
  www-cnbc-com-d1364ee3-2026-07-1  secondary  2026-07-02  CNBC
  www-digitimes-com-8764779e-1  secondary  2026-07-01  Digitimes
  www-digitimes-com-f88ca4e6-1  secondary  2026-06-30  Digitimes
  www-digitimes-com-f88ca4e6-2  secondary  2026-06-30  Digitimes
  www-ebay-com-fe5361e5-1  secondary  2026-07-02  eBay (via web search aggregation)
  www-investing-com-09606ac9-2026-07-1  secondary  2026-06-24  Micron Q3 FY2026 slides via Investing.com
  www-investing-com-f24cdca0-1  secondary  2026-06-29  Investing.com
  www-investing-com-f24cdca0-2  secondary  2026-06-29  Investing.com
  www-runpod-io-59ae0a2f-2026-07-1  secondary  2026-07-05  RunPod NVIDIA B200 spec guide
  www-runpod-io-bdb62dfd-2026-07-1  secondary  2026-07-05  RunPod pricing
  www-spheron-network-e5a0032c-2026-07-2  secondary  2026-06-10  Spheron Blog - GPU Cloud News 2026 (release cadence + lead t
  www-stocktitan-net-fe36e810-2026-07-1  secondary  2026-05-05  AMD Q1 2026 financial results press release (Form 8-K)
  www-stocktitan-net-fe36e810-2026-07-2  secondary  2026-05-05  AMD Q1 2026 financial results press release (Form 8-K)
  www-stocktitan-net-fe36e810-2026-07-3  secondary  2026-05-05  AMD Q1 2026 financial results press release (Form 8-K)
```

## Daily update (2026-07-05)

```
==================================================================================================
CATEGORY REPORT: chips.merchant-gpu  |  Cycle: 2026-07-05  |  2026-07-05T13:33:57.025619+00:00
==================================================================================================
 Evidence: median 2026-06-30 · oldest 2026-03-20 · 11% older than 6 weeks
 Confidence: vote agreement medium (3 votes) — agreement between raters, not evidence freshness

WHAT MOVED SINCE LAST RUN  (vs 2026-07-03)
  = MOVED  nvidia — no-state (n/a)  (6 sources), press / analyst report  (early — not yet corroborated)

STATE OF THE MARKET
  Strong, worsening — Durable, widening demand keeps the position Strong: Nvidia's vendor-financing program now underwrites roughly 210,000 GPUs and rent-back guarantees keep orders flowing. The binding constraint has shifted from customers' custom-silicon push to export-control enforcement, as a U.S. indictment plus Taiwan's Supermicro raids over about $2.5 billion of diverted chips, carried by three publishers including a primary filing, widen the ceiling on China revenue and pull the direction to worsening.
  Demand: FLAT ▼ (was FIRM)
  Supply: FLAT ▼ (was FIRM)
  Gap: Demand outrunning supply — shortage pressure forming
  NOW (Momentum): demand negative ▼ / supply negative ▼    NEXT (Outlook): demand positive ▲ / supply flat =
  ⚠ DIVERGENCE: 
  BINDING CONSTRAINT: China export-control enforcement

THE CALLS
  ● AMD credible second source   CHALLENGED — pending confirmation ⚠, strengthened ▲  (high, 3 cycles)
      AMD converts its Instinct roadmap into material datacenter share.  (1 source)
      breaks if: AMD Data Center revenue per DC revenue structure grows below 20% YoY with no new named hyperscaler deployment for 2 consecutive quarters, or Instinct Market share stalls below 6%.
  ● Export control exposure   INTACT, strengthened ▲  (high, 1 cycles)
      Export-control policy materially constrains addressable merchant-GPU demand.  (3 sources, incl. company filing / official post)
      breaks if: Commerce removes H200 China case-by-case licensing and the 25% tariff and NVIDIA books over $2B China Data Center compute revenue per Export-control / China-revenue exposure for 2 consecutive quarters.
  ● NVDA demand durability   INTACT, reaffirmed =  (high, 5 cycles)
      Datacenter GPU demand continues to outrun NVIDIA's ability to serve it.  (3 sources)
      breaks if: Backlog / purchase commitments stops growing while Merchant-GPU product lead times fall below 26 weeks for 2 consecutive quarters as Data Center revenue keeps rising.
  ● Supply constraint binding   INTACT, strengthened ▲  (high, 4 cycles)
      Advanced packaging + HBM — not wafers or demand — cap realizable merchant-GPU revenue.  (2 sources)
      breaks if: CoWoS Merchant-GPU product lead times fall below 26 weeks and HBM per Whole-chain inventory returns to available supply for 2 consecutive quarters while demand stays positive.
  ● Vendor-financed demand circularity   INTACT, strengthened ▲  (high, 1 cycles)
      NVIDIA's own revenue-sharing and credit-support financing increasingly underwrites its accelerator demand, coupling reported demand strength to NVIDIA-extended credit and adding circularity risk to buildout durability.  (1 source)
      breaks if: NVIDIA's 10-Q shows customer financing or notes receivable rising for 2 consecutive quarters, or a named financed neocloud customer fails to convert its financed commitment to cash revenue within 1 quarter.
  ● Customer concentration risk   INTACT, reaffirmed =  (medium, 3 cycles)
      NVIDIA's data-center revenue is increasingly concentrated in a few direct customers, raising demand-durability risk if any single hyperscaler slows orders or shifts to in-house silicon.  (1 source)
      breaks if: NVIDIA top-3 direct-customer concentration falls below 40% of total revenue for 2 consecutive quarters per Customer & supplier concentration disclosure.
  ● Pricing power persistence   INTACT, reaffirmed =  (medium, 5 cycles)
      GPU rental/spot price levels hold up despite added supply.  (3 sources)
      breaks if: GPU rental price H100 median falls below $2.50 per GPU-hour for 2 consecutive quarters, or B200 rental declines at least 15% at two or more providers within one quarter.
  ● Cheaper inference pulls in demand   INTACT, reaffirmed =  (low, 2 cycles)
      NVIDIA's each-generation drop in cost per token pulls more inference workloads onto its GPUs and widens the market it can serve.  (1 source)
      breaks if: NVIDIA cost per token fails to improve for 2 consecutive product cycles, or Data Center revenue per DC revenue structure growth turns negative for 2 consecutive quarters.
  ● Custom ASIC substitution   INTACT, reaffirmed =  (low, 2 cycles)
      Hyperscaler custom silicon meaningfully displaces merchant-GPU demand growth.  (2 sources)
      breaks if: NVIDIA Data Center revenue per DC revenue structure grows above 20% YoY for 2 consecutive quarters while GPUs hold above 50% of hyperscaler build-out per Market share.
  ● Networking attach as systems moat   INTACT, reaffirmed =  (low, 3 cycles)
      NVIDIA now leads the data-center Ethernet switch market and sells that networking bundled with its GPUs, deepening a full-system moat that raises switching costs versus standalone accelerators and custom chips. NVIDIA took the top revenue spot in data-center Ethernet switching in Q1 2026 by pairing Spectrum-X and Quantum with Blackwell and GB300, and its NVLink systems cut cost per token, but no finding compares networking growth against compute growth, so the sharper claim that networking scales faster than compute is not supported.  (1 source)
      breaks if: NVIDIA networking revenue grows slower than Data Center compute revenue for 2 consecutive quarters, or networking falls below 15% of Data Center revenue per Market share.
  ● Conditional China re-opening with a capped ceiling   INTACT, reaffirmed =  (low, 1 cycles)  (early — not yet corroborated)
      U.S. regulators now allow case-by-case China sales of H200 and MI325X-class chips, but a 25% tariff, security conditions, and a volume cap keep any China revenue recovery small.  (3 sources, incl. company filing / official post)
      breaks if: NVIDIA books over $2B China Data Center compute revenue per Export-control / China-revenue exposure for 2 consecutive quarters despite the tariff and volume cap.
  ● CUDA software lock-in sustains the moat   INTACT, not yet judged  (low, 0 cycles)  (early — not yet corroborated)
      The difficulty of running existing AI software on non-Nvidia chips keeps customers on Nvidia even when rivals cut hardware prices.  (sources in history)
      breaks if: A funded compatibility layer or a rival software stack reaches parity such that two or more named hyperscalers move production inference off Nvidia within 2 consecutive quarters.
  ● Prepaid HBM take-or-pay locks in accelerator demand   INTACT, reaffirmed =  (low, 1 cycles)  (early — not yet corroborated)
      Non-cancelable multi-year HBM contracts backed by billions in customer deposits lock a large share of future accelerator demand into place and reduce the chance that today's buildout is speculative.  (1 source)
      breaks if: Micron or its memory peers report cancellations or renegotiations of these take-or-pay agreements, or Backlog / purchase commitments tied to the deposits falls for 2 consecutive quarters.

WHY (drivers -> constraints)
  Pulling demand:
    • Advanced packaging and memory output cap how many GPUs Nvidia can ship while orders and rent-back financing keep buyers lined up.  (NVDA demand durability)  (3 sources)
    • Tight supply keeps rental prices for Nvidia GPUs elevated even as new capacity comes online.  (Pricing power persistence)  (3 sources)
  Capping supply:
    • Foundry packaging and stacked-memory output, not silicon wafers or order books, set the ceiling on how many accelerators can be built and sold.  (Supply constraint binding)  (2 sources)
  Contested:
    • Named hyperscaler wins and 57% data-center revenue growth show AMD is taking a growing slice of accelerator spending.  (AMD credible second source — CHALLENGED ⚠)  (1 source)
    • Case-by-case licensing paired with a tariff, security terms, and heavy enforcement against diversion keeps the legal China channel small.  (Conditional China re-opening with a capped ceiling — early — not yet corroborated)  (3 sources)
    • As open-source compatibility layers lose funding and rival chips still hit software limits, buyers stay on Nvidia to avoid rewriting their software stacks.  (CUDA software lock-in sustains the moat — early — not yet corroborated)  (sources in history)
    • Hyperscalers and Chinese firms build their own or domestic accelerators for some workloads, but this adds to total AI silicon demand rather than cutting Nvidia GPU orders.  (Custom ASIC substitution — low conviction)  (2 sources)
    • Nvidia sells its switching and interconnect bundled with its GPUs, so buyers adopt the whole system and face higher costs to switch away.  (Networking attach as systems moat — low conviction)  (1 source)
    • Customers prepay billions on non-cancelable multi-year memory supply, so a large share of future accelerator output is already committed.  (Prepaid HBM take-or-pay locks in accelerator demand — early — not yet corroborated)  (1 source)

DEMAND | SUPPLY
  DEMAND
    Backlog / purchase commitments  +strong ▲  [leading, ⚠ one source]
  SUPPLY
    Alternative supply        +strong ▲  [⚠ one source]
    Merchant-GPU product lead times  −strong ▲  [⚠ one source]

STORYLINES (tracked over time)
  ESTABLISHED
    (none tracked yet)
  EARLY (not yet corroborated)
    • AMD   →   (last updated 2026-07)  ·
    • NVDA   →   (last updated 2026-07-02)  ·
    • market   →   (last updated 2026-07-02)  ·
    • multi   →   (last updated 2026-07)  ·
    • nvidia   →   (last updated 2026-07-05)  ·

TRUST & COVERAGE (caveat)
  the index level varies run to run until longer history accumulates — read direction, not level
  Evidence: 10 findings — 2 evidence items from company filing / official post, 16 from press / analyst report
  Thin evidence: 2 of 6 dimensions (detail in appendix)

──────────────────────────── APPENDIX ────────────────────────────

OVERALL CATEGORY STATUS
  Status:     Strong  ↓ worsening
  Bottleneck: strategicRisk
  Reason:     see State of the Market above

DIMENSION RATINGS  (Δ vs prior cycle: 2026-07-03 (prior))
  momentum                Strong        ↑ improving     medium    grounded  Δ: = same
  unitEconomics           —/under-supported  (findings: 0; confidence capped at low; no findings mapped to unitEconomics this cycle)  Δ: absent in prior too
  competitiveStructure    Mixed         ↓ worsening     medium    grounded  Δ: ↓ worsened
  moat                    —/under-supported  (findings: 0; confidence capped at low; no findings mapped to moat this cycle)  Δ: was present in prior cycle
  bottleneck              Mixed         ↓ worsening     medium    grounded  Δ: ↓ worsened
  strategicRisk           Weak          ↓ worsening     high      grounded  Δ: new this cycle

  Coverage: 4/6 dimensions grounded; 2 under-supported

Raw indices (DMI/SMI/SDGI):
    DMI 0.040  Δ −0.093  (was FIRM)
    SMI -0.027  Δ −0.173  (was FIRM)
    SDGI 0.067  Δ +0.080  (was FLAT)

PRICE TRACK
  2 price series captured; day-over-day change needs two matched cycles

ENTITY PANEL
  nvidia  (10 findings)
    Demand signal: −slight   Supply signal: −slight
    Key signals:
      [demand/observed]  Nvidia has scaled a CFO-approved vendor-financing programme that helps smaller cloud providers buy i...
      [supply/observed]  Meituan's 1.6-trillion-parameter LongCat-2.0 was trained on roughly 50,000 Chinese domestic accelera...
      [supply/observed]  DigiTimes reports AI demand in 2026 is broadening beyond GPUs into ASICs, networking, PMICs and peri...

EVIDENCE QUALITY  (per dimension)
  momentum                  1 finding   (primary/secondary evidence: 0/2)  [grounded]
  unitEconomics            0 findings  ——  [under-supported]
  competitiveStructure      2 findings  (primary/secondary evidence: 0/4)  [grounded]
  moat                     0 findings  ——  [under-supported]
  bottleneck                2 findings  (primary/secondary evidence: 0/4)  [grounded]
  strategicRisk             3 findings  (primary/secondary evidence: 2/3)  [grounded]
  (unattributed)            2 findings  (primary/secondary evidence: 0/3)

  Total: 10 findings  (primary/secondary evidence: 2/16)

SOURCES  (10 unique; primary first, then by date descending)
  [primary]     www.sec.gov                     2026-03-20   Super Micro Computer, Inc. (SEC Form 8-K)
  [secondary]   lambda.ai                       2026-07-05   Lambda (Lambda GPU Cloud)
  [secondary]   startupfortune.com              2026-07-05   Startup Fortune
  [secondary]   www.coreweave.com               2026-07-05   CoreWeave
  [secondary]   finance.yahoo.com               2026-06-30   Yahoo Finance (Bloomberg syndication)
  [secondary]   tech.yahoo.com                  2026-06-30   Yahoo Tech (BeInCrypto syndication)
  [secondary]   www.digitimes.com               2026-06-30   DigiTimes
  [secondary]   www.tomshardware.com            2026-06-30   Tom's Hardware
  [secondary]   vosen.github.io                 2026-06-29   ZLUDA project blog (vosen.github.io)
  [secondary]   www.tomshardware.com            2026-06-29   Tom's Hardware

COVERAGE / SKIP GAPS
  unitEconomics           — 0 findings this cycle; dimension under-supported
  moat                    — 0 findings this cycle; dimension under-supported
  (No orphan source references detected)

CITATION MAP
  finance-yahoo-com-f1703d5e-2026-07-05-1  secondary  2026-06-30  Yahoo Finance (Bloomberg syndication)
  lambda-ai-845323fc-2026-07-05-1  secondary  2026-07-05  Lambda (Lambda GPU Cloud)
  startupfortune-com-6857e872-2026-07-05-1  secondary  2026-07-05  Startup Fortune
  startupfortune-com-6857e872-2026-07-05-1  secondary  2026-07-05  Startup Fortune
  tech-yahoo-com-71aaa132-2026-07-05-1  secondary  2026-06-30  Yahoo Tech (BeInCrypto syndication)
  tech-yahoo-com-71aaa132-2026-07-05-1  secondary  2026-06-30  Yahoo Tech (BeInCrypto syndication)
  vosen-github-io-96638c47-2026-07-05-1  secondary  2026-06-29  ZLUDA project blog (vosen.github.io)
  vosen-github-io-96638c47-2026-07-05-1  secondary  2026-06-29  ZLUDA project blog (vosen.github.io)
  www-coreweave-com-eb7fcb71-2026-07-05-1  secondary  2026-07-05  CoreWeave
  www-coreweave-com-eb7fcb71-2026-07-05-1  secondary  2026-07-05  CoreWeave
  www-digitimes-com-e48a6e49-2026-07-05-1  secondary  2026-06-30  DigiTimes
  www-digitimes-com-e48a6e49-2026-07-05-1  secondary  2026-06-30  DigiTimes
  www-sec-gov-d3c91348-2026-07-05-1  primary  2026-03-20  Super Micro Computer, Inc. (SEC Form 8-K)
  www-sec-gov-d3c91348-2026-07-05-1  primary  2026-03-20  Super Micro Computer, Inc. (SEC Form 8-K)
  www-tomshardware-com-0169805b-2026-07-05-1  secondary  2026-06-30  Tom's Hardware
  www-tomshardware-com-0169805b-2026-07-05-1  secondary  2026-06-30  Tom's Hardware
  www-tomshardware-com-df64dd8f-2026-07-05-1  secondary  2026-06-29  Tom's Hardware
  www-tomshardware-com-df64dd8f-2026-07-05-1  secondary  2026-06-29  Tom's Hardware
```
