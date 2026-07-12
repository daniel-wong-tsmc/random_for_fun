# F23 — Charter compliance matrix — design spec

> **Status:** AFK design. The user was not available during this run, so every fork below is
> resolved on best judgment and labelled **AFK-precedent — user to confirm at merge review**.
> Nothing here is recorded as user-approved.
>
> **Backlog item (F23, `docs/fix-backlog.md`):** "Charter compliance matrix. Clause → enforcement
> point → test; stops 'binding' drifting into aspiration (would have caught F2/F3/F5)."
>
> **Date:** 2026-07-12 · **Branch:** `f23-compliance-matrix` · **Lane:** F23 (Feature track).

---

## 1. The problem, in one paragraph

The charter (`docs/agent-swarm-charter.md`, 39 Parts) is full of rules it calls **binding** — "must",
"never", "rejected", "enforced". Some of those rules are genuinely enforced in code; some are only
followed because a skill's prose tells an agent to; some were quietly never built. F2, F3, and F5 are
the cautionary tale: each was a binding doctrine rule that had silently become **aspiration** (stated
as in-force, enforced by nothing) until a review caught it. This feature builds an honest, machine-
checkable map — clause → where it is actually enforced → the test that pins it — and a lint that keeps
the map from rotting. **Honesty is the product:** an accurate "not enforced" row is a success.

## 2. Scope and non-goals

**In scope (the whole diff):**
- `docs/compliance-matrix.md` — the matrix (one row per binding clause) + a status summary + a
  Findings section.
- `tests/test_compliance_matrix.py` — a deterministic lint that parses the matrix and fails if it is
  internally inconsistent or references anything that does not exist.
- This spec + the implementation plan under `docs/superpowers/`.

**Non-goals (hard constraints from the lane brief):**
- **Touch no product code.** No change under `gpu_agent/`, `store/`, `registry/`, `taxonomy.json`, or
  any existing test. The matrix *reports* reality; it does not change it.
- **Do not edit the charter.** If the matrix reveals a wording problem or a gap, it goes in the
  Findings section — not into the charter, and not into new backlog items (listing gaps ≠ minting F-items).
- **No new backlog items.** Gaps are findings, surfaced for the user to triage at merge review.
- `tests/test_evals_baseline_pin.py` must stay green — it cannot go red from a docs+test-only change;
  if it does, that is contamination and the run stops.

## 3. The three forks (decisions)

### Fork A — What counts as a *binding clause* vs. narrative?

**Decision (AFK-precedent):** A binding clause is a **normative rule the charter states as currently
in force** — identified by imperative/prohibitive language (*must, never, always, required, rejected,
enforced, capped, "binding"*), the numbered doctrine rules (Part 1), the Part 7 gate checklist boxes,
the Part 8 standing guardrails, the Part 2 field rules, the Part 17 rating rules, the Part 18
principles, and each Part's "Self-check" bullets where they restate a hard rule. Purely descriptive
prose (org-chart shapes, motivation, "Reuses (don't rebuild)" lists) is **not** a clause on its own.

Two consequences, both deliberate:
- **Forward-looking mechanisms still get a row.** Parts 19–36 and the deferred tiers describe binding-
  *sounding* mechanisms that v1 has not built. Those are included and marked honestly `DEFERRED` — that
  visibility is exactly the aspiration-drift the matrix exists to expose.
- **Per-Part completeness.** The matrix carries **at least one row for every Part the charter defines**
  (1–39). A Part that states no independently-enforceable rule gets one honest `NARRATIVE` row rather
  than being silently omitted. This is machine-checked (§4, check 5) so a future Part 40 forces a new row.

Granularity: aim for thorough clause-level coverage of Parts 1–18 (the in-force doctrine, where drift
is most dangerous), and at least honest per-Part coverage of 19–39, breaking out specific ENFORCED /
PARTIAL rows where those Parts actually landed (e.g. Part 24 eval harness, Part 37 corroboration).
This is a **living floor, not a frozen ceiling** — rows can be added later without a redesign.

### Fork B — Table format (must be strictly parseable)

**Decision (AFK-precedent):** A GitHub-flavoured markdown table with a **fixed 6-column schema**,
located by an exact header-row match so the lint never guesses. Columns:

| Column | Meaning | Machine-checked? |
|---|---|---|
| `Clause ID` | stable id `P<part>[.<suffix>]`, e.g. `P1.1`, `P7.a`, `P21.count-once` | yes — unique, well-formed, part-prefix matches `Part` |
| `Part` | the Part number as an integer (1–39) | yes — in range, matches Clause ID |
| `Clause` | short quote/paraphrase of the rule | no (free text; no `\|`) |
| `Status` | one word from the controlled set (below) | yes — in the set |
| `Enforcement` | code path(s) + rule hint, or `SESSION-PROSE (skill: X)`, or `DEFERRED (…)`, or `NOT ENFORCED — aspiration`, or `—` | yes — every path-like token must exist |
| `Pinning test` | `tests/f.py::test_name` (one or more) or `—` | yes — file exists **and** `def test_name` exists |

Format rules that make it strict:
- Every data row starts and ends with `|` and has exactly 6 cells. No literal `|` inside a cell.
- **Paths are always repo-root-relative** (`gpu_agent/gate.py`, not `gate.py`). Function/rule names go
  in parentheses as *hints* and are not path-validated (`gpu_agent/gate.py (check_finding, F2e)`).
- **No line numbers anywhere** (`:NN`). Line numbers rot on every edit; reference by function/rule name.
  The lint forbids the `\.py:\d+` pattern in any cell.

**Controlled status vocabulary (exactly six):**

