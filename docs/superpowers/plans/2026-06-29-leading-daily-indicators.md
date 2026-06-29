# Leading + daily indicators (sub-project 4-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add five forward/daily-cadence indicators for `merchant-gpu`'s own lane, tag **every** registered indicator with a cadence × horizon axis as registry DATA, and ship a small read accessor (`registry/horizon.py`) that 4-3 will use to split Momentum from Outlook — all additive, with the frozen contract byte-unchanged.

**Architecture:** Three additive layers. (1) Five new indicators are added to the `indicators` map in `registry/indicators.json`; the frozen `dmi_smi_contribution` already excludes `side in ("price","structural")` and non-scoring, so the two overlay indicators are automatically out of the index. (2) A new **top-level** `cadenceHorizon` map (sibling to `indicators`/`overrides`/`sourceInventory`) tags all 17 indicators; the frozen `IndicatorRegistry.load()` reads only `indicators`/`overrides` and ignores unknown top-level keys, so `indicators.py`/`validate.py` stay byte-unchanged. A new module `gpu_agent/registry/horizon.py` reads that map and enforces coverage. (3) Source-inventory + manifest coverage for the five new ids reuse the existing C models.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), stdlib `json`/`pathlib`, pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py` (incl. `dmi_smi_contribution`), `gpu_agent/registry/indicators.py`, `gpu_agent/registry/validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names (`momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`), the rating scale, `pipeline.py`'s Part-7 gate, the `JsonStore`/`FindingStore` class bodies. **Additive only** (Part 33): registry DATA (`indicators.json` — new indicators + the top-level `cadenceHorizon` map + new `sourceInventory` entries), the manifest (`manifests/chips.merchant-gpu.json`), and the NEW module `gpu_agent/registry/horizon.py`.
- **C-3 lesson:** `IndicatorSpec` is `extra="forbid"`. Per-indicator metadata (cadenceHorizon) is a **top-level map** keyed by indicator id — never inside an indicator dict, never a new `IndicatorSpec` field. New indicators use only the existing `IndicatorSpec` fields (`label, dimension, polarityTrack, side, weight, unit, kind, comparability, scoring, readsLevelOrSlope, decayLambda, leadMonths`).
- **Lane discipline (Part 21 "counted once"):** the five new indicators are strictly merchant-GPU vendor signals (NVIDIA/AMD/Intel). No sibling-owned signals (CoWoS/HBM/wafer/ASIC/power/capex/inference).
- **Doctrine:** 4-2 defines indicators; it invents no values (they are inert with zero findings until 4-4 feeds them). Paywalled sources are inventoried + labeled, never scraped. Coverage gaps are logged, never silent.
- **The full suite stays green after every task.** Baseline: **248 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file branch base for the guard:** `559abd0` (current `main`, the branch point). The `git diff --stat 559abd0 -- <frozen files>` guard in Task 3 must print nothing.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `registry/indicators.json` | Indicator DATA + top-level metadata maps | Modify: +5 indicators, +`cadenceHorizon` map, +5 `sourceInventory` entries |
| `gpu_agent/registry/horizon.py` | Read accessor + coverage guard for the cadence×horizon tags | Create |
| `manifests/chips.merchant-gpu.json` | Expected-coverage declaration | Modify: +5 expectedIndicators, +new expectedSources |
| `tests/test_registry_indicators.py` | Registry resolution / taxonomy validation | Extend |
| `tests/test_scoring.py` | DMI/SMI scoring-vs-overlay behavior | Extend |
| `tests/test_registry_horizon.py` | The new accessor + coverage guard | Create |
| `tests/test_manifest.py` | Manifest↔registry seam + coverage gaps + source inventory | Extend |

---

### Task 1: Five new in-lane indicators (DATA) + classification tests

**Files:**
- Modify: `registry/indicators.json` (add 5 entries to the `indicators` object)
- Test: `tests/test_registry_indicators.py` (extend)
- Test: `tests/test_scoring.py` (extend)

