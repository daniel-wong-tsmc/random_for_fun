"""F79 Stage 6 — shadow wiring. Each live cycle records the v2 indices in the
scorecard's free-form provenance dict (string keys, additive — NOT a schema change) via
the append-only `v2-shadow` CLI verb; ONLY v1 renders until the G4 cutover.

Invariants pinned here: an empty/absent series store is a byte-identical no-op (older
and replayed cycles unchanged); stamping is idempotent and touches ONLY v2.* keys; the
exact as-of day is honored (no look-ahead inside the cycle month); and no render path
(report.py / reader.py) reads any v2.* provenance key.
"""
from __future__ import annotations
import json
import pathlib
import pytest
from gpu_agent import shadow
from gpu_agent.series_store import SeriesPoint, SeriesSource, append_point
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence


def _fill(root, ind, values, unit="u", pub_day="15"):
    for i, v in enumerate(values):
        p = f"2025-{i + 1:02d}"
        append_point(root, SeriesPoint(
            indicatorId=ind, period=p, value=v, unit=unit,
            publishedAt=f"{p}-{pub_day}", capturedAt="2026-07-13",
            source=SeriesSource(url="https://x/y", title="t")))


def _registry_file(tmp_path):
    reg = {"version": "1.0", "seriesIndicators": {
        "d": {"side": "demand", "weight": 0.5, "decayLambda": 0.0,
              "polarityDemand": 1, "polaritySupply": 0, "lifecycle": "active",
              "unit": "u"}}}
    p = tmp_path / "series-indicators.json"
    p.write_text(json.dumps(reg), encoding="utf-8")
    return p


def _scorecard(as_of="2025-05"):
    return Scorecard(
        categoryId="chips.merchant-gpu", asOf=as_of,
        demandSupply=DemandSupply(dmiContribution=0.1, smiContribution=0.0),
        narrative="n", confidence=Confidence(level="medium", basis="b"),
        provenance={"assignment": "asg.chips.merchant-gpu@1.1"})


def test_compute_v2_shadow_matches_engine(tmp_path):
    store = tmp_path / "series"
    _fill(store, "d", [1.0, 2.0, 3.0, 4.0])
    keys = shadow.compute_v2_shadow("2025-05", series_registry_path=_registry_file(tmp_path),
                                    series_root=store)
    assert set(keys) == {"v2.dmi", "v2.smi", "v2.sdgi", "v2.alertRaw"}
    # 2025-05: latest point 2025-04 (z=2, weight 0.5, lam 0, age 1mo but lam=0) -> dmi 1.0
    assert keys["v2.dmi"] == "1.000000"
    assert keys["v2.smi"] == "0.000000"
    assert keys["v2.sdgi"] == "1.000000"
    assert keys["v2.alertRaw"] in ("green", "yellow", "orange", "red")


def test_compute_v2_shadow_empty_store_is_empty_dict(tmp_path):
    keys = shadow.compute_v2_shadow("2025-05", series_registry_path=_registry_file(tmp_path),
                                    series_root=tmp_path / "series")   # dir absent
    assert keys == {}


def test_compute_v2_shadow_honors_exact_day_vintage(tmp_path):
    # the 2025-04 point publishes on the 15th; a cycle asOf 2025-04-10 must not see it
    store = tmp_path / "series"
    _fill(store, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _registry_file(tmp_path)
    early = shadow.compute_v2_shadow("2025-04-10", series_registry_path=reg, series_root=store)
    late = shadow.compute_v2_shadow("2025-04-15", series_registry_path=reg, series_root=store)
    assert late["v2.dmi"] == "1.000000"
    assert early["v2.dmi"] != late["v2.dmi"]


def test_stamp_scorecard_adds_only_v2_keys_and_is_idempotent(tmp_path):
    store = tmp_path / "series"
    _fill(store, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _registry_file(tmp_path)
    sc_path = tmp_path / "2025-05-v1.json"
    sc_path.write_text(_scorecard().model_dump_json(indent=2), encoding="utf-8")
    before = json.loads(sc_path.read_text("utf-8"))

    stamped = shadow.stamp_scorecard(sc_path, series_registry_path=reg, series_root=store)
    assert stamped is True
    after = json.loads(sc_path.read_text("utf-8"))
    assert after["provenance"]["v2.dmi"] == "1.000000"
    assert after["provenance"]["assignment"] == "asg.chips.merchant-gpu@1.1"
    # ONLY provenance changed, and only by v2.* keys
    prov_wo_v2 = {k: v for k, v in after["provenance"].items() if not k.startswith("v2.")}
    assert prov_wo_v2 == before["provenance"]
    assert {k: v for k, v in after.items() if k != "provenance"} == \
        {k: v for k, v in before.items() if k != "provenance"}

    bytes_once = sc_path.read_bytes()
    assert shadow.stamp_scorecard(sc_path, series_registry_path=reg, series_root=store) is True
    assert sc_path.read_bytes() == bytes_once    # idempotent


def test_stamp_scorecard_empty_store_leaves_file_untouched(tmp_path):
    sc_path = tmp_path / "2025-05-v1.json"
    sc_path.write_text(_scorecard().model_dump_json(indent=2), encoding="utf-8")
    before = sc_path.read_bytes()
    stamped = shadow.stamp_scorecard(sc_path, series_registry_path=_registry_file(tmp_path),
                                     series_root=tmp_path / "series")
    assert stamped is False
    assert sc_path.read_bytes() == before


def test_no_render_path_reads_v2_keys():
    """Nothing user-facing renders v2 before G4 — tripwire over the render sources."""
    for mod in ("gpu_agent/report.py", "gpu_agent/reader.py"):
        src = pathlib.Path(mod).read_text(encoding="utf-8")
        assert "v2." not in src, f"{mod} must not read v2 shadow keys before G4"
