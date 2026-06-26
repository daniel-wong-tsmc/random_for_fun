# Claude Code Harness (sub-project 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the v1 Claude Code harness from charter Part 38 — a single, scope-selecting `/run-cycle` trigger (a specific category, a layer and all its categories, or the whole market) that runs the Category tier and reports Layer/Main as explicit deferred stages.

**Architecture:** A small, tested orchestration core (`gpu_agent/cycle.py` + two additive methods on the `Taxonomy` loader + one `cli.py` subcommand) resolves a scope string into a **cycle plan** — which categories are ready (have an assignment) vs. skipped-no-assignment — without ever running an LLM. A session-driven **`run-cycle` skill** is the plain driver: it reads the plan, runs each ready category through the existing `gather → ingest → brain` path (reusing the `gather-category` skill), writes a replayable cycle log, and prints per-tier-stage status with Layer/Main deferred. This is the modular split from Part 38: deterministic resolution is tested code; session orchestration is a skill.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest. Run all commands from repo root `C:\Users\danie\random_for_fun` using `.venv/Scripts/python`.

## Global Constraints

- **Frozen contract — never edit:** the Finding/Scorecard schema (`gpu_agent/schema/`), the 6 dimensions, `gpu_agent/gate.py`, `gpu_agent/scoring.py` functions, `pipeline.py`'s Part-7 gate behavior, and the Increment-A registry (`gpu_agent/registry/indicators.py`, `validate.py`). This plan only **adds** to `structure.py` (the scope-resolver seam) and `cli.py` (an adapter subcommand); it creates one new module and one new skill.
- **The 6 dimensions are fixed:** `momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk`.
- **Doctrine (charter Part 38):** the session orchestrates; code computes + gates + stores; delegation stays **one level deep**; a selected category with **no assignment is logged as skipped, never silently dropped**; a cycle must be replayable from its run log.
- **TDD:** every code task writes the failing test first, watches it fail, then implements.
- **Commit message trailer (every commit):** end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **Run from repo root**; interpreter `.venv/Scripts/python`; tests via `.venv/Scripts/python -m pytest`.
- **Branch:** work on `claude-code-harness` (already created; charter Part 38 committed there at `18cbbfc`).
- Baseline suite before Task 1: **96 passed, 3 skipped.** This plan adds tests; the full suite stays green after every task (no signature changes to existing code).

---

## File Structure

**Create:**
- `gpu_agent/cycle.py` — `AssignmentProvider`, `resolve_scope`, `CycleEntry`, `CyclePlan`, `build_cycle_plan` (the deterministic orchestration core).
- `tests/test_taxonomy_scope.py`, `tests/test_assignment_provider.py`, `tests/test_cycle_plan.py`, `tests/test_cli_cycle_plan.py`.
- `.claude/skills/run-cycle/SKILL.md` — the session-driven `/run-cycle` orchestrator.

**Modify:**
- `gpu_agent/registry/structure.py` — add `categories_by_layer` field + `categories_in_layer()` + `all_categories()` (additive; existing `dimensions`/`categories` unchanged).
- `gpu_agent/cli.py` — add a `cycle-plan` subcommand (adapter; emits the plan JSON, logs skipped categories to stderr).

---

## Task 1: Layer-scoped accessors on the `Taxonomy` loader

**Files:**
- Modify: `gpu_agent/registry/structure.py`
- Test: `tests/test_taxonomy_scope.py`

**Interfaces:**
- Consumes: the existing `Taxonomy.load(path)` and `docs/taxonomy.json` (layers → `layers[].id`, categories → `layers[].categories[].id`; composed id is `"<layer.id>.<category.id>"`).
- Produces:
  - `Taxonomy.categories_by_layer: dict[str, frozenset[str]]` (layer id → its composed category ids).
  - `Taxonomy.categories_in_layer(self, layer_id: str) -> tuple[str, ...]` — sorted; raises `ValueError` on an unknown layer.
  - `Taxonomy.all_categories(self) -> tuple[str, ...]` — sorted.

- [ ] **Step 1: Write the failing test**

Create `tests/test_taxonomy_scope.py`:

```python
import pathlib
import pytest
from gpu_agent.registry.structure import Taxonomy

TAX = pathlib.Path("docs/taxonomy.json")

def test_categories_in_layer_returns_sorted_layer_members():
    tax = Taxonomy.load(TAX)
    chips = tax.categories_in_layer("chips")
    assert "chips.merchant-gpu" in chips
    assert "chips.hbm-memory" in chips
    assert all(c.startswith("chips.") for c in chips)
    assert list(chips) == sorted(chips)

def test_all_categories_spans_layers_and_is_unique():
    tax = Taxonomy.load(TAX)
    allc = tax.all_categories()
    assert {"chips.merchant-gpu", "models.frontier-closed", "energy.cooling"} <= set(allc)
    assert len(allc) == len(set(allc))
    assert list(allc) == sorted(allc)

def test_categories_in_layer_unknown_raises():
    tax = Taxonomy.load(TAX)
    with pytest.raises(ValueError):
        tax.categories_in_layer("not-a-layer")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_taxonomy_scope.py -v`
Expected: FAIL with `AttributeError: 'Taxonomy' object has no attribute 'categories_in_layer'`.

- [ ] **Step 3: Implement the additive methods**

Replace `gpu_agent/registry/structure.py` with:

```python
from __future__ import annotations
import json, pathlib
from pydantic import BaseModel, Field

class Taxonomy(BaseModel):
    dimensions: frozenset[str]
    categories: frozenset[str]
    categories_by_layer: dict[str, frozenset[str]] = Field(default_factory=dict)

    @classmethod
    def load(cls, path) -> "Taxonomy":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        dims = {d["id"] for d in data["scoringRubric"]["dimensions"]}
        by_layer = {
            layer["id"]: frozenset(f"{layer['id']}.{c['id']}" for c in layer["categories"])
            for layer in data["layers"]
        }
        cats = frozenset().union(*by_layer.values()) if by_layer else frozenset()
        return cls(dimensions=frozenset(dims), categories=cats, categories_by_layer=by_layer)

    def categories_in_layer(self, layer_id: str) -> tuple[str, ...]:
        if layer_id not in self.categories_by_layer:
            raise ValueError(f"unknown layer: {layer_id}")
        return tuple(sorted(self.categories_by_layer[layer_id]))

    def all_categories(self) -> tuple[str, ...]:
        return tuple(sorted(self.categories))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_taxonomy_scope.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Confirm no regression in the registry suite**

Run: `.venv/Scripts/python -m pytest tests/test_registry_structure.py tests/test_registry_validate.py -v`
Expected: PASS (the additive field has a default; `validate_against` and the clean-registry test are unaffected).

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/registry/structure.py tests/test_taxonomy_scope.py
git commit -m "$(printf 'feat(registry): Taxonomy layer-scope accessors (categories_in_layer, all_categories)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 2: The assignment provider seam

**Files:**
- Create: `gpu_agent/cycle.py`
- Test: `tests/test_assignment_provider.py`

**Interfaces:**
- Consumes: `load_assignment(path) -> Assignment` and `Assignment` (with `.category`) from `gpu_agent.assignment`.
- Produces:
  - `class AssignmentProvider` with `__init__(self, root="fixtures")`, `path_for(self, category_id: str) -> pathlib.Path` (convention: `<root>/asg.<category_id>.json`), and `get(self, category_id: str) -> Assignment | None` (returns `None` when the file is absent — the caller logs the skip).

- [ ] **Step 1: Write the failing test**

Create `tests/test_assignment_provider.py`:

```python
from gpu_agent.cycle import AssignmentProvider

def test_path_for_uses_asg_convention():
    p = AssignmentProvider("fixtures")
    assert p.path_for("chips.merchant-gpu").name == "asg.chips.merchant-gpu.json"

def test_get_returns_assignment_when_file_exists():
    a = AssignmentProvider("fixtures").get("chips.merchant-gpu")
    assert a is not None
    assert a.category == "chips.merchant-gpu"

def test_get_returns_none_when_missing():
    assert AssignmentProvider("fixtures").get("energy.cooling") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_assignment_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.cycle'`.

- [ ] **Step 3: Create `gpu_agent/cycle.py` with the provider**