**Interfaces:**
- Consumes: `IndicatorRegistry.load`, `.resolve`, `.validate_against` (frozen `gpu_agent/registry/indicators.py`); `dmi_smi_contribution` (frozen `gpu_agent/scoring.py`); `Finding` schema; `Taxonomy.load` (`gpu_agent/registry/structure.py`).
- Produces (registry DATA — new indicator ids other tasks rely on): `rpoBacklog`, `vendorRevenueGuidance`, `leadTimes` (scoring), `designWins` (side `structural`, scoring false), `gpuSpotPrice` (side `price`, scoring false).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_registry_indicators.py`:

```python
def test_new_in_lane_indicators_resolve():
    reg = IndicatorRegistry.load(REG)
    for ind in ("rpoBacklog", "vendorRevenueGuidance", "leadTimes", "designWins", "gpuSpotPrice"):
        spec = reg.resolve(ind, "chips.merchant-gpu")
        assert isinstance(spec, IndicatorSpec)
        assert spec.id == ind


def test_new_scoring_indicators_have_dimension_and_nonzero_weight():
    reg = IndicatorRegistry.load(REG)
    expected = {
        "rpoBacklog": "momentum",
        "vendorRevenueGuidance": "momentum",
        "leadTimes": "bottleneck",
    }
    for ind, dim in expected.items():
        spec = reg.resolve(ind, "chips.merchant-gpu")
        assert spec.scoring is True
        assert spec.dimension == dim
        assert spec.weight > 0.0


def test_new_overlay_indicators_are_non_scoring():
    reg = IndicatorRegistry.load(REG)
    dw = reg.resolve("designWins", "chips.merchant-gpu")
    assert dw.scoring is False
    assert dw.side == "structural"
    assert dw.dimension == "competitiveStructure"
    sp = reg.resolve("gpuSpotPrice", "chips.merchant-gpu")
    assert sp.scoring is False
    assert sp.side == "price"


def test_new_indicators_pass_validate_against_taxonomy():
    from gpu_agent.registry.structure import Taxonomy
    reg = IndicatorRegistry.load(REG)
    tax = Taxonomy.load(pathlib.Path("docs/taxonomy.json"))
    reg.validate_against(tax)  # must not raise (overlay indicators are skipped)
```

Append to `tests/test_scoring.py`:

```python
def test_new_overlay_indicators_excluded_from_dmi_smi():
    reg = IndicatorRegistry.load("registry/indicators.json")
    # designWins is structural; gpuSpotPrice is price — both auto-excluded.
    findings = [_f("designWins", 1, 0, 3), _f("gpuSpotPrice", 1, 0, 3)]
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu")
    assert dmi == 0.0 and smi == 0.0


