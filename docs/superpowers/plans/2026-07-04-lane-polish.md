# Lane γ — Render/Prompt Polish (F68 a–f + F56 minor-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Execute tasks IN ORDER, strict TDD, commit per task.

**Goal:** Clear the F68 follow-up bundle from the F67 review — full-evidence citation map (b), a correctly-keyed BLUF reconciliation note (c), a de-duplicated what-moved empty state (d), collision-safe id-label substitution (e), a thesis-prose lint symmetrical to the judgment one (a), and the acronym allowlist gap (f) — plus F56's `thesis.py` comment minor.

**Architecture:** All render/validation surface, all additive. Every change is in a renderer (`report.py`, `brief.py`), the reader utility (`reader.py`), the acronym data (`registry/acronyms.json`), or a NEW post-hoc lint in `thesis.py` that reuses `reader.lint_prose`. **No emitted brain prompt changes** (do not touch `thesis.py`'s `_finding_lines` / `build_*` prompt text, `judgment/prompt.py`, or `extraction/prompt.py`) — so `fixtures/evals/baseline.json` is untouched.

**Tech Stack:** Python 3.11, pydantic v2, pytest; JSON data.

## Global Constraints
- Branch `fix/lane-polish`, own worktree `.worktrees/lane-polish`, run from its root. Tests: `/c/Users/danie/random_for_fun/.venv/Scripts/python -m pytest -q` (baseline **927 / 3**). Full suite green after every task.
- **You own (no other lane touches):** `gpu_agent/report.py`, `gpu_agent/brief.py`, `gpu_agent/reader.py`, `gpu_agent/thesis.py` (the NEW prose lint + the F56 comment ONLY — never `_finding_lines` or prompt text), `registry/acronyms.json`, and tests `tests/test_report*.py`, `tests/test_brief*.py`, `tests/test_reader*.py`, `tests/test_thesis*.py` (additive), new `tests/test_lane_polish.py`.
- **NEVER edit (frozen core / brain prompts / other lanes' files):** `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`, `extraction/*`, `gathering/*`, `wiki/*`, `manifest.py`, `cli.py`, `.claude/skills/*`, `manifests/*`, `evals/*`, any `fixtures/`. In `thesis.py`: **only** add the new lint function + fix the F56 comment; do not alter `_finding_lines`, `build_thesis_*`, or any gate math.
- **Eval gate:** no task changes an emitted prompt → `tests/test_evals_baseline_pin.py` stays green. If it goes red, you edited prompt text — stop and re-scope.
- **Rebase note:** Lane γ and F62 both edit `thesis.py` (F62 changed `_finding_lines` for the `observed=` tag). On rebase onto post-F62 `main`, keep F62's `_finding_lines` and land the γ lint/comment changes around it — they touch different functions, so the conflict is mechanical.
- Commit trailer: `Co-Authored-By:` naming the ACTUAL implementer model (sonnet fits these mechanical fixes per the repo model policy).
- Windows: use bash for `>` redirects; no double quotes inside `git commit -m` under PowerShell (bash heredocs).

---

### Task 1: F68b — citation map renders ALL evidence items
**Files:** `gpu_agent/report.py:689-704` (`render_citation_map`); test `tests/test_lane_polish.py`.

**Why:** `render_citation_map` emits one line per finding using `ev = f.evidence[0]`, so a finding corroborated by 3 publishers shows only its first source — the appendix map is the one place ids trace to sources, so it should show all.

- [ ] **Step 1 (failing test):** build a `Scorecard` with one finding carrying two `Evidence` items (distinct source/date/tier), call `render_citation_map(sc)`, assert BOTH sources appear (two lines under that id, or the id + both sources). Reuse the scorecard/finding factory from existing `tests/test_report*.py`.
- [ ] **Step 2:** Run it — FAIL (only the first evidence line renders).
- [ ] **Step 3:** Replace lines 700-703's single-evidence emit with a loop over `f.evidence` (still `if not f.evidence: continue`), emitting one `  {f.id}  {ev.tier}  {ev.date}  {ev.source[:60]}` line per evidence item, preserving the outer sort by `f.id`:
```python
    for f in sorted(sc.findings, key=lambda f: f.id):
        for ev in f.evidence:
            lines.append(f"  {f.id}  {ev.tier}  {ev.date}  {ev.source[:60]}")
```
- [ ] **Step 4:** Re-run — PASS. Full suite — green (a single-evidence finding is byte-identical; only multi-evidence findings gain lines — update any existing citation-map assertion that pinned the old first-only shape).
- [ ] **Step 5:** Commit: `fix(F68b): citation map renders every evidence item, not just the first`.

---

### Task 2: F68c — BLUF reconciliation note keys off sdgiDirection
**Files:** `gpu_agent/brief.py:49-52`; test `tests/test_lane_polish.py`.

**Why:** The "supply is the constraint, not a demand problem" note fires on `ds.smiContribution < 0`, a raw-sign proxy; the scorecard already computes the supply-gap direction as `sdgiDirection` — key off that so the note matches the demand/supply-gap semantics the rest of the brief uses.

- [ ] **Step 1 (failing test):** render `render_state_of_market` (or whichever function contains brief.py:41-52 — confirm the enclosing name) for a `Strong`-rated scorecard whose `demandSupply.sdgiDirection == "supply-led"` and assert the note renders; and one with `sdgiDirection == "balanced"` (but `smiContribution` slightly negative) and assert it does NOT. Reuse the brief factory from existing `tests/test_brief*.py`.
- [ ] **Step 2:** Run it — FAIL (current code fires on `smiContribution < 0`, so the balanced-but-negative case wrongly renders the note).
- [ ] **Step 3:** Change the condition at brief.py:49-50 from `and ds.smiContribution < 0` to `and ds.sdgiDirection == "supply-led"` (the `_sdgi_direction` value meaning supply is the binding gap; the other values are `"demand-led"` / `"balanced"`).
- [ ] **Step 4:** Re-run — PASS. Full suite — green.
- [ ] **Step 5:** Commit: `fix(F68c): BLUF supply-constraint note keys off sdgiDirection, not raw smiContribution sign`.

---

### Task 3: F68d — de-duplicate the what-moved folded-count line
**Files:** `gpu_agent/brief.py:224-238` (`render_what_moved`); test `tests/test_lane_polish.py`.

**Why:** When there are no material moves AND `foldedCount > 0`, both the empty-state branch ("N below-threshold items folded") and the always-on tail ("N lower-materiality items folded — see wiki-lint") render, stating the folded count twice.

- [ ] **Step 1 (failing test):** build a `movement` with `moved == []`, `prevAsOf` set, `foldedCount == 3`; call `render_what_moved(movement)`; assert the substring `folded` appears **exactly once**. Reuse the movement factory from existing `tests/test_brief*.py`.
- [ ] **Step 2:** Run it — FAIL (folded count appears twice).
- [ ] **Step 3:** Guard the tail block (brief.py:237, `if movement.foldedCount:`) so it only fires when there WERE moves — change to `if movement.moved and movement.foldedCount:`. The no-moves branch (brief.py:227-229) keeps owning the folded message in the empty state.
- [ ] **Step 4:** Re-run — PASS. Also assert the moves-present case still shows the tail once (add that assertion). Full suite — green.
- [ ] **Step 5:** Commit: `fix(F68d): what-moved empty state states the folded count once, not twice`.

---

### Task 4: F68e — collision-safe id→label substitution
**Files:** `gpu_agent/reader.py` (`label_ids_in_text`); test `tests/test_lane_polish.py`.

**Why:** `label_ids_in_text` substitutes indicator ids → labels iteratively; if a future registry label contains another id as a token, iterative replacement can chain (re-substitute inside an already-inserted label). No collision today — harden it before one lands.

- [ ] **Step 1:** Read `label_ids_in_text` in `reader.py` to confirm its current substitution loop and signature.
- [ ] **Step 2 (failing test):** construct a registry (or minimal stub matching its lookup) where label of id `A` contains the literal token of id `B`; call `label_ids_in_text("… A … B …", registry)`; assert `A`→label(A) and `B`→label(B) each happen once and label(A)'s embedded `B`-token is NOT re-substituted. (If the current loop is already single-pass, write the test that would fail under a naive iterative version and add a `reader.py` comment pinning the single-pass guarantee instead of a code change — state which in the task report.)
- [ ] **Step 3:** Run it — FAIL under iterative substitution.
- [ ] **Step 4:** Make substitution single-pass: match all id tokens against a compiled alternation of ids (longest-first to avoid prefix shadowing) in ONE `re.sub` pass with a replacement function that looks up each matched id's label, so inserted label text is never re-scanned.
- [ ] **Step 5:** Re-run — PASS. Full suite — green (existing no-collision inputs stay byte-identical — pin one existing "breaks if" render as unchanged).
- [ ] **Step 6:** Commit: `fix(F68e): label_ids_in_text substitutes in one pass - no chaining if a label embeds another id`.

---

### Task 5: F68a — thesis-prose lint (symmetrical to the judgment lint) + F56 comment minor
**Files:** `gpu_agent/thesis.py` (NEW lint fn + fix one comment); test `tests/test_lane_polish.py`.

**Why:** The judgment path enforces analyst voice via `reader.lint_prose` (statement/mechanism sentence caps, ids-only-where-allowed, banned words); the thesis spec §2b shipped its equivalent as prompt rules only. Add the deterministic lint so thesis prose is held to the same bar. F56 minor-1: a `_gate_depth_fields`-area comment overclaims "mirrors gate rule 3" (rule 3 doesn't check the statement) — correct it (comment only).

- [ ] **Step 1 (failing test):** for a judged thesis whose `statement` is two sentences (or carries a finding id outside `falsifiableTrigger`), assert a new `lint_thesis_prose(...)` returns a non-empty violation list naming the field; for clean prose it returns `[]`. Model the call and return shape on `reader.lint_prose(text, field, *, max_sentences)` (returns `list[str]`). Reuse the thesis factory from existing `tests/test_thesis*.py`.
- [ ] **Step 2:** Run it — FAIL (`lint_thesis_prose` undefined).
- [ ] **Step 3:** Add `lint_thesis_prose` to `thesis.py`: call `reader.lint_prose(statement, "statement", max_sentences=1)` and `reader.lint_prose(mechanism, "mechanism", max_sentences=1)`, and flag any finding id token appearing outside `falsifiableTrigger`. Return the concatenated violations. **Do NOT modify `_finding_lines`, any `build_*` prompt text, or the gate math** — this is post-hoc validation only, mirroring the judgment lint. (Wire it into the thesis `--recorded` validation path only if that path already fails-loud on lint like the judge path; if wiring risks changing recorded-fixture behavior, land the function + its unit test now and note the wire-up as a follow-up — say which in the task report.)
- [ ] **Step 4:** F56 minor-1 — fix the comment near `thesis.py:366-371` (`_gate_depth_fields` docstring / the "rule 2/3" wording) that overclaims it "mirrors gate rule 3"; reword per the F56 backlog entry (rule 3 does not check the statement). Comment only — no behavior change.
- [ ] **Step 5:** Re-run — PASS. Full suite — green.
- [ ] **Step 6:** Commit: `feat(F68a): deterministic thesis-prose lint mirrors the judgment voice lint; fix(F56): correct the depth-fields gate-rule-3 comment`.

---

### Task 6: F68f — acronym allowlist gap
**Files:** `registry/acronyms.json`; test `tests/test_lane_polish.py` (or proofread).

**Why:** Live thesis-store prose carried off-allowlist tokens `MI` and `GB300`. `GB300` is ALREADY in the allowlist (acronyms.json:98), so only `MI` remains — a legitimate standalone token (AMD MI-series). Add it (or, if you judge it should be cleaned from prose on re-judge instead, record that decision and skip — do not do both).

- [ ] **Step 1:** Confirm `GB300` is present and `MI` is absent in `registry/acronyms.json`.
- [ ] **Step 2:** Add `"MI"` to the `allowed` array (keep the file's existing formatting/ordering convention).
- [ ] **Step 3 (pin):** load `registry/acronyms.json`, assert `"MI"` and `"GB300"` are both in `allowed`; or a `reader.lint_prose`-based test that a sentence containing `MI` no longer trips the off-list-acronym check. Full suite — green.
- [ ] **Step 4:** Commit: `fix(F68f): allowlist the MI acronym (GB300 already present)`.

---

## Self-review
- F68b→T1, F68c→T2, F68d→T3, F68e→T4, F68a→T5 (+F56 minor-1), F68f→T6. Every F68 sub-item and the routed F56 comment maps to a task.
- No task edits a frozen-core file, an emitted-prompt file/text, `cli.py`, a skill, or a Lane β file → eval pin green, domains disjoint. `thesis.py` touches are additive (new lint fn) + a comment — `_finding_lines`/prompt text untouched.
- Exact anchors: report.py:699-703, brief.py:49-50, brief.py:237, reader.label_ids_in_text, thesis.py:366-371, acronyms.json. sdgiDirection value pinned = `"supply-led"`.