```python
from __future__ import annotations
import pathlib
from gpu_agent.assignment import Assignment, load_assignment

class AssignmentProvider:
    """category_id -> its Assignment, by file convention `<root>/asg.<category_id>.json`.

    Returns None when no assignment exists (the caller logs it as skipped — Part 38
    no-silent-truncation). Swap this seam later for a taxonomy-default generator.
    """
    def __init__(self, root: str | pathlib.Path = "fixtures"):
        self.root = pathlib.Path(root)

    def path_for(self, category_id: str) -> pathlib.Path:
        return self.root / f"asg.{category_id}.json"

    def get(self, category_id: str) -> Assignment | None:
        p = self.path_for(category_id)
        if not p.exists():
            return None
        return load_assignment(p)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_assignment_provider.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cycle.py tests/test_assignment_provider.py
git commit -m "$(printf 'feat(cycle): assignment provider seam (category -> assignment | None)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 3: Scope resolution + cycle plan

**Files:**
- Modify: `gpu_agent/cycle.py`
- Test: `tests/test_cycle_plan.py`

**Interfaces:**
- Consumes: `Taxonomy` (Task 1: `categories_in_layer`, `all_categories`, `.categories`); `AssignmentProvider` (Task 2).
- Produces:
  - `resolve_scope(scope: str, taxonomy) -> tuple[str, ...]` — `"category:<id>"` → that one id (raises `ValueError` if id ∉ `taxonomy.categories`); `"layer:<id>"` → `taxonomy.categories_in_layer(id)`; `"all"` or `"market"` → `taxonomy.all_categories()`; anything else → `ValueError`.
  - `class CycleEntry(BaseModel)`: `category_id: str`, `assignment_path: str | None`, `status: str` (`"ready"` | `"skipped-no-assignment"`).
  - `class CyclePlan(BaseModel)`: `scope: str`, `entries: list[CycleEntry]`, `stages: list[dict[str, str]]`.
  - `build_cycle_plan(scope: str, taxonomy, provider: AssignmentProvider) -> CyclePlan` — resolves the scope, marks each category ready/skipped, and sets stages `category=active, layer=deferred, main=deferred`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cycle_plan.py`:

```python
import pathlib
import pytest
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan, resolve_scope

TAX = pathlib.Path("docs/taxonomy.json")

def _tax():
    return Taxonomy.load(TAX)

def test_resolve_scope_category():
    assert resolve_scope("category:chips.merchant-gpu", _tax()) == ("chips.merchant-gpu",)

def test_resolve_scope_layer():
    cats = resolve_scope("layer:chips", _tax())
    assert "chips.merchant-gpu" in cats and all(c.startswith("chips.") for c in cats)

def test_resolve_scope_all():
    cats = resolve_scope("all", _tax())
    assert {"chips.merchant-gpu", "models.frontier-closed"} <= set(cats)

def test_resolve_scope_unknown_category_raises():
    with pytest.raises(ValueError):
        resolve_scope("category:chips.not-real", _tax())

def test_resolve_scope_malformed_raises():
    with pytest.raises(ValueError):
        resolve_scope("bogus", _tax())

def test_build_cycle_plan_marks_ready_skipped_and_stages():
    plan = build_cycle_plan("layer:chips", _tax(), AssignmentProvider("fixtures"))
    by_id = {e.category_id: e for e in plan.entries}
    # the one category with a committed assignment is ready
    assert by_id["chips.merchant-gpu"].status == "ready"
    assert by_id["chips.merchant-gpu"].assignment_path is not None
    # a category with no assignment is skipped, not dropped (no silent truncation)
    assert by_id["chips.hbm-memory"].status == "skipped-no-assignment"
    assert by_id["chips.hbm-memory"].assignment_path is None
    # every selected category is present
    assert set(by_id) == set(resolve_scope("layer:chips", _tax()))
    # Category active; Layer/Main deferred
    assert {s["tier"]: s["status"] for s in plan.stages} == {
        "category": "active", "layer": "deferred", "main": "deferred"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_cycle_plan.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_cycle_plan' from 'gpu_agent.cycle'`.

- [ ] **Step 3: Add resolution + plan to `gpu_agent/cycle.py`**

Add to the top of `gpu_agent/cycle.py` (alongside the existing imports):

```python
from pydantic import BaseModel, Field
```

Append to `gpu_agent/cycle.py` (after `AssignmentProvider`):

