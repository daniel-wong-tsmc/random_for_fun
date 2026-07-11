# tests/test_pricefeed_coreweave.py
from gpu_agent.pricefeed import _coreweave_points

CW_HEADER = (",GPU Model,GPU Count,VRAM (GB),vCPUs,System RAM (GB),Local Storage (TB),"
             "Instance Price (Per Hour),date,On-Demand Price (Per Hour),Spot Price (Per Hour),"
             "Inference Single GPU Price(Per Hour),Region\n")
CW_ROWS = [
    # priced rows carry a BLANK region (real-data quirk); price / count
    "0,NVIDIA HGX H100,8,80,128,2048,61,$49.24,260305,,,,",
    "1,NVIDIA HGX H200,8,141,128,2048,61,$50.44,260305,,,,",
    "2,NVIDIA B200,8,180,128,2048,61,$68.80,260305,,,,",
    # a later date where price went BLANK and Region got filled -> must be ignored (no price)
    "3,NVIDIA HGX H100,8,80,128,2048,61,,260707,,,,NORTH AMERICA",
]


def _write(tmp_path):
    (tmp_path / "coreweave_gpu_price.csv").write_text(
        CW_HEADER + "\n".join(CW_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_coreweave_per_gpu_and_nearest_priced_date(tmp_path):
    _write(tmp_path)
    pts = {p.model: p for p in _coreweave_points("2026-07-08", tmp_path)}
    assert round(pts["H100"].usd_per_gpu_hour, 4) == 6.155        # 49.24 / 8
    assert round(pts["B200"].usd_per_gpu_hour, 3) == 8.6          # 68.80 / 8
    # newest date is 260707 but its price is blank -> selects the last PRICED date 260305
    assert pts["H100"].price_date == "260305"
    assert pts["H100"].gpu_class == "gpu"
    assert "CoreWeave" in pts["H100"].region


def test_coreweave_before_first_priced_date_is_empty(tmp_path):
    _write(tmp_path)
    assert _coreweave_points("2026-01-01", tmp_path) == []
