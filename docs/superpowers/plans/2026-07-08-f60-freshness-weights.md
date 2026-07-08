# F60 (S1) — Freshness Weights (data half) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Intended repo home:** `docs/superpowers/plans/2026-07-08-f60-freshness-weights.md` (currently drafted in scratch; place + commit it onto the `fix/freshness-weights` lane at claim time — do NOT drop it on the root checkout's main while another instance is mid-merge).

**Goal:** Give the forward/leading **demand** indicator set (`rpoBacklog`, `vendorRevenueGuidance`) real weight in `registry/indicators.json` so fresh, corpus-persisted leading findings actually move the DMI — without touching the frozen scoring engine.

**Architecture:** A **weight-only** edit to the indicator registry (DATA). `gpu_agent/scoring.py` already reads `spec.weight` when it accumulates `dmi_smi_contribution` (`scoring.py:20-23`); raising the two default weights changes the index a leading finding produces with zero code change. Because weights never reach the emitted brain prompts (the emit path serializes only `{id, label, side, unit}` — `gpu_agent/evals/emit.py:26-38`, `gpu_agent/cli.py:286-294`), the F6 eval hash-pin stays green, which is the proof the change stayed inside the data half. **Caveat (verified 2026-07-08):** both ids appear across eval cases, ~10 committed `store/` scorecards, and ~two dozen test files — so the reweight WILL likely ripple into recomputed test goldens (Task 2 is real work, not a no-op), and historical `store/` scorecards must be treated as immutable.

**Tech Stack:** Python 3.13, pytest, Pydantic finding schema, JSON registry.

## Global Constraints

- **Wave position: this is lane S1.** Base = **post-P3 main.** Barrier **B2** (wave plan §4): do NOT start implementation until `fix/contract-v1.4` (P3) has **merged AND been pushed** to `origin/main`; then create/rebase the lane onto the updated main. P3 nicks `gate.py` (+8 lines); it does **not** touch `scoring.py` or `registry/indicators.json`, so this plan's surface is unaffected — but rebase so the lane's suite runs against the merged gate.
- **DATA-ONLY. Never edit `gpu_agent/scoring.py`.** The exclusion rule (`scoring.py:14`, `if not spec.scoring or spec.side in ("price","structural")`) and the contribution formula (`scoring.py:22-23`) are **frozen core**; any side-semantics change ships only as the **v1.5 migration (Part 33)** — see Deferred Ledger below. This lane touches `registry/indicators.json` **weights** and tests only.
- **F6 pin is the guardrail, not a gate to unlock.** `tests/test_evals_baseline_pin.py` must **stay GREEN**. If it goes RED, STOP: you changed a prompt-visible field (`side`, `label`, or a new `id`) — that is Option B/C, out of scope for this lane.
- **Do NOT tick F60 as done** when this merges (Deferred Ledger §6). The `scoring.py` side-semantics half and the SMI-leading gap remain open for v1.5.
- **Chosen approach: Option A (reweight existing leading set)** — user decision 2026-07-08. Options B (reclassify `designWins`) and C (admit a news-sourced leading indicator) were rejected for this lane (both trip the pin; B is doctrinally loaded).
- Suite green at merge (expect **3–4 skips**). **Only the user merges to main** — this is a data lane, but it still lands via the user's gate.
- Run tests from the worktree root: `../../.venv/Scripts/python -m pytest -q`. One shared root venv — never create a per-worktree venv.
- Lane: worktree `.worktrees/freshness-weights`, branch `fix/freshness-weights`. Completion sentinel: `.superpowers/handoffs/freshness-weights-DONE.md`.

## Scope / Non-goals (read before Task 1)

