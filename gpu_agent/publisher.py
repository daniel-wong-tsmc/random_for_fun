# gpu_agent/publisher.py
from __future__ import annotations
from urllib.parse import urlparse


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
    netloc = urlparse(evidence.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc:
        return netloc
    return evidence.source.strip().lower()
