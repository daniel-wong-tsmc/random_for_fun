"""F79 — the series store. Append-only, one JSONL file per indicator under store/series/.

Each point carries its publication VINTAGE (publishedAt) separately from when WE recorded
it (capturedAt), so a vintage-aware read can hide any revision published after a given
as-of (F52 no-look-ahead discipline). Revisions are appended (never rewritten); at read
time the later vintage wins for a given period.
"""
from __future__ import annotations
import pathlib
import re
from typing import Optional
from pydantic import BaseModel, field_validator

_PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class SeriesSource(BaseModel):
    url: str
    title: str = ""


class SeriesPoint(BaseModel):
    indicatorId: str
    period: str            # YYYY-MM
    value: float
    unit: str
    publishedAt: str       # ISO date, the publication VINTAGE
    capturedAt: str        # ISO date, when WE recorded it
    source: SeriesSource
    estimateGrade: bool = False
    note: str = ""

    @field_validator("period")
    @classmethod
    def _period_shape(cls, v: str) -> str:
        if not _PERIOD_RE.match(v):
            raise ValueError(f"period must be YYYY-MM: {v!r}")
        return v


def _path(root, indicator_id: str) -> pathlib.Path:
    if not _SAFE_ID.match(indicator_id):
        raise ValueError(f"unsafe indicator id: {indicator_id!r}")
    return pathlib.Path(root) / f"{indicator_id}.jsonl"


def append_point(root, point: SeriesPoint) -> pathlib.Path:
    path = _path(root, point.indicatorId)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(point.model_dump_json() + "\n")
    return path


def read_series(root, indicator_id: str, *, as_of: Optional[str] = None) -> list[SeriesPoint]:
    path = _path(root, indicator_id)
    if not path.exists():
        return []
    pts = [SeriesPoint.model_validate_json(ln)
           for ln in path.read_text("utf-8").splitlines() if ln.strip()]
    if as_of is not None:
        pts = [p for p in pts if p.publishedAt <= as_of]   # vintage discipline: no look-ahead
    return pts


def latest_by_period(root, indicator_id: str, *, as_of: Optional[str] = None) -> dict[str, SeriesPoint]:
    """One point per period — the one with the greatest publishedAt that is <= as_of
    (revisions append; the later vintage wins at read time). With as_of set, a revision
    published after that date is invisible (no look-ahead)."""
    out: dict[str, SeriesPoint] = {}
    for p in read_series(root, indicator_id, as_of=as_of):
        cur = out.get(p.period)
        if cur is None or p.publishedAt > cur.publishedAt:
            out[p.period] = p
    return out
