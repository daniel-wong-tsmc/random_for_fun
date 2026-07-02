# Wave-2 Lane J — Per-Dimension Rating Anchor Definitions (F39) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. One task, docs-only, but held to test-grade precision.

**Goal:** Two analysts shown the same evidence pick the same word: written five-word-scale definitions for each of the six dimensions (charter Part 17's "Very strong choke point" example, generalized), as a method doc the judge prompt can later reference.

## Global Constraints
- Branch `fix/lane-j`, own worktree. **You own ONLY:** new `docs/rating-anchors.md` and new `tests/test_rating_anchors.py`. Nothing else — no prompt, no code, no other doc.
- Ground the wording in `docs/agent-swarm-charter.md` (read Part 17 and the six-dimension definitions before writing) and `docs/taxonomy.json`'s dimension list. The six dimensions (exact ids): momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk. The five ratings (exact): Very strong, Strong, Mixed, Weak, Very weak.
- Tests: `C:\Users\danie\random_for_fun\.venv\Scripts\python -m pytest -q` (baseline 516/3).
- Commit trailer: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

### Task 1: docs/rating-anchors.md + structure guard test
- The doc: a short preamble (what an anchor definition is FOR: the rating names a market POSITION on that dimension, not a mood; the numeric anchor bounds it, the words decide within the band), then one section per dimension with a 5-row table: rating | one-sentence definition | a falsifiable marker ("you should be able to point at..."). Definitions must be DISCRIMINATIVE (adjacent ratings differ by a stated observable, not an adverb) and category-agnostic (no "GPU"/"NVIDIA" in the definitions themselves; examples may use any category).
  - Critical semantic to get right (it is counter-intuitive and the reason F39 exists): for **bottleneck** and **strategicRisk**, "Very strong" means the FACTOR IS VERY STRONGLY PRESENT (a very strong choke point / very high risk exposure) — the charter Part 17 usage — NOT "the company is in a very strong position." State this inversion explicitly in those two sections and in the preamble.
- The guard test (`tests/test_rating_anchors.py`): parse the doc; assert (1) all six dimension ids appear as headings, (2) each section contains all five rating words exactly once as table rows, (3) the inversion note is present for bottleneck and strategicRisk (assert a pinned phrase, e.g. "presence of the factor"), (4) no occurrence of "GPU" outside a clearly-marked Examples block. This keeps the doc from drifting into decoration.
- Commit: `docs(F39): per-dimension five-word rating anchor definitions - two analysts, same word (with the bottleneck/strategicRisk inversion stated)`.

## Self-review: doc + guard test only; suite green (517+/3).
