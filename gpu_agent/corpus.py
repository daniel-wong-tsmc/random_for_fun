"""gpu_agent/corpus.py — the flagship input corpus (F62).

Read-only consumer of existing stores: the wiki (page index + observations) as the
category-scoped index over the canonical FindingStore, and the L2 dedup classifier
for fresh-vs-store classification. Assembles the windowed accumulated store findings
plus this cycle's fresh gated findings into ONE merged corpus for the judge/thesis
brains and the scorecard, and reports coverage so the gather can run as a top-up.

This module never writes anything: no store mutation, no file writes, no clock
reads. Same inputs -> byte-identical CorpusResult, always. Window membership is
label-based (asOf period ends), never wall-clock, so replays/backtests are
deterministic and a past cycle never sees a future label.
"""
from __future__ import annotations
import calendar
import datetime
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.gathering.dedup import DEFAULT_DEDUP_CONFIG, FindingClass, classify_findings
from gpu_agent.schema.finding import Finding
from gpu_agent.store import FindingNotFound, FindingStore
from gpu_agent.wiki.store import WikiStore

WINDOW_DAYS_DEFAULT = 45

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class CorpusError(ValueError):
    """Raised on invalid labels or canonical-store integrity violations (fail loud)."""


def period_end(label: str) -> datetime.date:
    """A label's period end: a day-grain label is its own day; a month-grain label is
    that month's last calendar day. Any other shape fails loud (F56-adjacent defense)."""
    try:
        if _DAY_RE.match(label):
            return datetime.date.fromisoformat(label)
        if _MONTH_RE.match(label):
            y, m = int(label[:4]), int(label[5:7])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
    except ValueError as e:
        raise CorpusError(f"invalid asOf label: {label!r} ({e})") from e
    raise CorpusError(f"invalid asOf label: {label!r} (want YYYY-MM or YYYY-MM-DD)")


def in_window(label: str, as_of: str, window_days: int) -> bool:
    """Spec window rule: period_end(as_of) - window_days < period_end(label) <= period_end(as_of)."""
    end = period_end(as_of)
    start = end - datetime.timedelta(days=window_days)
    return start < period_end(label) <= end


class CoverageEntry(BaseModel):
    entity: str
    indicatorId: str
    count: int
    latestAsOf: str
    latestObservedAt: str


class SkippedPage(BaseModel):
    id: str
    category: Optional[str] = None


class CorpusReport(BaseModel):
    asOf: str
    category: str
    windowDays: int
    windowStart: str   # ISO day, exclusive lower bound
    windowEnd: str     # ISO day, inclusive upper bound
    storeIncluded: list[str] = Field(default_factory=list)      # finding ids, sorted with merged order
    outOfWindow: int = 0
    skippedPages: list[SkippedPage] = Field(default_factory=list)
    freshNew: list[FindingClass] = Field(default_factory=list)
    freshUpdate: list[FindingClass] = Field(default_factory=list)
    freshDuplicate: list[FindingClass] = Field(default_factory=list)
    idOverlaps: list[str] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    notCovered: list[str] = Field(default_factory=list)


class CorpusResult(BaseModel):
    merged: list[Finding] = Field(default_factory=list)
    dedupedFresh: list[Finding] = Field(default_factory=list)   # the write-back stream
    report: CorpusReport
