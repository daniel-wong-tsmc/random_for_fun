# F78 Stage 2 — Calendar-day thesis pacing (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-express the thesis book's anti-whipsaw *pacing* — the `streak` of consecutive same-direction signals, the low/medium/high conviction swing, and rule-5 promotion persistence — from *counting cycles* to *calendar days derived from `asOf` labels*, so that running the brief daily cannot advance pacing ~30× faster than the old ~monthly flagship cadence. A same-direction signal advances the streak / steps conviction / counts toward promotion **only when it is separated from the prior counted signal by at least a minimum day-gap** (a provisional, tunable dial); a genuine conviction change or direction reversal remains immediate (it is already evidence-gated by rule 6).

**Architecture:** The pacing lives entirely in `gpu_agent/thesis.py`:
- `_apply_judgment_record` (the pure replay/apply transition, shared by `ThesisStore.rebuild()` and `apply_answer`) code-derives `streak`. Today: `streak = 1 if (conviction_changed or reversal) else entry.streak + 1`.
- `_build_judgment_records` (rule 6) decides applied/deferred and the post-apply `conviction` via `_bump_conviction(±1)`.
- `_promotion_eligible` (rule 5) requires judgments across `>= 2 distinct asOf` values **and** `>= 2` publisher domains.

This stage introduces two provisional day dials and one shared predicate, adds a **new code-derived entry field `lastPaceAsOf`** (the asOf of the last signal that *counted* toward pacing — a natural sibling of the already-code-derived `streak`, per the pattern `test_streak_is_code_derived_*` documents), and rewires the three functions above to measure in days. It re-uses `gpu_agent.asof.days_between` / `period_end` from **Stage 1** (assume Stage 1 landed first). Emitted prompt bytes, `gate_answer`, the prompt templates, and `_book_entry_lines` are **untouched**.

**Tech Stack:** Python 3.11, pydantic v2, pytest. Run Python as `.venv/Scripts/python` from repo root (from a worktree, `../../.venv/Scripts/python`; one shared root venv — never create a per-worktree venv).

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` §5.2 (the thesis-pacing paragraph of D5), decision **D5** in §4, testing §7, risks §8. This is **F78 Stage 2** of 6; Stage 1 (`gpu_agent/asof.py`, calendar-day wiki decay) lands first.

## Global Constraints

- **Determinism, never wall-clock.** All day-math derives from `asOf` labels via `asof.period_end` / `asof.days_between` (the project's label-based convention). No `datetime.now()`, `Date.now()`, `Math.random()`. Same inputs → byte-identical output.
- **Frozen core untouched:** do NOT modify `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`. `thesis.py` is NOT frozen core but is behavior-sensitive and heavily test-pinned (scenarios a–k) — update the pinned thesis tests to the new calendar-day semantics **deterministically**, and NEVER weaken an assertion to a range to make it pass. (Note: `gpu_agent/wiki/lifecycle.py`'s `persistence`/`corroboration`/`promotion_candidates` — pinned by `tests/test_lifecycle_promotion.py` — is a **separate** wiki-page subsystem, NOT thesis pacing; it is out of scope and must not be touched here.)
- **Eval pin stays green:** no emitted brain-prompt bytes change here (this is code, not prompt text); `tests/test_evals_baseline_pin.py` must stay green. The thesis seam hashes `fixtures/evals/hash-input.json` (a static fixture book) through `_book_entry_lines`, which is untouched and never emits `lastPaceAsOf`. If the pin goes red, you touched a prompt path — stop and re-scope.
- **Provisional numbers (D5).** The two day dials — `MIN_PACE_GAP_DAYS = 21` and `MIN_PROMOTION_SPAN_DAYS = 21` — are deliberately provisional and will be recalibrated later. They are chosen to approximate today's behavior under the old ~monthly cadence (see "Provisional values", below), not to be final.
- **Execution happens in a git worktree** per repo discipline (`.worktrees/<name>` on a claimed branch, never the root checkout's main). The plan is executed later.
- **Suite green at every commit.** Baseline before starting: run `.venv/Scripts/python -m pytest -q` and record the pass count (expect 3–4 skips).
- **Windows:** use the Bash tool for `>` redirects / heredocs; no double quotes inside `git commit -m` under PowerShell (use a bash heredoc). Commit trailer names the ACTUAL implementer model: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## Provisional values (state them explicitly — D5)

| Dial | Value | Governs | Why this value |
|---|---|---|---|
| `MIN_PACE_GAP_DAYS` | **21 days** | streak advance + conviction step | The retired flagship advanced once per ~monthly cycle (28–31 days). 21 days sits **below the shortest month (Feb, 28d)**, so a monthly cadence still counts *every* cycle — reproducing today's "one step per cycle" — while sitting **well above** the daily/weekly cadence, so daily re-runs no longer inflate pacing. Matches Stage 1's `h_med_days = 21`. |
| `MIN_PROMOTION_SPAN_DAYS` | **21 days** | rule-5 persistence | The old rule promoted at `>= 2 distinct asOf` cycles; under monthly cadence the 2nd cycle already spans ~30 days, so requiring a **≥21-day calendar span** between the earliest and latest judgment reproduces "promotes on the 2nd monthly cycle" while blocking "promotes on two consecutive days" under daily cadence. Kept as a **separate** constant from `MIN_PACE_GAP_DAYS` so the two can be recalibrated independently. |

Exact values are deferred (D5 "calendar day for now, recalibrate later"). The `>= 2` distinct-**publisher-domains** half of rule 5 is a corroboration bar, not a time bar, and is **unchanged**.

---

### Task 1: Provisional day dials, `_pace_counts` predicate, and the `lastPaceAsOf` field

**Files:**
- Modify: `gpu_agent/thesis.py` (imports; new dials + `_pace_counts`; `ThesisEntry.lastPaceAsOf`)
- Create: `tests/test_thesis_pacing.py`

**Interfaces:**
- Consumes: `gpu_agent.asof.days_between`, `gpu_agent.asof.period_end` (Stage 1).
- Produces: module constants `MIN_PACE_GAP_DAYS = 21`, `MIN_PROMOTION_SPAN_DAYS = 21`; `_pace_counts(last_pace_asof: str, as_of: str) -> bool`; `ThesisEntry.lastPaceAsOf: str = ""` (code-derived, defaults empty so a freshly seeded/proposed thesis's first judgment behaves exactly as before this change).

- [ ] **Step 1: Write the failing test**

Create `tests/test_thesis_pacing.py` with the shared helpers plus the predicate tests (the streak/conviction/promotion behavior tests are added in Tasks 2–4, in this same file):

```python
# tests/test_thesis_pacing.py
"""F78 Stage 2: calendar-day thesis pacing. streak advance, conviction swing, and rule-5
promotion are measured in CALENDAR DAYS derived from asOf labels, not per cycle."""
import pytest

