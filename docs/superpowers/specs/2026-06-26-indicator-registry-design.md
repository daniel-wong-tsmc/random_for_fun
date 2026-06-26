# Indicator Registry — Category-Agnostic Scoring Backbone (Increment A)

- **Date:** 2026-06-26
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **References:** [`docs/category-agent-guide.md`](../../category-agent-guide.md) §2.2, §4.3 ·
  [`docs/taxonomy.json`](../../taxonomy.json) ·
  [`docs/superpowers/specs/2026-06-19-gpu-category-agent-design.md`](./2026-06-19-gpu-category-agent-design.md) §13.3 (registries)

---

## 1. Context & goal

The brain works for `chips.merchant-gpu`, but it is **silently GPU-shaped**. The
indicator→dimension and indicator→polarity-track bindings are hardcoded in
`gpu_agent/judgment/map.py` (its own comment: *"YAGNI — not yet assignment-driven"*), and the
DMI/SMI weights live in the assignment. The consequences, observed in a live run:

- A CPU agent's or AI-model agent's indicators map to **nothing** — they cannot score.
- Two rated dimensions (`moat`, `unitEconomics`) contribute **exactly 0** to DMI/SMI because their
  metrics (`market-share-pct`, `grossMargin`) carry no weight — a **silent** zero, not a flagged one.
- `dmi_smi_contribution` is a **sum over findings**, so an indicator counts once *per finding*: DMI's
  sign flipped purely on whether 1 vs 3 NVDA-quarter findings were written. The index scaled with
  extraction verbosity, not signal.

**Goal:** make the scoring brain **registry-driven and category-agnostic**, so a new Category Agent
(CPU, AI-model, HBM, neocloud, …) is *pure configuration* — its own metrics, the **same**
sophisticated processing. This is the scalability backbone the rest of the improvement roadmap sits
on.

### Guiding principle (user)
> Each category agent can have its own unique compute metrics, but the **processing and thought
> process must be uniform and sophisticated**.

The registry is exactly this separation: metric *definitions* vary per category (data); the
*machinery* — standardize → weight → map onto the 6 fixed dimensions → roll up → bounded judgment —
is identical for every agent (code).

### Where this sits in the roadmap (decomposition)
- **A — Indicator registry (this spec).** Define-once metric metadata + registry-driven, correct
  aggregation + a validation gate.
- **B — Vintage store + z-score / freshness / ΔSDGI momentum** (later). Consumes registry fields
  `decayLambda`, `readsLevelOrSlope`, `leadMonths`. Unlocks σ-based alert tiers.
- **C — Hard multi-source corroboration + provenance** (later). The ≥2-independent-source rule.

A and B and C each get their own spec → plan → build cycle. B and C both depend on A.

---

## 2. Scope

### In scope
1. **`registry/indicators.json`** — the single authoritative source for metric-and-scoring metadata.
2. **`gpu_agent/registry/`** loader module — `IndicatorSpec` model, `IndicatorRegistry` with
   `resolve(indicatorId, categoryId)`, `validate_against(taxonomy)`, and accessors used by scoring
   and judgment.
3. **Rewire** `judgment/map.py` (delete the hardcoded dicts), `judgment/briefing.py`, and
   `scoring.py` to read the registry instead of hardcoded maps / `assignment.weights`.
4. **Aggregation correctness (Option B):** `dmi_smi_contribution` collapses an indicator's findings
   to **one contribution per indicator** (latest vintage; tie-break highest magnitude) so the index
   stops scaling with finding count. Closes the zero-weight gap.
5. **Registry-validation gate:** every metric an assignment references must resolve to a registered
   indicator whose `dimension` is one of the 6 and whose `category` exists in the taxonomy; a
   dimension-mapped indicator with `weight == 0` fails loudly. Non-scoring metrics are allowed but
   must be **explicitly** marked (`scoring: false`) — no silent omissions.
6. **Slim `taxonomy.json`** to pure structure (layers, category ids+names, the 6 dimensions, scale,
   rollup, layerFlags, schemas). **Lift** `quantMetrics` / `qualMetrics` / `seedMetrics` into the
   registry. Promote taxonomy from a dangling doc to the **contract the registry validates against**.
7. **Re-baseline** the golden fixtures and add a second category's registry entries
   (e.g. a thin `models.frontier-closed` or CPU set) as a **generalization test** — proof that a new
   agent is config-only.

### Out of scope (explicitly)
- Z-scores, 36-month standardization, freshness decay, impulse, ΔSDGI momentum, σ-based alert tiers
  (**Increment B** — the registry only *carries the fields*).
- Hard corroboration / the ≥2-source rule (**Increment C**).
- Entity-level cross-sectional rollup (e.g. NVDA-vs-AMD share dispersion inside one indicator). The
  collapse is per-indicator for now; richer entity-aware aggregation is a noted B refinement.
- The frozen Finding/Scorecard schema, the 6 dimensions, the gate's existing rules — unchanged
  contract. We add a *new* registry-validation gate; we do not alter the Part-7 finding/scorecard gate.

