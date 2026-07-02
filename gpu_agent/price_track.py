"""gpu_agent/price_track.py — the Price Momentum overlay (F49).

Pure, deterministic, no I/O: extracts per-series price levels from a Scorecard's
price-side findings, matches each against a prior scorecard's same-key series for a
delta + direction, and rolls matched series into a PMI (Price Momentum Index). This is
an OVERLAY — displayed beside DMI/SMI, never blended into demandSupply or indices; the
frozen v1.2 scoring contract is untouched by this module.
"""
from __future__ import annotations
from typing import Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field

from gpu_agent.schema.scorecard import Scorecard

REL_TOL = 0.01     # relative tolerance for "flat" — mirrors gathering.dedup's DedupConfig.rel_tol
_EPS = 1e-9        # floor so a near-zero prior value can't divide-by-zero


class PriceSeries(BaseModel):
    indicatorId: str
    unit: str
    publisher: str
    value: float
    observedAt: str
    findingId: str
    delta: Optional[float] = None                              # vs prior scorecard's matching series
    direction: Optional[Literal["up", "down", "flat"]] = None  # |delta| <= rel_tol -> flat


class PriceTrack(BaseModel):
    series: list[PriceSeries] = Field(default_factory=list)   # sorted (indicatorId, publisher, unit)
    pmi: Optional[float] = None    # mean of (+1 up / -1 down / 0 flat); None if no series has a delta
    matchedSeries: int = 0


def _publisher(f) -> str:
    """First evidence item's URL netloc, lowercased, minus a leading 'www.'; falls back
    to that evidence's source name, or '' with no evidence at all — the same rule F29
    (brief board single-source tag) and F51 (dedup price key) use."""
    if not f.evidence:
        return ""
    ev = f.evidence[0]
    netloc = urlparse(ev.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[len("www."):]
    return netloc or ev.source.lower()


def _latest_by_series(sc: Optional[Scorecard]) -> dict[tuple[str, str, str], object]:
    """One Finding per (indicatorId, publisher, unit) series — the latest vintage by
    (capturedAt, observedAt, magnitude); ties keep the first-seen finding, the same
    deterministic tie-break brief._collapse_latest uses. Only measured price findings
    carrying a value are series members. None scorecard -> empty (no prior cycle)."""
    latest: dict[tuple[str, str, str], object] = {}
    if sc is None:
        return latest
    for f in sc.findings:
        if f.side != "price" or f.value is None:
            continue
        key = (f.indicatorId, _publisher(f), f.value.unit)
        cur = latest.get(key)
        cand = (f.capturedAt, f.observedAt, f.magnitude)
        if cur is None or cand > (cur.capturedAt, cur.observedAt, cur.magnitude):
            latest[key] = f
    return latest


def compute_price_track(sc: Scorecard, prior: Optional[Scorecard] = None) -> PriceTrack:
    """Extract this cycle's price series, match each against the prior scorecard's
    same-key series for a delta + direction, and roll the matched series into a PMI
    (mean of +1 up / -1 down / 0 flat over MATCHED series only; None with no matches —
    "needs two cycles of the same series" is an honest state, not a fabricated 0).
    Read-only: never mutates sc or prior, never writes demandSupply/indices — the
    overlay is computed and displayed, never blended into the frozen scoring contract."""
    current = _latest_by_series(sc)
    prior_series = _latest_by_series(prior)

    rows: list[PriceSeries] = []
    signed: list[float] = []
    matched = 0
    for key in sorted(current):
        indicator_id, publisher, unit = key
        f = current[key]
        delta: Optional[float] = None
        direction: Optional[str] = None
        pf = prior_series.get(key)
        if pf is not None and pf.value is not None:
            delta = f.value.number - pf.value.number
            matched += 1
            tol = REL_TOL * max(abs(pf.value.number), _EPS)
            if abs(delta) <= tol:
                direction = "flat"
                signed.append(0.0)
            elif delta > 0:
                direction = "up"
                signed.append(1.0)
            else:
                direction = "down"
                signed.append(-1.0)
        rows.append(PriceSeries(
            indicatorId=indicator_id, unit=unit, publisher=publisher,
            value=f.value.number, observedAt=f.observedAt, findingId=f.id,
            delta=delta, direction=direction))

    pmi = (sum(signed) / len(signed)) if signed else None
    return PriceTrack(series=rows, pmi=pmi, matchedSeries=matched)
