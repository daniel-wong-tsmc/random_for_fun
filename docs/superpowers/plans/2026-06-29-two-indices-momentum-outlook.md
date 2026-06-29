# Two indices — Momentum vs Outlook (sub-project 4-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two horizon-split indices to the scorecard — trailing **Momentum** (lagging+coincident) and forward **Outlook** (leading), each with demand/supply tracks + SDGI — plus a deterministic cross-sectional **divergence** verdict, all computed in code from gated findings and all additive (the frozen scoring/gate are byte-unchanged).

**Architecture:** In `build_scorecard`, partition the cycle's findings into a Momentum bucket (`lagging`+`coincident`) and an Outlook bucket (`leading`) using the 4-2 `IndicatorHorizons` accessor, then call the **frozen** `dmi_smi_contribution` on each bucket (same `assignment.weights`). Each bucket yields a `DemandSupply`; a pure `_divergence` helper compares their SDGI directions into a four-state verdict. The result is attached as a new optional `Scorecard.indices`. Because each indicator has exactly one horizon tag and `dmi_smi_contribution` is an additive sum over indicators, `demandSupply == momentum + outlook` exactly.

**Tech Stack:** Python 3.11+, Pydantic v2 (only runtime dependency), pytest. No new dependency.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset on Windows — prefix every command with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`.
- **Truly frozen — byte-unchanged:** `gpu_agent/scoring.py` (incl. `dmi_smi_contribution`, `zscore`), `gpu_agent/gate.py`, `gpu_agent/registry/indicators.py`, `gpu_agent/registry/validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names (`momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`), the rating scale, `pipeline.py`'s Part-7 gate behavior (the `check_scorecard` call). **Additive only** (Part 33): new optional `Scorecard.indices` field + `MarketIndices`/`Divergence` models; new private helpers in `pipeline.py`; `build_scorecard` gains an optional `horizons=` kwarg; `cli.py` passes horizons at its two `build_scorecard` call sites.
- **Reuse, do not rebuild:** the frozen `dmi_smi_contribution`; B's `DemandSupply` model + `_sdgi_direction` helper; 4-2's `IndicatorHorizons` (`gpu_agent/registry/horizon.py`).
- **No invented values (Part 17):** the indices are sums over gated findings via the frozen function; the agent sets none of them. Price/structural/non-scoring indicators stay auto-excluded (inside `dmi_smi_contribution`).
- **Honest coverage (Part 29):** with `< 1` contributing leading finding, divergence is `insufficient-coverage` with a logged `note` — never a fabricated forward signal. Counts are of **scoring** (contributing) findings only.
- **Committed fixtures byte-unchanged:** do NOT edit any file under `fixtures/` (esp. `fixtures/golden/scorecard.json`). `indices` is optional, so the committed fixtures remain valid without it.
- **Determinism:** no wall-clock; the same findings always yield the same indices.
- **The full suite stays green after every task.** Baseline: **268 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Frozen-file guard:** while on the feature branch (before merge), `git diff --stat main -- <frozen files>` must print nothing (the branch base `main` stays put until the final merge).
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gpu_agent/schema/scorecard.py` | Scorecard data model | Modify: add `Divergence`, `MarketIndices`; add optional `Scorecard.indices` |
| `gpu_agent/pipeline.py` | Scorecard assembly + the new computation | Modify: add `_DIR_RANK`, `_contributes`, `_partition_by_horizon`, `_index_for`, `_divergence`; wire into `build_scorecard` via an optional `horizons=` kwarg |
| `gpu_agent/cli.py` | Real entry points | Modify: load `IndicatorHorizons` and pass it at the two `build_scorecard` call sites |
| `tests/test_scorecard_indices.py` | New schema models | Create |
| `tests/test_divergence.py` | The `_divergence` helper (pure) | Create |
| `tests/test_pipeline.py` | partition + index wiring in `build_scorecard` | Extend |
| `tests/test_golden_integration.py` | cli run populates indices on the golden fixture | Extend |

---

### Task 1: Schema — `Divergence`, `MarketIndices`, `Scorecard.indices`

**Files:**
- Modify: `gpu_agent/schema/scorecard.py` (add two models + one optional field)
- Test: `tests/test_scorecard_indices.py`

**Interfaces:**
- Consumes: existing `DemandSupply` (in the same module).
- Produces:
  - `class Divergence(BaseModel)`: `state: Literal["aligned","diverging-weakening","diverging-strengthening","insufficient-coverage"]`, `sdgiGap: float`, `outlookFindingCount: int`, `momentumFindingCount: int`, `note: str = ""`.
  - `class MarketIndices(BaseModel)`: `momentum: DemandSupply`, `outlook: DemandSupply`, `divergence: Divergence`.
  - `Scorecard.indices: Optional[MarketIndices] = None`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scorecard_indices.py`:

