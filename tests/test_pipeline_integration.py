import json, os, pathlib
import pytest
from gpu_agent.cli import main

def test_pipeline_extract_judge_score(tmp_path):
    store = tmp_path / "store"
    rc = main(["pipeline", "--docs", "fixtures/raw",
               "--assignment", "fixtures/asg.chips.merchant-gpu.json",
               "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z", "--samples", "3",
               "--recorded-extract", "fixtures/recorded/extract-nvda.json",
               "--recorded-judge", "fixtures/recorded/judge-nvda.json",
               "--out", str(store)])
    assert rc == 0
    written = list((store / "chips.merchant-gpu").glob("2026-06-v*.json"))
    assert written, "pipeline wrote no scorecard"
    sc = json.loads(written[0].read_text("utf-8"))
    assert sc["dimensionRatings"]["momentum"]["rating"] == "Strong"
    assert sc["narrative"].startswith("NVDA demand momentum")
    assert sc["demandSupply"]["anchors"]["momentum"] != 0

@pytest.mark.skipif(os.environ.get("GPU_AGENT_LIVE_LLM") != "1",
                    reason="live LLM smoke disabled (set GPU_AGENT_LIVE_LLM=1)")
def test_live_smoke_judge_real_backend():
    from gpu_agent.schema.finding import Finding
    from gpu_agent.judgment.judge import judge_findings
    from gpu_agent.llm.factory import make_client
    from gpu_agent.registry.indicators import IndicatorRegistry
    findings = [Finding.model_validate(d) for d in json.loads(
        pathlib.Path("fixtures/golden/findings.json").read_text("utf-8"))]
    client = make_client(os.environ.get("GPU_AGENT_LLM_BACKEND", "claude_code"))
    registry = IndicatorRegistry.load("registry/indicators.json")
    bundle = judge_findings(findings, client, registry, "chips.merchant-gpu", samples=1, model="claude-opus-4-8")
    assert bundle.ratings  # produced at least one gate-valid rating
