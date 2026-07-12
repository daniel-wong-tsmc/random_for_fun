# F83 Conformance Pin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task (write test → prove RED via mutation → GREEN). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic conformance suite that drives the $0 recorded cycle path end-to-end and pins the machine-checkable prescriptions of `run-cycle/SKILL.md`, so a drifted skill edit or a skipped prescribed step fails loud instead of silently degrading unattended cycles.

**Architecture:** One new pytest file, `tests/test_run_cycle_conformance.py`, that (a) calls the real CLI (`gpu_agent.cli.main`) over committed `fixtures/recorded/*` into a `tmp_path` store and asserts exit codes / stderr contract / written-file discipline; (b) authors a finalized cycle-log journal the way `run-cycle` Step 6 prescribes and asserts its shape via the existing `gpu_agent.cycle` models and the F74 `_is_bare_plan` helper (no hand-copied key lists); (c) introspects the `pipeline` argparse to pin the F75 no-whole-run-bypass rule; (d) fingerprints the SKILL's Procedure step-list against a test constant and a one-line fingerprint comment in `SKILL.md` (the compliance-matrix rot-lint pattern). No product code, prompts, store, or frozen core are touched.

**Tech Stack:** Python, pytest, stdlib `hashlib`/`re`/`json`/`pathlib`, the repo's `gpu_agent` package (CLI + `cycle` models), committed recorded fixtures.

## Global Constraints

- Touch NOTHING but: the new test file `tests/test_run_cycle_conformance.py`, ONE fingerprint-comment line in `.claude/skills/run-cycle/SKILL.md`, and this plan doc. No product code, prompts, `store/`, or frozen core.
- Never hand-author brain answers — reuse only committed recorded artifacts (`fixtures/recorded/extract-nvda.json`, `fixtures/recorded/judge-nvda.json`) and committed config (taxonomy, the two `asg.*` files). If a needed shape has no committed fixture, that step is a documented residual — do not fabricate it.
- Suite green at every commit (fresh baseline: 1345 passed, 6 skipped). F6 pin (`tests/test_evals_baseline_pin.py`) untouched and green.
- Cardinal rule: if a conformance assertion FAILS against current behavior, that is a FINDING to report via QUESTION-STOP — never "fix" product code in this lane.
- Python from worktree root: `../../.venv/Scripts/python`. LF canonical. `git log --oneline -1` before every commit. Trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- The SKILL.md fingerprint line is the collision surface with the concurrent F88 instance — add it as the LAST commit and re-check the file is clean immediately before.

## Empirical baseline (verified against today's main before planning)

- `pipeline --recorded-extract fixtures/recorded/extract-nvda.json --recorded-judge fixtures/recorded/judge-nvda.json --docs fixtures/raw --assignment fixtures/asg.chips.merchant-gpu.json --as-of 2026-06 --captured-at 2026-06-12T00:00:00Z --out <tmp>` → exit 0, writes exactly `<tmp>/chips.merchant-gpu/2026-06-v1.json` (DMI=0.067 SMI=0.000), empty stderr.
- `pipeline --no-sufficiency ...` → exit 2 `unrecognized arguments: --no-sufficiency` (F75 whole-run bypass removed).
- `extract --recorded <3-answer file> --docs <1 doc>` → exit 2 `recorded answers (3) != documents (1)` (loud, no silent partial).
- `cycle-plan --scope all` → exit 0, emits one `SKIPPED <id>: skipped-no-assignment` stderr line per unassigned category (32 today; assert against the taxonomy-derived count, not a magic number).
- `cycle-plan --scope category:chips.merchant-gpu --out <finalized journal>` → exit 1, refuses to overwrite (F74).
- Clean recorded fixtures emit NO `DROPPED`/`UNREGISTERED-ENTITY` line — forcing those requires a malformed brain answer (residual, see Task 6).

## Residual (unpinnable by a recorded replay — written into the test docstring AND the sentinel)