```python
import pytest
from gpu_agent.schema.scorecard import (
    Divergence, MarketIndices, DemandSupply, Scorecard, DemandSupply as DS)
from gpu_agent.schema.finding import Confidence


def _ds(dmi, smi, sdgi, direction):
    return DemandSupply(dmiContribution=dmi, smiContribution=smi, sdgi=sdgi, sdgiDirection=direction)


def test_divergence_model_roundtrips():
    d = Divergence(state="diverging-weakening", sdgiGap=-0.2,
                   outlookFindingCount=2, momentumFindingCount=5, note="")
    assert d.state == "diverging-weakening" and d.sdgiGap == -0.2
    assert d.outlookFindingCount == 2 and d.momentumFindingCount == 5


def test_divergence_rejects_unknown_state():
    with pytest.raises(Exception):  # pydantic ValidationError
        Divergence(state="exploding", sdgiGap=0.0, outlookFindingCount=0, momentumFindingCount=0)


def test_market_indices_holds_two_demandsupply_and_a_divergence():
    mi = MarketIndices(
        momentum=_ds(0.07, 0.05, 0.02, "balanced"),
        outlook=_ds(0.0, 0.0, 0.0, "balanced"),
        divergence=Divergence(state="insufficient-coverage", sdgiGap=-0.02,
                              outlookFindingCount=0, momentumFindingCount=4,
                              note="no leading findings; Outlook deferred to 4-4"))
    assert mi.momentum.dmiContribution == 0.07
    assert mi.divergence.state == "insufficient-coverage"


def test_scorecard_indices_defaults_none():
    sc = Scorecard(
        categoryId="chips.merchant-gpu", asOf="2026-06",
        demandSupply=_ds(0.0, 0.0, 0.0, "balanced"),
        narrative="n", confidence=Confidence(level="medium", basis="b"))
    assert sc.indices is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_scorecard_indices.py -q`
Expected: FAIL with `ImportError: cannot import name 'Divergence'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/schema/scorecard.py`, add these two models immediately after the existing `DemandSupply` class:

```python
class Divergence(BaseModel):
    state: Literal["aligned", "diverging-weakening", "diverging-strengthening", "insufficient-coverage"]
    sdgiGap: float
    outlookFindingCount: int
    momentumFindingCount: int
    note: str = ""

class MarketIndices(BaseModel):
    momentum: DemandSupply       # lagging + coincident
    outlook: DemandSupply        # leading
    divergence: Divergence
```

Then add this field to the `Scorecard` model (after the `categoryStatus` field):

```python
    indices: Optional[MarketIndices] = None
```

(`Literal` and `Optional` are already imported at the top of the file.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_scorecard_indices.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 272 passed, 3 skipped (268 baseline + 4 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/schema/scorecard.py tests/test_scorecard_indices.py && git commit -m "feat(4-3): Scorecard.indices schema — MarketIndices + Divergence (additive, optional)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: The `_divergence` helper (pure, deterministic)

**Files:**
- Modify: `gpu_agent/pipeline.py` (add `_DIR_RANK` + `_divergence`)
- Test: `tests/test_divergence.py`

**Interfaces:**
- Consumes: `DemandSupply` (has `.sdgi: Optional[float]`, `.sdgiDirection: Optional[str]`), `Divergence` (Task 1).
- Produces: `def _divergence(momentum: DemandSupply, outlook: DemandSupply, mom_count: int, out_count: int, *, floor: int = 1) -> Divergence`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_divergence.py`:

```python
from gpu_agent.pipeline import _divergence
from gpu_agent.schema.scorecard import DemandSupply


def _ds(sdgi, direction):
    return DemandSupply(dmiContribution=0.0, smiContribution=0.0, sdgi=sdgi, sdgiDirection=direction)


def test_insufficient_coverage_when_outlook_below_floor():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.0, "balanced"), mom_count=4, out_count=0)
    assert d.state == "insufficient-coverage"
    assert "Outlook" in d.note and d.outlookFindingCount == 0


