"""Label-based date helpers shared across the aging subsystems (F78 Stage 1).

An `asOf` label is either day-grain (YYYY-MM-DD) or month-grain (YYYY-MM). Its
"period end" is the last calendar day it covers. All elapsed-time math derives from
these period-ends — never the wall clock — so replays are deterministic.
"""
from __future__ import annotations
import calendar
import datetime
import re

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


class AsOfError(ValueError):
    """Raised when an asOf label is not YYYY-MM or YYYY-MM-DD (fail loud)."""


def period_end(label: str) -> datetime.date:
    """A label's period end: a day-grain label is its own day; a month-grain label is
    that month's last calendar day. Any other shape fails loud."""
    try:
        if _DAY_RE.match(label):
            return datetime.date.fromisoformat(label)
        if _MONTH_RE.match(label):
            y, m = int(label[:4]), int(label[5:7])
            return datetime.date(y, m, calendar.monthrange(y, m)[1])
    except ValueError as e:
        raise AsOfError(f"invalid asOf label: {label!r} ({e})") from e
    raise AsOfError(f"invalid asOf label: {label!r} (want YYYY-MM or YYYY-MM-DD)")


def days_between(later_label: str, earlier_label: str) -> int:
    """Calendar days from `earlier_label`'s period end to `later_label`'s period end.
    Negative if the labels are out of order (the caller decides whether to clamp)."""
    return (period_end(later_label) - period_end(earlier_label)).days
