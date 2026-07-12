from __future__ import annotations
import datetime
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence
from gpu_agent.change import nearest_run_at_or_before


def _write(store, as_of, version, dmi=0.5, smi=0.3):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
                   narrative="n", confidence=Confidence(level="medium", basis="b"))
    (cat / f"{as_of}-v{version}.json").write_text(sc.model_dump_json(), "utf-8")


def test_exact_day_hit(tmp_path):
    _write(tmp_path, "2026-07-01", 1)
    _write(tmp_path, "2026-07-07", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 7))
    assert got.name == "2026-07-07-v1.json"


def test_skipped_day_falls_back_to_nearest_before(tmp_path):
    # target is 07-07 but only 07-05 exists at/before it -> nearest at/before wins.
    _write(tmp_path, "2026-07-01", 1)
    _write(tmp_path, "2026-07-05", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 7))
    assert got.name == "2026-07-05-v1.json"


def test_highest_version_same_day(tmp_path):
    _write(tmp_path, "2026-07-05", 1)
    _write(tmp_path, "2026-07-05", 2)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 6))
    assert got.name == "2026-07-05-v2.json"


def test_month_grain_period_end(tmp_path):
    # month-grain 2026-06 has period-end 2026-06-30 -> counts as at/before a July target.
    _write(tmp_path, "2026-06", 12)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 1))
    assert got.name == "2026-06-v12.json"


def test_nothing_at_or_before_returns_none(tmp_path):
    _write(tmp_path, "2026-07-10", 1)
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu", datetime.date(2026, 7, 1))
    assert got is None


def test_before_excludes_current_run(tmp_path):
    _write(tmp_path, "2026-07-08", 1)
    _write(tmp_path, "2026-07-08", 2)
    # exclude the current (2026-07-08, v2); nearest strictly-below is v1 same day.
    got = nearest_run_at_or_before(tmp_path, "chips.merchant-gpu",
                                   datetime.date(2026, 7, 8), before=("2026-07-08", 2))
    assert got.name == "2026-07-08-v1.json"


def test_missing_category_dir_returns_none(tmp_path):
    assert nearest_run_at_or_before(tmp_path, "nope", datetime.date(2026, 7, 1)) is None
