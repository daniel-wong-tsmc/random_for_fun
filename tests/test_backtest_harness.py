"""F79 Stage 5 — the backtest harness. Replays the series store by publication vintage
month-by-month, computes the v2 index + σ-band alert stream, and scores recall /
false-alarm(orange+) / lead-time against the three NAMED turns.

Measurement conventions (pre-registered BEFORE the real run; disclosed at G2):
- The walk is monthly; each month's as-of is its last calendar day (a point published
  inside the month is visible from that month on — never earlier).
- Episode detection runs on RAW colors: the anti-flapping fold (right for a reader
  display) merges warm-up noise and genuine signal into one giant episode, destroying
  catch attribution — raw episodes fragment honestly and count false alarms
  CONSERVATIVELY (more episodes than a reader would see). Folded colors stay in the
  result for display.
- An EPISODE = a maximal run of consecutive orange-or-worse months (one alarm, not N).
- CATCH of a turn = an episode STARTING a with 3 <= (turnMonth - a) <= 9 months
  (>= 1 quarter of lead, within the series' stated 2-4Q lead horizon).
- FALSE alarm = an episode associated with NO turn, where association is a start
  inside [turnMonth - 9, turnMonth + 3]. Bar: <= 1 false episode per backtest YEAR.
- PASS = >= 2 of 3 turns caught AND the false bar holds (the spec's pre-committed bar).
"""
from __future__ import annotations
import pytest
from gpu_agent import backtest as bt
from gpu_agent.series_store import SeriesPoint, SeriesSource, append_point
from gpu_agent.series_registry import SeriesIndicatorSpec


def test_named_turns_are_the_three_from_the_spec():
    ids = [t.id for t in bt.NAMED_TURNS]
    assert ids == ["h100-crunch-onset", "cowos-bottleneck", "hbm-squeeze"]
    months = {t.id: t.turnMonth for t in bt.NAMED_TURNS}
    assert months["h100-crunch-onset"] == "2023-09"
    assert months["cowos-bottleneck"] == "2023-12"
    assert months["hbm-squeeze"] == "2024-03"


# ---- evaluate(): metric arithmetic over a fabricated alert stream ----------------------

def _months(start="2023-01", n=36):
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _result(colors, start="2023-01"):
    months = _months(start, len(colors))
    return bt.BacktestResult(months=months, dmi=[0.0] * len(colors),
                             smi=[0.0] * len(colors), sdgi=[0.0] * len(colors),
                             rawColors=list(colors), foldedColors=list(colors))


def test_evaluate_catches_with_lead_and_counts_false_episodes():
    colors = ["green"] * 36
    colors[5] = "orange"                      # 2023-06: lead 3 to h100 turn (2023-09)
    colors[8] = "orange"                      # 2023-09: lead 3 to cowos (2023-12)
    colors[26] = colors[27] = "orange"        # 2025-03/04: ONE false episode
    v = bt.evaluate(_result(colors), turns=bt.NAMED_TURNS)
    caught = {c.turnId: c for c in v.catches}
    assert caught["h100-crunch-onset"].leadMonths == 3
    assert caught["cowos-bottleneck"].leadMonths == 3
    # 2023-09 also sits 6 months before hbm-squeeze (2024-03) -> caught by the same episode
    assert caught["hbm-squeeze"].leadMonths == 6
    assert v.falseEpisodes == ["2025-03"]     # consecutive oranges = one episode
    assert v.maxFalsePerYear == 1
    assert v.passed is True


def test_evaluate_fails_below_two_catches():
    colors = ["green"] * 36
    colors[5] = "orange"                      # catches h100 only (and cowos at lead 6)
    v = bt.evaluate(_result(colors), turns=bt.NAMED_TURNS)
    assert len(v.catches) >= 1
    # force the single-catch case: an alert too late for every other turn
    colors2 = ["green"] * 36
    colors2[8] = "orange"                     # 2023-09: lead 0 to h100 (NOT a catch),
    v2 = bt.evaluate(_result(colors2), turns=bt.NAMED_TURNS)        # lead 3 to cowos, lead 6 to hbm -> 2 catches
    assert {c.turnId for c in v2.catches} == {"cowos-bottleneck", "hbm-squeeze"}
    colors3 = ["green"] * 36
    colors3[30] = "orange"                    # 2025-07: associated with nothing -> false
    v3 = bt.evaluate(_result(colors3), turns=bt.NAMED_TURNS)
    assert v3.catches == [] and v3.passed is False