from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact, Kind
from gpu_agent.thesis import (
    MIN_PACE_GAP_DAYS,
    MIN_PROMOTION_SPAN_DAYS,
    ThesisAnswer,
    ThesisBook,
    ThesisEntry,
    ThesisJudgment,
    _pace_counts,
    apply_answer,
)

CATEGORY_ID = "chips.merchant-gpu"


def _evidence(tier, url="https://example.com/a"):
    return Evidence(source="Example", url=url, date="2026-07-01", excerpt="e", tier=tier)


def _finding(fid, *, evidence, indicator="D2"):
    return Finding(
        id=fid, statement="x", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"),
        asOf="2026-07", indicatorId=indicator, side="demand",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="nvidia",
        observedAt="2026-07-01", capturedAt="2026-07-01", evidence=evidence,
    )


def _fd(fid, domain):
    return _finding(fid, evidence=[_evidence("secondary", url=f"https://{domain}/p")])


def _entry(entry_id, **kw):
    base = dict(
        title="T", statement="s", lens="demand", status="registered",
        conviction="medium", lastDirection=0, streak=0,
        mechanism="m", falsifiableTrigger="Reassessed next quarter.",
        sensitivity="s", createdAsOf="2026-05-01", lastChangedAsOf="2026-05-01",
    )
    base.update(kw)
    return ThesisEntry(id=entry_id, **base)


def _book(*entries):
    return ThesisBook(categoryId=CATEGORY_ID, entries=list(entries))


def _judgment(thesis_id, *, verdict="reaffirmed", finding_ids=("f-1",), rationale="r"):
    return ThesisJudgment(
        thesisId=thesis_id, verdict=verdict, rationale=rationale,
        findingIds=list(finding_ids), mechanism="m",
        falsifiableTrigger="Reassessed next quarter.", sensitivity="s",
    )


def _answer(*judgments):
    return ThesisAnswer(judgments=list(judgments), proposed=[])


SEC = {"f-1": _finding("f-1", evidence=[_evidence("secondary")])}


def test_dials_are_the_provisional_defaults():
    assert MIN_PACE_GAP_DAYS == 21
    assert MIN_PROMOTION_SPAN_DAYS == 21


def test_pace_counts_first_signal_always_counts():
    # no prior counted signal (freshly seeded/proposed: lastPaceAsOf == "") -> counts,
    # so a thesis's FIRST judgment behaves exactly as before this change.
    assert _pace_counts("", "2026-07-03") is True


def test_pace_counts_below_gap_does_not_count():
    assert _pace_counts("2026-07-01", "2026-07-21") is False    # 20 days < 21


def test_pace_counts_at_gap_boundary_counts():
    assert _pace_counts("2026-07-01", "2026-07-22") is True     # exactly 21 days


