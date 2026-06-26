# Indicator Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move indicator→dimension / polarity-track / weight bindings out of hardcoded code into a define-once `registry/indicators.json`, make DMI/SMI aggregate per-indicator (not per-finding), and add a fail-loud validation gate — so a new Category Agent (CPU, AI-model, …) is pure config.

**Architecture:** A small `gpu_agent/registry/` package loads `registry/indicators.json` (global indicator defaults + per-category overrides) and the slimmed `docs/taxonomy.json` (the structural contract it validates against). `briefing.py` and `scoring.py` stop importing the hardcoded `judgment/map.py` (deleted) and resolve dimension / polarity-track / weight through the registry. `scoring.dmi_smi_contribution` collapses each indicator's findings to one latest-vintage contribution. A new registry-validation gate runs at pipeline start.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest. Run all commands from repo root `C:\Users\danie\random_for_fun` using `.venv/Scripts/python`.

## Global Constraints

- **Frozen contract — never edit:** the Finding/Scorecard schema (`gpu_agent/schema/`), the 6 dimensions, `gpu_agent/gate.py` rules, `gpu_agent/scoring.py:zscore`, the Part-7 finding/scorecard gate behavior. This plan adds a *separate* registry gate; it does not change the Part-7 gate.
- **The 6 dimensions are fixed:** `momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`.
- **TDD:** every task writes the failing test first, watches it fail, then implements.
- **Commit message trailer (every commit):** end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Run from repo root**; interpreter is `.venv/Scripts/python`; tests via `.venv/Scripts/python -m pytest`.
- **Branch:** work on `indicator-registry` (already created; the design spec is committed there).
- **No invented numbers / no silent zeros:** a dimension-mapped (`scoring:true`) indicator with `weight == 0` is a hard error; a non-scoring metric must be explicitly `scoring:false`.

---

## File Structure

**Create:**
- `registry/indicators.json` — the registry data (global `indicators` + per-category `overrides`).
- `gpu_agent/registry/__init__.py` — package marker; re-exports `IndicatorRegistry`, `IndicatorSpec`, `RegistryError`, `Taxonomy`, `validate_assignment`.
- `gpu_agent/registry/indicators.py` — `IndicatorSpec`, `IndicatorRegistry`, `RegistryError`.
- `gpu_agent/registry/structure.py` — `Taxonomy` loader (dimensions, categories) from `docs/taxonomy.json`.
- `gpu_agent/registry/validate.py` — `validate_assignment(assignment, registry, taxonomy) -> list[str]`.
- `tests/test_registry_indicators.py`, `tests/test_registry_structure.py`, `tests/test_registry_validate.py`, `tests/test_generalization.py`.

**Modify:**
- `docs/taxonomy.json` — slim to structure; lift metric lists into the registry.
- `gpu_agent/assignment.py` — add `category: str`.
- `fixtures/asg.chips.merchant-gpu.json` — add `"category": "chips.merchant-gpu"`.
- `gpu_agent/judgment/briefing.py` — resolve dimension + polarity-track via registry.
- `gpu_agent/judgment/map.py` — **delete**.
- `gpu_agent/scoring.py` — `dmi_smi_contribution` becomes registry-driven + per-indicator collapse.
- `gpu_agent/judgment/judge.py` — `judge_findings` + `build_briefing` call sites take `registry, category_id`.
- `gpu_agent/pipeline.py` — `build_scorecard` takes `registry`, uses `assignment.category`, runs registry gate.
- `gpu_agent/cli.py` — load registry + taxonomy; thread through `_pipeline`, `_judge`, `_build`.
- `fixtures/golden/scorecard.json` — re-baseline.

---

## Task 1: Indicator registry data + loader (`IndicatorSpec`, `IndicatorRegistry`)

**Files:**
- Create: `registry/indicators.json`
- Create: `gpu_agent/registry/__init__.py`
- Create: `gpu_agent/registry/indicators.py`
- Test: `tests/test_registry_indicators.py`

**Interfaces:**
- Produces:
  - `class RegistryError(Exception)` with `.violations: list[str]`.
  - `class IndicatorSpec(BaseModel)` — fields below.
  - `class IndicatorRegistry` with `@classmethod load(path) -> IndicatorRegistry` and `resolve(indicator_id: str, category_id: str | None = None) -> IndicatorSpec` (raises `RegistryError` if `indicator_id` unknown) and attribute `.indicators: dict[str, dict]`, `.overrides: dict[str, dict]`.

- [ ] **Step 1: Write the registry data file**

Create `registry/indicators.json`:

