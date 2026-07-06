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
from gpu_agent.gate import _rating_consistent_with_anchor
from gpu_agent.publisher import publisher_key

# F71 (contract v1.4): the trust-footer stamp an anchor-forced move rides on. Kept as a
# named constant so the exemption path and any renderer name the exact same string.
ANCHOR_BOUNDED_STAMP = "anchor-bounded on thin evidence"


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


def _anchor_forced(prior_rating, new_rating, anchor) -> bool:
    """F71: the move is anchor-FORCED (exempt from sufficiency) iff the PRIOR rating is illegal
    under the measured anchor (the Part 7 bias guardrail bounds it) AND the NEW rating resolves
    that conflict (is anchor-legal). A move where the prior is still anchor-legal is a genuine
    judgment re-rate and stays gated; a new rating that is itself still illegal is the anchor
    gate's problem, not an exemption."""
    if anchor is None:
        return False
    return (not _rating_consistent_with_anchor(prior_rating, anchor)
            and _rating_consistent_with_anchor(new_rating, anchor))


def check_sufficiency(raw_answers: list, memory, findings_by_id, *,
                      anchors: dict | None = None, exemptions: dict | None = None) -> list[str]:
    """`raw_answers` is the recorded-samples list (each item a JudgmentResult JSON string,
    RecordedClient's replay shape — same input contract as cli._voice_lint_samples).
    `memory` is the MemoryBundle the emitted prompt carried, or None (-> inert).

    F71 (contract v1.4): `anchors` (dim -> measured anchor, from build_briefing) enables the
    anchor-forced-move exemption — a rating change forced by the anchor making the prior rating
    illegal is code-computed measured evidence, not a judgment re-rate, so it is NOT gated for
    sufficiency. When exempted, the dimension is recorded in `exemptions` (dim -> stamp) if a
    dict is supplied, so the caller can stamp the trust footer. Omitting `anchors` reproduces
    the pre-v1.4 behavior byte-for-byte (no exemption path)."""
    if memory is None:
        return []
    n = min_distinct_publishers()
    prior_ratings = memory.priorRatings or {}
    prior_bottleneck = (memory.priorCategoryStatus or {}).get("bottleneck")
    anchors = anchors or {}
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
                if _anchor_forced(prior.get("rating"), d.get("rating"), anchors.get(dim)):
                    if exemptions is not None:
                        exemptions[dim] = ANCHOR_BOUNDED_STAMP
                    continue
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
