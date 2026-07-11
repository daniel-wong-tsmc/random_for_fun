# tests/test_pricefeed_helpers.py
import pytest
from gpu_agent.pricefeed import (
    PricePoint, _label_to_yymmdd, _nearest_at_or_before, _money, _lead_int,
    _match_model, _vendor, lookback_label,
)


def test_label_to_yymmdd():
    assert _label_to_yymmdd("2026-07-08") == "260708"
    assert _label_to_yymmdd("2025-02-06") == "250206"


def test_nearest_at_or_before_exact():
    cols = ["260601", "260607", "260608", "260707", "260708"]
    assert _nearest_at_or_before("260708", cols) == "260708"


def test_nearest_at_or_before_gap_picks_prior():
    # target 260610 has no column -> nearest at/before is 260608
    cols = ["260601", "260607", "260608", "260707", "260708"]
    assert _nearest_at_or_before("260610", cols) == "260608"


def test_nearest_at_or_before_none_when_all_after():
    assert _nearest_at_or_before("250101", ["260601", "260708"]) is None


def test_money_strips_dollar_and_commas():
    assert _money("$68.80") == 68.8
    assert _money("$1,234.50") == 1234.5
    assert _money("") is None
    assert _money("  ") is None
    assert _money(None) is None


def test_lead_int_handles_footnote_pollution():
    assert _lead_int("16") == 16
    assert _lead_int("4^1") == 4      # CoreWeave footnote artifact
    assert _lead_int("") is None


def test_match_model_gb_prefix_not_confused_with_b():
    assert _match_model("NVIDIA GB200 NVL72") == "GB200"
    assert _match_model("8x Nvidia B200 180GB") == "B200"
    assert _match_model("NVIDIA HGX H100") == "H100"
    assert _match_model("8x NVIDIA H200 141GB Tensor Core") == "H200"
    assert _match_model("8x AMD MI300X 192GB Matrix Core") == "MI300X"
    assert _match_model("something unmapped") is None


def test_vendor_detects_amd():
    assert _vendor("8x AMD MI300X 192GB Matrix Core") == "amd"
    assert _vendor("8x NVIDIA H100 80GB Tensor Core") == "nvidia"


def test_lookback_label_is_calendar_days_before():
    assert lookback_label("2026-07-08", 1) == "2026-07-07"
    assert lookback_label("2026-07-08", 7) == "2026-07-01"
    assert lookback_label("2026-07-08", 30) == "2026-06-08"


def test_pricepoint_is_frozen():
    p = PricePoint(provider="aws", vendor="nvidia", model="H100", gpu_class="gpu",
                   region="US East (N. Virginia)", term="on_demand",
                   usd_per_gpu_hour=6.88, price_date="260708", as_of="2026-07-08",
                   instance="p5.48xlarge")
    with pytest.raises(Exception):
        p.usd_per_gpu_hour = 0.0