def test_pace_counts_handles_mixed_grain_labels():
    # month-grain vs day-grain, resolved by period_end, never lexicographically.
    assert _pace_counts("2026-06", "2026-07-31") is True        # Jun30 -> Jul31 = 31 days
    assert _pace_counts("2026-07", "2026-07-15") is False       # Jul31 -> Jul15 = -16 days
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py -q`
Expected: FAIL with `ImportError: cannot import name 'MIN_PACE_GAP_DAYS'` (and `_pace_counts`).

- [ ] **Step 3: Add the import, the dials, and the predicate in `gpu_agent/thesis.py`**

Add the asof import directly after `from gpu_agent import reader` (currently line 8):

```python
from gpu_agent.asof import days_between, period_end
```

Add the dials and predicate immediately after the `CONVICTION_RANK = {...}` line (currently line 16):

```python
# --- F78 Stage 2: calendar-day thesis pacing (D5; provisional — recalibrate later) ---
# The retired monthly flagship advanced pacing once per ~30-day cycle; running the brief
# daily would advance ~30x faster. We re-express "one cycle" as a minimum calendar-day gap
# (from asOf period-ends, never the wall clock), so a same-direction signal only counts
# toward the streak / a conviction step / promotion when it is at least this many days after
# the prior counted signal. 21 days sits below the shortest month (Feb, 28d) so a monthly
# cadence still counts every cycle — reproducing today's behavior — and well above the
# daily/weekly cadence so runs no longer inflate pacing.
MIN_PACE_GAP_DAYS = 21        # streak advance + conviction-step gate
MIN_PROMOTION_SPAN_DAYS = 21  # rule-5 persistence: judged asOfs must span >= this many days


def _pace_counts(last_pace_asof: str, as_of: str) -> bool:
    """True iff a signal at `as_of` COUNTS toward pacing: it is at least MIN_PACE_GAP_DAYS
    (calendar days, via period-ends) after the prior counted signal `last_pace_asof`. An
    entry with no prior counted signal (freshly seeded/proposed: last_pace_asof == "")
    always counts, so a thesis's first judgment is unchanged. A negative gap (out-of-order
    mixed-grain labels) does not count — the streak safely holds rather than crashing."""
    if not last_pace_asof:
        return True
    return days_between(as_of, last_pace_asof) >= MIN_PACE_GAP_DAYS
```

Add the `lastPaceAsOf` field to `ThesisEntry`, directly after `streak: int = 0` (currently line 41):

```python
    streak: int = 0
    lastPaceAsOf: str = ""  # F78 S2: asOf of the last signal that COUNTED toward pacing;
                            # code-derived (like streak), defaults empty (first signal counts)
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Confirm nothing else broke (the new defaulted field is backward-compatible)**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_store.py tests/test_thesis_apply.py tests/test_thesis_models.py tests/test_thesis_prompt.py -q`
Expected: PASS. `lastPaceAsOf` defaults to `""` everywhere (seed, proposed, rebuild-of-old-history), and no logic reads it yet, so round-trips still match. If `tests/test_thesis_models.py` pins ThesisEntry's exact field set, add `lastPaceAsOf` to that expected set (deterministic — a defaulted `str = ""`).

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/thesis.py tests/test_thesis_pacing.py
git commit -m "$(cat <<'EOF'
feat(F78-2): provisional day dials, _pace_counts predicate, lastPaceAsOf field for thesis pacing

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Streak advances in calendar days

**Files:**
- Modify: `gpu_agent/thesis.py` (`apply_record` docstring; `_apply_judgment_record` applied branch)
- Modify: `tests/test_thesis_pacing.py` (add streak tests)
- Modify: `tests/test_thesis_store.py` (`_apply_judgment_to_book` helper; replace `test_streak_is_code_derived_from_record_and_prior_state`)

**Interfaces:**
- Consumes: `_pace_counts`, `entry.lastPaceAsOf` (Task 1).
- Produces: `_apply_judgment_record` sets `streak` and `lastPaceAsOf` deterministically — reset to 1 on a conviction change or a non-zero direction reversal (re-anchoring the pace clock); on a same-direction confirmation it advances **only when the signal counts** (`_pace_counts` True), else the streak **holds** and the pace clock keeps running from the prior counted signal.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_thesis_pacing.py`:

```python
# --- streak pacing (via apply_answer's applied path) -----------------------------------

def test_streak_holds_when_confirmation_is_too_soon():
    # a same-direction reaffirm only 7 days after the last counted signal must NOT advance.
    entry = _entry("t", conviction="medium", lastDirection=0, streak=4,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="reaffirmed")),
        as_of="2026-07-08", findings_by_id=SEC, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True
    assert e.streak == 4                      # held, not 5
    assert e.lastPaceAsOf == "2026-07-01"     # clock still runs from the prior counted signal


def test_streak_advances_when_confirmation_clears_the_gap():
    entry = _entry("t", conviction="medium", lastDirection=0, streak=4,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="reaffirmed")),
        as_of="2026-08-01", findings_by_id=SEC, history=[],   # 31 days after 2026-07-01
    )
    e = new_book.get("t")
    assert e.streak == 5
    assert e.lastPaceAsOf == "2026-08-01"     # re-anchored
```

- [ ] **Step 2: Update the pinned store test to calendar-day semantics**

In `tests/test_thesis_store.py`, add `lastPaceAsOf` to the `_apply_judgment_to_book` helper's `update` dict (so the manually-built expected book matches what `rebuild()` now computes — a counted single judgment after seed sets it to `as_of`):

```python
            update = {
                "lastVerdict": kwargs["verdict"],
                "conviction": kwargs["conviction"],
                "mechanism": kwargs["mechanism"],
                "falsifiableTrigger": kwargs["trigger"],
                "sensitivity": kwargs["sensitivity"],
                "streak": kwargs["streak"],
                "lastPaceAsOf": kwargs["as_of"],   # F78 S2: applied signal counts -> anchors here
                "lastChangedAsOf": kwargs["as_of"],
                "lastJudgedAsOf": kwargs["as_of"],
                "pendingChallenge": None,
            }
```

