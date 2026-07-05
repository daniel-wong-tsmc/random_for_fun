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

# F74 — the clobber scenario, pinned: cycle-plan must never destroy a finalized journal.

_ENRICHED_JOURNAL = {
    "scope": "category:chips.merchant-gpu",
    "asOf": "2026-07",
    "capturedAt": "2026-07-05T12:00:00Z",
    "entries": [{
        "category_id": "chips.merchant-gpu",
        "assignment_path": "fixtures\\asg.chips.merchant-gpu.json",
        "status": "ready",
        "scorecard": "store/chips.merchant-gpu/2026-07-v3.json",
        "gates": {"sufficiency": "bypassed - logged"},
    }],
    "stages": [{"tier": "category", "status": "active"}],
}

def test_cycle_plan_refuses_to_overwrite_enriched_journal(tmp_path):
    log = tmp_path / "cycle-log.json"
    log.write_text(json.dumps(_ENRICHED_JOURNAL, indent=2), encoding="utf-8")
    before = log.read_text("utf-8")
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode != 0
    assert log.read_text("utf-8") == before          # journal byte-identical
    assert "F74" in out.stderr                        # guard names its rule
    assert "journal" in out.stderr.lower()

def test_cycle_plan_overwrites_bare_plan(tmp_path):
    log = tmp_path / "cycle-log.json"
    bare = {"scope": "layer:chips",
            "entries": [{"category_id": "chips.hbm-memory", "assignment_path": None,
                         "status": "skipped-no-assignment"}],
            "stages": [{"tier": "category", "status": "active"}]}
    log.write_text(json.dumps(bare), encoding="utf-8")
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode == 0, out.stderr            # plans are regenerable — replan is fine
    written = json.loads(log.read_text("utf-8"))
    assert written["scope"] == "category:chips.merchant-gpu"

def test_cycle_plan_refuses_unparseable_out_file(tmp_path):
    log = tmp_path / "cycle-log.json"
    log.write_text("{not json", encoding="utf-8")
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode != 0
    assert log.read_text("utf-8") == "{not json"      # unknown content never destroyed
    assert "F74" in out.stderr

def test_cycle_plan_refuses_null_entries_cleanly(tmp_path):
    log = tmp_path / "cycle-log.json"
    log.write_text('{"scope": "x", "entries": null, "stages": []}', encoding="utf-8")
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode != 0
    assert "F74" in out.stderr                        # clean refusal, not a TypeError traceback
    assert "Traceback" not in out.stderr

def test_cycle_plan_refuses_directory_out_cleanly(tmp_path):
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(tmp_path))
    assert out.returncode != 0
    assert "F74" in out.stderr                        # clean refusal, not PermissionError
    assert "Traceback" not in out.stderr

def test_cycle_plan_overwrites_bom_bare_plan(tmp_path):
    log = tmp_path / "cycle-log.json"
    bare = {"scope": "layer:chips",
            "entries": [{"category_id": "chips.hbm-memory", "assignment_path": None,
                         "status": "skipped-no-assignment"}],
            "stages": [{"tier": "category", "status": "active"}]}
    log.write_text(json.dumps(bare), encoding="utf-8-sig")   # Windows editors add a BOM
    out = _run("--scope", "category:chips.merchant-gpu", "--out", str(log))
    assert out.returncode == 0, out.stderr            # a BOM does not make a plan a journal
    assert json.loads(log.read_text("utf-8"))["scope"] == "category:chips.merchant-gpu"