def test_aligned_when_directions_match():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.1, "demand-led"), mom_count=4, out_count=2)
    assert d.state == "aligned"


def test_diverging_weakening_when_outlook_more_supply_led():
    d = _divergence(_ds(0.3, "demand-led"), _ds(-0.1, "supply-led"), mom_count=4, out_count=2)
    assert d.state == "diverging-weakening"


def test_diverging_strengthening_when_outlook_more_demand_led():
    d = _divergence(_ds(-0.2, "supply-led"), _ds(0.2, "demand-led"), mom_count=4, out_count=2)
    assert d.state == "diverging-strengthening"


def test_sdgi_gap_is_outlook_minus_momentum():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.1, "demand-led"), mom_count=4, out_count=2)
    assert abs(d.sdgiGap - (0.1 - 0.3)) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_divergence.py -q`
Expected: FAIL with `ImportError: cannot import name '_divergence'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/pipeline.py`, update the scorecard import to include the new models and add the helper. Change the existing import line

```python
from gpu_agent.schema.scorecard import (
    Scorecard, DimensionRating, DemandSupply, DimensionStatus, CategoryStatus, DIMENSIONS)
```

to

```python
from gpu_agent.schema.scorecard import (
    Scorecard, DimensionRating, DemandSupply, DimensionStatus, CategoryStatus, DIMENSIONS,
    MarketIndices, Divergence)
```

Then add, immediately after the existing `_sdgi_direction` function:

```python
# direction rank from a demand perspective: demand-led is the "strongest forward" lean
_DIR_RANK = {"demand-led": 1, "balanced": 0, "supply-led": -1}

