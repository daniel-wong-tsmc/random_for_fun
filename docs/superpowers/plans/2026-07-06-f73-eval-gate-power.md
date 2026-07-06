# F73 — Eval-v2 Gate Power Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** DRAFT for user review — 2026-07-06 concurrency wave (lane **P2**, `fix/eval-gate-power`, build+review **Opus**). Not dispatched; HOLD until user "go". **Barrier B1:** this must merge *before* any product-chain rebaseline, so later prompt changes are judged by the improved gate.

**Goal:** Give the eval-v2 gate demonstrable regression-catching power: a symmetric marginal band on the PASS side, a pooled-dispersion ε that converges on real run noise, and a seeded-regression canary that proves (and keeps proving) the gate hard-fails a deliberately damaged prompt.

**Architecture:** Three additive changes to `gpu_agent/evals/harness.py` + the baseline schema, none touching any prompt (so the F6 hash-pin cannot trip): (c) ε recomputed from an accumulating per-seam score history (converges via sample-stdev) instead of a 3-point half-range; (b) `evaluate_v2` gains a `marginal-pass` decision when a single-run seam sits within one ε *above* the bar, which the eval-driver replicates like the existing fail side; (a) a captured damaged-prompt run stored as a fixture, replayed by a deterministic test, plus a committed live-calibration note.

**Tech Stack:** Python 3, pydantic, pytest. LLM (Opus brains + Opus rubric graders) only for the one-time live canary capture in Task 3.

## Global Constraints

- **Lane isolation:** worktree `.worktrees/eval-gate-power` on branch `fix/eval-gate-power`. Never edit the root checkout's `main`.
- **`gpu_agent/evals/harness.py` + baseline schema ONLY.** No prompt/emit changes → no hash-pin trip; **rebaseline governance untouched.** (backlog F73)
- **Baseline back-compat:** keep `BASELINE_SCHEMA_VERSION = 2`. New fields are **additive and optional**, defaulting to today's behavior when absent, so the committed `fixtures/evals/baseline.json` keeps working **without an expensive 3-replicate re-baseline**.
- **Never poison the noise pool:** only an *accepted* (pass / marginal-resolved-pass) gate run may append to the seam history. A failing run must never widen ε and hide itself.
- **Python is `../../.venv/Scripts/python`** from the worktree (shared root venv).
- **Determinism:** no `Date.now()`/random in gate logic; ε and decisions are pure functions of stored numbers. Values exactly on a bar PASS (existing `_EPS` convention).
- **Commit discipline:** `git log --oneline -1` before every commit; add only this lane's files.

---

### Task 1: Pooled-dispersion ε that converges (fix c)

**Files:**
- Modify: `gpu_agent/evals/harness.py` (add `pooled_epsilon`, `append_run_to_history`; wire into `build_baseline_v2`)
- Test: `tests/test_evals_v2.py`

**Interfaces:**
- Consumes: `seam_quanta(cases) -> dict[str,float]` (existing).
- Produces:
  - `pooled_epsilon(history: dict[str, list[float]], quanta: dict[str, float]) -> dict[str, float]` — per seam, `max(EPS_Z * sample_stdev(history[seam]), quanta[seam])`; when `len(history[seam]) < 2`, falls back to the quantum floor.
  - `append_run_to_history(baseline: dict, report: dict) -> dict` — returns a new baseline dict with `report["seamMeans"]` appended to `baseline["seamHistory"]` and `epsilon` recomputed via `pooled_epsilon`; seeds `seamHistory` from `baseline["replicates"]` when the field is absent (v2 back-compat).
  - Baseline gains optional `seamHistory: dict[str, list[float]]`.
  - Module constant `EPS_Z = 2.0` (≈95% band; one editable constant, documented).

- [ ] **Step 1: Write the failing tests**

