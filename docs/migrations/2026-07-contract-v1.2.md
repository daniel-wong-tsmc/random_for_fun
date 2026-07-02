# Contract v1.2 migration — 2026-07-02

The one sanctioned frozen-core migration (charter Part 33, user-approved 2026-07-02). It
lands the evidence-integrity gate bundle, headline protection, DMI/SMI entity shadowing fix,
price overlay handling, deterministic anchor tracks, injection hardening, vintage honesty,
impact quality, the tighter anchor band, and Finding.side authority as one versioned event:
`schemaVersion` → **1.2**, golden fixtures regenerated once, shadow-run + replay recorded here.

## Rule changes (one line each, by F-id)

- **F2a** — an `observed` (or `measured`) finding with empty `evidence` is rejected at the gate.
- **F2b** — every `evidence.excerpt` must be a whitespace-folded verbatim substring of the source document, or the draft is dropped.
- **F2c** — every `evidence.url` must equal the source document's own url, or the draft is dropped.
- **F2d** — `evidence.tier` is code-stamped from `doc.tier`; a draft that tries to supply `tier` fails answer validation loudly (`DraftEvidence` forbids extras).
- **F2e** — a finding whose evidence is entirely `secondary` cannot carry `confidence=high` (headline protection at the finding level).
- **F3** — a grounded dimension whose cited findings carry no `primary` evidence gets `dimensionStatus.confidenceCap="medium"` + `note="secondary-only evidence"`, and its rating confidence is capped high→medium.
- **F7** — DMI/SMI bucket per `(entity, indicatorId)`; NVDA and AMD on the same indicator no longer shadow each other (the latest-vintage collapse is now per entity).
- **F8** — price is a display overlay: `D6` flips to `side=price` / `scoring=false`; a static price level (`trend=unknown`) must carry `polarityDemand=polaritySupply=0` and is exempt from the affects-neither-track rule.
- **F9** — the anchor polarity track is defined **per dimension** at the registry level (`dimensionTracks`), read via `DimensionTracks.for_dimension`; anchors are order-independent (no longer the last finding's per-indicator `polarityTrack`).
- **F16** — `build_user_prompt` escapes `</document` inside untrusted content so the document fence cannot be closed from inside (prompt-injection hardening).
- **F17** — vintage honesty: `observedAt` and every `evidence.date` must be ISO `YYYY-MM-DD`; evidence dated after `asOf` (grain-aware compare) is rejected as future-dated.
- **F21** — impact quality: `impact.targets` non-empty and (at extraction) members of the taxonomy; `impact.mechanism` non-empty.
- **F36** — the anchor consistency band tightens `0.5 → 0.15`; the gate message label changes `z=` → `a=`; the dead `zscore` helper is removed.
- **F37** — `Finding.side` is code-stamped from the registry spec at extraction and validated against the registry spec side in the pipeline — the registry is the side authority; a contradiction raises `GateError`.

## The D6 flip

`D6` (GPU rental price) was a scoring momentum/demand indicator (weight 0.12). Under v1.2 it is a
price **overlay**: `dimension=null`, `polarityTrack=null`, `side=price`, `weight=0.0`,
`scoring=false`. It no longer contributes to DMI/SMI or to any dimension anchor — it is a display
signal only. This is the single biggest source of the DMI deltas below for the versions that
carried D6 findings.

## schemaVersion bump

Every newly extracted finding is stamped `schemaVersion="1.2"` (was `1.1`). The replay (below)
writes v1.2-math scorecards as new store versions; the stored 2026-06 findings themselves remain
`1.1` historical records — the replay re-runs MATH, not the gate.

## Would the stored 2026-06 findings pass the v1.2 gate?

No — that is the point of the migration. The most recent cycle, `2026-06-v6` (`asOf=2026-06`),
contains **20** findings whose evidence is dated `2026-07-02` (future-dated vs `asOf` → F17) and
**20** findings whose `side` contradicts the registry spec (`grossMargin` / `market-share-pct` /
`S9` stamped `structural`; → F37). The v1.2 extraction trust boundary would have dropped or
rejected these at capture. The replay deliberately does **not** re-gate history; it recomputes the
indices under v1.2 math so the series stays continuous.

## Shadow run

`scripts/shadow_run_v12.py` recomputes DMI/SMI and anchors two ways over the SAME stored findings:
**old** = a frozen inline copy of the pre-v1.2 algorithm (bucket by `indicatorId` only, latest
vintage, last-finding's `polarityTrack` for anchors, and the pre-v1.2 D6 spec restored since D6 is
the only indicator whose spec changed); **new** = the current package
(`dmi_smi_contribution` per `(entity, indicator)` + `build_briefing` on registry `dimensionTracks`).
No store writes.

| file | old DMI | new DMI | old SMI | new SMI | old anchors | new anchors | delta notes |
|---|---|---|---|---|---|---|---|
| 2026-06-v1.json | +0.0667 | +0.0667 | +0.0000 | +0.0000 | {momentum +0.67} | {momentum +0.67} | dDMI +0.000, dSMI +0.000 |
| 2026-06-v2.json | +0.2200 | +0.3000 | +0.1067 | +0.1600 | {bottleneck +1.00, competitiveStructure +0.53, moat +0.89, momentum +0.33, unitEconomics +0.33} | {bottleneck +1.00, competitiveStructure +0.00, moat +0.89, momentum +1.00, unitEconomics +0.33} | 2 D6 finding(s) dropped from index (price overlay); un-shadowed multi-entity: S9, grossMargin; dDMI +0.080, dSMI +0.053 |
| 2026-06-v3.json | +0.1000 | +0.3667 | +0.0267 | +0.0667 | {competitiveStructure +0.33, moat -0.25, momentum +0.83, unitEconomics +0.44} | {competitiveStructure +0.00, moat -0.25, momentum +0.83, unitEconomics +0.44} | un-shadowed multi-entity: D2, S9, grossMargin, market-share-pct, perfPerWatt; dDMI +0.267, dSMI +0.040 |
| 2026-06-v4.json | +0.3133 | +0.4000 | +0.0267 | +0.0400 | {competitiveStructure +0.36, moat -0.11, momentum +0.67, unitEconomics +0.58} | {competitiveStructure +0.00, moat -0.11, momentum +0.81, unitEconomics +0.58} | 3 D6 finding(s) dropped from index (price overlay); un-shadowed multi-entity: D2, S9, grossMargin, market-share-pct, perfPerWatt; dDMI +0.087, dSMI +0.013 |
| 2026-06-v5.json | +0.1467 | +0.3333 | +0.0267 | +0.0133 | {competitiveStructure +0.31, moat -0.22, momentum +0.74, unitEconomics +0.50} | {competitiveStructure +0.00, moat -0.22, momentum +0.81, unitEconomics +0.50} | 2 D6 finding(s) dropped from index (price overlay); un-shadowed multi-entity: D2, S9, flopsPerDollar, grossMargin, market-share-pct, perfPerWatt; dDMI +0.187, dSMI -0.013 |
| 2026-06-v6.json | +0.3000 | +0.5067 | -0.1067 | -0.0733 | {bottleneck -0.67, competitiveStructure -0.21, moat +0.00, momentum +0.61, strategicRisk -0.13, unitEconomics +0.33} | {bottleneck -0.67, competitiveStructure -0.21, moat +0.00, momentum +0.79, strategicRisk -0.13, unitEconomics +0.33} | 12 D6 finding(s) dropped from index (price overlay); un-shadowed multi-entity: D2, D6, designWins, grossMargin, vendorRevenueGuidance; dDMI +0.207, dSMI +0.033 |

Reading the table: **new DMI is uniformly ≥ old** once entities stop shadowing each other (v3
jumps +0.267 from un-shadowing D2 across intel/amd/nvidia), while **D6-carrying versions lose the
price-overlay contribution**; the `competitiveStructure` anchor collapses to the demand-track value
(`+0.00` where S9's `polarityDemand` is 0) instead of the old order-dependent supply-track reading.

## Replay mapping (2026-06 v1..v6 → v7..v12)

_Added by the Task-9 replay._
