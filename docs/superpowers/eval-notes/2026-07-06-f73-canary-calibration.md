# F73a — Seeded-regression canary calibration note

**Status:** SCAFFOLD — live capture is a flagged follow-up (see "Open follow-up" below).
Written in worktree `.worktrees/eval-gate-power`, branch `fix/eval-gate-power`, alongside
the F73b/F73c gate changes. No numbers below are invented; the fields marked `TODO (live
capture)` stay empty until a real eval run fills them.

## Purpose

Prove — and keep proving — that the improved eval-v2 gate (F73b marginal band + F73c
pooled-dispersion epsilon) hard-fails a deliberately damaged extract prompt. The canary is
a captured `report.json` from a live damaged-prompt run, replayed by the deterministic test
`tests/test_evals_canary.py`. If the damaged prompt still clears the bar, that is a finding
(the gate lacks power), not a test bug — record it here and escalate to the reviewer.

## The damage (exact, reproducible)

Damage exactly ONE prompt, transiently, for the capture only:

- **Seam:** extract.
- **Edit:** strip the corroboration sentence from the extract SYSTEM prompt — the clause
  requiring corroboration across *distinct outlets, not syndication of one story* /
  *across separately fetched documents*.
- **Everything else unchanged:** same cases (`fixtures/evals/cases`), same graders, Opus
  brains + Opus rubric graders.

The damage is NEVER committed to a prompt file — the F6 hash-pin would trip, and prompt
changes are out of scope for this lane. Restore the prompt immediately after capture.

## Capture procedure (one-time, live)

1. In a clean checkout, apply the extract-system-prompt damage above (working tree only).
2. Run the standard eval pipeline for the extract seam against the committed cases:
   emit-brain -> record-brain -> emit-grade -> record-grade, Opus brains + Opus graders.
3. Copy the produced `report.json` to
   `fixtures/evals/canary/extract-corroboration-stripped/report.json`.
4. Keep the raw run dir under gitignored `work/` (never `git clean`).
5. **Restore the prompt** (revert the working-tree damage) and confirm the hash-pin is
   green again.
6. Fill the results table below, delete the `@pytest.mark.skip` marker in
   `tests/test_evals_canary.py`, and run `pytest tests/test_evals_canary.py` — expect PASS
   (i.e. the gate rejected the damaged run).

## Results (from the live capture)

| Field | Value |
| --- | --- |
| Run dir (gitignored `work/`) | TODO (live capture) |
| asOf | TODO (live capture) |
| Extract seam mean (damaged) | TODO (live capture) |
| Baseline extract mean / bar / hard-bar | 6.75 / (bar = 6.75 - eps) / (hard = 6.75 - 2*eps) — eps from live baseline |
| Gate decision | TODO (live capture) — expected `marginal-fail` or `hard-fail` |
| `verdict.reasons` (extract) | TODO (live capture) |

Note: the committed `fixtures/evals/baseline.json` records extract seamMean 6.75 and
epsilon 0.3125 (v1 half-range) at time of writing; the bar the canary is judged against is
whatever the committed baseline holds when the capture is replayed.

## Standing rule

**Re-run this live canary after ANY change to `gpu_agent/evals/harness.py`** (gate math) or
to the extract prompt/baseline, and update both the fixture and this note. A green replay
test with a stale fixture is not proof.

## Open follow-up (flagged — requires the live harness)

- [ ] **Live capture + un-skip.** This lane (P2, isolated worktree) scaffolded the test and
  this note but did NOT run the live eval cycle — driving a full Opus-brains + Opus-graders
  capture is out of reach from here, and the fixture MUST be captured live, never
  hand-authored. The fixture path currently holds only a `PENDING.md` marker. A follow-up
  with the live harness must: capture the damaged run, commit the real `report.json`, fill
  the results table, delete the skip marker, and confirm the replay test PASSES. If the
  damaged prompt clears the bar even after F73b/F73c, record that as a gate-power finding
  and escalate to the reviewer (epsilon still too wide).
