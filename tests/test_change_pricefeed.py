# tests/test_change_pricefeed.py
"""Task 4: gpu_agent/change.py's price-feed adapter — the sole pricefeed seam.

DEVIATION (plan-sanctioned seam): the task-4 brief was written against an ASSUMED
Stage-5 interface (`pricefeed.read_prices(as_of, *, scrape_dir=...) -> list[PricePoint]`
with `.model/.usdPerGpuHour/.column/.custom`) that does not exist. The real Stage-5
(gpu_agent/pricefeed.py) ships `headline_prices(as_of, data_dir=..., max_staleness_days=45)
-> dict[model, usd]` (median-of-medians over fresh gpu-class points; custom silicon is
already excluded upstream) plus `PricePoint.usd_per_gpu_hour` / `.gpu_class` (snake_case).
These tests exercise the adapted `price_cells_from_feed` / `prices_by_lookback` against
that real shape — see gpu_agent/change.py for the mapping.
"""
from __future__ import annotations
import pytest

from gpu_agent import pricefeed
from gpu_agent.change import PriceCell, price_cells_from_feed, prices_by_lookback


def test_maps_dict_to_sorted_price_cells():
    def read(as_of, **kw):
        return {"B200": 3.99, "H100": 2.50}

    cells = price_cells_from_feed("2026-07-08", read=read)
    assert [c.model for c in cells] == ["B200", "H100"]     # sorted by model
    assert cells[0].usdPerGpuHour == 3.99
    assert cells[0].asOfColumn == "2026-07-08"               # requested label (no single column)
    assert cells[0].custom is False
    assert cells[1].usdPerGpuHour == 2.50


def test_maps_empty_dict_to_empty_list():
    cells = price_cells_from_feed("2026-07-08", read=lambda as_of, **kw: {})
    assert cells == []


def test_scrape_dir_maps_to_data_dir_kwarg_only_when_given():
    seen_kwargs = []

    def read(as_of, **kw):
        seen_kwargs.append(kw)
        return {}

    price_cells_from_feed("2026-07-08", read=read)                    # no scrape_dir
    price_cells_from_feed("2026-07-08", read=read, scrape_dir="/tmp/x")
    assert seen_kwargs == [{}, {"data_dir": "/tmp/x"}]


def test_prices_by_lookback_reads_all_four_columns():
    seen = []

    def read(as_of, **kw):
        seen.append(as_of)
        return {"B200": 4.0}

    got = prices_by_lookback("2026-07-08", read=read)
    # today (0) + 1 + 7 + 30 day offsets of period_end(2026-07-08)
    assert set(got) == {0, 1, 7, 30}
    assert seen == ["2026-07-08", "2026-07-07", "2026-07-01", "2026-06-08"]
    assert got[0] == [PriceCell(model="B200", usdPerGpuHour=4.0, asOfColumn="2026-07-08", custom=False)]


def test_prices_by_lookback_passes_scrape_dir_through():
    seen_kwargs = []

    def read(as_of, **kw):
        seen_kwargs.append(kw)
        return {}

    prices_by_lookback("2026-07-08", read=read, scrape_dir="/tmp/x")
    assert all(kw == {"data_dir": "/tmp/x"} for kw in seen_kwargs)
    assert len(seen_kwargs) == 4


def test_real_feed_default_read_is_headline_prices_and_excludes_custom_silicon():
    """Contract test against the REAL Stage-5 feed (default `read`, no stub). Read-only,
    deterministic (fixed as_of, never wall-clock). gpu_agent/scrape_data/ is gitignored, so
    a fresh checkout has no CSVs and the feed returns {} — that would make the assertions
    below vacuous, so skip honestly instead; the live check runs where the data exists."""
    cells = price_cells_from_feed("2026-07-08")
    if not cells:
        pytest.skip("no scrape data on this machine — live contract check runs where the feed data exists")
    for c in cells:
        assert c.model in pricefeed.HEADLINE_MODELS
        assert "Trainium" not in c.model
        assert c.custom is False


def test_import_check_real_stage5_names():
    from gpu_agent.pricefeed import headline_prices, lookback_label
    assert callable(headline_prices) and callable(lookback_label)
