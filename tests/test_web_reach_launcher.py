import os
import pathlib
import subprocess
import sys
import pytest

SH = pathlib.Path("scripts/web-reach-ensure")
CMD = pathlib.Path("scripts/web-reach-ensure.cmd")


def test_launchers_exist():
    assert SH.exists(), "POSIX launcher missing"
    assert CMD.exists(), "Windows launcher missing"


def test_launchers_target_the_module_not_cli():
    # must invoke the stdlib-only module entry, never gpu_agent.cli (pydantic-heavy)
    for p in (SH, CMD):
        text = p.read_text(encoding="utf-8")
        assert "gpu_agent.web_reach_ensure" in text, f"{p} does not run the ensure module"
        assert "gpu_agent.cli" not in text, f"{p} must not import the heavy cli"


def test_launchers_prefer_venv_python():
    assert ".venv/bin/python" in SH.read_text(encoding="utf-8")
    assert ".venv\\Scripts\\python.exe" in CMD.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher runs on Windows only")
def test_windows_launcher_runs_check_only():
    r = subprocess.run([str(CMD), "--check-only", "--json"],
                       capture_output=True, text=True)
    # exit code may be 1 if tools not yet installed; it must still emit valid JSON
    assert "webReach" in r.stdout


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher runs on POSIX only")
def test_posix_launcher_runs_check_only():
    r = subprocess.run(["sh", str(SH), "--check-only", "--json"],
                       capture_output=True, text=True)
    assert "webReach" in r.stdout
