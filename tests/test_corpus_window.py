import datetime

import pytest

from gpu_agent.corpus import (
    WINDOW_DAYS_DEFAULT, CorpusError, CorpusReport, CorpusResult, period_end, in_window,
)


def test_window_default_is_45():
    assert WINDOW_DAYS_DEFAULT == 45


def test_period_end_day_grain_is_itself():
    assert period_end("2026-07-03") == datetime.date(2026, 7, 3)


def test_period_end_month_grain_is_last_calendar_day():
    assert period_end("2026-07") == datetime.date(2026, 7, 31)
    assert period_end("2026-02") == datetime.date(2026, 2, 28)   # non-leap
    assert period_end("2028-02") == datetime.date(2028, 2, 29)   # leap


@pytest.mark.parametrize("bad", ["2026", "2026-13", "2026-00-01", "2026/07/03", "", "2026-07-32"])
def test_period_end_rejects_bad_labels(bad):
    with pytest.raises(CorpusError):
        period_end(bad)


def test_in_window_upper_bound_inclusive_lower_exclusive():
    # run asOf 2026-07 -> end 2026-07-31, start = end - 45d = 2026-06-16 (exclusive)
    assert in_window("2026-07-31", "2026-07", 45) is True     # == end
    assert in_window("2026-06-17", "2026-07", 45) is True     # start + 1
    assert in_window("2026-06-16", "2026-07", 45) is False    # == start (exclusive)
    assert in_window("2026-08-01", "2026-07", 45) is False    # future label excluded


def test_in_window_daily_finding_inside_flagship_month():
    # a July daily belongs to the July flagship's window by design (spec: window rule)
    assert in_window("2026-07-02", "2026-07", 45) is True


def test_in_window_month_grain_finding_uses_its_period_end():
    # June monthly findings (period end 2026-06-30) are in the July flagship's 45d window
    assert in_window("2026-06", "2026-07", 45) is True
    # but not in-window once the gap exceeds the window
    assert in_window("2026-04", "2026-07", 45) is False


def test_report_model_shape():
    r = CorpusReport(asOf="2026-07", category="chips.merchant-gpu", windowDays=45,
                     windowStart="2026-06-16", windowEnd="2026-07-31")
    assert r.storeIncluded == [] and r.outOfWindow == 0 and r.skippedPages == []
    assert r.freshNew == [] and r.freshUpdate == [] and r.freshDuplicate == []
    assert r.idOverlaps == [] and r.coverage == [] and r.notCovered == []
    res = CorpusResult(report=r)
    assert res.merged == [] and res.dedupedFresh == []