- **In scope:** `rpoBacklog.weight` 0.10 → **0.14**; `vendorRevenueGuidance.weight` 0.12 → **0.16**. Both are `side:"demand"`, `dimension:"momentum"`, `scoring:true` — so they feed **DMI**. These are the only two scoring indicators on the leading horizon (`indicators.json` `cadenceHorizon`: `rpoBacklog`/`vendorRevenueGuidance` = `leading`; the third leading indicator `designWins` is `structural`/non-scoring and is **not** touched here).
- **Explicit non-goal — the SMI residual.** The backlog cited `smiContribution: 0.0`. SMI is the **supply** index; there is **no leading *supply* indicator** in the registry, so no data-only reweight can move SMI-from-leading. That gap is left for a future Option-C indicator or the v1.5 scoring half. This plan must not be judged against SMI movement.
- **The weight numbers are tunable, not sacred.** 0.14/0.16 lift the leading pair to ~½·`apiArr` (0.20, the largest coincident demand weight) while staying below it — forward signal counts, but a single quarter's guidance doesn't dominate realized momentum. If the Task 2 measurement shows the effect is still negligible, re-open the weights with the user rather than silently over-tuning.

## File Structure

- `registry/indicators.json` — MODIFY: two `weight` values in the `indicators` block. No other field, no `overrides` entry, no new key.
- `tests/test_registry_indicators.py` — MODIFY: add one integrity test pinning the new weights + invariants.
- `tests/test_scoring.py` — MODIFY: add one behavioral test proving the new default weights flow through `dmi_smi_contribution` via the registry (no override).
- `docs/fix-backlog.md` — MODIFY: F60 entry — record the DATA half done, keep F60 open for the deferred scoring half + SMI residual.
- `docs/superpowers/eval-notes/2026-07-08-f60-freshness-weights-note.md` — CREATE: short verification note (measured DMI effect + the deferred residual).

---

## Task 1: Reweight the leading demand set (data change + guard tests)

**Files:**
- Modify: `registry/indicators.json` (lines 16–17: `rpoBacklog`, `vendorRevenueGuidance` `weight`)
- Test: `tests/test_registry_indicators.py`, `tests/test_scoring.py`

**Interfaces:**
- Consumes: `IndicatorRegistry.load(path)` → `reg.resolve(id, category_id)` → `IndicatorSpec` with `.weight/.scoring/.side/.dimension`; `dmi_smi_contribution(findings, reg, category_id, weight_overrides=None)` → `(dmi, smi)` reading `spec.weight` when no override is passed (`scoring.py:20`).
- Produces: nothing importable — a registry data change guarded by two tests.

- [ ] **Step 1: Write the failing registry-integrity test**

Append to `tests/test_registry_indicators.py` (idiom mirrors `test_new_scoring_indicators_have_dimension_and_nonzero_weight`):

```python
def test_leading_demand_indicators_reweighted_for_freshness():
    # F60 data-half (Option A): give the forward/leading demand set real weight so
    # fresh, corpus-persisted leading findings move DMI. Weight-only -> no emitted-
    # prompt change -> F6 pin stays green. Invariants (side/dimension/scoring) MUST
    # be preserved: a side change would be Option B and trip the pin.
    reg = IndicatorRegistry.load(REG)
    rpo = reg.resolve("rpoBacklog", "chips.merchant-gpu")
    vrg = reg.resolve("vendorRevenueGuidance", "chips.merchant-gpu")
    assert rpo.weight == 0.14
    assert vrg.weight == 0.16
    assert rpo.scoring is True and rpo.side == "demand" and rpo.dimension == "momentum"
    assert vrg.scoring is True and vrg.side == "demand" and vrg.dimension == "momentum"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_registry_indicators.py::test_leading_demand_indicators_reweighted_for_freshness -v`
Expected: FAIL — `assert 0.1 == 0.14` (registry still holds the old weights).

- [ ] **Step 3: Write the failing scoring-behavior test**