def test_new_scoring_indicators_contribute_to_dmi_smi():
    reg = IndicatorRegistry.load("registry/indicators.json")
    # rpoBacklog (demand) + leadTimes (supply) both flow into the index.
    findings = [_f("rpoBacklog", 1, 0, 3), _f("leadTimes", 0, -1, 3)]
    weights = {"rpoBacklog": 0.10, "leadTimes": 0.08}
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu", weights)
    assert math.isclose(dmi, 0.10 * 1 * 1.0)   # rpoBacklog demand contribution
    assert math.isclose(smi, 0.08 * -1 * 1.0)  # leadTimes supply contribution
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_registry_indicators.py tests/test_scoring.py -q`
Expected: FAIL — `RegistryError: unregistered indicator: rpoBacklog` (the new indicators are not in the registry yet).

- [ ] **Step 3: Add the five indicators**

In `registry/indicators.json`, inside the `"indicators"` object, after the `"customerConcentration"` entry (add a comma after that entry's closing `}`), insert:

```json
    "rpoBacklog": { "label": "Backlog / purchase commitments", "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.10, "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.3, "scoring": true, "comparability": "remaining performance obligations / purchase commitments; vendor backlog as a forward demand signal" },
    "vendorRevenueGuidance": { "label": "Vendor DC-GPU revenue guidance", "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.12, "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.4, "scoring": true, "comparability": "next-period data-center / AI revenue guidance from the vendor; forward demand slope" },
    "leadTimes": { "label": "Merchant-GPU product lead times", "dimension": "bottleneck", "polarityTrack": "supply", "side": "supply", "weight": 0.08, "unit": "weeks", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true, "comparability": "quoted channel lead time in weeks; longer = tighter supply (negative polaritySupply)" },
    "designWins": { "label": "Merchant-GPU design wins", "dimension": "competitiveStructure", "polarityTrack": "demand", "side": "structural", "weight": 0.0, "kind": "qualitative", "scoring": false, "comparability": "design-win announcements reallocate share between vendors; structural competitive overlay, not a category-demand input" },
    "gpuSpotPrice": { "label": "Merchant-GPU hardware spot/resale price", "dimension": null, "polarityTrack": "demand", "side": "price", "weight": 0.0, "unit": "USD_per_gpu", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.6, "scoring": false, "comparability": "secondary-market hardware price; daily confirmation overlay, distinct from D6 (cloud rental); price side auto-excluded from the index" }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_registry_indicators.py tests/test_scoring.py -q`
Expected: PASS (existing + 6 new).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 254 passed, 3 skipped (248 baseline + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add registry/indicators.json tests/test_registry_indicators.py tests/test_scoring.py && git commit -m "feat(4-2): five in-lane leading/daily indicators (rpoBacklog, vendorRevenueGuidance, leadTimes, designWins, gpuSpotPrice)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `cadenceHorizon` map (DATA) + `registry/horizon.py` accessor

**Files:**
- Modify: `registry/indicators.json` (add the top-level `cadenceHorizon` map for all 17 indicators)
- Create: `gpu_agent/registry/horizon.py`
- Test: `tests/test_registry_horizon.py`

**Interfaces:**
- Consumes: `IndicatorRegistry` (frozen `gpu_agent/registry/indicators.py` — uses `registry.indicators` dict + `registry.resolve`).
- Produces:
  - module constants `CADENCES = {"daily","weekly","quarterly"}`, `HORIZONS = {"leading","coincident","lagging"}`
  - `class HorizonError(Exception)`
  - `class IndicatorHorizons` with `__init__(self, mapping: dict[str, dict])`, classmethod `load(cls, path) -> IndicatorHorizons` (reads top-level `cadenceHorizon`), `get(self, indicator_id) -> dict | None`, `cadence(self, indicator_id) -> str` (raises `HorizonError` if untagged/invalid), `horizon(self, indicator_id) -> str` (same), `validate_coverage(self, registry) -> None` (raises `HorizonError` if any scoring indicator is untagged/invalid or any tag is an orphan).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_registry_horizon.py`:

