import json, subprocess, sys


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def test_extract_emit_prompt_emits_canonical_bundle_no_llm():
    out = _run("extract", "--emit-prompt", "--docs", "fixtures/raw", "--as-of", "2026-06")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    # canonical extraction SYSTEM (defined once in extraction/prompt.py)
    assert "You extract demand/supply Findings" in bundle["system"]
    # the answer schema the subagent must match
    assert bundle["schema"]["title"] == "ExtractionResult"
    # one prompt per document, in load order; carries the canonical user-prompt shape
    assert [d["id"] for d in bundle["docs"]] == ["doc-nvda"]
    assert "Extract Findings about entity '" in bundle["docs"][0]["user"]
    assert "<document>" in bundle["docs"][0]["user"]


def _gated_findings(tmp_path):
    """Produce a gated findings file by replaying the committed extraction fixture through the gate."""
    findings = tmp_path / "findings.json"
    out = _run("extract", "--recorded", "fixtures/recorded/extract-nvda.json",
               "--docs", "fixtures/raw", "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--out", str(findings))
    assert out.returncode == 0, out.stderr
    return findings


def test_judge_emit_prompt_emits_canonical_bundle_no_llm(tmp_path):
    findings = _gated_findings(tmp_path)
    out = _run("judge", "--emit-prompt", "--findings", str(findings),
               "--category", "chips.merchant-gpu")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "assigning the six dimension ratings" in bundle["system"]
    assert bundle["schema"]["title"] == "JudgmentResult"
    assert "<briefing>" in bundle["user"]
    assert bundle["samples"] == 3


def test_emit_then_recorded_round_trips_through_gate_and_judge(tmp_path):
    # acceptance: an answer to the emitted prompt, fed via --recorded, gates + scores
    findings = _gated_findings(tmp_path)              # extract --recorded round-trips through the gate
    jdir = tmp_path / "judge"
    out = _run("judge", "--findings", str(findings),
               "--recorded", "fixtures/recorded/judge-nvda.json",
               "--category", "chips.merchant-gpu", "--out", str(jdir))
    assert out.returncode == 0, out.stderr
    ratings = json.loads((jdir / "ratings.json").read_text("utf-8"))
    assert ratings  # non-empty dimension ratings produced from the recorded answer


def test_judge_without_out_and_without_emit_prompt_fails_clean(tmp_path):
    findings = _gated_findings(tmp_path)
    out = _run("judge", "--findings", str(findings), "--category", "chips.merchant-gpu")
    assert out.returncode == 2, out.stderr        # clean argparse-style error, not a TypeError(exit 1)
    assert "--out is required" in out.stderr


def test_recorded_answer_must_be_array_of_serialized_strings(tmp_path):
    # Guards the emit->answer->recorded contract the run-cycle SKILL documents: the brain's answer
    # (and the committed fixtures) is a JSON array of STRINGS, each a serialized result object — the
    # shape RecordedClient replays. An array of bare OBJECTS (the wrong shape) must NOT be silently
    # accepted/scored; it is rejected non-zero. This is exactly what the live run produced and what the
    # SKILL's dispatch wording must instruct.
    import pathlib
    fixture = json.loads(pathlib.Path("fixtures/recorded/extract-nvda.json").read_text("utf-8"))
    assert all(isinstance(x, str) for x in fixture)   # the committed answer shape is array-of-strings

    good = tmp_path / "good.json"                      # correct shape -> gates cleanly
    good.write_text(json.dumps(fixture), "utf-8")
    ok = _run("extract", "--recorded", str(good), "--docs", "fixtures/raw", "--as-of", "2026-06",
              "--captured-at", "2026-06-12T00:00:00Z", "--out", str(tmp_path / "f_good.json"))
    assert ok.returncode == 0, ok.stderr

    bad = tmp_path / "bad.json"                        # array-of-objects -> rejected, never silently scored
    bad.write_text(json.dumps([json.loads(s) for s in fixture]), "utf-8")
    nok = _run("extract", "--recorded", str(bad), "--docs", "fixtures/raw", "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z", "--out", str(tmp_path / "f_bad.json"))
    assert nok.returncode != 0, "array-of-objects must not be accepted as a recorded answer"
