# tests/test_pricefeed_api.py
from gpu_agent.pricefeed import (
    load_points, headline_prices, price_delta, custom_silicon_series, lookback_label,
)

# reuse the per-adapter fixtures inline (small)
AWS = ("instance,term,region,260601,260707,260708\n"
       "p5.48xlarge,on_demand,US East (N. Virginia),50.0,55.04,55.04\n"       # H100 6.88
       "trn1.32xlarge,on_demand,US East (N. Virginia),21.5,21.5,21.5\n")      # Trainium1
ORACLE = (",Shape,GPUs,Architecture,Network,GPU Price Per Hour **,date\n"
          "0,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,n,$10.00,260707\n")
GCP = (",name,sku_id,currency,price,rate_unit,date\n"
       "0,Nvidia H100 80GB GPU running in Americas,A,USD,9.796550569,1h,260707\n")
CW = (",GPU Model,GPU Count,VRAM (GB),vCPUs,System RAM (GB),Local Storage (TB),"
      "Instance Price (Per Hour),date,On-Demand Price (Per Hour),Spot Price (Per Hour),"
      "Inference Single GPU Price(Per Hour),Region\n"
      "0,NVIDIA HGX H100,8,80,128,2048,61,$49.24,260305,,,,\n")   # stale (260305)


def _write_all(tmp_path):
    (tmp_path / "aws_price.csv").write_text(AWS, encoding="utf-8")
    (tmp_path / "oracle_gpu_price.csv").write_text(ORACLE, encoding="utf-8")
    (tmp_path / "gcp_gpu_price.csv").write_text(GCP, encoding="utf-8")
    (tmp_path / "coreweave_gpu_price.csv").write_text(CW, encoding="utf-8")
    return tmp_path


def test_load_points_unions_all_providers(tmp_path):
    _write_all(tmp_path)
    provs = {p.provider for p in load_points("2026-07-08", tmp_path)}
    assert provs == {"aws", "oracle", "gcp", "coreweave"}


def test_headline_price_is_median_of_provider_medians(tmp_path):
    _write_all(tmp_path)
    # fresh H100 provider medians: aws 6.88, oracle 10.0, gcp 9.796551; coreweave (260305) is stale (>45d) -> excluded
    # median of [6.88, 9.796551, 10.0] = 9.796551
    hp = headline_prices("2026-07-08", tmp_path, max_staleness_days=45)
    assert round(hp["H100"], 4) == 9.7966
    assert "B200" not in hp                      # no B200 in these fixtures


def test_stale_provider_included_when_window_widened(tmp_path):
    _write_all(tmp_path)
    # widen staleness so CoreWeave's 260305 point (124d before 260708) is admitted:
    # provider medians [aws 6.88, coreweave 6.155, gcp 9.796551, oracle 10.0] -> median = (6.88+9.796551)/2 = 8.338276
    hp = headline_prices("2026-07-08", tmp_path, max_staleness_days=400)
    assert round(hp["H100"], 4) == 8.3383


def test_custom_silicon_is_trainium_only(tmp_path):
    _write_all(tmp_path)
    cs = custom_silicon_series("2026-07-08", tmp_path)
    assert {p.model for p in cs} == {"Trainium1"}
    assert all(p.gpu_class == "custom_silicon" and p.provider == "aws" for p in cs)


def test_price_delta_since_last_week(tmp_path):
    _write_all(tmp_path)
    # AWS H100: 260708 uses 55.04 (6.88/gpu); a week back 2026-07-01 -> nearest col <=260701 is 260601 = 50.0 (6.25/gpu)
    # but oracle/gcp have no 260601 rows, so at lookback only AWS+CoreWeave(stale,excluded) -> H100 median = 6.25
    d = price_delta("2026-07-08", lookback_label("2026-07-08", 7), tmp_path, max_staleness_days=45)
    assert d["H100"]["current"] == round(headline_prices("2026-07-08", tmp_path)["H100"], 4)
    assert d["H100"]["prior"] == 6.25
    assert d["H100"]["abs_delta"] is not None


def test_determinism_same_asof_same_bytes(tmp_path):
    _write_all(tmp_path)
    a = load_points("2026-07-08", tmp_path)
    b = load_points("2026-07-08", tmp_path)
    assert a == b                                # frozen dataclasses compare by value
