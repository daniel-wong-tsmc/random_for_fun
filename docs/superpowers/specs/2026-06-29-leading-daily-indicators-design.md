# Leading + daily indicators (sub-project 4-2) — design

- **Date:** 2026-06-29
- **Status:** Draft for review (the second piece of sub-project 4)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md);
  the human-output target
  [`2026-06-29-human-market-brief-design-target.md`](2026-06-29-human-market-brief-design-target.md);
  charter Part 18 (registries/assignments; discovery lane), Part 21 ("counted once"), Part 22 (source
  inventory / honest sourcing), Part 17 (numbers only from gated findings; price/structural stay out of the
  index). Builds additively on **C** (manifest + top-level-map registry pattern).
- **Depends on:** 4-1 (merged — temporal store/wiki). **Feeds:** 4-3 (the two indices read the horizon tags).

---

## 0. What 4-2 is — and the lane discipline that scopes it

4-2 adds **forward (leading) and daily-cadence indicators** for the **`merchant-gpu` category's own lane**,
and tags **every** registered indicator with two orthogonal axes — **cadence** (`daily | weekly | quarterly`)
and **horizon** (`leading | coincident | lagging`) — as registry DATA. 4-3 reads the horizon tag to split
trailing **Momentum** (lagging+coincident) from forward **Outlook** (leading); the 4-5 per-category brief reads
cadence for per-signal recency.

**The lane discipline (Part 21 "counted once"; the 5-layer cake).** A category agent owns only its own lane.
`merchant-gpu` = the merchant GPU **vendors** (NVIDIA/AMD/Intel): their demand momentum, unit economics,
competitive position *within merchant GPUs*, product lead-times/pricing, and strategic risk. The deep **supply
constraints** (CoWoS, HBM, wafers, networking, power) and broad **demand drivers** (hyperscaler capex, inference,
datacenter buildouts, the ASIC threat) are **owned by sibling / adjacent category agents** — `foundry-packaging`,
`hbm-memory`, `hyperscaler-asic`, `networking-silicon`, the energy layer, the infrastructure/models layers —
and reach `merchant-gpu` only as cited **adjacent-layer context** via the (deferred) Layer rollup. **4-2 does
NOT annex those signals.** The full cross-cutting "GPU market state" brief is a **layer-tier product**, a
separate later arc (charter Part 38 / the design-target §0).

**4-2 is NOT:** the two indices (4-3); the daily gather / scrape cron that *populates* these indicators with
findings, or the discovery engine (4-4); the layer/market brief. 4-2 ships **registry DATA + a small read
accessor + tests** only.

**Locked decisions (from brainstorming):**
- Cadence×horizon live as a **top-level DATA map** in `indicators.json` (the C-3 pattern — `IndicatorSpec` is
  `extra="forbid"` and `indicators.py` is frozen, so never a spec field and never inside an indicator dict).
- Scoring-vs-overlay is **automatic**: the frozen `dmi_smi_contribution` already excludes `side in
  ("price","structural")`, so price/structural indicators are overlay-only (on the board, never in the index).
- The 5 new indicators are strictly **in merchant-gpu's lane**.

---

## 1. The cadence × horizon tagging scheme (DATA)

A new **top-level** key in `registry/indicators.json` (sibling to `indicators`/`overrides`/`sourceInventory`),
keyed by indicator id:

```json
"cadenceHorizon": {
  "market-share-pct":      { "cadence": "quarterly", "horizon": "coincident" },
  "grossMargin":           { "cadence": "quarterly", "horizon": "lagging"    },
  "rpoBacklog":            { "cadence": "quarterly", "horizon": "leading"    }
}
```

The frozen `IndicatorRegistry.load()` reads only `indicators`/`overrides` and **ignores unknown top-level keys**
(verified for `sourceInventory` in C) — so adding `cadenceHorizon` keeps `indicators.py`/`validate.py`
**byte-unchanged**. `cadence ∈ {daily, weekly, quarterly}`; `horizon ∈ {leading, coincident, lagging}`.

**Coverage rule:** every **scoring** indicator (`scoring: true`) MUST have a `cadenceHorizon` entry with valid
values (4-3 routes scoring indicators by horizon; an untagged one would be silently misrouted). Overlay
indicators (`scoring: false`, incl. price/structural) SHOULD also be tagged (the board shows their recency) and
this spec tags all of them, but the hard guard is on scoring indicators.

---

## 2. New in-lane indicators (added to `indicators` in `indicators.json`)

All five are unambiguously the merchant-GPU vendors' own signals (no sibling overlap):

