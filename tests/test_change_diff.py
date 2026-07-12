# tests/test_change_diff.py
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, DimensionRating
from gpu_agent.schema.finding import Confidence
from gpu_agent.thesis import ThesisBook, ThesisEntry
from gpu_agent.change import build_state, build_change_report, diff_states, PriceCell


def _conf():
    return Confidence(level="medium", basis="b")


def _dim(rating, direction="steady"):
    return DimensionRating(rating=rating, direction=direction, confidence=_conf(),
                           findingIds=[], rationale="r")


def _sc(store, as_of, version, dmi, smi, dims):
    cat = store / "chips.merchant-gpu"
    cat.mkdir(parents=True, exist_ok=True)
    sc = Scorecard(categoryId="chips.merchant-gpu", asOf=as_of, findings=[],
                   dimensionRatings=dims,
                   demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
                   narrative="n", confidence=_conf())
    (cat / f"{as_of}-v{version}.json").write_text(sc.model_dump_json(), "utf-8")
    return sc


def _entry(**kw):
    f = dict(id="demand-durability", title="Demand outruns capacity",
             statement="s", lens="demand", status="registered", conviction="high",
             lastVerdict="strengthened", lastDirection=1, streak=3, mechanism="m",
             falsifiableTrigger="t", sensitivity="s", createdAsOf="2026-06",
             lastChangedAsOf="2026-07-08", lastJudgedAsOf="2026-07-08")
    f.update(kw)
    return ThesisEntry(**f)


def test_dimension_change_and_direction():
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      dimensionRatings={"momentum": _dim("Very strong", "improving")},
                      demandSupply=DemandSupply(dmiContribution=0.6, smiContribution=0.3),
                      narrative="n", confidence=_conf()))
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        dimensionRatings={"momentum": _dim("Strong", "steady")},
                        demandSupply=DemandSupply(dmiContribution=0.4, smiContribution=0.3),
                        narrative="n", confidence=_conf()))
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", None)
    dim = next(i for i in hd.items if i.key == "dim:momentum")
    assert dim.changed and dim.today.startswith("Very strong") and dim.prior.startswith("Strong")
    dem = next(i for i in hd.items if i.key == "index:demand")
    assert dem.changed and dem.direction == "up"
    sup = next(i for i in hd.items if i.key == "index:supply")
    assert not sup.changed and sup.direction == "same"


def test_thesis_moved_when_changed_after_prior_asof():
    book = ThesisBook(categoryId="c", entries=[_entry(lastChangedAsOf="2026-07-08")])
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()), book=book)
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                        narrative="n", confidence=_conf()))
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", book)
    th = next(i for i in hd.items if i.key == "thesis:demand-durability")
    assert th.changed and th.direction == "up"   # lastDirection 1 -> up


def test_thesis_not_moved_when_change_precedes_prior_asof():
    book = ThesisBook(categoryId="c", entries=[_entry(lastChangedAsOf="2026-06-20")])
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()), book=book)
    hd = diff_states("last week", 7, cur, cur, "2026-07-01", book)
    th = next(i for i in hd.items if i.key == "thesis:demand-durability")
    assert not th.changed


def test_price_change_uses_rel_tol():
    cur = build_state(Scorecard(categoryId="c", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf()),
                      prices=[PriceCell(model="B200", usdPerGpuHour=3.75, asOfColumn="2026-07-08")])
    prior = build_state(Scorecard(categoryId="c", asOf="2026-07-01", findings=[],
                        demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                        narrative="n", confidence=_conf()),
                        prices=[PriceCell(model="B200", usdPerGpuHour=3.99, asOfColumn="2026-07-01")])
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", None)
    price = next(i for i in hd.items if i.key == "price:B200")
    assert price.changed and price.direction == "down"


def test_build_change_report_three_horizons_and_unchanged_since(tmp_path):
    # Runs at -30d, -7d, -1d relative to 2026-07-08 (period-end math): 06-08, 07-01, 07-07.
    steady = {"moat": _dim("Mixed", "improving")}
    _sc(tmp_path, "2026-06-08", 1, 0.5, 0.3, steady)
    _sc(tmp_path, "2026-07-01", 1, 0.5, 0.3, steady)
    _sc(tmp_path, "2026-07-07", 1, 0.5, 0.3, steady)
    today = Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                      dimensionRatings=steady,
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf())
    rpt = build_change_report(tmp_path, today)
    assert [h.horizon for h in rpt.horizons] == ["yesterday", "last week", "last month"]
    assert [h.priorAsOf for h in rpt.horizons] == ["2026-07-07", "2026-07-01", "2026-06-08"]
    # moat never moved across all three sampled runs -> unchanged since the oldest (06-08).
    moat = next(i for i in rpt.horizons[0].items if i.key == "dim:moat")
    assert moat.changed is False
    assert moat.unchangedSince == "2026-06-08"


def test_build_change_report_no_run_at_horizon(tmp_path):
    _sc(tmp_path, "2026-07-07", 1, 0.5, 0.3, {})
    today = Scorecard(categoryId="chips.merchant-gpu", asOf="2026-07-08", findings=[],
                      demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                      narrative="n", confidence=_conf())
    rpt = build_change_report(tmp_path, today)
    last_month = next(h for h in rpt.horizons if h.horizon == "last month")
    assert last_month.priorAsOf is None and last_month.items == []


def test_constraint_rotation_item_and_priors_carried():
    # AMENDED 2026-07-11: status:constraint item + ChangeReport.priors for the top band.
    from gpu_agent.schema.scorecard import CategoryStatus

    def _sc_status(as_of, label):
        sc = Scorecard(categoryId="c", asOf=as_of, findings=[],
                       demandSupply=DemandSupply(dmiContribution=0.5, smiContribution=0.3),
                       narrative="n", confidence=_conf())
        return sc.model_copy(update={"categoryStatus": CategoryStatus(
            rating="Strong", direction="steady", bottleneck="b", reason="r",
            constraintLabel=label)})

    cur = build_state(_sc_status("2026-07-08", "HBM memory scarcity"))
    prior = build_state(_sc_status("2026-07-01", "export enforcement"))
    hd = diff_states("last week", 7, cur, prior, "2026-07-01", None)
    item = next(i for i in hd.items if i.key == "status:constraint")
    assert item.changed and item.today == "HBM memory scarcity" and item.prior == "export enforcement"
    # same label -> unchanged
    hd2 = diff_states("last week", 7, cur, cur, "2026-07-01", None)
    item2 = next(i for i in hd2.items if i.key == "status:constraint")
    assert item2.changed is False
