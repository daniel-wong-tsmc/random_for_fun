# F23 Charter Compliance Matrix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an honest, machine-checkable map of every binding charter clause to where it is actually enforced (`docs/compliance-matrix.md`) plus a deterministic lint that keeps the map from rotting (`tests/test_compliance_matrix.py`).

**Architecture:** The lint is a pure-stdlib pytest module that parses two strict markdown tables out of the matrix doc (a 6-column matrix, a 2-column summary), reads the charter live to enumerate Parts, and asserts internal consistency + that every referenced path/test exists. The matrix is authored by hand and grouped by Part; the lint is its regression test. No product code is touched.

**Tech Stack:** Python stdlib only (`re`, `pathlib`, `collections`), pytest. Markdown (GFM tables).

## Global Constraints

- **Diff is docs + one test file only.** No change under `gpu_agent/`, `store/`, `registry/`, `taxonomy.json`, or any existing test. Verbatim from the lane brief.
- **Suite green at every commit.** Baseline: `1200 passed / 5 skipped`. Run from worktree root: `../../.venv/Scripts/python -m pytest -q`.
- **`tests/test_compliance_matrix.py` must not import product code** — pure stdlib, so it cannot be contaminated by product changes.
- **`tests/test_evals_baseline_pin.py` red = contamination → STOP and report.** It cannot go red from a docs+test-only change.
- **Repo-root resolution in tests:** `pathlib.Path(__file__).resolve().parents[1]` (the repo/worktree root), matching `tests/test_handoff_integrity.py`.
- **Matrix format is strict:** 6-column table `Clause ID | Part | Clause | Status | Enforcement | Pinning test`; every row exactly 6 cells; no literal `|` inside a cell; paths are repo-root-relative; **no line numbers** (`:NN`) anywhere; controlled 6-status vocabulary `ENFORCED | PARTIAL | SESSION-PROSE | DEFERRED | NOT-ENFORCED | NARRATIVE`.
- **Small commits; `git log --oneline -1` immediately before every commit** (concurrent-instance guard). Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **No new backlog items.** Gaps go in the matrix's Findings section only.

---

### Task 1: The lint + a complete-enough matrix (green in one commit)

Because the suite must be green at every commit, the first commit that adds `test_compliance_matrix.py` must already pass. So this task writes the lint (observing red first in the working tree), then authors a matrix that covers **all 39 Parts** with the high-confidence rows, reconciles the summary, and commits only once green.

**Files:**
- Create: `tests/test_compliance_matrix.py`
- Create: `docs/compliance-matrix.md`

**Interfaces:**
- Produces (module-level, used by Tasks 2–3 only implicitly — they edit the doc, not the test): parser helpers `_matrix_rows()`, `_summary_counts()`, `_charter_parts()`, constant `STATUSES`, `COLUMNS`.

- [ ] **Step 1: Write the failing lint test**

Create `tests/test_compliance_matrix.py` with the full lint:

