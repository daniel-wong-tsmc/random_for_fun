# F65 — "So what for TSMC": registry-driven implication brain + brief section

**Status:** approved design, ready for a lane plan.
**Decision provenance — user-approved 2026-07-13 (interactive, orchestrator session):**
(1) **dedicated one-author dispatch** (confirmed after an explicit pros/cons round on extending
the judge — rejected for: frozen-schema coupling to F79, role mixing, prose-can't-vote across
the judge's 3 samples, wider eval blast radius, and because the post-judgment dispatch sees
strictly MORE: the final gated scorecard + thesis book + the same evidence/memory bundle);
(2) **decision variables as registry DATA** — scalable to new issues by data edit (user's
explicit scalability requirement); (3) **renders as a section in the daily brief** below the
executive top band (amends exec-format decision E4 — user-approved). Unsettled forks =
QUESTION-STOP → `.superpowers/handoffs/f65-tsmc-QUESTIONS.md`, end turn, wait.

## Architecture

- **Registry `registry/implications.json`:** per-category decision-variable list. Seed
  (chips.merchant-gpu → TSMC): `waferStartsByNode`, `cowosSoicAllocation`, `n2CustomerMix`,
  `pricingLeverage`, `foundryCompetitiveEvents` — each `{id, label, description}`. Adding
  issue #6 later = a data edit (prompt-affecting → F6 gate, one change at a time, by design).
- **Prompt template (new module, e.g. `gpu_agent/implication.py`):** category-agnostic (F26
  pattern — zero merchant-gpu idioms in code); built from the registry + the FINAL gated
  scorecard + the judged thesis book + the F4 memory bundle. ONE author, no sampling (thesis
  precedent). Tool-less dispatch via the standard seam: `implication --emit-prompt` →
  `--recorded`.
- **Gate (deterministic, code):** every implication line cites the scorecard dimension(s) /
  thesis id(s) / finding id(s) it derives from (ids must exist); voice lint (F67 allowlist,
  exec-readable); length cap (≤ ~8 lines above-fold quality); **lane discipline hard rule:
  implications are watch-items and exposure statements, NEVER recommendations or actions**
  (charter Parts 10–11/21 — tailwind/headwind/risk is Layer's altitude; if a draft says
  "should", reject → re-dispatch). Gate rejection → re-dispatch with errors, never hand-edit.
- **Storage (new carve-out, no frozen schema):** `store/implications/<category>/<asOf>.json`
  (gitignore whitelist extended). The scorecard is untouched.
- **Renderer:** a short "FOR TSMC" section in `report.py`, below the top band, above the
  appendix — pure projection of the stored artifact, honest empty state ("no implication
  recorded this cycle").
- **run-cycle SKILL.md:** one added step (dispatch implication after thesis; commit artifact).
- **Eval:** new golden cases + rubric grader for the implication seam; ships through run-eval →
  rebaseline. **Serialization rule (orchestrator-enforced): F65's re-gate completes BEFORE
  F79's bundled re-gate begins.** Existing seams' prompts stay byte-identical (additive
  pattern; the F6 pin must stay green until this lane's own re-gate).

## Lane ownership / hard constraints

Owns: `registry/implications.json` (new), `gpu_agent/implication.py` (new), the `report.py`
section, `cli.py` verb (append-only — F79 also adds verbs; trivial rebase expected),
run-cycle prose step, tests, eval cases. Must NOT touch: `scoring.py`, `change.py`,
`registry/indicators.json`, `wiki/`, frozen core, `store/` data. Suite green at every commit
(baseline 1346/5).

## Acceptance (each pinned)

1. Registry-driven prompt: adding a variable to the registry changes the emitted prompt; code
   contains no hardcoded variable list.
2. Gate: an uncited line, an off-allowlist token, an over-length draft, and a
   recommendation-verb draft are each rejected loud.
3. One author: exactly one generation per cycle; re-dispatch path logged.
4. Renderer: section renders from a real stored artifact; honest empty state; appendix
   untouched above/below contract holds.
5. Category-agnostic: a second category's registry entry produces a well-formed prompt with
   zero code edits (paper test, F27 style).
6. Eval: implication golden cases graded; rebaseline via governance; full suite + pin green.

## Non-goals

Recommendations/actions (Layer/Main altitude); auto-feeding Main (later tier work); rendering
inside the top band; touching the judge.
