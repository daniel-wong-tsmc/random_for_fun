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

REGISTRY_PATH = pathlib.Path("registry/web-reach-tools.json")

_HEALTH_TIMEOUT = 60  # health checks are cheap; cap them low


def _augment_path() -> None:
    # pipx installs its shims into ~/.local/bin, which is NOT on PATH on a pristine
    # machine. Prepend it to this process's PATH so subsequent same-run subprocess
    # calls (install recipes, recheck healthCmd) can find a just-installed shim
    # (e.g. `agent-reach`) even before the shell/profile has picked up `pipx ensurepath`.
    import os
    extra = os.path.expanduser(os.path.join("~", ".local", "bin"))
    cur = os.environ.get("PATH", "")
    parts = cur.split(os.pathsep)
    if extra and extra not in parts:
        os.environ["PATH"] = extra + os.pathsep + cur


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
    # encoding+errors: tool output can carry non-ASCII bytes (e.g. agent-reach's
    # localized doctor text); decode as UTF-8 and never crash on undecodable
    # bytes, so the reader thread can't die and drop the returncode (the Windows
    # cp1252 default raised UnicodeDecodeError on real install output).
    return subprocess.run(cmd, shell=True, timeout=timeout,
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


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
    _augment_path()
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

    registry = load_registry(REGISTRY_PATH)
    log = (lambda m: None) if args.json else print
    results = ensure_all(registry, check_only=args.check_only, timeout=args.timeout, log=log)
    if args.json:
        print(json.dumps({"webReach": {r["tool"]: r for r in results}}, indent=2))
    return 0 if all(r["status"] in ("ok", "installed-ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