```python
def resolve_scope(scope: str, taxonomy) -> tuple[str, ...]:
    if scope in ("all", "market"):
        return taxonomy.all_categories()
    if scope.startswith("category:"):
        cid = scope.split(":", 1)[1]
        if cid not in taxonomy.categories:
            raise ValueError(f"unknown category: {cid}")
        return (cid,)
    if scope.startswith("layer:"):
        return taxonomy.categories_in_layer(scope.split(":", 1)[1])
    raise ValueError(f"unrecognized scope: {scope!r} "
                     f"(expected 'category:<id>', 'layer:<id>', or 'all')")

class CycleEntry(BaseModel):
    category_id: str
    assignment_path: str | None
    status: str  # "ready" | "skipped-no-assignment"

class CyclePlan(BaseModel):
    scope: str
    entries: list[CycleEntry] = Field(default_factory=list)
    stages: list[dict[str, str]] = Field(default_factory=list)

def build_cycle_plan(scope: str, taxonomy, provider: AssignmentProvider) -> CyclePlan:
    entries: list[CycleEntry] = []
    for cid in resolve_scope(scope, taxonomy):
        path = provider.path_for(cid)
        if path.exists():
            entries.append(CycleEntry(category_id=cid, assignment_path=str(path), status="ready"))
        else:
            entries.append(CycleEntry(category_id=cid, assignment_path=None,
                                      status="skipped-no-assignment"))
    stages = [{"tier": "category", "status": "active"},
              {"tier": "layer", "status": "deferred"},
              {"tier": "main", "status": "deferred"}]
    return CyclePlan(scope=scope, entries=entries, stages=stages)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_cycle_plan.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cycle.py tests/test_cycle_plan.py
git commit -m "$(printf 'feat(cycle): scope resolution + cycle plan (ready vs skipped, deferred tiers)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 4: `cycle-plan` CLI subcommand (the deterministic seam the skill calls)

**Files:**
- Modify: `gpu_agent/cli.py`
- Test: `tests/test_cli_cycle_plan.py`

**Interfaces:**
- Consumes: `Taxonomy.load` (Task 1); `AssignmentProvider`, `build_cycle_plan` (Tasks 2–3).
- Produces: a `cycle-plan` subcommand — `python -m gpu_agent.cli cycle-plan --scope <scope> [--assignments DIR] [--taxonomy PATH] [--out FILE]`. Prints the `CyclePlan` JSON to stdout; writes it to `--out` if given (the initial cycle log); prints each non-ready entry to stderr (`SKIPPED <id>: <status>`); exits non-zero on a bad scope (`ValueError`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_cycle_plan.py`:

```python
import json, subprocess, sys

def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", "cycle-plan", *args],
                          capture_output=True, text=True)

def test_cycle_plan_category_emits_ready_json():
    out = _run("--scope", "category:chips.merchant-gpu")
    assert out.returncode == 0, out.stderr
    plan = json.loads(out.stdout)
    assert plan["scope"] == "category:chips.merchant-gpu"
    assert plan["entries"][0]["category_id"] == "chips.merchant-gpu"
    assert plan["entries"][0]["status"] == "ready"
    assert {s["tier"]: s["status"] for s in plan["stages"]} == {
        "category": "active", "layer": "deferred", "main": "deferred"}

def test_cycle_plan_layer_surfaces_skipped_on_stderr():
    out = _run("--scope", "layer:chips")
    assert out.returncode == 0, out.stderr
    assert "chips.hbm-memory" in out.stderr  # skipped category surfaced, not silent

def test_cycle_plan_writes_out_file(tmp_path):
    log = tmp_path / "cycle-log.json"
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode == 0, out.stderr
    written = json.loads(log.read_text("utf-8"))
    assert written["entries"][0]["category_id"] == "chips.merchant-gpu"

def test_cycle_plan_bad_scope_fails_loud():
    out = _run("--scope", "bogus")
    assert out.returncode != 0
    assert "bogus" in (out.stderr + out.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_cli_cycle_plan.py -v`
Expected: FAIL (argparse exits non-zero: `invalid choice: 'cycle-plan'`).

- [ ] **Step 3: Add imports near the top of `gpu_agent/cli.py`**

After the existing `from gpu_agent.registry...` imports (added in Increment A), add:

```python
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan
```

(`Taxonomy` is already imported in `cli.py` from Increment A. If it is not, also add `from gpu_agent.registry.structure import Taxonomy`.)

- [ ] **Step 4: Add the `_cycle_plan` handler**

In `gpu_agent/cli.py`, add this handler (place it after `_pipeline`):

```python
def _cycle_plan(args) -> int:
    taxonomy = Taxonomy.load(args.taxonomy)
    provider = AssignmentProvider(args.assignments)
    plan = build_cycle_plan(args.scope, taxonomy, provider)   # raises ValueError on bad scope
    payload = plan.model_dump_json(indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload, encoding="utf-8")
    print(payload)
    for e in plan.entries:
        if e.status != "ready":
            print(f"SKIPPED {e.category_id}: {e.status}", file=sys.stderr)
    return 0
```

- [ ] **Step 5: Register the subparser and dispatch**

