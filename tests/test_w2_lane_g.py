"""Wave-2 Lane G robustness bundle: F41 (non-finite values, timestamp normalization,
wiki page id validation, crash-recoverable routing), F42 (config paths), F50 (run asOf
owns the scorecard label), F26-cli (de-GPU'd judge --category default)."""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys
import pytest
from gpu_agent.cli import main


PIPELINE_ARGS = [
    "--docs", "fixtures/raw",
    "--assignment", "fixtures/asg.chips.merchant-gpu.json",
    "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
    "--recorded-extract", "fixtures/recorded/extract-nvda.json",
    "--recorded-judge", "fixtures/recorded/judge-nvda.json", "--no-voice-lint",
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


# --- Task 4: F41b — wiki page id validation + crash-recoverable routing --------------

from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _wiki_store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _finding(fid, entity, statement="s", **over):
    data = dict(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")
    data.update(over)
    return Finding(**data)


def test_page_path_rejects_path_escape_on_get(tmp_path):
    ws = _wiki_store(tmp_path)
    with pytest.raises(ValueError):
        ws.get_page("entity:../escape")


def test_page_path_rejects_path_escape_on_create(tmp_path):
    ws = _wiki_store(tmp_path)
    with pytest.raises(ValueError):
        ws.create_page("entity:../x", "entity", "X", as_of="2026-06-26")


def test_page_path_rejects_unknown_type(tmp_path):
    ws = _wiki_store(tmp_path)
    with pytest.raises(ValueError):
        ws.get_page("bogus:nvidia")


def test_page_path_rejects_uppercase_slug(tmp_path):
    ws = _wiki_store(tmp_path)
    with pytest.raises(ValueError):
        ws.get_page("entity:NVIDIA")


def test_page_path_happy_path_ids_unaffected(tmp_path):
    ws = _wiki_store(tmp_path)
    ws.create_page("entity:nvidia", "entity", "NVIDIA", as_of="2026-06-26")
    assert ws.get_page("entity:nvidia").title == "NVIDIA"
    ws.create_page("theme:cowos-capacity", "theme", "CoWoS", as_of="2026-06-26")
    assert ws.get_page("theme:cowos-capacity").title == "CoWoS"


def test_route_findings_crash_recoverable_and_idempotent_on_retry(tmp_path):
    ws = _wiki_store(tmp_path)
    # Pre-existing finding "f-3" under a DIFFERENT statement, simulating an id already
    # claimed (elsewhere / an earlier cycle) with different content.
    ws.findings.append(_finding("f-3", "NVDA", statement="original content"))

    f1 = _finding("f-1", "NVDA", statement="finding one")
    f2 = _finding("f-2", "AMD", statement="finding two")
    f3_colliding = _finding("f-3", "NVDA", statement="COLLIDING content")

    with pytest.raises(ValueError):
        route_findings(ws, [f1, f2, f3_colliding], as_of="2026-06-28")

    # findings 1-2 are durably routed even though the batch blew up on finding 3
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1"}
    assert {o.findingId for o in ws.observations("entity:amd")} == {"f-2"}
    n_events_after_crash = len(ws.log.read())

    # a re-run with finding 3 corrected (matching the pre-existing content) converges:
    # no exception, no duplicate observations for f-1/f-2, and f-3 now routes cleanly.
    f3_fixed = _finding("f-3", "NVDA", statement="original content")
    touched = route_findings(ws, [f1, f2, f3_fixed], as_of="2026-06-28")
    assert touched == ["entity:amd", "entity:nvidia"]
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1", "f-3"}
    assert {o.findingId for o in ws.observations("entity:amd")} == {"f-2"}
    # exactly one new event landed (append-observation for f-3); f-1/f-2 were no-ops
    assert len(ws.log.read()) == n_events_after_crash + 1


# --- Task 5: F26 (cli half) — de-GPU'd judge --category default ----------------------

def test_judge_without_category_is_a_clean_usage_error(tmp_path):
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps([{
        "id": "x-1", "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
        "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
        "evidence": [{"source": "S", "url": "u", "date": "2026-06-01", "excerpt": "e",
                      "tier": "primary"}],
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
        "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "E", "observedAt": "2026-06-01",
        "capturedAt": "2026-06-12T00:00:00Z",
    }]), "utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "judge", "--findings", str(findings),
         "--out", str(tmp_path / "jdg"), "--samples", "3"],
        capture_output=True, text=True)
    assert out.returncode == 2, out.stderr   # argparse usage error: missing required --category
    assert "--category" in out.stderr
