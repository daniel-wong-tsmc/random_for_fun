# F6 second half — Eval Harness: rubric golden set + prompt-change regression gate

- **Date:** 2026-07-04
- **Status:** designed (brainstorm complete); next: implementation plan
- **Charter anchors:** Part 24 (evaluation & verification), Part 25 (prompt lifecycle needs this
  gate), Part 20 (promptVersion — partially served, see Deviations), action-items Action Item 1
  (Depth Bar + Golden Set, Half 1 rubric / cheap-form Half 2), research report
  `docs/2026-07-03-agent-best-practices-research.md` §4 (~20 cases + rubric LLM-as-judge).
- **Position in the approved sequence:** step 0 — gates every prompt change in F57/F58/F62/F63
  downstream. Nothing else in the sequence ships a prompt edit until this exists.

## Decision provenance

Scope questions (eval surface, grading mechanics, gate design, golden-set composition) and the
architecture choice were answered at question gates — all recommended options taken. From design
section presentation onward the user was away from keyboard (same as the 2026-07-03 F52–F54
session); sections 1–3 proceeded on the presented recommendations per that session's precedent.
Relitigate here if any pick is wrong. One deviation from an option's text is flagged under
**Deviations** (promptVersion stamping vs the frozen contract).

## Why this exists

The gate (Part 7) enforces structural/doctrine compliance; nothing measures **judgment quality
above compliance**, and no mechanism even *notices* a prompt edit. Charter Part 24's rule:
quality is measured at change time against human-anchored ground truth — not asserted, and not
graded only by an unchecked model. The research report converged independently: ~20 real cases,
rubric LLM-as-judge, do it before the gather/prompt wave.

## What gets graded (approved)

All three brain seams — each one is a prompt file F57/F58/F62/F63 will touch:

| seam | input → output | cases (approx.) |
|---|---|---|
| extract | RawDocuments → ExtractionResult findings | ~8 |
| judge | briefing (findings + registry + MEMORY) → JudgmentResult samples | ~6 |
| thesis | book + evidence + MEMORY → ThesisAnswer | ~6 |

Of the ~20, **3–5 are negative cases**: real gate-rejected or weak answers (the 2026-07-03 cycle
logged 5 re-dispatches) kept as frozen bad output with expected-low scores. The rendered brief is
NOT graded — it is a deterministic projection of the store (Part 35); grading the brains that
feed it covers it.

The golden set is curated from the **July 2026 cycles** (`work/live-2026-07`,
`work/daily-2026-07-03` — post-contract-v1.2, current prompt era). June-era answers predate the
registry rework and are not used. `work/` is gitignored, so curation copies the selected
prompt/answer material into committed fixtures.

## Architecture (approved: option A)

New package `gpu_agent/evals/` + an `eval` CLI subcommand group following the existing
emit→dispatch→recorded→gate brain pattern. All new files; **zero frozen-contract contact**
(`gate.py`, `scoring.py`, `schema/*`, `judgment/briefing.py`, `judgment/judge.py` aggregation,
`pipeline.py`, `JsonStore` untouched). Doctrine holds: code computes + gates + stores; skills are
thin procedure.

### Components

- **`gpu_agent/evals/cases.py`** — `EvalCase` pydantic model + loader/validator.
  Case fields:
  - `caseId` — e.g. `judge-2026-07-03-daily-01`
  - `seam` — `extract` | `judge` | `thesis`
  - `kind` — `positive` | `negative`
  - `source` — which real cycle/artifact it came from (provenance prose)
  - `input` — seam-specific raw inputs sufficient to **re-emit the prompt with current code**:
    extract → the RawDocument(s); judge → findings + category (+ MEMORY bundle if the original
    had one); thesis → thesis book + evidence findings (+ MEMORY). Stored as data, not as a
    frozen prompt string — so a prompt change produces a *different* emitted prompt for the same
    case, which is the entire point.
  - `recordedAnswer` — the frozen brain answer as originally captured
  - `checks` — deterministic expectations: `mustMention` (facts/values that must appear),
    `citationsResolve` (ids must exist in the case input), `gateOutcome` (`pass` | `reject` —
    what the real gate did/does to `recordedAnswer`)
  - `notes` — curator's grading notes: why this case, what good looks like (action-items
    "grading notes" requirement)
