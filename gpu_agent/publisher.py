# gpu_agent/publisher.py
from __future__ import annotations
import json
import os
import pathlib
from functools import lru_cache
from urllib.parse import urlparse

# F72 (contract v1.4): the syndicator registry — netloc -> shared originating-publisher
# identity. env-overridable like the other registry paths (config.py); DATA, edited freely.
SYNDICATORS_PATH = os.environ.get("GPU_AGENT_SYNDICATORS", "registry/syndicators.json")


def _netloc(evidence) -> str:
    """The evidence URL's registered netloc, www.-stripped and lowercased (''-safe)."""
    netloc = urlparse(evidence.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def publisher_key(evidence) -> str:
    """F31 publisher identity — THE corroboration key. Moved verbatim from
    wiki/lifecycle.py::_publisher_key when F63 gave it three consumers (wiki page
    promotion, thesis rule 6, gate F2e); import this, never re-derive it, so the
    publisher-identity notion can never drift between surfaces.

    Keys by the evidence URL's registered netloc (www.-stripped, lowercased) —
    corroboration must be keyed by publisher, not by free-text source strings that can
    name the same publisher two different ways ('NVIDIA Newsroom' vs 'NVIDIA press
    release'). Falls back to the source string when the URL has no netloc (e.g. a
    non-URL citation)."""
    netloc = _netloc(evidence)
    if netloc:
        return netloc
    return evidence.source.strip().lower()


@lru_cache(maxsize=1)
def _syndicators() -> dict[str, str]:
    """netloc (www-stripped, lowercased) -> originating-publisher identity, loaded from
    registry/syndicators.json. F72: known wire/PR-syndication + aggregator endpoints
    collapse to a shared identity so a single wire story mirrored across several domains
    counts as ONE distinct publisher. A missing/unreadable file -> no registry (empty map),
    so collapsed_publisher degrades to publisher_key."""
    try:
        data = json.loads(pathlib.Path(SYNDICATORS_PATH).read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    reg = data.get("syndicators", data) if isinstance(data, dict) else {}
    return {str(k).lower(): v for k, v in reg.items() if isinstance(v, str)}


def collapsed_publisher(evidence, *, bodies=None) -> str:
    """F72 syndication-resistant publisher identity (contract v1.4) — beside publisher_key.

    (a) Registry: any netloc in registry/syndicators.json collapses to its ORIGINATING
        publisher, so one wire story mirrored across several syndicator domains is one
        identity. Any other netloc returns publisher_key(evidence) unchanged.
    (b) Near-dup: when `bodies` — a content_hash(excerpt) -> canonical-identity map built
        by collapsed_publisher_set over a citation SET — is supplied, an evidence whose
        body is a byte-identical reprint of another citation's body collapses to that
        shared identity (L1 exact-hash; normalized/shingle similarity deferred, spec §7 Q6).

    `bodies=None` (the single-evidence call) is pure registry-or-publisher_key."""
    if bodies is not None:
        excerpt = (getattr(evidence, "excerpt", "") or "")
        if excerpt.strip():
            from gpu_agent.gathering.dedup import content_hash
            canon = bodies.get(content_hash(excerpt))
            if canon is not None:
                return canon
    netloc = _netloc(evidence)
    reg = _syndicators()
    if netloc and netloc in reg:
        return reg[netloc]
    return publisher_key(evidence)


def _near_dup_bodies(evidence_list) -> dict[str, str]:
    """content_hash(excerpt) -> canonical (registry-collapsed) identity of the FIRST citation
    carrying that body, so byte-identical wire reprints across different netlocs collapse to
    one identity (F72(b), L1 exact-hash). Empty/whitespace excerpts carry no comparable body
    and are never collapsed on content."""
    from gpu_agent.gathering.dedup import content_hash
    bodies: dict[str, str] = {}
    for e in evidence_list:
        excerpt = (getattr(e, "excerpt", "") or "")
        if not excerpt.strip():
            continue
        h = content_hash(excerpt)
        if h not in bodies:
            bodies[h] = collapsed_publisher(e)   # registry-aware; bodies=None avoids recursion
    return bodies


def collapsed_publisher_set(evidence_list) -> set[str]:
    """THE shared F72 distinct-publisher identity set over a citation list — registry
    syndicator collapse AND exact-hash near-dup collapse composed. Gate F2e, thesis rule 6,
    and wiki promotion all route through this so the syndication-resistant distinctness notion
    can never drift between the three corroboration surfaces (contract v1.4; never re-derive
    distinctness locally)."""
    evs = list(evidence_list)
    bodies = _near_dup_bodies(evs)
    return {collapsed_publisher(e, bodies=bodies) for e in evs}


def distinct_publisher_count(evidence_list) -> int:
    """len(collapsed_publisher_set) — the syndication-resistant distinct-publisher count that
    gate F2e's `minDistinctPublishers` bar (registry/corroboration.json) is measured against."""
    return len(collapsed_publisher_set(evidence_list))
