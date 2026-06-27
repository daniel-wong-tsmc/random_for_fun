# Coverage Manifest + Source Inventory — Design

- **Date:** 2026-06-27
- **Status:** Draft (sub-project C spec; binds the C implementation plan)
- **Sub-project:** C of the Output & Coverage Overhaul — see umbrella design
  `docs/superpowers/specs/2026-06-27-output-coverage-decomposition-design.md`
- **Build order:** C is built LAST — after B (six-dimension integrity) and A (executive report) are
  merged into `main`. C rebases onto B's indicator set (which by then includes `strategicRisk`).
- **Charter parts:** Part 22 (data-source reality; source inventory), Part 37 (the gathering swarm),
  Part 18 (assignments / registries; principle #8 bend-don't-break; adding coverage is a DATA edit).

---

## 1. Context and goal

The live `chips.merchant-gpu` run rated only 4 of 6 dimensions — `bottleneck` and `strategicRisk` were
silently absent. One root cause is that the gatherer has no authoritative list of what a cycle is
*expected* to cover: it runs until it goes dry or a cap trips, commits whatever it finds, and the
scorecard quietly omits any dimension that happened not to receive any Findings that run.

Sub-project C closes this gap at the sourcing layer:

1. **A per-category coverage manifest** declares, ahead of time, which indicators (and hence which
   dimensions) plus which source URLs a cycle is *expected* to produce. This is the "expected coverage
   set" that B's `under-supported` state and A's coverage-% line both read from (umbrella §2.3).
2. **A per-metric source inventory** (charter Part 22 fields) is attached to indicators in
   `registry/indicators.json`, documenting *how* each metric is obtained: access method, tier, cost,
   license, and refresh cadence.
3. The **`gather-category` skill** is made manifest-driven: it seeds from the manifest's expected
   sources, sharpens its on-topic filter from the manifest's expected indicators, and — critically —
   logs every not-covered expected item as a **surfaced coverage gap** in `gather-log.json`. A gap is
   never silent.
4. The **assignment** gains a `manifestRef` field pointing at the category's manifest file.

The result: every cycle either covers what it declared it would, or explains publicly why it did not.
B's `under-supported` logic reads that declaration; A renders the gap count. The indices become
trendable because "what was expected" is fixed, not variable run-to-run.

---

## 2. The coverage manifest

### 2.1 Location and naming

Manifest files live at `manifests/<categoryId>.json`, where `categoryId` is the full dotted id used
in `taxonomy.json` and the assignment (e.g. `chips.merchant-gpu`). The directory `manifests/` sits at
the repo root alongside `registry/` and `fixtures/`.

**Why separate from the assignment:** The assignment is the "pick and pull" scope config (Part 18): it
declares *which entities, metrics, budget, depth, explore allowance* the run uses. The manifest is a
different artifact: it declares *what a well-run cycle is expected to cover*. These are read by
different consumers — the assignment is read by the gather coordinator, while the manifest is also read
independently by B's scoring pipeline and A's report renderer. Embedding the manifest in the assignment
would require B and A to parse assignments, creating an unintended coupling. A separate file, referenced
by `manifestRef` in the assignment, keeps concerns cleanly separated. The assignment remains lean; the
manifest remains a first-class artifact.

### 2.2 JSON schema

```jsonc
// manifests/chips.merchant-gpu.json — annotated skeleton
{
  "version": "1.0",
  "categoryId": "chips.merchant-gpu",         // matches taxonomy.json category full id
  "asOf": "2026-06",                           // the cycle this manifest was authored for
  "description": "Expected coverage for the merchant-GPU category (NVDA/AMD/INTC)",

  // expectedIndicators: the indicators a well-run cycle MUST attempt to cover.
  // These are the grounding signals for the 6 dimensions. After B lands, this list
  // includes the strategicRisk indicator B added.
  // priority: required = gap is always surfaced; preferred = gap surfaced but lower severity;
  //           optional = surfaced only in verbose mode.
  "expectedIndicators": [
    {
      "indicatorId": "D2",            // id in registry/indicators.json
      "dimension": "momentum",        // cross-check against registry; must match
      "priority": "required",
      "sourceIds": ["nvda-earnings", "amd-earnings", "intc-earnings"]
    },
    {
      "indicatorId": "D6",
      "dimension": "momentum",
      "priority": "required",
      "sourceIds": ["lambda-gpu-pricing", "coreweave-pricing"]
    },
    {
      "indicatorId": "market-share-pct",
      "dimension": "moat",
      "priority": "required",
      "sourceIds": ["jpmorgan-gpu-note", "trendforce-gpu-tracker"]
    },
    {
      "indicatorId": "grossMargin",
      "dimension": "unitEconomics",
      "priority": "required",
      "sourceIds": ["nvda-earnings", "amd-earnings"]
    },
    {
      "indicatorId": "S9",
      "dimension": "competitiveStructure",
      "priority": "required",
      "sourceIds": ["nvda-earnings", "amd-earnings", "open-web-asic"]
    },
    {
      "indicatorId": "S10",
      "dimension": "bottleneck",
      "priority": "preferred",
      "sourceIds": ["nvda-earnings", "channel-checks"]
    },
    {
      "indicatorId": "strategicRisk",   // added by B; C rebases after B merges
      "dimension": "strategicRisk",
      "priority": "required",
      "sourceIds": ["bis-export-controls", "nvda-10k-risk-factors"]
    }
  ],

  // expectedSources: the specific sources the gather is expected to fetch.
  // Each has a stable id used in coverage-gap references, and the full Part 22 metadata.
  "expectedSources": [
    {
      "id": "nvda-earnings",
      "label": "NVIDIA earnings / 10-Q / investor relations",
      "urlPatterns": ["investor.nvidia.com", "sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=nvda"],
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "quarterly",
      "indicators": ["D2", "grossMargin", "S10", "market-share-pct"]
    },
    {
      "id": "amd-earnings",
      "label": "AMD earnings / 10-Q / investor relations",
      "urlPatterns": ["ir.amd.com", "sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=amd"],
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "quarterly",
      "indicators": ["D2", "grossMargin", "S9"]
    },
    {
      "id": "intc-earnings",
      "label": "Intel earnings / 10-Q / investor relations",
      "urlPatterns": ["intc.com/financials", "sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=intc"],
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "quarterly",
      "indicators": ["D2"]
    },
    {
      "id": "lambda-gpu-pricing",
      "label": "Lambda Labs / open-web GPU rental price trackers",
      "urlPatterns": ["lambdalabs.com/gpu-cloud", "vast.ai/pricing"],
      "accessMethod": "free-web",
      "tier": "secondary",
      "costUsd": 0,
      "license": "public",
      "refresh": "weekly",
      "indicators": ["D6"]
    },
    {
      "id": "trendforce-gpu-tracker",
      "label": "TrendForce GPU market share tracker",
      "urlPatterns": ["trendforce.com"],
      "accessMethod": "licensed-api",
      "tier": "secondary",
      "costUsd": 5000,
      "license": "licensed",
      "refresh": "quarterly",
      "indicators": ["market-share-pct"],
      "paywalledNote": "Subscription required. Until licensed, market-share-pct runs at estimate-grade."
    },
    {
      "id": "bis-export-controls",
      "label": "BIS export control notices / Federal Register",
      "urlPatterns": ["bis.doc.gov", "federalregister.gov/agencies/industry-and-security-bureau"],
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "on-demand",
      "indicators": ["strategicRisk"]
    },
    {
      "id": "nvda-10k-risk-factors",
      "label": "NVIDIA 10-K risk factor section",
      "urlPatterns": ["investor.nvidia.com/annual-reports"],
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "annual",
      "indicators": ["strategicRisk"]
    },
    {
      "id": "open-web-asic",
      "label": "Open-web reporting on hyperscaler ASICs (Google TPU, AWS Trainium, etc.)",
      "urlPatterns": ["blog.google", "aws.amazon.com/machine-learning", "techcrunch.com"],
      "accessMethod": "free-web",
      "tier": "secondary",
      "costUsd": 0,
      "license": "public",
      "refresh": "weekly",
      "indicators": ["S9"]
    }
  ]
}
```

**Field definitions:**

| Field | Type | Meaning |
|---|---|---|
| `version` | string | manifest schema version — bumped when structure changes |
| `categoryId` | string | must match the taxonomy's full category id |
| `asOf` | YYYY-MM | cycle this manifest was authored for; the gather reads it but may run later |
| `expectedIndicators[].indicatorId` | string | id in `registry/indicators.json` |
| `expectedIndicators[].dimension` | string | cross-checked against registry at load time |
| `expectedIndicators[].priority` | enum | `required` \| `preferred` \| `optional` |
| `expectedIndicators[].sourceIds` | string[] | references into `expectedSources[].id` |
| `expectedSources[].id` | string | stable id referenced by expectedIndicators |
| `expectedSources[].urlPatterns` | string[] | domain/path patterns the coordinator matches blobs against |
| `expectedSources[].accessMethod` | enum | `free-web` \| `filing` \| `licensed-api` \| `mcp` \| `manual` |
| `expectedSources[].tier` | enum | `primary` \| `secondary` |
| `expectedSources[].costUsd` | number | annual subscription cost (0 = free) |
| `expectedSources[].license` | enum | `public` \| `licensed` \| `confidential` \| `unknown` |
| `expectedSources[].refresh` | enum | `realtime` \| `daily` \| `weekly` \| `quarterly` \| `annual` \| `on-demand` |
| `expectedSources[].paywalledNote` | string? | human-readable note for paywalled sources |

---

## 3. Per-indicator source inventory (in `registry/indicators.json`)

C adds a `sourceInventory` field to each indicator entry. This is the Part 22 artifact attached to the
metric registry — it documents HOW to get each metric, independent of any category.

### 3.1 The `sourceInventory` field

```jsonc
// Added to each indicator in registry/indicators.json by sub-project C.
// Example for D2 (DC revenue structure):
"D2": {
  "label": "DC revenue structure",
  "dimension": "momentum",
  // ... existing fields unchanged ...
  "sourceInventory": [
    {
      "name": "NVIDIA 10-Q (Data Center segment)",
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "quarterly"
    },
    {
      "name": "AMD 10-Q (Data Center segment)",
      "accessMethod": "filing",
      "tier": "primary",
      "costUsd": 0,
      "license": "public",
      "refresh": "quarterly"
    },
    {
      "name": "Trade press (DigiTimes, Tom's Hardware)",
      "accessMethod": "free-web",
      "tier": "secondary",
      "costUsd": 0,
      "license": "public",
      "refresh": "weekly"
    }
  ]
}
```

The `sourceInventory` array lists known source types for that metric in PRIORITY ORDER (primary first,
then secondary, then licensed/paywalled). The gather uses this as guidance; the manifest's
`expectedSources` are the category-specific instantiations.

The existing `defaultSourceHint` (string array) documented in `taxonomy.json`'s `metricSchema` is
superseded by `sourceInventory`. During C's implementation, `sourceInventory` is added alongside any
existing `defaultSourceHint` field (none currently appear in the actual `indicators.json` — the field
is in the schema doc only, not populated). Code that previously read `defaultSourceHint` (if any)
should fall back gracefully; C's code reads `sourceInventory`.

### 3.2 Source-inventory schema (Pydantic)

```python
# gpu_agent/manifest.py — SourceEntry (also the per-indicator source inventory entry)
class SourceEntry(BaseModel):
    name: str
    accessMethod: Literal["free-web", "filing", "licensed-api", "mcp", "manual"]
    tier: Literal["primary", "secondary"]
    costUsd: float = 0.0
    license: Literal["public", "licensed", "confidential", "unknown"] = "public"
    refresh: Literal["realtime", "daily", "weekly", "quarterly", "annual", "on-demand"]
```

---

## 4. How the gather targets the manifest and logs gaps

### 4.1 Assignment reads the manifest

The assignment file gains one field:

```json
"manifestRef": "manifests/chips.merchant-gpu.json"
```

At the start of a `gather-category` run, the coordinator checks for `manifestRef`. If present, it loads
the manifest. If absent (e.g., a category without a manifest yet), the gather runs exactly as before —
no manifest-driven behavior, no error. This keeps the skill backward-compatible for categories that
pre-date C.

### 4.2 Priority seeding from the manifest

The manifest drives round-1 seed construction in two ways:

**Primary-source seeds (highest priority):** For each `expectedSource` where `accessMethod == "filing"`
or `tier == "primary"` and `costUsd == 0`, the coordinator adds the source's `urlPatterns` as explicit
seed URLs to chase in round 1. These are prepended to the entity×metric slices so they are guaranteed
to be attempted before any cap can clip them.

**Paywalled-source pass-through:** For each `expectedSource` where `accessMethod == "licensed-api"` or
`costUsd > 0` and no license is active (the license field is `"licensed"` but we have no subscription
key), the coordinator does NOT attempt to fetch it. Instead, it immediately creates a coverage-gap
entry with `acquisitionStatus: "paywalled"` and logs the `paywalledNote`. This is the honest-labeling
rule from Part 22 — we inventory it, we surface it, we never fake it.

**Free-web source seeds:** For each `expectedSource` where `accessMethod == "free-web"`, the coordinator
adds a query derived from the source's label + the entity names to the round-1 search queue alongside
the standard entity×metric slices.

### 4.3 On-topic filter sharpening

The existing on-topic filter ("chase a lead only if it bears on the assigned entities/metrics") is
sharpened by the manifest: the set of relevant metric terms includes all `indicatorId`s in
`expectedIndicators`, so the filter is exactly as wide as the manifest declares — no narrower (a lead
that touches a manifest-expected indicator is always on-topic), no wider than the assignment scope.

### 4.4 Coverage-gap detection and logging

After the gather loop finishes (after all rounds or after a cap trips), the coordinator performs a
coverage check:

**Source coverage check:** For each `expectedSource` in the manifest:
- If `acquisitionStatus` is already set to `"paywalled"` (from step 4.2), skip.
- Otherwise: does any blob's URL match at least one of the source's `urlPatterns` (substring match
  against normalized URL)? If yes: covered. If no: create a gap with `acquisitionStatus: "not-covered"`.

**Indicator coverage check:** For each `expectedIndicator` in the manifest:
- Is there at least one blob whose content (or whose source URL) is linked to an expected source that
  lists this indicator? (i.e., `source.id in expectedIndicators[i].sourceIds` AND that source was
  covered.) If yes: covered. If no: create a gap.

**Gap record schema:**
```json
{
  "type": "indicator" | "source",
  "id": "<indicatorId or sourceId>",
  "priority": "required" | "preferred" | "optional",
  "acquisitionStatus": "paywalled" | "not-covered" | "cap-truncated",
  "reason": "human-readable explanation",
  "paywalledNote": "<string if paywalled>"
}
```

**Gap log placement:** All gap records are appended to `gather-log.json` under a top-level
`coverageGaps` array key. This is the file that already carries `rounds`, `documents`,
`primary`, `secondary`, `duplicates`, `dropped`, `skipped`. The `coverageGaps` key is new and
additive — existing consumers of `gather-log.json` that don't read this key are unaffected.

**Severity in logging:**
- A `required` gap is surfaced at warning level in the coordinator's terminal report.
- A `preferred` gap is logged but does not elevate the report severity.
- An `optional` gap is logged only in verbose mode.

The coordinator's final report (step 8 of the existing SKILL.md procedure) is extended to include:
"Coverage gaps: N required, M preferred (see gather-log.json coverageGaps)."

### 4.5 The gap propagates to B's under-supported logic

After C lands, the `pipeline` CLI command gains a `--manifest` flag. When provided, scorecard assembly
uses manifest-expected indicators as the authoritative "should be grounded" set: a dimension is marked
`under-supported` if ALL its expected indicators have no supporting Findings in the assembled scorecard.
The `coverageGaps` from `gather-log.json` are included verbatim in the scorecard's `provenance` block
(or a dedicated `coverageGaps` key on the scorecard — B owns the exact scorecard field; C documents
the gap source).

Until C lands, B uses the simpler rule: a dimension with zero supporting findings is `under-supported`
(umbrella §2.3). C's flag tightens this to the manifest-declared set.

---

## 5. Tiered acquisition and degradation rules

These rules bind the gather coordinator whenever a manifest is present. They restate and operationalize
Part 22's doctrine.

| Source tier / access | Rule |
|---|---|
| `filing` / `primary` / `costUsd == 0` | Always attempted; seed in round 1. A failed fetch = gap with `acquisitionStatus: "not-covered"`. |
| `free-web` / `secondary` | Attempted; on-topic filter applies. A failed or uncovered source = gap with `acquisitionStatus: "not-covered"`. |
| `licensed-api` or `costUsd > 0` (no active license) | Never fetched. Gap created immediately with `acquisitionStatus: "paywalled"`. The metric runs at `estimate`-grade until licensed. |
| `manual` | Never fetched programmatically. Gap created with `acquisitionStatus: "manual-upload-required"` and an explanation. |
| `mcp` | Fetched via MCP tool if available in session; otherwise gap with `acquisitionStatus: "mcp-unavailable"`. |

**Degradation chain (in order, per indicator):**
1. Primary sources (filings, official IR pages) — prefer always.
2. Secondary open-web (trade press, pricing pages) — used if primary is insufficient.
3. Estimate-grade — if a metric only exists behind a paywall we don't license, the scorecard carries
   `kind: "observed"` with `confidence.level: "low"` and `confidence.basis: "no primary source available;
   paywalled trackers not licensed"` — never invented, never faked.
4. Unavailable — if even open-web provides no data for a metric, the Finding is omitted entirely and
   the indicator shows as a coverage gap. The dimension degrades to `under-supported` (B's logic).

**Hard rules that cannot be softened:**
- Paywalled trackers (Gartner, TrendForce, JPR, IDC, Mercury, Dell'Oro) are inventoried + labeled.
  They are NEVER scraped, NEVER circumvented. The `costUsd` and `paywalledNote` fields make the
  licensing decision legible to leadership (Part 22: "which paid feeds are worth licensing is
  leadership's call — we produce the inventory + cost").
- A hard figure for a metric that only exists behind a paywall must NEVER appear in a Finding without
  a sourced receipt. The metric runs at `estimate`-grade or is not rated.
- "Estimate-grade" means: the finding's `confidence.level` is capped at `"low"`, the `kind` is
  `"observed"` (not `"measured"`), and the narrative says explicitly that the primary tracker is not
  licensed.

---

## 6. How B and A consume the manifest

### 6.1 B's under-supported logic (after C lands)

B's scorecard assembly (in the `pipeline` CLI) accepts a `--manifest manifests/<categoryId>.json` flag.
When the flag is present:

- For each dimension, the manifest's `expectedIndicators` filtered to that dimension gives the
  "should be grounded" set.
- A dimension is `under-supported` if at least one of its `required` expected indicators has NO
  supporting Finding in the assembled scorecard.
- A dimension is `grounded` if all its `required` expected indicators have at least one Finding.

This replaces (for manifest-equipped categories) B's initial simpler rule (zero findings = under-
supported). The semantics are sharper: a dimension can have Findings but still be `under-supported` if
a required indicator was not covered (e.g. `market-share-pct` only had estimated data, no Finding
of `kind: "measured"` was emitted, and the gap log shows it was paywalled).

B's interface for reading the manifest: `load_manifest(path) -> CoverageManifest` (defined in
`gpu_agent/manifest.py`, owned by C). B calls this function; C's code, not B's, owns the manifest
model. This is the seam between B and C's code.

### 6.2 A's coverage rendering (after C lands)

A's `report.py` reads the manifest from the assignment's `manifestRef` (if present). It renders a
coverage line in the report:

> Evidence coverage: 5 of 7 expected indicators grounded (2 gaps — see Sources).

A reads:
- `manifest.expectedIndicators` to get the total expected count.
- The scorecard's dimension ratings with `evidenceStatus` (B's field) to count grounded vs.
  under-supported dimensions.
- The scorecard's `coverageGaps` (from the gather-log, passed through by the pipeline) to render
  the gap list with human-readable labels.

A never reads the manifest directly for ratings — it reads the scorecard B produced. The manifest
is used only for the coverage arithmetic (count of expected vs. grounded).

---

## 7. Testing

### 7.1 Code: TDD (required for all new Python)

**Baseline:** 117 passed, 3 skipped. Every commit in C keeps this green and adds new passing tests.

**New test file:** `tests/test_manifest.py`

Tests must cover:
- `CoverageManifest` loads a valid JSON without error.
- `CoverageManifest` rejects a manifest whose `expectedIndicators[].dimension` does not match the
  registered dimension for that indicator (cross-validation against a stub registry).
- `compute_coverage_gaps()` returns an empty list when all expected sources are covered by blobs.
- `compute_coverage_gaps()` returns a gap with `acquisitionStatus: "not-covered"` for a source with
  no matching blob URL.
- `compute_coverage_gaps()` returns a gap with `acquisitionStatus: "paywalled"` for a source with
  `costUsd > 0`.
- `compute_coverage_gaps()` marks a `required` gap and a `preferred` gap at different severity levels.
- `load_manifest()` raises a clear error (not an uncaught Pydantic exception) when the file is missing.
- `load_manifest()` raises a clear error when the JSON fails schema validation.

**No new tests for SKILL.md:** The gather skill is a markdown procedure, not Python. It is validated
by the documented dry-run below.

### 7.2 Skill: documented dry-run (required, instead of pytest)

A dry-run document at `docs/superpowers/dry-runs/2026-06-27-gather-category-manifest-dry-run.md`
walks step-by-step through a simulated execution of the updated `gather-category` skill with
`asg.chips.merchant-gpu.json` (with `manifestRef` added) and `manifests/chips.merchant-gpu.json`.

The dry-run must cover:
1. The coordinator loads the manifest; lists the 7 expected sources.
2. Round-1 seed construction: 3 filing URLs prepended, 2 free-web queries added.
3. TrendForce immediately creates a paywalled gap — no fetch attempted.
4. Rounds 1–2 execute; 2 of the 3 paywalled-free expected sources are covered by blobs.
5. After the loop, the coverage check finds: 1 source uncovered (`intc-earnings` — no 10-Q found
   because cap hit); 1 indicator not covered (`D6` — no GPU rental price blob).
6. `gather-log.json` coverageGaps section is shown in full.
7. The coordinator's report reads: "Coverage gaps: 2 required (D6, intc-earnings), 1 paywalled
   (trendforce-gpu-tracker)."

The dry-run is the spec author's proof that the skill changes are coherent end-to-end.

### 7.3 Schema validation for indicators.json (C's source-inventory additions)

The existing `registry/validate.py` is frozen. A separate new validator script
`gpu_agent/manifest_loader.py` (or incorporated into `gpu_agent/manifest.py`) validates that:
- Each `sourceInventory` entry on an indicator has all required Part 22 fields.
- Any indicator referenced in a manifest's `expectedIndicators` exists in `registry/indicators.json`.
- Any `sourceId` referenced in `expectedIndicators[].sourceIds` has a matching entry in
  `expectedSources`.

This validator is called by the tests and can also be run standalone:
`.venv/Scripts/python -m gpu_agent.manifest validate manifests/chips.merchant-gpu.json`

---

## 8. Seam constraints (binding)

These restate the umbrella §2.2–§2.4 constraints that C must not violate:

- **C does not add or redefine indicators or dimension mappings.** That is B's ownership.
  C adds `sourceInventory` fields only. If a `strategicRisk` indicator does not yet exist in
  `indicators.json` when C's plan executes, C waits for B to merge first (build order: B → A → C).
- **The manifest's `expectedIndicators[].dimension` is a cross-check, not a definition.** If the
  manifest's dimension for an indicator disagrees with the registry, the registry wins and the
  manifest fails validation.
- **`registry/validate.py` is frozen.** C's new validation logic lives in `gpu_agent/manifest.py`
  and `tests/test_manifest.py`, not in `validate.py`.
- **The `Finding` schema, 6 dimension names, rating scale, `gate.py`, `scoring.py`, `pipeline.py`
  gate are frozen.** C does not touch any of these.
- **Gatherers return raw material only.** The manifest-driven seeding and gap logging are done by the
  coordinator, not by gatherers. Gatherers continue to return blobs + leads; the coordinator runs the
  coverage check after the gather loop.
- **Caps are logged, never silent.** If a cap prevents a manifest-expected source from being fetched,
  the gap is logged with `acquisitionStatus: "cap-truncated"`. "The cap hit" is an explanation, not
  an excuse — it is written into the log.
- **Paywalled sources are inventoried and labeled, never scraped or faked.**

---

## 9. Acceptance criteria

The following must all be true for sub-project C to be considered complete:

- `manifests/chips.merchant-gpu.json` exists, validates against the schema (the manifest validator
  passes), and covers all 6 dimensions (via their expected indicators, including `strategicRisk`).
- Every indicator in `registry/indicators.json` has a `sourceInventory` array with at least one entry.
- `fixtures/asg.chips.merchant-gpu.json` has a `manifestRef` field pointing at the manifest.
- A `gather-category` run against `asg.chips.merchant-gpu.json` produces a `gather-log.json` with a
  `coverageGaps` key. Every expected source that was not fetched or is paywalled appears in that array.
  No coverage gap is silent.
- TrendForce appears in the gap log with `acquisitionStatus: "paywalled"` — never fetched,
  never faked.
- `tests/test_manifest.py` passes as part of the full suite; the baseline of 117 passed, 3 skipped
  is maintained (no regressions).
- The documented dry-run covers all 7 steps (§7.2) and is internally consistent.
- B and A can read the manifest via `load_manifest()` and receive a typed `CoverageManifest` object.
- The umbrella acceptance criterion for C (§6): "A coverage manifest + per-metric source inventory
  exist; the gather targets the manifest; not-covered items are logged gaps, never silent; paywalled
  sources are labeled `estimate`/`unavailable`, not faked."
