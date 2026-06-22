# GPU Category Agent — Core (Level A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic core of the `chips.merchant-gpu` Category Agent — it turns fixture Findings + ratings into a gate-validated 6-dimension scorecard with a Demand/Supply (DMI/SMI) contribution, matching a hand-authored golden scorecard.

**Architecture:** A small Python package (`gpu_agent`) with focused modules: Pydantic `schema`, a pure `gate` (charter Part 7), deterministic `scoring` (z-score anchors + DMI/SMI), an append-only JSON `store`, an `assignment` loader, and a `cli` that composes them. No LLM and no network — the LLM adapters (judgment, extraction) and connectors are a separate follow-on plan that builds on this frozen interface.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest.

## Global Constraints

- **Python 3.11+**; Pydantic **v2**; pytest. (Exact, from spec §10.)
- **No invented numbers** — a non-`measured` Finding must have `value = None`; never synthesize a figure (charter doctrine Rule 2). Applies to every task.
- **Append-only store** — never mutate or delete a written record; new state is a new versioned entry (charter Part 9).
- **Ratings are judgment, not arithmetic** — code computes *anchors* and *bounds* ratings; it never *sets* a rating (charter Part 17). Applies to the gate and scoring tasks.
- **Pre-merge gate (not a coding task here):** the charter reconciliation (repo Task #9 — additive edits to Parts 2/7/17) must land before this branch merges, so the charter stays the source of truth (spec §11).
- All commands assume the repo root `C:\Users\danie\random_for_fun` and a venv with the package installed editable (`pip install -e .`).

---

### Task 1: Project scaffold + Finding model

**Files:**
- Create: `pyproject.toml`
- Create: `gpu_agent/__init__.py`
- Create: `gpu_agent/schema/__init__.py`
- Create: `gpu_agent/schema/finding.py`
- Test: `tests/test_finding_schema.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `gpu_agent.schema.finding` exporting `Finding`, `Kind`, `Value`, `Impact`, `Evidence`, `Confidence`. `Finding` fields: `id:str, statement:str, kind:Kind, value:Value|None, trend:Literal["rising","falling","flat","unknown"], why:str, impact:Impact, evidence:list[Evidence], reasoning:str|None, confidence:Confidence, dispersion:str|None, asOf:str, indicatorId:str, side:Literal["demand","supply","price","structural"], polarityDemand:Literal[-1,0,1], polaritySupply:Literal[-1,0,1], magnitude:Literal[1,2,3], entity:str, observedAt:str, capturedAt:str, extractionModel:str|None, schemaVersion:str`.

- [ ] **Step 1: Create the package scaffold and install it**

Create `pyproject.toml`:
```toml
[project]
name = "gpu_agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["pydantic>=2,<3"]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["gpu_agent*"]
```
Create empty `gpu_agent/__init__.py` and `gpu_agent/schema/__init__.py`.
Run: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`
Expected: installs pydantic + pytest, `Successfully installed gpu_agent-0.1.0`.

- [ ] **Step 2: Write the failing test**

Create `tests/test_finding_schema.py`:
```python
from gpu_agent.schema.finding import Finding

def test_measured_finding_roundtrips():
    data = {
        "id": "f-001", "statement": "NVIDIA DC revenue growth slope flattened.",
        "kind": "measured", "value": {"number": 8.0, "unit": "% QoQ"},
        "trend": "rising", "why": "Blackwell ramp digesting.",
        "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "slope flattening caps DMI"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "http://x", "date": "2026-05", "excerpt": "...", "tier": "primary"}],
        "reasoning": None,
        "confidence": {"level": "high", "basis": "primary filing"},
        "dispersion": None, "asOf": "2026-06",
        "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12",
        "extractionModel": None, "schemaVersion": "1.0",
    }
    f = Finding.model_validate(data)
    assert f.value.number == 8.0
    assert f.polarityDemand == 1 and f.polaritySupply == 0
    assert Finding.model_validate(f.model_dump()).id == "f-001"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_finding_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.schema.finding'`.

- [ ] **Step 4: Write the Finding model**

Create `gpu_agent/schema/finding.py`:
```python
from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel

class Kind(str, Enum):
    measured = "measured"
    observed = "observed"
    hypothesis = "hypothesis"

class Value(BaseModel):
    number: float
    unit: str

class Impact(BaseModel):
    targets: list[str]
    direction: Literal["positive", "negative", "mixed"]
    mechanism: str

class Evidence(BaseModel):
    source: str
    url: str
    date: str
    excerpt: str
    tier: Literal["primary", "secondary"]

class Confidence(BaseModel):
    level: Literal["low", "medium", "high"]
    basis: str

class Finding(BaseModel):
    id: str
    statement: str
    kind: Kind
    value: Optional[Value] = None
    trend: Literal["rising", "falling", "flat", "unknown"]
    why: str
    impact: Impact
    evidence: list[Evidence] = []
    reasoning: Optional[str] = None
    confidence: Confidence
    dispersion: Optional[str] = None
    asOf: str
    indicatorId: str
    side: Literal["demand", "supply", "price", "structural"]
    polarityDemand: Literal[-1, 0, 1]
    polaritySupply: Literal[-1, 0, 1]
    magnitude: Literal[1, 2, 3]
    entity: str
    observedAt: str
    capturedAt: str
    extractionModel: Optional[str] = None
    schemaVersion: str = "1.0"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_finding_schema.py -v`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml gpu_agent/ tests/test_finding_schema.py
git commit -m "feat: scaffold gpu_agent package + Finding schema"
```

---

### Task 2: Scorecard + DimensionRating models

**Files:**
- Create: `gpu_agent/schema/scorecard.py`
- Test: `tests/test_scorecard_schema.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.finding` (`Finding`, `Confidence`).
- Produces: `gpu_agent.schema.scorecard` exporting `DIMENSIONS` (list[str] of the 6 fixed dimensions), `DimensionRating`, `DemandSupply`, `Scorecard`. `DimensionRating` fields: `rating:Literal["Very strong","Strong","Mixed","Weak","Very weak"], direction:Literal["improving","steady","worsening"], confidence:Confidence, findingIds:list[str], rationale:str`. `DemandSupply` fields: `dmiContribution:float, smiContribution:float, anchors:dict[str,float]`. `Scorecard` fields: `categoryId:str, asOf:str, findings:list[Finding], dimensionRatings:dict[str,DimensionRating], demandSupply:DemandSupply, narrative:str, confidence:Confidence, sources:list[str], provenance:dict[str,str]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scorecard_schema.py`:
```python
from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS

def test_dimensions_are_the_six_fixed_ones():
    assert DIMENSIONS == ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]