| id | label | dimension | side | scoring | weight | horizon | cadence |
|---|---|---|---|---|---|---|---|
| `rpoBacklog` | Backlog / purchase commitments | momentum | demand | true | 0.10 | leading | quarterly |
| `vendorRevenueGuidance` | Vendor DC-GPU revenue guidance | momentum | demand | true | 0.12 | leading | quarterly |
| `leadTimes` | Merchant-GPU product lead times | bottleneck | supply | true | 0.08 | coincident | weekly |
| `designWins` | Merchant-GPU design wins | competitiveStructure | structural | **false** | 0.0 | leading | weekly |
| `gpuSpotPrice` | Merchant-GPU hardware spot/resale price | *(none)* | **price** | **false** | 0.0 | coincident | daily |

- **Scoring three** (`rpoBacklog`, `vendorRevenueGuidance`, `leadTimes`) flow into DMI/SMI once 4-4 produces
  findings referencing them; 4-3 routes the two `leading` ones to **Outlook**, `leadTimes` (coincident) to
  **Momentum**. `validate_against` requires them to have a taxonomy dimension + non-zero weight — satisfied.
- **`designWins`** is a competitive/structural signal, not demand momentum (a design win reallocates share, it
  doesn't raise category demand). `side="structural"` + `scoring:false` keeps it out of the index (the existing
  `exportControlExposure`/`customerConcentration` pattern); it informs the competitiveStructure judgment + the
  AMD/NVIDIA storylines.
- **`gpuSpotPrice`** is a daily confirmation overlay; `side="price"` auto-excludes it from the index
  (charter Part 17). Distinct from the existing `D6` (cloud *rental* price).
- **No generic "news-event indicator":** arbitrary news belongs on wiki threads (4-4), not the registry.

Each new indicator carries the same fields the existing ones use (`label, dimension, polarityTrack, side,
weight, unit, kind, scoring`, and where apt `readsLevelOrSlope, decayLambda, comparability`). No new
`IndicatorSpec` field is introduced (frozen).

---

## 3. Cadence × horizon tags for the existing 12

| id | dimension / side | horizon | cadence |
|---|---|---|---|
| `market-share-pct` | moat / demand | coincident | quarterly |
| `grossMargin` | unitEconomics / demand | lagging | quarterly |
| `D2` (DC revenue structure) | momentum / demand | lagging | quarterly |
| `D6` (GPU rental price) | momentum / demand | coincident | daily |
| `S9` (alternative supply) | competitiveStructure / supply | coincident | quarterly |
| `S10` (whole-chain inventory) | bottleneck / supply | coincident | quarterly |
| `perfPerWatt` | — (scoring false) | lagging | quarterly |
| `flopsPerDollar` | — (scoring false) | lagging | quarterly |
| `apiArr` (API ARR) | momentum / demand | lagging | quarterly |
| `releaseCadence` | competitiveStructure / demand | coincident | quarterly |
| `exportControlExposure` | strategicRisk / structural | lagging | quarterly |
| `customerConcentration` | strategicRisk / structural | lagging | quarterly |

**Pre-existing cross-lane notes (NOT fixed in 4-2; revisit when sibling agents exist):** `apiArr` (API ARR) is
really a models/apps demand signal, and `D6` (GPU *rental* price) is neocloud/cloud territory — both sit in
`merchant-gpu` today. Tagged as-is here; flagged for the layer-tier arc, not relitigated now.

---

## 4. Wiring — the read accessor + coverage guard (new, additive)

A new module **`gpu_agent/registry/horizon.py`** (frozen `indicators.py`/`validate.py` untouched):

```python
CADENCES = {"daily", "weekly", "quarterly"}
HORIZONS = {"leading", "coincident", "lagging"}

class HorizonError(Exception): ...

class IndicatorHorizons:
    def __init__(self, mapping: dict[str, dict]): ...
    @classmethod
    def load(cls, path) -> "IndicatorHorizons": ...        # reads top-level "cadenceHorizon"
    def get(self, indicator_id) -> dict | None             # {"cadence","horizon"} or None
    def cadence(self, indicator_id) -> str                 # raises HorizonError if untagged/invalid
    def horizon(self, indicator_id) -> str                 # raises HorizonError if untagged/invalid
    def validate_coverage(self, registry) -> None          # every SCORING indicator tagged + valid; else HorizonError
```

`validate_coverage` enforces the §1 coverage rule and that every tag value is in `CADENCES`/`HORIZONS` and every
mapped id is a registered indicator (no orphan tags). This is the seam 4-3 reads (it asks `horizon(id)` to bucket
Momentum vs Outlook). Wiring it now (with a guard test) keeps the tags **real**, not documentation-only.

---