Then REPLACE the body of `test_streak_is_code_derived_from_record_and_prior_state` (currently lines ~322-356) with the calendar-day version below (rename included). The old version stepped cycles 7 days apart, which no longer advances the streak; the intent — "streak is code-derived: reset on conviction change / reversal, else prior+1" — is preserved and extended with the day-gap:

```python
def test_streak_is_code_derived_in_calendar_days(tmp_path):
    """streak is NOT in the record contract; apply_record derives it: reset to 1 on a
    conviction change or a non-zero direction reversal (re-anchoring lastPaceAsOf); on a
    same-direction confirmation it advances ONLY when the signal is >= MIN_PACE_GAP_DAYS
    (21) after the prior counted signal, else it holds."""
    thesis_id = "nvda-demand-durability"
    book1 = seed_book(SEED_PATH, CATEGORY_ID, AS_OF_1)   # AS_OF_1 = 2026-07-03
    store = ThesisStore(tmp_path / "theses" / CATEGORY_ID)
    store.root.mkdir(parents=True, exist_ok=True)

    def append(record):
        with store.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    append(_seeded_record(book1, AS_OF_1))

    # first reaffirm: seeded entry has no prior counted signal -> counts -> streak 1
    append(_judgment_record(thesis_id, as_of="2026-08-01", verdict="reaffirmed", conviction="medium"))
    assert store.rebuild().get(thesis_id).streak == 1

    # only 7 days later: too soon -> streak HOLDS at 1
    append(_judgment_record(thesis_id, as_of="2026-08-08", verdict="reaffirmed", conviction="medium"))
    assert store.rebuild().get(thesis_id).streak == 1

    # 31 days after the last counted signal (2026-08-01) -> advances to 2
    append(_judgment_record(thesis_id, as_of="2026-09-01", verdict="reaffirmed", conviction="medium"))
    assert store.rebuild().get(thesis_id).streak == 2

    # strengthened WITH conviction change -> reset to 1, lastDirection +1 (re-anchors clock)
    append(_judgment_record(thesis_id, as_of="2026-09-25", verdict="strengthened", conviction="high"))
    entry = store.rebuild().get(thesis_id)
    assert entry.streak == 1
    assert entry.lastDirection == 1

    # same direction, conviction unchanged, 25-day gap -> advances to 2
    append(_judgment_record(thesis_id, as_of="2026-10-20", verdict="strengthened", conviction="high"))
    assert store.rebuild().get(thesis_id).streak == 2

    # pure direction reversal (conviction unchanged) -> reset to 1, lastDirection -1
    append(_judgment_record(thesis_id, as_of="2026-11-15", verdict="weakened", conviction="high"))
    entry = store.rebuild().get(thesis_id)
    assert entry.streak == 1
    assert entry.lastDirection == -1
```

- [ ] **Step 3: Run them — verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py -k streak tests/test_thesis_store.py -k "calendar_days or rebuild_from_history or history_is_append_only" -q`
Expected: FAIL — the new streak tests fail (streak still per-cycle: `test_streak_holds_when_confirmation_is_too_soon` gets 5, not 4; `test_streak_is_code_derived_in_calendar_days` gets 2 at the 7-day step) and the round-trip tests fail on the missing `lastPaceAsOf` in the rebuilt book.

- [ ] **Step 4: Update `apply_record`'s docstring and `_apply_judgment_record`'s applied branch**

In `apply_record`'s docstring (currently the `- streak (applied records only): ...` bullet at lines ~140-143), replace that bullet with:

```python
      - `streak` and `lastPaceAsOf` (applied records only): reset streak to 1 when the
        record's after-conviction differs from the entry's prior conviction, or when the
        verdict's direction is a non-zero reversal of a non-zero prior lastDirection — a
        genuine change re-anchors lastPaceAsOf to this record's asOf. Otherwise a
        same-direction confirmation advances the streak (entry.streak + 1) and re-anchors
        lastPaceAsOf ONLY when it is >= MIN_PACE_GAP_DAYS after the prior counted signal
        (entry.lastPaceAsOf); a closer-spaced re-run holds both (F78 Stage 2 calendar-day
        pacing). Non-applied records leave streak and lastPaceAsOf unchanged.
```

In `_apply_judgment_record`, replace the streak computation and the `updates.update({...})` in the applied branch (currently lines ~210-226) with:

```python
            direction = DIRECTION[verdict]
            conviction_changed = record["conviction"] != entry.conviction
            reversal = direction != 0 and entry.lastDirection != 0 and direction != entry.lastDirection
            # F78 Stage 2: streak is paced in CALENDAR DAYS. A conviction change or a
            # direction reversal is a genuine event -> reset to 1 and re-anchor the pace
            # clock. A same-direction confirmation advances only when it clears the day-gap
            # from the prior counted signal; otherwise it holds and the clock keeps running.
            if conviction_changed or reversal:
                streak = 1
                last_pace = record["asOf"]
            elif _pace_counts(entry.lastPaceAsOf, record["asOf"]):
                streak = entry.streak + 1
                last_pace = record["asOf"]
            else:
                streak = entry.streak
                last_pace = entry.lastPaceAsOf
            updates.update({
                "statement": statement,
                "lastVerdict": verdict,
                "conviction": record["conviction"],
                "mechanism": record["mechanism"],
                "falsifiableTrigger": record["falsifiableTrigger"],
                "sensitivity": record["sensitivity"],
                "streak": streak,
                "lastPaceAsOf": last_pace,
                "lastChangedAsOf": record["asOf"],
                "pendingChallenge": None,
            })
            if direction != 0:
                updates["lastDirection"] = direction
