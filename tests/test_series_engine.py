"""F79 Task 3.3 — the series engine: z-scores (prior-history), same-class borrowing,
freshness decay, index composition, ΔSDGI momentum trigger, event impulses."""
import math
import pytest
from gpu_agent import series as eng
from gpu_agent.series_store import SeriesPoint, SeriesSource, append_point
from gpu_agent.series_registry import SeriesIndicatorSpec


def _pt(ind, period, value, published=None, unit="u"):
    return SeriesPoint(indicatorId=ind, period=period, value=value, unit=unit,
                       publishedAt=(published or f"{period}-28"), capturedAt="2026-07-13",
                       source=SeriesSource(url="https://x/y", title="t"))


def _spec(id, side, weight, *, polD=0, polS=0, lam=0.0, unit="u"):
    return SeriesIndicatorSpec(id=id, side=side, weight=weight, polarityDemand=polD,
                               polaritySupply=polS, decayLambda=lam, unit=unit)


# ---- decay + impulse ------------------------------------------------------------------

def test_decay_weight():
    assert eng.decay_weight(0.0, 0.4) == 1.0
    assert eng.decay_weight(1.0, 0.4) == pytest.approx(math.exp(-0.4))
    assert eng.decay_weight(3.0, 0.4) == pytest.approx(math.exp(-1.2))


def test_impulse_half_life():
    assert eng.impulse(0.0) == 1.0
    assert eng.impulse(8.0) == pytest.approx(0.5)
    assert eng.impulse(16.0) == pytest.approx(0.25)
    assert eng.impulse(4.0, half_life_weeks=4.0) == pytest.approx(0.5)


# ---- z-score against prior history ----------------------------------------------------

def test_zscore_latest_against_prior_history():
    # prior [1,2,3]: mean 2, sample std 1 -> x=4 gives z=2
    assert eng.zscore_latest([1.0, 2.0, 3.0, 4.0]) == pytest.approx(2.0)


def test_zscore_latest_insufficient_history_is_none():
    assert eng.zscore_latest([1.0, 2.0]) is None          # only 1 prior value
    assert eng.zscore_latest([1.0, 2.0, 3.0]) is None     # 2 priors < min 3


def test_zscore_latest_window_limits_history():
    # window=4 -> only the last 3 priors [11,12,13] count: mean 12, std 1, x=15 -> z=3
    vals = [100.0, 100.0, 11.0, 12.0, 13.0, 15.0]
    assert eng.zscore_latest(vals, window=4) == pytest.approx(3.0)


def test_zscore_latest_zero_std_is_none():
    assert eng.zscore_latest([2.0, 2.0, 2.0, 2.0]) is None


def test_zscore_with_borrow_uses_same_unit_pool():
    # young series: 1 prior value; pool provides the distribution (mean 10, std ~ sample)
    pool = [8.0, 9.0, 10.0, 11.0, 12.0, 10.0, 9.0, 11.0]
    import statistics
    expect = (14.0 - statistics.mean(pool)) / statistics.stdev(pool)
    assert eng.zscore_with_borrow([10.0, 14.0], pool) == pytest.approx(expect)


def test_zscore_with_borrow_prefers_own_history_when_filled():
    z = eng.zscore_with_borrow([1.0, 2.0, 3.0, 4.0], [100.0] * 20)
    assert z == pytest.approx(2.0)   # own prior [1,2,3], pool ignored


def test_zscore_with_borrow_no_pool_no_history_is_none():
    assert eng.zscore_with_borrow([1.0, 5.0], []) is None


# ---- ΔSDGI momentum trigger ------------------------------------------------------------

def test_delta_sdgi_fires_on_two_consecutive_big_moves():
    assert eng.delta_sdgi_trigger([0.0, 0.0, 0.0, 0.0, 10.0, 20.0]) is True


