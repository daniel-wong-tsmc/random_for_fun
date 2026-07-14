# PENDING — F79 canary fixture awaiting live capture (fold into the G3 re-gate run)

`report.json` for the F79 seeded-regression canary is NOT yet captured. It must be
produced by the LIVE G3 eval run (Opus brains + Opus graders) against a deliberately
damaged extract prompt — it MUST NOT be hand-authored (hand-editing brain or grader
output is forbidden in this repo).

**The seeded damage (F79-specific):** the extract system prompt with the SIX new series
indicator ids stripped from the `scoring_indicators` vocabulary block — i.e. the brain
is told the pre-F79 vocabulary while the gate expects the six new ids. A context-free
brain then cannot emit pkgCapacityOrderSpread / hbmSupplyCapex / hyperscalerCapexRevision
/ odmMonthlyAiRevenue / tokenEconomics / marginalBuyerFinancing, so drafts for those
signals are invented or gate-dropped. This is the standing proof that the F79 prompt
change has teeth: a prompt that lost the new vocabulary cannot clear the bar.

- Seam under test: **extract** (the only seam whose prompt hash moved for F79 — the
  only seam that binds under F65's seam-scoped verdicts).
- Test that will replay it: `tests/test_evals_canary_f79.py` (currently `@pytest.mark.skip`).
- Capture procedure + standing rule (shared with the F73a canary):
  `docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md`.

Once `report.json` lands here, delete this file and remove the skip marker in the test.
