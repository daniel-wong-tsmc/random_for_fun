# F78 Stage 1 — Calendar-day wiki decay (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the wiki's fact-aging from *counting runs* to *calendar days derived from `asOf` labels*, so a fact fades by real elapsed time regardless of how often the agent runs.

**Architecture:** The wiki decay is `effective_salience = intrinsic × 0.5^(quiet_age / half_life)`. Today both `quiet_age` (in `wiki/lint.py`) and `half_life` are measured in *cycles*. This stage re-expresses both in **calendar days** computed from `asOf` period-ends (a new shared `gpu_agent/asof.py`), leaving the `decay`/`effective_salience` math and both call sites (`_score_move`, `health_report`) untouched — only the units change.

**Tech Stack:** Python 3.11, pydantic v2, pytest. Run Python as `.venv/Scripts/python` from repo root.

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` §5.2 (this is D5, the calendar-day decision). This is **F78 Stage 1** of 6.

## Global Constraints

- **Determinism, never wall-clock.** All day-math derives from `asOf` labels via period-ends (the project's label-based convention). No `datetime.now()`, `Date.now()`, `Math.random()`. Same inputs → byte-identical output.
- **Frozen core untouched:** do NOT edit `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`. This stage touches only `gpu_agent/asof.py` (new), `gpu_agent/wiki/lint.py`, and their tests.
- **Eval pin stays green:** no emitted brain-prompt bytes change here (`tests/test_evals_baseline_pin.py` must stay green). If it goes red, you touched a prompt file — stop and re-scope.
- **Provisional numbers (D5).** The half-life day-values (7 / 21 / 120) are deliberately provisional and will be recalibrated later; they are chosen to be sensible for a daily-run product, not to reproduce the old cycle-based values.
- **Suite green at every commit.** Baseline before starting: run `.venv/Scripts/python -m pytest -q` and record the pass count.
- **Windows:** use the Bash tool for `>` redirects / heredocs; no double quotes inside `git commit -m` under PowerShell (use a bash heredoc). Commit trailer names the ACTUAL implementer model.

---

### Task 1: Shared `asof` date helpers

**Files:**
- Create: `gpu_agent/asof.py`
- Create: `tests/test_asof.py`

**Interfaces:**
- Produces: `period_end(label: str) -> datetime.date` (day-grain label → its own day; month-grain → last day of month; else raises `AsOfError`); `days_between(later_label: str, earlier_label: str) -> int` (`(period_end(later) - period_end(earlier)).days`); `class AsOfError(ValueError)`.
- Note (DRY): `corpus.py` currently has its own `period_end`. It is **left untouched in this stage** to keep this behavior-sensitive change isolated; F78 Stage 3 (corpus rework) consolidates `corpus.py` onto `gpu_agent/asof.py`. This temporary duplication is intentional and scheduled.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_asof.py
import datetime
import pytest
from gpu_agent.asof import period_end, days_between, AsOfError


def test_period_end_day_grain():
    assert period_end("2026-07-08") == datetime.date(2026, 7, 8)


def test_period_end_month_grain_is_last_day():
    assert period_end("2026-07") == datetime.date(2026, 7, 31)
    assert period_end("2026-02") == datetime.date(2026, 2, 28)


def test_period_end_bad_shape_fails_loud():
    with pytest.raises(AsOfError):
        period_end("2026/07/08")


def test_days_between_month_labels():
    # Apr 30 -> Jun 30 = 61 days
    assert days_between("2026-06", "2026-04") == 61


def test_days_between_day_labels():
    assert days_between("2026-07-08", "2026-07-01") == 7


def test_days_between_same_label_is_zero():
    assert days_between("2026-07", "2026-07") == 0
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_asof.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.asof'`.

- [ ] **Step 3: Write the implementation**

