# Wave-2 Lane F — Brief/Report + Price Track (F18, F29, F33, F34, F49, F51) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute tasks IN ORDER, strict TDD, commit per task.

**Goal:** Honest rendering (F18 token-matched trajectory arrows, F29 single-source ⚠, F33 bounded STORYLINES), a recalibrated materiality fold (F34), and the F8-decision deliverable: a code-computed **Price Momentum overlay** (F49) fed by per-series price dedup keys (F51).

**Tech Stack:** Python 3.11, pydantic v2, pytest. No new dependencies.

## Global Constraints
- Branch `fix/lane-f`, own worktree, run from its root. Tests: `C:\Users\danie\random_for_fun\.venv\Scripts\python -m pytest -q` (baseline 516 passed / 3 skipped). Full suite green after every task.
- **You own:** `gpu_agent/brief.py`, `gpu_agent/report.py`, `gpu_agent/wiki/lint.py` (ONLY `LintConfig` defaults + `_score_move`'s ind_sum line), `gpu_agent/gathering/dedup.py` (ONLY the price-key branch in `classify_findings`), new `gpu_agent/price_track.py`, and tests `test_brief_*.py`, `test_report.py`, `test_wiki_lint_materiality.py`, `test_dedup_classify.py` (price cases), new `test_price_track.py`, new `test_w2_lane_f.py`.
- **NEVER edit:** `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`, `extraction/*`, `cli.py`, `wiki/` other files, `llm/*`, `manifest.py`, `registry/*` code, fixtures under `fixtures/golden|recorded`, `.claude/skills/*`. The frozen v1.2 contract is CLOSED — nothing in it may change again.
- Commit trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: F18 — trajectory arrows match TOKENS, not substrings
**Files:** `gpu_agent/brief.py` (`_traj_arrow`); tests in `test_w2_lane_f.py`.
- Replace substring matching with token matching: `tokens = set(re.findall(r"[a-z]+(?:-[a-z]+)?", (text or "").lower()))`, then intersect with `_TRAJ_UP/_TRAJ_DOWN/_TRAJ_FLAT`. Precedence unchanged (UP, DOWN, FLAT, `·`).
- Pin: `"supply glut worsening"` → `▼` (the review's bug: `"up" ⊂ "supply"` gave ▲); `"shutdown risk"` → `·` (no "down" from "shutdown"); `"on-track"` → `=`; `"tight but improving"` → `▲` (UP precedence).
- Commit: `fix(F18): trajectory arrows tokenize - 'supply glut worsening' no longer renders UP`.

### Task 2: F29 — single-source ⚠ flag in the brief board
**Files:** `gpu_agent/brief.py` (`_board_rows`); tests in `test_w2_lane_f.py`.
- For each rendered row, compute distinct publisher domains over the latest finding's evidence (`urlparse(e.url).netloc.lower()` minus leading `www.`; empty → `e.source.lower()`). If exactly one distinct publisher → append tag `⚠single-source` to that row's existing tag list.
- Pin: one-evidence finding → tagged; two evidence entries from different domains → NOT tagged; two evidence entries from the SAME domain → tagged.
- Commit: `fix(F29): single-source rows carry a visible warning tag in the demand/supply board`.

### Task 3: F33 — bound STORYLINES growth
**Files:** `gpu_agent/brief.py` (`render_storylines`); tests in `test_w2_lane_f.py`.
- Cap each group (REGISTERED / PROVISIONAL) at the top **8** by the existing `(-salience, title)` order; when a group is capped, append `    (+K more tracked — see wiki-lint)` with the exact fold count. Nothing silent.
- Pin: 10 provisional storylines → 8 rendered + `(+2 more tracked — see wiki-lint)`; 8 or fewer → no fold line; byte-determinism preserved (same input → same output).
- Commit: `fix(F33): STORYLINES render capped at 8 per group with an explicit fold count`.

### Task 4: F34 — recalibrate the materiality fold
**Files:** `gpu_agent/wiki/lint.py`; tests: update `test_wiki_lint_materiality.py`, add cases in `test_w2_lane_f.py`.
- Change `_score_move`'s indicator sum to count EVERY observed finding's magnitude (`ind_sum += f.magnitude` unconditionally) — the `scoring` flag stays recorded in `factors.indicatorMoves` for display, but a non-scoring indicator (designWins, D6) is still ACTIVITY. Rationale: under F15's computed salience, a NEW secondary non-scoring thread scored `w_new 0.5 × tier 0.6 × salience-weight 0.5 = 0.15 < 0.3` — the lifecycle's discovery class was structurally folded.
- Verify the new arithmetic IN TESTS (show the math in comments):
  - NEW secondary thread, one non-scoring mag-2 finding: `(0.5 + 0.3·2) × 0.6 × 1.0 × 1.0 × 0.5 = 0.33 ≥ 0.3` → material.
  - NEW secondary price-only thread, one D6 mag-1 finding: `(0.5 + 0.3·1) × 0.6 × 0.5 = 0.24 < 0.3` → folded (price noise stays quiet).
  - Existing `test_wiki_lint_materiality.py` expectations updated with the same explicitness — no assertion deleted.
- Commit: `fix(F34): materiality counts non-scoring activity - the discovery class is no longer structurally folded`.

### Task 5: F51 — per-series dedup key for price findings
**Files:** `gpu_agent/gathering/dedup.py` (`classify_findings` key construction ONLY); tests: price cases in `test_dedup_classify.py`.
- For findings with `f.side == "price"`, the L2 key becomes `(entity, indicatorId, publisher, unit)` where `publisher` = first evidence url's netloc lowercased minus `www.` (fallback `evidence[0].source.lower()`, or `""` if no evidence) and `unit` = `f.value.unit if f.value else ""`. Non-price findings keep `(entity, indicatorId)` exactly as today (represented internally as `(entity, indicatorId, "", "")` — pin that non-price behavior is byte-identical via an existing-test re-run).
- Pin: Lambda B200 + CoreWeave B200 + Runpod B200 (same entity+indicator, three domains) → three NEW records, no dispersion; two same-domain same-unit rows with different values → one rep + dispersion (unchanged conflict semantics WITHIN a series). Document the known limit in a comment: SKU granularity (B200 vs H100 at one provider) still collapses until a seriesKey field exists (feature track).
- Commit: `fix(F51): price findings dedup per (entity, indicator, publisher, unit) series - providers no longer collapse`.

### Task 6: F49 — the Price Momentum overlay (computed, displayed, never blended)
**Files:** Create `gpu_agent/price_track.py`; modify `gpu_agent/report.py` (add ONE section renderer + wire into `render_report` after the DEMAND/SUPPLY MOMENTUM section) and `gpu_agent/brief.py` (one overlay line in `render_state_of_market`, after the Gap line, only when a track exists); tests `test_price_track.py`.
- `price_track.py` — pure, deterministic, no I/O:
```python
class PriceSeries(BaseModel):
    indicatorId: str; unit: str; publisher: str
    value: float; observedAt: str; findingId: str
    delta: Optional[float] = None       # vs prior scorecard's matching series
    direction: Optional[Literal["up", "down", "flat"]] = None   # |Δ| <= rel_tol 0.01 -> flat

class PriceTrack(BaseModel):
    series: list[PriceSeries]           # sorted (indicatorId, publisher, unit)
    pmi: Optional[float] = None         # mean of (+1 up / -1 down / 0 flat); None if no series has a delta
    matchedSeries: int = 0

def compute_price_track(sc: Scorecard, prior: Scorecard | None = None) -> PriceTrack: ...
```
  Series extraction: measured findings with `side == "price"` and a value; per series key `(indicatorId, publisher, unit)` keep the latest vintage (capturedAt, observedAt, magnitude). Prior matching by the same key. PMI over matched series only.
- Report section (renderer `render_price_track(track)`):
```
PRICE TRACK  (overlay — displayed, never blended into DMI/SMI)
  D6 [lambda.ai] 6.69 USD_per_gpu_hr   Δ vs prior: —
  gpuSpotPrice [ebay.com] 6113 USD_per_card   Δ vs prior: —
  PMI: — (0 matched series — needs two cycles of the same series)
```
  Omit the whole section when the scorecard has no price series (honest absence, no placeholder).
- Brief line (only when track non-empty): `  Price overlay: N series tracked, PMI —` (or the signed PMI with ▲/▼/= via the report's momentum word at |PMI| ≥ 0.5 up/down else flat — pin exact wording in tests).
- Pin: (1) v13-style scorecard fixture with the live 2026-07-02 price findings → 3+ series, pmi None; (2) synthetic prior with one matching series 5% lower → delta positive, direction "up", pmi 1.0; (3) rel_tol flat case; (4) report renders the section between DEMAND/SUPPLY MOMENTUM and ENTITY PANEL and stays byte-deterministic; (5) NEVER feeds any number into demandSupply/indices (assert scorecard fields untouched).
- Commit: `feat(F49): Price Momentum overlay - per-series levels + deltas + PMI computed in code, displayed beside DMI/SMI, never blended`.

## Self-review: each F-id maps to a task; `git diff main --stat` shows only owned files; suite green.
