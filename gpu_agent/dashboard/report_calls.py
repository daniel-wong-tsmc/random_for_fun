import re
from pathlib import Path

_HEAD = re.compile(
    r"^\s*●\s+(?P<name>.+?)\s{2,}(?P<statusdir>.+?)\s+\((?P<conv>high|medium|low),\s*(?P<cycles>\d+)\s*cycles?\)(?P<tail>.*)$"
)
_SRC = re.compile(r"\((?P<n>\d+)\s+sources?", re.IGNORECASE)


def _slug(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def find_latest_report(work_dir):
    base = Path(work_dir)
    dailies = sorted([p for p in base.glob("daily-*") if (p / "report.txt").exists()],
                     key=lambda p: p.name)
    if not dailies:
        return None
    return dailies[-1] / "report.txt"


def _status(statusdir):
    s = statusdir.upper()
    if "CHALLENGED" in s:
        return "challenged"
    if "NOT YET JUDGED" in s:
        return "not_judged"
    return "intact"


def _direction(statusdir):
    s = statusdir.lower()
    if "strengthened" in s:
        return "strengthened"
    if "weakened" in s:
        return "weakened"
    if "reaffirmed" in s:
        return "reaffirmed"
    return "none"


def parse_calls(report_text):
    lines = report_text.splitlines()
    calls = []
    i = 0
    while i < len(lines):
        m = _HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group("name").strip()
        tail = m.group("tail") or ""
        # Following indented lines until the next call or blank-section break.
        body = []
        j = i + 1
        while j < len(lines) and lines[j].startswith("      ") and "●" not in lines[j]:
            body.append(lines[j].strip())
            j += 1
        statement = body[0] if body else ""
        breaks_if = ""
        for b in body:
            if b.lower().startswith("breaks if:"):
                breaks_if = b.split(":", 1)[1].strip()
        src = _SRC.search(statement)
        calls.append({
            "name": name,
            "slug": _slug(name),
            "status": _status(m.group("statusdir")),
            "direction": _direction(m.group("statusdir")),
            "conviction": m.group("conv"),
            "cycles": int(m.group("cycles")),
            "statement": re.sub(r"\s*\(\d+ sources?.*?\)\s*$", "", statement).strip(),
            "source_count": int(src.group("n")) if src else 0,
            "has_official": "official post" in (statement + tail).lower()
                            or "company filing" in (statement + tail).lower(),
            "early": "early" in tail.lower() and "corroborated" in tail.lower(),
            "breaks_if": breaks_if,
        })
        i = j
    return calls
