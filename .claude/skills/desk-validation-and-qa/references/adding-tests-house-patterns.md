# Adding tests — house patterns, by layer

Companion to SKILL.md §6. This walks through four representative test files chosen because
each exercises a different layer of the stack and each shows a convention worth copying rather
than reinventing.

## Layer 1 — schema/gate unit tests: the `_base(**over)` builder

`tests/test_gate_finding.py` (full file is ~40 lines) is the cleanest example:

```python
from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding

def _base(**over):
    data = {
        "id": "f", "statement": "s", "kind": "observed", "value": None, "trend": "flat",
        "why": "because", "impact": {"targets": ["chips.merchant-gpu"], "direction": "positive",
                                       "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-05-01", "excerpt": "e",
                       "tier": "primary"}],
        "reasoning": None, "confidence": {"level": "high", "basis": "b"}, "dispersion": None,
        "asOf": "2026-06", "indicatorId": "S9", "side": "supply", "polarityDemand": -1,
        "polaritySupply": 1, "magnitude": 2, "entity": "AMD", "observedAt": "2026-05-01",
        "capturedAt": "2026-06-12", "schemaVersion": "1.0",
    }
    data.update(over)
    return Finding.model_validate(data)

def test_clean_finding_passes():
    assert check_finding(_base()) == []

def test_measured_without_value_fails():
    f = _base(kind="measured", value=None)
    assert any("missing value" in e for e in check_finding(f))
```

Rules this pattern encodes:

- Start from a **known-valid** object; override exactly one field per test.
- Assert `== []` for the clean case (an explicit "nothing wrong" check, not just "didn't raise").
- Assert on a **violation-message substring**, never exact string equality — wording changes,
  the violation *category* is the contract.
- One test = one behavior. Don't combine "missing value" and "invented value" checks in one
  function even though they're both about `kind`/`value` consistency.

Use this pattern for anything under `gate.py`, `extractor.py` trust-boundary checks,
`judgment/judge.py` aggregation rules, `sufficiency.py`, or `thesis.py`'s `gate_answer`.

## Layer 2 — CLI plumbing tests: exit codes and stage contracts

`tests/test_cli_eval.py` drives the eval CLI verbs entirely offline via `main([...])` (no
subprocess, no LLM):

```python
def test_record_steps_missing_stage_input_exit_2(tmp_path, capsys):
    cases_dir = _write_cases(tmp_path)
    run = tmp_path / "run"
    main(["eval", "emit-brain", "--cases", str(cases_dir), "--out", str(run)])

    # record-brain with no brain-answers.json -> operator error (2), not gate failure (1)
    assert main(["eval", "record-brain", "--cases", str(cases_dir), "--out", str(run)]) == 2
    err = capsys.readouterr().err
    assert "brain-answers.json not found" in err
    assert "emit-brain" in err
```

Rules: exit code discipline is precise and worth asserting exactly —

| Exit code | Means |
|---|---|
| `0` | Clean run / PASS |
| `1` | Gate rejection or regression FAIL — a real signal about the thing under test |
| `2` | Operator error — a missing stage file, a bad flag combination; never a signal about the brain/prompt |

A test that only asserts `!= 0` on a failure path is weaker than the house standard — assert
the specific code, and (for operator errors) that stderr names the missing file and the command
that would have produced it.

The full `test_eval_full_offline_cycle` test in the same file is the reference example for
exercising the entire emit→dispatch(stubbed)→record→verdict→rebaseline cycle without any LLM
involvement — useful as a template if you need to test a NEW eval CLI verb end-to-end.

## Layer 3 — harness-internals tests: constructing reports directly

`tests/test_evals_harness_baseline.py` bypasses the CLI and cases-on-disk machinery entirely to
test `build_report()`/`evaluate_v2()` against hand-built dicts — useful when you want to hit an
edge state (miscalibration, bootstrap, v1-baseline no-comparison) without wiring up real case
files:

```python
def test_miscalibration_fails_verdict():
    cases = [_case("extract-t-01"), _case("extract-t-02", kind="negative")]
    grades, _ = record_grades(cases, {
        "extract-t-01": _grade_json("extract-t-01", 2),
        "extract-t-02": _grade_json("extract-t-02", 2),   # negative scores 8 -> miscalibrated
    })
    report = build_report(cases, grades, HASHES, baseline=None, as_of="2026-07-04")
    assert report["verdict"]["pass"] is False
    assert report["verdict"]["decision"] == "invalid-run"
    assert any("miscalibrated" in r for r in report["verdict"]["reasons"])
```

This file also carries the negative-space test that matters most for change control:
`test_v1_rebaseline_is_gone` — `assert not hasattr(harness, "rebaseline")` — a one-line pin
that the old single-run `--out` rebaseline form stays dead. If you ever see a plan or an old doc
reference `eval rebaseline --out`, this test is why it's wrong: the v1 form was deliberately
removed, not merely deprecated.

## Layer 4 — golden/fixture-health tests: whole-pipeline and whole-golden-set assertions

`tests/test_golden_integration.py` runs the real CLI `run` verb against `fixtures/golden/` and
diffs the result against the committed `scorecard.json`, popping `provenance` first (it carries
non-deterministic fields like capture timestamps):

```python
def test_cli_produces_golden_scorecard(tmp_path):
    rc = main(["run", "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--fixtures", "fixtures/golden", "--out", str(tmp_path)])
    assert rc == 0
    written = sorted((tmp_path / "chips.merchant-gpu").glob("*.json"))[0]
    got = json.loads(written.read_text("utf-8"))
    golden = json.loads(pathlib.Path("fixtures/golden/scorecard.json").read_text("utf-8"))
    got.pop("provenance", None)
    assert got["demandSupply"] == golden["demandSupply"]
```

`tests/test_evals_fixture_health.py` is the golden-SET-wide health check (not the scoring
golden) — it iterates every case in `fixtures/evals/cases/` and checks census floors, re-emit
success, frozen-answer gate-outcome stability under CURRENT gates, `mustMention` presence, and
notes/source substance. This is the test that catches contract drift silently invalidating old
frozen answers — if a case's `recordedAnswer` used to gate-pass and a later frozen-core change
makes it gate-fail (or vice versa), this test fails loudly instead of the golden set quietly
going stale. When it fails, the fix is almost never "update the test" — it's either (a) the
frozen-core change genuinely invalidates that case's premise and the case needs curating out
with a note explaining why, or (b) the frozen-core change has an unintended side effect and
needs its own fix.

## Where NOT to add a test

- **Anything that calls a real LLM or the network.** The suite is `$0` and deterministic by
  doctrine (`CLAUDE.md`; the F6 design's own "Out of scope: LLM dispatch in CI"). Live-only
  behavior gets an env-gated `skipif` test (see the 4 skip files in SKILL.md §2) — never a test
  that silently no-ops without an explicit skip reason.
- **A new pytest marker.** None are registered (no `conftest.py`, no `[tool.pytest.ini_options]`
  section); the only selection mechanism is `skipif` on env vars. Don't invent a marker-based
  selection scheme without first checking whether it belongs in this repo's minimal-tooling
  philosophy at all.
- **A test asserting on `checks.citationsResolve`.** It's a dead field (SKILL.md §6) — testing
  it tests nothing real; test the actual gate behavior in `gate_brain_answer()` instead.