```json
{
  "version": "1.0",
  "indicators": {
    "market-share-pct": { "label": "Market share", "dimension": "moat", "polarityTrack": "demand", "side": "demand", "weight": 0.10, "unit": "pct_segment_rev", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.3, "scoring": true, "comparability": "revenue share; state segment + period; not unit share" },
    "grossMargin": { "label": "Gross margin", "dimension": "unitEconomics", "polarityTrack": "demand", "side": "demand", "weight": 0.10, "unit": "pct", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.3, "scoring": true },
    "D2": { "label": "DC revenue structure", "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.10, "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.4, "scoring": true },
    "D6": { "label": "GPU rental price", "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.12, "unit": "USD_per_gpu_hr", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.6, "scoring": true },
    "S9": { "label": "Alternative supply", "dimension": "competitiveStructure", "polarityTrack": "supply", "side": "supply", "weight": 0.04, "unit": "mixed", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true },
    "S10": { "label": "Whole-chain inventory", "dimension": "bottleneck", "polarityTrack": "supply", "side": "supply", "weight": 0.08, "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true },
    "perfPerWatt": { "label": "Performance per watt", "dimension": null, "scoring": false, "kind": "measured", "unit": "perf_per_W" },
    "flopsPerDollar": { "label": "FLOPs per dollar", "dimension": null, "scoring": false, "kind": "measured", "unit": "flops_per_USD" }
  },
  "overrides": {
    "chips.hbm-memory": { "market-share-pct": { "weight": 0.04 } }
  }
}
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_registry_indicators.py`:

```python
import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec, RegistryError

REG = pathlib.Path("registry/indicators.json")

def test_resolve_returns_spec_with_dimension():
    reg = IndicatorRegistry.load(REG)
    spec = reg.resolve("market-share-pct")
    assert isinstance(spec, IndicatorSpec)
    assert spec.dimension == "moat"
    assert spec.polarityTrack == "demand"
    assert spec.weight == 0.10
    assert spec.scoring is True

def test_resolve_applies_category_override():
    reg = IndicatorRegistry.load(REG)
    base = reg.resolve("market-share-pct")
    overridden = reg.resolve("market-share-pct", "chips.hbm-memory")
    assert base.weight == 0.10
    assert overridden.weight == 0.04
    assert overridden.dimension == "moat"  # non-overridden fields preserved

def test_resolve_unknown_indicator_raises():
    reg = IndicatorRegistry.load(REG)
    with pytest.raises(RegistryError):
        reg.resolve("does-not-exist")

def test_non_scoring_metric_has_null_dimension():
    reg = IndicatorRegistry.load(REG)
    spec = reg.resolve("perfPerWatt")
    assert spec.scoring is False
    assert spec.dimension is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_registry_indicators.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.registry'`

- [ ] **Step 4: Write the package marker**

Create `gpu_agent/registry/__init__.py`:

```python
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec, RegistryError

__all__ = ["IndicatorRegistry", "IndicatorSpec", "RegistryError"]
```

- [ ] **Step 5: Write minimal implementation**

Create `gpu_agent/registry/indicators.py`:

```python
from __future__ import annotations
import json, pathlib
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict

class RegistryError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))

class IndicatorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str = ""
    dimension: Optional[str] = None
    polarityTrack: Optional[Literal["demand", "supply"]] = None
    side: Optional[Literal["demand", "supply", "price", "structural"]] = None
    weight: float = 0.0
    unit: str = ""
    kind: Literal["measured", "qualitative"] = "measured"
    comparability: str = ""
    scoring: bool = True
    readsLevelOrSlope: Optional[Literal["level", "slope"]] = None
    decayLambda: float = 0.0
    leadMonths: str = ""

class IndicatorRegistry:
    def __init__(self, indicators: dict[str, dict], overrides: dict[str, dict] | None = None):
        self.indicators = indicators
        self.overrides = overrides or {}

    @classmethod
    def load(cls, path) -> "IndicatorRegistry":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(data.get("indicators", {}), data.get("overrides", {}))

    def resolve(self, indicator_id: str, category_id: str | None = None) -> IndicatorSpec:
        if indicator_id not in self.indicators:
            raise RegistryError([f"unregistered indicator: {indicator_id}"])
        merged = dict(self.indicators[indicator_id])
        if category_id and indicator_id in self.overrides.get(category_id, {}):
            merged.update(self.overrides[category_id][indicator_id])
        return IndicatorSpec(id=indicator_id, **merged)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_registry_indicators.py -v`
Expected: PASS (4 passed)

- [ ] **Step 7: Commit**