---

## 3. Success criteria (acceptance)

1. `judgment/map.py`'s hardcoded `DIMENSION_MAP` / `DIMENSION_POLARITY` are **gone**; dimension and
   polarity-track for every finding are resolved through the registry.
2. DMI/SMI are computed **per-indicator** (one contribution per indicator); adding a duplicate finding
   for an already-counted indicator does **not** change DMI/SMI. A regression test pins this against
   the old finding-count-scaling behavior.
3. `moat` and `unitEconomics` carry **non-zero** weight from the registry and move DMI/SMI; no
   dimension-mapped indicator silently contributes 0.
4. An assignment referencing an **unregistered** metric, an unknown dimension, or a zero-weight scoring
   indicator **fails the validation gate** with a clear message (tested per failure type).
5. A **second category** scorecard is produced end-to-end with **no code change** — only a new
   assignment + registry entries — demonstrating category-agnosticism.
6. `taxonomy.json` contains no metric lists; every `dimension`/`category` referenced by the registry
   validates against it. Full existing suite green (golden re-baselined; deltas explained in the PR).

---

## 4. The registry

### 4.1 `IndicatorSpec` (one entry)

| Field | Governance | Used by | Notes |
|---|---|---|---|
| `id` | human | all | e.g. `D2`, `market-share-pct`, `grossMargin`, `S9`, `serverCpuShare`, `apiArr` |
| `label` | human | docs | |
| `dimension` | **human (durable)** | judgment, gate | one of the 6, or `null` when `scoring:false` |
| `polarityTrack` | **human (durable)** | briefing anchor | `demand` \| `supply` — which polarity field expresses this indicator's signal (generalizes `DIMENSION_POLARITY`, now per-indicator) |
| `side` | human | scoring filter | `demand`\|`supply`\|`price`\|`structural`; `price`/`structural` do not feed DMI/SMI (guide §3.x) |
| `weight` | **calibrated** | scoring | seed from guide §4.3; backtest-tuned later (Increment B/calibration). Must be > 0 for a scoring indicator |
| `unit` | human | docs/extraction | |
| `kind` | human | extraction | `measured` \| `qualitative` |
| `comparability` | human | extraction | "what it is / isn't comparable to" (from taxonomy `metricSchema`) |
| `scoring` | human | gate | default `true`; `false` = documented narrative-only metric (e.g. `perfPerWatt`), allowed by the gate, contributes nothing, **but visible** |
| `readsLevelOrSlope` | calibrated | **Increment B** | `level`\|`slope`. `D2` reads slope; `market-share-pct` reads level. Carried now, consumed by B |
| `decayLambda` | calibrated | **Increment B** | freshness decay; carried now |
| `leadMonths` | human | docs | informational |

### 4.2 File shape — global definitions + per-category overrides (Option 2)

```json
{
  "version": "1.0",
  "indicators": {
    "market-share-pct": {
      "label": "Market share", "dimension": "moat", "polarityTrack": "demand",
      "side": "demand", "weight": 0.10, "unit": "pct_segment_rev", "kind": "measured",
      "readsLevelOrSlope": "level", "decayLambda": 0.3, "scoring": true,
      "comparability": "revenue share; state segment + period; not unit share"
    },
    "grossMargin": { "dimension": "unitEconomics", "polarityTrack": "demand", "side": "demand",
                     "weight": 0.10, "unit": "pct", "kind": "measured",
                     "readsLevelOrSlope": "level", "decayLambda": 0.3, "scoring": true },
    "D2":  { "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.10,
             "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.4,
             "scoring": true },
    "D6":  { "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.12,
             "readsLevelOrSlope": "slope", "decayLambda": 0.6, "scoring": true },
    "S9":  { "dimension": "competitiveStructure", "polarityTrack": "supply", "side": "supply",
             "weight": 0.04, "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true },
    "S10": { "dimension": "bottleneck", "polarityTrack": "supply", "side": "supply", "weight": 0.08,
             "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true },
    "perfPerWatt":   { "dimension": null, "scoring": false, "kind": "measured", "unit": "perf/W" },
    "flopsPerDollar":{ "dimension": null, "scoring": false, "kind": "measured", "unit": "flops/USD" }
  },
  "overrides": {
    "chips.hbm-memory": { "market-share-pct": { "weight": 0.04 } }
  }
}
```

`resolve(indicatorId, categoryId)` = base `indicators[id]` deep-merged with
`overrides[categoryId][id]` if present. Precedence (low→high): **registry default → category override
→ assignment override** (`assignment.weights[id]` stays as the highest-priority per-run knob for
adhoc runs).

### 4.3 Why per-indicator `polarityTrack` (not per-dimension)
`side` is already per-indicator; making `polarityTrack` per-indicator generalizes the old
per-dimension `DIMENSION_POLARITY` without losing today's behavior (every current indicator in a
dimension shares its track). The briefing anchor for a finding uses **its own indicator's**
`polarityTrack`. A consistency check (warn) flags a dimension whose indicators disagree on track.

---

## 5. The aggregation fix (Option B)