```python
import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import (
    IndicatorHorizons, HorizonError, CADENCES, HORIZONS,
)

REG = pathlib.Path("registry/indicators.json")


def test_load_reads_cadence_horizon_map():
    h = IndicatorHorizons.load(REG)
    assert h.get("rpoBacklog") == {"cadence": "quarterly", "horizon": "leading"}


def test_cadence_and_horizon_return_values():
    h = IndicatorHorizons.load(REG)
    assert h.cadence("gpuSpotPrice") == "daily"
    assert h.horizon("leadTimes") == "coincident"
    assert h.horizon("vendorRevenueGuidance") == "leading"


def test_get_returns_none_for_untagged():
    h = IndicatorHorizons.load(REG)
    assert h.get("does-not-exist") is None


def test_cadence_untagged_raises():
    h = IndicatorHorizons.load(REG)
    with pytest.raises(HorizonError):
        h.cadence("does-not-exist")


def test_invalid_cadence_raises():
    h = IndicatorHorizons({"x": {"cadence": "hourly", "horizon": "leading"}})
    with pytest.raises(HorizonError):
        h.cadence("x")


def test_invalid_horizon_raises():
    h = IndicatorHorizons({"x": {"cadence": "daily", "horizon": "sideways"}})
    with pytest.raises(HorizonError):
        h.horizon("x")


def test_validate_coverage_passes_for_real_registry():
    reg = IndicatorRegistry.load(REG)
    h = IndicatorHorizons.load(REG)
    h.validate_coverage(reg)  # must not raise


def test_validate_coverage_fails_on_untagged_scoring_indicator():
    reg = IndicatorRegistry({"foo": {"dimension": "momentum", "weight": 0.1, "scoring": True}})
    h = IndicatorHorizons({})  # foo is a scoring indicator with no tag
    with pytest.raises(HorizonError):
        h.validate_coverage(reg)


def test_validate_coverage_fails_on_orphan_tag():
    reg = IndicatorRegistry({"foo": {"dimension": "momentum", "weight": 0.1, "scoring": True}})
    h = IndicatorHorizons({
        "foo": {"cadence": "quarterly", "horizon": "leading"},
        "ghost": {"cadence": "daily", "horizon": "leading"},  # not a registered indicator
    })
    with pytest.raises(HorizonError):
        h.validate_coverage(reg)


def test_all_real_indicators_tagged_with_valid_values():
    reg = IndicatorRegistry.load(REG)
    h = IndicatorHorizons.load(REG)
    for ind_id in reg.indicators:
        tag = h.get(ind_id)
        assert tag is not None, f"{ind_id} is untagged"
        assert tag["cadence"] in CADENCES
        assert tag["horizon"] in HORIZONS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_registry_horizon.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.registry.horizon'`.

- [ ] **Step 3: Create the accessor module**

Create `gpu_agent/registry/horizon.py`:

```python
from __future__ import annotations
import json
import pathlib
from typing import Optional

CADENCES = {"daily", "weekly", "quarterly"}
HORIZONS = {"leading", "coincident", "lagging"}


class HorizonError(Exception):
    """Raised when a cadence/horizon tag is missing, invalid, or orphaned (fail loud)."""


class IndicatorHorizons:
    """Read accessor for the top-level `cadenceHorizon` map in indicators.json.

    The frozen IndicatorRegistry.load() ignores this top-level key; this class is
    the seam 4-3 reads to bucket Momentum (lagging+coincident) vs Outlook (leading).
    """

    def __init__(self, mapping: dict[str, dict]):
        self.mapping = mapping

    @classmethod
    def load(cls, path) -> "IndicatorHorizons":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(data.get("cadenceHorizon", {}))

    def get(self, indicator_id: str) -> Optional[dict]:
        return self.mapping.get(indicator_id)

    def _valid_tag(self, indicator_id: str) -> dict:
        tag = self.mapping.get(indicator_id)
        if tag is None:
            raise HorizonError(f"indicator '{indicator_id}' has no cadenceHorizon tag")
        if tag.get("cadence") not in CADENCES:
            raise HorizonError(
                f"indicator '{indicator_id}' has invalid cadence: {tag.get('cadence')!r}")
        if tag.get("horizon") not in HORIZONS:
            raise HorizonError(
                f"indicator '{indicator_id}' has invalid horizon: {tag.get('horizon')!r}")
        return tag

    def cadence(self, indicator_id: str) -> str:
        return self._valid_tag(indicator_id)["cadence"]

    def horizon(self, indicator_id: str) -> str:
        return self._valid_tag(indicator_id)["horizon"]

    def validate_coverage(self, registry) -> None:
        """Fail loud unless every SCORING indicator is tagged with valid values and
        every tag refers to a registered indicator (no orphans)."""
        violations: list[str] = []
        for ind_id in self.mapping:
            if ind_id not in registry.indicators:
                violations.append(f"cadenceHorizon tags unregistered indicator '{ind_id}'")
        for ind_id in registry.indicators:
            spec = registry.resolve(ind_id)
            if not spec.scoring:
                continue
            tag = self.mapping.get(ind_id)
            if tag is None:
                violations.append(f"scoring indicator '{ind_id}' is untagged")
                continue
            if tag.get("cadence") not in CADENCES:
                violations.append(
                    f"scoring indicator '{ind_id}' has invalid cadence: {tag.get('cadence')!r}")
            if tag.get("horizon") not in HORIZONS:
                violations.append(
                    f"scoring indicator '{ind_id}' has invalid horizon: {tag.get('horizon')!r}")
        if violations:
            raise HorizonError("; ".join(violations))
```

