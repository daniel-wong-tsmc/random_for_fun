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


# Regression (Task-7 real-data fix): the GB200/GB300 NVL72 rack shapes carry a GPUs
# free-text that names the constituent chip ("4 x Nvidia B200 189GB (NVL72)"). The pinned
# derived map (plan line 79) and self-review gap #2 require these to label as GB200/GB300
# (kept OUT of the B200/B300 headline), NOT be folded into the bare-B series.
GB_HEADER = ",Shape,GPUs,Architecture,Network,GPU Price Per Hour **,date\n"
GB_ROWS = [
    "0,BM.GPU.B200.8,8x NVIDIA B200 180GB Tensor Core,Blackwell,net,$14.00,260707",
    "1,BM.GPU.GB200.4,4 x Nvidia B200 189GB (NVL72),Blackwell,net,$16.00,260707",
    "2,BM.GPU.B300.8,8 x Nvidia B300 263GB,Blackwell,net,$15.00,260707",
    "3,BM.GPU.GB300.4,4 x Nvidia B300 279GB (NVL72),Blackwell,net,$18.00,260707",
    # legacy shape whose NAME lacks a model token -> must still resolve from the GPUs text
    "4,BM.GPU4.8,8x NVIDIA A100 40GB Tensor Core,Ampere,net,$3.05,260707",
]


def _write_gb(tmp_path):
    (tmp_path / "oracle_gpu_price.csv").write_text(
        GB_HEADER + "\n".join(GB_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_oracle_gb_superchip_shapes_not_folded_into_bare_b_series(tmp_path):
    _write_gb(tmp_path)
    by_model = {p.model: p for p in _oracle_points("2026-07-08", tmp_path)}
    assert set(by_model) == {"B200", "B300", "GB200", "GB300", "A100"}
    # the NVL72 rack SKUs are their own model, kept out of the bare-B headline series
    assert by_model["GB200"].usd_per_gpu_hour == 16.0
    assert by_model["GB300"].usd_per_gpu_hour == 18.0
    assert by_model["B200"].usd_per_gpu_hour == 14.0    # NOT 16.0 (GB200 not folded in)
    assert by_model["B300"].usd_per_gpu_hour == 15.0    # NOT 18.0
    # legacy shape whose name lacks a token still resolves via the GPUs text
    assert by_model["A100"].usd_per_gpu_hour == 3.05
