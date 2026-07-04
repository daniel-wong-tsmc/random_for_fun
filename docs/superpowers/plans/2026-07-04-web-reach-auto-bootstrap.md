# Web-Reach Auto-Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a fresh clone of this repo, run through Claude Code, auto-install and health-pass both web-reach tools (`agent-reach`, `last30days`) in free-core mode on Windows/macOS/Linux — every run, idempotently, with nothing installed ever committed.

**Architecture:** The registry (`registry/web-reach-tools.json`) carries per-OS `install` recipes + OS-keyed `healthCmd`. A stdlib-only engine (`gpu_agent/web_reach_ensure.py`, with its own `__main__`) reads the registry, health-checks each enabled tool, and installs any missing one. One cross-platform launcher (`scripts/web-reach-ensure[.cmd]`) resolves a Python and runs the engine module directly (so it works before `.venv`/pydantic exist). Two triggers call the launcher: the `gather-category` skill preamble (primary) and a committed `.claude/settings.json` SessionStart hook (backstop). A `gpu_agent.cli web-reach-ensure` subcommand delegates to the same engine for in-venv use.

**Tech Stack:** Python 3.11+ (stdlib `platform`/`subprocess`/`json`/`argparse` only for the engine), `pytest`, JSON registry, POSIX sh + Windows cmd launchers, Claude Code `settings.json` hooks.

## Global Constraints

- **Platform support:** Windows + macOS + Linux (verbatim per spec).
- **Engine is stdlib-only:** `gpu_agent/web_reach_ensure.py` imports NO third-party packages and does NOT import `gpu_agent.cli` (which pulls pydantic). It must run on a bare clone with only a system Python.
- **Idempotent, install-if-missing only:** never upgrade a healthy tool; never touch secrets; never fetch/install paywalled sources.
- **Logged, never silent** (charter Part 37): every check/install/skip emits a line; `--json` emits a machine-readable block.
- **Never blocks a run:** a failed/timed-out install is logged; callers continue on WebSearch/WebFetch. `web-reach-ensure` exits non-zero on any failure but callers treat that as non-fatal.
- **Nothing installed is committed:** installs go to pipx / a dedicated venv / the global skills dir / Node/gh/mcporter — never into the repo tree.
- **Free-core bar:** auto path needs no secrets; logged-in extras remain a documented optional per-machine step.
- **Install recipes are verify-on-real-machine:** concrete best-effort commands are given from the tools' own docs; Task 8 runs them for real on this Windows box and corrects the registry if reality differs.

---

### Task 1: Registry — per-OS `install` + OS-keyed `healthCmd`

**Files:**
- Modify: `registry/web-reach-tools.json` (both tool objects)
- Test: `tests/test_web_reach_registry.py` (add cases)

**Interfaces:**
- Produces: each `enabled` tool has `install: {windows:[str],macos:[str],linux:[str]}` (non-empty lists) and `healthCmd: {windows:str,macos:str,linux:str}`. Consumed by Task 2's engine.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_web_reach_registry.py`:

```python
OSES = ("windows", "macos", "linux")


def test_enabled_tools_have_per_os_install_recipes():
    for t in _load()["tools"]:
        if not t.get("enabled"):
            continue
        inst = t.get("install")
        assert isinstance(inst, dict), f"{t['id']} missing install object"
        for os_key in OSES:
            cmds = inst.get(os_key)
            assert isinstance(cmds, list) and cmds, f"{t['id']} install.{os_key} empty"
            assert all(isinstance(c, str) and c for c in cmds), f"{t['id']} install.{os_key} non-string"


def test_enabled_tools_have_per_os_healthcmd():
    for t in _load()["tools"]:
        if not t.get("enabled"):
            continue
        hc = t.get("healthCmd")
        assert isinstance(hc, dict), f"{t['id']} healthCmd must be OS-keyed object"
        for os_key in OSES:
            assert isinstance(hc.get(os_key), str) and hc[os_key], f"{t['id']} healthCmd.{os_key} empty"


def test_windows_healthcmd_avoids_store_alias_python3():
    # the 2026-07 root cause: bare `python3` on Windows hits the Store alias stub
    for t in _load()["tools"]:
        if not t.get("enabled"):
            continue
        win = t["healthCmd"]["windows"]
        assert "python3 " not in win and not win.startswith("python3"), \
            f"{t['id']} windows healthCmd uses bare python3 (Store-alias trap): {win}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -k "per_os or store_alias" -v`
