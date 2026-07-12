import pytest
from gpu_agent.series_store import SeriesPoint, SeriesSource, append_point, read_series


def _pt(period, value, published, captured=None, **kw):
    return SeriesPoint(indicatorId="hbmSupplyCapex", period=period, value=value, unit="pct_yoy",
                       publishedAt=published, capturedAt=(captured or published),
                       source=SeriesSource(url="https://x/y", title="t"), **kw)


def test_append_then_read_roundtrip(tmp_path):
    p = _pt("2024-01", 12.5, "2024-02-10")
    append_point(tmp_path, p)
    got = read_series(tmp_path, "hbmSupplyCapex")
    assert len(got) == 1
    assert got[0].value == 12.5
    assert got[0].period == "2024-01"
    assert got[0].estimateGrade is False


def test_period_must_be_year_month(tmp_path):
    with pytest.raises(ValueError):
        _pt("2024-1", 1.0, "2024-02-10")   # not zero-padded YYYY-MM


def test_revision_later_vintage_wins(tmp_path):
    append_point(tmp_path, _pt("2024-01", 10.0, "2024-02-10"))
    append_point(tmp_path, _pt("2024-01", 11.0, "2024-05-10"))   # revision of the same period
    from gpu_agent.series_store import latest_by_period
    latest = latest_by_period(tmp_path, "hbmSupplyCapex")
    assert latest["2024-01"].value == 11.0


def test_as_of_hides_later_vintage(tmp_path):
    append_point(tmp_path, _pt("2024-01", 10.0, "2024-02-10"))
    append_point(tmp_path, _pt("2024-01", 11.0, "2024-05-10"))
    from gpu_agent.series_store import latest_by_period
    at_march = latest_by_period(tmp_path, "hbmSupplyCapex", as_of="2024-03-01")
    assert at_march["2024-01"].value == 10.0   # the May revision is in the future at as_of