```python
"""F23 — charter compliance matrix lint.

Parses docs/compliance-matrix.md and fails if the matrix is internally
inconsistent or references anything that does not exist. Pure stdlib — no
product imports — so it cannot be contaminated by product-code changes.

The matrix maps every binding charter clause to its enforcement point and
pinning test. This lint stops the map from rotting silently (the F23 goal:
keep 'binding' from drifting into aspiration).
"""
import re
import pathlib
from collections import Counter

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/compliance-matrix.md"
CHARTER = ROOT / "docs/agent-swarm-charter.md"

COLUMNS = ["Clause ID", "Part", "Clause", "Status", "Enforcement", "Pinning test"]
SUMMARY_COLUMNS = ["Status", "Count"]
STATUSES = {"ENFORCED", "PARTIAL", "SESSION-PROSE", "DEFERRED", "NOT-ENFORCED", "NARRATIVE"}

# a repo-root-relative path token, e.g. gpu_agent/gate.py, registry/x.json,
# .claude/skills/run-cycle/SKILL.md  (optional ::symbol suffix)
_PATH_RE = re.compile(r"[.\w][\w./-]*\.(?:py|json|md|toml|cmd)(?:::[\w]+)?")
_CLAUSE_ID_RE = re.compile(r"^P(\d+)(?:\.[\w-]+)?$")
_LINENO_RE = re.compile(r"\.py:\d+")


def _cells(line):
    # a table row: strip leading/trailing pipe, split on '|', trim cells
    inner = line.strip()
    inner = inner[1:] if inner.startswith("|") else inner
    inner = inner[:-1] if inner.endswith("|") else inner
    return [c.strip() for c in inner.split("|")]


def _is_separator(cells):
    return all(set(c) <= set("-: ") and c for c in cells)


def _table_after(header_cells):
    """Return the list of data-row cell-lists for the single table whose header
    equals header_cells. Fails if not exactly one such header exists."""
    lines = MATRIX.read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines)
              if ln.lstrip().startswith("|") and _cells(ln) == header_cells]
    assert len(starts) == 1, (
        f"expected exactly one table with header {header_cells}, found {len(starts)}")
    rows = []
    i = starts[0] + 1
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = _cells(lines[i])
        if not _is_separator(cells):
            rows.append(cells)
        i += 1
    return rows


def _matrix_rows():
    return _table_after(COLUMNS)


def _summary_counts():
    out = {}
    for cells in _table_after(SUMMARY_COLUMNS):
        assert len(cells) == 2, f"summary row not 2 cells: {cells}"
        out[cells[0]] = int(cells[1])
    return out


def _charter_parts():
    text = CHARTER.read_text(encoding="utf-8")
    return sorted({int(m) for m in re.findall(r"^## Part (\d+)", text, re.M)})


# ---- the checks -----------------------------------------------------------

def test_matrix_file_exists():
    assert MATRIX.is_file(), f"{MATRIX} missing"


def test_rows_have_six_cells():
    for cells in _matrix_rows():
        assert len(cells) == len(COLUMNS), f"row not {len(COLUMNS)} cells: {cells}"


def test_clause_ids_wellformed_unique_and_match_part():
    seen = set()
    for cells in _matrix_rows():
        cid, part = cells[0], cells[1]
        m = _CLAUSE_ID_RE.match(cid)
        assert m, f"bad Clause ID: {cid!r}"
        assert cid not in seen, f"duplicate Clause ID: {cid}"
        seen.add(cid)
        assert part.isdigit(), f"Part not an int: {part!r} ({cid})"
        assert int(m.group(1)) == int(part), f"Clause ID {cid} disagrees with Part {part}"
        assert 1 <= int(part) <= 39, f"Part out of range: {part} ({cid})"


def test_status_vocabulary_controlled():
    for cells in _matrix_rows():
        assert cells[3] in STATUSES, f"bad Status {cells[3]!r} in {cells[0]}"


def test_no_line_numbers_anywhere():
    for cells in _matrix_rows():
        for c in cells:
            assert not _LINENO_RE.search(c), f"line-number ref in {cells[0]}: {c!r}"


def test_every_charter_part_present():
    parts_in_matrix = {int(cells[1]) for cells in _matrix_rows()}
    missing = [p for p in _charter_parts() if p not in parts_in_matrix]
    assert not missing, f"charter Parts with no matrix row: {missing}"


def test_referenced_paths_exist():
    for cells in _matrix_rows():
        for col in (cells[4], cells[5]):        # Enforcement, Pinning test
            for tok in _PATH_RE.findall(col):
                path_part = tok.split("::", 1)[0]
                assert (ROOT / path_part).is_file(), (
                    f"{cells[0]}: referenced path does not exist: {path_part}")


def test_referenced_test_functions_exist():
    for cells in _matrix_rows():
        for col in (cells[4], cells[5]):
            for tok in _PATH_RE.findall(col):
                if "::" not in tok:
                    continue
                path_part, sym = tok.split("::", 1)
                body = (ROOT / path_part).read_text(encoding="utf-8")
                assert re.search(rf"def {re.escape(sym)}\b", body), (
                    f"{cells[0]}: {sym} not defined in {path_part}")


def test_summary_counts_match_rows():
    rows = _matrix_rows()
    actual = Counter(cells[3] for cells in rows)
    summary = _summary_counts()
    for status in STATUSES:
        assert summary.get(status, 0) == actual.get(status, 0), (
            f"summary {status}={summary.get(status, 0)} but rows have {actual.get(status, 0)}")
    assert set(summary) <= STATUSES, f"summary lists unknown status: {set(summary) - STATUSES}"
    assert sum(summary.values()) == len(rows), "summary total != row count"
```

- [ ] **Step 2: Run the lint to verify it fails (red)**

Run: `cd C:/Users/danie/random_for_fun/.worktrees/f23-compliance && ../../.venv/Scripts/python -m pytest tests/test_compliance_matrix.py -q`
Expected: FAIL — `test_matrix_file_exists` (and the parser helpers) error because `docs/compliance-matrix.md` does not exist yet.

- [ ] **Step 3: Author the matrix doc covering all 39 Parts**

