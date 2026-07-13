"""F79 Stage 5 — the scoring v2.0 backtest harness.

Replays the series store STRICTLY by publication vintage over the backtest window
(monthly walk; each month's as-of is its last calendar day), computes the v2 index
(score_v2) and the σ-band alert stream (raw_alert_v2 + the shared anti-flapping fold),
and scores recall / false-alarm(orange+) / lead-time against the three NAMED turns.

The pass bar is PRE-COMMITTED (spec, written before this harness ran): catch >= 2 of
the 3 named turns with >= 1 quarter of lead each, AND <= 1 false orange-or-worse alarm
per backtest year. A miss = STOP and redesign — no weight tweaks off a single miss.
The G2 verdict gate is USER-SIGNED.

Turn definitions (DP-4, pre-registered before the real run; the month is when the
condition became public consensus, so lead time measures genuine earliness):
- h100-crunch-onset 2023-09 — Mark Liu's public "we can support about 80% of needs"
  (SEMICON Taiwan, 2023-09-08) marks the shortage as acknowledged consensus.
- cowos-bottleneck 2023-12 — by the Q4-2023 earnings cycle "doubling capacity and
  still not enough" was the universal public frame for advanced packaging.
- hbm-squeeze 2024-03 — Micron's "HBM sold out for calendar 2024" (2024-03-20) made
  the HBM squeeze explicit vendor-stated fact.

Measurement conventions (pre-registered during synthetic TDD, before the real run;
see tests/test_backtest_harness.py):
episodes = maximal runs of consecutive RAW orange+ months; catch = episode start a
with 3 <= (turnMonth - a) <= 9; false = episode associated with no turn's
[turn-9, turn+3] window; the false bar counts episodes per calendar year.
RAW (not folded) colors drive episode detection: the anti-flapping fold — correct for
a reader-facing display — merges the young-history warm-up noise and any genuine
signal into one giant episode, destroying both catch attribution and false counting.
Raw episodes fragment honestly and count MORE alarms than a reader would see, so the
false bar is measured conservatively. Folded colors stay in the result for display.

No event impulses here: the news-flow layer's deep history cannot be reconstructed
without hindsight bias (spec non-goal) — the series layer IS the backtest spine.
"""
from __future__ import annotations

import calendar
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from gpu_agent.change import raw_alert_v2, fold_displayed, _ALERT_RANK
from gpu_agent.scoring import score_v2


class Turn(BaseModel):
    id: str
    turnMonth: str                 # YYYY-MM: when the condition became public consensus
    direction: str = "shortage"


NAMED_TURNS = [
    Turn(id="h100-crunch-onset", turnMonth="2023-09"),
    Turn(id="cowos-bottleneck", turnMonth="2023-12"),
    Turn(id="hbm-squeeze", turnMonth="2024-03"),
]

LEAD_MIN_MONTHS = 3        # >= 1 quarter (the pre-committed bar)
LEAD_MAX_MONTHS = 9        # inside the series' stated 2-4Q lead horizon
GRACE_AFTER_MONTHS = 3     # an alarm this soon after a turn is turn-associated, not false
_ORANGE = _ALERT_RANK["orange"]


class BacktestResult(BaseModel):
    months: list[str]
    dmi: list[float]
    smi: list[float]
    sdgi: list[float]
    rawColors: list[str]
    foldedColors: list[str]


class Catch(BaseModel):
    turnId: str
    episodeStart: str
    leadMonths: int


class Verdict(BaseModel):
    catches: list[Catch] = Field(default_factory=list)
    missedTurns: list[str] = Field(default_factory=list)
    falseEpisodes: list[str] = Field(default_factory=list)   # episode start months
    maxFalsePerYear: int = 0
    passed: bool = False


def _months_between(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + (int(b[5:7]) - int(a[5:7]))


def _month_range(start: str, end: str) -> list[str]:
    out, y, m = [], int(start[:4]), int(start[5:7])
    while f"{y:04d}-{m:02d}" <= end:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _month_end(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    return f"{month}-{calendar.monthrange(y, m)[1]:02d}"


def run_backtest(registry, series_root, *, start: str = "2023-01",
                 end: str = "2025-12") -> BacktestResult:
    """The vintage walk: at each month, score the v2 index with as-of = month end
    (points published later are invisible — no look-ahead), then evaluate the σ-band
    alert over the history accumulated SO FAR and fold the anti-flapping memory."""
    months = _month_range(start, end)
    dmi_s: list[float] = []
    smi_s: list[float] = []
    sdgi_s: list[float] = []
    raws: list[str] = []
    for month in months:
        dmi, smi = score_v2(registry, series_root, as_of=_month_end(month))
        dmi_s.append(dmi)
        smi_s.append(smi)
        sdgi_s.append(dmi - smi)
        color, _trig = raw_alert_v2(list(sdgi_s), list(dmi_s))
        raws.append(color)
    return BacktestResult(months=months, dmi=dmi_s, smi=smi_s, sdgi=sdgi_s,
                          rawColors=raws, foldedColors=fold_displayed(raws))


def _episodes(result: BacktestResult) -> list[str]:
    """Start months of maximal consecutive orange-or-worse runs (RAW colors — see the
    module docstring for why the fold is display-only here)."""
    starts, in_ep = [], False
    for month, color in zip(result.months, result.rawColors):
        hot = _ALERT_RANK[color] >= _ORANGE
        if hot and not in_ep:
            starts.append(month)
        in_ep = hot
    return starts


def evaluate(result: BacktestResult, turns: Optional[Sequence[Turn]] = None) -> Verdict:
    turns = list(NAMED_TURNS if turns is None else turns)
    episodes = _episodes(result)
    catches: list[Catch] = []
    missed: list[str] = []
    for t in turns:
        leads = [(_months_between(e, t.turnMonth), e) for e in episodes]
        ok = [(lead, e) for lead, e in leads if LEAD_MIN_MONTHS <= lead <= LEAD_MAX_MONTHS]
        if ok:
            lead, e = min(ok)          # the NEAREST qualifying episode — the
            # conservative lead (an early episode is not double-credited with
            # inflated leads across every later overlapping turn)
            catches.append(Catch(turnId=t.id, episodeStart=e, leadMonths=lead))
        else:
            missed.append(t.id)
    false_eps = [e for e in episodes
                 if not any(-GRACE_AFTER_MONTHS <= _months_between(e, t.turnMonth)
                            <= LEAD_MAX_MONTHS for t in turns)]
    per_year: dict[str, int] = {}
    for e in false_eps:
        per_year[e[:4]] = per_year.get(e[:4], 0) + 1
    max_false = max(per_year.values(), default=0)
    passed = len(catches) >= 2 and max_false <= 1
    return Verdict(catches=catches, missedTurns=missed, falseEpisodes=false_eps,
                   maxFalsePerYear=max_false, passed=passed)
