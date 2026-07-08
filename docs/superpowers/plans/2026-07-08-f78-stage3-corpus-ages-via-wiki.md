# F78 Stage 3 — Corpus ages via the wiki (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the corpus from keeping a store fact just because its cycle stamp (`asOf`) is inside a flat 45-day window. Instead, surface a fact on its **decayed effective salience** — the page's intrinsic salience decayed over the fact's **real age in calendar days** (`observedAt` vs the run's `asOf`) through the wiki's own half-life/decay curve — against a **salience floor** (a decay-based cutoff, not a cycle window), PLUS its page's **lifecycle state** (pruned pages excluded). Remove the flat `asOf` `window_days` filter. `assemble()` still unions the aged store corpus with this cycle's fresh gated findings. Also consolidate `corpus.py`'s date logic onto `gpu_agent/asof.py`.

**Architecture:** Today `corpus.enumerate_store` keeps a finding when `in_window(f.asOf, as_of, 45)` — it reads the *cycle stamp*, never the evidence's real age, so old-content findings pile up (measured live: stale-secondary evidence grew 5→8 across the 2026-07 v2→v4 flagships; a finding whose evidence is dated **2025-08-22** — 343 days before the 2026-07 flagship — rode into v4). This stage replaces that window with `aged_salience(finding, page.salience, as_of, horizons)` = `effective_salience(max(salience_floor, page.salience), days_between(as_of, finding.observedAt), half_life([finding]))`, kept iff `>= SALIENCE_FLOOR` (0.1). It reuses the wiki's decay machinery unchanged (`half_life`/`decay`/`effective_salience`, now in **calendar days** from F78 Stage 1) — only the corpus's *selection rule* changes. A pruned page is excluded whole before per-fact aging.