Create `docs/compliance-matrix.md` with this skeleton, then fill rows (see the enforcement map in the appendix). Every Part 1–39 needs ≥1 row. Use the high-confidence rows now; deepen in Tasks 2–3.

````markdown
# Charter compliance matrix (F23)

> Maps every **binding** clause of `docs/agent-swarm-charter.md` to where it is actually enforced and
> the test that pins it. **Honesty is the product** — an accurate `NOT-ENFORCED` row is a success, not
> a failure. Design: `docs/superpowers/specs/2026-07-12-f23-compliance-matrix-design.md`.
>
> **Format contract (kept parseable by `tests/test_compliance_matrix.py`):** the matrix is the single
> 6-column table below; the summary is the single `Status | Count` table. Every row has exactly 6
> cells, no literal `|` inside a cell. Paths are repo-root-relative; **no line numbers** — reference a
> function/rule by name in parentheses. `Status` is one of:
> `ENFORCED · PARTIAL · SESSION-PROSE · DEFERRED · NOT-ENFORCED · NARRATIVE`.

## Summary

| Status | Count |
|---|---|
| ENFORCED | 0 |
| PARTIAL | 0 |
| SESSION-PROSE | 0 |
| DEFERRED | 0 |
| NOT-ENFORCED | 0 |
| NARRATIVE | 0 |

## Compliance matrix

| Clause ID | Part | Clause | Status | Enforcement | Pinning test |
|---|---|---|---|---|---|
| P1.1 | 1 | Every metric has a why — no naked numbers | ENFORCED | gpu_agent/gate.py (check_finding, why non-empty) | tests/test_gate_finding.py |
| ... | ... | ... | ... | ... | ... |

## Findings

(Prose — the NOT-ENFORCED and thinner-than-implied PARTIAL rows. No new backlog items.)
````

Fill every Part 1–39. Reconcile the six summary counts to the actual row tallies (the lint checks this exactly).

- [ ] **Step 4: Run the full lint to verify it passes (green)**

Run: `../../.venv/Scripts/python -m pytest tests/test_compliance_matrix.py -q`
Expected: PASS (all checks). If `test_referenced_paths_exist` or `test_referenced_test_functions_exist` fails, fix the offending cell (wrong path or wrong test name) — do not weaken the lint.

- [ ] **Step 5: Run the full suite to confirm green baseline**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: `1200 passed / 5 skipped` **plus** the new matrix tests (so `~1209 passed / 5 skipped`). Confirm `tests/test_evals_baseline_pin.py` is not red.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/danie/random_for_fun/.worktrees/f23-compliance
git log --oneline -1
git add tests/test_compliance_matrix.py docs/compliance-matrix.md
git commit -F - <<'EOF'
feat(f23): compliance-matrix lint + matrix covering all 39 charter Parts

Deterministic pure-stdlib lint parses the matrix, verifies clause IDs,
status vocabulary, per-Part completeness (read live from the charter),
that every referenced path/test exists, and that the summary counts match
the rows. Matrix seeded with the high-confidence rows.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 2: Deepen the in-force doctrine (Parts 1–18)

Add the fine-grained clause rows for the doctrine that is *currently in force* — where binding→aspiration drift is most dangerous (this is where F2/F3/F5 lived). Each added row keeps the lint green (adding rows only tightens per-Part completeness; the summary must be re-reconciled).

**Files:**
- Modify: `docs/compliance-matrix.md`

- [ ] **Step 1: Add the remaining Part 1–18 clause rows**

For each, quote/paraphrase the clause, set the honest status, and cite the enforcement point + pinning test. Use the appendix map. Cover at minimum: Part 1 rules 1–7 + confidence/dispersion; Part 2 field-rules-by-kind (measured/observed/hypothesis) + v1.1 polarity; Part 7 gate checklist boxes (each a row); Part 8 guardrails; Part 17 rating scale + plain-language rule + anchor bound + DMI/SMI/SDGI; Part 18 principles 1–8 + the three discipline rules.

- [ ] **Step 2: Re-reconcile the summary counts**

Update the six counts in the `## Summary` table to the new tallies.

- [ ] **Step 3: Run the lint (green)**

Run: `../../.venv/Scripts/python -m pytest tests/test_compliance_matrix.py -q`
Expected: PASS. If `test_summary_counts_match_rows` fails, fix the summary numbers.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/danie/random_for_fun/.worktrees/f23-compliance
git log --oneline -1
git add docs/compliance-matrix.md
git commit -F - <<'EOF'
docs(f23): deepen matrix — Parts 1-18 in-force doctrine clauses

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 3: Parts 19–39 breakout + Findings section

