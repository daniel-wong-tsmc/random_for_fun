import json
from pathlib import Path
from .glossary import term_swap

STATE_OF_MARKET_KEY = "stateOfMarket"


def dimension_key(name):
    return f"dimension.{name}.rationale"


def claim_key(slug):
    return f"claim.{slug}.statement"


def finding_key(fid):
    return f"finding.{fid}.statement"


def load_plain_language(path):
    if not path or not Path(path).exists():
        return {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
    except (ValueError, OSError):
        return {}
    return data.get("rewrites", {}) or {}


def _norm(s):
    return " ".join((s or "").split())


def resolve_text(key, original, plain_map, glossary):
    entry = plain_map.get(key)
    if entry and _norm(entry.get("original")) == _norm(original) and entry.get("plain"):
        return entry["plain"], False
    return term_swap(original, glossary), True