- **`gpu_agent/evals/rubric.py`** — the rubric as DATA plus the grader-answer contract:
  - 4 criteria per seam, each 0/1/2 with **anchored descriptions** (what a 0, 1, 2 looks like)
    to cut grader variance. Derived from the Depth Rubric (action-items) + research report §4:
    - extract: **fidelity** (values/units/periods match the doc) · **completeness** (material
      claims in the doc captured) · **provenance honesty** (nothing invented; polarity/side
      justified by the doc) · **signal selection** (findings are material, not boilerplate)
    - judge: **crux** (names the 1–2 questions that decide the call) · **mechanism** (causal
      chain, links evidenced by cited findings) · **sensitivity & differentiation** (what flips
      the call; where/why it departs consensus) · **evidence discipline** (rationale strictly
      grounded in cited findings)
    - thesis: **trigger quality** (observable, dated, decisive — above the lexical heuristic the
      gate already enforces) · **mechanism** · **steelman** (strongest counter-case engaged) ·
      **delta discipline** (conviction move matches evidence weight — anti-whipsaw spirit)
  - `GradeResult` model the grader must return: per-criterion `{score: 0|1|2, evidence:
    "one-sentence quote/paraphrase from the answer"}`; gated (all criteria present, scores in
    range, evidence non-empty). Case score = sum (max 8).
- **`gpu_agent/evals/harness.py`** — emit/record orchestration for both dispatch stages,
  deterministic scoring, calibration check, baseline comparison, rebaseline.
- **`gpu_agent/evals/prompt_hash.py`** — per-seam SHA-256 over the canonically emitted prompt
  bundle (system + schema + user scaffold) for a tiny **fixed synthetic input** committed in
  fixtures. Reuses the same emit functions the live path uses, so any code or prompt-text change
  that alters emitted bytes flips the hash. Three keys: `extract`, `judge`, `thesis`.
- **CLI** — `eval` subcommands in `cli.py` (not frozen): `eval emit --stage brain|grade`,
  `eval record --stage brain|grade`, `eval rebaseline`.