Append to `tests/test_scoring.py` (reuses the module's `_f` helper and the no-override call so it reads the registry default):

```python
def test_reweighted_leading_demand_moves_dmi_via_registry_default():
    # No weight_overrides -> dmi_smi_contribution reads spec.weight (registry default),
    # proving the F60 data change flows through the FROZEN scoring path unchanged.
    # _f uses mag=3, and the formula divides magnitude by 3, so contribution == weight.
    reg = IndicatorRegistry.load("registry/indicators.json")
    findings = [_f("rpoBacklog", 1, 0, 3), _f("vendorRevenueGuidance", 1, 0, 3)]
    dmi, smi = dmi_smi_contribution(findings, reg, "chips.merchant-gpu")
    assert math.isclose(dmi, 0.14 + 0.16)   # new registry-default demand weights
    assert math.isclose(smi, 0.0)           # leading set is demand-only -> SMI unmoved (scope boundary)
```

- [ ] **Step 4: Run it to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_scoring.py::test_reweighted_leading_demand_moves_dmi_via_registry_default -v`
Expected: FAIL — `dmi` computes to `0.10 + 0.12 = 0.22`, not `0.30`.

- [ ] **Step 5: Apply the data change**

In `registry/indicators.json`, edit exactly two `weight` values (leave every other field byte-identical):

- `rpoBacklog`: `"weight": 0.10` → `"weight": 0.14`
- `vendorRevenueGuidance`: `"weight": 0.12` → `"weight": 0.16`

- [ ] **Step 6: Run both new tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_registry_indicators.py::test_leading_demand_indicators_reweighted_for_freshness tests/test_scoring.py::test_reweighted_leading_demand_moves_dmi_via_registry_default -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Prove the F6 pin stayed green (the data-half guardrail)**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -v`
Expected: PASS. If it FAILS, STOP and revert — a weight-only change cannot move the pin, so a red pin means an unintended prompt-visible edit crept in.

- [ ] **Step 8: Commit**

```bash
git add registry/indicators.json tests/test_registry_indicators.py tests/test_scoring.py
git commit -m "feat(F60): reweight leading demand set so fresh signal moves DMI (data half)"
```

---

## Task 2: Full-suite reconciliation — update recomputed goldens; NEVER touch historical store scorecards

**Expect real work here.** `rpoBacklog`/`vendorRevenueGuidance` appear in eval cases, ~10 committed `store/` scorecards, and ~two dozen `tests/*` files (verified 2026-07-08). Any test that constructs a Finding with these ids and asserts a DMI/SMI/scorecard number computed from the **registry default** (no `weight_overrides`) will shift. Tests that pass explicit overrides (e.g. `test_scoring.py:49`) or assert on non-numeric fields (labels, dedup, lifecycle, rendering) are immune.

**Files:**
- Modify: whichever recomputing test goldens Step 1 surfaces (unknown set until the run; candidates concentrate in `test_pipeline.py`, `test_corpus_*.py`, `test_brief_*.py`, `test_scorecard_indices.py`, `test_lifecycle_*.py`).
- **NEVER modify:** `store/**` scorecards or `store/findings/**`. Those are immutable historical cycle records — they recorded the index at the weights in force that cycle. Retro-editing them is falsifying history.

**Interfaces:**
- Consumes: nothing new. Runs the whole suite and reconciles fallout from Task 1's default-weight change.
- Produces: a green full suite on the lane.

- [ ] **Step 1: Run the full suite and capture every failure**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: the 2 new tests pass; **expect additional failures** in tests that recompute an index from the new default weights. Record the full failing list before touching anything.

- [ ] **Step 2: Triage each failure — confirm it traces to this reweight**

For each failing test, confirm the delta is a Finding with `indicatorId` `rpoBacklog`/`vendorRevenueGuidance` scored at the new default weight (grep the test/fixture for those ids; confirm no `weight_overrides` shields it). A failure that does NOT trace to these ids is unrelated — STOP and investigate separately; do not paper over it.

- [ ] **Step 3: For each confirmed test, update ONLY the recomputed number**

Recompute the expected DMI/SMI/scorecard value with the new weights and update the assertion, adding a one-line comment citing F60. Data-driven update, not a frozen-core edit. **If a failure is a golden `store/`-shaped fixture that is actually a snapshot of a historical cycle, do NOT edit it** — instead confirm whether the test should be pinning a live recompute at all; if it's genuinely asserting historical output, the reweight should not reach it (flag as a mis-scoped test to the user rather than editing history).

- [ ] **Step 4: Re-run the full suite to confirm green**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: all green, 3–4 skips.

- [ ] **Step 5: Commit**

```bash
git add -- <the specific reconciled test files only>   # never store/**
git commit -m "test(F60): reconcile recomputed index goldens with the new leading weights"
```

---

## Task 3: Deferred-ledger discipline + verification note

**Files:**
- Modify: `docs/fix-backlog.md` (F60 entry, line ~334)
- Create: `docs/superpowers/eval-notes/2026-07-08-f60-freshness-weights-note.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the durable record that (a) the DATA half shipped and (b) F60 stays OPEN for the deferred scoring half.

- [ ] **Step 1: Amend the F60 backlog entry — record the split, do NOT check the box**

Leave the `- [ ]` checkbox **unchecked**. Append a STATUS line to the F60 entry:

```markdown
  **STATUS 2026-07-08 (S1 lane `fix/freshness-weights`): DATA half done — reweighted the
  leading DEMAND set (`rpoBacklog` 0.10→0.14, `vendorRevenueGuidance` 0.12→0.16) so
  corpus-persisted leading findings move DMI; weight-only, F6 pin green, no scoring.py
  change. F60 STAYS OPEN (Deferred Ledger §6): (1) the `scoring.py` side-semantics half
  ships as the future v1.5 migration; (2) the SMI-leading gap (no leading *supply*
  indicator exists) is unaddressed by a data reweight — needs an Option-C indicator or the
  v1.5 half. Do NOT tick F60 done on this merge.**
```

- [ ] **Step 2: Write the verification note**

Create `docs/superpowers/eval-notes/2026-07-08-f60-freshness-weights-note.md` recording: the two weight changes and rationale (leading pair ≈ ½·`apiArr`); the measured DMI effect from Task 1's behavioral test (0.22 → 0.30 on the canonical two-finding fixture); confirmation the F6 pin stayed green; and the explicit deferred residual (v1.5 scoring half + SMI-leading gap). Reference this plan.

- [ ] **Step 3: Commit**

```bash
git add docs/fix-backlog.md docs/superpowers/eval-notes/2026-07-08-f60-freshness-weights-note.md
git commit -m "docs(F60): record data-half done + keep F60 open for the deferred v1.5 half"
```

---

## Lane finish (not a TDD task — the instance-sync close protocol)

- [ ] Confirm `../../.venv/Scripts/python -m pytest -q` is green (3–4 skips) on the lane tip.
- [ ] Write `.superpowers/handoffs/freshness-weights-DONE.md`: date, branch, commit hashes, suite status, the "F60 NOT ticked done — v1.5 half + SMI residual open" reminder, and "STOPS before merge — only the user merges."
- [ ] STOP. Do not merge. Surface to the user for the merge gate.

---

## Self-Review (against the spec — wave plan §3/§6, backlog F60, D2)

1. **Spec coverage.** D2 "registry-weight DATA half only" → Tasks 1–2 (weights only, scoring.py untouched). "scoring.py side-semantics DEFERRED" / Deferred Ledger §6 "do NOT tick F60 done" → Task 3 Step 1 (box stays unchecked, residual recorded). Backlog "give the leading set real weight in registry/indicators.json" → Task 1 Step 5. Backlog "smiContribution 0.0" → addressed by scoping it OUT (Non-goals + Task 1 Step 3's `smi == 0.0` assert) with the residual logged, because no data-only change can move SMI-from-leading. B3 "eval pin per prompt change" → inverted here into the green-pin guardrail (Task 1 Step 7). B2 "P3 merges before S1 starts" → Global Constraints.
2. **Placeholder scan.** No TBD/TODO. Task 2 is contingent but its condition and action are concrete (grep the failing fixture for the two ids; update only confirmed golden). Test bodies are complete and runnable.
3. **Type consistency.** `reg.resolve(id, category_id).weight/.scoring/.side/.dimension` matches `IndicatorSpec` (verified in `test_registry_indicators.py`). `dmi_smi_contribution(findings, reg, category_id)` no-override signature matches `scoring.py:7`. `_f(ind, pd, ps, mag)` matches the helper in `test_scoring.py:6`. Expected `dmi == 0.30` derived from `weight * polarity * mag/3` with `mag=3`.

## Execution Handoff

**Two execution options:**

1. **Subagent-Driven (recommended)** — one fresh subagent per task, two-stage review between tasks. Overkill-ish for a 3-task data lane, but keeps the golden-reconciliation judgment (Task 2) honest.
2. **Inline Execution** — execute the three tasks in-session with a checkpoint after Task 1 (the substantive change) and after Task 2 (the suite reconciliation).

Given the size, **inline execution** is the pragmatic pick — but nothing runs until **P3 is merged and pushed** (B2).
