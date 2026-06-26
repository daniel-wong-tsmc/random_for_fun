import json, pathlib, subprocess, sys

def test_pipeline_rejects_unregistered_metric(tmp_path):
    asg = json.loads(pathlib.Path("fixtures/asg.chips.merchant-gpu.json").read_text("utf-8"))
    asg["metrics"] = asg["metrics"] + ["totallyMadeUp"]
    p = tmp_path / "asg.bad.json"
    p.write_text(json.dumps(asg), "utf-8")
    out = subprocess.run(
        [sys.executable, "-m", "gpu_agent.cli", "pipeline", "--docs", "fixtures/raw",
         "--assignment", str(p), "--as-of", "2026-06", "--captured-at", "2026-06-12T00:00:00Z",
         "--recorded-extract", "fixtures/recorded/extract-nvda.json",
         "--recorded-judge", "fixtures/recorded/judge-nvda.json", "--out", str(tmp_path / "store")],
        capture_output=True, text=True)
    assert out.returncode != 0
    assert "totallyMadeUp" in (out.stderr + out.stdout)