def test_minimal_scorecard_roundtrips():
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06", "findings": [],
        "dimensionRatings": {
            "momentum": {"rating": "Strong", "direction": "worsening",
                         "confidence": {"level": "high", "basis": "x"},
                         "findingIds": ["f-001"], "rationale": "slope flattening"}},
        "demandSupply": {"dmiContribution": 0.4, "smiContribution": 0.6, "anchors": {"momentum": 0.4}},
        "narrative": "Strong but softening.", "confidence": {"level": "medium", "basis": "x"},
        "sources": ["NVIDIA 10-Q"], "provenance": {"runId": "r1"},
    }
    sc = Scorecard.model_validate(data)
    assert sc.dimensionRatings["momentum"].rating == "Strong"
    assert sc.demandSupply.smiContribution == 0.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_scorecard_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.schema.scorecard'`.

- [ ] **Step 3: Write the Scorecard models**

Create `gpu_agent/schema/scorecard.py`:
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding, Confidence

DIMENSIONS = ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]

class DimensionRating(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]
    direction: Literal["improving", "steady", "worsening"]
    confidence: Confidence
    findingIds: list[str]
    rationale: str

class DemandSupply(BaseModel):
    dmiContribution: float
    smiContribution: float
    anchors: dict[str, float] = Field(default_factory=dict)

class Scorecard(BaseModel):
    categoryId: str
    asOf: str
    findings: list[Finding] = Field(default_factory=list)
    dimensionRatings: dict[str, DimensionRating] = Field(default_factory=dict)
    demandSupply: DemandSupply
    narrative: str
    confidence: Confidence
    sources: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_scorecard_schema.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/schema/scorecard.py tests/test_scorecard_schema.py
git commit -m "feat: add Scorecard + DimensionRating schema"
```

---

### Task 3: Finding-level validation gate

**Files:**
- Create: `gpu_agent/gate.py`
- Test: `tests/test_gate_finding.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.finding` (`Finding`, `Kind`).
- Produces: `gpu_agent.gate.check_finding(f: Finding) -> list[str]` (returns violation strings; empty list = pass).

- [ ] **Step 1: Write the failing test**

Create `tests/test_gate_finding.py`:
```python
from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding

def _base(**over):
    data = {
        "id": "f", "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "because", "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "secondary"}],
        "reasoning": None, "confidence": {"level": "high", "basis": "b"}, "dispersion": None, "asOf": "2026-06",
        "indicatorId": "S9", "side": "supply", "polarityDemand": -1, "polaritySupply": 1, "magnitude": 2,
        "entity": "AMD", "observedAt": "2026-05", "capturedAt": "2026-06-12", "schemaVersion": "1.0",
    }
    data.update(over)
    return Finding.model_validate(data)

def test_clean_finding_passes():
    assert check_finding(_base()) == []

def test_measured_without_value_fails():
    f = _base(kind="measured", value=None)
    assert any("missing value" in e for e in check_finding(f))

def test_observed_with_value_is_invented_number():
    f = _base(kind="observed", value={"number": 5.0, "unit": "x"})
    assert any("invented value" in e for e in check_finding(f))

