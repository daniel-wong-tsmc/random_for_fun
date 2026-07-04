import json
import types
import pytest
from gpu_agent import web_reach_ensure as wre


def _reg():
    return {"tools": [
        {"id": "toolA", "enabled": True,
         "healthCmd": {"windows": "hc-A", "macos": "hc-A", "linux": "hc-A"},
         "install": {"windows": ["i-A"], "macos": ["i-A"], "linux": ["i-A"]}},
        {"id": "toolB", "enabled": True,
         "healthCmd": {"windows": "hc-B", "macos": "hc-B", "linux": "hc-B"},
         "install": {"windows": ["i-B1", "i-B2"], "macos": ["i-B"], "linux": ["i-B"]}},
        {"id": "off", "enabled": False,
         "healthCmd": {"windows": "x", "macos": "x", "linux": "x"},
         "install": {"windows": ["x"], "macos": ["x"], "linux": ["x"]}},
    ]}


def _cp(returncode, stderr=""):
    return types.SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)


def test_healthy_tool_is_not_installed(monkeypatch):
    calls = []
    monkeypatch.setattr(wre, "_run", lambda cmd, timeout: (calls.append(cmd), _cp(0))[1])
    res = wre.ensure_tool(_reg()["tools"][0], "linux", log=lambda m: None)
    assert res == {"tool": "toolA", "status": "ok"}
    assert calls == ["hc-A"]  # only the health check ran, no install


def test_missing_tool_runs_install_cmds_in_order_then_rechecks(monkeypatch):
    calls = []
    # health fails first, install cmds succeed, health passes on recheck
    seq = {"hc-B": [1, 0]}
    def fake_run(cmd, timeout):
        calls.append(cmd)
        if cmd in seq:
            return _cp(seq[cmd].pop(0))
        return _cp(0)
    monkeypatch.setattr(wre, "_run", fake_run)
    res = wre.ensure_tool(_reg()["tools"][1], "windows", log=lambda m: None)
    assert res == {"tool": "toolB", "status": "installed-ok"}
    assert calls == ["hc-B", "i-B1", "i-B2", "hc-B"]  # health, both installs in order, recheck


def test_check_only_never_installs(monkeypatch):
    calls = []
    monkeypatch.setattr(wre, "_run", lambda cmd, timeout: (calls.append(cmd), _cp(1))[1])
    res = wre.ensure_tool(_reg()["tools"][0], "macos", check_only=True, log=lambda m: None)
    assert res == {"tool": "toolA", "status": "missing"}
    assert calls == ["hc-A"]  # no install attempted


def test_failed_install_reports_failed(monkeypatch):
    # health always fails AND the install command always fails -> status "failed"
    monkeypatch.setattr(wre, "_run", lambda cmd, timeout: _cp(1))
    res = wre.ensure_tool(_reg()["tools"][0], "linux", log=lambda m: None)
    assert res["tool"] == "toolA" and res["status"] == "failed"
    assert "detail" in res


def test_ensure_all_skips_disabled_and_uses_os(monkeypatch):
    monkeypatch.setattr(wre, "_run", lambda cmd, timeout: _cp(0))
    out = wre.ensure_all(_reg(), "linux", log=lambda m: None)
    assert [r["tool"] for r in out] == ["toolA", "toolB"]  # "off" skipped
    assert all(r["status"] == "ok" for r in out)


def test_detect_os_maps_platform(monkeypatch):
    monkeypatch.setattr(wre.platform, "system", lambda: "Windows")
    assert wre.detect_os() == "windows"
    monkeypatch.setattr(wre.platform, "system", lambda: "Darwin")
    assert wre.detect_os() == "macos"
    monkeypatch.setattr(wre.platform, "system", lambda: "Linux")
    assert wre.detect_os() == "linux"


def test_main_check_only_json_exit_code(monkeypatch, capsys, tmp_path):
    reg_file = tmp_path / "reg.json"
    reg_file.write_text(json.dumps(_reg()), encoding="utf-8")
    monkeypatch.setattr(wre, "REGISTRY_PATH", reg_file)
    monkeypatch.setattr(wre, "_run", lambda cmd, timeout: _cp(0))
    rc = wre.main(["--check-only", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(out["webReach"].keys()) == {"toolA", "toolB"}
    assert out["webReach"]["toolA"]["status"] == "ok"
