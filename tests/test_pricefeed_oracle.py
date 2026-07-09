# tests/test_pricefeed_oracle.py
from gpu_agent.pricefeed import _oracle_points

ORACLE_HEADER = ",Shape,GPUs,Architecture,Network,GPU Price Per Hour **,date\n"
ORACLE_ROWS = [
    "0,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,net,$10.00,260707",
    "1,BM.GPU.H200.8,8x Nvidia H200 141GB Tensor Core,Hopper,net,$10.00,260707",
    "2,BM.GPU.B200.8,8x Nvidia B200 180GB,Blackwell,net,$14.00,260707",
    "3,BM.GPU.MI300X.8,8x AMD MI300X 192GB Matrix Core,CDNA 3,net,$6.00,260707",
    # an older date to prove nearest-at/before + that stale rows aren't chosen when a newer exists
    "4,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,net,$9.50,260601",
]


def _write(tmp_path):
    (tmp_path / "oracle_gpu_price.csv").write_text(
        ORACLE_HEADER + "\n".join(ORACLE_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_oracle_price_is_already_per_gpu(tmp_path):
    _write(tmp_path)
    pts = {p.model: p for p in _oracle_points("2026-07-08", tmp_path)}
    assert pts["H100"].usd_per_gpu_hour == 10.0        # taken as-is, NOT divided by 8
    assert pts["H100"].price_date == "260707"          # newest at/before, not the 260601 row
    assert pts["B200"].usd_per_gpu_hour == 14.0
    assert pts["H100"].gpu_class == "gpu"


def test_oracle_classifies_amd_vendor(tmp_path):
    _write(tmp_path)
    mi = [p for p in _oracle_points("2026-07-08", tmp_path) if p.model == "MI300X"]
    assert mi and mi[0].vendor == "amd" and mi[0].gpu_class == "gpu"


def test_oracle_no_data_before_first_scrape(tmp_path):
    _write(tmp_path)
    assert _oracle_points("2025-01-01", tmp_path) == []   # all rows are after -> nothing at/before