```bash
git add registry/indicators.json gpu_agent/registry/__init__.py gpu_agent/registry/indicators.py tests/test_registry_indicators.py
git commit -m "$(printf 'feat(registry): indicator spec + loader with category overrides\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 2: Slim taxonomy + structure loader (`Taxonomy`)

**Files:**
- Modify: `docs/taxonomy.json` (lift metric lists out; keep structure)
- Create: `gpu_agent/registry/structure.py`
- Modify: `gpu_agent/registry/__init__.py`
- Modify: `gpu_agent/registry/indicators.py` (add `validate_against`)
- Test: `tests/test_registry_structure.py`

**Interfaces:**
- Consumes: `IndicatorRegistry`, `RegistryError` (Task 1).
- Produces:
  - `class Taxonomy(BaseModel)` with `dimensions: frozenset[str]`, `categories: frozenset[str]`, `@classmethod load(path) -> Taxonomy`. Category ids are composed as `"<layer.id>.<category.id>"`.
  - `IndicatorRegistry.validate_against(self, taxonomy: Taxonomy) -> None` — raises `RegistryError` listing every scoring indicator whose `dimension` is not in `taxonomy.dimensions`, every override whose `category` is not in `taxonomy.categories`, and every `scoring:true` indicator with `weight == 0`.

- [ ] **Step 1: Slim `docs/taxonomy.json`**

Edit `docs/taxonomy.json`: in every `layers[].categories[]` entry, **delete** the `quantMetrics` and `qualMetrics` keys (keep `id`, `name`, `seedConstituents`). Under `modularity`, **delete** the `seedMetrics` array. Leave `meta`, `scoringRubric`, `scorecardSchema`, `modularity.assignmentSchema`, `modularity.entitySchema`, `modularity.seedEntities`, and the `layers` (now metric-free) intact. Add to `meta`: `"metricsAuthority": "registry/indicators.json is the authoritative source for indicator/metric scoring metadata; this file is structure only."`

- [ ] **Step 2: Write the failing test**

Create `tests/test_registry_structure.py`:

```python
import pathlib
import pytest
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.structure import Taxonomy

TAX = pathlib.Path("docs/taxonomy.json")
REG = pathlib.Path("registry/indicators.json")

def test_taxonomy_exposes_six_dimensions():
    tax = Taxonomy.load(TAX)
    assert tax.dimensions == frozenset(
        {"momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"})

def test_taxonomy_composes_layer_dot_category_ids():
    tax = Taxonomy.load(TAX)
    assert "chips.merchant-gpu" in tax.categories
    assert "chips.hbm-memory" in tax.categories

def test_registry_validates_clean_against_taxonomy():
    reg = IndicatorRegistry.load(REG)
    tax = Taxonomy.load(TAX)
    reg.validate_against(tax)  # must not raise

def test_validate_against_rejects_bad_dimension():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry({"x": {"dimension": "notADimension", "weight": 0.1, "scoring": True}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)

def test_validate_against_rejects_zero_weight_scoring_indicator():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry({"x": {"dimension": "moat", "weight": 0.0, "scoring": True}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)

def test_validate_against_rejects_unknown_override_category():
    tax = Taxonomy.load(TAX)
    bad = IndicatorRegistry(
        {"market-share-pct": {"dimension": "moat", "weight": 0.1, "scoring": True}},
        {"chips.not-a-category": {"market-share-pct": {"weight": 0.2}}})
    with pytest.raises(RegistryError):
        bad.validate_against(tax)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_registry_structure.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.registry.structure'`

- [ ] **Step 4: Write `structure.py`**

Create `gpu_agent/registry/structure.py`:

```python
from __future__ import annotations
import json, pathlib
from pydantic import BaseModel

class Taxonomy(BaseModel):
    dimensions: frozenset[str]
    categories: frozenset[str]

    @classmethod
    def load(cls, path) -> "Taxonomy":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        dims = {d["id"] for d in data["scoringRubric"]["dimensions"]}
        cats = {f"{layer['id']}.{c['id']}"
                for layer in data["layers"] for c in layer["categories"]}
        return cls(dimensions=frozenset(dims), categories=frozenset(cats))
```

- [ ] **Step 5: Add `validate_against` to `IndicatorRegistry`**

In `gpu_agent/registry/indicators.py`, add this method to `IndicatorRegistry` (place after `resolve`). It must NOT import `structure` at module top (avoid a cycle); it duck-types the taxonomy:

```python
    def validate_against(self, taxonomy) -> None:
        violations: list[str] = []
        for ind_id, raw in self.indicators.items():
            spec = IndicatorSpec(id=ind_id, **raw)
            if not spec.scoring:
                continue
            if spec.dimension not in taxonomy.dimensions:
                violations.append(f"{ind_id}: dimension '{spec.dimension}' not in taxonomy")
            if spec.weight == 0.0:
                violations.append(f"{ind_id}: scoring indicator has zero weight")
        for cat, inds in self.overrides.items():
            if cat not in taxonomy.categories:
                violations.append(f"override category '{cat}' not in taxonomy")
            for ind_id in inds:
                if ind_id not in self.indicators:
                    violations.append(f"override for unregistered indicator '{ind_id}'")
        if violations:
            raise RegistryError(violations)
```

- [ ] **Step 6: Re-export `Taxonomy`**

Replace `gpu_agent/registry/__init__.py` with:

```python
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec, RegistryError
from gpu_agent.registry.structure import Taxonomy

__all__ = ["IndicatorRegistry", "IndicatorSpec", "RegistryError", "Taxonomy"]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_registry_structure.py -v`
Expected: PASS (6 passed)

- [ ] **Step 8: Commit**

```bash
git add docs/taxonomy.json gpu_agent/registry/structure.py gpu_agent/registry/indicators.py gpu_agent/registry/__init__.py tests/test_registry_structure.py
git commit -m "$(printf 'feat(registry): slim taxonomy to structure + validate_against\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 3: Registry-validation gate for assignments

**Files:**
- Create: `gpu_agent/registry/validate.py`
- Modify: `gpu_agent/registry/__init__.py`
- Test: `tests/test_registry_validate.py`

**Interfaces:**
- Consumes: `IndicatorRegistry`, `Taxonomy`, `RegistryError` (Tasks 1–2); `Assignment` (from `gpu_agent.assignment`, gains `category` in Task 4 — this task uses a stub object in tests and accesses `.category` + `.metrics`).
- Produces: `validate_assignment(assignment, registry, taxonomy) -> list[str]` — returns a list of violation strings (does not raise): assignment `category` not in taxonomy; any metric in `assignment.metrics` unregistered; any *scoring* metric whose `dimension` not in taxonomy.

- [ ] **Step 1: Write the failing test**

Create `tests/test_registry_validate.py`:

```python
import pathlib
from types import SimpleNamespace
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment

REG = pathlib.Path("registry/indicators.json")
TAX = pathlib.Path("docs/taxonomy.json")

def _asg(category, metrics):
    return SimpleNamespace(category=category, metrics=metrics)

def test_clean_assignment_has_no_violations():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["D2", "D6", "S9", "S10", "market-share-pct", "grossMargin"])
    assert validate_assignment(asg, reg, tax) == []

def test_unregistered_metric_is_flagged():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["D2", "totallyMadeUp"])
    violations = validate_assignment(asg, reg, tax)
    assert any("totallyMadeUp" in v for v in violations)