In `gpu_agent/cli.py` `main()`, add the subparser (next to the other `sub.add_parser(...)` blocks):

```python
    cp = sub.add_parser("cycle-plan")
    cp.add_argument("--scope", required=True,
                    help="category:<id> | layer:<id> | all")
    cp.add_argument("--assignments", default="fixtures",
                    help="dir of asg.<category>.json files")
    cp.add_argument("--taxonomy", default="docs/taxonomy.json")
    cp.add_argument("--out", default=None, help="write the cycle plan JSON here (initial cycle log)")
```

Then dispatch it, wrapping the `ValueError` so a bad scope fails loud with exit 1 (place alongside the other `if args.cmd == ...` checks, before the `run`/`score` try-block):

```python
    if args.cmd == "cycle-plan":
        try:
            return _cycle_plan(args)
        except ValueError as e:
            print("CYCLE SCOPE ERROR:", e, file=sys.stderr)
            return 1
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_cli_cycle_plan.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Run the full suite (no regressions)**

Run: `.venv/Scripts/python -m pytest -q`
Expected: PASS — all green (baseline 96 + the new tests; 3 live smokes still skipped).

- [ ] **Step 8: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_cycle_plan.py
git commit -m "$(printf 'feat(cli): cycle-plan subcommand (scope -> plan JSON; skipped to stderr; fail-loud scope)\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Task 5: The `/run-cycle` orchestrator skill

**Files:**
- Create: `.claude/skills/run-cycle/SKILL.md`

**Interfaces:**
- Consumes: the `cycle-plan` subcommand (Task 4); the existing `gather-category` skill (the per-category gather→ingest→brain procedure); the `pipeline` CLI subcommand; `JsonStore` output path `store/<categoryId>/<asOf>-v<n>.json`.
- Produces: a manual-trigger skill (`/run-cycle`) — the plain session driver from charter Part 38. No Python; validated by a documented deterministic dry-run.

This task has no pytest (a skill is a markdown procedure, validated by a documented dry-run — the same way `gather-category` was). The deliverable is the SKILL.md plus the recorded dry-run evidence in the report.

- [ ] **Step 1: Write the skill**

Create `.claude/skills/run-cycle/SKILL.md` with this content:

````markdown
---
name: run-cycle
description: Use to run the GPU Category Agent swarm for a chosen scope — a specific category, a whole layer (all its categories), or the entire market. Manual-trigger; the session is the coordinator (charter Part 38). v1 runs the Category tier; Layer and Main are deferred stages.
---

# Run Cycle (the Claude Code harness — charter Part 38)

You are the **plain driver** for a swarm cycle. You turn a **scope** into a set of category runs, run the
Category tier over them via the existing gathering swarm + frozen brain, write a replayable cycle log, and
report each tier-stage's status. v1 executes **Category**; **Layer and Main are deferred** stages you report,
not run.

## Invariants (charter Part 38 — do not violate)
- **The session orchestrates; code computes + gates + stores.** You drive; the deterministic CLI does the
  scoring, gating, and persistence. You never invent a number or edit the frozen brain.
- **Delegation one level deep.** You (the session) are each category's coordinator; gatherers are your only
  sub-level (charter Part 37). Do not nest coordinators.
- **No silent truncation.** A selected category with no assignment is reported as skipped, with the reason —
  never dropped quietly.
- **Replayable.** Every run writes a cycle log; a cycle you can't replay from it did not happen.

## Inputs
- `scope` — one of: `category:<id>` (e.g. `category:chips.merchant-gpu`), `layer:<id>` (e.g. `layer:chips`),
  or `all` / `market`.
- `asOf` (e.g. `2026-06`), and the model backend choice: in-session/recorded (default, $0) or a metered
  backend (`--backend claude_code`, requires the `[llm]` extra + a token).

## Procedure
1. **Resolve the scope to a cycle plan** (deterministic — no LLM):
   ```
   .venv/Scripts/python -m gpu_agent.cli cycle-plan --scope <scope> --out store/cycle-log.json
   ```
   This prints the plan and writes the initial cycle log. Categories with no assignment are printed to
   stderr as `SKIPPED <id>: skipped-no-assignment` — report these; do not chase them.
2. **Run each `ready` category (Category tier), sequentially.** For each `ready` entry, run that category
   through the gathering swarm + frozen brain by following the **`gather-category`** skill for its
   `assignment_path` and `asOf` (gather → ingest → `pipeline`). For a deterministic dry-run, use the
   recorded fixtures instead of live gathering (see the dry-run below). Record the written scorecard path
   (`store/<categoryId>/<asOf>-v<n>.json`) and its DMI/SMI.
3. **Layer stage — deferred.** Do not run it. Report: "Layer assessment: deferred — not yet built
   (sub-project 3)." For a `layer:` or `all` scope, name which layer(s) would be assessed.
4. **Main stage — deferred.** Report: "Main / market-state: deferred — not yet built (sub-project 4)."
5. **Finalize the cycle log.** Update `store/cycle-log.json` with, per ready category, its scorecard path +
   DMI/SMI, and the tier-stage statuses (`category: done`, `layer: deferred`, `main: deferred`).
6. **Report:** the scope, categories run (with scorecard paths + DMI/SMI), categories skipped (with reason),
   and the deferred Layer/Main stages.

## Caps & safety
- A live `all` run fans out gatherers across ~34 categories — honor any budget/`maxDocuments` the user gives,
  and log anything skipped. If no backend/token is available for a metered run, say so and use the in-session
  recorded path; never silently produce an empty or partial cycle as if it were complete.
- If zero categories are `ready`, report "nothing to run (no assignments for this scope)" and stop — do not
  write empty scorecards.

## Snapshot / determinism
`store/cycle-log.json` + the per-category gather snapshots + scorecards are the saved artifacts; the cycle
replays from them. A cycle that can't be replayed from its log did not happen.
````

- [ ] **Step 2: Validate with a deterministic dry-run (single category)**

Run the scope resolver and confirm the plan:

```bash
.venv/Scripts/python -m gpu_agent.cli cycle-plan --scope category:chips.merchant-gpu --out store/_dryrun-cycle-log.json
```
Expected: stdout shows one `ready` entry for `chips.merchant-gpu` and stages `category=active, layer=deferred, main=deferred`; the file is written.

Then run the Category brain on the committed recorded fixtures (the $0 replay the skill's step 2 would drive):

```bash
.venv/Scripts/python -m gpu_agent.cli pipeline --docs fixtures/raw \
  --assignment fixtures/asg.chips.merchant-gpu.json --as-of 2026-06 \
  --captured-at 2026-06-12T00:00:00Z \
  --recorded-extract fixtures/recorded/extract-nvda.json \
  --recorded-judge fixtures/recorded/judge-nvda.json --out store/_dryrun_store
