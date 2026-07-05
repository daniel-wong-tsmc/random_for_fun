# F63 — Corroboration Doctrine for Secondary Evidence + Evidence-Sufficiency Gate: Design

**Date:** 2026-07-04
**Status:** approved by user (approach A; four AskUserQuestion forks recorded below)
**Author model:** Claude Fable 5
**Branch:** `f63-corroboration-doctrine` (worktree `.worktrees/f63-corroboration`, from post-F62 main)

## Problem

Secondary evidence is confidence-capped at medium (extraction prompt rule + gate F2e) and
secondary-only findings may not move headline status (charter Part 37) — so **no quantity of
independent open-web reporting can move status or conviction until a filing confirms it**. The
desk resolves at filing cadence; the exec decides at headline cadence. Part 37's staged-trust
paragraph explicitly reserved this increment: "Hard multi-source corroboration ('did ≥2
independent sources agree?') is the next increment, not v1." F63 is that increment, plus the
counterweight the backlog binds to it: a deterministic **evidence-sufficiency gate** so that
corroborated news can move ratings and insufficient news cannot. Loosening without the
tightening half would reintroduce the whipsaw the anti-whipsaw machinery exists to prevent.

## Doctrine (one sentence)

**N independent secondary publishers (distinct outlets, not syndication) agreeing within the
corpus window may move confidence / conviction / a dimension rating ONE bounded step; every
such step is logged with its corroboration set and a pending-filing-checkpoint tag; the next
primary-evidence cycle confirms or reverses it as ordinary re-judging.**

- **N = 3**, stored once in a new `registry/corroboration.json`
  (`{"minDistinctPublishers": 3}`), loaded via `gpu_agent/config.py`. Deliberately stricter
  than the wiki's ≥2 page-promotion bar because these steps move decision-facing state; the
  wiki bar is untouched.
- **Publisher identity = F31's `_publisher_key`** (evidence URL netloc, www-stripped,
  lowercased; fallback to the source string). Syndication of one wire story across N outlets
  hosted at one domain collapses to one publisher; genuinely distinct outlets count once each.
- **Checkpoint = logged tag, no auto-resolve machinery.** The thesis book and judge memory
  re-litigate every cycle; when the filing lands, the next judgment naturally confirms or
  reverses the step. No new lifecycle state machine.
- Charter home: **append to Part 37** (F69 precedent), amending the staged-trust paragraph to
  say the increment has landed and the confidence cap / status freeze now yield to the ≥N rule.

## Architecture — the three surfaces + shared identity

### 0. `gpu_agent/publisher.py` (new, tiny; zero behavior change)

`publisher_key(evidence) -> str`: the F31 identity, moved verbatim from
`wiki/lifecycle.py::_publisher_key`. `wiki/lifecycle.py` re-exports it (`_publisher_key =
publisher_key`) so its callers and `thesis.py`'s defensive import keep working byte-identically.
Rationale: after F63 the identity has three consumers (wiki lifecycle, thesis rule 6, gate
F2e) — one neutral home prevents drift. `thesis.py`'s inline fallback copy is retired in favor
of importing the shared module (thesis.py is edited in surface 2 anyway).

### 1. Gate F2e amendment — the single frozen-core edit (contract v1.3)

`gpu_agent/gate.py` (currently):

```python
# F2e — headline protection at finding level
if f.evidence and all(e.tier == "secondary" for e in f.evidence) and f.confidence.level == "high":
    errors.append(f"{f.id}: secondary-only evidence cannot support high confidence")
```

becomes: the error is raised only when the finding's evidence spans **fewer than N distinct
publishers** (`publisher_key` over `f.evidence`). Error text names the shortfall:
`"{f.id}: secondary-only evidence cannot support high confidence (2 distinct publishers < 3)"`.
A corroborated finding (≥N distinct secondary publishers) may carry high confidence.

- **Extraction SYSTEM sentence amended** (same rule, told to the brain): the current
  "A Finding whose only supporting evidence is secondary … must set confidence at most medium;
  only primary (filing) evidence may support high confidence." gains the exception
  "— unless its evidence spans at least 3 distinct publishers (distinct outlets, not
  syndication of one story), in which case high is allowed and the basis must name the
  corroboration." Exact wording finalized in the plan; extract prompt hash drifts.