**Tech Stack:** Python 3.11, pydantic v2, pytest. Run Python as `.venv/Scripts/python` from repo root (from the worktree: `../../.venv/Scripts/python`).

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` — §5.3 (this is D4), §7 (testing / shadow-check), §8 (risks). This is **F78 Stage 3** of the build order in §9. **Depends on F78 Stage 1** having landed: `gpu_agent/asof.py` exists (`period_end`, `days_between`, `AsOfError`), and `wiki/lint.py`'s `quiet_age`/`half_life` are in **calendar days** (`LintConfig.h_short_days/h_med_days/h_long_days`, `stale_threshold`, `salience_floor` intact).

## Global Constraints

- **Determinism, never wall-clock:** all day-math derives from `asOf`/`observedAt` labels via `asof.period_end`/`days_between`; the corpus must stay "same inputs → byte-identical output". No `datetime.now()`, `Date.now()`, `Math.random()`.
- **Frozen core untouched:** do NOT modify `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`. `corpus.py` and `wiki/*` are **not** frozen core. This stage touches `gpu_agent/corpus.py`, `gpu_agent/cli.py` (corpus wiring only), and their tests.
- **Eval pin stays green:** no emitted brain-prompt bytes change here; `tests/test_evals_baseline_pin.py` must stay green. If it goes red, you touched a prompt path — stop and re-scope.
- **Provisional numbers (D5):** the salience floor `0.1` and the intrinsic floor `0.5` are the wiki's existing `stale_threshold` / `salience_floor` values, reused deliberately; they are tunable and recalibrated later. Do not invent new magic numbers.
- **Shadow-check required (§5.3, §7):** Task 6 runs the new aged corpus over the stored 2026-07 v1–v4 flagships and the recent dailies, diffs the surfaced findings against the old window rule, and confirms the pile-up drops (the 2025-08-22 / ~343-day NVIDIA content, the 2026-01-15 / ~174-day AMD content) while live fundamentals (the ~49–64-day quarterly earnings) stay. **No stored scorecard is edited** (read-only diagnostic).
- **Suite green at every commit.** Baseline before starting: `.venv/Scripts/python -m pytest -q` and record the pass count (expect 3–4 skips).
- **Execution happens in a git worktree** per repo discipline: create/claim `.worktrees/f78-stage3-corpus` on a claimed branch; never work on the root checkout's `main`; one shared root venv (never a per-worktree venv). `git log --oneline -1` immediately before every commit (concurrent-instance guard).
- **Windows:** use the Bash tool for `>` redirects / heredocs; no double quotes inside `git commit -m` under PowerShell (use a bash heredoc). Commit trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task 0: Worktree + baseline

- [ ] Create/enter the worktree and confirm the suite is green from a known-good base.

```bash
cd /c/Users/danie/random_for_fun
git worktree add .worktrees/f78-stage3-corpus -b f78-stage3-corpus-ages-via-wiki
cd .worktrees/f78-stage3-corpus
../../.venv/Scripts/python -m pytest -q 2>&1 | tail -5   # record the pass/skip counts
```
Expected: suite green (3–4 skips). If red, stop — you are not on a clean base.

> All subsequent `pytest`/`git` commands run from inside `.worktrees/f78-stage3-corpus`. Python is `../../.venv/Scripts/python`.

---

### Task 1: Consolidate onto `asof.py` + add the aging primitives

Remove the corpus-local date logic and the window constant; import the shared helpers from `gpu_agent.asof` (Stage 1). Add the two pure primitives the new selection rule is built from: `aged_salience` (a fact's decayed effective salience) and `_is_pruned` (the lifecycle gate). Delete the now-obsolete `tests/test_corpus_window.py`.

**Files:**
- Modify: `gpu_agent/corpus.py` (imports, module docstring, constants; add `aged_salience`, `_is_pruned`; delete `period_end`, `in_window`, `_DAY_RE`, `_MONTH_RE`, `WINDOW_DAYS_DEFAULT`)
- Create: `tests/test_corpus_aging.py`
- Delete: `tests/test_corpus_window.py`

**Interfaces:**
- Consumes: `gpu_agent.asof.days_between`/`AsOfError` (Stage 1); `gpu_agent.wiki.lint` (`DEFAULT_LINT_CONFIG`, `half_life`, `effective_salience`); `gpu_agent.wiki.lifecycle.DEFAULT_LIFECYCLE_CONFIG`.
- Produces: `SALIENCE_FLOOR_DEFAULT: float` (= `DEFAULT_LINT_CONFIG.stale_threshold`, 0.1); `aged_salience(finding, page_salience, as_of, horizons, config=DEFAULT_LINT_CONFIG) -> float`; `_is_pruned(store, page_id, page, lifecycle_config=DEFAULT_LIFECYCLE_CONFIG) -> bool`. `CorpusError` stays (store-integrity only).

- [ ] **Step 1: Write the failing test** — `tests/test_corpus_aging.py`

```python
# tests/test_corpus_aging.py — F78 Stage 3 aging primitives.
# Repo convention: LOCAL factories per file (tests/ is not a package).
from gpu_agent.asof import days_between
from gpu_agent.corpus import SALIENCE_FLOOR_DEFAULT, aged_salience, _is_pruned
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.lint import effective_salience
from gpu_agent.wiki.store import PageNotFound, WikiStore

WEEKLY = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}})
QUARTERLY = IndicatorHorizons({"designWins": {"cadence": "quarterly", "horizon": "lagging"}})


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def test_salience_floor_is_the_wiki_stale_threshold():
    assert SALIENCE_FLOOR_DEFAULT == 0.1


def test_aged_salience_wires_floor_age_and_cadence():
    # unscored page (salience 0.0) -> intrinsic floored to salience_floor (0.5);
    # age = days_between(as_of, observedAt); half-life = weekly -> h_med_days (21).
    f = _f("f1", observedAt="2026-06-01")
    expected = effective_salience(0.5, days_between("2026-07", "2026-06-01"), 21)
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) == expected


def test_aged_salience_uses_page_salience_when_above_floor():
    f = _f("f1", observedAt="2026-07-30")
    expected = effective_salience(0.9, days_between("2026-07", "2026-07-30"), 21)
    assert aged_salience(f, 0.9, "2026-07", WEEKLY) == expected


def test_aged_salience_monotonic_in_age():
    fresh = _f("fresh", observedAt="2026-07-30")
    old = _f("old", observedAt="2026-01-15")
    assert aged_salience(fresh, 0.0, "2026-07", WEEKLY) > aged_salience(old, 0.0, "2026-07", WEEKLY)


def test_aged_salience_quarterly_outlives_weekly():
    # a ~72-day fact: fades under a weekly half-life, survives under a quarterly one.
    f = _f("f1", observedAt="2026-05-20")
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) < SALIENCE_FLOOR_DEFAULT
    assert aged_salience(f, 0.0, "2026-07", QUARTERLY) >= SALIENCE_FLOOR_DEFAULT


def test_aged_salience_clamps_future_observed_at():
    # observedAt after as_of (out-of-order label) clamps age to 0 -> no decay, full intrinsic.
    f = _f("f1", observedAt="2026-09-01")
    assert aged_salience(f, 0.0, "2026-07", WEEKLY) == effective_salience(0.5, 0, 21)


def test_is_pruned_true_only_for_scored_then_floored(tmp_path):
    store = _store(tmp_path)
    store.create_page("entity:a", "entity", "A", category="chips.merchant-gpu", as_of="2026-06")
    # scored, then lifecycle-floored to 0.0 (a real prune) -> excluded
    store.record_state("entity:a", as_of="2026-06", state="live", trajectory="steady", salience=0.6)
    store.record_state("entity:a", as_of="2026-07", state="live", trajectory="steady", salience=0.0)
    assert _is_pruned(store, "entity:a", store.get_page("entity:a")) is True


def test_is_not_pruned_when_never_scored(tmp_path):
    # a never-scored page (salience default 0.0, no state-change) is NOT pruned — the live-store case.
    store = _store(tmp_path)
    store.create_page("entity:b", "entity", "B", category="chips.merchant-gpu", as_of="2026-07")
    assert _is_pruned(store, "entity:b", store.get_page("entity:b")) is False
```

- [ ] **Step 2: Run it — verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_aging.py -q`
Expected: FAIL — `ImportError: cannot import name 'aged_salience'` (and `SALIENCE_FLOOR_DEFAULT`/`_is_pruned`).

- [ ] **Step 3: Edit `gpu_agent/corpus.py`** — replace the top-of-file block (lines 1–56, the module docstring through `in_window`) with the consolidated imports, constant, and primitives.

Replace the module docstring + imports + label helpers with:

```python
"""gpu_agent/corpus.py — the flagship input corpus (F62; F78 Stage 3: ages via the wiki).

Read-only consumer of existing stores: the wiki (page index + observations) as the
category-scoped index over the canonical FindingStore, and the L2 dedup classifier for
fresh-vs-store classification. Assembles the AGED accumulated store findings plus this
cycle's fresh gated findings into ONE merged corpus for the judge/thesis brains and the
scorecard, and reports coverage so the gather can run as a top-up.

F78 Stage 3 (D4): the flat 45-day `asOf` window is gone. A store fact now survives on its
decayed effective salience — the page's intrinsic salience (floored at the wiki's
salience_floor, as _score_move already treats it) decayed over the fact's REAL age in
calendar days (`as_of` period-end minus the fact's `observedAt`) via the fact's cadence
half-life — against a salience floor, PLUS its page's lifecycle state (pruned pages
excluded). Genuinely superseded old facts fade toward zero and drop out; a fresh
observation dominates. It reuses the wiki's decay curve unchanged (half_life/decay/
effective_salience, now in calendar days — F78 Stage 1); only the corpus's SELECTION rule
changes.

This module never writes anything: no store mutation, no file writes, no clock reads. All
day-math derives from `asOf`/`observedAt` labels via gpu_agent.asof — never wall-clock — so
replays/backtests are deterministic and a past cycle never sees a future label.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.asof import AsOfError, days_between  # F78-3: shared date logic (was corpus-local)
from gpu_agent.gathering.dedup import DEFAULT_DEDUP_CONFIG, FindingClass, classify_findings
from gpu_agent.schema.finding import Finding
from gpu_agent.store import FindingNotFound, FindingStore
from gpu_agent.wiki.lifecycle import DEFAULT_LIFECYCLE_CONFIG
from gpu_agent.wiki.lint import DEFAULT_LINT_CONFIG, effective_salience, half_life
from gpu_agent.wiki.store import WikiStore

# F78 Stage 3: the decayed-effective-salience cutoff below which an aged store fact drops
# from the baseline corpus. This is the wiki's OWN "this fact has faded" line
# (LintConfig.stale_threshold, 0.1) — a decay-based cutoff, never a cycle-count window (D4).
# NOTE: distinct from LintConfig.salience_floor (0.5), which is the intrinsic-salience WEIGHT
# floor reused inside aged_salience below.
SALIENCE_FLOOR_DEFAULT = DEFAULT_LINT_CONFIG.stale_threshold  # 0.1


class CorpusError(ValueError):
    """Raised on canonical-store integrity violations (fail loud). Invalid asOf/observedAt
    labels raise gpu_agent.asof.AsOfError (a sibling ValueError) from the shared date logic."""


def aged_salience(finding: Finding, page_salience: float, as_of: str, horizons,
                  config=DEFAULT_LINT_CONFIG) -> float:
    """A store fact's decayed effective salience at `as_of`: the page's intrinsic salience —
    floored at the wiki's salience_floor so an unscored page still starts from a baseline
    (matching _score_move's `max(salience_floor, page.salience)` treatment) — decayed over the
    fact's REAL age in calendar days (`as_of` period-end minus the fact's `observedAt`, clamped
    at 0) via the fact's cadence half-life. Uses the wiki's own decay/effective_salience curve
    (now in calendar days — F78 Stage 1)."""
    intrinsic = max(config.salience_floor, page_salience)
    age_days = max(0, days_between(as_of, finding.observedAt))
    hl, _ = half_life([finding], horizons, config)
    return effective_salience(intrinsic, age_days, hl)


def _is_pruned(store, page_id, page, lifecycle_config=DEFAULT_LIFECYCLE_CONFIG) -> bool:
    """True iff the page has been lifecycle-pruned. The wiki represents a prune by flooring a
    (previously scored) page's salience to prune_salience_floor via a state-change
    (lifecycle.apply_lifecycle). A page whose salience is at/below that floor AND that carries a
    state-change history was scored then pruned; a never-scored page (salience default 0.0, no
    state-change) is NOT pruned. archived/retired are not wiki-page states in the current model,
    so 'pruned' is the operative lifecycle exclusion."""
    return (page.salience <= lifecycle_config.prune_salience_floor
            and bool(store.state_history(page_id)))
```

Then **delete** the old `period_end` and `in_window` functions (old lines 38–56) and the `WINDOW_DAYS_DEFAULT` constant / `_DAY_RE` / `_MONTH_RE` — they are fully replaced by `gpu_agent.asof` and the aging rule. (`CoverageEntry`, `SkippedPage`, `CorpusReport`, etc. below are handled in Tasks 2–3.)

- [ ] **Step 4: Delete the obsolete window test**

`tests/test_corpus_window.py` tests `period_end`, `in_window`, and `WINDOW_DAYS_DEFAULT` — all removed. Its bad-label case (`test_period_end_rejects_bad_labels`, which asserted **`CorpusError`**) is superseded by Stage 1's `tests/test_asof.py::test_period_end_bad_shape_fails_loud` (which asserts **`AsOfError`**). Its `CorpusReport`/`CorpusResult` shape assertions are relocated in Task 3.

```bash
git rm tests/test_corpus_window.py
```

- [ ] **Step 5: Run it — verify it passes**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_aging.py -q`
Expected: PASS (8 passed). `tests/test_corpus_enumerate.py`, `_assemble.py`, `_coverage.py` will now FAIL to import (window symbols gone) — expected, fixed in Tasks 2–3.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_aging.py
git rm --cached tests/test_corpus_window.py 2>/dev/null; true
git commit -m "$(cat <<'EOF'
feat(F78-3): consolidate corpus dates onto asof.py; add aged_salience + _is_pruned primitives

Removes corpus-local period_end/in_window/WINDOW_DAYS_DEFAULT. Adds the decay-based
selection rule primitives (aged_salience over observedAt, lifecycle prune gate) that
replace the flat asOf window. Bad-label errors now raise asof.AsOfError.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `enumerate_store` ages facts and excludes pruned pages

Replace the `in_window` filter with the aged-salience rule and the lifecycle gate. The return tuple grows a fourth member (`lifecycle_excluded`) and renames `out_of_window` → `faded_out`.

**Files:**
- Modify: `gpu_agent/corpus.py` (`enumerate_store`)
- Modify: `tests/test_corpus_enumerate.py`

**Interfaces:**
- Consumes: `horizons` (an `IndicatorHorizons`), `salience_floor` (default `SALIENCE_FLOOR_DEFAULT`), `config` (default `DEFAULT_LINT_CONFIG`).
- Produces: `enumerate_store(store_root, category, as_of, horizons, *, salience_floor=SALIENCE_FLOOR_DEFAULT, config=DEFAULT_LINT_CONFIG) -> tuple[list[Finding], int, list[SkippedPage], list[SkippedPage]]` = `(included, faded_out, skipped_wrong_category, lifecycle_excluded)`.

- [ ] **Step 1: Rewrite the failing test** — replace `tests/test_corpus_enumerate.py` (keep the file's local `_store`/`_f`/`_seed` block; add the horizons import + fixture; rewrite the assertions).

```python
import pytest

from gpu_agent.corpus import CorpusError, enumerate_store
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

# designWins tagged weekly -> half-life h_med_days (21). At as_of 2026-07 (period end
# 2026-07-31) a weekly fact fades below the 0.1 floor once its observedAt age exceeds ~49 days.
HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}})


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-30"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_missing_wiki_dir_is_honest_empty(tmp_path):
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == [] and faded == 0 and skipped == [] and excluded == []


def test_fresh_facts_surface_sorted(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("b-2", as_of="2026-07-03", observedAt="2026-07-29"), "2026-07-03")
    _seed(store, _f("a-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["a-1", "b-2"]   # sorted by (asOf, id)
    assert faded == 0 and skipped == [] and excluded == []


def test_old_content_fades_and_is_counted_not_listed(tmp_path):
    # cycle stamp is recent (asOf 2026-07-02) but the evidence is dated 2026-01-15 (~197 days):
    # under the OLD window it rode forward; under aging it fades below the floor and drops.
    store = _store(tmp_path)
    _seed(store, _f("stale-1", as_of="2026-07-02", observedAt="2026-01-15"), "2026-07-02")
    _seed(store, _f("fresh-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    included, faded, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["fresh-1"]
    assert faded == 1


def test_pruned_page_excluded_whole_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("on-pruned", observedAt="2026-07-30"), "2026-07-02", pid="entity:amd")
    # scored, then lifecycle-floored to 0.0 -> the whole page is a lifecycle exclusion
    store.record_state("entity:amd", as_of="2026-07-02", state="live", trajectory="steady", salience=0.6)
    store.record_state("entity:amd", as_of="2026-07-03", state="live", trajectory="steady", salience=0.0)
    included, faded, skipped, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == [] and faded == 0 and skipped == []
    assert [(s.id, s.category) for s in excluded] == [("entity:amd", "chips.merchant-gpu")]


def test_never_scored_page_surfaces_its_fresh_facts(tmp_path):
    # the live-store case: salience 0.0 with no state-change is NOT pruned; intrinsic floors to 0.5.
    store = _store(tmp_path)
    _seed(store, _f("live-1", observedAt="2026-07-30"), "2026-07-02")
    included, faded, _, excluded = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["live-1"] and excluded == []


def test_wrong_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("mine-1"), "2026-07-02", category="chips.merchant-gpu")
    _seed(store, _f("theirs-1", entity="OPENAI"), "2026-07-02", category="models.frontier-closed")
    included, _, skipped, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [f.id for f in included] == ["mine-1"]
    assert [(s.id, s.category) for s in skipped] == [("entity:openai", "models.frontier-closed")]


def test_absent_category_page_skipped_and_reported(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("nocat-1"), "2026-07-02", category=None)
    included, _, skipped, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert included == []
    assert [(s.id, s.category) for s in skipped] == [("entity:nvda", None)]


def test_same_finding_on_two_pages_deduplicated(tmp_path):
    store = _store(tmp_path)
    f = _f("shared-1", observedAt="2026-07-30")
    _seed(store, f, "2026-07-02")
    store.create_page("entity:amd", "entity", "AMD", category="chips.merchant-gpu", as_of="2026-07-02")
    store.append_observation("entity:amd", f.id, as_of="2026-07-02")
    included, _, _, _ = enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
    assert [x.id for x in included] == ["shared-1"]


def test_dangling_observation_fails_loud(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("ok-1", observedAt="2026-07-30"), "2026-07-02")
    (tmp_path / "findings" / "ok-1.json").unlink()   # corrupt the canonical store
    with pytest.raises(CorpusError, match="ok-1"):
        enumerate_store(tmp_path, "chips.merchant-gpu", "2026-07", HZ)
```

- [ ] **Step 2: Run it — verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_enumerate.py -q`
Expected: FAIL — `enumerate_store` still has the old signature/`in_window` body.

- [ ] **Step 3: Rewrite `enumerate_store` in `gpu_agent/corpus.py`**

```python
def enumerate_store(store_root, category: str, as_of: str, horizons, *,
                    salience_floor: float = SALIENCE_FLOOR_DEFAULT,
                    config=DEFAULT_LINT_CONFIG,
                    ) -> tuple[list[Finding], int, list["SkippedPage"], list["SkippedPage"]]:
    """The AGED store corpus for `category`: every finding observed by a category-matching wiki
    page, deduplicated across pages, kept iff its decayed effective salience (aged_salience) is at
    or above `salience_floor`, sorted by (asOf, id). Pruned pages are excluded whole (lifecycle
    gate) BEFORE per-fact aging. Pages with a different or absent category are skipped AND reported.
    A faded fact (below the floor) is COUNTED, not listed. A dangling/unreadable observation finding
    fails loud: the canonical store is trusted input, corruption is a stop-the-line event.
    Returns (included, faded_out, skipped_wrong_category, lifecycle_excluded)."""
    store_root = Path(store_root)
    wiki_dir = store_root / "wiki"
    if not wiki_dir.is_dir():
        return [], 0, [], []   # honest empty: no wiki yet (first-ever cycle)
    store = WikiStore(wiki_dir, FindingStore(store_root / "findings"))
    included: list[Finding] = []
    seen_ids: set[str] = set()
    faded_out = 0
    skipped: list[SkippedPage] = []
    lifecycle_excluded: list[SkippedPage] = []
    for entry in store.index():
        if entry.category != category:
            skipped.append(SkippedPage(id=entry.id, category=entry.category))
            continue
        page = store.get_page(entry.id)
        if _is_pruned(store, entry.id, page):
            lifecycle_excluded.append(SkippedPage(id=entry.id, category=entry.category))
            continue
        for obs in store.observations(entry.id):
            if obs.findingId in seen_ids:
                continue
            seen_ids.add(obs.findingId)
            try:
                f = store.findings.get(obs.findingId)
            except (FindingNotFound, ValueError) as e:
                raise CorpusError(
                    f"store integrity: page {entry.id} observation references "
                    f"unreadable finding {obs.findingId}: {e}") from e
            if aged_salience(f, page.salience, as_of, horizons, config) >= salience_floor:
                included.append(f)
            else:
                faded_out += 1
    included.sort(key=lambda f: (f.asOf, f.id))
    return included, faded_out, skipped, lifecycle_excluded
```

- [ ] **Step 4: Run it — verify it passes**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_enumerate.py -q`
Expected: PASS (9 passed). (`test_corpus_assemble.py`/`_coverage.py` still fail — Task 3.)

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_enumerate.py
git commit -m "$(cat <<'EOF'
feat(F78-3): enumerate_store ages facts by observedAt decay + excludes pruned pages

Replaces the flat in_window(asOf) filter with aged_salience >= salience_floor and a
lifecycle prune gate. Return tuple gains lifecycle_excluded; out_of_window -> faded_out.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `CorpusReport` + `assemble` + `coverage` + `render_coverage_text`

Drop the window fields from the report; add `salienceFloor`, `fadedOut`, `lifecycleExcluded`. Thread `horizons`/`salience_floor` through `assemble`. `coverage` logic is unchanged (it operates on whatever store findings survived aging); only its docstring wording updates. `render_coverage_text` describes the aged floor instead of the window.

**Files:**
- Modify: `gpu_agent/corpus.py` (`CorpusReport`, `assemble`, `coverage` docstring, `render_coverage_text`)
- Modify: `tests/test_corpus_assemble.py`, `tests/test_corpus_coverage.py`

**Interfaces:**
- Produces: `assemble(store_root, category, as_of, fresh, registry, horizons, *, salience_floor=SALIENCE_FLOOR_DEFAULT, config=DEFAULT_LINT_CONFIG) -> CorpusResult`. `CorpusReport` gains `salienceFloor: float`, `fadedOut: int`, `lifecycleExcluded: list[SkippedPage]`; loses `windowDays`, `windowStart`, `windowEnd`, `outOfWindow`.

- [ ] **Step 1: Rewrite the failing tests**

In `tests/test_corpus_assemble.py`: add `from gpu_agent.registry.horizon import IndicatorHorizons`, define `HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"}, "rpoBacklog": {"cadence": "quarterly", "horizon": "lagging"}})`, change every `_f(...)` seeded into the store to carry a fresh `observedAt="2026-07-30"` (so it survives aging), and pass `HZ` into every `assemble(...)` call. Update the report-shape assertions:

```python
def test_assemble_empty_store_merged_equals_fresh(tmp_path):
    fresh = [_f("fresh-1", indicatorId="rpoBacklog")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    assert [f.id for f in res.merged] == ["fresh-1"]
    assert [f.id for f in res.dedupedFresh] == ["fresh-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]
    assert res.report.storeIncluded == []
    assert res.report.salienceFloor == 0.1 and res.report.fadedOut == 0
    assert res.report.lifecycleExcluded == []


def test_assemble_store_plus_fresh_new(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", entity="AMD", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    fresh = [_f("fresh-1", entity="NVDA", indicatorId="rpoBacklog", as_of="2026-07")]
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", fresh, REGISTRY, HZ)
    assert [f.id for f in res.merged] == ["store-1", "fresh-1"]   # store part first
    assert res.report.storeIncluded == ["store-1"]
    assert [fc.findingId for fc in res.report.freshNew] == ["fresh-1"]
```

Add a report-shape test relocated from the deleted `test_corpus_window.py`:

```python
def test_report_model_shape():
    from gpu_agent.corpus import CorpusReport, CorpusResult
    r = CorpusReport(asOf="2026-07", category="chips.merchant-gpu", salienceFloor=0.1)
    assert r.storeIncluded == [] and r.fadedOut == 0 and r.skippedPages == []
    assert r.lifecycleExcluded == []
    assert r.freshNew == [] and r.freshUpdate == [] and r.freshDuplicate == []
    assert r.idOverlaps == [] and r.coverage == [] and r.notCovered == []
    res = CorpusResult(report=r)
    assert res.merged == [] and res.dedupedFresh == []
```

Update the remaining `test_corpus_assemble.py` cases (`test_assemble_fresh_duplicate_dropped_and_reported`, `test_assemble_id_overlap_keeps_store_copy`, `test_assemble_deterministic`) the same way: give each store-seeded `_f` a fresh `observedAt="2026-07-30"` and pass `HZ` as the sixth positional arg to `assemble`.

In `tests/test_corpus_coverage.py`: add the same `IndicatorHorizons`/`HZ` import, give store-seeded findings `observedAt="2026-07-30"`, pass `HZ` to the two `assemble(...)` calls, and update the render test's header line + `CorpusReport` construction:

```python
def test_assemble_fills_coverage(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [], REGISTRY, HZ)
    assert [e.indicatorId for e in res.report.coverage] == ["designWins"]
    assert "designWins" not in res.report.notCovered


def test_render_coverage_text_covered_and_gaps():
    report = CorpusReport(
        asOf="2026-07", category="chips.merchant-gpu", salienceFloor=0.1,
        storeIncluded=["a-1"],
        coverage=[{"entity": "NVDA", "indicatorId": "designWins", "count": 2,
                   "latestAsOf": "2026-07-03", "latestObservedAt": "2026-07-03"}],
        notCovered=["leadTimes", "rpoBacklog"])
    text = render_coverage_text(report)
    lines = text.splitlines()
    assert lines[0] == "STORE COVERAGE (aged, salience floor 0.1, 1 finding(s)):"
    assert "  NVDA designWins: 2 finding(s), latest asOf 2026-07-03 (observed 2026-07-03)" in lines
    assert "  not covered: leadTimes, rpoBacklog" in lines


def test_render_coverage_text_empty_store_names_full_gather():
    report = CorpusReport(asOf="2026-07", category="c", salienceFloor=0.1)
    assert "(no store coverage — full gather)" in render_coverage_text(report)


def test_render_deterministic():
    report = CorpusReport(asOf="2026-07", category="c", salienceFloor=0.1)
    assert render_coverage_text(report) == render_coverage_text(report)
```

(`test_coverage_entries_latest_and_count` and `test_coverage_empty_store` call `coverage(...)` directly and need no change beyond existing.)

- [ ] **Step 2: Run them — verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_assemble.py tests/test_corpus_coverage.py -q`
Expected: FAIL — `assemble` still window-shaped; `CorpusReport` lacks `salienceFloor`.

- [ ] **Step 3: Edit `gpu_agent/corpus.py`**

Replace `CorpusReport` (drop window fields, add the aged ones):

```python
class CorpusReport(BaseModel):
    asOf: str
    category: str
    salienceFloor: float
    storeIncluded: list[str] = Field(default_factory=list)      # finding ids, sorted with merged order
    fadedOut: int = 0                                           # aged below the floor, dropped
    skippedPages: list[SkippedPage] = Field(default_factory=list)        # wrong/absent category
    lifecycleExcluded: list[SkippedPage] = Field(default_factory=list)   # pruned pages
    freshNew: list[FindingClass] = Field(default_factory=list)
    freshUpdate: list[FindingClass] = Field(default_factory=list)
    freshDuplicate: list[FindingClass] = Field(default_factory=list)
    idOverlaps: list[str] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    notCovered: list[str] = Field(default_factory=list)
```

Replace `assemble` (new signature; no window math; new report fields):

```python
def assemble(store_root, category: str, as_of: str, fresh: list[Finding], registry, horizons, *,
             salience_floor: float = SALIENCE_FLOOR_DEFAULT, config=DEFAULT_LINT_CONFIG) -> CorpusResult:
    """The F62 merged corpus: the AGED store findings (F78 Stage 3) + this cycle's fresh gated
    findings, classified against the store by the existing L2 machinery (intra-batch collapse +
    evidence-merge, then cross-store NEW/UPDATE keep vs DUPLICATE drop). The store part is never
    collapsed: it holds only NEW/UPDATE vintages by construction and multiple vintages of one
    series are deliberate history — scoring takes latest-per-series, the judge sees the (dated)
    evolution. An id overlap means the identical finding is already stored: the store copy is kept
    and the event reported. `registry` feeds the coverage table (store part only); `horizons`
    supplies each fact's cadence half-life for aging."""
    store_root = Path(store_root)
    store_findings, faded_out, skipped, lifecycle_excluded = enumerate_store(
        store_root, category, as_of, horizons, salience_floor=salience_floor, config=config)
    wiki = WikiStore(store_root / "wiki", FindingStore(store_root / "findings"))
    res = classify_findings(fresh, wiki, config=DEFAULT_DEDUP_CONFIG)
    store_ids = {f.id for f in store_findings}
    id_overlaps = sorted(f.id for f in res.outFindings if f.id in store_ids)
    fresh_keeps = [f for f in res.outFindings if f.id not in store_ids]
    merged = store_findings + fresh_keeps
    cov_entries, not_covered = coverage(store_findings, registry)
    report = CorpusReport(
        asOf=as_of, category=category, salienceFloor=salience_floor,
        storeIncluded=[f.id for f in store_findings],
        fadedOut=faded_out, skippedPages=skipped, lifecycleExcluded=lifecycle_excluded,
        freshNew=res.new, freshUpdate=res.update, freshDuplicate=res.duplicate,
        idOverlaps=id_overlaps,
        coverage=cov_entries, notCovered=not_covered,
    )
    return CorpusResult(merged=merged, dedupedFresh=fresh_keeps, report=report)
```

In `coverage`, update only the docstring first line: `"""Per (entity, indicatorId) over the AGED STORE part: count + latest vintage."""` (logic unchanged — it counts whatever survived aging).

Replace `render_coverage_text`:

```python
def render_coverage_text(report: CorpusReport) -> str:
    """Deterministic coverage block for the gather-category dispatch (run-cycle step a0):
    one header line naming the aged salience floor, one line per covered series, one not-covered line."""
    lines = [f"STORE COVERAGE (aged, salience floor {report.salienceFloor:g}, "
             f"{len(report.storeIncluded)} finding(s)):"]
    if not report.coverage:
        lines.append("  (no store coverage — full gather)")
    for c in report.coverage:
        lines.append(f"  {c.entity} {c.indicatorId}: {c.count} finding(s), "
                     f"latest asOf {c.latestAsOf} (observed {c.latestObservedAt})")
    if report.notCovered:
        lines.append("  not covered: " + ", ".join(report.notCovered))
    return "\n".join(lines)
```

- [ ] **Step 4: Run them — verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_corpus_assemble.py tests/test_corpus_coverage.py tests/test_corpus_aging.py tests/test_corpus_enumerate.py -q`
Expected: PASS (all corpus-unit tests green).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/corpus.py tests/test_corpus_assemble.py tests/test_corpus_coverage.py
git commit -m "$(cat <<'EOF'
feat(F78-3): CorpusReport/assemble report aged salience floor, faded-out, lifecycle-excluded

assemble() gains horizons + salience_floor; drops the windowDays/windowStart/windowEnd/
outOfWindow fields; render_coverage_text names the aged floor instead of the window.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: CLI wiring — thread horizons + salience floor, drop the window flags

`corpus.assemble` gains required `horizons`; the two CLI call sites (`_corpus`, the pipeline seam) must load `IndicatorHorizons` and pass it, swap `--window-days`/`--corpus-window-days` for `--salience-floor`/`--corpus-salience-floor`, catch `AsOfError` alongside `CorpusError`, and update the "in-window"/"out" wording in the printed summaries and the report loop (`outOfWindow` → `fadedOut`; surface `lifecycleExcluded`).

**Files:**
- Modify: `gpu_agent/cli.py` (imports; `_corpus`; the pipeline `--corpus-store` block; argparse for `corpus` and `pipeline`)
- Modify: `tests/test_cli_corpus.py`, `tests/test_cli_pipeline_corpus.py`, `tests/test_cli_sufficiency.py`

> Note on back-compat: the live `run-cycle` SKILL.md pipeline invocation passes `--corpus-store`/`--corpus-report` but **not** any window flag (it used the default), so removing the flag does not break the live path. The only reference to the old flag names is a doc line in `.claude/skills/desk-config-and-flags/references/cli-verbs.md` — flag that as a **non-blocking follow-up doc fix**, out of scope here.

- [ ] **Step 1: Update the failing CLI tests**

In `tests/test_cli_corpus.py`: change the summary assertion (line ~94) from
`"store 1 in-window (0 out), fresh new 1 update 0 duplicate 0 -> merged 2"` to
`"store 1 aged (0 faded), fresh new 1 update 0 duplicate 0 -> merged 2"`. If any test invokes the CLI with `--window-days`, change it to `--salience-floor`. Ensure the seeded store findings carry a fresh `observedAt` (default `_f` observedAt is `2026-07-01`; at as_of `2026-07` that is ~30 days → weekly `designWins` survives — keep, but if a test uses an old observedAt update it to `2026-07-30`).

In `tests/test_cli_pipeline_corpus.py`: change the stderr assertion (line ~105) from `"corpus: store 1 in-window"` to `"corpus: store 1 aged"`; adjust the line-55 comment wording ("in-window" → "surfaced"). Confirm the seeded store finding's `observedAt` is fresh enough to survive aging under its indicator's cadence (use `observedAt="2026-07-30"` at as_of `2026-07`).

In `tests/test_cli_sufficiency.py`: if it asserts any "in-window"/"out" corpus summary string or passes `--corpus-window-days`, update to the aged wording / `--corpus-salience-floor`. (Run it first to see whether it references the corpus summary at all; many sufficiency tests only assert gate output.)

- [ ] **Step 2: Run them — verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_cli_corpus.py tests/test_cli_pipeline_corpus.py -q`
Expected: FAIL (old strings / missing horizons arg).

- [ ] **Step 3: Edit `gpu_agent/cli.py`**

Imports (line ~51–52) — drop `WINDOW_DAYS_DEFAULT`, add `SALIENCE_FLOOR_DEFAULT` and the `AsOfError`:

```python
from gpu_agent.asof import AsOfError
from gpu_agent.corpus import (
    SALIENCE_FLOOR_DEFAULT, CorpusError, assemble as corpus_assemble, render_coverage_text)
```

In `_corpus` (after `registry, _ = _load_registry()`, ~line 174) load horizons and swap the call + error catch + report loop + summary:

```python
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    ...
    try:
        result = corpus_assemble(args.store, args.category, args.as_of, fresh,
                                 registry, horizons, salience_floor=args.salience_floor)
    except (CorpusError, AsOfError) as e:
        print(f"gpu-agent corpus: error: {e}", file=sys.stderr)
        return 1
    report = result.report
    for sp in report.skippedPages:
        print(f"SKIPPED-PAGE {sp.id}: category={sp.category}", file=sys.stderr)
    for sp in report.lifecycleExcluded:
        print(f"LIFECYCLE-EXCLUDED {sp.id}: pruned page", file=sys.stderr)
    for fc in report.freshDuplicate:
        print(f"DROPPED-DUPLICATE {fc.findingId}: {fc.detail or 'duplicate'}", file=sys.stderr)
    for fid in report.idOverlaps:
        print(f"ID-OVERLAP {fid}: store copy kept", file=sys.stderr)
    if report.fadedOut:
        print(f"faded-out: {report.fadedOut} store finding(s) below salience floor", file=sys.stderr)
```

And the assemble-mode summary print (~line 205):

```python
        print(f"store {len(report.storeIncluded)} aged ({report.fadedOut} faded), "
              f"fresh new {len(report.freshNew)} update {len(report.freshUpdate)} "
              f"duplicate {len(report.freshDuplicate)} -> merged {len(result.merged)}")
```

In the pipeline `--corpus-store` block (~line 787) load horizons before the call and swap it:

```python
    if args.corpus_store:
        horizons = IndicatorHorizons.load(REGISTRY_PATH)
        try:
            cres = corpus_assemble(args.corpus_store, a.category, args.as_of, findings,
                                   registry, horizons, salience_floor=args.corpus_salience_floor)
        except (CorpusError, AsOfError) as e:
            print(f"gpu-agent pipeline: corpus error: {e}", file=sys.stderr)
            return 1
        findings = cres.merged
        rep = cres.report
        if args.corpus_report:
            pathlib.Path(args.corpus_report).write_text(rep.model_dump_json(indent=2), "utf-8")
        print(f"corpus: store {len(rep.storeIncluded)} aged ({rep.fadedOut} faded), "
              f"fresh new {len(rep.freshNew)} update {len(rep.freshUpdate)} "
              f"duplicate {len(rep.freshDuplicate)} -> merged {len(findings)}",
              file=sys.stderr)
```

Argparse — `corpus` subparser (~line 1080), replace `--window-days`:

```python
    co.add_argument("--salience-floor", type=float, default=SALIENCE_FLOOR_DEFAULT,
                    help=f"aged-corpus decay cutoff (default {SALIENCE_FLOOR_DEFAULT})")
```

Argparse — `pipeline` subparser (~line 1150), replace `--corpus-window-days`:

```python
    pl.add_argument("--corpus-salience-floor", type=float, default=SALIENCE_FLOOR_DEFAULT,
                    help=f"aged-corpus decay cutoff (default {SALIENCE_FLOOR_DEFAULT})")
```

- [ ] **Step 4: Run them — verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_cli_corpus.py tests/test_cli_pipeline_corpus.py tests/test_cli_sufficiency.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cli.py tests/test_cli_corpus.py tests/test_cli_pipeline_corpus.py tests/test_cli_sufficiency.py
git commit -m "$(cat <<'EOF'
feat(F78-3): CLI threads horizons + salience floor into corpus; drops the window flags

corpus/pipeline load IndicatorHorizons, pass --salience-floor/--corpus-salience-floor,
catch AsOfError, and report aged/faded/lifecycle-excluded instead of in-window/out.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Full-suite reconciliation + eval pin green

The corpus change ripples only through code that assembled or asserted the windowed corpus. Reconcile any remaining failures **deterministically** (recompute the exact aged outcome — never weaken an assertion to a range).

**Files (candidates — confirm by running):** `tests/test_wiki_v12.py`, `tests/test_prompt_dates.py`, `tests/test_registry_indicators.py` (matched "corpus"/"window" in the grep — likely incidental), plus anything importing `corpus.period_end`/`in_window`/`WINDOW_DAYS_DEFAULT`.

- [ ] **Step 1: Confirm no stale references to removed corpus symbols**

Run (grep): `grep -rn "WINDOW_DAYS_DEFAULT\|corpus.period_end\|corpus.in_window\|in_window\|outOfWindow\|windowDays\|--window-days\|--corpus-window-days" gpu_agent tests`
Expected: ZERO hits (all replaced). Any hit is a leftover — fix it.

- [ ] **Step 2: Run the full suite**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green except possibly a couple of downstream corpus-summary/report assertions.

- [ ] **Step 3: Reconcile each failure deterministically**

For each failure, recompute the expected value under the aged rule and update the literal (e.g. a merged-count or `storeIncluded` list that shifts because an old-`observedAt` fixture finding now fades). Do NOT relax an assertion. If a fixture's *intent* was "an old finding is kept because its cycle stamp is recent," that intent is exactly what this stage retires — update the fixture to a fresh `observedAt` (to keep it) or assert it now fades (to drop it), matching the test's real purpose.

- [ ] **Step 4: Confirm the eval pin is green**

Run: `../../.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS. The eval pin does not exercise the corpus (no `corpus`/`corpus-store` reference in it), so it stays green trivially. If it goes red, a prompt path changed unexpectedly — stop, do NOT edit the pin (HANDOFF standing rule), investigate.

- [ ] **Step 5: Commit the reconciliation**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test(F78-3): reconcile downstream corpus assertions to the aged selection rule; suite green

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Shadow-check over the live 2026-07 flagships + dailies

Prove the behavior change on real data: diff the OLD flat-window surfacing against the NEW aged surfacing over the live store at the 2026-07 flagship vintage, and confirm the pile-up drops while live fundamentals stay. **Read-only** — no store or scorecard is written (spec §7).

Live facts this check exercises (from `store/findings/*.json`; the store has 68 findings, all with recent `asOf` = 2026-07 or a July daily, but `observedAt` spanning 2025-08-22 → 2026-07-08):
- **2025-08-22** (~343 days before 2026-07-31) — the NVIDIA product/spec page that rode into v4.
- **2026-01-15** (~197 days) — old AMD secondary content.
- **2026-05-05 / -20 / -27** (~49–64 days) — the quarterly earnings/fundamentals that legitimately stay.

- [ ] **Step 1: Run the shadow-check diagnostic** (from the worktree; it reads `../../store` — the shared live store — read-only). Reconfigure stdout to UTF-8 first per the Windows note.

```bash
../../.venv/Scripts/python - <<'PY'
import sys, datetime; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from gpu_agent.asof import days_between, period_end
from gpu_agent.corpus import SALIENCE_FLOOR_DEFAULT, aged_salience, enumerate_store
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore

ROOT = "../../store"; CAT = "chips.merchant-gpu"; AS_OF = "2026-07"   # the v1-v4 flagship vintage
hz = IndicatorHorizons.load("../../registry/indicators.json")
ws = WikiStore(f"{ROOT}/wiki", FindingStore(f"{ROOT}/findings"))

def old_in_window(label, as_of, wd=45):   # the retired flat-window rule, reconstructed
    end = period_end(as_of); return (end - datetime.timedelta(days=wd)) < period_end(label) <= end

rows, seen = [], set()
for e in ws.index():
    if e.category != CAT:
        continue
    page = ws.get_page(e.id)
    for o in ws.observations(e.id):
        if o.findingId in seen:
            continue
        seen.add(o.findingId)
        f = ws.findings.get(o.findingId)
        eff = aged_salience(f, page.salience, AS_OF, hz)
        rows.append((f.id, f.entity, f.indicatorId, f.observedAt,
                     max(0, days_between(AS_OF, f.observedAt)), eff,
                     old_in_window(f.asOf, AS_OF), eff >= SALIENCE_FLOOR_DEFAULT))

old_n = sum(r[6] for r in rows); new_n = sum(r[7] for r in rows)
inc, faded, skip, life = enumerate_store(ROOT, CAT, AS_OF, hz)
print(f"OLD in-window surfaced : {old_n}")
print(f"NEW aged surfaced      : {new_n}   (enumerate_store: {len(inc)} incl, {faded} faded, "
      f"{len(life)} pruned-pages)")
print(f"DROPPED by aging (old kept, new fades), oldest first:")
for r in sorted((r for r in rows if r[6] and not r[7]), key=lambda r: -r[4]):
    print(f"  DROP {r[0]:22} {r[1]:10} {r[2]:22} obs {r[3]} ({r[4]:>3}d) eff={r[5]:.3f}")
print(f"KEPT despite age >= 45d (should be quarterly fundamentals):")
for r in sorted((r for r in rows if r[7] and r[4] >= 45), key=lambda r: -r[4]):
    print(f"  KEEP {r[0]:22} {r[1]:10} {r[2]:22} obs {r[3]} ({r[4]:>3}d) eff={r[5]:.3f}")
PY
```

- [ ] **Step 2: Confirm the direction and record the numbers**

Expected (record the actual counts in the commit body / SDD ledger):
- `NEW aged surfaced < OLD in-window surfaced` — the aged rule surfaces strictly fewer (the window kept every recent-`asOf` fact; aging drops the stale-content ones).
- The **2025-08-22** (~343d) NVIDIA fact appears in **DROP** (it fades below 0.1 under every cadence: even quarterly `0.5·0.5^(343/120) ≈ 0.07 < 0.1`).
- The **2026-01-15** (~197d) AMD secondary fact appears in **DROP** under its (weekly/structural) cadence.
- At least one **2026-05-\*** (~49–64d) quarterly earnings/fundamentals fact appears in **KEEP** (`0.5·0.5^(~55/120) ≈ 0.36 ≥ 0.1`).
- No file under `store/` is modified (`cd ../.. && git status --short store/` shows nothing from this step).

If a named pile-up item does NOT drop (or a live fundamental DOES drop), that is a finding, not a pass — see the Open Questions note in Self-review about the `observedAt`-vs-page-`quiet_age` design choice, and surface it before merge rather than tuning the floor to force the result.

- [ ] **Step 3: Record the shadow-check result** (evidence, not a code change)

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f78-stage3-corpus
git log --oneline -1   # concurrent-instance guard before any commit
git commit --allow-empty -m "$(cat <<'EOF'
test(F78-3): shadow-check — aged corpus drops the 343d/197d stale-content pile-up; fundamentals stay

Read-only diff of old flat-window vs new aged surfacing over the live 2026-07 store.
<paste the OLD/NEW counts + the DROP/KEEP lines here>

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Spec coverage (§5.3 / D4):** flat `asOf` window removed (Task 1–2); facts surface on decayed `effective_salience` against a **salience floor** `0.1` = the wiki's `stale_threshold`, a decay-based cutoff not a cycle window (Task 1–2); pruned pages excluded via `_is_pruned` lifecycle gate (Task 2); `assemble()` still unions aged store ∪ fresh gated findings (Task 3); shadow-check over 2026-07 v1–v4 + dailies (Task 6). ✅
- **DRY consolidation:** `corpus.py` no longer defines `period_end`/`in_window`/`WINDOW_DAYS_DEFAULT`; it imports `days_between`/`AsOfError` from `gpu_agent.asof` and reuses `wiki.lint`'s `half_life`/`effective_salience` and `wiki.lifecycle`'s `prune_salience_floor`. ✅
- **Determinism:** aging is `days_between(as_of, observedAt)` (label-based) × `half_life` (registry-based) × `effective_salience` (pure) — no wall-clock; `merged` = sorted store part + fresh keeps → byte-stable. ✅
- **Frozen core / eval pin:** only `corpus.py`, `cli.py` (corpus wiring), and tests change; `gate.py`/`scoring.py`/`pipeline.py`/`schema/*`/`judgment/*` untouched; eval pin has no corpus dependency and stays green (Task 5 Step 4). ✅
- **Placeholders:** none — every step shows real code grounded in the read `corpus.py`/`wiki`; Task 5 forbids range-weakening.
- **Type consistency:** `enumerate_store(...) -> (list[Finding], int, list[SkippedPage], list[SkippedPage])`; `assemble(..., horizons, *, salience_floor, config)`; `aged_salience(finding, page_salience, as_of, horizons, config) -> float`; `_is_pruned(store, page_id, page, lifecycle_config) -> bool`. All call sites (Tasks 2–4, tests) match.
- **`CorpusError` → `AsOfError` migration:** the one corpus test that asserted `CorpusError` on **bad labels** (`tests/test_corpus_window.py::test_period_end_rejects_bad_labels`) is deleted; that coverage now lives in Stage 1's `tests/test_asof.py` (raising `AsOfError`). `CorpusError` is retained only for store-integrity (`test_dangling_observation_fails_loud`, unchanged). The CLI catches `(CorpusError, AsOfError)` so a bad `--as-of` still exits 1 cleanly.
- **Open question (surfaced to the parent, do not silently resolve):** the spec §5.3 phrases the aging as the page's `effective_salience` (page-level, keyed on the page's last-observation `asOf` via `quiet_age`). On the **live store every page was observed at 2026-07**, so page-level `quiet_age ≈ 0` for all pages and page-level decay would drop **nothing**. The real aging signal that captures the 343-day / 197-day pile-up is the **fact's own `observedAt`** (the "evidence's real publication date" named in §1's root cause #2). This plan therefore ages **per fact on `observedAt`** (using the wiki's decay curve in calendar days), which both honors the parent's phrasing ("what a **fact** survives on is its decayed effective_salience") and actually reproduces the spec's described drop. If the parent intends strict page-level `quiet_age` decay instead, the shadow-check (Task 6) will show it dropping nothing — flag before merge. Related, smaller choices to confirm: (a) intrinsic salience is floored at `LintConfig.salience_floor` (0.5) so unscored live pages (all salience 0.0) still age meaningfully — without this floor the aged corpus is empty on the current store; (b) "pruned" is detected as *scored-then-floored* (`salience ≤ prune_floor` **and** has state-change history) because `salience == 0.0` is overloaded (also the never-scored default); archived/retired are not wiki-page states in the current model, so no status enum change is made here.