`dmi_smi_contribution(findings, registry, categoryId)`:

1. Drop findings whose indicator is `scoring:false` or whose `side ∈ {price, structural}`.
2. **Group by `indicatorId`**; within each group keep the **latest-vintage** finding
   (`capturedAt` then `observedAt`; tie-break highest `magnitude`). One contribution per indicator.
3. `DMI = Σ_indicator weight · polarityDemand · magnitude/3`;
   `SMI = Σ_indicator weight · polaritySupply · magnitude/3` over the collapsed set.

This makes the index reflect the **current** read per indicator (e.g. D2 collapses 3 quarters to the
latest, +21% QoQ), independent of how many findings were extracted. The **anchor** computation in
`briefing.py` keeps its mean-over-findings behavior (it is gate-consistent and not the bug); only
`dmi_smi` changes its aggregation. Multi-entity dispersion within one indicator is surfaced via the
existing `dispersion` field, with proper entity-aware series deferred to B.

---

## 6. Components & data flow

```
registry/indicators.json ──load──> IndicatorRegistry ──validate_against──> taxonomy.json (structure)
                                          │
   assignment (category, metrics, weight-overrides) ─┐
                                          ▼          ▼
                         [registry-validation gate]  (fail loudly: unregistered / bad dim / zero-weight)
                                          │
 findings ──> briefing.build_briefing(findings, registry, category)  # anchors via registry dim+track
          ──> scoring.dmi_smi_contribution(findings, registry, category)  # per-indicator collapse
          ──> judgment ──> ratings (dimensions from registry) ──> build_scorecard ──> [Part-7 gate] ──> store
```

- **`gpu_agent/registry/indicators.py`** — `IndicatorSpec`, `IndicatorRegistry` (load, resolve,
  validate, accessors). Small, focused, the only module that parses the registry file.
- **`gpu_agent/registry/taxonomy.py`** (or accessor) — loads the slimmed `taxonomy.json` and exposes
  `dimensions: set[str]`, `categories: set[str]` for validation.
- **`judgment/map.py`** — deleted; callers use the registry.
- **`judgment/briefing.py`** — `_polarity` and dimension grouping resolve through the registry.
- **`scoring.py`** — `dmi_smi_contribution` signature gains `(registry, categoryId)`; aggregation per §5.
- **`pipeline.py` / `cli.py`** — load the registry once, run the validation gate before scoring,
  thread `registry` + `categoryId` through. `zscore()` left untouched for B.

---

## 7. Error handling

- **Validation gate → fail the run, don't emit a misleading scorecard.** Unregistered metric, unknown
  dimension/category, or `scoring:true` with `weight == 0` → `RegistryError` listing every offense
  (same "collect all violations" shape as the Part-7 gate).
- **Bend-don't-break stays for data, not config.** A *missing data point* still emits a
  confidence-capped, under-supported dimension (existing behavior). A *malformed registry/assignment*
  is a config error and fails fast — config bugs must be loud.
- **Override merge is total/partial-safe:** an override supplies only the fields it changes; unknown
  override keys are a `RegistryError`.

---

## 8. Testing strategy (TDD-first)

- **Registry unit:** load + schema round-trip; `resolve` applies category override; precedence
  (default < category < assignment); unknown override key rejected; `validate_against` catches
  bad-dimension and unknown-category.
- **Gate unit:** one test per failure type (unregistered metric; dimension not in the 6; zero-weight
  scoring indicator; `scoring:false` metric passes and contributes nothing).
- **Aggregation:** the **regression pin** — N duplicate D2 findings yield the **same** DMI as one
  (proves count-independence); latest-vintage wins; `price`/`structural` excluded;
  `moat`/`unitEconomics` now non-zero.
- **Generalization test:** a second category (e.g. `models.frontier-closed` with `apiArr`,
  `releaseCadence`, or a CPU set) scores end-to-end on recorded fixtures with **no code change** —
  the headline proof of the whole increment.
- **Golden re-baseline:** the `chips.merchant-gpu` golden updates (weights + aggregation changed); the
  PR explains each delta. Full suite green.

---

## 9. Migration (taxonomy.json)

1. Move every category's `quantMetrics` / `qualMetrics` and the top-level `seedMetrics` into
   `registry/indicators.json` (as `indicators` with `scoring` flags; qualitative ones `kind:qualitative`).
2. Leave `taxonomy.json` with: `meta`, `scoringRubric` (the 6 dimensions, scale, rollup, layerFlags),
   `scorecardSchema` / `assignmentSchema` / `entitySchema`, and `layers[].categories[]` reduced to
   `{id, name, seedConstituents}`.
3. Add the cross-check in `validate_against`: registry `dimension ∈ scoringRubric.dimensions`,
   registry/override `category ∈ layers[].categories[].id`.

---

## 10. Open questions

None blocking. Initial `weight` values are calibration **seeds** (guide §4.3 where defined; sensible
defaults for `market-share-pct`/`grossMargin`), explicitly flagged for backtest tuning in Increment B —
not hand-tuned truth.
