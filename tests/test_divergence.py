from gpu_agent.pipeline import _divergence
from gpu_agent.schema.scorecard import DemandSupply


def _ds(sdgi, direction):
    return DemandSupply(dmiContribution=0.0, smiContribution=0.0, sdgi=sdgi, sdgiDirection=direction)


def test_insufficient_coverage_when_outlook_below_floor():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.0, "balanced"), mom_count=4, out_count=0)
    assert d.state == "insufficient-coverage"
    assert "Outlook" in d.note and d.outlookFindingCount == 0


def test_aligned_when_directions_match():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.1, "demand-led"), mom_count=4, out_count=2)
    assert d.state == "aligned"


def test_diverging_weakening_when_outlook_more_supply_led():
    d = _divergence(_ds(0.3, "demand-led"), _ds(-0.1, "supply-led"), mom_count=4, out_count=2)
    assert d.state == "diverging-weakening"


def test_diverging_strengthening_when_outlook_more_demand_led():
    d = _divergence(_ds(-0.2, "supply-led"), _ds(0.2, "demand-led"), mom_count=4, out_count=2)
    assert d.state == "diverging-strengthening"


def test_sdgi_gap_is_outlook_minus_momentum():
    d = _divergence(_ds(0.3, "demand-led"), _ds(0.1, "demand-led"), mom_count=4, out_count=2)
    assert abs(d.sdgiGap - (0.1 - 0.3)) < 1e-9
