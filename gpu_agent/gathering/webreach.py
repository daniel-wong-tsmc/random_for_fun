from __future__ import annotations
import json
import pathlib
import re
import subprocess
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel

from gpu_agent.web_reach_ensure import detect_os

PAYWALLED_REGISTRY = pathlib.Path("registry/paywalled-domains.json")

_TOOL_VERSION_TIMEOUT = 30  # health-check-style probe; keep it snappy
_SLUG_MAX_LEN = 80

# Anything outside this set is stripped from a result-file slug. This is the last
# line of defense against path traversal: even if a hostile `target` (attacker-
# controlled web content) contains "/", "\", "..", drive letters, or shell/URL
# metacharacters, the derived filename can never contain a path separator.
_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")


class FetchRequest(BaseModel):
    toolId: str
    verb: str
    target: str
    outName: Optional[str] = None


def load_refused_domains(path: pathlib.Path = PAYWALLED_REGISTRY) -> set[str]:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return {d.lower() for d in data["domains"]}


def _tool_entry(registry: dict, tool_id: str) -> dict | None:
    for t in registry["tools"]:
        if t["id"] == tool_id and t.get("enabled"):
            return t
    return None


def validate_request(req: FetchRequest, registry: dict,
                     refused_domains: set[str]) -> str | None:
    tool = _tool_entry(registry, req.toolId)
    if tool is None:
        return f"unknown tool: {req.toolId}"
    verbs = tool.get("fetchVerbs", {})
    if req.verb not in verbs:
        return f"unknown verb for {req.toolId}: {req.verb}"
    if verbs[req.verb]["kind"] == "url":
        parsed = urlparse(req.target)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return f"refused scheme/shape: {req.target!r} (http/https only)"
        host = parsed.hostname
        if not host:
            return f"refused scheme/shape: {req.target!r} (unparseable host)"
        for dom in refused_domains:
            if host == dom or host.endswith("." + dom):
                return f"paywalled/licensed domain refused: {host} (Part 22)"
    return None


def build_argv(tool: dict, req: FetchRequest) -> list[str]:
    template = tool["fetchVerbs"][req.verb]["argv"]
    return [req.target if slot == "{target}" else slot for slot in template]


def _sanitize_slug(text: str, max_len: int = _SLUG_MAX_LEN) -> str:
    """Render arbitrary (attacker-controlled) text into a single safe filename
    component. Path separators, drive letters/colons, and ".." sequences are
    neutralized FIRST, then anything left outside [A-Za-z0-9._-] is stripped —
    the result never contains a character capable of leaving the current
    directory component."""
    s = text.replace("\\", "_").replace("/", "_").replace(":", "_")
    s = _UNSAFE_CHARS_RE.sub("_", s)
    while ".." in s:
        s = s.replace("..", "_")
    s = s.strip("._") or "x"
    return s[:max_len] or "x"


def _safe_result_path(out_dir: pathlib.Path, seq: int, tool_id: str, target: str) -> pathlib.Path:
    """Build `<seq>-<toolId>-<slug>.txt` strictly inside out_dir. Neither the
    request's `outName` nor the raw `target` is ever used as a path — only a
    sanitized slug derived from `target` (see _sanitize_slug). A resolve()
    check is a second, independent guarantee the file cannot land outside
    out_dir even if the sanitizer above were ever buggy."""
    tool_slug = _sanitize_slug(tool_id, max_len=40)
    target_slug = _sanitize_slug(target)
    name = f"{seq}-{tool_slug}-{target_slug}.txt"
    path = out_dir / name
    out_resolved = out_dir.resolve()
    if path.resolve().parent != out_resolved:   # pragma: no cover - defense in depth
        path = out_dir / f"{seq}.txt"
    return path


def _tool_version(tool: dict, os_key: str, timeout: int = _TOOL_VERSION_TIMEOUT) -> str:
    cmd = (tool.get("healthCmd") or {}).get(os_key)
    if not cmd:
        return "unknown"
    try:
        cp = subprocess.run(cmd, shell=True, timeout=timeout, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    except (subprocess.TimeoutExpired, OSError):
        return "unknown"
    if cp.returncode != 0:
        return "unknown"
    first_line = (cp.stdout or "").strip().splitlines()
    return first_line[0].strip() if first_line and first_line[0].strip() else "unknown"


def run_requests(requests_path, out_dir, registry: dict, refused_domains: set[str],
                 timeout: int = 120) -> dict:
    """Read a JSON array of FetchRequest objects from requests_path, validate each
    (BEFORE building/executing anything), execute the allowed ones as argv arrays
    (shell=False), save stdout to a sanitized-path result file, and write/return a
    result manifest. One request's failure/timeout never aborts the batch."""
    requests_path = pathlib.Path(requests_path)
    raw = json.loads(requests_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(
            f"requests file must contain a JSON array, got {type(raw).__name__}: {requests_path}")
    reqs = [FetchRequest.model_validate(r) for r in raw]

    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    used_tool_ids: list[str] = []
    for seq, req in enumerate(reqs, start=1):
        row = {"toolId": req.toolId, "verb": req.verb, "target": req.target,
               "path": None, "bytes": 0, "exitCode": None, "refused": None, "error": None}
        reason = validate_request(req, registry, refused_domains)
        if reason is not None:
            row["refused"] = reason
            results.append(row)
            continue   # never build/execute a refused request

        tool = _tool_entry(registry, req.toolId)
        argv = build_argv(tool, req)
        if req.toolId not in used_tool_ids:
            used_tool_ids.append(req.toolId)

        try:
            cp = subprocess.run(argv, shell=False, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        except (subprocess.TimeoutExpired, OSError) as e:
            row["error"] = str(e)
            results.append(row)
            continue

        stdout = cp.stdout or ""
        result_path = _safe_result_path(out_dir, seq, req.toolId, req.target)
        result_path.write_text(stdout, encoding="utf-8", newline="\n")
        row["path"] = str(result_path)
        row["bytes"] = len(stdout)
        row["exitCode"] = cp.returncode
        if cp.returncode != 0:
            row["error"] = (cp.stderr or "")[-500:]
        results.append(row)

    os_key = detect_os()
    tool_versions = {tid: _tool_version(_tool_entry(registry, tid), os_key)
                     for tid in used_tool_ids}

    manifest = {"results": results, "toolVersions": tool_versions}
    (out_dir / "fetch-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
