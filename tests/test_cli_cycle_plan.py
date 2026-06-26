import json, subprocess, sys

def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", "cycle-plan", *args],
                          capture_output=True, text=True)

def test_cycle_plan_category_emits_ready_json():
    out = _run("--scope", "category:chips.merchant-gpu")
    assert out.returncode == 0, out.stderr
    plan = json.loads(out.stdout)
    assert plan["scope"] == "category:chips.merchant-gpu"
    assert plan["entries"][0]["category_id"] == "chips.merchant-gpu"
    assert plan["entries"][0]["status"] == "ready"
    assert {s["tier"]: s["status"] for s in plan["stages"]} == {
        "category": "active", "layer": "deferred", "main": "deferred"}

def test_cycle_plan_layer_surfaces_skipped_on_stderr():
    out = _run("--scope", "layer:chips")
    assert out.returncode == 0, out.stderr
    assert "chips.hbm-memory" in out.stderr  # skipped category surfaced, not silent

def test_cycle_plan_writes_out_file(tmp_path):
    log = tmp_path / "cycle-log.json"
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode == 0, out.stderr
    written = json.loads(log.read_text("utf-8"))
    assert written["entries"][0]["category_id"] == "chips.merchant-gpu"

def test_cycle_plan_bad_scope_fails_loud():
    out = _run("--scope", "bogus")
    assert out.returncode != 0
    assert "bogus" in (out.stderr + out.stdout)