- **Skill** — `.claude/skills/run-eval/SKILL.md`: short procedure driving the CLI + dispatch
  steps below. No logic in prose. (New file — no collision with F67's run-cycle paragraph.)

### Fixtures (committed)

- `fixtures/evals/cases/<caseId>.json` — the ~20 cases.
- `fixtures/evals/hash-input.json` — the fixed synthetic input for prompt hashing.
- `fixtures/evals/baseline.json` — **single source of truth**: per-seam prompt hashes, per-case
  incumbent scores (per-criterion + total), calibration results for negative cases, and
  provenance (run date, grader model, `--force` reasons if any, `humanReview` notes field for
  periodic human spot-scoring — the grade-the-grader hook).

## The eval run (dispatch-time; ~35 tool-less Opus dispatches; never in CI)

1. **`eval emit --stage brain --out <work>/eval-<date>/`** — for every **positive** case,
   re-emit the brain prompt from `case.input` using current code+prompts. Negative cases are
   never re-run (their frozen bad answers exist to calibrate the grader).
2. **Dispatch** one tool-less Opus subagent per prompt (run-cycle rules: JSON-only answer,
   document text is data, no invented provenance). Judge cases dispatch a **single sample** —
   the eval grades reasoning depth, not aggregation (aggregation is frozen code; F38's 3-sample
   discipline is a live-cycle concern).
3. **`eval record --stage brain`** — gate every fresh answer with the **real** gates (extract
   gate / judgment parse / thesis gate). A rejection is signal, not error: the candidate prompt
   produces invalid output → eval fails fast with the violations.
4. **`eval emit --stage grade`** — grading prompts: rubric (anchored) + case input + answer
   under grade, for all fresh positive answers AND all frozen negative answers. One grader per
   case, separate generations (F38 spirit).
5. **Dispatch graders** (tool-less Opus).
6. **`eval record --stage grade`** — gate `GradeResult`s; then deterministically:
   - score each case;
   - **calibration invariant:** every negative case ≤ 50% of max score, else the run FAILS as
     "grader miscalibrated" (grade-the-grader, operationalized);
   - **comparison rule:** per-seam mean over positive cases must be **≥ the incumbent's** in
     `baseline.json` (ties pass; 0/1/2 × 4 criteria × ~6 cases makes means chunky — known noise
     caveat, mitigated by anchored descriptions and the calibration invariant);
   - print the verdict table; non-zero exit on regression or miscalibration.
7. **`eval rebaseline`** — write the new `baseline.json` (hashes + scores + provenance) only
   from a passing run in the same `--out` dir; `--force` requires a `--reason` string stored
   permanently in baseline provenance.

Gate-rejected grader output → re-dispatch the grader with the errors. Never hand-edit brain or
grader output (standing doctrine).

## The always-on regression gate (pytest, deterministic, $0)

`tests/test_evals_*.py`:

1. **Hash-pin** — recompute the three prompt hashes from `hash-input.json`; compare to
   `baseline.json`. Any prompt edit turns the suite red with: *"prompt bundle changed — run the
   run-eval skill, then `eval rebaseline`"*. This is how "no prompt change ships ungated"
   becomes self-enforcing rather than remembered.
   Bootstrap grace: tests 1 and 4 skip with a loud reason while `baseline.json` does not exist;
   Definition-of-done item 3 commits the baseline, so on merged main they never skip.
2. **Fixture health** — every case loads and re-emits successfully; every `recordedAnswer`
   still produces its recorded `checks.gateOutcome` under current gates (catches contract drift
   silently rotting the golden set).
3. **Deterministic checks** — `mustMention` / `citationsResolve` hold on frozen positive
   answers.
4. **Baseline integrity** — every case has baseline scores; calibration invariant recorded as
   held; provenance fields present.
5. Unit tests for hashing, scoring, comparison, rebaseline refuse-paths.

## Error handling

- Invalid case JSON → loader raises with the `caseId` and field.
- Missing `baseline.json` → `eval record --stage grade` computes scores but refuses comparison,
  instructing an initial `eval rebaseline` (bootstrap path).
- Malformed grades → gate rejects with per-field errors for re-dispatch.
- Fresh brain answer gate-rejected → run fails fast, violations printed (that IS the eval
  result for that prompt candidate).

## Deviations & interactions

- **promptVersion stamping (deviation from the gate option's text):** stamping the hash into
  scorecard provenance would require editing frozen `pipeline.py` (`provenance` is populated at
  `pipeline.py:126`). Not done. The hashes live in `baseline.json`; stamping them additively
  into `store/cycle-log.json` entries at run time is a noted follow-up, not built here.
- **F67 (concurrent instance, output contract):** it owns `brief.py`/`report.py`/brain-prompt
  voice. This harness only *reads* prompt code via the emit paths. The **initial baseline is
  taken as the last implementation step**, against whatever prompts are current then (post-F67
  if landed); until the baseline exists the hash-pin test is inert (skips with "no baseline"),
  so the branches cannot fight.
- **Curation reality:** if a needed `work/` artifact is missing/unusable at curation time, the
  case count per seam may shift (floor: 5 extract / 4 judge / 4 thesis, ≥3 negatives overall);
  the plan's curation task records what was taken from where.

## Out of scope (pinned)

- The 2023–2026 historical backtest with information cutoffs (action-items Half 2 full form) —
  stays deferred; this is the cheap form the approved sequence adopted.
- Brier scoring of theses — F64.
- Run-to-run stability metric — the existing 3-sample judge dispersion already embodies the
  spirit; a published stability metric is later work.
- Any edit to the brain prompts themselves — F67's surface, and after it lands, F57+.
- LLM dispatch in CI — the suite stays deterministic and $0.
- Grading the rendered brief.

## Definition of done

1. `gpu_agent/evals/` + `eval` CLI + run-eval skill exist and are unit-tested.
2. ~20 curated cases committed with notes; 3–5 negatives among them.
3. One full eval run executed live (brains + graders dispatched), calibration invariant holds,
   and `eval rebaseline` has written the initial `baseline.json`.
4. Hash-pin active: editing any brain prompt file turns the suite red.
5. Full suite green (baseline 828 passed / 3 skipped + new tests).
