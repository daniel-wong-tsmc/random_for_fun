# tests/test_pricefeed_aws.py
from gpu_agent.pricefeed import _aws_points

AWS_HEADER = "instance,term,region,250718,260601,260607,260608,260707,260708\n"
AWS_ROWS = [
    # p5 -> H100, 8 GPUs, N. Virginia present (and a pricier N. California to prove region pick)
    "p5.48xlarge,on_demand,US East (N. Virginia),55.04,55.04,55.04,55.04,55.04,55.04",
    "p5.48xlarge,on_demand,US West (N. California),68.8,68.8,68.8,68.8,68.8,68.8",
    "p5.48xlarge,reserved,US East (N. Virginia),40,40,40,40,40,40",          # non-on_demand -> skip
    # p5en -> H200, 8 GPUs
    "p5en.48xlarge,on_demand,US East (N. Virginia),63.296,63.296,63.296,63.296,63.296,63.296",
    # p6-b200 -> B200, 8 GPUs
    "p6-b200.48xlarge,on_demand,US East (N. Virginia),113.9328,113.9328,113.9328,113.9328,113.9328,113.9328",
    # trn1.32xlarge -> Trainium1 custom silicon, 16
    "trn1.32xlarge,on_demand,US East (N. Virginia),21.5,21.5,21.5,21.5,21.5,21.5",
    # trn2 -> only Ohio, blank in recent columns -> nearest non-blank at/before 260708 is 260607
    "trn2.48xlarge,on_demand,US East (Ohio),85.964,85.964,85.964,,,",
    # GB200 ultraserver -> only reserved local zone -> no on_demand US -> excluded
    "u-p6e-gb200x72,reserved,US East (Dallas) Local Zone,761.904,761.904,761.904,761.904,761.904,761.904",
    # foreign region only for an otherwise-mapped instance is still fine to skip via fallback
    "p6-b300.48xlarge,on_demand,Asia Pacific (Tokyo),160,160,160,160,160,160",  # no US -> skip
]


def _write_aws(tmp_path):
    (tmp_path / "aws_price.csv").write_text(AWS_HEADER + "\n".join(AWS_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_aws_normalizes_to_per_gpu_hour_and_picks_us_east(tmp_path):
    _write_aws(tmp_path)
    pts = {p.model: p for p in _aws_points("2026-07-08", tmp_path)}
    assert round(pts["H100"].usd_per_gpu_hour, 4) == 6.88          # 55.04 / 8, N. Virginia (not 68.8)
    assert pts["H100"].region == "US East (N. Virginia)"
    assert round(pts["H200"].usd_per_gpu_hour, 4) == 7.912         # 63.296 / 8
    assert round(pts["B200"].usd_per_gpu_hour, 4) == 14.2416       # 113.9328 / 8
    assert pts["H100"].price_date == "260708"
    assert pts["H100"].term == "on_demand"


def test_aws_trainium_is_custom_silicon(tmp_path):
    _write_aws(tmp_path)
    trn = [p for p in _aws_points("2026-07-08", tmp_path) if p.model == "Trainium1"]
    assert len(trn) == 1
    assert trn[0].gpu_class == "custom_silicon"
    assert trn[0].vendor == "aws"
    assert round(trn[0].usd_per_gpu_hour, 5) == 1.34375            # 21.5 / 16


def test_aws_blank_recent_cell_falls_back_to_nearest_prior(tmp_path):
    _write_aws(tmp_path)
    trn2 = [p for p in _aws_points("2026-07-08", tmp_path) if p.model == "Trainium2"]
    assert len(trn2) == 1
    assert trn2[0].price_date == "260607"                         # last non-blank <= 260708
    assert trn2[0].region == "US East (Ohio)"                     # fallback: no N. Virginia row


def test_aws_gb200_ultraserver_without_ondemand_us_is_excluded(tmp_path):
    _write_aws(tmp_path)
    models = {p.model for p in _aws_points("2026-07-08", tmp_path)}
    assert "GB200" not in models                                  # only reserved/local-zone existed
    assert "B300" not in models                                   # only APAC on_demand existed
