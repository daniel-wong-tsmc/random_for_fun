"""F73a seeded-regression canary: replay a captured damaged-prompt run through the
improved eval-v2 gate and assert the gate REJECTS it. This is the standing proof that the
gate has teeth — that a deliberately weakened prompt cannot clear the bar.

SKIPPED until the one-time live capture lands: the fixture
`fixtures/evals/canary/extract-corroboration-stripped/report.json` must be produced by a
real eval run (Opus brains + Opus graders) against the damaged extract prompt — it MUST
NOT be hand-authored (hand-editing brain/grader output is forbidden in this repo). Once the
live capture is committed, delete the skip marker. See
docs/superpowers/eval-notes/2026-07-06-f73-canary-calibration.md (Task 3 follow-up)."""
from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent.evals.harness import evaluate_v2, load_baseline

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.skip(reason="canary fixture pending live capture — see F73 plan Task 3 Step 1")
def test_canary_damaged_prompt_is_rejected():
    baseline = load_baseline(ROOT / "fixtures/evals/baseline.json")
    report = json.loads(
        (ROOT / "fixtures/evals/canary/extract-corroboration-stripped/report.json")
        .read_text("utf-8"))
    v = evaluate_v2(baseline, [report])
    assert v["pass"] is False                       # the gate has teeth
    assert v["decision"] in ("marginal-fail", "hard-fail")
    assert any("extract" in r for r in v["reasons"])