def test_evaluate_false_bar_breach_fails():
    colors = ["green"] * 36
    colors[5] = "orange"                      # catch h100
    colors[8] = "orange"                      # catch cowos + hbm
    colors[24] = "orange"                     # 2025-01 false
    colors[28] = "orange"                     # 2025-05 false (separate episode)
    v = bt.evaluate(_result(colors), turns=bt.NAMED_TURNS)
    assert v.maxFalsePerYear == 2
    assert v.passed is False


# ---- run_backtest(): the vintage walk over a synthetic store ---------------------------

class _Reg:
    def __init__(self, specs):
        self.specs = {s.id: s for s in specs}


def test_run_backtest_catches_a_planted_turn(tmp_path):
    # demand series: alternating base 2023-01..2023-12, hard sustained ramp from
    # 2024-01. Reality this test intentionally captures: a young z-history is NOISY
    # (an alternating base swings z by ~1 regardless of amplitude), so the warm-up
    # phase throws raw orange episodes — the earliest of them (2023-05, 11 months
    # before the planted turn) counts as FALSE, while the ramp's own 2024-01 episode
    # catches the planted 2024-04 turn with a 3-month lead.
    months = _months("2023-01", 15)
    base = [10.0, 11.0] * 6
    values = base + [30.0, 35.0, 36.0]
    for p, v in zip(months, values):
        append_point(tmp_path, SeriesPoint(
            indicatorId="d", period=p, value=v, unit="u",
            publishedAt=f"{p}-15", capturedAt="2026-07-13",
            source=SeriesSource(url="https://x/y", title="t")))
    reg = _Reg([SeriesIndicatorSpec(id="d", side="demand", weight=1.0,
                                    polarityDemand=1, polaritySupply=0)])
    res = bt.run_backtest(reg, tmp_path, start="2023-01", end="2024-03")
    assert res.months[-1] == "2024-03"
    assert all(c == "green" for c in res.rawColors[:4])      # zero-history months
    jan = res.months.index("2024-01")
    assert res.rawColors[jan] in ("orange", "red")           # the planted jump fires
    turns = [bt.Turn(id="planted", turnMonth="2024-04", direction="shortage")]
    v = bt.evaluate(res, turns=turns)
    assert v.catches and v.catches[0].turnId == "planted"
    assert v.catches[0].leadMonths == 3
    assert v.catches[0].episodeStart == "2024-01"
    assert v.falseEpisodes == ["2023-05"]                    # warm-up noise, counted honestly


def test_run_backtest_respects_publication_vintage(tmp_path):
    # a point for 2023-06 published LATE (2023-09-20) must not move the June index
    months = _months("2023-01", 8)
    for i, p in enumerate(months):
        published = "2023-09-20" if p == "2023-06" else f"{p}-15"
        append_point(tmp_path, SeriesPoint(
            indicatorId="d", period=p, value=10.0 + (i % 2), unit="u",
            publishedAt=published, capturedAt="2026-07-13",
            source=SeriesSource(url="https://x/y", title="t")))
    reg = _Reg([SeriesIndicatorSpec(id="d", side="demand", weight=1.0,
                                    polarityDemand=1, polaritySupply=0)])
    res = bt.run_backtest(reg, tmp_path, start="2023-01", end="2023-08")
    assert "2023-06" in res.months
    # the vintage property, asserted directly: at the June as-of the June point is
    # invisible (published 2023-09-20) — the newest visible period is May; by the
    # September as-of it has appeared.
    from gpu_agent.series_store import latest_by_period
    assert max(latest_by_period(tmp_path, "d", as_of="2023-06-30")) == "2023-05"
    assert "2023-06" in latest_by_period(tmp_path, "d", as_of="2023-09-25")
