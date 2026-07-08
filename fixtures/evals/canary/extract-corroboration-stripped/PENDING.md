# PENDING — canary fixture awaiting live capture

`report.json` for the F73a seeded-regression canary is NOT yet captured. It must be
produced by a live eval run (Opus brains + Opus graders) against the extract prompt with
the corroboration sentence stripped — it MUST NOT be hand-authored (hand-editing brain or
grader output is forbidden in this repo).

- Test that will replay it: `tests/test_evals_canary.py` (currently `@pytest.mark.skip`).
- Capture procedure + standing rule:
  `docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md`.

Once `report.json` lands here, delete this file and remove the skip marker in the test.