def test_delta_sdgi_no_fire_on_direction_flip():
    assert eng.delta_sdgi_trigger([0.0, 0.0, 0.0, 0.0, 10.0, 5.0]) is False


def test_delta_sdgi_no_fire_below_half_sigma():
    # wiggly history keeps sigma ~1; the last two moves are +0.05 each (cum 0.1 << 0.5σ)
    assert eng.delta_sdgi_trigger([1.0, -1.0, 1.0, -1.0, 1.0, 1.05, 1.1]) is False


def test_delta_sdgi_short_series_never_fires():
    assert eng.delta_sdgi_trigger([1.0, 2.0]) is False


# ---- index composition over a real (tmp) store ----------------------------------------

class _Reg:
    def __init__(self, specs):
        self.specs = {s.id: s for s in specs}


def _fill(root, ind, values, start_year=2025, unit="u"):
    for i, v in enumerate(values):
        m = i + 1
        append_point(root, _pt(ind, f"{start_year}-{m:02d}", v, unit=unit))


def test_compose_index_weights_polarity_and_z(tmp_path):
    # demand series d: [1,2,3,4] -> z=2, fresh (age 0), lam 0 -> dmi = 0.5*1*2 = 1.0
    # supply series s: [10,20,30,40] -> z=2, polS=-1     -> smi = 0.4*(-1)*2 = -0.8
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    _fill(tmp_path, "s", [10.0, 20.0, 30.0, 40.0], unit="w")
    reg = _Reg([_spec("d", "demand", 0.5, polD=1), _spec("s", "supply", 0.4, polS=-1, unit="w")])
    dmi, smi = eng.compose_index(reg, tmp_path, as_of="2025-04-30")
    assert dmi == pytest.approx(1.0)
    assert smi == pytest.approx(-0.8)


def test_compose_index_freshness_decay(tmp_path):
    # latest point 2025-04; as_of 2025-06 -> age 2 months, lam 0.4 -> factor exp(-0.8)
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _Reg([_spec("d", "demand", 0.5, polD=1, lam=0.4)])
    dmi, _ = eng.compose_index(reg, tmp_path, as_of="2025-06-30")
    assert dmi == pytest.approx(1.0 * math.exp(-0.8))


def test_compose_index_source_dark_three_months_zero_weight(tmp_path):
    # latest 2025-04; as_of 2025-08 -> age 4 months > 3 -> contributes 0
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _Reg([_spec("d", "demand", 0.5, polD=1)])
    dmi, smi = eng.compose_index(reg, tmp_path, as_of="2025-08-15")
    assert dmi == 0.0 and smi == 0.0


def test_compose_index_vintage_no_lookahead(tmp_path):
    # the 2025-04 point publishes 2025-04-28; an as_of before that must not see it
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _Reg([_spec("d", "demand", 0.5, polD=1)])
    dmi_before, _ = eng.compose_index(reg, tmp_path, as_of="2025-04-10")
    dmi_after, _ = eng.compose_index(reg, tmp_path, as_of="2025-04-28")
    assert dmi_after == pytest.approx(1.0)
    assert dmi_before != pytest.approx(1.0)   # April invisible; March is the latest


def test_compose_index_retired_lifecycle_excluded(tmp_path):
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    spec = _spec("d", "demand", 0.5, polD=1).model_copy(update={"lifecycle": "retired"})
    dmi, smi = eng.compose_index(_Reg([spec]), tmp_path, as_of="2025-04-30")
    assert dmi == 0.0 and smi == 0.0


def test_compose_index_with_impulses(tmp_path):
    # no series points at all; one demand impulse of weight 0.3, age 8 weeks -> 0.15
    reg = _Reg([])
    imps = [eng.Impulse(ageWeeks=8.0, weight=0.3, polarityDemand=1, polaritySupply=0)]
    dmi, smi = eng.compose_index(reg, tmp_path, as_of="2025-04-30", impulses=imps)
    assert dmi == pytest.approx(0.15)
    assert smi == 0.0
