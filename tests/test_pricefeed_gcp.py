# tests/test_pricefeed_gcp.py
from gpu_agent.pricefeed import _gcp_points

GCP_HEADER = ",name,sku_id,currency,price,rate_unit,date\n"
GCP_ROWS = [
    "0,Nvidia H100 80GB GPU running in Americas,AAA,USD,9.796550569,1h,260707",
    "1,H200 141GB GPU running in Americas,BBB,USD,9.31174,1h,260707",
    "2,A4 Nvidia B200 (1 gpu slice) running in Americas,CCC,USD,16.11,1h,260707",
    "3,Nvidia H100 80GB Plus GPU running in Americas,DDD,USD,10.344275712,1h,260707",
    # noise that MUST be excluded by the allow-list:
    "4,Commitment v1: Nvidia H100 80GB GPU running in Americas for 1 Year,EEE,USD,4.0,1h,260707",
    "5,Spot Nvidia H100 80GB GPU running in Americas,FFF,USD,3.0,1h,260707",
    "6,Nvidia H100 80GB GPU running in Frankfurt,GGG,USD,11.0,1h,260707",
    # older date for nearest-at/before
    "7,Nvidia H100 80GB GPU running in Americas,AAA,USD,9.0,1h,260601",
]


def _write(tmp_path):
    (tmp_path / "gcp_gpu_price.csv").write_text(
        GCP_HEADER + "\n".join(GCP_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_gcp_ondemand_americas_only_price_is_per_gpu(tmp_path):
    _write(tmp_path)
    pts = _gcp_points("2026-07-08", tmp_path)
    by_model = {}
    for p in pts:
        by_model.setdefault(p.model, []).append(p)
    # H100 base + "Plus" both kept (two SKUs), region Americas, per-GPU as-is
    h100 = sorted(p.usd_per_gpu_hour for p in by_model["H100"])
    assert h100 == [9.796551, 10.344276]               # rounded to 6dp; the 9.0/260601 row NOT chosen
    assert all(p.region == "Americas" and p.term == "on_demand" for p in pts)
    assert by_model["H200"][0].usd_per_gpu_hour == 9.31174
    assert by_model["B200"][0].usd_per_gpu_hour == 16.11


def test_gcp_excludes_commitment_spot_and_foreign_region(tmp_path):
    _write(tmp_path)
    prices = {p.usd_per_gpu_hour for p in _gcp_points("2026-07-08", tmp_path)}
    assert 4.0 not in prices and 3.0 not in prices and 11.0 not in prices


def test_gcp_has_no_custom_silicon(tmp_path):
    # documents the data fact: the GCP file contains NO TPU / custom silicon.
    _write(tmp_path)
    assert all(p.gpu_class == "gpu" for p in _gcp_points("2026-07-08", tmp_path))