def test_empty_why_fails():
    f = _base(why="   ")
    assert any("missing why" in e for e in check_finding(f))

def test_hypothesis_requires_reasoning_and_capped_confidence():
    f = _base(kind="hypothesis", value=None, reasoning=None, confidence={"level": "high", "basis": "b"})
    errs = check_finding(f)
    assert any("missing reasoning" in e for e in errs)
    assert any("confidence capped" in e for e in errs)

def test_finding_affecting_neither_track_fails():
    f = _base(polarityDemand=0, polaritySupply=0)
    assert any("affects neither" in e for e in check_finding(f))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_gate_finding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.gate'`.

- [ ] **Step 3: Write the Finding-level gate**

Create `gpu_agent/gate.py`:
```python
from __future__ import annotations
from gpu_agent.schema.finding import Finding, Kind

def check_finding(f: Finding) -> list[str]:
    errors: list[str] = []
    if f.kind == Kind.measured:
        if f.value is None:
            errors.append(f"{f.id}: measured finding missing value")
        if not f.evidence:
            errors.append(f"{f.id}: measured finding missing evidence")
    else:
        if f.value is not None:
            errors.append(f"{f.id}: non-measured finding has invented value")
    if not f.why.strip():
        errors.append(f"{f.id}: missing why")
    if f.kind == Kind.hypothesis:
        if not f.reasoning:
            errors.append(f"{f.id}: hypothesis missing reasoning")
        if f.confidence.level == "high":
            errors.append(f"{f.id}: hypothesis confidence capped at medium")
    if f.polarityDemand == 0 and f.polaritySupply == 0:
        errors.append(f"{f.id}: finding affects neither demand nor supply track")
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_gate_finding.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/gate.py tests/test_gate_finding.py
git commit -m "feat: add Finding-level pre-commit gate (Part 7)"
```

---

### Task 4: Scoring — z-score anchors + DMI/SMI contribution

**Files:**
- Create: `gpu_agent/scoring.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.finding` (`Finding`).
- Produces:
  - `gpu_agent.scoring.zscore(value: float, history: list[float]) -> float` (population stdev; returns `0.0` when `len(history) < 2` or stdev is 0).
  - `gpu_agent.scoring.dmi_smi_contribution(findings: list[Finding], weights: dict[str, float]) -> tuple[float, float]` where each track = `sum(weights.get(indicatorId, 0.0) * polarity * magnitude / 3)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scoring.py`:
```python
import math
from gpu_agent.scoring import zscore, dmi_smi_contribution
from gpu_agent.schema.finding import Finding

def test_zscore_basic():
    assert zscore(12.0, [10.0, 10.0, 10.0, 10.0]) == 0.0  # stdev 0 -> 0.0
    z = zscore(4.0, [0.0, 2.0, 4.0])  # mean 2, pstdev ~1.633
    assert math.isclose(z, (4.0 - 2.0) / 1.632993, rel_tol=1e-4)

def test_zscore_thin_history_is_zero():
    assert zscore(5.0, [1.0]) == 0.0

def _f(ind, pd, ps, mag):
    return Finding.model_validate({
        "id": ind, "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "secondary"}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
        "indicatorId": ind, "side": "demand", "polarityDemand": pd, "polaritySupply": ps,
        "magnitude": mag, "entity": "E", "observedAt": "2026-05", "capturedAt": "2026-06-12",
    })

def test_dmi_smi_contribution():
    findings = [_f("D2", 1, 0, 3), _f("S9", -1, 1, 3)]
    weights = {"D2": 0.10, "S9": 0.04}
    dmi, smi = dmi_smi_contribution(findings, weights)
    assert math.isclose(dmi, 0.10 * 1 * 1.0 + 0.04 * -1 * 1.0)  # 0.06
    assert math.isclose(smi, 0.04 * 1 * 1.0)                    # 0.04
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.scoring'`.

- [ ] **Step 3: Write the scoring module**

Create `gpu_agent/scoring.py`:
```python
from __future__ import annotations
import statistics
from gpu_agent.schema.finding import Finding

def zscore(value: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    sigma = statistics.pstdev(history)
    if sigma == 0:
        return 0.0
    return (value - statistics.mean(history)) / sigma

def dmi_smi_contribution(findings: list[Finding], weights: dict[str, float]) -> tuple[float, float]:
    dmi = sum(weights.get(f.indicatorId, 0.0) * f.polarityDemand * f.magnitude / 3 for f in findings)
    smi = sum(weights.get(f.indicatorId, 0.0) * f.polaritySupply * f.magnitude / 3 for f in findings)
    return dmi, smi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_scoring.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/scoring.py tests/test_scoring.py
git commit -m "feat: add deterministic scoring (z-score + DMI/SMI contribution)"
```

---

### Task 5: Scorecard-level gate — citations, anchor-consistency, self-reference