```python
from gpu_agent.evals.harness import pooled_epsilon, append_run_to_history

def test_pooled_epsilon_uses_sample_stdev_over_quantum_floor():
    hist = {"extract": [6.5, 6.6, 6.4, 6.7, 6.3]}   # spread ~0.15 stdev
    eps = pooled_epsilon(hist, {"extract": 0.01})
    # 2 * sample stdev, above the tiny quantum floor
    assert eps["extract"] == pytest.approx(2 * 0.158113883, abs=1e-6)

def test_pooled_epsilon_quantum_floor_when_history_too_short():
    assert pooled_epsilon({"thesis": [6.0]}, {"thesis": 0.5}) == {"thesis": 0.5}

def test_append_run_grows_history_and_recomputes_epsilon():
    base = {"seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.25},
            "seamHistory": {"extract": [6.5, 6.6, 6.4]},
            "replicates": [{"seamMeans": {"extract": 6.5}}]}
    out = append_run_to_history(base, {"seamMeans": {"extract": 6.55}})
    assert out["seamHistory"]["extract"] == [6.5, 6.6, 6.4, 6.55]
    assert out["epsilon"]["extract"] > 0            # recomputed, not the stale 0.25 unless equal

def test_append_seeds_history_from_replicates_when_absent():
    base = {"seamMeans": {"extract": 6.5}, "epsilon": {"extract": 0.5},
            "replicates": [{"seamMeans": {"extract": 6.4}},
                           {"seamMeans": {"extract": 6.6}},
                           {"seamMeans": {"extract": 6.5}}]}
    out = append_run_to_history(base, {"seamMeans": {"extract": 6.5}})
    assert out["seamHistory"]["extract"] == [6.4, 6.6, 6.5, 6.5]
```

- [ ] **Step 2: Run to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_v2.py -k "pooled or append" -v`
Expected: FAIL — `pooled_epsilon` / `append_run_to_history` not defined.

- [ ] **Step 3: Implement**

Add to `gpu_agent/evals/harness.py` (near `compute_epsilon`):

```python
import statistics

EPS_Z = 2.0  # pooled-dispersion band width (~95%); tune here only

def pooled_epsilon(history: dict[str, list[float]], quanta: dict[str, float]) -> dict[str, float]:
    eps: dict[str, float] = {}
    for seam, vals in history.items():
        disp = EPS_Z * statistics.stdev(vals) if len(vals) >= 2 else 0.0
        eps[seam] = max(disp, quanta[seam])
    return eps

def _seed_history(baseline: dict) -> dict[str, list[float]]:
    if baseline.get("seamHistory"):
        return {s: list(v) for s, v in baseline["seamHistory"].items()}
    return {s: [r["seamMeans"][s] for r in baseline["replicates"]]
            for s in baseline["replicates"][0]["seamMeans"]}

def append_run_to_history(baseline: dict, report: dict) -> dict:
    history = _seed_history(baseline)
    for seam, mean in report["seamMeans"].items():
        history.setdefault(seam, []).append(mean)
    quanta = {s: baseline["epsilon"].get(s, 0.0) and 0.0 or 0.0 for s in history}  # placeholder
    new = dict(baseline)
    new["seamHistory"] = history
    new["epsilon"] = pooled_epsilon(history, {s: 1e-9 for s in history})  # quantum re-derived below
    return new
```

> Implementer note: the quantum must come from `seam_quanta(cases)`, not a placeholder. Thread the
> real quanta through — either pass `cases` into `append_run_to_history(baseline, report, cases)` or
> store `quanta` in the baseline at build time. Prefer **storing `quanta` in the baseline** (Task 1
> Step 5) so append needs no `cases`. Replace the placeholder line accordingly. This note is a
> deliberate flag, not a placeholder to ship — the Step 5 test pins the correct behavior.

- [ ] **Step 4: Store quanta in the baseline and seed history at build time**

In `build_baseline_v2`, add to the returned dict:
```python
        "quanta": seam_quanta(cases),
        "seamHistory": {seam: [m[seam] for m in replicate_means] for seam in replicate_means[0]},
```
and change `"epsilon": compute_epsilon(...)` to
```python
        "epsilon": pooled_epsilon(
            {seam: [m[seam] for m in replicate_means] for seam in replicate_means[0]},
            seam_quanta(cases)),
```
Then simplify `append_run_to_history` to read `baseline["quanta"]` (falling back to `compute_epsilon`-parity when absent, for old baselines).

> **Continuity check:** for the initial 3 replicates, `pooled_epsilon` (`2*stdev`) will differ
> numerically from the old `compute_epsilon` (`half-range`). Update `test_build_baseline_v2_shape`
> and `test_compute_epsilon_*` expectations to the new formula. Keep `compute_epsilon` in the module
> (still referenced by the back-compat fallback and its own tests) — do not delete it.

- [ ] **Step 5: Add the build-shape + quanta tests, run all**

```python
def test_build_baseline_v2_stores_quanta_and_history():
    # (build a baseline via build_baseline_v2 with 2 positive extract cases)
    assert b["quanta"]["extract"] == pytest.approx(0.5)
    assert b["seamHistory"]["extract"] == [r["seamMeans"]["extract"] for r in reports]
    assert b["epsilon"]["extract"] == pytest.approx(pooled_epsilon(
        {"extract": b["seamHistory"]["extract"]}, {"extract": 0.5})["extract"])