- [ ] **Step 4: Add the `cadenceHorizon` map to the registry DATA**

In `registry/indicators.json`, add a new **top-level** key after the `"sourceInventory"` object's closing `}` (add a comma after `sourceInventory`'s closing brace, before the file's final `}`):

```json
  "cadenceHorizon": {
    "market-share-pct":       { "cadence": "quarterly", "horizon": "coincident" },
    "grossMargin":            { "cadence": "quarterly", "horizon": "lagging"    },
    "D2":                     { "cadence": "quarterly", "horizon": "lagging"    },
    "D6":                     { "cadence": "daily",     "horizon": "coincident" },
    "S9":                     { "cadence": "quarterly", "horizon": "coincident" },
    "S10":                    { "cadence": "quarterly", "horizon": "coincident" },
    "perfPerWatt":            { "cadence": "quarterly", "horizon": "lagging"    },
    "flopsPerDollar":         { "cadence": "quarterly", "horizon": "lagging"    },
    "apiArr":                 { "cadence": "quarterly", "horizon": "lagging"    },
    "releaseCadence":         { "cadence": "quarterly", "horizon": "coincident" },
    "exportControlExposure":  { "cadence": "quarterly", "horizon": "lagging"    },
    "customerConcentration":  { "cadence": "quarterly", "horizon": "lagging"    },
    "rpoBacklog":             { "cadence": "quarterly", "horizon": "leading"    },
    "vendorRevenueGuidance":  { "cadence": "quarterly", "horizon": "leading"    },
    "leadTimes":              { "cadence": "weekly",    "horizon": "coincident" },
    "designWins":             { "cadence": "weekly",    "horizon": "leading"    },
    "gpuSpotPrice":           { "cadence": "daily",     "horizon": "coincident" }
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_registry_horizon.py -q`
Expected: PASS (10 passed).

- [ ] **Step 6: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 264 passed, 3 skipped (254 + 10 new). The existing registry tests still pass — confirming the frozen loader ignores the new top-level key.

- [ ] **Step 7: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add registry/indicators.json gpu_agent/registry/horizon.py tests/test_registry_horizon.py && git commit -m "feat(4-2): cadenceHorizon top-level map (all 17 tagged) + registry/horizon.py accessor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Source inventory + manifest coverage for the five new + frozen guard

**Files:**
- Modify: `registry/indicators.json` (add 5 `sourceInventory` entries)
- Modify: `manifests/chips.merchant-gpu.json` (add 5 expectedIndicators; extend/add expectedSources)
- Test: `tests/test_manifest.py` (extend)

**Interfaces:**
- Consumes: `load_manifest`, `CoverageManifest`, `SourceEntry`, `compute_coverage_gaps` (`gpu_agent/manifest.py`); `IndicatorRegistry` (frozen).
- Produces (manifest DATA): expectedIndicators for `rpoBacklog`, `vendorRevenueGuidance`, `leadTimes`, `designWins`, `gpuSpotPrice`; new expectedSources `vendor-pr-trade-press`, `semianalysis`, `gpu-marketplaces`; reuses `nvda-earnings`/`amd-earnings`/`channel-checks` by extending their `indicators` lists.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_manifest.py`:

```python
def test_new_indicators_present_in_manifest_and_resolve():
    """The five 4-2 indicators are declared in the shipped manifest and resolve."""
    from gpu_agent.registry.indicators import IndicatorRegistry

    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    reg = IndicatorRegistry.load("registry/indicators.json")
    declared = {e.indicatorId for e in manifest.expectedIndicators}
    for ind in ("rpoBacklog", "vendorRevenueGuidance", "leadTimes", "designWins", "gpuSpotPrice"):
        assert ind in declared, f"{ind} missing from manifest expectedIndicators"
        reg.resolve(ind)  # must not raise