def test_unknown_category_is_flagged():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.not-real", ["D2"])
    violations = validate_assignment(asg, reg, tax)
    assert any("chips.not-real" in v for v in violations)

def test_non_scoring_metric_passes():
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    asg = _asg("chips.merchant-gpu", ["perfPerWatt"])
    assert validate_assignment(asg, reg, tax) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_registry_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.registry.validate'`

- [ ] **Step 3: Write `validate.py`**

Create `gpu_agent/registry/validate.py`:

```python
from __future__ import annotations
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError

def validate_assignment(assignment, registry: IndicatorRegistry, taxonomy) -> list[str]:
    violations: list[str] = []
    if assignment.category not in taxonomy.categories:
        violations.append(f"assignment category '{assignment.category}' not in taxonomy")
    for metric in assignment.metrics:
        try:
            spec = registry.resolve(metric, assignment.category)
        except RegistryError as e:
            violations.extend(e.violations)
            continue
        if spec.scoring and spec.dimension not in taxonomy.dimensions:
            violations.append(f"{metric}: dimension '{spec.dimension}' not in taxonomy")
    return violations
```

- [ ] **Step 4: Re-export**

Update `gpu_agent/registry/__init__.py` to add the import and `__all__` entry:

```python
from gpu_agent.registry.indicators import IndicatorRegistry, IndicatorSpec, RegistryError
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment

__all__ = ["IndicatorRegistry", "IndicatorSpec", "RegistryError", "Taxonomy", "validate_assignment"]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_registry_validate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/registry/validate.py gpu_agent/registry/__init__.py tests/test_registry_validate.py
git commit -m "$(printf 'feat(registry): fail-loud assignment validation gate\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 4: Add `category` to Assignment; de-hardcode scorecard categoryId

**Files:**
- Modify: `gpu_agent/assignment.py:5-13`
- Modify: `fixtures/asg.chips.merchant-gpu.json`
- Modify: `gpu_agent/pipeline.py:8-22`
- Test: `tests/test_assignment_category.py` (create)

**Interfaces:**
- Consumes: existing `Assignment`, `build_scorecard` (current signature `build_scorecard(findings, ratings, anchors, assignment, narrative, confidence)`).
- Produces: `Assignment` gains `category: str`. `build_scorecard` still has the same parameters in this task; it now reads `assignment.category` for `categoryId` instead of the hardcoded string. (Task 7 adds the `registry` parameter.)

- [ ] **Step 1: Write the failing test**

Create `tests/test_assignment_category.py`:

```python
from gpu_agent.assignment import load_assignment

def test_assignment_has_category():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    assert a.category == "chips.merchant-gpu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_assignment_category.py -v`
Expected: FAIL with `AttributeError: 'Assignment' object has no attribute 'category'` (or a Pydantic validation error once the field is required)

- [ ] **Step 3: Add the field**

In `gpu_agent/assignment.py`, add `category: str` to the `Assignment` model (after `id`):

```python
class Assignment(BaseModel):
    id: str
    category: str
    template: str
    mode: str
    entities: list[str]
    metrics: list[str]
    weights: dict[str, float] = Field(default_factory=dict)
    version: str
    asOf: str
```

- [ ] **Step 4: Update the fixture**

In `fixtures/asg.chips.merchant-gpu.json`, add `"category": "chips.merchant-gpu",` immediately after the `"id"` line.

- [ ] **Step 5: De-hardcode `build_scorecard`**

In `gpu_agent/pipeline.py`, change the `Scorecard(...)` construction to use `assignment.category`:

```python
    sc = Scorecard(
        categoryId=assignment.category, asOf=assignment.asOf, findings=findings,
        dimensionRatings=ratings,
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors),
        narrative=narrative, confidence=confidence,
        sources=sorted({e.source for f in findings for e in f.evidence}),
        provenance={"assignment": f"{assignment.id}@{assignment.version}"})
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_assignment_category.py -v`
Expected: PASS (1 passed)

- [ ] **Step 7: Commit**

```bash
git add gpu_agent/assignment.py fixtures/asg.chips.merchant-gpu.json gpu_agent/pipeline.py tests/test_assignment_category.py
git commit -m "$(printf 'feat(assignment): add category field; de-hardcode scorecard categoryId\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 5: Rewire `briefing.py` to the registry; delete `map.py`

**Files:**
- Modify: `gpu_agent/judgment/briefing.py`
- Delete: `gpu_agent/judgment/map.py`
- Modify: `gpu_agent/judgment/judge.py` (call site of `build_briefing`)
- Test: `tests/test_briefing_registry.py` (create)

**Interfaces:**
- Consumes: `IndicatorRegistry` (Task 1), `Finding`.
- Produces: `build_briefing(findings: list[Finding], registry: IndicatorRegistry, category_id: str) -> Briefing`. Dimension grouping and the anchor's polarity track are resolved per finding via `registry.resolve(f.indicatorId, category_id)`; findings whose indicator has `dimension is None` are skipped.

- [ ] **Step 1: Write the failing test**

Create `tests/test_briefing_registry.py`:

```python
import pathlib
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG = pathlib.Path("registry/indicators.json")

def _f(fid, indicatorId, pol_d, pol_s, mag):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity="nvidia",
        observedAt="2026-06", capturedAt="2026-06-25T00:00:00Z")

def test_briefing_groups_by_registry_dimension():
    reg = IndicatorRegistry.load(REG)
    findings = [_f("a", "D2", 1, 0, 3), _f("b", "S10", 0, 1, 3)]
    b = build_briefing(findings, reg, "chips.merchant-gpu")
    assert "momentum" in b.grouped
    assert "bottleneck" in b.grouped
    assert b.anchors["momentum"] == 1.0   # demand-track +1 * 3/3
    assert b.anchors["bottleneck"] == 1.0  # supply-track +1 * 3/3

def test_briefing_skips_non_scoring_indicator():
    reg = IndicatorRegistry.load(REG)
    findings = [_f("a", "perfPerWatt", 1, 0, 3)]  # dimension is None
    b = build_briefing(findings, reg, "chips.merchant-gpu")
    assert b.grouped == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_briefing_registry.py -v`
Expected: FAIL with `TypeError` (build_briefing takes 1 positional arg) or an `ImportError` from `map`.

- [ ] **Step 3: Rewrite `briefing.py`**

Replace `gpu_agent/judgment/briefing.py` with:

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.registry.indicators import IndicatorRegistry

class Briefing(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
    anchors: dict[str, float] = Field(default_factory=dict)
    grouped: dict[str, list[str]] = Field(default_factory=dict)

def _polarity(f: Finding, track: str) -> int:
    return f.polarityDemand if track == "demand" else f.polaritySupply

def build_briefing(findings: list[Finding], registry: IndicatorRegistry,
                   category_id: str) -> Briefing:
    grouped: dict[str, list[Finding]] = {}
    tracks: dict[str, str] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        if spec.dimension is None:
            continue
        grouped.setdefault(spec.dimension, []).append(f)
        tracks[spec.dimension] = spec.polarityTrack or "demand"
    anchors: dict[str, float] = {}
    grouped_ids: dict[str, list[str]] = {}
    for dim, fs in grouped.items():
        track = tracks[dim]
        anchors[dim] = sum(_polarity(f, track) * f.magnitude / 3 for f in fs) / len(fs)
        grouped_ids[dim] = [f.id for f in fs]
    return Briefing(findings=findings, anchors=anchors, grouped=grouped_ids)
```

- [ ] **Step 4: Delete `map.py`**

```bash
git rm gpu_agent/judgment/map.py
```

- [ ] **Step 5: Update the `build_briefing` call site in `judge.py`**

In `gpu_agent/judgment/judge.py`, change `judge_findings` to accept and pass the registry + category. Update the signature and the `build_briefing` call:

```python
def judge_findings(findings: list[Finding], client: LLMClient, registry, category_id: str,
                   *, samples: int = 3, resample_budget: int = 2,
                   model: str = "claude-opus-4-8") -> JudgmentBundle:
    briefing = build_briefing(findings, registry, category_id)
    prompt = build_user_prompt(briefing)
    ...
```

(Leave the rest of `judge_findings` unchanged.)

> **Sequencing note:** this changes `judge_findings`' signature, so its CLI callers
> (`cli._pipeline`, `cli._judge`) are temporarily broken until they are rewired in Task 7.
> Run only this task's test file in Step 6 — do **not** run the full suite until Task 7.

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_briefing_registry.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add gpu_agent/judgment/briefing.py gpu_agent/judgment/judge.py tests/test_briefing_registry.py
git rm gpu_agent/judgment/map.py
git commit -m "$(printf 'refactor(judgment): resolve dimension/track via registry; drop hardcoded map\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 6: Registry-driven, per-indicator DMI/SMI (the aggregation fix)