**Files:**
- Modify: `gpu_agent/gate.py`
- Test: `tests/test_gate_scorecard.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.scorecard` (`Scorecard`), `gpu_agent.gate.check_finding`.
- Produces: `gpu_agent.gate.check_scorecard(sc: Scorecard) -> list[str]` — runs `check_finding` on every finding, then: every rating cites ≥1 known finding id; no rating contradicts its anchor (`sc.demandSupply.anchors[dim]`): positive ratings (`Very strong`/`Strong`) require anchor `> -0.5`; negative ratings (`Weak`/`Very weak`) require anchor `< 0.5`; `Mixed` always allowed; no finding evidence self-references the dashboard (`source == "AI Market State dashboard"` or `"market-state.json" in url`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_gate_scorecard.py`:
```python
from gpu_agent.gate import check_scorecard
from gpu_agent.schema.scorecard import Scorecard

def _sc(**over):
    data = {
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06",
        "findings": [{
            "id": "f-001", "statement": "s", "kind": "measured", "value": {"number": 8.0, "unit": "%"},
            "trend": "rising", "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
            "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "primary"}],
            "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": "D2",
            "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2,
            "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12",
        }],
        "dimensionRatings": {"momentum": {"rating": "Strong", "direction": "worsening",
            "confidence": {"level": "high", "basis": "b"}, "findingIds": ["f-001"], "rationale": "r"}},
        "demandSupply": {"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": 0.4}},
        "narrative": "n", "confidence": {"level": "medium", "basis": "b"}, "sources": ["NVIDIA 10-Q"], "provenance": {},
    }
    data.update(over)
    return Scorecard.model_validate(data)

def test_clean_scorecard_passes():
    assert check_scorecard(_sc()) == []

def test_rating_with_no_citations_fails():
    sc = _sc(dimensionRatings={"momentum": {"rating": "Strong", "direction": "steady",
        "confidence": {"level": "high", "basis": "b"}, "findingIds": [], "rationale": "r"}})
    assert any("cites no findings" in e for e in check_scorecard(sc))

def test_rating_contradicting_anchor_fails():
    # "Very strong" momentum while the anchor z-score is deeply negative
    sc = _sc(dimensionRatings={"momentum": {"rating": "Very strong", "direction": "steady",
        "confidence": {"level": "high", "basis": "b"}, "findingIds": ["f-001"], "rationale": "r"}},
        demandSupply={"dmiContribution": 0.1, "smiContribution": 0.0, "anchors": {"momentum": -1.8}})
    assert any("contradicts anchor" in e for e in check_scorecard(sc))

def test_self_reference_fails():
    sc = _sc()
    sc.findings[0].evidence[0].source = "AI Market State dashboard"
    assert any("self-reference" in e for e in check_scorecard(sc))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_gate_scorecard.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_scorecard'`.

- [ ] **Step 3: Add the scorecard-level gate**

Append to `gpu_agent/gate.py`:
```python
from gpu_agent.schema.scorecard import Scorecard

_POSITIVE = {"Very strong", "Strong"}
_NEGATIVE = {"Weak", "Very weak"}

def _rating_consistent_with_anchor(rating: str, anchor: float) -> bool:
    if rating in _POSITIVE:
        return anchor > -0.5
    if rating in _NEGATIVE:
        return anchor < 0.5
    return True  # "Mixed" is always allowed

def check_scorecard(sc: Scorecard) -> list[str]:
    errors: list[str] = []
    for f in sc.findings:
        errors.extend(check_finding(f))
    known = {f.id for f in sc.findings}
    for dim, r in sc.dimensionRatings.items():
        if not r.findingIds:
            errors.append(f"{dim}: rating cites no findings")
        for fid in r.findingIds:
            if fid not in known:
                errors.append(f"{dim}: cites unknown finding {fid}")
        anchor = sc.demandSupply.anchors.get(dim)
        if anchor is not None and not _rating_consistent_with_anchor(r.rating, anchor):
            errors.append(f"{dim}: rating {r.rating} contradicts anchor z={anchor:.2f}")
    for f in sc.findings:
        for e in f.evidence:
            if e.source == "AI Market State dashboard" or "market-state.json" in e.url:
                errors.append(f"{f.id}: evidence self-references the dashboard output")
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_gate_scorecard.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/gate.py tests/test_gate_scorecard.py
git commit -m "feat: add scorecard gate (citations, anchor-consistency, self-reference)"
```

---

### Task 6: Append-only JSON store

**Files:**
- Create: `gpu_agent/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.scorecard` (`Scorecard`).
- Produces: `gpu_agent.store.JsonStore(root: pathlib.Path)` with `append(sc: Scorecard) -> pathlib.Path` (writes `<root>/<categoryId>/<asOf>-v<N>.json`, N = next integer, never overwriting) and `versions(category_id: str, as_of: str) -> list[pathlib.Path]` (sorted).

- [ ] **Step 1: Write the failing test**

