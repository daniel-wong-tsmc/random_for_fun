# F71 mechanism trace, verified code paths, and the reproduction test to build

This file is the deep technical backing for Phase 1 of `SKILL.md`. Read the phase first; come
here when you need exact line references or want to build the discriminating test.

## 1. The two code paths that collide

**Path A — the anchor bound (Part 7 "bias guardrail").** A dimension rating may not contradict
its code-computed anchor. Implemented TWICE, deliberately, at two different points in the judge
pipeline:

- `gpu_agent/gate.py:65-89` — `_rating_consistent_with_anchor` + the loop inside
  `check_scorecard`. `_ANCHOR_TOL = 0.15` (line 67; tightened from 0.5 by F36 — "'Very strong' at
  anchor -0.49 is not judgment room"). `"Very strong"/"Strong"` need `anchor > -0.15`;
  `"Weak"/"Very weak"` need `anchor < 0.15`; `"Mixed"` is always legal.
- `gpu_agent/judgment/judge.py:109-119` (`_conflicts`) — the SAME tolerance function, imported
  directly (`from gpu_agent.gate import _rating_consistent_with_anchor, check_scorecard`), run
  against the AGGREGATED majority rating before a scorecard object even exists.

`judge_findings` (`judge.py:131-152`) wraps `_conflicts` in an **automatic resample loop**:
`for _ in range(1 + resample_budget)` (default `resample_budget=2`, hardcoded — not a CLI flag
anywhere; confirmed via `grep -n resample_budget gpu_agent/cli.py` returning nothing but the
`judge_findings(...)` call sites). Each round calls `client.complete_json` `samples` times, then
`aggregate()`, then `_conflicts()`. If conflicts persist for all `1 + resample_budget` rounds it
raises `JudgmentError(last_conflicts)` (line 152).

**Path B — the F63 evidence-sufficiency gate.** `gpu_agent/sufficiency.py::check_sufficiency`.
Rule: a dimension rating that CHANGES vs the prior cycle's `MemoryBundle.priorRatings` needs
either a primary-tier citation or `>= minDistinctPublishers` (3, `registry/corroboration.json`)
distinct `publisher_key` values among its cited findings' evidence. No memory (no prior
scorecard) → inert. This is called from two CLI sites, BOTH before `judge_findings`/the anchor
check ever runs in that invocation: `cli.py:451-457` (`judge --recorded`) and `cli.py:782-790`
(`pipeline --recorded-judge`, after the F62 corpus merge, using the merged `findings` + a
`MemoryBundle` built from `--corpus-store`).

## 2. Why they deadlock (verified against `store/cycle-log.json` at commit `99ca522`)

```
git show 99ca522:store/cycle-log.json | Select-String sufficiency
```
returns (verbatim, 2026-07-05 monthly v3 run):
> `"sufficiency": "bypassed - moat Weak->Mixed forced by +0.50 anchor (Weak illegal) but evidence
> is 2 secondary publishers (<3, no primary); one rewrite attempt made, then --no-sufficiency;
> logged"`

Reconstructed sequence across the SESSION's dispatch rounds (the CLI does not orchestrate this
loop itself — the coordinator does, per `run-cycle` SKILL step (d)):

1. Judge brain rates `moat` **Weak**, citing findings whose measured `moat` anchor is **+0.50**.
   `+0.50 > -0.15` ⇒ `"Weak"` is illegal under `_rating_consistent_with_anchor` — Path A fires.
2. Session re-dispatches (this is the "one rewrite attempt" the backlog records); brain now says
   **Mixed** — anchor-legal (`"Mixed"` is always allowed). Path A is now clean.
3. But `moat`'s PRIOR memory rating (say, whatever the last committed scorecard held) differs
   from `Mixed` — a rating **change**. Path B fires: the findings behind the change cite only 2
   secondary publishers, no primary. Sufficiency gate rejects the same answer Path A just forced.
4. There is no THIRD legal state — the anchor forbids Weak, the evidence forbids a corroborated
   Mixed-vs-prior — so the run completes under `--no-sufficiency` (a whole-run bypass), logged
   honestly, not hand-waved. This is F75's exhibit A as well as F71's.

## 3. A verified extra wrinkle: Path A has NO clean CLI-level error handler

`grep -n "JudgmentError" gpu_agent/cli.py` returns nothing except the import and the raise sites
inside `judge.py` — **no `except JudgmentError` exists anywhere in `cli.py`**, unlike
`check_sufficiency`/voice-lint which have dedicated `_report_sufficiency_violations` /
`_report_voice_violations` clean-exit helpers (`cli.py:407-424`). A `JudgmentError` — whether
from `_gate_backstop` or from resample-budget exhaustion — propagates as an **uncaught Python
exception** (a traceback), not a friendly re-dispatchable message.

