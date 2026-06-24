import json, pathlib, argparse
from gpu_agent.cli import main, _build

ASSIGN = "fixtures/asg.chips.merchant-gpu.json"

def _clean_finding(fid="x-1"):
    return {"id": fid, "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
            "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
            "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
            "indicatorId": "D2", "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
            "magnitude": 2, "entity": "E", "observedAt": "2026-06",
            "capturedAt": "2026-06-12T00:00:00Z"}

def test_judge_writes_three_files(tmp_path):
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps([_clean_finding()]), "utf-8")
    judgment = json.dumps({"dimensions": {"momentum": {"rating": "Strong", "direction": "steady",
        "findingIds": ["x-1"], "rationale": "r"}}, "narrative": "judged narrative"})
    recorded = tmp_path / "rec.json"
    recorded.write_text(json.dumps([judgment] * 3), "utf-8")
    out = tmp_path / "bundle"
    rc = main(["judge", "--findings", str(findings), "--out", str(out),
               "--samples", "3", "--recorded", str(recorded)])
    assert rc == 0
    ratings = json.loads((out / "ratings.json").read_text("utf-8"))
    assert ratings["momentum"]["rating"] == "Strong"
    assert json.loads((out / "anchors.json").read_text("utf-8"))["momentum"] != 0
    assert json.loads((out / "narrative.json").read_text("utf-8"))["narrative"] == "judged narrative"

def test_build_reads_narrative_json_when_present(tmp_path):
    (tmp_path / "findings.json").write_text(json.dumps([_clean_finding()]), "utf-8")
    (tmp_path / "ratings.json").write_text(json.dumps({"momentum": {"rating": "Strong",
        "direction": "steady", "confidence": {"level": "high", "basis": "b"},
        "findingIds": ["x-1"], "rationale": "r"}}), "utf-8")
    (tmp_path / "anchors.json").write_text(json.dumps({"momentum": 0.5}), "utf-8")
    (tmp_path / "narrative.json").write_text(json.dumps({"narrative": "judged narrative",
        "confidence": {"level": "high", "basis": "3 samples"}}), "utf-8")
    sc = _build(argparse.Namespace(assignment=ASSIGN, fixtures=str(tmp_path)))
    assert sc.narrative == "judged narrative"
    assert sc.confidence.level == "high"

def test_build_falls_back_without_narrative_json():
    sc = _build(argparse.Namespace(assignment=ASSIGN, fixtures="fixtures/golden"))
    assert sc.narrative == "MVP scorecard."
    assert sc.confidence.basis == "fixture run"
