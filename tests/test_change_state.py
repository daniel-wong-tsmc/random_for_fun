from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Finding, Kind, Value, Impact, Evidence, Confidence
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import build_state, PriceCell, SCARCITY_INDICATORS, MONEY_INDICATORS


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(rating, direction="steady"):
    return DimensionRating(rating=rating, direction=direction, confidence=_conf(),
                           findingIds=[], rationale="r")


def _finding(iid, *, number=None, unit=None, statement="s", date="2026-05-05",
             captured="2026-07-08T00:00:00Z", observed="2026-05-05", mag=2, fid=None):
    return Finding(
        id=fid or f"{iid}-x-1", statement=statement, kind=Kind.measured,
        value=(Value(number=number, unit=unit) if number is not None else None),
        trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=date,
                           excerpt="e", tier="primary")],
        confidence=_conf(), asOf="2026-07-08", indicatorId=iid, side="demand",
        polarityDemand=1, polaritySupply=0, magnitude=mag, entity="nvidia",
        observedAt=observed, capturedAt=captured)


def _sc(as_of="2026-07-08", dmi=0.57, smi=0.29, dims=None, findings=None):
    return Scorecard(
        categoryId="chips.merchant-gpu", asOf=as_of,
        findings=findings or [],
        dimensionRatings=dims or {},
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n", confidence=_conf())


def _entry(eid="demand-durability", **kw):
    f = dict(id=eid, title="Demand outruns capacity",
             statement="Demand keeps outrunning capacity.", lens="demand",
             status="registered", conviction="high", lastVerdict="reaffirmed",
             lastDirection=0, streak=3, mechanism="m",
             falsifiableTrigger="Backlog growth falls below shipment growth.",
             sensitivity="capex", createdAsOf="2026-06", lastChangedAsOf="2026-07-05",
             lastJudgedAsOf="2026-07-05")
    f.update(kw)
    return ThesisEntry(**f)


def test_dimensions_and_indices_captured():
    sc = _sc(dmi=0.57, smi=0.29,
             dims={"momentum": _dim("Very strong", "improving"),
                   "moat": _dim("Mixed", "improving")})
    st = build_state(sc)
    assert st.asOf == "2026-07-08"
    assert st.dimensions["momentum"].rating == "Very strong"
    assert st.dimensions["momentum"].direction == "improving"
    assert st.demand == 0.57 and st.supply == 0.29
    # sdgi = dmi - smi when not stored
    assert abs(st.sdgi - 0.28) < 1e-9


def test_standing_theses_captured_retired_excluded():
    book = ThesisBook(categoryId="chips.merchant-gpu",
                      entries=[_entry(), _entry(eid="gone", status="retired")])
    st = build_state(_sc(), book=book)
    assert set(st.theses) == {"demand-durability"}
    cell = st.theses["demand-durability"]
    assert cell.conviction == "high" and cell.streak == 3 and cell.challenged is False


def test_headline_metrics_latest_vintage_and_age_source():
    old = _finding("grossMargin", number=53.0, unit="pct", date="2026-05-05",
                   captured="2026-07-04T00:00:00Z", fid="gm-old")
    new = _finding("grossMargin", number=55.0, unit="pct", date="2026-05-20",
                   captured="2026-07-08T00:00:00Z", fid="gm-new")
    lead = _finding("leadTimes", statement="lead times ~40 weeks", date="2026-06-30",
                    captured="2026-07-08T00:00:00Z", fid="lt-1")
    st = build_state(_sc(findings=[old, new, lead]))
    # latest vintage wins (captured 07-08 > 07-04)
    assert st.metrics["grossMargin"].value == 55.0
    assert st.metrics["grossMargin"].observedAt == "2026-05-20"   # newest evidence date -> age source
    assert st.metrics["grossMargin"].tier == "money"
    assert st.metrics["leadTimes"].tier == "scarcity"
    assert "grossMargin" in MONEY_INDICATORS and "leadTimes" in SCARCITY_INDICATORS


def test_prices_passed_through():
    prices = [PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-08")]
    st = build_state(_sc(), prices=prices)
    assert st.prices[0].model == "B200" and st.prices[0].usdPerGpuHour == 3.99


def test_category_status_projected_none_safe():
    # AMENDED 2026-07-11 (exec top band): categoryStatus fields ride the state vector.
    from gpu_agent.schema.scorecard import CategoryStatus
    sc = _sc()
    sc = sc.model_copy(update={"categoryStatus": CategoryStatus(
        rating="Strong", direction="worsening", bottleneck="bottleneck",
        reason="memory caps shipments")})
    st = build_state(sc)
    assert st.statusRating == "Strong" and st.statusDirection == "worsening"
    # constraintLabel is optional on CategoryStatus — absent -> None, never a crash
    assert st.constraintLabel is None or isinstance(st.constraintLabel, str)
    # a scorecard with NO categoryStatus at all stays None-safe
    bare = build_state(_sc())
    assert bare.statusRating is None and bare.constraintLabel is None