Break out the specific ENFORCED/PARTIAL rows where later Parts actually landed (Part 20 provenance, Part 21 reconciliation, Part 24 eval harness, Part 26 corroboration, Part 33 migrations, Part 37 gatherer swarm + corroboration, Part 38 seams/cycle log, Part 39 sub-project 4), keep the honest DEFERRED rows for the rest, then write the Findings section.

**Files:**
- Modify: `docs/compliance-matrix.md`

- [ ] **Step 1: Add/refine Part 19–39 rows**

Mark genuinely-built mechanisms ENFORCED/PARTIAL with their tests; mark unbuilt binding mechanisms DEFERRED (name the roadmap phase); mark any in-force-sounding-but-unenforced clause NOT-ENFORCED.

- [ ] **Step 2: Write the Findings section**

Prose listing: (a) every `NOT-ENFORCED` row (aspiration-only), (b) notably `PARTIAL` rows thinner than the charter implies (e.g. Part 21 "counted once" pending F24 entity canonicalization; Part 26 hard-corroboration staged), (c) any ENFORCED-but-unpinned rows. No new backlog items — surface for the user to triage at merge review.

- [ ] **Step 3: Re-reconcile summary + run lint (green)**

Run: `../../.venv/Scripts/python -m pytest tests/test_compliance_matrix.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/danie/random_for_fun/.worktrees/f23-compliance
git log --oneline -1
git add docs/compliance-matrix.md
git commit -F - <<'EOF'
docs(f23): matrix Parts 19-39 breakout + Findings section

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

### Task 4: Full verification, sentinel, final push

**Files:**
- Create: `.superpowers/handoffs/f23-compliance-DONE.md` (gitignored — plain file write, not committed)

- [ ] **Step 1: Full suite**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: all green (`~1211 passed / 5 skipped`), `test_evals_baseline_pin.py` not red. If it is red → STOP, report contamination.

- [ ] **Step 2: Confirm diff scope**

Run: `git diff --stat main...HEAD`
Expected: only `docs/compliance-matrix.md`, `tests/test_compliance_matrix.py`, `docs/superpowers/specs/2026-07-12-f23-compliance-matrix-design.md`, `docs/superpowers/plans/2026-07-12-f23-compliance-matrix.md`. Nothing under `gpu_agent/`, `store/`, `registry/`.

- [ ] **Step 3: Push**

Run: `git push` (branch already tracks origin).

- [ ] **Step 4: Write the DONE sentinel**

Write `.superpowers/handoffs/f23-compliance-DONE.md` with date, branch + commit hashes, suite status, delivered list, top findings (aspiration-only clauses), and open decisions (the AFK-precedent forks A1–A3 from the spec). Do NOT merge — stop for the user.

---

## Appendix — enforcement-point map (research already done)

High-confidence clause → enforcement → test anchors to draw rows from (verify each path/test name exists as you place it; the lint will catch mistakes):

- **P1.1 why / P1.2 no invented number / P2 field rules** → `gpu_agent/gate.py` (`check_finding`) → `tests/test_gate_finding.py`, `tests/test_finding_schema.py`.
- **P1.3 impact / P21-impact-quality** → `gpu_agent/gate.py` (F21 targets+mechanism non-empty) → `tests/test_gate_finding.py`.
- **P1.5 provenance/source tier / P2 evidence** → `gpu_agent/gate.py` (F2a evidence required; tier stamped in `gpu_agent/gathering/ingest.py`) → `tests/test_gate_finding.py`, `tests/test_ingest.py`, `tests/test_raw_document.py`.
- **P1.6 hypothesis capped ≤ medium** → `gpu_agent/gate.py` (hypothesis confidence cap) → `tests/test_gate_finding.py`.
- **P1.7 / P17 plain-language (no jargon)** → `gpu_agent/judgment/` voice lint → `tests/test_judge_voice_lint.py`; also SESSION-PROSE (skill: stop-slop) — likely PARTIAL.
- **P7 gate checklist** (one row per box): measured value+source, no invented value, why, impact, provenance-or-reasoning, hypothesis label+cap, dispersion, ratings cite finding IDs, no dashboard self-reference, polarity declared, rating-vs-anchor bound → all `gpu_agent/gate.py` (`check_finding`/`check_scorecard`) → `tests/test_gate_finding.py`, `tests/test_gate_scorecard.py`, `tests/test_gate_corroboration.py`.
- **P7 secondary-only confidence cap / F2e / P37 corroboration** → `gpu_agent/gate.py` (F2e, `collapsed_publisher_set`) + `gpu_agent/publisher.py` + `gpu_agent/sufficiency.py` → `tests/test_gate_corroboration.py`, `tests/test_publisher.py`, `tests/test_sufficiency.py`, `tests/test_cli_sufficiency.py`. Likely PARTIAL (staged path to Part 26).
- **P8 injection / data-not-instructions** → `gpu_agent/extraction/prompt.py` (F16 delimiting) → `tests/test_extraction_prompt.py`; tool-less dispatch is SESSION-PROSE (skill: gather-category). PARTIAL.
- **P8 vintage honesty** → `gpu_agent/gate.py` (F17 `_future_dated`, ISO dates) → `tests/test_gate_finding.py`.
- **P8 dispersion / corroboration merge** → `gpu_agent/gathering/dedup.py` (F10) → `tests/test_dedup_classify.py`, `tests/test_corroboration_config.py`.
- **P17 rating scale / anchor bound / weakest-link** → `gpu_agent/gate.py` (`_rating_consistent_with_anchor`, F36) + `gpu_agent/scoring.py` + `gpu_agent/bands.py` → `tests/test_gate_scorecard.py`, `tests/test_scoring.py`, `tests/test_bands.py`, `tests/test_rating_anchors.py`.
- **P17/P2 DMI/SMI/SDGI computed in code** → `gpu_agent/scoring.py` (F7 `(entity, indicatorId)` bucket) → `tests/test_scoring.py`, `tests/test_scoring_entity.py`, `tests/test_scoring_per_indicator.py`.
- **P18 define-once / registries / modularity** → `registry/indicators.json`, `taxonomy.json`, `gpu_agent/registry/` → `tests/test_registry_structure.py`, `tests/test_registry_validate.py`, `tests/test_taxonomy_scope.py`, `tests/test_assignment.py`.
- **P19 no silent partial / cycle coverage** → `gpu_agent/cycle.py` + cycle log → `tests/test_cycle_plan.py`, `tests/test_store_cycle_log_integrity.py`.
- **P20 provenance stamp** → check `gpu_agent/schema/finding.py` provenance fields → `tests/test_finding_schema.py` (verify — may be PARTIAL/DEFERRED).
- **P21 entity counted-once / reconciliation** → PARTIAL/NOT-ENFORCED — F24 (entity canonicalization) still open in `docs/fix-backlog.md`; note in Findings.
- **P24 eval harness / regression gate** → `gpu_agent/evals/` + `gpu_agent/evals/prompt_hash.py` → `tests/test_evals_baseline_pin.py`, `tests/test_evals_harness_gate.py`, `tests/test_evals_hash.py`, `tests/test_evals_v2.py`.
- **P26 hard-corroboration / circular-source** → DEFERRED (charter says staged); partial via `gpu_agent/publisher.py` syndication collapse + `registry/syndicators.json` → `tests/test_publisher.py`.
- **P28 scheduling / P14 interactive / P38 Layer+Main tiers / P9 canonical store** → DEFERRED (roadmap Phases 3–7; charter Part 38 "Not yet").
- **P33 schema migration / frozen contract** → `gpu_agent/schema/finding.py` (`schemaVersion`) + `docs/migrations/` → `tests/test_finding_schema.py`; frozen-contract enforced by SESSION-PROSE (roadmap standing constraint) + the eval pin. PARTIAL.
- **P37 gatherer swarm / ingest seam / web-reach registry** → `gpu_agent/gathering/ingest.py` + `registry/web-reach-tools.json` + `gpu_agent/web_reach_ensure.py` → `tests/test_ingest.py`, `tests/test_web_reach_registry.py`, `tests/test_web_reach_ensure.py`, `tests/test_gather_integration.py`. Follow-the-trail loop caps = SESSION-PROSE (skill: gather-category).
- **P38 uniform tier interface / seams / cycle log** → `gpu_agent/cycle.py` + `gpu_agent/assignment.py` → `tests/test_cycle_plan.py`, `tests/test_assignment_category.py`, `tests/test_store_cycle_log_integrity.py`. Layer/Main stages DEFERRED.
- **P39 sub-project 4 (wiki, indices, momentum/outlook, discovery)** → `gpu_agent/wiki/`, `gpu_agent/registry/horizon.py`, `gpu_agent/registry/tracks.py` → `tests/test_wiki_*.py`, `tests/test_divergence.py`, `tests/test_registry_horizon.py`, `tests/test_registry_tracks.py`.

For any Part with no in-force binding clause, use one `NARRATIVE` row (e.g. Part 3 org shape, Part 6 data-contract description where the binding "schema frozen" clause is already covered under P18/P33).
