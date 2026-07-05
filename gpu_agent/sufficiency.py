"""F63 evidence-sufficiency gate — the deterministic counterweight to the corroboration
doctrine: corroborated news can move ratings, insufficient news cannot.

Rule: changing a dimension RATING (vs the prior cycle's MEMORY state) or the
categoryStatus.bottleneck requires the changed item's cited findings to include primary
evidence or span >= N distinct publishers (F31 key; N from registry/corroboration.json).

Deliberate scope (spec): rating + binding-constraint changes only — direction-only and
constraintLabel/prose changes never trigger; a dimension with no prior rating is exempt;
no MEMORY at all -> inert. Violations are gate failures: the caller re-dispatches the
judge brain with the violations appended (never edits the answer)."""
from __future__ import annotations
import json

from gpu_agent.config import min_distinct_publishers
from gpu_agent.publisher import publisher_key


def _sufficient(finding_ids, findings_by_id, n) -> tuple[bool, int]:
    """(passes, distinct-publisher count). Primary anywhere passes outright. Unresolvable
    ids contribute nothing — citation validity against the briefing is the aggregator's
    job, not this gate's."""
    evs = [e for fid in finding_ids if fid in findings_by_id
           for e in findings_by_id[fid].evidence]
    publishers = {publisher_key(e) for e in evs}
    if any(e.tier == "primary" for e in evs):
        return True, len(publishers)
    return len(publishers) >= n, len(publishers)


def check_sufficiency(raw_answers: list, memory, findings_by_id) -> list[str]:
    """`raw_answers` is the recorded-samples list (each item a JudgmentResult JSON string,
    RecordedClient's replay shape — same input contract as cli._voice_lint_samples).
    `memory` is the MemoryBundle the emitted prompt carried, or None (-> inert)."""
    if memory is None:
        return []
    n = min_distinct_publishers()
    prior_ratings = memory.priorRatings or {}
    prior_bottleneck = (memory.priorCategoryStatus or {}).get("bottleneck")
    violations: list[str] = []
    for i, raw in enumerate(raw_answers):
        sample = json.loads(raw)
        prefix = f"sample {i + 1}: "
        dims = sample.get("dimensions") or {}
        for dim, d in dims.items():
            prior = prior_ratings.get(dim)
            if prior is None or d.get("rating") == prior.get("rating"):
                continue
            ok, count = _sufficient(d.get("findingIds") or [], findings_by_id, n)
            if not ok:
                violations.append(
                    prefix + f"{dim}: rating changed {prior.get('rating')}->"
                    f"{d.get('rating')} with insufficient evidence "
                    f"(no primary; {count} distinct publishers < {n})")
        status = sample.get("categoryStatus") or {}
        new_bottleneck = status.get("bottleneck")
        if prior_bottleneck and new_bottleneck and new_bottleneck != prior_bottleneck:
            ids = (dims.get(new_bottleneck) or {}).get("findingIds") or []
            ok, count = _sufficient(ids, findings_by_id, n)
            if not ok:
                violations.append(
                    prefix + f"categoryStatus.bottleneck: changed {prior_bottleneck}->"
                    f"{new_bottleneck} with insufficient evidence "
                    f"(no primary; {count} distinct publishers < {n})")
    return violations