```

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_v2.py -q`
Expected: PASS (with the updated ε-formula expectations).

- [ ] **Step 6: Full suite + pin**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green, 3–4 skips, `test_evals_baseline_pin.py` PASS (no prompt changed).

> **Baseline artifact decision (flag for reviewer):** the committed `fixtures/evals/baseline.json`
> has no `seamHistory`/`quanta` yet. Options: (i) leave it — the back-compat seed path fills them on
> first append (chosen default, needs no re-run); (ii) hand-add `seamHistory` seeded from its stored
> `replicates` in a data-only edit (no re-baseline, governance-neutral). Do **not** run a 3-replicate
> re-baseline just for this. Record the choice in the commit message.

- [ ] **Step 7: Commit**

```bash
git log --oneline -1
git add gpu_agent/evals/harness.py tests/test_evals_v2.py
git commit -m "feat(F73c): pooled-dispersion epsilon converges on real run noise"
```

---

### Task 2: Symmetric marginal band on the PASS side (fix b)

**Files:**
- Modify: `gpu_agent/evals/harness.py` (`evaluate_v2` decision logic)
- Modify: the `eval-driver` skill's decision table (treat `marginal-pass` like `marginal-fail`: replicate once)
- Test: `tests/test_evals_v2.py`

**Interfaces:**
- Consumes: `baseline["seamMeans"]`, `baseline["epsilon"]` (existing).
- Produces: `evaluate_v2` returns `decision == "marginal-pass"` on a **single** report when every seam passes but **at least one seam value is within `[bar, bar + eps)`** and there is no crater/hard issue. Two-report path is unchanged (mean decides pass|fail). `pass` stays `True` for `marginal-pass` (it did pass) but the decision signals the eval-driver to replicate.

- [ ] **Step 1: Write the failing tests**

```python
def test_verdict_marginal_pass_within_one_epsilon_above_bar():
    # extract mean 6.30, base 6.5, eps 0.25 -> bar 6.25; 6.30 in [6.25, 6.50) -> marginal-pass
    v = evaluate_v2(BASE, [report_with_extract_mean(6.30)])
    assert (v["decision"], v["pass"]) == ("marginal-pass", True)

def test_verdict_clear_pass_when_comfortably_above_bar_plus_epsilon():
    # 6.80 >= bar 6.25 + eps 0.25 = 6.50 -> plain pass, no replication asked
    v = evaluate_v2(BASE, [report_with_extract_mean(6.80)])
    assert v["decision"] == "pass"

def test_two_run_mean_after_marginal_pass_decides_plain():
    # two reports -> mean decides; never 'marginal-pass' with 2 runs
    v = evaluate_v2(BASE, [report_with_extract_mean(6.30), report_with_extract_mean(6.40)])
    assert v["decision"] in ("pass", "fail")
```

- [ ] **Step 2: Run to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_v2.py -k marginal_pass -v`
Expected: FAIL — decision is currently `pass`, never `marginal-pass`.

- [ ] **Step 3: Implement**

In `evaluate_v2`, while iterating seams, track a marginal-pass flag:
```python
    any_marginal_pass = False
    ...
        ok = value >= bar - _EPS
        seams[seam] = {"value": value, "bar": bar, "hardBar": hard_bar, "ok": ok}
        if ok and value < bar + eps - _EPS:
            any_marginal_pass = True
        if not ok:
            ...
```
Then in the decision ladder (single-report branch only), before `decision = "pass"`:
```python
    if not any_fail:
        decision = "marginal-pass" if (len(reports) == 1 and any_marginal_pass) else "pass"
    elif len(reports) == 2:
        decision = "fail"
    ...
