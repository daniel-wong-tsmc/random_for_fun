# gpu_agent/dashboard/ranking.py
from datetime import date
from .glossary import has_big_figure

W_NEW = 0.40
W_OFFICIAL = 0.35
W_IMPACT = 0.25
RECENCY_FULL_DAYS = 7
RECENCY_ZERO_DAYS = 42
MAGNITUDE_MAX = 3

_NEW_BADGE_AT = 0.66
_IMPACT_BADGE_AT = 0.66


def _parse_date(s):
    try:
        return date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def _recency(observed_at, as_of):
    d0, d1 = _parse_date(observed_at), _parse_date(as_of)
    if not d0 or not d1:
        return 0.0
    age = (d1 - d0).days
    if age <= RECENCY_FULL_DAYS:
        return 1.0
    if age >= RECENCY_ZERO_DAYS:
        return 0.0
    span = RECENCY_ZERO_DAYS - RECENCY_FULL_DAYS
    return max(0.0, 1.0 - (age - RECENCY_FULL_DAYS) / span)


def finding_signals(finding, as_of, glossary):
    new = _recency(finding.get("observed_at"), as_of)
    official = 1.0 if finding.get("tier") == "primary" else 0.4
    impact = min(1.0, (finding.get("magnitude", 0) or 0) / MAGNITUDE_MAX)
    if has_big_figure(finding.get("statement", "")):
        impact = min(1.0, impact + 0.2)
    return {"new": new, "official": official, "impact": impact}


_CONV = {"high": 1.0, "medium": 0.66, "low": 0.33}
_MOVED = {"strengthened", "weakened"}


def call_signals(call):
    status = call.get("status")
    direction = call.get("direction")
    moved = direction in _MOVED or status in ("challenged", "not_judged") or call.get("cycles", 0) == 0
    new = 1.0 if moved else 0.3
    official = 1.0 if call.get("has_official") else 0.4
    impact = _CONV.get(call.get("conviction"), 0.33)
    return {"new": new, "official": official, "impact": impact}


def importance(signals):
    return (W_NEW * signals.get("new", 0.0)
            + W_OFFICIAL * signals.get("official", 0.0)
            + W_IMPACT * signals.get("impact", 0.0))


def badges(signals):
    out = []
    if signals.get("new", 0.0) >= _NEW_BADGE_AT:
        out.append("new")
    if signals.get("official", 0.0) >= 1.0:
        out.append("official")
    if signals.get("impact", 0.0) >= _IMPACT_BADGE_AT:
        out.append("impact")
    return out


def _sort_key(item):
    s = item["_signals"]
    return (-item["_score"], -s["new"], -s["official"])


def rank_findings(findings, as_of, glossary):
    out = []
    for f in findings:
        sig = finding_signals(f, as_of, glossary)
        out.append({**f, "_signals": sig, "_score": importance(sig), "_badges": badges(sig)})
    out.sort(key=_sort_key)
    return out


def rank_calls(calls):
    out = []
    for c in calls:
        sig = call_signals(c)
        out.append({**c, "_signals": sig, "_score": importance(sig), "_badges": badges(sig)})
    out.sort(key=_sort_key)
    return out
