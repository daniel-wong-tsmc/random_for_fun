# Wave-2 Lane H — Generalization (F26 prompts, F27 frontier-closed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute tasks IN ORDER, strict TDD, commit per task.

**Goal:** The persona and category stop being hardcoded GPU-isms (F26's prompt half), and `models.frontier-closed` becomes actually runnable — real weights, a manifest, a scoring proof (F27). Second category = the generalization proof.

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints
- Branch `fix/lane-h`, own worktree, run from its root. Tests: `C:\Users\danie\random_for_fun\.venv\Scripts\python -m pytest -q` (baseline 516/3). Full suite green after every task.
- **You own:** `gpu_agent/extraction/prompt.py`, `gpu_agent/judgment/prompt.py`, `gpu_agent/judgment/judge.py` (persona pass-through param only), `gpu_agent/assignment.py` (ONE additive field), `fixtures/asg.models.frontier-closed.json`, new `manifests/models.frontier-closed.json`, `registry/indicators.json` DATA (only if a frontier indicator lacks something — expected: none), and tests `test_extraction_prompt.py`, `test_judgment_prompt.py`, `test_generalization.py`, new `test_w2_lane_h.py`.
- **NEVER edit:** `cli.py` (Lane G owns it; the persona threading through cli is a CONTROLLER step at merge — design for it, don't wire it), `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `extraction/extractor.py`, `gathering/*`, `wiki/*`, `brief.py`, `report.py`, `manifest.py`, `llm/*`, fixtures golden/recorded, `.claude/skills/*`.
- CRITICAL compatibility rule: module-level `SYSTEM` constants in both prompt files MUST keep existing byte-identical DEFAULT behavior (cli imports them; golden/recorded flows depend on them). Parameterization is ADDITIVE.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: F26 — parameterized personas, GPU as the default
**Files:** `gpu_agent/extraction/prompt.py`, `gpu_agent/judgment/prompt.py`, `gpu_agent/assignment.py`, `gpu_agent/judgment/judge.py`; tests `test_w2_lane_h.py` + existing prompt tests.
- `extraction/prompt.py`: introduce
```python
DEFAULT_PERSONA = "GPU market"
def build_system(persona: str = DEFAULT_PERSONA) -> str:
    return _SYSTEM_TEMPLATE.format(persona=persona)
SYSTEM = build_system()   # byte-identical to today's constant — pin with a test
```
  where `_SYSTEM_TEMPLATE` is today's SYSTEM text with `You extract demand/supply Findings from a source document for a {persona} analyst.` (ONLY that occurrence templated; escape any literal `{`/`}` in the text — there are JSON braces: use a safe replacement like `_SYSTEM_TEMPLATE.replace("<PERSONA>", persona)` with a `<PERSONA>` placeholder instead of str.format to avoid brace escaping entirely — implementer's choice, pin byte-identity).
- Same pattern in `judgment/prompt.py` (`You are a {persona} analyst assigning the six dimension ratings...`).
- `assignment.py`: additive optional field `personaLabel: str | None = None` on `Assignment` (loader unchanged; old fixtures still validate).
- `judgment/judge.py`: `judge_findings(..., persona: str | None = None)` — when set, `prompt.SYSTEM` is replaced by `build_system(persona)` for the samples (additive param, default preserves behavior).
- Pin: `SYSTEM == build_system()` byte-identical in BOTH files (guard against accidental drift); `build_system("frontier AI model market")` contains that persona and no "GPU"; old assignment fixtures load with `personaLabel is None`; `judge_findings` default path byte-identical prompt.
- Commit: `fix(F26): extraction/judgment personas parameterized by assignment - GPU is a default, not a hardcode`.

### Task 2: F27 — make models.frontier-closed runnable
**Files:** `fixtures/asg.models.frontier-closed.json`, new `manifests/models.frontier-closed.json`; tests `test_w2_lane_h.py` + `test_generalization.py` extensions.
- Assignment: fill real `weights` (`apiArr: 0.2`, `releaseCadence: 0.1`, `market-share-pct: 0.1`, `grossMargin: 0.1`), set `personaLabel: "frontier AI model market"`, add `manifestRef: "manifests/models.frontier-closed.json"`, `asOf` stays as-is.
- Manifest (follow `manifests/chips.merchant-gpu.json`'s shape EXACTLY — read it first): categoryId `models.frontier-closed`; expectedIndicators: apiArr (momentum, required), releaseCadence (competitiveStructure, preferred), market-share-pct (moat, preferred), grossMargin (unitEconomics, optional); expectedSources (all free-web/filings, no invented paywalls): openai.com/blog + anthropic.com/news (vendor PR, secondary), SEC filings of MSFT/GOOGL as proxies (filing, primary, sec.gov), theinformation.com marked `licensed-api` costUsd 399 (paywalled, never fetched — with a paywalledNote), plus an open-web analyst-notes source (secondary).
- Prove runnability in tests (NO live calls, NO recorded brain fixtures — direct library calls):
  1. `load_manifest("manifests/models.frontier-closed.json")` validates; every `indicatorId` resolves in the registry AND is cadenceHorizon-tagged.
  2. `validate_assignment(load_assignment("fixtures/asg.models.frontier-closed.json"), registry, taxonomy)` returns [].
  3. `build_cycle_plan("category:models.frontier-closed", ...)` → status "ready".
  4. Synthetic frontier findings (apiArr +1 mag 3, releaseCadence +1 mag 2, entity "OpenAI") through `build_briefing` + `build_scorecard` (with horizons) → NONZERO DMI (hand-compute in the test comment: `0.2·1·3/3 + 0.1·1·2/3 = 0.2667`), indices present, gate passes. This closes the backlog's "empty weights (zero indices)".
- Flat indicator namespace: NOT fixed here (F24 feature track) — add one line to the manifest description acknowledging shared global indicator ids; note it in your report.
- Commit: `fix(F27): models.frontier-closed runnable - real weights, coverage manifest, nonzero-index proof`.

## Out of scope (controller wires at merge): cli threading of `personaLabel` → `build_system` in the emit/judge paths.
## Self-review: SYSTEM byte-identity pinned in both prompt files; diff shows only owned files; suite green.