**Files:**
- Modify: `gpu_agent/scoring.py:13-16`
- Test: `tests/test_scoring_per_indicator.py` (create)

**Interfaces:**
- Consumes: `IndicatorRegistry` (Task 1), `Finding`.
- Produces: `dmi_smi_contribution(findings: list[Finding], registry: IndicatorRegistry, category_id: str, weight_overrides: dict[str, float] | None = None) -> tuple[float, float]`. Collapses each indicator's findings to one latest-vintage finding (`capturedAt` then `observedAt`; tie-break highest `magnitude`); skips `scoring:false` and `side ∈ {price, structural}`; weight = `weight_overrides[id]` if present else `registry.resolve(id, category).weight`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scoring_per_indicator.py`:

```python
import pathlib
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG = pathlib.Path("registry/indicators.json")

def _f(fid, indicatorId, pol_d, pol_s, mag, observedAt):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity="nvidia",
        observedAt=observedAt, capturedAt="2026-06-25T00:00:00Z")

def test_duplicate_findings_do_not_scale_the_index():
    reg = IndicatorRegistry.load(REG)
    one = dmi_smi_contribution([_f("a", "D2", 1, 0, 3, "2026-05")], reg, "chips.merchant-gpu")
    three = dmi_smi_contribution(
        [_f("a", "D2", 1, 0, 3, "2026-05"), _f("b", "D2", 1, 0, 3, "2026-02"),
         _f("c", "D2", 1, 0, 3, "2025-11")], reg, "chips.merchant-gpu")
    assert one == three  # per-indicator collapse: count-independent

def test_latest_vintage_wins_within_indicator():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("old", "D2", -1, 0, 3, "2025-11"), _f("new", "D2", 1, 0, 3, "2026-05")],
        reg, "chips.merchant-gpu")
    assert dmi == 0.10  # uses the +1 latest finding: 0.10 * 1 * 3/3

def test_moat_and_unit_economics_now_carry_weight():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("m", "market-share-pct", 1, 0, 3, "2026-06")], reg, "chips.merchant-gpu")
    assert dmi == 0.10  # 0.10 weight, was 0.0 before

def test_weight_override_takes_precedence():
    reg = IndicatorRegistry.load(REG)
    dmi, _ = dmi_smi_contribution(
        [_f("d", "D2", 1, 0, 3, "2026-05")], reg, "chips.merchant-gpu",
        weight_overrides={"D2": 0.50})
    assert dmi == 0.50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_scoring_per_indicator.py -v`
Expected: FAIL — current `dmi_smi_contribution(findings, weights)` has a different signature, raising `TypeError`.

- [ ] **Step 3: Rewrite `dmi_smi_contribution`**

In `gpu_agent/scoring.py`, replace `dmi_smi_contribution` (keep `zscore` untouched above it):

```python
def _latest(findings: list[Finding]) -> Finding:
    return max(findings, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))

def dmi_smi_contribution(findings, registry, category_id,
                         weight_overrides: dict[str, float] | None = None) -> tuple[float, float]:
    weight_overrides = weight_overrides or {}
    by_indicator: dict[str, list[Finding]] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        if not spec.scoring or spec.side in ("price", "structural"):
            continue
        by_indicator.setdefault(f.indicatorId, []).append(f)
    dmi = smi = 0.0
    for ind_id, fs in by_indicator.items():
        spec = registry.resolve(ind_id, category_id)
        weight = weight_overrides.get(ind_id, spec.weight)
        chosen = _latest(fs)
        dmi += weight * chosen.polarityDemand * chosen.magnitude / 3
        smi += weight * chosen.polaritySupply * chosen.magnitude / 3
    return dmi, smi
```

Add `from gpu_agent.schema.finding import Finding` at the top if not already imported (it is).

> **Sequencing note:** this changes `dmi_smi_contribution`' signature; its caller
> `pipeline.build_scorecard` is rewired to match in Task 7. Run only this task's test file in
> Step 4 — do **not** run the full suite until Task 7.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_scoring_per_indicator.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/scoring.py tests/test_scoring_per_indicator.py
git commit -m "$(printf 'fix(scoring): per-indicator DMI/SMI from registry (no finding-count scaling)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 7: Thread registry through pipeline + CLI; run the gate; re-baseline golden

**Files:**
- Modify: `gpu_agent/pipeline.py`
- Modify: `gpu_agent/judgment/judge.py` (call sites already updated in Task 5; here we wire callers)
- Modify: `gpu_agent/cli.py`
- Modify: `fixtures/golden/scorecard.json`
- Test: `tests/test_pipeline_integration.py` (update existing if present), `tests/test_gate_registry_integration.py` (create)

