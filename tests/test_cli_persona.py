"""F26 controller wiring: the persona threads from the CLI into the emitted system prompts
and from the assignment into the live judge path (the skills' emit->recorded flow only ever
consumes the EMITTED system, so these pins cover the real seam)."""
import json
import subprocess
import sys

PY = sys.executable


def _run(argv):
    return subprocess.run([PY, "-m", "gpu_agent.cli", *argv], capture_output=True, text=True)


def test_extract_emit_prompt_default_persona_is_gpu():
    r = _run(["extract", "--emit-prompt", "--docs", "fixtures/raw", "--as-of", "2026-06"])
    assert r.returncode == 0
    bundle = json.loads(r.stdout)
    assert "GPU market analyst" in bundle["system"]


def test_extract_emit_prompt_persona_flag_swaps_the_analyst():
    r = _run(["extract", "--emit-prompt", "--docs", "fixtures/raw", "--as-of", "2026-06",
              "--persona", "frontier AI model market"])
    assert r.returncode == 0
    bundle = json.loads(r.stdout)
    assert "frontier AI model market analyst" in bundle["system"]
    assert "GPU market analyst" not in bundle["system"]


def test_judge_emit_prompt_persona_flag_swaps_the_analyst():
    r = _run(["judge", "--emit-prompt", "--findings", "fixtures/golden/findings.json",
              "--category", "chips.merchant-gpu", "--persona", "frontier AI model market"])
    assert r.returncode == 0
    bundle = json.loads(r.stdout)
    assert "frontier AI model market analyst" in bundle["system"]
    assert "GPU market analyst" not in bundle["system"]


def test_pipeline_threads_assignment_persona_into_judge():
    # the frontier assignment carries personaLabel; _pipeline passes it to judge_findings.
    # Pin at the source level (no live run needed): the wiring line exists and uses a.personaLabel.
    import inspect
    from gpu_agent import cli
    src = inspect.getsource(cli._pipeline)
    assert "persona=a.personaLabel" in src
