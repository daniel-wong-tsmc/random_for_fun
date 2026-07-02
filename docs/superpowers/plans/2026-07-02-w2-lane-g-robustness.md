# Wave-2 Lane G — Robustness Bundle (F41, F42, F50, F26-cli) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute tasks IN ORDER, strict TDD, commit per task.

**Goal:** Input robustness (F41: non-finite values, timestamp normalization, wiki id validation, crash-recoverable routing), hardcoded paths → config (F42), the run's asOf owning the scorecard label (F50, born from the F46 gate), and the de-GPU'd CLI defaults (F26's cli half).

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints
- Branch `fix/lane-g`, own worktree, run from its root. Tests: `C:\Users\danie\random_for_fun\.venv\Scripts\python -m pytest -q` (baseline 516/3). Full suite green after every task.
- **You own:** `gpu_agent/cli.py`, new `gpu_agent/config.py`, `gpu_agent/extraction/extractor.py` (validation additions only), `gpu_agent/wiki/store.py` (`_page_path` validation only), `gpu_agent/wiki/ingest.py` (`route_findings` recoverability only), and tests `test_cli_*.py`, `test_extractor*.py` (additive cases), `test_wiki_store.py` (additive), new `test_w2_lane_g.py`.
- **NEVER edit (re-frozen v1.2 contract + other lanes' files):** `gate.py`, `scoring.py`, `schema/finding.py`, `schema/scorecard.py`, `judgment/*`, `pipeline.py`, `brief.py`, `report.py`, `gathering/dedup.py`, `wiki/lint.py`, `wiki/lifecycle.py`, `manifest.py`, `llm/*`, `extraction/prompt.py`, `registry/*`, fixtures golden/recorded, `.claude/skills/*`. F41's "bump Finding.schemaVersion default" is EXPLICITLY SKIPPED — the schema is frozen again post-v1.2; note it in your final report.
- `assignment.py` is NOT yours (Lane H adds a field there in parallel) — F50 must work through `model_copy`, not schema edits.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: F50 — the run's asOf owns the scorecard label
**Files:** `gpu_agent/cli.py` (`_pipeline`); tests in `test_w2_lane_g.py`.
- In `_pipeline`, after `a = load_assignment(args.assignment)`: when `a.asOf != args.as_of`, do `a = a.model_copy(update={"asOf": args.as_of})` and print to stderr: `note: assignment asOf <old> overridden by run asOf <new> (F50)`. The scorecard then lands at `store/<cat>/<run-asOf>-vN.json`.
- Pin via the recorded-pipeline harness (copy the invocation pattern from existing `test_cli_*` pipeline tests): run with `--as-of 2026-06` (fixture agrees → no note; existing goldens unaffected), then with a divergent `--as-of` in a tmp store → file named by the RUN asOf + stderr note present. Context: the F46 daily run first wrote its scorecard as `2026-06-v13` because the committed assignment pins `asOf: 2026-06`.
- Commit: `fix(F50): pipeline run asOf overrides assignment asOf - daily scorecards stop mislabeling into the fixture month`.

### Task 2: F42 — hardcoded paths → gpu_agent/config.py
**Files:** Create `gpu_agent/config.py`; modify `gpu_agent/cli.py` (every `"registry/indicators.json"` / `"docs/taxonomy.json"` literal); tests in `test_w2_lane_g.py`.
```python
# gpu_agent/config.py
import os
REGISTRY_PATH = os.environ.get("GPU_AGENT_REGISTRY", "registry/indicators.json")
TAXONOMY_PATH = os.environ.get("GPU_AGENT_TAXONOMY", "docs/taxonomy.json")
```
- cli.py imports these; grep `cli.py` for the literals and replace every occurrence (`_load_registry`, `IndicatorHorizons.load(...)` call sites, `cycle-plan --taxonomy` DEFAULT value). Library modules that default-load (extraction/extractor.py's registry/taxonomy defaults) also switch to `config` constants — that file is yours for validation additions anyway.
- Pin: monkeypatched `GPU_AGENT_REGISTRY` env var pointing at a copy → `_load_registry` reads it (subprocess or importlib-reload pattern; document whichever you use); default behavior byte-identical.
- Commit: `fix(F42): registry/taxonomy paths resolve through gpu_agent.config (env-overridable) instead of scattered literals`.

### Task 3: F41a — non-finite values + timestamp normalization at extraction
**Files:** `gpu_agent/extraction/extractor.py`; tests additive in `test_extractor_v12.py` or `test_w2_lane_g.py`.
- In the per-draft validation (where excerpt/url are checked): a measured draft whose `value.number` is NaN or ±inf → violation `"non-finite value"` → dropped (use `math.isfinite`).
- In `draft_to_finding`: normalize `observedAt` and `capturedAt` — if the string parses with `datetime.fromisoformat` (handle trailing `Z` by replacing with `+00:00`), re-emit as UTC `YYYY-MM-DDTHH:MM:SSZ` for full timestamps and leave bare dates (`YYYY-MM-DD`) as-is; unparseable strings pass through unchanged (the gate's ISO-prefix check already fails them loud). This makes the frozen scoring's lexical `(capturedAt, ...)` comparison safe against mixed offsets WITHOUT touching scoring.py.
- Pin: NaN draft dropped with the named violation; `"2026-07-02T05:00:00+08:00"` normalizes to `"2026-07-01T21:00:00Z"`; `"2026-07-02"` passes through; garbage passes through (and a gate test confirms it still errors).
- Commit: `fix(F41a): extraction rejects non-finite values and normalizes timestamps to UTC - lexical vintage compare is safe`.

### Task 4: F41b — wiki page id validation + crash-recoverable routing
**Files:** `gpu_agent/wiki/store.py` (`_page_path`), `gpu_agent/wiki/ingest.py` (`route_findings`); tests in `test_w2_lane_g.py`.
- `_page_path`: validate `ptype in {"entity", "theme"}` and `slug` matches `^[a-z0-9][a-z0-9-]*$` → else `ValueError(f"unsafe page id: {page_id!r}")`. (Kills the `entity:../..` path escape.)
- `route_findings`: wrap the per-finding body so that a failure on finding N (e.g. a FindingStore id collision) does NOT lose findings 1..N-1's routing — they are already durably appended (verify by reading the code: appends happen per finding). Add the recoverability TEST: route a batch where finding 3 collides (same id, different content → ValueError), assert findings 1–2 are routed AND the error propagates loud AND a re-run after fixing finding 3 converges idempotently (no duplicate observations).
- Pin: `store.get_page("entity:../escape")` and `create_page("entity:../x", ...)` raise; happy-path ids unaffected.
- Commit: `fix(F41b): wiki page ids validated against path escape; routing is provably crash-recoverable`.

### Task 5: F26 (cli half) — de-GPU'd defaults
**Files:** `gpu_agent/cli.py`; tests updated where they relied on defaults.
- `judge --category`: drop `default="chips.merchant-gpu"` → `required=True`. Update any test invoking `judge` without `--category`.
- `ingest --primary-sources`: default stays `"sec.gov"` but the help text states it is a generic filings allowlist, extended per category via the gather skill (no behavioral change — document only). NOTE in your report: the prompt-persona half of F26 is Lane H's; the persona THREADING through cli is a controller step at merge — do NOT attempt it.
- Commit: `fix(F26-cli): judge --category is explicit - no merchant-gpu default baked into the CLI`.

## Self-review: F41 (a+b, schema bump skipped+noted), F42, F50, F26-cli each map to a task; diff shows only owned files; suite green.