def _divergence(momentum: DemandSupply, outlook: DemandSupply,
                mom_count: int, out_count: int, *, floor: int = 1) -> Divergence:
    gap = (outlook.sdgi or 0.0) - (momentum.sdgi or 0.0)
    if out_count < floor:
        state, note = "insufficient-coverage", "no leading findings; Outlook deferred to 4-4"
    elif outlook.sdgiDirection == momentum.sdgiDirection:
        state, note = "aligned", ""
    elif _DIR_RANK[outlook.sdgiDirection] < _DIR_RANK[momentum.sdgiDirection]:
        state, note = "diverging-weakening", ""
    else:
        state, note = "diverging-strengthening", ""
    return Divergence(state=state, sdgiGap=gap, outlookFindingCount=out_count,
                      momentumFindingCount=mom_count, note=note)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_divergence.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 277 passed, 3 skipped (272 + 5 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/pipeline.py tests/test_divergence.py && git commit -m "feat(4-3): _divergence — deterministic cross-sectional Momentum-vs-Outlook verdict

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Partition by horizon + compute the indices in `build_scorecard`

**Files:**
- Modify: `gpu_agent/pipeline.py` (add `_contributes`, `_partition_by_horizon`, `_index_for`; wire into `build_scorecard` via an optional `horizons=` kwarg)
- Test: `tests/test_pipeline.py` (extend)

**Interfaces:**
- Consumes: `dmi_smi_contribution` (frozen), `_sdgi_direction` + `_divergence` (Task 2), `IndicatorHorizons` (4-2), `IndicatorRegistry` (`.resolve`), `Finding`, `DemandSupply`, `MarketIndices`.
- Produces:
  - `def _contributes(spec) -> bool` (True iff `spec.scoring and spec.side not in ("price","structural")`).
  - `def _partition_by_horizon(findings, horizons) -> tuple[list[Finding], list[Finding]]` (returns `(momentum_findings, outlook_findings)`; `leading` → outlook, else momentum; calls `horizons.horizon(id)` which fails loud on an untagged indicator).
  - `def _index_for(findings, registry, category, weights) -> tuple[DemandSupply, int]` (returns the index + the contributing-finding count).
  - `build_scorecard(..., *, category_status=None, horizons: IndicatorHorizons | None = None)` — when `horizons` is provided, attaches `Scorecard.indices`; when `None`, leaves it `None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pipeline.py` (the file already defines `_finding()` with `indicatorId="D2"` and `_rating()`; add imports at the top of the file: `from gpu_agent.pipeline import _partition_by_horizon` and `from gpu_agent.registry.horizon import IndicatorHorizons`):

```python
def _leading_finding(fid="f-lead", indicator="rpoBacklog", pd=1, ps=0, mag=3):
    return Finding.model_validate({
        "id": fid, "statement": "s", "kind": "measured", "value": None, "trend": "rising",
        "why": "w", "impact": {"targets": ["x"], "direction": "mixed", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05", "excerpt": "e", "tier": "primary"}],
        "confidence": {"level": "high", "basis": "b"}, "asOf": "2026-06", "indicatorId": indicator,
        "side": "demand", "polarityDemand": pd, "polaritySupply": ps, "magnitude": mag,
        "entity": "NVDA", "observedAt": "2026-05", "capturedAt": "2026-06-12"})


def test_partition_by_horizon_buckets_leading_vs_rest():
    hz = IndicatorHorizons.load("registry/indicators.json")
    mom, out = _partition_by_horizon([_finding(), _leading_finding()], hz)  # D2=lagging, rpoBacklog=leading
    assert [f.indicatorId for f in mom] == ["D2"]
    assert [f.indicatorId for f in out] == ["rpoBacklog"]


def test_build_scorecard_without_horizons_leaves_indices_none():
    reg = IndicatorRegistry.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg)
    assert sc.indices is None


def test_build_scorecard_computes_indices_and_invariant():
    reg = IndicatorRegistry.load("registry/indicators.json")
    hz = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    findings = [_finding(), _leading_finding()]  # D2 (lagging, demand) + rpoBacklog (leading, demand)
    sc = build_scorecard(findings, {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg, horizons=hz)
    assert sc.indices is not None
    # additive invariant: blended == momentum + outlook
    assert abs(sc.demandSupply.dmiContribution
               - (sc.indices.momentum.dmiContribution + sc.indices.outlook.dmiContribution)) < 1e-9
    assert abs(sc.demandSupply.smiContribution
               - (sc.indices.momentum.smiContribution + sc.indices.outlook.smiContribution)) < 1e-9
    # the leading finding lands in Outlook (nonzero demand push), Momentum has the D2 finding
    assert sc.indices.outlook.dmiContribution > 0.0
    assert sc.indices.divergence.outlookFindingCount == 1
    assert sc.indices.divergence.momentumFindingCount == 1


def test_build_scorecard_insufficient_coverage_without_leading():
    reg = IndicatorRegistry.load("registry/indicators.json")
    hz = IndicatorHorizons.load("registry/indicators.json")
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    sc = build_scorecard([_finding()], {"momentum": _rating(["f-001"])}, {"momentum": 0.4},
                         a, "n", Confidence(level="medium", basis="b"), reg, horizons=hz)
    assert sc.indices.divergence.state == "insufficient-coverage"
    assert sc.indices.outlook.dmiContribution == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_pipeline.py -q`
Expected: FAIL with `ImportError: cannot import name '_partition_by_horizon'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/pipeline.py`, add the import for the accessor near the other imports:

```python
from gpu_agent.registry.horizon import IndicatorHorizons
```

Add these helpers after `_divergence`:

```python
def _contributes(spec) -> bool:
    """A finding contributes to an index iff its indicator is scoring and not a price/structural overlay
    (mirrors the filter inside the frozen dmi_smi_contribution)."""
    return spec.scoring and spec.side not in ("price", "structural")

def _partition_by_horizon(findings, horizons: IndicatorHorizons):
    """Split findings into (momentum, outlook) by indicator horizon. leading -> outlook; else momentum.
    horizons.horizon() fails loud on an untagged indicator (never a silent drop)."""
    momentum, outlook = [], []
    for f in findings:
        (outlook if horizons.horizon(f.indicatorId) == "leading" else momentum).append(f)
    return momentum, outlook

def _index_for(findings, registry, category, weights) -> tuple[DemandSupply, int]:
    """Compute one DemandSupply index over a finding bucket via the frozen dmi_smi_contribution,
    plus the count of contributing (scoring, non-overlay) findings."""
    dmi, smi = dmi_smi_contribution(findings, registry, category, weights)
    sdgi = dmi - smi
    count = sum(1 for f in findings if _contributes(registry.resolve(f.indicatorId, category)))
    return (DemandSupply(dmiContribution=dmi, smiContribution=smi,
                         sdgi=sdgi, sdgiDirection=_sdgi_direction(sdgi)), count)
```

Then modify `build_scorecard`. Change its signature to add the `horizons` kwarg:

```python
def build_scorecard(findings: list[Finding], ratings: dict[str, DimensionRating],
                    anchors: dict[str, float], assignment: Assignment,
                    narrative: str, confidence: Confidence, registry,
                    *, category_status: CategoryStatus | None = None,
                    horizons: IndicatorHorizons | None = None) -> Scorecard:
```

Inside it, after the line `any_under = any(s.evidenceStatus == "under-supported" for s in status.values())` and before the `sc = Scorecard(` construction, insert:

```python
    indices = None
    if horizons is not None:
        horizons.validate_coverage(registry)  # fail-loud: every scoring indicator must be tagged
        mom_f, out_f = _partition_by_horizon(findings, horizons)
        momentum, mom_n = _index_for(mom_f, registry, assignment.category, assignment.weights)
        outlook, out_n = _index_for(out_f, registry, assignment.category, assignment.weights)
        indices = MarketIndices(momentum=momentum, outlook=outlook,
                                divergence=_divergence(momentum, outlook, mom_n, out_n))
```

Then add `indices=indices,` to the `Scorecard(...)` constructor call (e.g. right after `categoryStatus=category_status`):

```python
        dimensionStatus=status, categoryStatus=category_status, indices=indices)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_pipeline.py -q`
Expected: PASS (existing + 4 new).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 281 passed, 3 skipped (277 + 4 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/pipeline.py tests/test_pipeline.py && git commit -m "feat(4-3): compute Momentum/Outlook indices in build_scorecard (frozen dmi_smi reused via horizon partition)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Wire `cli.py` so real runs populate `indices` + golden guard

**Files:**
- Modify: `gpu_agent/cli.py` (load `IndicatorHorizons`, pass `horizons=` at both `build_scorecard` call sites)
- Test: `tests/test_golden_integration.py` (extend)

**Interfaces:**
- Consumes: `build_scorecard(..., horizons=)` (Task 3), `IndicatorHorizons` (4-2).
- Produces: cli `run` / `extract` write a scorecard whose `indices` is populated.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_golden_integration.py`:

```python
def test_cli_run_populates_indices_on_golden(tmp_path):
    rc = main(["run", "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--fixtures", "fixtures/golden", "--out", str(tmp_path)])
    assert rc == 0
    written = sorted((tmp_path / "chips.merchant-gpu").glob("*.json"))[0]
    got = json.loads(written.read_text("utf-8"))
    idx = got["indices"]
    assert idx is not None
    # golden findings are all lagging/coincident -> Momentum == blended demandSupply, Outlook all-zero
    assert idx["momentum"]["dmiContribution"] == got["demandSupply"]["dmiContribution"]
    assert idx["momentum"]["smiContribution"] == got["demandSupply"]["smiContribution"]
    assert idx["outlook"]["dmiContribution"] == 0.0 and idx["outlook"]["smiContribution"] == 0.0
    assert idx["divergence"]["state"] == "insufficient-coverage"
    assert idx["divergence"]["outlookFindingCount"] == 0
    # every golden finding is a contributing (scoring, non-overlay) momentum signal
    assert idx["divergence"]["momentumFindingCount"] == len(got["findings"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_golden_integration.py -q`
Expected: FAIL — `got["indices"]` is `None` (cli does not pass horizons yet), so `idx["momentum"]` raises `TypeError`/`KeyError`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/cli.py`, add the import near the other registry imports at the top of the file:

```python
from gpu_agent.registry.horizon import IndicatorHorizons
```

At the **first** `build_scorecard` call site (inside `_run`, currently):

```python
    registry, _ = _load_registry()
    return build_scorecard(findings, ratings, anchors, a, narrative, confidence, registry,
                           category_status=category_status)
```

change the call to pass horizons:

```python
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    return build_scorecard(findings, ratings, anchors, a, narrative, confidence, registry,
                           category_status=category_status, horizons=horizons)
```

At the **second** `build_scorecard` call site (in the extract path, currently):

```python
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a, bundle.narrative, bundle.confidence, registry,
                         category_status=bundle.categoryStatus)
```

change it to:

```python
    horizons = IndicatorHorizons.load("registry/indicators.json")
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a, bundle.narrative, bundle.confidence, registry,
                         category_status=bundle.categoryStatus, horizons=horizons)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_golden_integration.py -q`
Expected: PASS (existing + 1 new).

- [ ] **Step 5: Run the full suite + confirm frozen files untouched**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 282 passed, 3 skipped (281 + 1 new).

Run: `cd /c/Users/danie/random_for_fun && git diff --stat main -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py`
Expected: **no output** (these frozen files are byte-unchanged on the branch vs `main`).

Run: `cd /c/Users/danie/random_for_fun && git diff main -- fixtures/`
Expected: **no output** (no committed fixture changed).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/cli.py tests/test_golden_integration.py && git commit -m "feat(4-3): cli run/extract populate Scorecard.indices (Momentum/Outlook + divergence)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage** (against `2026-06-29-two-indices-momentum-outlook-design.md`):
- §1 partition by horizon + reuse frozen `dmi_smi_contribution` with same weights → Task 3 (`_partition_by_horizon`, `_index_for` passes `assignment.weights`). ✓
- §1 additive invariant `demandSupply == momentum + outlook` → Task 3 `test_build_scorecard_computes_indices_and_invariant` + Task 4 golden (`momentum == demandSupply`, outlook zero). ✓
- §1 untagged indicator fails loud → Task 3 `_partition_by_horizon` via `horizons.horizon()`; `validate_coverage` guard in `build_scorecard`. ✓
- §2 `Divergence`/`MarketIndices`/optional `Scorecard.indices`; reuse `DemandSupply`; `demandSupply` unchanged → Task 1. ✓
- §2/§3 counts are contributing (scoring) findings only → Task 3 `_contributes` + `_index_for` count; Task 4 asserts `momentumFindingCount == len(findings)` (all golden findings contribute). ✓
- §3 divergence rule (4 states, categorical direction boundary, weakening/strengthening by rank, insufficient-coverage first, sdgiGap carried) → Task 2 `_divergence` + `test_divergence.py`. ✓
- §4 wiring: `build_scorecard` gains optional `horizons`; runs `validate_coverage`; existing output unchanged; cli passes horizons → Task 3 (kwarg + guard) + Task 4 (cli). ✓
- §5 frozen byte-unchanged; additive only → Task 4 Step 5 git-diff guards (frozen files + fixtures). ✓
- §6 doctrine (numbers from gated findings; overlays excluded; logged-not-silent; deterministic) → frozen `dmi_smi_contribution` reuse + `_contributes` + the `note` on insufficient-coverage. ✓
- §7 test strategy (partition, invariant, fixture inertness, all 4 divergence states, coverage guard, frozen guard, suite green) → Tasks 1–4 tests + Task 4 guards. ✓
- §9 acceptance items 1–4 all map to the tasks above. ✓

**Fixture inertness (acceptance §2):** Task 4 asserts on the committed golden run that `indices.momentum == demandSupply` (dmi/smi) and `outlook` is all-zero — i.e. adding the indices changed nothing about the blended numbers. Committed fixtures are not edited (Task 4 Step 5 `git diff main -- fixtures/` guard). ✓

**Placeholder scan:** none — every step has complete code/commands.

**Type consistency:** `Divergence`/`MarketIndices` (Task 1) imported in Task 2/3. `_divergence` signature (Task 2) is called in Task 3 with `(momentum, outlook, mom_n, out_n)`. `_index_for` returns `(DemandSupply, int)` consumed as `momentum, mom_n` in Task 3. `build_scorecard(..., horizons=)` kwarg (Task 3) is what cli passes (Task 4). `_partition_by_horizon(findings, horizons)` (2-arg) matches its Task 3 test call. `_sdgi_direction` and `dmi_smi_contribution` are pre-existing. `IndicatorHorizons.horizon`/`.validate_coverage`/`.load` are the 4-2 accessor's real methods. ✓

**Test-count math:** baseline 268 → +4 (Task 1) → +5 (Task 2) → +4 (Task 3) → +1 (Task 4) = **282 passed, 3 skipped** at the end.