Expected: FAIL (install object missing; healthCmd is a string).

- [ ] **Step 3: Edit `registry/web-reach-tools.json`**

For the `agent-reach` object, replace its `"healthCmd": "agent-reach doctor"` line with:

```json
      "healthCmd": {
        "windows": "agent-reach doctor",
        "macos": "agent-reach doctor",
        "linux": "agent-reach doctor"
      },
      "install": {
        "windows": [
          "py -3 -m pip install --user pipx",
          "py -3 -m pipx install https://github.com/Panniantong/agent-reach/archive/main.zip",
          "agent-reach install --env=auto"
        ],
        "macos": [
          "python3 -m pip install --user pipx || brew install pipx",
          "pipx ensurepath",
          "pipx install https://github.com/Panniantong/agent-reach/archive/main.zip",
          "agent-reach install --env=auto"
        ],
        "linux": [
          "python3 -m pip install --user pipx",
          "python3 -m pipx ensurepath",
          "pipx install https://github.com/Panniantong/agent-reach/archive/main.zip",
          "agent-reach install --env=auto"
        ]
      },
```

For the `last30days` object, replace its `"healthCmd": "python3 skills/last30days/scripts/last30days.py --preflight"` line with (a Python probe — cross-platform, checks the `skills` CLI's global list; Task 8 confirms/corrects the exact verb on a real machine):

```json
      "healthCmd": {
        "windows": "py -3 -c \"import subprocess,sys; r=subprocess.run(['npx','-y','skills','list','-g'],capture_output=True); sys.exit(0 if b'last30days' in r.stdout.lower() else 1)\"",
        "macos": "python3 -c \"import subprocess,sys; r=subprocess.run(['npx','-y','skills','list','-g'],capture_output=True); sys.exit(0 if b'last30days' in r.stdout.lower() else 1)\"",
        "linux": "python3 -c \"import subprocess,sys; r=subprocess.run(['npx','-y','skills','list','-g'],capture_output=True); sys.exit(0 if b'last30days' in r.stdout.lower() else 1)\""
      },
      "install": {
        "windows": ["npx -y skills add mvanhorn/last30days-skill -g"],
        "macos": ["npx -y skills add mvanhorn/last30days-skill -g"],
        "linux": ["npx -y skills add mvanhorn/last30days-skill -g"]
      },
```

Keep every other field (`id`, `enabled`, `role`, `repo`, `installDocUrl`, `invokeHint`, `capabilities`, `defaultTier`, `notes`) unchanged.

- [ ] **Step 4: Run the full registry test file to verify pass**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -v`
Expected: PASS (new cases pass; existing `test_enabled_tools_have_required_fields` still passes because a dict `healthCmd` is truthy).

- [ ] **Step 5: Commit**

```bash
git add registry/web-reach-tools.json tests/test_web_reach_registry.py
git commit -m "feat(web-reach): per-OS install recipes + OS-keyed healthCmd in registry"
```

---

### Task 2: Ensure engine — `gpu_agent/web_reach_ensure.py` (stdlib-only)

**Files:**
- Create: `gpu_agent/web_reach_ensure.py`
- Test: `tests/test_web_reach_ensure.py`

**Interfaces:**
- Consumes: registry shape from Task 1.
- Produces (imported by Task 3 CLI + Task 4 launcher):
  - `detect_os() -> str` → `"windows"|"macos"|"linux"`
  - `load_registry(path: pathlib.Path = REGISTRY_PATH) -> dict`
  - `health_ok(tool: dict, os_key: str, timeout: int = 60) -> bool`
  - `ensure_tool(tool: dict, os_key: str, *, check_only=False, timeout=600, log=print) -> dict` → `{"tool":str,"status":"ok"|"missing"|"installed-ok"|"failed","detail"?:str}`
  - `ensure_all(registry: dict, os_key: str | None = None, *, check_only=False, timeout=600, log=print) -> list[dict]`
  - `main(argv: list[str] | None = None) -> int` (own argparse; used by `python -m gpu_agent.web_reach_ensure`)
  - module-level `_run(cmd: str, timeout: int) -> subprocess.CompletedProcess` (monkeypatched in tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_web_reach_ensure.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_ensure.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.web_reach_ensure'`.

- [ ] **Step 3: Create `gpu_agent/web_reach_ensure.py`**

```python
"""Idempotent, cross-platform ensure-installed for the web-reach tools.

STDLIB ONLY. Must run on a bare clone (no .venv, no pydantic). Do NOT import
gpu_agent.cli or any third-party package here.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import platform
import subprocess
import sys

REGISTRY_PATH = pathlib.Path("registry/web-reach-tools.json")

_HEALTH_TIMEOUT = 60  # health checks are cheap; cap them low


def detect_os() -> str:
    s = platform.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "macos"
    return "linux"


def load_registry(path: pathlib.Path = REGISTRY_PATH) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _run(cmd: str, timeout: int) -> subprocess.CompletedProcess:
    # shell=True: registry commands may use the OS shell (cmd.exe on Windows,
    # /bin/sh on POSIX). Each OS's recipe is authored for its own shell.
    return subprocess.run(cmd, shell=True, timeout=timeout,
                          capture_output=True, text=True)


def health_ok(tool: dict, os_key: str, timeout: int = _HEALTH_TIMEOUT) -> bool:
    cmd = (tool.get("healthCmd") or {}).get(os_key)
    if not cmd:
        return False
    try:
        return _run(cmd, timeout).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ensure_tool(tool: dict, os_key: str, *, check_only: bool = False,
                timeout: int = 600, log=print) -> dict:
    tid = tool["id"]
    if health_ok(tool, os_key):
        log(f"web-reach: {tid} ok")
        return {"tool": tid, "status": "ok"}
    if check_only:
        log(f"web-reach: {tid} missing (check-only; not installing)")
        return {"tool": tid, "status": "missing"}
    cmds = (tool.get("install") or {}).get(os_key) or []
    if not cmds:
        log(f"web-reach: {tid} missing and no install recipe for {os_key}")
        return {"tool": tid, "status": "failed", "detail": f"no install recipe for {os_key}"}
    for c in cmds:
        log(f"web-reach: {tid} installing -> {c}")
        try:
            r = _run(c, timeout)
        except subprocess.TimeoutExpired:
            return {"tool": tid, "status": "failed", "detail": f"timeout: {c}"}
        except OSError as e:
            return {"tool": tid, "status": "failed", "detail": f"{c}: {e}"}
        if r.returncode != 0:
            tail = (r.stderr or "")[-500:]
            return {"tool": tid, "status": "failed",
                    "detail": f"install cmd failed ({r.returncode}): {c}\n{tail}"}
    if health_ok(tool, os_key):
        log(f"web-reach: {tid} installed-ok")
        return {"tool": tid, "status": "installed-ok"}
    return {"tool": tid, "status": "failed", "detail": "healthCmd still failing after install"}


def ensure_all(registry: dict, os_key: str | None = None, *, check_only: bool = False,
               timeout: int = 600, log=print) -> list[dict]:
    os_key = os_key or detect_os()
    results = []
    for tool in registry.get("tools", []):
        if not tool.get("enabled"):
            continue
        results.append(ensure_tool(tool, os_key, check_only=check_only,
                                    timeout=timeout, log=log))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="web-reach-ensure",
                                 description="Idempotently ensure web-reach tools are installed.")
    ap.add_argument("--check-only", action="store_true", help="health-check only; never install")
    ap.add_argument("--json", action="store_true", help="emit a machine-readable webReach block")
    ap.add_argument("--timeout", type=int, default=600, help="per-install-command timeout (s)")
    args = ap.parse_args(argv)

    registry = load_registry()
    log = (lambda m: None) if args.json else print
    results = ensure_all(registry, check_only=args.check_only, timeout=args.timeout, log=log)
    if args.json:
        print(json.dumps({"webReach": {r["tool"]: r for r in results}}, indent=2))
    return 0 if all(r["status"] in ("ok", "installed-ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_ensure.py -v`
Expected: PASS (all 7 tests).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/web_reach_ensure.py tests/test_web_reach_ensure.py
git commit -m "feat(web-reach): stdlib-only idempotent ensure engine + __main__"
```

---

### Task 3: CLI subcommand `web-reach-ensure` (delegates to the engine)

**Files:**
- Modify: `gpu_agent/cli.py` (add parser + handler + dispatch)
- Test: `tests/test_web_reach_ensure.py` (add a CLI-level case)

**Interfaces:**
- Consumes: `web_reach_ensure.load_registry` / `ensure_all` from Task 2.
- Produces: `gpu-agent web-reach-ensure [--check-only] [--json] [--timeout N]` runnable once a `.venv` exists.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_web_reach_ensure.py`:

```python
def test_cli_subcommand_delegates(monkeypatch, capsys, tmp_path):
    from gpu_agent import cli, web_reach_ensure as w
    reg_file = tmp_path / "reg.json"
    reg_file.write_text(json.dumps(_reg()), encoding="utf-8")
    monkeypatch.setattr(w, "REGISTRY_PATH", reg_file)
    monkeypatch.setattr(w, "_run", lambda cmd, timeout: _cp(0))
    rc = cli.main(["web-reach-ensure", "--check-only", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(out["webReach"].keys()) == {"toolA", "toolB"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_ensure.py::test_cli_subcommand_delegates -v`
Expected: FAIL with `argument cmd: invalid choice: 'web-reach-ensure'`.

- [ ] **Step 3: Add parser, handler, dispatch to `gpu_agent/cli.py`**

Add the handler near the other `_xxx(args)` helpers (module level, above `def main`):

```python
def _web_reach_ensure(args) -> int:
    from gpu_agent.web_reach_ensure import load_registry, ensure_all
    registry = load_registry()
    log = (lambda m: None) if args.json else print
    results = ensure_all(registry, check_only=args.check_only, timeout=args.timeout, log=log)
    if args.json:
        print(json.dumps({"webReach": {r["tool"]: r for r in results}}, indent=2))
    return 0 if all(r["status"] in ("ok", "installed-ok") for r in results) else 1
```

Add the subparser inside `main()` alongside the other `sub.add_parser(...)` blocks (e.g. after the `report` parser at `gpu_agent/cli.py:970`):

```python
    wre = sub.add_parser("web-reach-ensure",
                         help="idempotently ensure web-reach tools are installed")
    wre.add_argument("--check-only", action="store_true")
    wre.add_argument("--json", action="store_true")
    wre.add_argument("--timeout", type=int, default=600)
```

Add the dispatch line in `main()` alongside the other `if args.cmd == ...` blocks (e.g. right before the `if args.cmd == "report":` line at `gpu_agent/cli.py:1037`):

```python
    if args.cmd == "web-reach-ensure":
        return _web_reach_ensure(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_ensure.py -v`
Expected: PASS (all cases, including the new CLI one).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/cli.py tests/test_web_reach_ensure.py
git commit -m "feat(web-reach): gpu-agent web-reach-ensure CLI subcommand"
```

---

### Task 4: Cross-platform launcher scripts

**Files:**
- Create: `scripts/web-reach-ensure` (POSIX sh)
- Create: `scripts/web-reach-ensure.cmd` (Windows)
- Test: `tests/test_web_reach_launcher.py`

**Interfaces:**
- Produces: two launcher entry points that resolve a Python (prefer `.venv`, else system) and run `python -m gpu_agent.web_reach_ensure "$@"` from the repo root. Called by Tasks 5 and 6. Uses the module entry (NOT `gpu_agent.cli`) so it stays stdlib-only / bare-clone-safe.

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_reach_launcher.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_launcher.py -v`
Expected: FAIL (launcher files do not exist).

- [ ] **Step 3: Create `scripts/web-reach-ensure` (POSIX sh)**

```sh
#!/bin/sh
# Resolve a Python and run the stdlib-only web-reach ensure engine from repo root.
# Bare-clone safe: uses the module entry, not gpu_agent.cli.
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "web-reach-ensure: no Python found on PATH" >&2
  exit 1
fi
cd "$DIR"
exec "$PY" -m gpu_agent.web_reach_ensure "$@"
```

- [ ] **Step 4: Create `scripts/web-reach-ensure.cmd` (Windows)**

```bat
@echo off
setlocal
set "DIR=%~dp0.."
set "PY="
if exist "%DIR%\.venv\Scripts\python.exe" (
  set "PY=%DIR%\.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo web-reach-ensure: no Python found on PATH 1>&2
  exit /b 1
)
pushd "%DIR%"
%PY% -m gpu_agent.web_reach_ensure %*
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
```

- [ ] **Step 5: Make the POSIX launcher executable, run tests**

```bash
git update-index --chmod=+x scripts/web-reach-ensure 2>/dev/null || chmod +x scripts/web-reach-ensure
```

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_launcher.py -v`
Expected: PASS (on Windows: existence + content + the Windows run case; POSIX run case skipped).

- [ ] **Step 6: Commit**

```bash
git add scripts/web-reach-ensure scripts/web-reach-ensure.cmd tests/test_web_reach_launcher.py
git commit -m "feat(web-reach): cross-platform ensure launcher scripts"
```

---

### Task 5: Wire the gather-category preamble (run-flow trigger)

**Files:**
- Modify: `.claude/skills/gather-category/SKILL.md` (web-reach preamble)
- Test: `tests/test_web_reach_registry.py` (add wiring assertion)

**Interfaces:**
- Consumes: the launcher from Task 4.
- Produces: the preamble instructs the operator to run the launcher (ensure) before health-check.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_web_reach_registry.py`:

```python
def test_gather_preamble_runs_ensure_before_healthcheck():
    text = SKILL.read_text(encoding="utf-8")
    assert "scripts/web-reach-ensure" in text, "preamble must call the ensure launcher"
    assert "ensure-installed" in text or "ensure installed" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py::test_gather_preamble_runs_ensure_before_healthcheck -v`
Expected: FAIL.

- [ ] **Step 3: Edit the preamble in `.claude/skills/gather-category/SKILL.md`**

In the `### Preamble: web-reach health check` section, insert this as the first action (before "Read `registry/web-reach-tools.json`"):

```markdown
- **Ensure-installed first (idempotent).** Before health-checking, run the committed launcher
  so a fresh machine self-bootstraps the tools:
  - POSIX: `sh scripts/web-reach-ensure --json`
  - Windows: `scripts\web-reach-ensure.cmd --json`
  It health-checks each enabled tool and installs any that are missing (no-op when already
  healthy; first run on a fresh machine takes a few minutes). Fold its `webReach` JSON block
  straight into `gather-log.json::webReach`. A tool it reports `failed` is logged and named in
  the gap/skip report — the run continues on WebSearch/WebFetch (doctrine unchanged). It never
  upgrades a healthy tool and never touches secrets.
```

- [ ] **Step 4: Run the registry test file to verify pass**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -v`
Expected: PASS (new assertion + all existing wiring assertions).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/gather-category/SKILL.md tests/test_web_reach_registry.py
git commit -m "feat(web-reach): gather preamble ensures tools before health-check"
```

---

### Task 6: SessionStart hook (backstop trigger)

**Files:**
- Create: `.claude/settings.json`
- Test: `tests/test_web_reach_hook.py`

**Interfaces:**
- Consumes: the launcher from Task 4.
- Produces: a committed Claude Code SessionStart hook that runs the launcher when a session opens in the repo.

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_reach_hook.py`:

```python
import json
import pathlib

SETTINGS = pathlib.Path(".claude/settings.json")


def test_settings_parses():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_sessionstart_hook_runs_the_launcher():
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    ss = hooks.get("SessionStart")
    assert ss, "no SessionStart hook configured"
    blob = json.dumps(ss)
    assert "web-reach-ensure" in blob, "SessionStart hook must call the ensure launcher"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_hook.py -v`
Expected: FAIL (`.claude/settings.json` does not exist).

- [ ] **Step 3: Create `.claude/settings.json`**

The hook runs a tiny shell snippet that picks the OS-appropriate launcher. It runs a full ensure (not `--check-only`) so a fresh machine self-installs on first session; subsequent sessions are an instant no-op. Runs from the project root (Claude Code sets cwd to the project dir).

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "if [ -f scripts/web-reach-ensure ]; then sh scripts/web-reach-ensure --json || true; else cmd //c scripts\\web-reach-ensure.cmd --json; fi"
          }
        ]
      }
    ]
  }
}
```

Note: Claude Code runs hook commands through the platform shell; the `if [ -f … ]` form works under Git Bash / sh on Windows too (the environment this repo runs in). Task 8 confirms the hook fires and does not error on this machine; if the Windows shell differs, split into an OS-specific command there.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_hook.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/settings.json tests/test_web_reach_hook.py
git commit -m "feat(web-reach): SessionStart hook auto-bootstraps tools on session open"
```

---

### Task 7: Doctrine + docs flip

**Files:**
- Modify: `docs/web-reach.md`
- Modify: `docs/agent-swarm-charter.md` (Part 37 subsection)
- Modify: `readme.md`
- Test: `tests/test_web_reach_registry.py` (doc/charter assertions)

**Interfaces:**
- No code interface; documents the new "ensure-installed idempotently at run start" doctrine.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_web_reach_registry.py`:

```python
def test_doc_documents_auto_bootstrap():
    text = DOC.read_text(encoding="utf-8")
    assert "web-reach-ensure" in text
    assert "idempotent" in text.lower()
    # the old "never installs mid-cycle" line must be gone / superseded
    assert "never installs mid-cycle" not in text


def test_charter_reflects_ensure_doctrine():
    text = CHARTER.read_text(encoding="utf-8")
    assert "ensure-installed" in text or "ensure installed" in text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -k "auto_bootstrap or ensure_doctrine" -v`
Expected: FAIL.

- [ ] **Step 3: Edit `docs/web-reach.md`**

Replace the `## One-time bootstrap (per machine)` section (and its steps) with:

```markdown
## Automatic bootstrap (idempotent, every run)
Web-reach tools are installed automatically — no manual per-machine ritual. The committed
launcher `scripts/web-reach-ensure` (`.cmd` on Windows) runs the stdlib-only
`gpu_agent.web_reach_ensure` engine, which reads this registry, health-checks each enabled
tool, and installs any that are missing using the registry's per-OS `install` recipes. It is
idempotent: a no-op (sub-second) when tools are healthy, a full install (a few minutes) only on
a fresh machine. It never upgrades a healthy tool and never touches secrets.

Two triggers call the launcher (both committed, both reproducible):
- the `gather-category` web-reach preamble, at the start of every agent run (primary);
- a `.claude/settings.json` SessionStart hook, when a session opens in the repo (backstop).

Nothing installed is committed — installs land in pipx / a dedicated venv / the global skills
dir / Node/gh/mcporter, per the registry recipes. Run it by hand any time with
`gpu-agent web-reach-ensure` (once a `.venv` exists) or `scripts/web-reach-ensure`.

Platform note: the Windows path is verified on real hardware; the macOS/Linux recipes are
authored from each tool's install doc and unit-tested (logic/order) but not yet run on those
OSes — the first mac/Linux operator should confirm and adjust the registry `install`/`healthCmd`
if reality differs.

## Optional per-machine secrets (not reproduced automatically)
Logged-in capabilities need per-user secrets that cannot be committed: agent-reach
(Twitter/Xiaohongshu cookies, optional Groq key), last30days (X via browser cookies; optional
Brave/Perplexity/ScrapeCreators keys). Set these up per machine following each tool's docs; their
absence just shows that capability unhealthy — logged, never fatal. Free-core capability works
without any of them.
```

Then find the line `it reads the registry and runs each enabled tool's healthCmd ... It never installs mid-cycle.` in the `## Health check (every run)` section and change `It never installs mid-cycle.` to `It ensures each tool is installed first (idempotent), then health-checks; it never upgrades a healthy tool mid-run.`

- [ ] **Step 4: Edit `docs/agent-swarm-charter.md` (Part 37)**

Find the Part 37 sentence stating web-reach tools are never installed mid-cycle (the "logged, never silent / never install" doctrine) and update it to read:

```markdown
Web-reach tools are **ensure-installed idempotently at run start** (the committed
`web-reach-ensure` launcher, called by the gather preamble and a SessionStart hook): install
once per machine, no-op thereafter, never upgrade a healthy tool mid-run. A tool that still
fails after an install attempt is logged and named in the gap/skip report; the run continues on
the built-ins (logged, never silent).
```

- [ ] **Step 5: Edit `readme.md`**

Add one line under the setup/usage section:

```markdown
- Web-reach tools (`agent-reach`, `last30days`) auto-install on first run via
  `scripts/web-reach-ensure` (idempotent, cross-platform); see `docs/web-reach.md`.
```

- [ ] **Step 6: Run the registry test file to verify pass**

Run: `.venv/Scripts/python -m pytest tests/test_web_reach_registry.py -v`
Expected: PASS (new doc/charter assertions + all pre-existing ones, e.g. "complementary, never a replacement" still present in the charter).

- [ ] **Step 7: Commit**

```bash
git add docs/web-reach.md docs/agent-swarm-charter.md readme.md tests/test_web_reach_registry.py
git commit -m "docs(web-reach): flip doctrine to ensure-installed idempotently at run start"
```

---

### Task 8: End-to-end verification on this Windows machine + full suite

**Files:**
- Modify (only if reality differs): `registry/web-reach-tools.json`
- No new test files; runs the whole suite + real installs.

**Interfaces:** none — this is the acceptance gate.

- [ ] **Step 1: Run the full test suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: PASS (baseline was 927 passed / 3 skipped before this work; expect that plus the new web-reach tests, 0 failures).

- [ ] **Step 2: Real ensure — check-only first (no install)**

Run: `scripts\web-reach-ensure.cmd --check-only --json`
Expected: JSON `webReach` block with both tools `missing` (they aren't installed yet), exit code 1. Confirms the launcher + engine + registry wire end-to-end on Windows.

- [ ] **Step 3: Real ensure — full install on this machine**

Run: `scripts\web-reach-ensure.cmd --json`
Expected: streamed install logs, then a `webReach` block with `agent-reach` and `last30days` at `installed-ok` (or `ok`). This actually installs the tools on this box (the parity the user asked for). If a command fails, read the error, correct that OS's recipe or `healthCmd` in `registry/web-reach-tools.json` (especially the `last30days` `skills list` verb / global path and any `pipx ensurepath` PATH-refresh needs), re-run tests (Task 1), and retry. Log any correction in the commit.

- [ ] **Step 4: Idempotency check — run again**

Run: `scripts\web-reach-ensure.cmd --json`
Expected: both tools `ok` in well under a second, no install commands run.

- [ ] **Step 5: Confirm the gather preamble health-check now passes**

Run: `.venv/Scripts/python -m gpu_agent.cli web-reach-ensure --check-only --json`
Expected: both tools `ok`, exit code 0 — i.e. a subsequent `gather-category` run would log `webReach: {agent-reach: ok, last30days: ok}` instead of `missing`.

- [ ] **Step 6: Commit any registry corrections + a short verification note**

```bash
git add registry/web-reach-tools.json
git commit -m "fix(web-reach): correct install recipes verified on Windows (if any)"
```

(If Step 3 needed no corrections, skip the commit and note "recipes verified as-authored on Windows" in the final report.)

---

## Self-Review

**Spec coverage** — every spec section maps to a task:
- Registry install source-of-truth → Task 1.
- Stdlib-only ensure engine + flags → Task 2 (engine) + Task 3 (CLI flags).
- Cross-platform launcher (bare-clone-safe, module entry) → Task 4.
- Run-flow trigger (gather preamble) → Task 5.
- SessionStart hook → Task 6.
- Doctrine flip + docs (web-reach.md, charter Part 37, readme) → Task 7.
- Tests (registry + ensure) → Tasks 1, 2, 3, 4, 6 (+ registry-wiring in 5, 7).
- Windows-verified / mac-linux-by-reading → Task 8 + the platform note committed in Task 7.
- "Nothing installed is committed" → recipes install to external locations; `.gitignore` already excludes `.venv`; no task adds installed artifacts to the tree.

**Placeholder scan** — no "TBD/TODO"; the only "confirm on real machine" is Task 8's explicit verify-and-correct step for third-party install recipes (inherent to installers, not a lazy gap); all code/JSON/shell is shown in full.

**Type consistency** — `ensure_tool`/`ensure_all`/`health_ok`/`detect_os`/`main`/`_run` names and the status strings `ok|missing|installed-ok|failed` are used identically across the engine (Task 2), CLI (Task 3), and tests. The launcher and both triggers all target `gpu_agent.web_reach_ensure` (module), never `gpu_agent.cli`, consistent with the stdlib-only constraint.