```

(`lastChangedAsOf` is deliberately still bumped on every applied judgment — `brief.py`'s "Nothing changed this cycle" headline depends on that invariant. `lastPaceAsOf` is the new, separate pace clock.)

- [ ] **Step 5: Run them — verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py tests/test_thesis_store.py tests/test_thesis_apply.py -q`
Expected: PASS. Note `tests/test_thesis_apply.py::test_a` still passes unchanged — its entry has `lastPaceAsOf == ""` (helper default), so the first signal counts and streak goes 2→3 exactly as before.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/thesis.py tests/test_thesis_pacing.py tests/test_thesis_store.py
git commit -m "$(cat <<'EOF'
feat(F78-2): thesis streak advances in calendar days (>= MIN_PACE_GAP_DAYS), not per cycle

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Conviction step rate-limited to the calendar pace

**Files:**
- Modify: `gpu_agent/thesis.py` (`_build_judgment_records` applied-conviction block)
- Modify: `tests/test_thesis_pacing.py` (add conviction tests)

**Interfaces:**
- Consumes: `_pace_counts`, `entry.lastPaceAsOf`, the existing `is_reversal` local (currently line ~542).
- Produces: a same-direction `strengthened`/`weakened` steps conviction ±1 **only when the signal clears the day-gap** (`_pace_counts` True); a reversal or a `broken` verdict steps immediately (a genuine, evidence-gated event). The `_bump_conviction` clamp and rule-6 applied/deferred decision are unchanged. This keeps the record's post-apply conviction consistent with Task 2's streak reset **by construction**: a step that counts flips `conviction_changed`, which resets the streak; a step that is rate-limited leaves conviction equal, so the streak holds — both keyed on the same `_pace_counts` predicate.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_thesis_pacing.py`:

```python
# --- conviction pacing -----------------------------------------------------------------

def test_conviction_holds_when_strengthened_too_soon():
    # strengthened again only 7 days after the last counted signal must NOT walk medium->high.
    entry = _entry("t", conviction="medium", lastDirection=1, streak=1,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="strengthened")),
        as_of="2026-07-08", findings_by_id=SEC, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True       # a same-direction strengthen still applies
    assert records[0]["conviction"] == "medium"
    assert e.conviction == "medium"            # but the level is rate-limited: held
    assert e.streak == 1                        # no conviction change, too soon -> held


def test_conviction_steps_when_strengthened_clears_the_gap():
    entry = _entry("t", conviction="medium", lastDirection=1, streak=1,
                   lastPaceAsOf="2026-07-01", lastChangedAsOf="2026-07-01")
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="strengthened")),
        as_of="2026-08-01", findings_by_id=SEC, history=[],   # 31-day gap clears the pace
    )
    e = new_book.get("t")
    assert e.conviction == "high"
    assert e.streak == 1                        # conviction change re-anchors the streak


def test_reversal_steps_conviction_immediately_despite_recent_signal():
    # a reversal is a genuine event: even 1 day after the last counted signal, a primary
    # weakened reversal steps conviction and is NOT rate-limited.
    entry = _entry("t", conviction="high", lastDirection=1, streak=3,
                   lastPaceAsOf="2026-07-07", lastChangedAsOf="2026-07-07")
    findings = {"f-1": _finding("f-1", evidence=[_evidence("primary")])}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", verdict="weakened")),
        as_of="2026-07-08", findings_by_id=findings, history=[],
    )
    e = new_book.get("t")
    assert records[0]["applied"] is True
    assert e.conviction == "medium"            # high -> medium, one step, despite 1-day gap
    assert e.lastDirection == -1
```

- [ ] **Step 2: Run them — verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py -k conviction_holds -q`
Expected: FAIL — `test_conviction_holds_when_strengthened_too_soon` gets `high` (conviction still steps every applied cycle).

- [ ] **Step 3: Rate-limit the conviction step in `_build_judgment_records`**

Replace the applied-branch conviction block (currently lines ~556-570) with the paced version. `is_reversal` is already computed just above (line ~542); reuse it so a reversal steps immediately:

```python
    # F78 Stage 2: a same-direction conviction step is rate-limited to the calendar pace
    # (MIN_PACE_GAP_DAYS) so daily re-runs cannot walk low->high (or high->low) in a few
    # days. A reversal or a break is a genuine, evidence-gated event -> steps immediately.
    # Same _pace_counts predicate _apply_judgment_record uses for the streak, so the record's
    # post-apply conviction and the streak reset stay consistent by construction.
    steps_now = _pace_counts(entry.lastPaceAsOf, as_of) or is_reversal

    if applied:
        if verdict == "broken":
            new_conviction = "low"
        elif verdict == "strengthened":
            new_conviction = _bump_conviction(entry.conviction, +1) if steps_now else entry.conviction
        elif verdict == "weakened":
            new_conviction = _bump_conviction(entry.conviction, -1) if steps_now else entry.conviction
        else:  # reaffirmed / adjusted: unchanged
            new_conviction = entry.conviction
        if corroborated_step:
            note = (f"{entry.id}: applied: corroborated secondary reversal "
                    f"({len(domains)} distinct publishers; pending filing checkpoint)")
            extra_note = note          # checkpoint steps are never silent
        else:
            note = f"{entry.id}: {verdict} applied, conviction {entry.conviction}->{new_conviction}"
            extra_note = None
    else:
```

(Only the `if applied:` conviction assignments change; the `broken`/`corroborated_step`/`note` lines below are shown for placement and are unchanged.)

- [ ] **Step 4: Run them — verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py tests/test_thesis_apply.py tests/test_thesis_corroboration.py -q`
Expected: PASS. The single-cycle a–k and corroboration tests are unaffected — their entries have `lastPaceAsOf == ""` (so `steps_now` is True via `_pace_counts`) or exercise reversals (so `steps_now` is True via `is_reversal`): `test_b` medium→high, `test_d`/`test_e` medium→low, `test_k` high clamp, and the corroborated/primary reversals all step exactly as before.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/thesis.py tests/test_thesis_pacing.py
git commit -m "$(cat <<'EOF'
feat(F78-2): rate-limit thesis conviction steps to the calendar pace; reversals step immediately

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Rule-5 promotion persistence in calendar days

**Files:**
- Modify: `gpu_agent/thesis.py` (`_promotion_eligible`; the promotion note in `apply_answer`)
- Modify: `tests/test_thesis_pacing.py` (add promotion tests)
- Modify: `tests/test_thesis_apply.py` (`test_j1_promotion_across_two_asofs_two_domains`, `test_j2_single_domain_stays_provisional`)

**Interfaces:**
- Consumes: `asof.period_end` (for a grain-safe span; string min/max would misorder `"2026-07"` vs `"2026-07-03"`).
- Produces: `_promotion_eligible(thesis_id, records) -> tuple[bool, int, int]` returning `(eligible, span_days, n_domains)`; eligible iff the thesis's judged asOfs span `>= MIN_PROMOTION_SPAN_DAYS` calendar days **and** `n_domains >= 2`. The distinct-publisher-domains bar is unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_thesis_pacing.py`:

```python
# --- rule-5 promotion pacing -----------------------------------------------------------

def _history_reaffirm(thesis_id, as_of, domain):
    return {
        "asOf": as_of, "thesisId": thesis_id, "verdict": "reaffirmed", "applied": True,
        "conviction": "low", "rationale": "r", "findingIds": ["f-0"], "mechanism": "m",
        "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": [domain],
    }


def test_promotion_needs_calendar_span_not_two_cycles():
    # two judgments only 7 days apart, 2 distinct domains: NOT promotable (span 7 < 21).
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-07-01", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-b.com")}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "provisional"
    assert not any(r.get("event") == "promoted" for r in records)


def test_promotion_when_span_and_domains_met():
    # 33-day span (period_end 2026-06-05 -> 2026-07-08) and 2 distinct domains -> promotes.
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-06-05", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-b.com")}
    new_book, records, notes = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "registered"
    promoted = [r for r in records if r.get("event") == "promoted"]
    assert len(promoted) == 1
    assert "days judged" in promoted[0]["note"]
    assert any("promoted" in n for n in notes)


def test_promotion_blocked_by_single_domain_even_when_span_met():
    # 33-day span but only ONE distinct domain -> the domain bar (unchanged) still blocks.
    entry = _entry("t", status="provisional", conviction="low")
    history = [_history_reaffirm("t", "2026-06-05", "domain-a.com")]
    findings = {"f-1": _fd("f-1", "domain-a.com")}
    new_book, records, _ = apply_answer(
        _book(entry), _answer(_judgment("t", finding_ids=("f-1",))),
        as_of="2026-07-08", findings_by_id=findings, history=history,
    )
    assert new_book.get("t").status == "provisional"
    assert not any(r.get("event") == "promoted" for r in records)
```

- [ ] **Step 2: Update the pinned `j` tests in `tests/test_thesis_apply.py`**

Both use `AS_OF_PRIOR = "2026-06-26"` (only 7 days before `AS_OF = "2026-07-03"`), which no longer clears the 21-day span. Give each a `>= 21`-day span by using a dedicated earlier history asOf, so `test_j1` still promotes and `test_j2` is blocked **solely** by its single domain (not accidentally by the span). Change ONLY the history record's `asOf` in each:

In `test_j1_promotion_across_two_asofs_two_domains`, set the history record's `"asOf"` to `"2026-06-05"` (span = period_end 2026-06-05 → 2026-07-03 = 28 days ≥ 21; 2 domains → promotes):