1. **Live gather quality** (3a) — real-web document selection, recency, provenance tiering: no recorded surrogate.
2. **Brain reasoning + re-dispatch** (3b/3c/3e) — extraction/judgment/thesis are session-dispatched Opus judgment; the pin replays FROZEN recorded answers, so it pins the gate/score plumbing, never the reasoning quality or the voice-lint/sufficiency re-dispatch loop.
3. **Thesis gate live execution** (3e) — no committed `thesis-answer` fixture exists; hand-authoring one is a forbidden brain answer. Thesis is pinned only as a PRESENCE+ORDER step in the prescription and a recorded journal outcome, not driven live.
4. **`DROPPED` / `UNREGISTERED-ENTITY` live emission** — clean fixtures do not trip them; producing them needs a malformed/out-of-taxonomy brain answer (forbidden). The stderr FORMAT is pinned indirectly (the no-silent contract is proven via the `SKIPPED` and length-mismatch paths); live emission is residual.
5. **Commit / push etiquette, cost-confirmation gate (Step 2), report prose surfacing (F67)** — session-judgment and interactive, not drivable by a $0 replay.

---

## File Structure

- `tests/test_run_cycle_conformance.py` (create) — the whole conformance suite. Stdlib + `gpu_agent` imports only; no network, no LLM. One module, grouped by the spec's five assertion families plus the sync guard.
- `.claude/skills/run-cycle/SKILL.md` (modify, ONE line) — the fingerprint comment, added in the final task.

Helpers reused (imported, not re-implemented):
- `gpu_agent.cli.main` — the CLI entrypoint (returns int exit code).
- `gpu_agent.cli._is_bare_plan`, `gpu_agent.cli._PLAN_ENTRY_KEYS` — F74 model-derived plan-skeleton logic.
- `gpu_agent.cycle.CyclePlan`, `gpu_agent.cycle.CycleEntry` — journal/plan models.
- `gpu_agent.taxonomy.Taxonomy` — to derive the expected `SKIPPED` count from committed config, not a magic number.

Module-level constants in the test:
- `RECORDED_EXTRACT = "fixtures/recorded/extract-nvda.json"`, `RECORDED_JUDGE = "fixtures/recorded/judge-nvda.json"`, `DOCS = "fixtures/raw"`, `ASSIGNMENT = "fixtures/asg.chips.merchant-gpu.json"`, `AS_OF = "2026-06"`, `CAPTURED_AT = "2026-06-12T00:00:00Z"`, `CATEGORY = "chips.merchant-gpu"`.
- `SKILL = ROOT/".claude/skills/run-cycle/SKILL.md"`.
- `EXPECTED_STEPS` — the canonical ordered step list parsed from the Procedure section (the pinned checklist).
- `STEP_FINGERPRINT_RE` — matches the SKILL.md fingerprint comment.

---

## Task 1: Recorded path runs end-to-end + write discipline

**Files:**
- Create/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Consumes: `gpu_agent.cli.main(argv: list[str]) -> int`.
- Produces: `_run_recorded_pipeline(tmp_path) -> pathlib.Path` helper returning the written scorecard path (used by Task 2).

- [ ] **Step 1: Write the failing test** — `test_recorded_pipeline_writes_only_the_scorecard_carveout`: run `main([...pipeline recorded args... , "--out", str(store)])`; assert rc == 0; assert exactly one file under `store/` and it is `store/chips.merchant-gpu/2026-06-v1.json`; assert no file was written outside `store` (snapshot cwd tree before/after — no stray files, no `cycle-log.json`).
- [ ] **Step 2: Run to verify FAIL** — `pytest tests/test_run_cycle_conformance.py::test_recorded_pipeline_writes_only_the_scorecard_carveout -v`. Expected: FAIL first (assertion not yet met / helper absent), then implement helper.
- [ ] **Step 3: Minimal implementation** — write module header/docstring (with the residual list), constants, `_run_recorded_pipeline`, and the test body.
- [ ] **Step 4: Verify PASS**.
- [ ] **Step 5: Mutation-verify (record in notes)** — temporarily change the expected path to a wrong version (`v2`) → confirm RED; temporarily assert an extra bogus file → confirm RED; revert. This proves the write-discipline assertion bites.
- [ ] **Step 6: Commit** (`test(f83): recorded pipeline write-discipline conformance`).

## Task 2: Journal shape via the existing models (F74 no-bare-ready + required header)

**Files:**
- Modify/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Consumes: `_run_recorded_pipeline` (Task 1); `gpu_agent.cli._is_bare_plan`, `_PLAN_ENTRY_KEYS`; `gpu_agent.cycle.CyclePlan/CycleEntry`.
- Produces: `_finalized_journal(scorecard_path) -> dict` helper (authors a Step-6-shaped journal) reused by Task 3.