- **Migration discipline:** `docs/migrations/2026-07-contract-v1.3.md` documents exactly this
  one rule change (v1.2 precedent format); gate tests for F2e are updated deliberately in the
  same commit; the frozen-core diff check for this branch asserts the gate.py diff is exactly
  the F2e rule and nothing else, and that scoring.py / schema/* / briefing.py / judge.py /
  pipeline.py remain empty-diff.

### 2. Thesis rule 6 amendment — corroborated reversals apply (`thesis.py`, not frozen)

Current: `applied = confirmed_by_pending or not is_reversal or _has_primary(findingIds)`.
Amended: `… or _distinct_publishers(findingIds, findings_by_id) >= N` where
`_distinct_publishers` counts `publisher_key` values across the cited findings' evidence
(the no-primary case is already the only path that reaches this clause, so tier filtering is
unnecessary — primary presence short-circuits earlier).

- The judgment record gains (additively) `"corroboratedStep": true` when this clause is the
  reason a reversal applied; the note reads
  `"{id}: applied: corroborated secondary reversal (K distinct publishers; pending filing checkpoint)"`.
  `publisherDomains` (already recorded on every judgment) IS the logged corroboration set.
- The under-corroborated deferral note becomes
  `"{id}: deferred: secondary-only reversal (K distinct publishers < 3)"` — the count makes
  the near-miss visible.
- Conviction movement stays inherently bounded: `_bump_conviction` clamps to ±1 per cycle.
- **THESIS_SYSTEM anti-whipsaw sentence amended**: "a reversal without primary evidence is
  recorded but not applied" gains "unless its cited findings span at least 3 distinct
  publishers". Thesis prompt hash drifts.
- `pendingChallenge` semantics are unchanged (a corroborated reversal simply applies instead
  of parking as a challenge; an under-corroborated one parks exactly as today).

### 3. Evidence-sufficiency gate — new `gpu_agent/sufficiency.py` (additive)

Deterministic post-judge check, wired at the SAME two seams as the F67 voice lint
(`judge --recorded` and `pipeline --recorded-judge` in `cli.py`); the frozen judge
aggregation is untouched.

**Rule:** for each dimension whose `rating` differs from the prior-cycle rating in MEMORY,
and for a changed `categoryStatus.bottleneck`, the changed item's cited findings must include
**primary evidence or span ≥N distinct publishers**. (For a bottleneck change, the newly named
dimension's citations are checked.)

- **Scope (deliberate, YAGNI):** rating changes and binding-constraint changes only.
  Direction-only changes, constraintLabel prose, and reason text never trigger. A dimension
  with no prior rating in MEMORY is exempt (nothing to protect). No MEMORY at all (first
  cycle) → the gate is inert.
- **Failure = gate failure, reject → re-dispatch** (user-selected): one stderr line per
  violation, prefix `sufficiency: ` (grep-stable, like `voice-lint: `):
  `sufficiency: momentum: rating changed Strong->Very strong with insufficient evidence (no primary; 2 distinct publishers < 3)`.
  The session re-dispatches the judge brain with the violations appended (F38 discipline —
  never hand-edit brain output). The re-answer either keeps the prior rating or cites
  sufficient evidence.
- **One judge SYSTEM sentence announces the rule** (so brains don't burn re-dispatch loops):
  "Changing a dimension rating or the binding constraint versus the MEMORY state requires the
  cited findings to include a primary source or at least 3 distinct publishers; otherwise
  keep the prior rating." Judge prompt hash drifts.
- Signature sketch: `check_sufficiency(answer_json, memory_state, findings_by_id, n) ->
  list[str]` — pure, memory-state parsed from the same prior-cycle data the emit path already
  loads; exact plumbing (how the recorded seams obtain the prior ratings) is a plan-level
  decision with the constraint that emit and gate must read the SAME memory source the brain
  saw (F62's same-captured-at precedent).

### 4. F69 handoff — structured chase field on gather blobs (bookkeeping surface)

Gather blobs gain an optional structured field:

```json
"chase": {"attempted": true, "primaryFound": "https://…|null", "corroborators": ["https://…"]}
```

written by gatherers where Part 37's chase-and-corroborate step currently records free text;
`gather-category` SKILL.md's gatherer contract documents the field and instructs that
corroborating sources are **fetched as their own blobs** (already F70 doctrine: leads are
fetched raw, never ingested as synthesis).

**The corroboration math never reads this field.** Extraction rules forbid evidence URLs other
than the document's own, so cross-publisher corroboration enters `evidence[]` solely through
the honest pipeline: corroborator fetched as blob → extracted as its own finding → L2 dedup
merges same-claim findings ("corroborates …; evidence merged") → merged `evidence[]` spans
multiple publishers → the F2e / rule 6 / sufficiency math counts them. The blob field is chase
bookkeeping and skill enforcement only. **No `Finding` schema change.**

## What does NOT change

- Frozen core except the single F2e rule: `scoring.py`, `schema/*`, `judgment/briefing.py`,
  `judgment/judge.py` aggregation, `pipeline.py`, `JsonStore` — empty diff, test-asserted.
- No weighting, no time decay, no multi-step moves, no cross-window corroboration memory:
  one bounded step per cycle or nothing. (Future work if ever needed; out of scope.)
- Code never authors a rating/confidence/conviction: corroboration only UNLOCKS what was
  previously auto-capped (F2e), auto-deferred (rule 6), or would now be auto-rejected
  (sufficiency). The brain still writes every judgment.
- Wiki page-promotion corroboration (≥2) and its `_publisher_key` behavior: unchanged.
- **Contract v1.2's F3 dimension-level cap is intentionally unchanged** (`dimensionStatus.
  confidenceCap="medium"` + note "secondary-only evidence" when a dimension's citations carry
  no primary): the backlog sanctions only gate rule F2e, and keeping the dimension-confidence
  DISPLAY conservative while corroboration unlocks finding confidence and rating/conviction
  movement is the safe asymmetry.
- The daily/monthly cycle skill flow: unchanged except the judge re-dispatch loop gains the
  `sufficiency:` failure mode alongside `voice-lint:`.

## Interaction with live work (merge order)

Lanes β (`cli.py`: two CLI arguments) and γ (`thesis.py`: prose lint; explicitly never
`_finding_lines`/prompt text) are in flight. F63 touches different regions of both files
(recorded-judge block in `cli.py`; rule 6 apply logic + THESIS_SYSTEM in `thesis.py`).
Standard sequential merge gate with rebase reconciliation (parallel-setup design); F63 is
eval-gated and merges through the baseline independently.

## Testing

- `tests/test_publisher.py`: identity (netloc, www-strip, casing, source-string fallback);
  wiki/lifecycle re-export is the same object; thesis import path resolves to it.
- `tests/test_gate_corroboration.py`: F2e both ways — high + 3 distinct secondary publishers
  passes; high + 2 rejected with the count in the message; 3 evidence items on one netloc
  collapse to 1 and reject; primary evidence path unchanged; medium confidence never touched.
- `tests/test_thesis_corroboration.py`: corroborated secondary-only reversal applies with
  `corroboratedStep: true` + checkpoint note; 2-publisher reversal defers with count in note;
  primary path and pendingChallenge semantics byte-compatible with existing tests.
- `tests/test_sufficiency.py`: primary-backed change passes; 3-publisher change passes;
  2-publisher change fails with the exact stderr line; unchanged ratings never checked;
  no-MEMORY inert; prior-omitted dimension exempt; bottleneck change enforced on the new
  dimension; CLI seam test at `judge --recorded` (exit code + `sufficiency: ` line).
- Prompt pins: the three amended SYSTEM sentences (extract / thesis / judge).
- Contract: `docs/migrations/2026-07-contract-v1.3.md` exists and names only F2e; branch
  frozen-core diff check per above.

## Eval gate (session-level, end of plan)

All three seams drift (extract + judge + thesis prompt hashes) → the plan ends with a full
run-eval (14 brains + graders, tool-less Opus, F38 pairs) and `eval rebaseline` on a merit
PASS, with the F62 pre-committed two-attempt disposition: if two full attempts fail, STOP,
keep the pin red, BLOCKED-on-user with both runs' data. Incumbent baseline is F62's
(extract 6.75 / judge 7.50 / thesis 6.00) — note judge's bar is now the post-consensus-clause
7.50.

## Decision provenance

User-approved 2026-07-04, four AskUserQuestion forks + approach selection:
1. **Step surfaces: all three** (F2e finding confidence, thesis conviction, sufficiency gate
   on ratings/binding constraint) — over thesis-only or F2e-only scopes.
2. **N = 3, registry-configurable** — over N=2-everywhere or tiered thresholds.
3. **Sufficiency gate action: reject → re-dispatch** — over clamp-to-prior or advisory flag.
4. **Checkpoint: logged tag, no auto-resolve** — over a tracked auto-resolve state machine.
5. **Approach A** (surgical contract v1.3; everything else additive) — over a schema-extending
   re-version (B) or a post-gate code transform that mutates brain output (C, doctrine-barred).
Relitigate here if any pick is wrong.