## 5. Source inventory + manifest coverage (reuse C)

**`sourceInventory`** (top-level map in `indicators.json`) entries for the 5 new ids (Part 22 honest sourcing):
- `rpoBacklog`, `vendorRevenueGuidance` → NVIDIA/AMD 10-Q/10-K + earnings-call/IR (primary, free filing).
- `designWins` → company PR + trade press (secondary, free-web).
- `leadTimes` → channel checks / SemiAnalysis (secondary; paywalled portions labeled `estimate`, never scraped)
  + trade press (free-web).
- `gpuSpotPrice` → GPU marketplaces / resale listings (free-web, **scrape-fed**, `estimate`-grade). The scrape
  cron itself is **4-4**; 4-2 only inventories the source.

**Manifest** (`manifests/chips.merchant-gpu.json`): add the 5 new ids to `expectedIndicators` (with dimension +
priority + sourceIds) and the new sources to `expectedSources`, so C's `compute_coverage_gaps` logs them as
gaps until 4-4 feeds them (gaps logged, never silent; paywalled labeled not scraped).

---

## 6. Frozen vs additive (Part 33)

- **Byte-unchanged:** `gpu_agent/registry/indicators.py`, `validate.py`, `gpu_agent/scoring.py` (incl.
  `dmi_smi_contribution`), `gate.py`, `pipeline.py` Part-7 gate, the `Finding`/`Scorecard` schemas, the 6
  dimension names. (Adding registry DATA + a new module touches none of them.)
- **Additive DATA:** `registry/indicators.json` — 5 new indicators, the new top-level `cadenceHorizon` map,
  new `sourceInventory` entries; `manifests/chips.merchant-gpu.json` — new expected indicators/sources.
- **New module:** `gpu_agent/registry/horizon.py` + its tests.

---

## 7. Doctrine

Numbers come only from gated findings — 4-2 defines indicators, it invents no values (the new indicators are
empty until 4-4's gather/scrape produces findings; coverage gaps are logged meanwhile). Price/structural
overlays are auto-excluded from the index. Paywalled sources are inventoried + labeled `estimate`, never
scraped. The lane discipline (Part 21) prevents double-counting sibling-owned signals.

---

## 8. Test strategy (deterministic; the C pattern)

- `tests/test_registry_horizon.py` — `IndicatorHorizons.load` reads the map; `cadence`/`horizon` return correct
  values; untagged/invalid → `HorizonError`; **`validate_coverage` passes for the real registry** (every
  scoring indicator tagged) and **fails loud** on a synthetic untagged scoring indicator and on an orphan tag.
- `tests/test_registry_indicators.py` (extend) — the 5 new indicators `resolve()` and `validate_against` the
  taxonomy passes (scoring ones have dimension+weight; overlay ones are `scoring:false`).
- Seam guard (extend the manifest↔registry test) — every new manifest `indicatorId` resolves in the registry.
- Confirm DMI/SMI on the **existing committed fixtures is unchanged** (new indicators have no findings → zero
  contribution) — guards "adding indicators is inert until 4-4."
- Full suite stays green (current baseline after 4-1 merge: **248 passed, 3 skipped**, plus the new tests).

---

## 9. Out of scope (later pieces / arcs)

- The two indices + the Momentum/Outlook divergence (4-3).
- The daily gather + **scrape cron** that populates these indicators, and the discovery engine (4-4).
- The per-category brief render (4-5); the cross-cutting **layer/market** brief (layer-tier arc, Part 38).
- Sibling-owned signals (CoWoS/HBM/wafer/ASIC/power/capex/inference) — other category agents.

---

## 10. Acceptance (4-2)

1. Five in-lane indicators (`rpoBacklog`, `vendorRevenueGuidance`, `leadTimes`, `designWins`, `gpuSpotPrice`)
   are registered; they `resolve()` and `validate_against` the taxonomy passes; price/structural ones stay out
   of `dmi_smi_contribution`.
2. A top-level `cadenceHorizon` map tags **every** indicator (existing 12 + new 5); `indicators.py`/`validate.py`
   remain byte-unchanged.
3. `gpu_agent/registry/horizon.py` exposes `cadence`/`horizon` accessors and a `validate_coverage` that **passes
   for the real registry** and **fails loud** on a missing/invalid/orphan tag.
4. Source inventory + manifest coverage updated for the 5 new (paywalled labeled `estimate`, scrape-fed source
   inventoried not scraped); coverage gaps computed by C are logged.
5. DMI/SMI on committed fixtures is unchanged (new indicators inert until fed); full suite green; frozen
   contract intact; the merchant-gpu **lane discipline** is honored (no sibling-owned signals added).