- [ ] **Step 1: Write the failing test** — `test_finalized_journal_shape`: build a plan via `CyclePlan`, run the recorded pipeline, author a finalized journal dict (header `asOf`/`mode`/`capturedAt`, entry enriched with `scorecard`/`dmi`/`smi`/`gates`/`stageStatus`, entry `status` promoted from `ready` to `done`); assert `journal["asOf"]` truthy (the F74 tripwire's required-header rule); for the ready-or-done entry assert `not _is_bare_plan_entry` i.e. `set(entry) - _PLAN_ENTRY_KEYS` is non-empty (reuse the model-derived key set, no hand-copied list); assert the `gates` block carries `extract`, `sufficiency`, `voiceLint`, `thesis` keys and `mode`/`capturedAt` present.
- [ ] **Step 2: Run to verify FAIL**.
- [ ] **Step 3: Minimal implementation** — add `_finalized_journal` + assertions.
- [ ] **Step 4: Verify PASS**.
- [ ] **Step 5: Mutation-verify** — drop `asOf` from the header → RED; leave the entry bare (only plan keys) → RED (`set(entry) - _PLAN_ENTRY_KEYS` empty); drop a `gates` sub-key → RED; revert.
- [ ] **Step 6: Commit** (`test(f83): finalized-journal shape via cycle models + F74 rule`).

## Task 3: Gate order + presence + no whole-run bypass (F75)

**Files:**
- Modify/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Consumes: `gpu_agent.cli.build_parser`/argparse introspection (via running `main` with a bad flag), `EXPECTED_STEPS` (Task 5), `_finalized_journal` (Task 2).

- [ ] **Step 1: Write the failing tests** —
  `test_pipeline_has_no_whole_run_sufficiency_bypass`: `main(["pipeline","--no-sufficiency", ...required args...])` raises `SystemExit(2)` (argparse `unrecognized arguments`); assert the exit code is 2. (Wrap in `pytest.raises(SystemExit)` and assert `.code == 2`.)
  `test_gate_order_in_prescription`: from the parsed step list (Task 5 parser), assert index(extraction) < index(judgment) < index(thesis) < index(report).
  `test_journal_records_each_gate_outcome`: the `_finalized_journal` gates block records extract → sufficiency/voiceLint → thesis, each with a non-empty value.
- [ ] **Step 2: Run to verify FAIL**.
- [ ] **Step 3: Minimal implementation**.
- [ ] **Step 4: Verify PASS**.
- [ ] **Step 5: Mutation-verify** — temporarily expect `--no-sufficiency` to be ACCEPTED → RED (documents the F75 pin bites); reorder the gate-order expectation → RED; revert.
- [ ] **Step 6: Commit** (`test(f83): gate order/presence + F75 no-bypass conformance`).

## Task 4: Nothing silent (SKIPPED contract + loud length-mismatch)

**Files:**
- Modify/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Consumes: `gpu_agent.cli.main`, `gpu_agent.taxonomy.Taxonomy`, `capsys` (pytest stderr capture).

- [ ] **Step 1: Write the failing tests** —
  `test_cycle_plan_surfaces_every_unassigned_category`: run `main(["cycle-plan","--scope","all"])`, capture stderr via `capsys`; count `SKIPPED ` lines; derive expected = number of taxonomy categories with no `fixtures/asg.<id>.json`; assert equal and > 0 (no category vanishes silently).
  `test_recorded_answer_count_mismatch_fails_loud`: run `extract --recorded fixtures/recorded/judge-nvda.json --docs fixtures/raw --as-of 2026-06`; assert rc == 2 and stderr contains `recorded answers (3) != documents (1)`.
- [ ] **Step 2: Run to verify FAIL**.
- [ ] **Step 3: Minimal implementation**.
- [ ] **Step 4: Verify PASS**.
- [ ] **Step 5: Mutation-verify** — temporarily expect one FEWER `SKIPPED` line (simulating a silenced skip) → RED; temporarily expect rc 0 on the mismatch → RED; revert.
- [ ] **Step 6: Commit** (`test(f83): nothing-silent (SKIPPED + loud count-mismatch)`).

## Task 5: SKILL.md step-list constant + gate-order parser

**Files:**
- Modify/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Produces: `_parse_procedure_steps(text) -> tuple[tuple[str,str],...]` (ordered `(step_id, title_head)` pairs from `## Procedure`..`## Daily mode`); `EXPECTED_STEPS` constant.

- [ ] **Step 1: Write the failing test** — `test_procedure_step_list_matches_pinned_constant`: parse SKILL.md's Procedure section into ordered `(step_id, title_head)` pairs (numbered `### N.` steps and `**(label) Title**` sub-steps; title_head = heading text up to the first ` — `/`.`/`(`, normalized, lowercased); assert `== EXPECTED_STEPS`. Fill `EXPECTED_STEPS` with the ACTUAL parsed value (this is the pin — a later SKILL edit that reorders/renames a step breaks it).
- [ ] **Step 2: Run to verify FAIL** (before `EXPECTED_STEPS` is filled / parser exists).
- [ ] **Step 3: Minimal implementation** — parser + constant.
- [ ] **Step 4: Verify PASS**.
- [ ] **Step 5: Mutation-verify** — temporarily append a fake step to `EXPECTED_STEPS` → RED; revert.
- [ ] **Step 6: Commit** (`test(f83): pin run-cycle Procedure step list`).

## Task 6: Fingerprint desync guard (the ONE SKILL.md line — LAST)

**Files:**
- Modify: `.claude/skills/run-cycle/SKILL.md` (ONE fingerprint-comment line)
- Modify/Test: `tests/test_run_cycle_conformance.py`

**Interfaces:**
- Consumes: `_parse_procedure_steps`, `EXPECTED_STEPS`, `hashlib`.

- [ ] **Step 1: Write the failing test** — `test_skill_fingerprint_in_sync`: compute `fp = hashlib.sha256(repr(EXPECTED_STEPS).encode()).hexdigest()`; read the SKILL.md fingerprint comment via `STEP_FINGERPRINT_RE`; assert the comment exists and its digest == `fp`. (This is RED until the comment line is added.)
- [ ] **Step 2: Run to verify FAIL** — comment absent → RED.
- [ ] **Step 3: Concurrent-edit guard** — `git -C <worktree> status --porcelain .claude/skills/run-cycle/SKILL.md` must be clean (no other instance mid-edit); `git log --oneline -1`; read the current Procedure header region to confirm it is unchanged since baseline.
- [ ] **Step 4: Add the ONE line** — insert directly under the `## Procedure` header:
  `<!-- run-cycle-step-fingerprint: sha256=<fp> — F83 conformance pin; regenerate via tests/test_run_cycle_conformance.py if the step list legitimately changes -->`
- [ ] **Step 5: Verify PASS + full suite** — `pytest tests/test_run_cycle_conformance.py -v` green; full suite green (1345+N passed).
- [ ] **Step 6: Mutation-verify** — temporarily corrupt the comment digest → RED; temporarily reorder a real SKILL step (in a scratch copy, or edit+revert) → parser output changes → `EXPECTED_STEPS` mismatch (Task 5) AND fingerprint mismatch → RED; revert.
- [ ] **Step 7: Commit** (`test(f83): SKILL.md step-list fingerprint desync guard`) — re-run `git log --oneline -1` and confirm SKILL.md clean immediately before.

## Final: verification-before-completion + sentinel

- [ ] Run the full suite once more; record exact pass/skip counts.
- [ ] Write `.superpowers/handoffs/f83-conformance-DONE.md` (date, commits, suite counts, mutation-verification evidence, residual list, merge notes: STOP before merge, park on branch).
- [ ] `git push -u origin f83-conformance-pin` (branch only; never main).

## Self-Review (spec coverage)

- Spec #1 journal shape → Task 2. Spec #2 gate order/presence/no-bypass → Task 3 (+ order via Task 5). Spec #3 nothing silent → Task 4. Spec #4 write discipline → Task 1 (+ F74 clobber refusal folded into Task 1 or 2) + Task 2 no-skeleton. Spec #5 sync guard → Tasks 5+6. Acceptance #1 recorded run passes on main → Task 1. Acceptance #2 mutation red-green → every task's Step 5. Acceptance #3 fingerprint desync fails loud → Task 6. Acceptance #4 residual written → module docstring + sentinel.
- Note: fold the F74 `cycle-plan --out <finalized>` clobber-refusal assertion into Task 1 as a second test (`test_cycle_plan_refuses_to_clobber_finalized_journal`) — it is write-discipline and needs the same fixtures.