**Interfaces:**
- Consumes: `IndicatorRegistry`, `Taxonomy`, `validate_assignment` (Tasks 1–3); `dmi_smi_contribution(findings, registry, category, weight_overrides)` (Task 6); `build_briefing(findings, registry, category)` (Task 5); `judge_findings(findings, client, registry, category, *, ...)` (Task 5).
- Produces: `build_scorecard(findings, ratings, anchors, assignment, narrative, confidence, registry) -> Scorecard`. CLI loads `registry/indicators.json` + `docs/taxonomy.json` once, runs `validate_assignment` (raising `RegistryError` on violations) before scoring.

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_gate_registry_integration.py`:

```python
import json, pathlib, subprocess, sys

def test_pipeline_rejects_unregistered_metric(tmp_path):
    asg = json.loads(pathlib.Path("fixtures/asg.chips.merchant-gpu.json").read_text("utf-8"))
    asg["metrics"] = asg["metrics"] + ["totallyMadeUp"]
    p = tmp_path / "asg.bad.json"
    p.write_text(json.dumps(asg), "utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "pipeline", "--docs", "fixtures/raw",
         "--assignment", str(p), "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z",
         "--recorded-extract", "fixtures/recorded/extract-nvda.json",
         "--recorded-judge", "fixtures/recorded/judge-nvda.json", "--out", str(tmp_path / "store")],
        capture_output=True, text=True)
    assert out.returncode != 0
    assert "totallyMadeUp" in (out.stderr + out.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_gate_registry_integration.py -v`
Expected: FAIL (the pipeline currently ignores unknown metrics and exits 0).

- [ ] **Step 3: Update `build_scorecard` to take the registry**

In `gpu_agent/pipeline.py`, update the signature and the `dmi_smi_contribution` call:

```python
def build_scorecard(findings, ratings, anchors, assignment, narrative, confidence, registry):
    dmi, smi = dmi_smi_contribution(findings, registry, assignment.category, assignment.weights)
    sc = Scorecard(
        categoryId=assignment.category, asOf=assignment.asOf, findings=findings,
        dimensionRatings=ratings,
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi, anchors=anchors),
        narrative=narrative, confidence=confidence,
        sources=sorted({e.source for f in findings for e in f.evidence}),
        provenance={"assignment": f"{assignment.id}@{assignment.version}"})
    violations = check_scorecard(sc)
    if violations:
        raise GateError(violations)
    return sc
```

- [ ] **Step 4: Wire the CLI (load registry, validate, thread through)**

In `gpu_agent/cli.py`, add imports near the top:

```python
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
```

Add a helper after `_load_docs`:

```python
def _load_registry():
    return (IndicatorRegistry.load("registry/indicators.json"), Taxonomy.load("docs/taxonomy.json"))

def _gate_assignment(a, registry, taxonomy):
    violations = validate_assignment(a, registry, taxonomy)
    if violations:
        raise RegistryError(violations)
```

In `_pipeline(args)`, after `a = load_assignment(args.assignment)`, add the gate and thread the registry. The judge + scorecard calls become:

```python
    a = load_assignment(args.assignment)
    registry, taxonomy = _load_registry()
    _gate_assignment(a, registry, taxonomy)
    ...
    bundle = judge_findings(findings, jdg_client, registry, a.category,
                            samples=args.samples, model=args.model)
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a,
                         bundle.narrative, bundle.confidence, registry)
```

In `_judge(args)`, load the registry and pass it (the judge needs a category; read it from a new optional `--category` arg defaulting via the assignment is out of scope — instead require the findings' assignment is not available here, so add `judge_findings(findings, client, registry, args.category, ...)` and add an `--category` argument to the `judge` subparser, default `"chips.merchant-gpu"`).

In `_build(args)`, load the registry and pass it to `build_scorecard(..., registry)`.

Wrap the `RegistryError` like the existing `GateError` handling in `main`:

```python
    try:
        return _pipeline(args)
    except RegistryError as e:
        print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
        return 1
```

(Apply the same try/except around `_judge` and `_build`/`run` paths that now construct scorecards.)

- [ ] **Step 5: Re-baseline the golden scorecard**

Run the existing golden generation path and inspect the diff. The DMI/SMI and any moat/unitEconomics contribution will change (weights + per-indicator collapse). Regenerate `fixtures/golden/scorecard.json` from the now-correct pipeline and **manually verify** the new DMI/SMI equal the hand-computed per-indicator values before committing. Document the old→new delta in the commit body.

Run: `.venv/Scripts/python -m pytest tests/test_pipeline_integration.py -v`
Expected: PASS after the golden is updated.

- [ ] **Step 6: Run the full suite**

Run: `.venv/Scripts/python -m pytest -v`
Expected: PASS — all tests green (golden re-baselined; the 3 live smokes remain skipped).

- [ ] **Step 7: Commit**

```bash
git add gpu_agent/pipeline.py gpu_agent/cli.py fixtures/golden/scorecard.json tests/test_gate_registry_integration.py tests/test_pipeline_integration.py
git commit -m "$(printf 'feat(pipeline): registry-driven scoring + assignment gate; re-baseline golden\n\nDMI/SMI now per-indicator and registry-weighted; moat/unitEconomics contribute.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 8: Generalization proof — a second category, config-only