```python
# gpu_agent/asof.py
"""Label-based date helpers shared across the aging subsystems (F78 Stage 1).

An `asOf` label is either day-grain (YYYY-MM-DD) or month-grain (YYYY-MM). Its
"period end" is the last calendar day it covers. All elapsed-time math derives from
these period-ends — never the wall clock — so replays are deterministic.
"""
from __future__ import annotations
import calendar
import datetime
import re

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class AsOfError(ValueError):
    """Raised when an asOf label is not YYYY-MM or YYYY-MM-DD (fail loud)."""


def period_end(label: str) -> datetime.date:
    """A label's period end: a day-grain label is its own day; a month-grain label is
    that month's last calendar day. Any other shape fails loud."""
    try:
        if _DAY_RE.match(label):
            return datetime.date.fromisoformat(label)
        if _MONTH_RE.match(label):
            y, m = int(label[:4]), int(label[5:7])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
    except ValueError as e:
        raise AsOfError(f"invalid asOf label: {label!r} ({e})") from e
    raise AsOfError(f"invalid asOf label: {label!r} (want YYYY-MM or YYYY-MM-DD)")


def days_between(later_label: str, earlier_label: str) -> int:
    """Calendar days from `earlier_label`'s period end to `later_label`'s period end.
    Negative if the labels are out of order (the caller decides whether to clamp)."""
    return (period_end(later_label) - period_end(earlier_label)).days
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_asof.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/asof.py tests/test_asof.py
git commit -m "$(cat <<'EOF'
feat(F78-1): shared asof date helpers (period_end, days_between) for calendar-day aging

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `half_life` returns calendar days

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (`LintConfig`, `_CADENCE_HL`, `half_life`)
- Modify: `tests/test_wiki_lint_decay.py` (the five `test_half_life_*` cases)

**Interfaces:**
- Consumes: nothing new.
- Produces: `LintConfig.h_short_days=7`, `h_med_days=21`, `h_long_days=120` (replacing `h_short/h_med/h_long`); `half_life(findings, horizons, config) -> (int_days, untagged_ids)` unchanged in signature, now returning **days**.

- [ ] **Step 1: Update the failing tests**

In `tests/test_wiki_lint_decay.py`, change the five half-life expectations to the day-values:

```python
def test_half_life_daily_short():
    hl, untagged = half_life([_f("f1", "A", "daily-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 7 and untagged == []


def test_half_life_quarterly_long():
    hl, _ = half_life([_f("f1", "A", "quarterly-coin")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 120


def test_half_life_leading_floor():
    # daily would be 7, but a leading-horizon signal is floored at H_med (21 days)
    hl, _ = half_life([_f("f1", "A", "daily-lead")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 21


def test_half_life_longest_class_wins():
    hl, _ = half_life([_f("f1", "A", "daily-coin"), _f("f2", "A", "quarterly-coin")],
                      _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 120


def test_half_life_untagged_default_and_logged():
    hl, untagged = half_life([_f("f1", "A", "ghost-ind")], _HZ, DEFAULT_LINT_CONFIG)
    assert hl == 21 and untagged == ["ghost-ind"]
```

- [ ] **Step 2: Run them — verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -k half_life -q`
Expected: FAIL (still returns 1/3/6 cycle values).

- [ ] **Step 3: Update `LintConfig` and `_CADENCE_HL` in `gpu_agent/wiki/lint.py`**

In `LintConfig` (currently lines ~83-85), replace the three cycle fields:

```python
    # F78 Stage 1: half-lives in CALENDAR DAYS (provisional — D5, recalibrate later).
    h_short_days: int = 7     # daily-cadence facts fade within ~a week if unrefreshed
    h_med_days: int = 21      # weekly cadence + the leading-horizon floor + untagged default
    h_long_days: int = 120    # quarterly facts persist ~a third of a year
```

Update the cadence map (currently line ~91):

```python
_CADENCE_HL = {"daily": "h_short_days", "weekly": "h_med_days", "quarterly": "h_long_days"}
```

- [ ] **Step 4: Update `half_life` to use the day fields**

Replace the two `config.h_med` references and the docstring in `half_life`:

```python
def half_life(findings, horizons, config=DEFAULT_LINT_CONFIG):
    """Longest-persistence half-life IN CALENDAR DAYS among the findings' cadence-horizon
    tags. cadence drives persistence (daily->short, weekly->med, quarterly->long); a
    leading-horizon finding is floored at H_med. Untagged indicator ids fall back to H_med
    and are RETURNED (the caller logs them). No findings -> H_med (neutral)."""
    untagged: list[str] = []
    classes: list[int] = []
    for f in findings:
        tag = horizons.get(f.indicatorId)
        if tag is None or tag.get("cadence") not in _CADENCE_HL:
            untagged.append(f.indicatorId)
            classes.append(config.h_med_days)
            continue
        hl = getattr(config, _CADENCE_HL[tag["cadence"]])
        if tag.get("horizon") == "leading":
            hl = max(hl, config.h_med_days)
        classes.append(hl)
    return (max(classes) if classes else config.h_med_days), untagged
```

- [ ] **Step 5: Confirm no other references to the old fields**

Run: `.venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -k half_life -q` → PASS.
Run (grep): search for stale field names — expect ZERO hits outside this diff:
`grep -rn "h_short\b\|h_med\b\|h_long\b\|\.h_short\|\.h_med\|\.h_long" gpu_agent tests` — if any hit is a `.h_short/.h_med/.h_long` attribute access, update it to the `_days` name.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/wiki/lint.py tests/test_wiki_lint_decay.py
git commit -m "$(cat <<'EOF'
feat(F78-1): wiki half_life returns calendar days (provisional 7/21/120), not cycles

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `quiet_age` returns calendar days

**Files:**
- Modify: `gpu_agent/wiki/lint.py` (`quiet_age`; drop the now-unused `_MATERIAL_CYCLE_KINDS` cycle-set)
- Modify: `tests/test_wiki_lint_decay.py` (the three `test_quiet_age_*` cases)

**Interfaces:**
- Consumes: `gpu_agent.asof.days_between` (Task 1).
- Produces: `quiet_age(store, page_id, as_of) -> int` — now **calendar days** (≥ 0) since the page's last material event's period-end.

- [ ] **Step 1: Update the failing tests**

In `tests/test_wiki_lint_decay.py`, replace the three quiet-age cases. Fresh and reset stay 0; the intervening case becomes a calendar-day gap (Apr 30 → Jun 30 = 61):

```python
def test_quiet_age_fresh_is_zero(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-06")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0


def test_quiet_age_is_calendar_days_since_last_material(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    # a is untouched through 2026-06; quiet age = period_end(2026-06) - period_end(2026-04)
    assert quiet_age(ws, "entity:a", "2026-06") == 61


def test_quiet_age_material_update_resets(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:a", "entity", "A", as_of="2026-04")
    ws.findings.append(_f("f1", "A"))
    ws.append_observation("entity:a", "f1", as_of="2026-04")
    # a gets a NEW observation at 2026-06 -> quietness resets to 0 days
    ws.findings.append(_f("f3", "A"))
    ws.append_observation("entity:a", "f3", as_of="2026-06")
    assert quiet_age(ws, "entity:a", "2026-06") == 0
```

- [ ] **Step 2: Run them — verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -k quiet_age -q`
Expected: FAIL (`test_quiet_age_is_calendar_days_since_last_material` gets a cycle count, not 61).

- [ ] **Step 3: Rewrite `quiet_age` in `gpu_agent/wiki/lint.py`**

Add the import near the top (after the existing imports):

```python
from gpu_agent.asof import days_between
```

Replace `quiet_age` (and delete the now-unused `_MATERIAL_CYCLE_KINDS` set above it):

```python
def quiet_age(store, page_id, as_of) -> int:
    """Calendar days between the page's last MATERIAL event (append-observation or
    state-change, up to as_of) and `as_of`, via label period-ends — deterministic, never
    wall-clock. A page with no material events decays from its createdAsOf. Returns days >= 0.

    F32 preserved: only material events set the baseline; read-only 'lint'/'header-change'
    events cannot age a page, because they neither move the baseline nor the as_of label."""
    materials = [e.asOf for e in store.log.read()
                 if e.pageId == page_id
                 and e.kind in ("append-observation", "state-change")
                 and e.asOf <= as_of]
    baseline = max(materials) if materials else store.get_page(page_id).createdAsOf
    return max(0, days_between(as_of, baseline))
```

- [ ] **Step 4: Run them — verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_wiki_lint_decay.py -q`
Expected: PASS (all decay tests, including the unchanged `test_decay_and_effective_salience`).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/wiki/lint.py tests/test_wiki_lint_decay.py
git commit -m "$(cat <<'EOF'
feat(F78-1): wiki quiet_age is calendar days since last material event, not cycle count

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Full-suite reconciliation + decay sanity check

Both call sites (`_score_move` line ~226, `health_report` line ~261) pass `quiet_age`/`half_life` straight into `effective_salience`, so no call-site code changes — but any test that asserted a specific `effectiveSalience` or stale-detection outcome under the old *cycle* decay will now see the *day* value. Reconcile those deterministically (the new numbers are exact, not judgment calls).

**Files (candidates to reconcile — confirm by running):**
- `tests/test_wiki_lint_health.py`, `tests/test_wiki_v12.py`, `tests/test_lifecycle_prune_quarantine.py`, `tests/dashboard/test_ranking.py` (all reference decay/stale per the grep).

- [ ] **Step 1: Run the full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: the decay/asof tests pass; some downstream tests may fail on changed `effectiveSalience`/stale numbers.

- [ ] **Step 2: Reconcile each failure deterministically**

For each failing assertion, recompute the expected value under calendar-day decay and update the literal. Do NOT weaken an assertion to a range to make it pass — compute the exact new number (e.g. print `effective_salience(intrinsic, quiet_age(...), half_life(...))` for that fixture and pin it). If a test's *intent* was "this page is stale after N cycles," restate it as "stale after N days" with the fixture's real day-gap.

- [ ] **Step 3: Confirm the eval pin is green**

Run: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS (this stage changed no emitted brain-prompt bytes).

- [ ] **Step 4: Decay sanity check (evidence, not just green tests)**

Run this one-off against the live wiki to confirm the aging now varies by calendar time (reconfigure stdout to UTF-8 first per the Windows note):

```bash
.venv/Scripts/python - <<'PY'
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import quiet_age, half_life, effective_salience, _findings_for
ws = WikiStore("store/wiki", FindingStore("store/findings"))
hz = IndicatorHorizons.load("registry/indicators.json")
as_of = "2026-07-08"
for e in ws.index():
    p = ws.get_page(e.id)
    fs, _ = _findings_for(ws, e.id, ws.observations(e.id))
    hl, _ = half_life(fs, hz)
    qa = quiet_age(ws, e.id, as_of)
    print(f"{e.id:<28} quiet={qa:>4}d  hl={hl:>3}d  eff_sal={effective_salience(p.salience, qa, hl):.3f}")
PY
```
Expected: quiet ages are in **days** (tens/hundreds), and a page not touched for months shows a visibly lower `eff_sal` than a freshly-observed one. This is the Stage-1 slice of the spec's shadow-check (the full corpus shadow-check lands in Stage 3).

- [ ] **Step 5: Commit the reconciliation**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test(F78-1): reconcile downstream wiki decay assertions to calendar-day units; suite green

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Spec coverage (§5.2):** `quiet_age` → days (Task 3), `half_life` → days (Task 2), decay/effective_salience math unchanged (verified in Task 3/4), determinism via `asof.period_end` (Task 1), no wall-clock. ✅ Thesis-pacing half of §5.2 is deliberately a **separate plan** (Stage 2) — same file/test isolation reason as the corpus DRY note.
- **Placeholders:** none — every code step shows the real code; Task 4's reconciliation lists exact candidate files and forbids range-weakening.
- **Type consistency:** `days_between(later, earlier) -> int` used by `quiet_age`; `half_life(...) -> (int, list)`; config fields `h_short_days/h_med_days/h_long_days` referenced identically in `_CADENCE_HL`, `half_life`, and the tests.
- **Frozen core / eval pin:** untouched / pinned green (Task 4 Step 3).
