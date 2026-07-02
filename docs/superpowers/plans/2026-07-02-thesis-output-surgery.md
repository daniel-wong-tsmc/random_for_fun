# Sub-project 5-2 — Output Surgery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Prerequisite: piece 5-1 (thesis engine) is merged — this plan consumes its interfaces.**

**Goal:** The report leads with THE CALLS (thesis book with per-cycle deltas) above a words-first STATE OF THE MARKET and a WHY section projected from the book; raw indices demote to the trust footer (spec §4 of `docs/superpowers/specs/2026-07-02-thesis-book-design.md`).

**Architecture:** New pure module `gpu_agent/bands.py` (five-word band map); new renderers `render_the_calls` / `render_why` in `gpu_agent/brief.py`; `report.render_report` gains `thesis_book=None` (the same precompute-and-pass seam `movement` uses) and reorders sections; `cli._report` loads the book when present. Everything stays a deterministic pure projection — no LLM, no new numbers.

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints

- Read the spec §4 first; it wins on wording details.
- **Consumes from 5-1 (exact names):** `gpu_agent.thesis.ThesisBook`, `ThesisEntry` (fields: id, title, statement, lens, status, conviction, lastVerdict, lastDirection, pendingChallenge, streak, mechanism, falsifiableTrigger, sensitivity, lastJudgedAsOf), `ThesisStore` (`.exists()`, `.load()`), `CONVICTION_RANK`.
- **NEVER edit:** the frozen v1.2 core, `gpu_agent/thesis.py`, `gpu_agent/memory.py`, `judgment/*`, `wiki/*`, `gathering/*`, `price_track.py` internals (import it, don't change it).
- Files you own: `gpu_agent/bands.py` (new), `gpu_agent/brief.py`, `gpu_agent/report.py`, `gpu_agent/cli.py` (`_report` only), run-cycle SKILL.md report-step note, and tests.
- Byte-determinism: same inputs → identical report text; pin with tests.
- Tests: `.venv/Scripts/python -m pytest -q`; suite green at the end of every task. Trailer on every commit.

---

### Task 1: `gpu_agent/bands.py` — the five-word band map

**Files:** Create `gpu_agent/bands.py`; Test `tests/test_bands.py`.

**Interfaces (Produces):**
```python
BANDS = [(0.30, "accelerating"), (0.05, "firm"), (-0.05, "flat"), (-0.30, "softening")]
# value >= 0.30 accelerating; >= 0.05 firm; > -0.05 flat; > -0.30 softening; else contracting

def band_word(value: float) -> str: ...
def band_with_prior(value: float, prior: float | None) -> str:
    # 'ACCELERATING ▲ (was FIRM)'; prior None -> 'ACCELERATING ▲ (no prior)'
    # arrow: ▲ if band rank rose vs prior, ▼ if fell, = if same band, · when no prior
```

- [ ] **Step 1: Failing tests:** boundary values (0.30→accelerating, 0.05→firm, 0.049999→flat, −0.05→softening boundary per the > rule — pin exact inclusivity as written above), `band_with_prior(0.41, 0.51)` == `"ACCELERATING = (was ACCELERATING)"` (same band → =), `band_with_prior(0.2, 0.5)` == `"FIRM ▼ (was ACCELERATING)"`, no-prior case.
- [ ] **Step 2:** FAIL. **Step 3:** Implement (pure; words uppercased only by the formatter). **Step 4:** Green + suite. **Step 5:** Commit `feat(5-2): five-word band map - indices become words with an earned (was X)`.

---

### Task 2: `render_the_calls` in brief.py

**Files:** Modify `gpu_agent/brief.py`; Test `tests/test_brief_calls.py`.

**Interfaces (Produces):**
```python
def render_the_calls(book, sc, last_findings: dict[str, list[str]] | None = None) -> str:
    """THE CALLS. book: ThesisBook | None. sc: Scorecard (for finding lookups).
    last_findings: latest judgment findingIds per thesis id (from history; see rules below).
    None book -> 'THE CALLS\n  (no thesis book yet - runs after the first thesis cycle)'"""
```
Rendering rules (spec §4, pin each with a test):
- Entries: non-retired, `registered` before `provisional`, then `(-CONVICTION_RANK[conviction], id)`.
- Per entry, three lines:
  `  ● <title>   <STATE>, <lastVerdict> <arrow>  (<conviction>, <streak> cycles)`
  `      <statement of the first cited finding from the entry's latest judgment, truncated to 90 chars>  [<findingIds>] <tier>`
  `      breaks if: <falsifiableTrigger>`
  where STATE = `INTACT` | `CHALLENGED — pending confirmation ⚠` (when pendingChallenge) ; arrows strengthened ▲ / weakened ▼ / reaffirmed = / adjusted ~ / broken ✕. The cited-finding line needs the entry's latest findingIds — 5-1's book does NOT store them; ADD them: the book entry field `lastFindingIds: list[str] = []` was NOT in 5-1's schema, so the renderer takes them from a companion dict: `render_the_calls(book, sc, last_findings: dict[str, list[str]] | None = None)` where cli passes the latest history records' findingIds per thesis (loaded via ThesisStore history read — implemented in Task 4). When absent → the evidence line renders `      (citations in history)` — never invented.
- A `retired` entry whose `lastChangedAsOf == sc.asOf` renders once as `  ✕ <title>   BROKEN — retired`.
- Tier tag: `primary` if any cited finding (resolvable in sc.findings) has primary evidence else `secondary`; unresolvable → omit the tier word.
- Nothing-changed headline: when every standing entry's lastVerdict is `reaffirmed` and no pendingChallenge and no entry changed this cycle → first line after the header is `  Nothing changed this cycle. (<n> theses reaffirmed)` followed by the compact one-line-per-thesis book.
- Provisional entries append `  (provisional)`.

- [ ] **Step 1: Failing tests:** ordering; CHALLENGED render; BROKEN-once render; nothing-changed headline; provisional tag; missing-citations fallback; byte-stability (two calls equal).
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** Green + suite. **Step 5:** Commit `feat(5-2): THE CALLS - the thesis book leads the page with earned deltas`.

---

### Task 3: `render_why` in brief.py

**Files:** Modify `gpu_agent/brief.py`; Test `tests/test_brief_why.py`.

**Interfaces (Produces):**
```python
def render_why(book) -> str:
    """WHY (drivers -> constraints) - a pure projection of the thesis book by lens.
    None/empty book -> 'WHY\n  (no thesis book yet)'"""
```
- `Pulling demand:` mechanisms of `lens == "demand"` entries with conviction ≥ medium, status registered, no pendingChallenge — one line each: `    • <mechanism>  (<title>)`.
- `Capping supply:` same for `lens == "supply"`.
- `Contested:` every entry with pendingChallenge OR status provisional OR `lens == "competitive"`/`"risk"` with conviction low — line: `    • <mechanism>  (<title> — <CHALLENGED ⚠|provisional|low conviction>)`.
- Empty groups render `    (none)`. Deterministic order: `(-CONVICTION_RANK, id)` within groups.

- [ ] **Step 1: Failing tests:** grouping per lens; contested precedence (a challenged demand thesis appears under Contested, not Pulling demand); empty-group `(none)`; byte-stability.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** Green + suite. **Step 5:** Commit `feat(5-2): WHY - drivers vs constraints projected from the thesis book, every line owned by a thesis`.

---

### Task 4: Page reorder + words-first STATE + index demotion + CLI loading

**Files:** Modify `gpu_agent/report.py` (`render_report` + the trust footer), `gpu_agent/brief.py` (`render_state_of_market` rework), `gpu_agent/cli.py` (`_report`), `.claude/skills/run-cycle/SKILL.md` (one line: the report step notes it renders THE CALLS from the just-updated book); Test `tests/test_report_surgery.py` + update existing `tests/test_brief_state.py` / `tests/test_brief_report.py` / `tests/test_cli_report.py` expectations.

**Interfaces (Produces):**
- `render_report(sc, prior, registry, *, render_ts=None, horizons=None, movement=None, thesis_book=None, thesis_last_findings=None)` — new optional params, default None keeps legacy layout available to old callers BUT the section ORDER changes for everyone (order is not a per-caller contract):
  `HEADER → THE CALLS → STATE OF THE MARKET → WHY → WHAT MOVED → DEMAND|SUPPLY board → STORYLINES → PRICE TRACK → ENTITY PANEL → EVIDENCE QUALITY → SOURCES → COVERAGE GAPS → TRUST & COVERAGE (+ the raw index table)`.
- `render_state_of_market(sc, prior)` rework: Demand/Supply lines become `Demand: <band_with_prior(dmi, prior_dmi)>` etc. via `gpu_agent.bands`; the raw `(DMI 0.227, Δ −0.280)` parenthetical MOVES to the trust footer as a small table `DMI/SMI/SDGI  value  Δ  (was-band)`; the SDGI interpretation sentence stays; NOW/NEXT + divergence + BINDING CONSTRAINT lines stay.
- `cli._report`: after loading the scorecard — `tstore = ThesisStore(pathlib.Path(args.store) / "theses" / sc.categoryId)`; when `tstore.exists()`: `thesis_book = tstore.load()`, `thesis_last_findings` = per-thesis findingIds of the latest history judgment records (read `history.jsonl`, last record per thesisId); pass both. Absent store → None (honest empty-states render).

- [ ] **Step 1: Failing tests:**

```python
# 1. section order: render a full fixture and assert index positions:
#    out.index('THE CALLS') < out.index('STATE OF THE MARKET') < out.index('WHY') <
#    out.index('WHAT MOVED') < out.index('TRUST & COVERAGE')
# 2. 'DMI 0.' appears ONLY after the TRUST & COVERAGE heading; the STATE section contains
#    'Demand: ' with a band word and '(was ' or '(no prior)'
# 3. thesis_book=None -> THE CALLS + WHY render their honest empty-state lines and the
#    report still renders end-to-end byte-stably
# 4. CLI: gpu-agent report over a tmp store WITH a seeded+judged thesis book (reuse the
#    5-1 clean-answer fixture flow to build it) -> stdout contains a '● ' calls row and
#    'breaks if:'; over a store without theses -> the empty-state line
# 5. byte-determinism: two renders identical
```

- [ ] **Step 2:** FAIL. **Step 3:** Implement; update the existing brief/report tests whose assertions pin the OLD order or the old `Demand momentum: positive` wording — move assertions, never delete coverage (each old assertion gets a new-format equivalent).
- [ ] **Step 4:** Green + FULL suite. **Step 5:** Commit `feat(5-2): the page tells you something - CALLS first, words-first state, WHY from the book, indices demoted to the footer`.

---

### Task 5: End-to-end acceptance render

**Files:** Test `tests/test_thesis_e2e.py` (new; no source changes expected).

- [ ] **Step 1:** Write the acceptance test: in tmp, copy `store/chips.merchant-gpu/2026-07-02-v1.json` + seed a thesis store + apply the committed clean-answer fixture via the CLI (`thesis --recorded`), then `gpu-agent report --scorecard ... --store ...` and assert: THE CALLS lists all six seed theses with verdicts; STATE has band words; WHY has all three groups; the raw DMI value appears only in the footer; exit 0.
- [ ] **Step 2:** Run — if anything fails, it's a real integration gap in Tasks 1–4: fix THERE (this task adds no new behavior). **Step 3:** Green + full suite. **Step 4:** Commit `test(5-2): end-to-end acceptance - a cycle's report leads with the thesis book`.

---

## Self-review checklist
- Spec §4 fully covered: CALLS format/ordering/nothing-changed (T2), WHY (T3), band map + demotion + reorder + CLI (T4), acceptance (T5).
- Consumed 5-1 names match its plan's Produces blocks (ThesisBook/ThesisStore/CONVICTION_RANK; `thesis_last_findings` companion dict documented — 5-1's book intentionally does not store findingIds).
- No frozen file, no thesis.py/memory.py edits; suite green.
