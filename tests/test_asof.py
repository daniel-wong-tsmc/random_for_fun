import datetime
import pytest
from gpu_agent.asof import period_end, days_between, AsOfError


def test_period_end_day_grain():
    assert period_end("2026-07-08") == datetime.date(2026, 7, 8)


def test_period_end_month_grain_is_last_day():
    assert period_end("2026-07") == datetime.date(2026, 7, 31)
    assert period_end("2026-02") == datetime.date(2026, 2, 28)


def test_period_end_bad_shape_fails_loud():
    with pytest.raises(AsOfError):
        period_end("2026/07/08")


def test_days_between_month_labels():
    # Apr 30 -> Jun 30 = 61 days
    assert days_between("2026-06", "2026-04") == 61


def test_days_between_day_labels():
    assert days_between("2026-07-08", "2026-07-01") == 7


def test_days_between_same_label_is_zero():
    assert days_between("2026-07", "2026-07") == 0
