from __future__ import annotations
import json
import pathlib
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel

PAYWALLED_REGISTRY = pathlib.Path("registry/paywalled-domains.json")


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