```python
    history = [{
        "asOf": "2026-06-05", "thesisId": "thesis-j", "verdict": "reaffirmed",
        "applied": True, "conviction": "low", "rationale": "r", "findingIds": ["f-0"],
        "mechanism": "m", "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": ["domain-a.com"],
    }]
```

In `test_j2_single_domain_stays_provisional`, likewise set `"asOf"` to `"2026-06-05"` (span now clears 21, so the assertion that it stays provisional now isolates the single-domain cause):

```python
    history = [{
        "asOf": "2026-06-05", "thesisId": "thesis-j2", "verdict": "reaffirmed",
        "applied": True, "conviction": "low", "rationale": "r", "findingIds": ["f-0"],
        "mechanism": "m", "falsifiableTrigger": "t", "sensitivity": "s", "note": "n",
        "publisherDomains": ["domain-a.com"],
    }]
```

- [ ] **Step 3: Run them — verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py -k promotion tests/test_thesis_apply.py -k "j1 or j2" -q`
Expected: FAIL — `test_promotion_needs_calendar_span_not_two_cycles` still promotes (old `>= 2 distinct asOf` rule), and `test_j1`/`test_j2` fail because the note text / eligibility no longer match under the old rule vs the new span rule.

- [ ] **Step 4: Rewrite `_promotion_eligible` and the promotion note**

Replace `_promotion_eligible` (currently lines ~596-608) with the calendar-span version:

```python
def _promotion_eligible(thesis_id: str, records: list[dict]) -> tuple[bool, int, int]:
    """Rule 5, calendar-day form (F78 Stage 2): eligible when this thesis's judgments span
    at least MIN_PROMOTION_SPAN_DAYS calendar days (latest judged asOf's period-end minus
    the earliest's) AND their record-carried publisherDomains collectively span >= 2 distinct
    publishers. Replaces the old '>= 2 distinct asOf cycles' persistence bar so a daily
    cadence cannot promote in two consecutive days; under the old ~monthly cadence the second
    cycle already spans ~30 days, so this reproduces today's 'promotes on the 2nd cycle'
    behavior. Only records with a 'verdict' key count (lifecycle records skipped); applied and
    deferred judgments both count. Returns (eligible, span_days, n_domains) for the note.
    Span uses period_end, never string min/max, so mixed-grain labels ('2026-07' vs
    '2026-07-03') order correctly."""
    as_ofs: set[str] = set()
    domains: set[str] = set()
    for record in records:
        if record.get("thesisId") == thesis_id and "verdict" in record:
            as_ofs.add(record["asOf"])
            domains.update(record.get("publisherDomains", []))
    if as_ofs:
        ends = [period_end(a) for a in as_ofs]
        span_days = (max(ends) - min(ends)).days
    else:
        span_days = 0
    return span_days >= MIN_PROMOTION_SPAN_DAYS and len(domains) >= 2, span_days, len(domains)
```

In `apply_answer`, update the promotion call + note (currently lines ~685 and ~688-694):

```python
        eligible, span_days, n_domains = _promotion_eligible(entry.id, combined_records)
        if not eligible:
            continue
        promoted_record = {
            "asOf": as_of, "event": "promoted", "thesisId": entry.id, "detail": None,
            "note": (
                f"{entry.id}: promoted to registered "
                f"({span_days} days judged, {n_domains} publisher domains)"
            ),
        }
```

- [ ] **Step 5: Run them — verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_thesis_pacing.py tests/test_thesis_apply.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/thesis.py tests/test_thesis_pacing.py tests/test_thesis_apply.py
git commit -m "$(cat <<'EOF'
feat(F78-2): rule-5 promotion persistence measured as a >= 21-day calendar span, not 2 cycles

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Full-suite reconciliation, eval pin, and committed-book migration (Stage-2 shadow-check)

The pacing change is behavior-sensitive. Reconcile any remaining pinned tests deterministically, confirm the eval pin is green, then migrate the one committed thesis book so the live store stays loadable — and capture the before/after streak diff as this stage's shadow-check evidence (spec §7: "thesis day-gap streak / promotion").

**Files (candidates to reconcile — confirm by running):**
- `tests/test_thesis_models.py`, `tests/test_thesis_prompt.py`, `tests/test_cli_thesis.py`, `tests/test_thesis_e2e.py`, `tests/test_memory_bundle.py`, `tests/test_brief_*.py` (all touch `ThesisEntry`/`streak`/the book, per the grep).
- Migrate: `store/theses/chips.merchant-gpu/book.json` (rebuild under the new code).

- [ ] **Step 1: Run the full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: the thesis/pacing tests pass; a small number of downstream tests may fail only if they pin ThesisEntry's exact field set or a specific streak value. `tests/test_thesis_e2e.py` and `tests/test_cli_thesis.py` seed FRESH tmp stores (single all-reaffirmed cycle, `lastPaceAsOf == ""` → first signal counts) and assert verdicts/ordering, not streak numbers, so they stay green.

- [ ] **Step 2: Reconcile each failure deterministically**

For each failure, recompute the expected value under calendar-day pacing and update the literal — never weaken an assertion to a range. If a test pins ThesisEntry's field set, add `lastPaceAsOf`. If a test constructs an entry and asserts a streak that assumed per-cycle advance, restate it with the fixture's real day-gap. Do NOT touch `brief.py` (its `"{streak} cycles"` wording is a Stage-5 renderer concern; the streak *value* it prints is read straight from the entry, unaffected by this code).

- [ ] **Step 3: Confirm the eval pin is green**

Run: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS. The thesis seam hashes the static `fixtures/evals/hash-input.json` book through `_book_entry_lines`, which is untouched and never emits `lastPaceAsOf`; no emitted prompt byte changed. If it goes red, a prompt path was touched — stop and re-scope.

- [ ] **Step 4: Migrate the committed thesis book (deterministic) + shadow-check evidence**

`ThesisStore.load()` verifies `book.json == rebuild()`. Because `streak`/`lastPaceAsOf` are now code-derived under the new day-gap logic, the committed `book.json` (written by the old per-cycle code) would drift and `load()` would raise `ThesisStoreError` on the next live run. Rebuild it from `history.jsonl` (the source of truth) and rewrite the book — this is pure and deterministic (`rebuild()` reads history directly, not the stale book), and the streak drop it produces IS the Stage-2 shadow-check (spec §7). Reconfigure stdout to UTF-8 first (Windows note):

```bash
.venv/Scripts/python - <<'PY'
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, pathlib
from gpu_agent.thesis import ThesisStore

