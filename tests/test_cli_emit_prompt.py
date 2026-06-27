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