Create `tests/test_store.py`:
```python
from gpu_agent.store import JsonStore
from gpu_agent.schema.scorecard import Scorecard

def _sc():
    return Scorecard.model_validate({
        "categoryId": "chips.merchant-gpu", "asOf": "2026-06", "findings": [],
        "dimensionRatings": {}, "demandSupply": {"dmiContribution": 0.0, "smiContribution": 0.0, "anchors": {}},
        "narrative": "n", "confidence": {"level": "low", "basis": "b"}, "sources": [], "provenance": {}})

def test_append_is_versioned_and_non_destructive(tmp_path):
    store = JsonStore(tmp_path)
    p1 = store.append(_sc())
    p2 = store.append(_sc())
    assert p1 != p2
    assert p1.name == "2026-06-v1.json" and p2.name == "2026-06-v2.json"
    assert len(store.versions("chips.merchant-gpu", "2026-06")) == 2
    assert p1.exists() and p2.exists()  # first not overwritten
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.store'`.

- [ ] **Step 3: Write the store**

Create `gpu_agent/store.py`:
```python
from __future__ import annotations
import pathlib
from gpu_agent.schema.scorecard import Scorecard

class JsonStore:
    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)

    def versions(self, category_id: str, as_of: str) -> list[pathlib.Path]:
        d = self.root / category_id
        if not d.exists():
            return []
        return sorted(d.glob(f"{as_of}-v*.json"))

    def append(self, sc: Scorecard) -> pathlib.Path:
        d = self.root / sc.categoryId
        d.mkdir(parents=True, exist_ok=True)
        n = len(self.versions(sc.categoryId, sc.asOf)) + 1
        path = d / f"{sc.asOf}-v{n}.json"
        path.write_text(sc.model_dump_json(indent=2), encoding="utf-8")
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_store.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/store.py tests/test_store.py
git commit -m "feat: add append-only versioned JSON store"
```

---

### Task 7: Assignment loader

**Files:**
- Create: `gpu_agent/assignment.py`
- Create: `fixtures/asg.chips.merchant-gpu.json`
- Test: `tests/test_assignment.py`

**Interfaces:**
- Consumes: nothing internal.
- Produces: `gpu_agent.assignment.Assignment` (Pydantic) with fields `id:str, template:str, mode:str, entities:list[str], metrics:list[str], weights:dict[str,float], version:str, asOf:str`, and `gpu_agent.assignment.load_assignment(path) -> Assignment`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_assignment.py`:
```python
from gpu_agent.assignment import load_assignment

