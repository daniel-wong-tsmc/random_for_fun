"""F67: the judge --recorded path lints brain prose and fails loud.

Adapted from the task-3 brief's placeholder test: the real `judge` subcommand takes
--recorded as a path to a JSON array of `samples` strings (one JudgmentResult per
element, RecordedClient's replay shape -- see test_cli_emit_prompt.py's
test_recorded_answer_must_be_array_of_serialized_strings), not a single answer object.
--findings/--category/--out/--samples mirror tests/test_cli_judge.py's real invocations."""
import json
import subprocess
import sys


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _clean_finding(fid="doc-nvda-1"):
    return {"id": fid, "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
            "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
            "evidence": [{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e", "tier": "primary"}],
            "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
            "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
            "magnitude": 2, "entity": "E", "observedAt": "2026-06-01",
            "capturedAt": "2026-06-12T00:00:00Z"}


BAD_NARRATIVE = "D2 rose. SDGI is robust. One. Two. Five sentences now."
GOOD_NARRATIVE = ("Demand is strong because hyperscaler orders exceed packaging output. "
                  "The crux is whether CoWoS capacity doubles by Q4. "
                  "Watch TSMC lead times first.")


def _judgment(narrative):
    return {"dimensions": {"momentum": {"rating": "Strong", "direction": "steady",
             "findingIds": ["doc-nvda-1"], "rationale": "Orders are strong."}},
            "categoryStatus": {"rating": "Strong", "direction": "steady",
                               "bottleneck": "momentum", "reason": "Orders are strong."},
            "narrative": narrative}


def _recorded_file(tmp_path, narrative):
    # RecordedClient replay shape: a JSON array of STRINGS, each a serialized JudgmentResult.
    p = tmp_path / "rec.json"
    p.write_text(json.dumps([json.dumps(_judgment(narrative))] * 3), "utf-8")
    return p


def _findings_file(tmp_path):
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([_clean_finding()]), "utf-8")
    return p


def _judge_args(tmp_path, recorded):
    return ("judge", "--findings", str(_findings_file(tmp_path)),
            "--category", "chips.merchant-gpu", "--samples", "3",
            "--recorded", str(recorded), "--out", str(tmp_path / "jdg"))


def test_bad_prose_fails_loud(tmp_path):
    rec = _recorded_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec))
    assert out.returncode != 0
    assert "voice-lint:" in out.stderr


def test_bad_prose_violations_are_indexed_by_sample(tmp_path):
    """F67 review fix: each violation is prefixed 'sample {i+1}: ' so a --samples 3+
    failure names WHICH recorded answer to re-dispatch, not just what broke. All 3
    recorded samples here are byte-identical, so all 3 indices must appear."""
    rec = _recorded_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec))
    assert out.returncode != 0
    for i in (1, 2, 3):
        assert f"voice-lint: sample {i}: " in out.stderr


def test_good_prose_passes(tmp_path):
    rec = _recorded_file(tmp_path, GOOD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec))
    assert out.returncode == 0, out.stderr


def test_bypass_flag(tmp_path):
    rec = _recorded_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec), "--no-voice-lint")
    assert out.returncode == 0, out.stderr


# ── pipeline --recorded-judge: the LIVE cycle's actual path (it never calls
# `judge --recorded` directly -- see .claude/skills/run-cycle/SKILL.md). The lint's whole
# purpose is to gate brain-written prose before it reaches a scorecard, so it must be wired
# here too, sharing _voice_lint_samples with the `judge --recorded` path above (same replay
# shape: a JSON array of serialized JudgmentResult strings). doc-nvda-1 is the finding id the
# extractor stamps for fixtures/raw/doc-nvda.json (docId + "-1"), matching _clean_finding's
# default and _judgment's findingIds so the recorded judge answer cites a real finding.

def _pipeline_recorded_judge_file(tmp_path, narrative):
    p = tmp_path / "rec-judge.json"
    p.write_text(json.dumps([json.dumps(_judgment(narrative))] * 3), "utf-8")
    return p


def _pipeline_args(tmp_path, recorded_judge, *extra):
    return ("pipeline", "--docs", "fixtures/raw",
            "--assignment", "fixtures/asg.chips.merchant-gpu.json",
            "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
            "--recorded-extract", "fixtures/recorded/extract-nvda.json",
            "--recorded-judge", str(recorded_judge), "--out", str(tmp_path / "store"), *extra)


def test_pipeline_recorded_judge_bad_prose_fails_loud(tmp_path):
    rec = _pipeline_recorded_judge_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_pipeline_args(tmp_path, rec))
    assert out.returncode != 0
    assert "voice-lint:" in out.stderr


def test_pipeline_recorded_judge_good_prose_passes(tmp_path):
    rec = _pipeline_recorded_judge_file(tmp_path, GOOD_NARRATIVE)
    out = _run(*_pipeline_args(tmp_path, rec))
    assert out.returncode == 0, out.stderr


def test_pipeline_recorded_judge_bypass_flag(tmp_path):
    rec = _pipeline_recorded_judge_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_pipeline_args(tmp_path, rec, "--no-voice-lint"))
    assert out.returncode == 0, out.stderr