```
Expected: `wrote store/_dryrun_store/chips.merchant-gpu/2026-06-v1.json  DMI=... SMI=...` (exit 0).

- [ ] **Step 3: Validate the layer-scope skip path (no silent truncation)**

```bash
.venv/Scripts/python -m gpu_agent.cli cycle-plan --scope layer:chips
```
Expected: stdout lists every `chips.*` category; stderr prints `SKIPPED chips.hbm-memory: skipped-no-assignment` (and the others lacking assignments) — confirming the skip is surfaced, not silent.

- [ ] **Step 4: Record the dry-run evidence and clean scratch**

Document the three runs above (commands + observed output) in the task report. Remove the dry-run scratch so it isn't committed:

```bash
rm -rf store/_dryrun_store store/_dryrun-cycle-log.json
```
(`store/` is gitignored, so this is just tidy-up.)

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/run-cycle/SKILL.md
git commit -m "$(printf 'feat(skill): run-cycle orchestrator — scope-selected manual swarm trigger (Part 38)\n\nCategory tier runs via gather-category + frozen brain; Layer/Main are deferred\nstages. Validated by a deterministic recorded dry-run (category + layer-skip path).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Final verification

- [ ] Run `.venv/Scripts/python -m pytest -q` — full suite green (baseline 96 + new tests; 3 live smokes skipped).
- [ ] `cycle-plan` resolves all three scope modes: `category:<id>`, `layer:<id>`, `all` — and fails loud (exit 1) on a bad scope.
- [ ] A `layer:`/`all` plan lists every selected category, marking those without an assignment `skipped-no-assignment` (no silent truncation).
- [ ] `.claude/skills/run-cycle/SKILL.md` exists, names the Category tier active and Layer/Main deferred, and reuses `gather-category` (does not duplicate it).
- [ ] Frozen contract untouched: `git diff main..HEAD --stat` shows changes only in `gpu_agent/registry/structure.py` (additive), `gpu_agent/cli.py` (new subcommand), `gpu_agent/cycle.py` (new), the new tests, the new skill, and the charter (Part 38, committed at the branch base).