This matters operationally for BOTH `judge --recorded` and `pipeline --recorded-judge`: both
paths hand `judge_findings` a `RecordedClient` seeded with EXACTLY `samples` canned answers
(`cli.py:434-437` validates `len(answers) != args.samples`, and `--recorded-judge` reads the
whole file as-is). `RecordedClient.complete_json` (`gpu_agent/llm/recorded.py:17-22`) pops one
canned answer per call and raises `LLMError("no recorded response for this call")` once the
deque is empty. So if the FIRST internal round already conflicts with the anchor, `judge_findings`
tries to resample (round 2) and the `RecordedClient` — which only ever had `samples` answers —
immediately raises `LLMError`, not a clean conflict report.

**Existing unit-level tests already pin pieces of this** (they are NOT run through the CLI, so
they dodge the `LLMError` trap by supplying padded arrays):
- `tests/test_judge_findings.py::test_anchor_conflict_resamples_then_resolves` — 3+3 recorded
  answers, first round conflicts, second round resolves.
- `tests/test_judge_findings.py::test_anchor_conflict_exhausts_budget_then_raises` — 9 recorded
  answers (`resample_budget=2` needs 3 rounds × `samples=3`), all conflict, raises `JudgmentError`
  cleanly (function-level, not CLI-level).

**What is NOT pinned anywhere:** the actual live failure mode — a `judge --recorded` or
`pipeline --recorded-judge` invocation fed exactly `samples` answers whose first round conflicts
with the anchor. Today that call would raise `LLMError`, not `JudgmentError`, and neither has a
`cli.py` handler. Practically this means the live session resolves the anchor conflict OUTSIDE
the CLI (reading the emitted prompt's stated anchor value, recognizing the qualitative rating
won't clear it, and re-dispatching BEFORE ever saving/running the recorded answer through
`--recorded-judge`) — the documented run-cycle re-dispatch protocol (SKILL.md ~141-162) covers
`voice-lint:`/`sufficiency:` stderr prefixes only; it says nothing about `"contradicts anchor"`
or an uncaught traceback. **If you hit a traceback mentioning `contradicts anchor` while
executing `run-cycle` today, that is expected under the current code — not a new bug — until F71
ships a clean handler.**

## 4. The discriminating test to design (proposed, not yet built)

Goal: pin the CROSS-GATE deadlock at the CLI level (not just each gate in isolation), so a Part-33
migration's fix can be verified red-before/green-after.

Sketch (mirrors `tests/test_cli_sufficiency.py::test_judge_recorded_rejects_undersourced_rating_change`
for the sufficiency half, and `tests/test_judge_findings.py::test_anchor_conflict_*` for the
anchor half — combine their fixtures):

1. Seed a `MemoryBundle`/prior scorecard with `moat` rated `"Weak"` (or any rating whose anchor-
   legal replacement is a genuine CHANGE).
2. Construct findings whose `moat` anchor computes to a value that makes `"Weak"` illegal (e.g.
   `pD=+1, magnitude=3` on a `moat`-grouped indicator → anchor `+1.0`, well past `+0.15`).
3. Give those same findings exactly 2 distinct secondary-tier publishers, no primary (below the
   `minDistinctPublishers=3` bar).
4. Record a judge answer that is ALREADY anchor-consistent (`"Mixed"`) — i.e. simulate the
   post-rewrite state directly, sidestepping the `LLMError` trap described in §3 (that trap is a
   SEPARATE, also-real gap worth its own tiny test, but don't conflate the two in one assertion).
5. Feed it to `pipeline --recorded-judge` (or call `check_sufficiency` + `judge_findings`
   directly at the function level for a faster unit test). Assert: TODAY this fails on
   `sufficiency:` with no legal alternative (the deadlock, reproduced). AFTER the fix: assert the
   chosen exemption path fires — e.g. the scorecard is written with a trust-footer stamp and no
   `--no-sufficiency` flag was needed — with a SEPARATE assertion that a genuine judgment
   re-rate (not anchor-forced) still gets blocked by sufficiency as before (the fix must not
   loosen the gate globally, only for the anchor-forced case — this is the regression the
   FENCED-OFF option in `SKILL.md` §"widen anchor tolerance" warns against).

## 5. Solution-menu cross-reference

The ranked menu lives in `SKILL.md` Phase 1 (kept there so the runbook stays the single source of
the decision). This file only backs the mechanism claims that menu's obligations rest on.