def test_loads_gpu_assignment():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    assert a.id == "asg.chips.merchant-gpu"
    assert "nvidia" in a.entities and "amd" in a.entities and "intel" in a.entities
    assert a.weights["D2"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_assignment.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.assignment'`.

- [ ] **Step 3: Write the loader and the fixture**

Create `gpu_agent/assignment.py`:
```python
from __future__ import annotations
import json, pathlib
from pydantic import BaseModel, Field

class Assignment(BaseModel):
    id: str
    template: str
    mode: str
    entities: list[str]
    metrics: list[str]
    weights: dict[str, float] = Field(default_factory=dict)
    version: str
    asOf: str

def load_assignment(path) -> Assignment:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return Assignment.model_validate(data)
```

Create `fixtures/asg.chips.merchant-gpu.json`:
```json
{
  "id": "asg.chips.merchant-gpu", "template": "category", "mode": "canonical",
  "entities": ["nvidia", "amd", "intel"],
  "metrics": ["D2", "D6", "S9", "S10", "market-share-pct", "perfPerWatt", "flopsPerDollar", "grossMargin"],
  "weights": {"D2": 0.10, "D6": 0.12, "S9": 0.04, "S10": 0.08},
  "version": "1.0", "asOf": "2026-06"
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_assignment.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/assignment.py fixtures/asg.chips.merchant-gpu.json tests/test_assignment.py
git commit -m "feat: add assignment loader + merchant-gpu assignment fixture"
```

---

### Task 8: Pipeline assembler + CLI

**Files:**
- Create: `gpu_agent/pipeline.py`
- Create: `gpu_agent/cli.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `assignment.Assignment`, `scoring.dmi_smi_contribution`, `gate.check_scorecard`, `schema.scorecard.Scorecard`, `store.JsonStore`.
- Produces: `gpu_agent.pipeline.build_scorecard(findings: list[Finding], ratings: dict[str, DimensionRating], anchors: dict[str, float], assignment: Assignment, narrative: str, confidence: Confidence) -> Scorecard` — computes DMI/SMI via `dmi_smi_contribution(findings, assignment.weights)`, assembles the Scorecard, runs `check_scorecard`, and raises `GateError` (new, in `gate.py`) listing violations if any. `gpu_agent.cli.main(argv) -> int`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline.py`:
```python
import pytest
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating

def _finding():
    return Finding.model_validate({
        "id": "f-001", "statement": "s", "kind": "measured", "value": {"number": 8.0, "unit": "%"},
        "trend": "rising", "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "NVIDIA 10-Q", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": "D2",
        "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 3,
        "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12"})

def _rating(fids):
    return DimensionRating(rating="Strong", direction="worsening",
        confidence=Confidence(level="high", basis="b"), findingIds=fids, rationale="r")

def test_build_scorecard_computes_dmi_and_passes_gate():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "Strong but softening.", Confidence(level="medium", basis="b"))
    assert sc.demandSupply.dmiContribution == pytest.approx(0.10 * 1 * 3 / 3)  # 0.10
    assert sc.dimensionRatings["momentum"].rating == "Strong"

def test_build_scorecard_raises_on_anchor_contradiction():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    bad = DimensionRating(rating="Very strong", direction="steady",
        confidence=Confidence(level="high", basis="b"), findingIds=["f-001"], rationale="r")
    with pytest.raises(GateError):
        build_scorecard([_finding()], {"momentum": bad}, {"momentum": -1.8},
                        a, "n", Confidence(level="low", basis="b"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.pipeline'`.

- [ ] **Step 3: Add `GateError`, the pipeline, and the CLI**

Append to `gpu_agent/gate.py`:
```python
class GateError(Exception):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))
```

Create `gpu_agent/pipeline.py`:
```python
from __future__ import annotations
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import Scorecard, DimensionRating, DemandSupply
from gpu_agent.assignment import Assignment
from gpu_agent.scoring import dmi_smi_contribution
from gpu_agent.gate import check_scorecard, GateError

def build_scorecard(findings: list[Finding], ratings: dict[str, DimensionRating],
                    anchors: dict[str, float], assignment: Assignment,
                    narrative: str, confidence: Confidence) -> Scorecard:
    dmi, smi = dmi_smi_contribution(findings, assignment.weights)
    sc = Scorecard(
        categoryId="chips.merchant-gpu", asOf=assignment.asOf, findings=findings,
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

Create `gpu_agent/cli.py`:
```python
from __future__ import annotations
import argparse, json, pathlib, sys
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.store import JsonStore

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gpu-agent")
    p.add_argument("--assignment", required=True)
    p.add_argument("--fixtures", required=True, help="dir with findings.json, ratings.json, anchors.json")
    p.add_argument("--out", default="store")
    args = p.parse_args(argv)
    a = load_assignment(args.assignment)
    fx = pathlib.Path(args.fixtures)
    findings = [Finding.model_validate(d) for d in json.loads((fx / "findings.json").read_text("utf-8"))]
    ratings = {k: DimensionRating.model_validate(v)
               for k, v in json.loads((fx / "ratings.json").read_text("utf-8")).items()}
    anchors = json.loads((fx / "anchors.json").read_text("utf-8"))
    try:
        sc = build_scorecard(findings, ratings, anchors, a, "MVP scorecard.",
                             Confidence(level="medium", basis="fixture run"))
    except GateError as e:
        print("GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
        return 1
    path = JsonStore(pathlib.Path(args.out)).append(sc)
    print(f"wrote {path}  DMI={sc.demandSupply.dmiContribution:.3f} SMI={sc.demandSupply.smiContribution:.3f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pipeline.py gpu_agent/cli.py gpu_agent/gate.py tests/test_pipeline.py
git commit -m "feat: add scorecard pipeline assembler + CLI"
```

---

### Task 9: Golden-set integration test (NVIDIA/AMD/Intel)

**Files:**
- Create: `fixtures/golden/findings.json`
- Create: `fixtures/golden/ratings.json`
- Create: `fixtures/golden/anchors.json`
- Create: `fixtures/golden/scorecard.json` (the expected golden output, minus volatile provenance)
- Test: `tests/test_golden_integration.py`

**Interfaces:**
- Consumes: `gpu_agent.cli.main`, `gpu_agent.store.JsonStore`, all prior modules.
- Produces: nothing (terminal acceptance test).

- [ ] **Step 1: Write the failing test**

Create `tests/test_golden_integration.py`:
```python
import json, pathlib
from gpu_agent.cli import main

def test_cli_produces_golden_scorecard(tmp_path):
    rc = main(["--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--fixtures", "fixtures/golden", "--out", str(tmp_path)])
    assert rc == 0
    written = sorted((tmp_path / "chips.merchant-gpu").glob("*.json"))[0]
    got = json.loads(written.read_text("utf-8"))
    golden = json.loads(pathlib.Path("fixtures/golden/scorecard.json").read_text("utf-8"))
    got.pop("provenance", None)
    assert got["demandSupply"] == golden["demandSupply"]
    assert {f["entity"] for f in got["findings"]} == {"NVDA", "AMD", "INTC"}
    assert set(got["dimensionRatings"].keys()) >= {"momentum", "competitiveStructure", "moat"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_golden_integration.py -v`
Expected: FAIL — fixtures not found / `FileNotFoundError: fixtures/golden/findings.json`.

- [ ] **Step 3: Author the golden fixtures**

Create `fixtures/golden/findings.json` — a JSON array of ≥4 Findings covering all three entities and both tracks. Each must be a valid `Finding` (see Task 1 shape). Include at minimum:
- NVDA D2 (demand, `polarityDemand:1, polaritySupply:0, magnitude:2`, `value` set, primary evidence);
- one S9 (supply, `polarityDemand:-1, polaritySupply:1, magnitude:2`, entity `AMD`, measured share, secondary evidence, `dispersion` set);
- one moat finding (observed, `value:null`, entity `NVDA`, `polarityDemand:0, polaritySupply:1` or `1,0`);
- one INTC finding (observed or measured) so all three entities appear.

```json
[
  {"id": "f-nvda-d2", "statement": "NVIDIA DC revenue growth slope flattened; concentration eased.",
   "kind": "measured", "value": {"number": 8.0, "unit": "% QoQ"}, "trend": "rising", "why": "Blackwell digestion.",
   "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "slope flattening caps DMI"},
   "evidence": [{"source": "NVIDIA 10-Q", "url": "http://sec/nvda", "date": "2026-05", "excerpt": "...", "tier": "primary"}],
   "confidence": {"level": "high", "basis": "primary filing"}, "asOf": "2026-06", "indicatorId": "D2",
   "side": "demand", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 2, "entity": "NVDA",
   "observedAt": "2026-05", "capturedAt": "2026-06-12"},
  {"id": "f-amd-s9", "statement": "AMD MI400 + custom ASICs erode NVIDIA share toward ~75%.",
   "kind": "measured", "value": {"number": 75.0, "unit": "% accelerator share"}, "trend": "falling",
   "why": "Hyperscalers internalize silicon.",
   "impact": {"targets": ["chips.merchant-gpu"], "direction": "mixed", "mechanism": "adds supply, erodes merchant demand"},
   "evidence": [{"source": "SemiAnalysis", "url": "http://sa", "date": "2026-04", "excerpt": "...", "tier": "secondary"}],
   "confidence": {"level": "medium", "basis": "secondary estimates"}, "dispersion": "73-78% across trackers",
   "asOf": "2026-06", "indicatorId": "S9", "side": "supply", "polarityDemand": -1, "polaritySupply": 1,
   "magnitude": 2, "entity": "AMD", "observedAt": "2026-04", "capturedAt": "2026-06-12"},
  {"id": "f-nvda-moat", "statement": "CUDA lock-in remains the dominant switching barrier.",
   "kind": "observed", "value": null, "trend": "flat", "why": "Accumulated tooling raises migration cost.",
   "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive", "mechanism": "protects pricing power"},
   "evidence": [{"source": "dev survey", "url": "http://dev", "date": "2026-05", "excerpt": "...", "tier": "secondary"}],
   "confidence": {"level": "high", "basis": "consistent coverage"}, "asOf": "2026-06", "indicatorId": "market-share-pct",
   "side": "structural", "polarityDemand": 1, "polaritySupply": 0, "magnitude": 1, "entity": "NVDA",
   "observedAt": "2026-05", "capturedAt": "2026-06-12"},
  {"id": "f-intc-s10", "statement": "Intel Gaudi channel inventory days are creeping up.",
   "kind": "measured", "value": {"number": 95.0, "unit": "days"}, "trend": "rising", "why": "Soft sell-through.",
   "impact": {"targets": ["chips.merchant-gpu"], "direction": "negative", "mechanism": "inventory build = glut tell"},
   "evidence": [{"source": "Intel 10-Q", "url": "http://sec/intc", "date": "2026-05", "excerpt": "...", "tier": "primary"}],
   "confidence": {"level": "medium", "basis": "filing"}, "asOf": "2026-06", "indicatorId": "S10",
   "side": "supply", "polarityDemand": 0, "polaritySupply": 1, "magnitude": 1, "entity": "INTC",
   "observedAt": "2026-05", "capturedAt": "2026-06-12"}
]
```

Create `fixtures/golden/anchors.json`:
```json
{"momentum": 0.4, "competitiveStructure": -0.3, "moat": 0.8}
```

Create `fixtures/golden/ratings.json` (ratings consistent with the anchors — none contradict):
```json
{
  "momentum": {"rating": "Strong", "direction": "worsening", "confidence": {"level": "high", "basis": "D2 slope"}, "findingIds": ["f-nvda-d2"], "rationale": "growing but flattening"},
  "competitiveStructure": {"rating": "Mixed", "direction": "worsening", "confidence": {"level": "medium", "basis": "share erosion"}, "findingIds": ["f-amd-s9"], "rationale": "share eroding to ~75%"},
  "moat": {"rating": "Strong", "direction": "steady", "confidence": {"level": "high", "basis": "CUDA"}, "findingIds": ["f-nvda-moat"], "rationale": "CUDA intact"},
  "bottleneck": {"rating": "Strong", "direction": "steady", "confidence": {"level": "medium", "basis": "upstream packaging"}, "findingIds": ["f-amd-s9"], "rationale": "gated upstream by CoWoS"},
  "strategicRisk": {"rating": "Mixed", "direction": "worsening", "confidence": {"level": "medium", "basis": "substitution"}, "findingIds": ["f-amd-s9", "f-intc-s10"], "rationale": "substitution + inventory"},
  "unitEconomics": {"rating": "Very strong", "direction": "steady", "confidence": {"level": "high", "basis": "margins"}, "findingIds": ["f-nvda-d2"], "rationale": "~70%+ gross margin"}
}
```

Compute the expected DMI/SMI by hand from the weights (`D2:0.10, S9:0.04, S10:0.08`) and `polarity*magnitude/3`:
- DMI = `0.10*1*2/3` (f-nvda-d2) + `0.04*-1*2/3` (f-amd-s9) + `0*...` = `0.0667 - 0.0267 = 0.0400`.
- SMI = `0.04*1*2/3` (f-amd-s9) + `0.08*1*1/3` (f-intc-s10) = `0.0267 + 0.0267 = 0.0533`.

Create `fixtures/golden/scorecard.json` (only the asserted slice):
```json
{"demandSupply": {"dmiContribution": 0.04, "smiContribution": 0.05333333333333333, "anchors": {"momentum": 0.4, "competitiveStructure": -0.3, "moat": 0.8}}}
```

> Note: if the computed float differs in trailing digits, set the golden value to the exact value the code emits (run the CLI once, copy the printed/written number). The test asserts equality on the `demandSupply` block.

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_golden_integration.py -v`
Expected: PASS (1 passed). If the float mismatches, reconcile `scorecard.json` to the emitted value and re-run.

- [ ] **Step 5: Run the full suite + the CLI smoke**

Run: `.venv/Scripts/python -m pytest -v`
Expected: all tests pass (Tasks 1–9).
Run: `.venv/Scripts/python -m gpu_agent.cli --assignment fixtures/asg.chips.merchant-gpu.json --fixtures fixtures/golden --out store`
Expected: prints `wrote store/chips.merchant-gpu/2026-06-v1.json  DMI=0.040 SMI=0.053`.

- [ ] **Step 6: Commit**

```bash
git add fixtures/golden tests/test_golden_integration.py
git commit -m "test: add golden-set integration test for GPU core (NVDA/AMD/INTC)"
```

---

## Self-Review

**1. Spec coverage:**
- §2 constituents NVIDIA/AMD/Intel → Task 7 fixture + Task 9 golden findings. ✓
- §2 indicators D2/D6/S9/S10 + measured/qual metrics → Task 7 weights + Task 9 findings (D2, S9, S10, market-share-pct moat). *D6 has weight but no golden finding* — acceptable for MVP (D6 exercised via weights map; add a D6 finding if desired). ✓ (noted)
- §3 success criteria (gate pass, finding coverage, deterministic DMI/SMI, golden match) → Tasks 3/5/8/9. ✓
- §4 modules → Tasks 1–8 map 1:1. ✓
- §5 grounded judgment + anchor-consistency → Task 5 `_rating_consistent_with_anchor` + Task 8 raises on contradiction. ✓
- §6 schemas + gate rules → Tasks 1/2/3/5. ✓
- §8 bend-don't-break: a missing anchor is tolerated (anchor `None` → rule skipped, Task 5). Missing-metric confidence-capping is **not** in the core MVP (it belongs to the judgment adapter) — out of this plan's scope per §7. ✓ (noted)
- §9 testing (golden set, unit per rule, integration) → Tasks 3/5/9. ✓
- §11 charter reconciliation → Global Constraints pre-merge gate (not a coding task). ✓

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; commands have expected output. ✓

**3. Type consistency:** `check_finding`/`check_scorecard`/`GateError` (gate.py); `zscore`/`dmi_smi_contribution` (scoring.py); `build_scorecard` signature consumed identically in Task 8 test, impl, and CLI; `DimensionRating`/`DemandSupply`/`Scorecard`/`Finding` field names consistent across Tasks 1/2/5/8/9. `dmi_smi_contribution` formula (`weight*polarity*magnitude/3`) identical in Task 4 and the Task 9 hand-computation. ✓

Two scope notes surfaced (D6 finding optional in golden; missing-metric confidence-capping deferred to the judgment adapter) — both consistent with the spec's §7 core/adapter split, no task gap.

---

## Out of scope for this plan (follow-on)
The **judgment** adapter (LLM forms ratings + self-consistency sampling), the **extraction** adapter (RawDocument → Findings), and the **connectors** (EDGAR, GPU-rental) — planned separately once this core interface is frozen (spec §7).
