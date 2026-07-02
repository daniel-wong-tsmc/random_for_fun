"""Wave-2 Lane G robustness bundle: F41 (non-finite values, timestamp normalization,
wiki page id validation, crash-recoverable routing), F42 (config paths), F50 (run asOf
owns the scorecard label), F26-cli (de-GPU'd judge --category default)."""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys
from gpu_agent.cli import main


PIPELINE_ARGS = [
    "--docs", "fixtures/raw",
    "--assignment", "fixtures/asg.chips.merchant-gpu.json",
    "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
    "--recorded-extract", "fixtures/recorded/extract-nvda.json",
    "--recorded-judge", "fixtures/recorded/judge-nvda.json",
]


# --- Task 1: F50 — the run's asOf owns the scorecard label ---------------------------

def test_pipeline_asof_matches_assignment_no_override_note(tmp_path, capsys):
    store = tmp_path / "store"
    rc = main(["pipeline", *PIPELINE_ARGS, "--as-of", "2026-06", "--out", str(store)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "F50" not in err
    written = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert written, "pipeline wrote no scorecard at the fixture's own asOf"


def test_pipeline_divergent_asof_overrides_assignment_and_notes(tmp_path, capsys):
    store = tmp_path / "store"
    rc = main(["pipeline", *PIPELINE_ARGS, "--as-of", "2026-07", "--out", str(store)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "note: assignment asOf 2026-06 overridden by run asOf 2026-07 (F50)" in err
    written = list((store / "chips.merchant-gpu").glob("2026-07-v*.json"))
    assert written, "scorecard was not labeled with the RUN asOf"
    stale = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert not stale, "scorecard was mislabeled with the stale fixture-assignment asOf"
    sc = json.loads(written[0].read_text("utf-8"))
    assert sc["asOf"] == "2026-07"


# --- Task 2: F42 — hardcoded paths -> gpu_agent/config.py ----------------------------

def _run_py(code: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=full_env)


def test_config_defaults_match_prior_literals():
    out = _run_py("from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH; "
                  "print(REGISTRY_PATH); print(TAXONOMY_PATH)")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["registry/indicators.json", "docs/taxonomy.json"]


def test_config_registry_path_honors_env_override(tmp_path):
    out = _run_py("from gpu_agent.config import REGISTRY_PATH; print(REGISTRY_PATH)",
                  env={"GPU_AGENT_REGISTRY": str(tmp_path / "custom-indicators.json")})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == str(tmp_path / "custom-indicators.json")


def test_config_taxonomy_path_honors_env_override(tmp_path):
    out = _run_py("from gpu_agent.config import TAXONOMY_PATH; print(TAXONOMY_PATH)",
                  env={"GPU_AGENT_TAXONOMY": str(tmp_path / "custom-taxonomy.json")})
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == str(tmp_path / "custom-taxonomy.json")


def test_load_registry_honors_env_override_end_to_end(tmp_path):
    """`_load_registry()` (used by judge --emit-prompt, wiki-lint, wiki-lifecycle, pipeline,
    score/run) must actually resolve through gpu_agent.config, not a literal — proven by
    pointing GPU_AGENT_REGISTRY at a path that does not exist and observing the CLI fail
    instead of silently falling back to the real registry."""
    env = {**os.environ, "GPU_AGENT_REGISTRY": str(tmp_path / "missing-indicators.json")}
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "judge", "--emit-prompt",
         "--findings", "fixtures/golden/findings.json", "--category", "chips.merchant-gpu"],
        capture_output=True, text=True, env=env)
    assert out.returncode != 0, "judge --emit-prompt should fail: GPU_AGENT_REGISTRY points nowhere"


def test_load_registry_default_unaffected_when_env_unset():
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "judge", "--emit-prompt",
         "--findings", "fixtures/golden/findings.json", "--category", "chips.merchant-gpu"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert bundle["schema"]["title"] == "JudgmentResult"


def test_extractor_default_registry_load_honors_env_override(tmp_path):
    """extraction/extractor.py's default-load path (registry=None) also switches to config;
    proven the same way as the judge default-load path above, via the `extract` command
    which never passes registry/taxonomy explicitly."""
    env = {**os.environ, "GPU_AGENT_REGISTRY": str(tmp_path / "missing-indicators.json")}
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "extract", "--docs", "fixtures/raw",
         "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z",
         "--recorded", "fixtures/recorded/extract-nvda.json"],
        capture_output=True, text=True, env=env)
    assert out.returncode != 0, "extract should fail: GPU_AGENT_REGISTRY points nowhere"


def test_extractor_default_registry_load_unaffected_when_env_unset():
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "extract", "--docs", "fixtures/raw",
         "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z",
         "--recorded", "fixtures/recorded/extract-nvda.json"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
