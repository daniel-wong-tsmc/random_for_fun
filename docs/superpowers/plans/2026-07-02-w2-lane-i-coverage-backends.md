# Wave-2 Lane I — Coverage Matching + Backends (F28, F40) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute tasks IN ORDER, strict TDD, commit per task.

**Goal:** Coverage-gap matching stops producing false "required gaps" that get waved off in free text (F28: host-aware matching + mirror patterns + structured, auditable overrides), and the dead-SDK `ClaudeCodeClient` becomes an honest loud signpost to the session-driven flow (F40).

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints
- Branch `fix/lane-i`, own worktree, run from its root. Tests: `C:\Users\danie\random_for_fun\.venv\Scripts\python -m pytest -q` (baseline 516/3). Full suite green after every task.
- **You own:** `gpu_agent/manifest.py`, `gpu_agent/llm/claude_code.py`, `gpu_agent/llm/factory.py` (only if needed), `manifests/chips.merchant-gpu.json` (mirrorPatterns data), and tests `test_manifest.py`, `test_llm_backends.py`, new `test_w2_lane_i.py`.
- **NEVER edit:** everything else — notably `cli.py`, `gathering/*`, the re-frozen v1.2 core, prompts, wiki, brief/report, fixtures golden/recorded, `.claude/skills/*`.
- Backward compatibility: `compute_coverage_gaps(manifest, blob_urls, found_indicator_ids)` must keep working positionally for existing callers (the gather skill scripts call it exactly like that).
- Commit trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: F28a — host-aware URL matching + mirrorPatterns
**Files:** `gpu_agent/manifest.py`, `manifests/chips.merchant-gpu.json`; tests in `test_w2_lane_i.py`.
- `ExpectedSource` gains `mirrorPatterns: list[str] = Field(default_factory=list)` — known mirrors/CDNs of the source (e.g. NVDA IR content served from `s201.q4cdn.com`; BIS rules on `www.bis.gov` vs the manifest's `bis.doc.gov`).
- New matching helper (pure):
```python
def _url_matches(url: str, pattern: str) -> bool:
    """Host-aware: a pattern with no '/' matches when the url's host == pattern or
    endswith '.'+pattern; a pattern with a path keeps today's substring semantics."""
```
  `compute_coverage_gaps` uses `_url_matches` over `urlPatterns + mirrorPatterns`.
- Data: add the two known mirrors to `manifests/chips.merchant-gpu.json` — `s201.q4cdn.com` on `nvda-earnings` and `nvda-10k-risk-factors`; `www.bis.gov` on `bis-export-controls`.
- Pin the review's exact false gaps: blob url `https://s201.q4cdn.com/141608511/files/doc_financials/10q.pdf` now COVERS `nvda-earnings`; `https://www.bis.gov/press-release/x` covers `bis-export-controls`; host matching does NOT over-match (`https://evil.com/?ref=sec.gov` must NOT match pattern `sec.gov` — host is `evil.com`); path-bearing patterns (`investor.nvidia.com/annual-reports`) keep substring semantics.
- Commit: `fix(F28a): coverage matching is host-aware with mirror patterns - 10-Q via q4cdn and BIS via www.bis.gov stop being false gaps`.

### Task 2: F28b — structured, auditable coverage overrides
**Files:** `gpu_agent/manifest.py`; tests in `test_w2_lane_i.py`.
- New model + additive param:
```python
class CoverageOverride(BaseModel):
    type: Literal["indicator", "source"]
    id: str
    reason: str          # the auditable free text that used to live in prose
    waivedBy: str        # who/what waived it, e.g. "gather-coordinator 2026-07-02"

def compute_coverage_gaps(manifest, blob_urls, found_indicator_ids,
                          overrides: list[CoverageOverride] | None = None) -> list[CoverageGap]:
```
- A gap whose `(type, id)` matches an override is STILL RETURNED but with `acquisitionStatus="waived"` (add the literal to `CoverageGap.acquisitionStatus`) and `reason` = `f"waived: {ov.reason} (by {ov.waivedBy}); original: {original_reason}"` — auditable, never silently dropped.
- Pin: override on a not-covered source → status "waived", original reason preserved inside; no override → byte-identical to today; an override naming a COVERED item changes nothing.
- Commit: `fix(F28b): coverage overrides are structured and auditable - waived gaps stay visible with who/why`.

### Task 3: F40 — ClaudeCodeClient tells the truth
**Files:** `gpu_agent/llm/claude_code.py`; tests update `test_llm_backends.py`.
- Delete the SDK-driving `_raw_complete` body (it reads `message.text` which the SDK never provides, leaves tools enabled, has zero coverage, and is NOT the path the skills use). Replace the class body with a loud, immediate error:
```python
class ClaudeCodeClient:
    """The session IS the brain (charter Part 38): live runs emit canonical prompts
    (--emit-prompt), a dispatched tool-less subagent answers, and --recorded replays the
    answer through the deterministic gate. There is no SDK/API path."""
    def __init__(self, **opts): self._opts = opts
    def complete_json(self, prompt, system, schema, model):
        raise LLMError(
            "the claude_code backend is session-driven: run '<cmd> --emit-prompt', answer via a "
            "dispatched subagent, then replay with --recorded (see .claude/skills/run-cycle)")
```
- Factory unchanged (the class still exists; constructing it is fine, CALLING it is loud). Pin: `make_client("claude_code")` constructs; `complete_json` raises `LLMError` mentioning `--emit-prompt` and `--recorded`; `pipeline` invoked live WITHOUT `--recorded-extract` now fails loud with that message (subprocess test, tmp store) instead of an AttributeError deep in the SDK.
- Commit: `fix(F40): ClaudeCodeClient is an honest signpost - the emit->recorded session flow is the only live path`.

## Self-review: F28a/F28b/F40 map to tasks; positional-call compatibility pinned; diff shows only owned files; suite green.