- `ENFORCED` — a deterministic code path (gate / lint / schema / scoring) enforces it, with a pinning test.
- `PARTIAL` — enforced, but the charter itself flags the enforcement as *staged / conservative /
  scoped* relative to the full binding intent (e.g. corroboration is a "staged path to Part 26"), **or**
  enforced in code but without a dedicated pinning test.
- `SESSION-PROSE` — enforced only by skill/prompt prose an agent follows at run time; no deterministic pin.
- `DEFERRED` — a binding mechanism the charter/roadmap explicitly defers to a later phase (Layer/Main
  tier, canonical store, scheduling, calibration).
- `NOT-ENFORCED` — reads as in-force but nothing enforces it. The aspiration-drift the matrix exists to
  catch; each one is echoed in Findings.
- `NARRATIVE` — descriptive context; states no independently-enforceable rule. Used sparingly to satisfy
  per-Part completeness.

### Fork C — How deep do enforcement-point references go?

**Decision (AFK-precedent):** **File + named function/rule**, never line numbers. The lint validates to
the granularity that is *stable*:
- The **file path** must exist on disk (strong, cheap, rot-resistant).
- A `path::symbol` reference additionally requires `def symbol` to be present in the file (so a renamed
  or deleted test/function fails the lint — this is the core anti-rot guarantee).
- Parenthetical rule hints (`F2e`, `rule 6`, `check_finding`) are human aids, not machine-validated.

Skills are referenced by name and, where they live in-repo, by path (`.claude/skills/run-cycle/SKILL.md`).
Skill paths that resolve are validated; a bare `skill: name` with no path is allowed (some skills are
user-level, outside the repo).

## 4. The lint — `tests/test_compliance_matrix.py`

A pure-stdlib pytest module (no product imports), resolving the repo root the way the repo's other
doc-linters do: `pathlib.Path(__file__).resolve().parents[1]`. It parses two tables out of
`docs/compliance-matrix.md` — the **matrix** and the **summary** — and asserts:

1. **Matrix present & well-formed.** The 6-column header is found by exact match; there is a separator
   row; there is at least one data row; every data row has exactly 6 cells.
2. **Clause IDs.** Each matches `^P\d+(\.[\w-]+)?$`, is unique, and its numeric prefix equals the `Part`
   cell; `Part` ∈ 1..39.
3. **Status vocabulary.** Every `Status` cell is one of the six controlled words.
4. **No line numbers.** No cell contains a `\.py:\d+` token.
5. **Per-Part completeness.** The lint parses the charter live (`^## Part (\d+)` over
   `docs/agent-swarm-charter.md`) and asserts **every** Part number found there appears in ≥1 matrix
   row. (A new charter Part forces a new row; the count is not hard-coded.)
6. **Code paths exist.** In `Enforcement` and `Pinning test`, every token matching a path regex
   (`[\w][\w./-]*\.(py|json|md|toml|cmd)`) resolves to an existing file under the repo root.
7. **Test functions exist.** Every `tests/….py::name` token: the file exists **and** contains `def name`.
   (Generalises to any `path::symbol`.)
8. **Summary integrity.** A `## Summary` section holds a strict `Status | Count` table; the lint asserts
   each listed count equals the actual tally of matrix rows with that status, all six statuses are
   listed, and the listed total equals the row count. This stops the headline numbers from rotting.

Each assertion is its own test function with a clear message, so a failure names exactly what rotted.
Determinism: no network, no product imports, no ordering assumptions — pure file parsing.

## 5. The matrix document — `docs/compliance-matrix.md`

Structure:
1. **Header note** — what this is, the honesty principle, the format contract (so a human editor keeps
   it parseable), and a pointer to this spec.
2. **`## Summary`** — the `Status | Count` table (machine-checked against the rows).
3. **`## Compliance matrix`** — the 6-column table, grouped by Part with `### Part N — <title>`
   sub-headings for readability (the lint reads rows regardless of sub-headings).
4. **`## Findings`** — prose, at the bottom: the clauses that are `NOT-ENFORCED` or notably `PARTIAL`
   (aspiration-only or thinner than the charter implies), and any "enforced but unpinned" rows. This is
   the honest payoff. **No new backlog items** — findings are surfaced for the user to triage.

## 6. Workflow & guardrails

- Skills, in order: brainstorming (this spec) → writing-plans → TDD (lint test first, red, then the
  matrix makes it green) → verification-before-completion.
- TDD nuance: the *test* is the executable artifact; the *matrix* is the "implementation" that satisfies
  it. Red state = lint written, matrix absent/stub. Green = matrix complete and self-consistent.
- Small commits; `git log --oneline -1` before every commit; push after the first commit and at the end.
- Suite baseline 1200 passed / 5 skipped must hold at every commit; `test_evals_baseline_pin.py` red =
  contamination → stop and report.
- Finish with the sentinel `.superpowers/handoffs/f23-compliance-DONE.md`. Stop before merge.

## 7. Open decisions for the user (merge review)

All are AFK-precedent; none block the build:
- **A1 — clause granularity.** Is thorough Parts 1–18 + honest per-Part 19–39 the right depth, or does
  the user want every later-Part mechanism broken out to full clause level now? (Chosen: the former —
  the matrix is a living floor.)
- **A2 — status vocabulary.** Six statuses incl. `PARTIAL` and `NARRATIVE`. The user may want these
  collapsed (e.g. drop `PARTIAL` into ENFORCED/NOT-ENFORCED) for a starker map.
- **A3 — summary-count integrity check.** Adds a maintenance cost (every row status change must update
  the summary). Kept because silent count-rot is precisely what F23 fights; the user may prefer to drop it.
