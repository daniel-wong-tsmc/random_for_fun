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


def test_good_prose_passes(tmp_path):
    rec = _recorded_file(tmp_path, GOOD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec))
    assert out.returncode == 0, out.stderr


def test_bypass_flag(tmp_path):
    rec = _recorded_file(tmp_path, BAD_NARRATIVE)
    out = _run(*_judge_args(tmp_path, rec), "--no-voice-lint")
    assert out.returncode == 0, out.stderr
