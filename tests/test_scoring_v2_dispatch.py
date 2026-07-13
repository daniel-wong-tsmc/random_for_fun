"""F79 Task 3.2 — the scoring v2.0 version dispatch. The v1 path (dmi_smi_contribution)
is byte-identical (pinned by test_scoring_v1_replay_pin); v2 is an ADDITIVE entry point
that delegates to the series engine. Nothing user-facing consumes v2 before G4."""
import pytest
from gpu_agent import scoring
from gpu_agent.series_store import SeriesPoint, SeriesSource, append_point
from gpu_agent.series_registry import SeriesIndicatorSpec


def test_scoring_version_marks_v2():
    assert scoring.SCORING_VERSION == "2.0"


def _fill(root, ind, values, unit="u"):
    for i, v in enumerate(values):
        p = f"2025-{i + 1:02d}"
        append_point(root, SeriesPoint(
            indicatorId=ind, period=p, value=v, unit=unit,
            publishedAt=f"{p}-28", capturedAt="2026-07-13",
            source=SeriesSource(url="https://x/y", title="t")))


class _Reg:
    def __init__(self, specs):
        self.specs = {s.id: s for s in specs}


def test_score_v2_delegates_to_series_engine(tmp_path):
    _fill(tmp_path, "d", [1.0, 2.0, 3.0, 4.0])
    reg = _Reg([SeriesIndicatorSpec(id="d", side="demand", weight=0.5,
                                    polarityDemand=1, polaritySupply=0)])
    dmi, smi = scoring.score_v2(reg, tmp_path, as_of="2025-04-30")
    assert dmi == pytest.approx(1.0)   # z=2 x weight 0.5, fresh, lam 0
    assert smi == 0.0


def test_v1_path_signature_unchanged():
    """The v1 entry point keeps its exact signature — a dispatch, not a rewrite."""
    import inspect
    params = list(inspect.signature(scoring.dmi_smi_contribution).parameters)
    assert params == ["findings", "registry", "category_id", "weight_overrides"]
