"""F79 — the scoring v2.0 series engine (doc-settled mechanics, 2026-07-11 spec §6).

Pure math over the series store: rolling z-scores against a series' OWN prior history
(36-month window), same-class (same-unit) distribution borrowing for young series,
freshness decay exp(-λ·age), weighted z-sum index composition with dual polarity and
the indicator lifecycle (retired excluded; source dark > 3 months → weight 0), the
ΔSDGI momentum trigger, and event impulses with an 8-week half-life.

Deterministic and clock-free: every read is vintage-aware via `as_of` (no look-ahead).
Mechanical interpretations recorded in the plan's decision provenance:
- z-score = surprise vs PRIOR history (the current value is excluded from mean/std);
  needs ≥ 3 prior values and a nonzero std, else None.
- "same-class" for borrowing = same UNIT string (the only pooling that is statistically
  meaningful); a young series (< 3 prior values but ≥ 1) borrows the pool's mean/std.
- source-dark = latest point's period more than 3 calendar months before as_of.
"""
from __future__ import annotations

import datetime
import math
import statistics
from typing import Optional, Sequence

from pydantic import BaseModel

from gpu_agent.series_store import latest_by_period

Z_WINDOW = 36           # months (doc-settled)
_MIN_PRIOR = 3          # prior values needed for an own-history z
DARK_MONTHS = 3         # source-dark threshold (doc-settled)
IMPULSE_HALF_LIFE_WEEKS = 8.0


class Impulse(BaseModel):
    """One decaying event signal (the news-flow channel enters the index through these)."""
    ageWeeks: float
    weight: float
    polarityDemand: int = 0
    polaritySupply: int = 0


def decay_weight(age_months: float, lam: float) -> float:
    return math.exp(-lam * age_months)


def impulse(age_weeks: float, half_life_weeks: float = IMPULSE_HALF_LIFE_WEEKS) -> float:
    return 0.5 ** (age_weeks / half_life_weeks)


def zscore_latest(values: Sequence[float], window: int = Z_WINDOW) -> Optional[float]:
    """z of the LAST value against the mean/std of its prior history inside the window
    (surprise vs the past — the current value is excluded from the distribution).
    None when history is too short (< 3 priors) or flat (zero std)."""
    if len(values) < _MIN_PRIOR + 1:
        return None
    prior = list(values[-window:])[:-1]
    if len(prior) < _MIN_PRIOR:
        return None
    std = statistics.stdev(prior)
    if std == 0.0:
        return None
    return (values[-1] - statistics.mean(prior)) / std


def zscore_with_borrow(values: Sequence[float], class_pool: Sequence[float],
                       window: int = Z_WINDOW) -> Optional[float]:
    """Own-history z when the window has filled enough; otherwise a young series
    (≥ 1 prior value) borrows the same-class pool's distribution (doc-settled).
    None when neither its own history nor the pool can support a z."""
    own = zscore_latest(values, window)
    if own is not None:
        return own
    if not values:
        return None
    if len(class_pool) >= _MIN_PRIOR + 1:
        std = statistics.stdev(class_pool)
        if std > 0.0:
            return (values[-1] - statistics.mean(class_pool)) / std
    return None


def delta_sdgi_trigger(sdgi_series: Sequence[float]) -> bool:
    """ΔSDGI momentum (doc-settled): the gap moved the SAME direction two consecutive
    periods with a cumulative move > 0.5σ of the series — fires even at green."""
    if len(sdgi_series) < 4:
        return False
    d1 = sdgi_series[-1] - sdgi_series[-2]
    d2 = sdgi_series[-2] - sdgi_series[-3]
    if d1 == 0.0 or d2 == 0.0 or (d1 > 0) != (d2 > 0):
        return False
    sigma = statistics.stdev(sdgi_series)
    if sigma == 0.0:
        return False
    return abs(d1 + d2) > 0.5 * sigma


def _months_between(a: str, b: str) -> int:
    """Whole calendar months from period/date a to b (YYYY-MM or YYYY-MM-DD)."""
    return (int(b[:4]) - int(a[:4])) * 12 + (int(b[5:7]) - int(a[5:7]))


def _as_of_period(as_of: str) -> str:
    return as_of[:7]


def compose_index(registry, series_root, *, as_of: str,
                  impulses: Sequence[Impulse] = ()) -> tuple[float, float]:
    """The v2 index: DMI/SMI as weighted z-sums with freshness decay + event impulses.

    For each non-retired series: vintage-aware read (publishedAt <= as_of), z of the
    latest value vs its own prior history (borrowing from same-unit siblings while
    young), decay by the latest point's age in months, weight x dual polarity.
    Source dark (> DARK_MONTHS since the latest period) contributes zero. Impulses add
    weight x 0.5^(age/8w) x polarity."""
    specs = [s for s in registry.specs.values() if s.lifecycle != "retired"]
    # same-unit sibling pools for borrowing (values of OTHER series with the same unit,
    # inside the window, vintage-aware)
    by_series: dict[str, list[float]] = {}
    unit_of: dict[str, str] = {}
    for spec in specs:
        pts = latest_by_period(series_root, spec.id, as_of=as_of)
        periods = sorted(p for p in pts if 0 <= _months_between(p, _as_of_period(as_of)) < Z_WINDOW)
        by_series[spec.id] = [pts[p].value for p in periods]
        unit_of[spec.id] = spec.unit

    dmi = smi = 0.0
    for spec in specs:
        values = by_series[spec.id]
        if not values:
            continue
        pts = latest_by_period(series_root, spec.id, as_of=as_of)
        latest_period = max(pts)
        age = _months_between(latest_period, _as_of_period(as_of))
        if age > DARK_MONTHS:
            continue   # source dark -> weight 0 (doc-settled lifecycle rule)
        pool = [v for other, vals in by_series.items()
                if other != spec.id and unit_of[other] == spec.unit for v in vals]
        z = zscore_with_borrow(values, pool)
        if z is None:
            continue   # honest: no defensible standardization yet
        contrib = spec.weight * decay_weight(float(max(age, 0)), spec.decayLambda) * z
        dmi += contrib * spec.polarityDemand
        smi += contrib * spec.polaritySupply
    for imp in impulses:
        k = imp.weight * impulse(imp.ageWeeks)
        dmi += k * imp.polarityDemand
        smi += k * imp.polaritySupply
    return dmi, smi