root = "store/theses/chips.merchant-gpu"
old = json.loads(pathlib.Path(root, "book.json").read_text("utf-8"))
old_streak = {e["id"]: e["streak"] for e in old["entries"]}

store = ThesisStore(root)
rebuilt = store.rebuild()          # NEW-code replay of history.jsonl; ignores the stale book
store.write(rebuilt, [])           # rewrite book.json to match; NO new history appended
store.load()                       # must NOT raise -> book.json == rebuild() now

print(f"{'thesis':<52} old -> new  lastPaceAsOf")
for e in rebuilt.entries:
    print(f"{e.id:<52} {old_streak.get(e.id, '?'):>3} -> {e.streak:<3} {e.lastPaceAsOf!r}")
PY
```
Expected: `load()` does not raise; the printed streaks are **lower** than the old per-cycle values wherever the committed history's judgments were spaced < 21 days apart (e.g. the 2026-07-02/03/05/06 dailies collapse to a single counted signal), and each entry now carries a `lastPaceAsOf`. This is the spec's Stage-2 shadow-check slice: the daily cadence no longer inflates the streak. No stored *scorecard* is edited.

- [ ] **Step 5: Commit the reconciliation + book migration**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test(F78-2): reconcile thesis pinned tests to calendar-day pacing; migrate committed book; suite green

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Spec coverage (§5.2 thesis-pacing paragraph / D5):** streak advance re-expressed in calendar days (Task 2), conviction swing rate-limited so low↔high cannot move faster than the intended cross-period pace (Task 3), rule-5 promotion persistence re-expressed as a calendar span (Task 4). All day-math via `asof.days_between`/`period_end`; no wall-clock. Provisional values stated (`MIN_PACE_GAP_DAYS = 21`, `MIN_PROMOTION_SPAN_DAYS = 21`), chosen to approximate today's ~monthly behavior; exact tuning deferred (D5). ✅
- **Placeholders:** none — every code step is the real edit grounded in the actual `thesis.py` (line anchors given), reusing the existing `is_reversal`, `_bump_conviction`, `DIRECTION`, and record shape.
- **Determinism / eval pin:** `_pace_counts` and the span use period-ends only; the emitted thesis prompt is byte-stable (untouched `_book_entry_lines`, `lastPaceAsOf` never emitted) → `tests/test_evals_baseline_pin.py` stays green (Task 5 Step 3). ✅
- **Frozen core:** `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*` untouched; `gpu_agent/wiki/lifecycle.py` (the separate wiki-page promotion pinned by `test_lifecycle_promotion.py`) explicitly out of scope. Only `thesis.py` + thesis tests + the one committed book change.
- **Pinned thesis tests (a–k):** most stay green unchanged because they are single-cycle (`lastPaceAsOf == ""` → first signal counts, so a–i, k behave identically); only the multi-cycle streak-derivation test and the two promotion `j` tests need deterministic date/assertion updates (Tasks 2 & 4) — no assertion weakened to a range.
- **Type consistency:** `_pace_counts(str, str) -> bool`; `_promotion_eligible(...) -> (bool, int, int)` with `span_days` replacing the old `n_asofs`; `ThesisEntry.lastPaceAsOf: str = ""` code-derived in `_apply_judgment_record`, matched by the updated `_apply_judgment_to_book` test helper so rebuild round-trips hold.

## Known follow-ups (out of scope here)

- `brief.py:360` renders `"{entry.streak} cycles"` — the word "cycles" is now imprecise (the streak counts ~21-day-spaced confirmations). Left untouched; the change-first renderer rework (F78 Stage 5) owns that wording. The streak *value* it prints is unaffected by this code.
- `gpu_agent/memory.py:140` serializes `streak` into the memory bundle — value shifts under calendar-day pacing, no code change needed.
- Exact recalibration of both day dials is deferred to the post-Stage tuning pass (D5).