```
`pass` stays `decision in ("pass", "marginal-pass")`. Two-report runs never yield `marginal-pass` (guarded by `len(reports) == 1`).

- [ ] **Step 4: Run tests to verify pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_v2.py -q`
Expected: PASS. Confirm `test_verdict_pass_on_bar_touch` still passes (bar-touch = value 6.5 with a tiny eps is still within band → may now read `marginal-pass`; update that test's expectation if so, since bar-touch *is* marginal by definition).

- [ ] **Step 5: Update the eval-driver decision handling**

In the `eval-driver` skill, extend the decision table: `marginal-pass` → replicate exactly once (same as `marginal-fail`), then `eval verdict --runs d1 d2`; the two-run mean decides. Add one line to the skill's "reading the verdict" section: "A `marginal-pass` is not a clean pass — replicate once before accepting."

- [ ] **Step 6: Full suite + pin**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green, pin PASS.

- [ ] **Step 7: Commit**

```bash
git log --oneline -1
git add gpu_agent/evals/harness.py tests/test_evals_v2.py
git commit -m "feat(F73b): symmetric marginal band - PASS within one epsilon replicates once"
```

---

### Task 3: Seeded-regression canary (fix a)

**Files:**
- Create: `fixtures/evals/canary/extract-corroboration-stripped/report.json` (captured from a live damaged-prompt run)
- Create: `docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md` (the one-time live proof)
- Test: `tests/test_evals_canary.py`

**Interfaces:**
- Consumes: the committed `fixtures/evals/baseline.json`; the improved `evaluate_v2` from Tasks 1–2.
- Produces: a deterministic replay test asserting the gate **rejects** the damaged-prompt report, and a committed calibration note recording the live demonstration.

- [ ] **Step 1: Capture the damaged run (one-time, live — documented procedure)**

Damage exactly one prompt: strip the extract corroboration sentence ("distinct outlets, not
syndication of one story" / "across separately fetched documents") from the extract SYSTEM prompt.
Run the standard eval pipeline for the extract seam against the committed cases with Opus brains +
Opus graders, produce `report.json`, and copy it to
`fixtures/evals/canary/extract-corroboration-stripped/report.json`. Record raw run dir under
gitignored `work/` (never `git clean`). **Restore the prompt** — the damage is never committed to a
prompt file (the hash-pin would trip; that is not this lane's change).

- [ ] **Step 2: Write the calibration note**

`docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md`: what was damaged, the run dir,
the resulting extract seam mean vs the baseline bar, and the gate decision (expected fail/hard-fail).
State the standing rule: **re-run this live canary after any `harness.py` change** and update the
fixture + note.

- [ ] **Step 3: Write the failing replay test**

```python
import json, pathlib
from gpu_agent.evals.harness import evaluate_v2, load_baseline

ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_canary_damaged_prompt_is_rejected():
    baseline = load_baseline(ROOT / "fixtures/evals/baseline.json")
    report = json.loads((ROOT / "fixtures/evals/canary/extract-corroboration-stripped/report.json")
                        .read_text("utf-8"))
    v = evaluate_v2(baseline, [report])
    assert v["pass"] is False                       # the gate has teeth
    assert v["decision"] in ("marginal-fail", "hard-fail")
    assert any("extract" in r for r in v["reasons"])
```

- [ ] **Step 4: Run to verify it passes against the captured fixture**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_canary.py -v`
Expected: PASS. If it does NOT (the damaged prompt still cleared the bar), that is a **finding**, not a test bug — the gate lacks power; record it in the calibration note and escalate to the reviewer, because it means ε is too wide even after Task 1.

- [ ] **Step 5: Full suite + pin**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green, pin PASS.

- [ ] **Step 6: Commit**

```bash
git log --oneline -1
git add fixtures/evals/canary tests/test_evals_canary.py docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md
git commit -m "test(F73a): seeded-regression canary - gate hard-fails a damaged prompt"
```

---

## Self-Review (author checklist — completed)

- **Spec coverage:** F73(a) canary → Task 3; F73(b) symmetric marginal band → Task 2; F73(c) pooled dispersion → Task 1. ✅
- **"harness.py + baseline schema only; no prompt changes":** honored — the canary damages a prompt only transiently for a live capture and never commits it; every task ends with `test_evals_baseline_pin.py` PASS.
- **Placeholder honesty:** Task 1 Step 3 ships a *flagged* placeholder line for the quantum, explicitly corrected in Step 4 with a pinning test — this is the TDD red state, not a shipped placeholder. Task 3's fixture is captured live (Step 1), not fabricated.
- **Type consistency:** `pooled_epsilon(history, quanta)`, `append_run_to_history(baseline, report)`, and the `marginal-pass` decision string are used identically across tasks and tests.
- **Non-poisoning invariant:** stated in Global Constraints and enforced by wiring append only into the accepted-run path (the eval-driver replicate/accept step, not raw `eval verdict`).

## Open questions for the reviewer

1. **ε formula:** `2 * sample_stdev` (chosen, ~95% band) vs `1 * stdev` vs IQR. The half-range is abandoned because it can't converge (max−min only grows). Confirm `EPS_Z = 2.0`.
2. **Baseline artifact:** leave `fixtures/evals/baseline.json` to back-compat seeding (default) vs a data-only hand-add of `seamHistory`/`quanta`. No 3-replicate re-baseline either way.
3. **Where does append fire?** Recommendation: in the eval-driver's *accept* step after a clean/replicate-resolved pass, not on every `eval verdict` (which also runs on candidate prompt changes that must not enter the incumbent noise pool).