**Files:**
- Modify: `registry/indicators.json` (add a second category's indicators)
- Create: `fixtures/asg.models.frontier-closed.json`
- Create: `fixtures/recorded/extract-frontier.json`, `fixtures/recorded/judge-frontier.json`
- Test: `tests/test_generalization.py`

**Interfaces:**
- Consumes: the whole pipeline (Tasks 1–7). No code changes — this task proves a new agent is config-only.

- [ ] **Step 1: Add a second category's indicators to the registry**

In `registry/indicators.json`, add to `indicators`:

```json
    "apiArr": { "label": "API ARR", "dimension": "momentum", "polarityTrack": "demand", "side": "demand", "weight": 0.20, "unit": "USD_B", "kind": "measured", "readsLevelOrSlope": "slope", "decayLambda": 0.4, "scoring": true },
    "releaseCadence": { "label": "Model release cadence", "dimension": "competitiveStructure", "polarityTrack": "demand", "side": "demand", "weight": 0.10, "unit": "releases_per_yr", "kind": "measured", "readsLevelOrSlope": "level", "decayLambda": 0.4, "scoring": true }
```

(Reuse the existing `market-share-pct` / `grossMargin` for the model category — that is the whole point of shared indicators.)

- [ ] **Step 2: Write the failing generalization test**

Create `tests/test_generalization.py`:

```python
import json, pathlib
from gpu_agent.assignment import load_assignment
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.schema.finding import Finding, Confidence, Impact

REG, TAX = pathlib.Path("registry/indicators.json"), pathlib.Path("docs/taxonomy.json")

def _f(fid, indicatorId, pol_d, pol_s, mag, entity):
    return Finding(
        id=fid, statement="s", kind="observed", value=None, trend="flat", why="w",
        impact=Impact(targets=["models.frontier-closed"], direction="positive", mechanism="m"),
        evidence=[], reasoning=None, confidence=Confidence(level="medium", basis="b"),
        dispersion=None, asOf="2026-06", indicatorId=indicatorId, side="demand",
        polarityDemand=pol_d, polaritySupply=pol_s, magnitude=mag, entity=entity,
        observedAt="2026-06", capturedAt="2026-06-25T00:00:00Z")

def test_new_category_validates_and_scores_without_code_change():
    a = load_assignment("fixtures/asg.models.frontier-closed.json")
    reg, tax = IndicatorRegistry.load(REG), Taxonomy.load(TAX)
    assert validate_assignment(a, reg, tax) == []
    findings = [_f("x", "apiArr", 1, 0, 3, "openai"),
                _f("y", "releaseCadence", 1, 0, 2, "anthropic")]
    b = build_briefing(findings, reg, a.category)
    assert "momentum" in b.grouped and "competitiveStructure" in b.grouped
    dmi, smi = dmi_smi_contribution(findings, reg, a.category)
    assert dmi == 0.20 * 1 * 3 / 3 + 0.10 * 1 * 2 / 3   # 0.20 + 0.0667
    assert smi == 0.0
```

- [ ] **Step 3: Create the assignment fixture**

Create `fixtures/asg.models.frontier-closed.json`:

```json
{
  "id": "asg.models.frontier-closed",
  "category": "models.frontier-closed",
  "template": "category", "mode": "canonical",
  "entities": ["openai", "anthropic", "google-deepmind"],
  "metrics": ["apiArr", "releaseCadence", "market-share-pct", "grossMargin"],
  "weights": {}, "version": "1.0", "asOf": "2026-06"
}
```

- [ ] **Step 4: Run test to verify it fails, then passes**

Run: `.venv/Scripts/python -m pytest tests/test_generalization.py -v`
Expected: first FAIL (fixture/registry entries missing), then PASS after Steps 1+3 are in place. If `models.frontier-closed` is not yet a taxonomy category id, confirm it exists in the slimmed `docs/taxonomy.json` (`models` layer → `frontier-closed`); it does.

- [ ] **Step 5: Run the full suite**

Run: `.venv/Scripts/python -m pytest -v`
Expected: PASS (all green; 3 live smokes skipped).

- [ ] **Step 6: Commit**

```bash
git add registry/indicators.json fixtures/asg.models.frontier-closed.json tests/test_generalization.py
git commit -m "$(printf 'test(registry): second category scores config-only (generalization proof)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Final verification

- [ ] Run `.venv/Scripts/python -m pytest -v` — full suite green (live smokes skipped).
- [ ] Confirm `gpu_agent/judgment/map.py` no longer exists and nothing imports it: `git grep -n "judgment.map\|DIMENSION_MAP\|DIMENSION_POLARITY"` returns nothing.
- [ ] Confirm `docs/taxonomy.json` has no `quantMetrics`/`qualMetrics`/`seedMetrics`: `git grep -n "quantMetrics\|qualMetrics\|seedMetrics" docs/taxonomy.json` returns nothing.
- [ ] Spot-check one merchant-GPU run: DMI/SMI now reflect per-indicator latest-vintage values and `moat`/`unitEconomics` contribute.