def test_source_inventory_entries_validate_as_source_entries():
    """Every sourceInventory entry in indicators.json (incl. the 5 new) is a valid SourceEntry."""
    import json
    from pathlib import Path
    from gpu_agent.manifest import SourceEntry

    data = json.loads(Path("registry/indicators.json").read_text(encoding="utf-8"))
    inv = data["sourceInventory"]
    for ind in ("rpoBacklog", "vendorRevenueGuidance", "leadTimes", "designWins", "gpuSpotPrice"):
        assert ind in inv, f"{ind} missing from sourceInventory"
    for ind_id, entries in inv.items():
        for entry in entries:
            SourceEntry(**entry)  # must not raise


def test_new_indicators_flagged_as_gaps_when_uncovered():
    """With nothing gathered, the five new indicators are logged as coverage gaps."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    gaps = compute_coverage_gaps(manifest, blob_urls=[], found_indicator_ids=set())
    gap_ids = {g.id for g in gaps if g.type == "indicator"}
    for ind in ("rpoBacklog", "vendorRevenueGuidance", "leadTimes", "designWins", "gpuSpotPrice"):
        assert ind in gap_ids


def test_semianalysis_source_is_paywalled_gap():
    """The SemiAnalysis lead-times source is inventoried as paywalled (labeled, never scraped)."""
    manifest = load_manifest("manifests/chips.merchant-gpu.json")
    gaps = compute_coverage_gaps(manifest, blob_urls=[], found_indicator_ids=set())
    sa = next((g for g in gaps if g.id == "semianalysis"), None)
    assert sa is not None
    assert sa.acquisitionStatus == "paywalled"
    assert sa.type == "source"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_manifest.py -q`
Expected: FAIL — `rpoBacklog missing from manifest expectedIndicators` (and the SemiAnalysis / gap assertions fail).

- [ ] **Step 3: Add the five `sourceInventory` entries to the registry DATA**

In `registry/indicators.json`, inside the `"sourceInventory"` object, after the `"customerConcentration"` array's closing `]` (add a comma after it), insert:

```json
    "rpoBacklog": [
      { "name": "NVIDIA / AMD 10-Q / 10-K (remaining performance obligations / purchase commitments)", "accessMethod": "filing", "tier": "primary", "costUsd": 0, "license": "public", "refresh": "quarterly" },
      { "name": "Earnings call / IR transcript (backlog commentary)", "accessMethod": "free-web", "tier": "secondary", "costUsd": 0, "license": "public", "refresh": "quarterly" }
    ],
    "vendorRevenueGuidance": [
      { "name": "NVIDIA / AMD earnings guidance (next-quarter DC/AI revenue outlook)", "accessMethod": "filing", "tier": "primary", "costUsd": 0, "license": "public", "refresh": "quarterly" },
      { "name": "Earnings call / investor-day transcript (forward guidance)", "accessMethod": "free-web", "tier": "secondary", "costUsd": 0, "license": "public", "refresh": "quarterly" }
    ],
    "leadTimes": [
      { "name": "Channel checks / distributor lead-time reporting (DigiTimes, Tom's Hardware)", "accessMethod": "free-web", "tier": "secondary", "costUsd": 0, "license": "public", "refresh": "weekly" },
      { "name": "SemiAnalysis channel-check lead-time data (deep tier subscription; estimate-grade, never scraped)", "accessMethod": "licensed-api", "tier": "secondary", "costUsd": 0, "license": "licensed", "refresh": "weekly" }
    ],
    "designWins": [
      { "name": "Company press releases / product announcements (design-win disclosures)", "accessMethod": "free-web", "tier": "primary", "costUsd": 0, "license": "public", "refresh": "on-demand" },
      { "name": "Trade press (Tom's Hardware, AnandTech, SemiAnalysis) on design wins", "accessMethod": "free-web", "tier": "secondary", "costUsd": 0, "license": "public", "refresh": "weekly" }
    ],
    "gpuSpotPrice": [
      { "name": "GPU marketplaces / resale listings (secondary-market spot price; scrape-fed, estimate-grade)", "accessMethod": "free-web", "tier": "secondary", "costUsd": 0, "license": "public", "refresh": "daily" }
    ]
```

- [ ] **Step 4: Extend the manifest — expectedIndicators**

In `manifests/chips.merchant-gpu.json`, inside `"expectedIndicators"`, after the `customerConcentration` entry's closing `}` (add a comma after it), insert:

```json
    {
      "indicatorId": "rpoBacklog",
      "dimension": "momentum",
      "priority": "preferred",
      "sourceIds": ["nvda-earnings", "amd-earnings"]
    },
    {
      "indicatorId": "vendorRevenueGuidance",
      "dimension": "momentum",
      "priority": "required",
      "sourceIds": ["nvda-earnings", "amd-earnings"]
    },
    {
      "indicatorId": "leadTimes",
      "dimension": "bottleneck",
      "priority": "preferred",
      "sourceIds": ["channel-checks", "semianalysis"]
    },
    {
      "indicatorId": "designWins",
      "dimension": "competitiveStructure",
      "priority": "optional",
      "sourceIds": ["vendor-pr-trade-press"]
    },
    {
      "indicatorId": "gpuSpotPrice",
      "dimension": "momentum",
      "priority": "optional",
      "sourceIds": ["gpu-marketplaces"]
    }
```

- [ ] **Step 5: Extend the manifest — reuse existing sources + add new ones**

In `manifests/chips.merchant-gpu.json`, extend the `"indicators"` list of the existing sources so the reuse is declared:
- In the `nvda-earnings` source, change `"indicators": ["D2", "grossMargin", "S9", "S10"]` to `"indicators": ["D2", "grossMargin", "S9", "S10", "rpoBacklog", "vendorRevenueGuidance"]`.
- In the `amd-earnings` source, change `"indicators": ["D2", "grossMargin", "S9"]` to `"indicators": ["D2", "grossMargin", "S9", "rpoBacklog", "vendorRevenueGuidance"]`.
- In the `channel-checks` source, change `"indicators": ["S10"]` to `"indicators": ["S10", "leadTimes"]`.

Then, inside `"expectedSources"`, after the last source (`nvda-10k-risk-factors`) entry's closing `}` (add a comma after it), insert:

```json
    {
      "id": "vendor-pr-trade-press",
      "label": "Vendor press releases + trade press on merchant-GPU design wins",
      "urlPatterns": ["nvidianews.nvidia.com", "ir.amd.com/news-events", "tomshardware.com", "semianalysis.com"],
      "accessMethod": "free-web",
      "tier": "secondary",
      "costUsd": 0,
      "license": "public",
      "refresh": "weekly",
      "indicators": ["designWins"]
    },
    {
      "id": "semianalysis",
      "label": "SemiAnalysis channel-check lead-time data (deep tier)",
      "urlPatterns": ["semianalysis.com"],
      "accessMethod": "licensed-api",
      "tier": "secondary",
      "costUsd": 0,
      "license": "licensed",
      "refresh": "weekly",
      "indicators": ["leadTimes"],
      "paywalledNote": "SemiAnalysis publishes free headlines; deep channel-check lead-time data is behind a subscription. Paywalled portions are inventoried + labeled estimate, never scraped (Part 22)."
    },
    {
      "id": "gpu-marketplaces",
      "label": "GPU marketplaces / resale listings (secondary-market spot price)",
      "urlPatterns": ["ebay.com", "amazon.com", "newegg.com"],
      "accessMethod": "free-web",
      "tier": "secondary",
      "costUsd": 0,
      "license": "public",
      "refresh": "daily",
      "indicators": ["gpuSpotPrice"]
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_manifest.py -q`
Expected: PASS (existing + 4 new). Note `test_real_manifest_indicator_ids_all_resolve_in_registry` now also covers the 5 new ids.

- [ ] **Step 7: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 268 passed, 3 skipped (264 + 4 new).

- [ ] **Step 8: Confirm the frozen contract is byte-unchanged**

Run: `cd /c/Users/danie/random_for_fun && git diff --stat 559abd0 -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py`
Expected: **no output** (every frozen file is byte-unchanged since the branch base).

- [ ] **Step 9: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add registry/indicators.json manifests/chips.merchant-gpu.json tests/test_manifest.py && git commit -m "feat(4-2): source inventory + manifest coverage for the five new indicators

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-06-29-leading-daily-indicators-design.md`):
- §1 cadence×horizon top-level DATA map; loader ignores it → Task 2 (map) + Task 2 Step 6 (full suite confirms loader unaffected). ✓
- §1 coverage rule (every scoring indicator tagged) → Task 2 `validate_coverage` + `test_validate_coverage_*`. ✓
- §2 five new in-lane indicators with exact fields/sides/scoring → Task 1. ✓
- §2 scoring three flow into DMI/SMI; price/structural overlays excluded → Task 1 `test_new_scoring_indicators_contribute_to_dmi_smi` + `test_new_overlay_indicators_excluded_from_dmi_smi`. ✓
- §3 cadence×horizon tags for the existing 12 → Task 2 map (all 17). ✓
- §4 `gpu_agent/registry/horizon.py` with `get/cadence/horizon/validate_coverage` + HorizonError; orphan-tag + invalid-value guards → Task 2. ✓
- §5 sourceInventory entries for the 5 new; manifest expectedIndicators + expectedSources; paywalled labeled estimate / scrape-fed inventoried not scraped → Task 3. ✓
- §6 frozen byte-unchanged; additive DATA + new module → Task 3 Step 8 git-diff guard. ✓
- §7 doctrine (no invented values; overlays excluded; paywalled labeled) → inert-by-design (no findings) + Task 1/Task 3 tests. ✓
- §8 test strategy (load reads map; cadence/horizon; untagged/invalid→error; validate_coverage pass+fail-loud; new indicators resolve+validate; seam guard; DMI/SMI unchanged on fixtures) → Tasks 1–3 tests. ✓
- §10 acceptance items 1–5 all map to tasks above. ✓

**DMI/SMI-unchanged-on-fixtures (acceptance §10.5):** the existing `test_scoring.py::test_dmi_smi_contribution` pins exact values from hand-built findings and continues to pass unchanged (new indicators have no findings → zero contribution); `test_new_overlay_indicators_excluded_from_dmi_smi` adds an explicit inert/overlay guard. ✓

**Placeholder scan:** none — every step has complete JSON/code/commands.

**Type consistency:** `IndicatorHorizons`/`HorizonError`/`CADENCES`/`HORIZONS` (Task 2) are imported by `test_registry_horizon.py` exactly as defined. `validate_coverage(registry)` uses `registry.indicators` (dict) and `registry.resolve` — both present on the frozen `IndicatorRegistry`. Manifest source ids referenced in expectedIndicators (`nvda-earnings`, `amd-earnings`, `channel-checks`, `vendor-pr-trade-press`, `semianalysis`, `gpu-marketplaces`) all exist after Task 3 Step 5. `SourceEntry`/`CoverageManifest`/`compute_coverage_gaps`/`load_manifest` names match `gpu_agent/manifest.py`. The `_f` helper used in the new scoring tests is defined at the top of `tests/test_scoring.py`. ✓

**Test-count math:** baseline 248 → +6 (Task 1) → +10 (Task 2) → +4 (Task 3) = **268 passed, 3 skipped** at the end.
