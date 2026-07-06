# Worked example: the live 2026-07 flagship, traced end to end

All numbers below were read directly from `store/chips.merchant-gpu/2026-07-v3.json` and
`registry/indicators.json` on 2026-07-05 (main @ 639c00d). They are a teaching snapshot, not
current state — re-read the newest `store/chips.merchant-gpu/<asOf>-v<N>.json` before citing any
of them as live. Reproduce the dump with:

```powershell
.venv\Scripts\python -c "import json; sc=json.load(open('store/chips.merchant-gpu/2026-07-v3.json', encoding='utf-8')); print(json.dumps({'anchors': sc['demandSupply']['anchors'], 'ratings': {k: v['rating'] for k, v in sc['dimensionRatings'].items()}, 'indices': sc['indices'], 'status': sc['categoryStatus']}, indent=2))"
```

## 1. The indicator registry (2026-07-05 snapshot — 17 indicators)

| Indicator | Dimension | Side | Weight | Scoring | Cadence/Horizon | Unit |
|---|---|---|---|---|---|---|
| apiArr | momentum | demand | 0.20 | yes | quarterly/lagging | USD_B |
| vendorRevenueGuidance | momentum | demand | 0.12 | yes | quarterly/**leading** | USD_B |
| rpoBacklog | momentum | demand | 0.10 | yes | quarterly/**leading** | USD_B |
| D2 | momentum | demand | 0.10 | yes | quarterly/lagging | USD_B |
| grossMargin | unitEconomics | demand | 0.10 | yes | quarterly/lagging | pct |
| market-share-pct | moat | demand | 0.10 | yes | quarterly/coincident | pct_segment_rev |
| releaseCadence | competitiveStructure | demand | 0.10 | yes | quarterly/coincident | releases_per_yr |
| S10 | bottleneck | supply | 0.08 | yes | quarterly/coincident | USD_B |
| leadTimes | bottleneck | supply | 0.08 | yes | weekly/coincident | weeks |
| S9 | competitiveStructure | supply | 0.04 | yes | quarterly/coincident | mixed |
| D6 | — | price | 0.0 | no | daily/coincident | USD_per_gpu_hr |
| gpuSpotPrice | — | price | 0.0 | no | daily/coincident | USD_per_gpu |
| exportControlExposure | strategicRisk | structural | 0.0 | no | quarterly/lagging | — |
| customerConcentration | strategicRisk | structural | 0.0 | no | quarterly/lagging | — |
| designWins | competitiveStructure | structural | 0.0 | no | weekly/**leading** | — |
| perfPerWatt | — | — | — | no | quarterly/lagging | perf_per_W |
| flopsPerDollar | — | — | — | no | quarterly/lagging | flops_per_USD |

Scoring weights sum to **1.02** — nothing normalizes them, and that is a documented reason DMI/SMI
levels carry no fixed scale. The leading+scoring set is only rpoBacklog + vendorRevenueGuidance
(designWins is leading but structural/non-scoring) — the concrete shape of open F60.

## 2. Anchor math (one micro-example)

Suppose the momentum group this cycle is three gated findings on momentum-dimension indicators
(apiArr, D2, rpoBacklog), with demand polarities/magnitudes (+1, 3), (+1, 3), (+1, 2). Momentum's
track is **demand** (`dimensionTracks`), so:

```
anchor(momentum) = ( (+1·3/3) + (+1·3/3) + (+1·2/3) ) / 3 = (1 + 1 + 0.667) / 3 ≈ +0.889
```

The gate then only checks the bound: a Weak/Very weak momentum rating would need anchor < +0.15 →
rejected ("momentum: rating Weak contradicts anchor a=0.89"); Very strong/Strong/Mixed are all
in-bounds and the judge's words + `docs/rating-anchors.md` discriminators decide among them.

## 3. The 2026-07-v3 flagship (asOf 2026-07, monthly grain)

**Anchors (code-computed):**

| Dimension | Anchor | Rating chosen | Bound check |
|---|---|---|---|
| momentum | +0.800 | Very strong | positive rating needs anchor > −0.15 ✓ |
| moat | +0.500 | Mixed | Mixed always allowed ✓ (see F71 note below) |
| competitiveStructure | +0.476 | Mixed | ✓ |
| unitEconomics | +0.111 | Strong | ✓ |
| strategicRisk | −0.067 | Mixed | ✓ |
| bottleneck | −1.000 | Weak | negative rating needs anchor < +0.15 ✓ |

**The F71 residue, visible in this exact scorecard:** the judge originally rated moat **Weak**, but
the +0.50 anchor made Weak illegal (needs anchor < +0.15), forcing Weak→Mixed; the F63 sufficiency
gate then correctly objected that the move vs prior memory rested on only 2 secondary publishers
(<3, no primary). After one rewrite attempt, the run completed under a whole-run `--no-sufficiency`
bypass (docs/fix-backlog.md F71; the shipped moat record itself is defensible — capped medium,
honest rationale). Open F71/F75 territory: see **gate-integrity-campaign** before touching it.

Note the bottleneck anchor: −1.0 on the **supply** track with a "Weak" rating — via the inversion,
this reads "the constraint is cited but not binding for merchant GPUs themselves this cycle", while
the categoryStatus still names `bottleneck` as the binding dimension with constraintLabel
"HBM3E/HBM4 memory supply allocation" (upstream memory, not GPU capacity). Rating word, anchor
sign, and constraint label answer three different questions — do not collapse them.

**Indices (code-computed, frozen formula):**

| Index | DMI | SMI | SDGI | Direction | Contributing findings |
|---|---|---|---|---|---|
| Overall (`demandSupply`, all findings) | +0.7000 | +0.0600 | +0.6400 | demand-led | — |
| Momentum (coincident+lagging) | +0.4533 | +0.0600 | +0.3933 | demand-led | 12 |
| Outlook (leading) | +0.2467 | 0.0000 | +0.2467 | demand-led | 3 |

Divergence: `aligned` (both demand-led), sdgiGap −0.1467. Band words (`bands.py`, applied by
`brief.py` to the OVERALL DMI and SMI): Demand +0.70 → **ACCELERATING** (≥0.30); Supply +0.06 →
**FIRM** (≥0.05). The SDGI gets an interpretation sentence, not a band (±0.05 thresholds,
`report.py`). Those words — not raw numbers, not magnitude adverbs — are what the brief may say
above the fold.

The Outlook column is the F60 story in one row: 3 contributing findings, SMI exactly 0.0, all
leading signal sourced from quarterly filings. Read it as thin coverage.

**One DMI contribution, by hand** (desk-proof-and-analysis-toolkit owns the general recipe): a
single apiArr finding with polarityDemand +1, magnitude 3 contributes
`0.20 × (+1) × 3/3 = +0.200` to DMI — and 0 to SMI if polaritySupply is 0. Only the latest finding
per (entity, indicatorId) bucket counts (F7).

## 4. Thesis book snapshot (2026-07-05)

13 entries: 10 registered, 3 provisional (prepaid-hbm-take-or-pay-locks-in-accelerator-demand,
conditional-china-re-opening-with-a-capped-ceiling, cuda-software-lock-in-sustains-the-moat), one
live pendingChallenge on `amd-credible-second-source` (a reversal recorded but not applied —
awaiting same-direction confirmation or lapse next cycle). Lenses in use: demand 4, supply 1,
competitive 4, risk 4. This is the anti-whipsaw machinery in its normal, healthy state.

## Provenance

Snapshot date 2026-07-05, main @ 639c00d. Source files: `store/chips.merchant-gpu/2026-07-v3.json`,
`registry/indicators.json`, `store/theses/chips.merchant-gpu/book.json`, `gpu_agent/scoring.py`,
`gpu_agent/judgment/briefing.py`, `gpu_agent/gate.py`, `gpu_agent/bands.py`. The registry table,
anchors, ratings, indices, and thesis counts are all volatile — re-run the command at the top and
the SKILL.md provenance commands before quoting them.
