import json, os, pathlib
import pytest
from gpu_agent.cli import main
from gpu_agent.gate import check_finding
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.assignment import load_assignment
from gpu_agent.pipeline import build_scorecard
from gpu_agent.registry.indicators import IndicatorRegistry

def test_level_c_recorded_extract_feeds_core(tmp_path):
    out = tmp_path / "findings.json"
    rc = main(["extract", "--docs", "fixtures/raw", "--as-of", "2026-06",
               "--captured-at", "2026-06-12T00:00:00Z",
               "--recorded", "fixtures/recorded/extract-nvda.json", "--out", str(out)])
    assert rc == 0
    raw = json.loads(out.read_text("utf-8"))
    findings = [Finding.model_validate(d) for d in raw]
    assert findings, "extraction produced no findings"
    # every extracted finding is gate-clean (Level C contract)
    for f in findings:
        assert check_finding(f) == []
    # and they flow into the existing core unchanged
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    ratings = {"momentum": DimensionRating(rating="Strong", direction="worsening",
        confidence=Confidence(level="high", basis="D2"), findingIds=[findings[0].id], rationale="r")}
    reg = IndicatorRegistry.load("registry/indicators.json")
    sc = build_scorecard(findings, ratings, {"momentum": 0.4}, a, "MVP via extraction.",
                         Confidence(level="medium", basis="level-c run"), reg)
    assert sc.dimensionRatings["momentum"].rating == "Strong"

@pytest.mark.skipif(os.environ.get("GPU_AGENT_LIVE_LLM") != "1",
                    reason="live LLM smoke disabled (set GPU_AGENT_LIVE_LLM=1)")
def test_live_smoke_real_backend():
    from gpu_agent.schema.raw_document import RawDocument
    from gpu_agent.extraction.extractor import extract_findings
    from gpu_agent.llm.factory import make_client
    doc = RawDocument.model_validate(json.loads(
        pathlib.Path("fixtures/raw/doc-nvda.json").read_text("utf-8")))
    client = make_client(os.environ.get("GPU_AGENT_LLM_BACKEND", "claude_code"))
    outcome = extract_findings(doc, client, as_of="2026-06",
                               captured_at="2026-06-12T00:00:00Z", extraction_model="live")
    for f in outcome.findings:
        assert check_finding(f) == []
