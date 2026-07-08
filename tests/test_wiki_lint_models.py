import json
from gpu_agent.wiki.lint import (
    IndicatorMove, MoveFactors, MaterialMove, CrossRefGap, ContradictionEntry,
    StaleEntry, HealthReport, LintReport, LintConfig, DEFAULT_LINT_CONFIG)


def test_lint_config_defaults():
    c = DEFAULT_LINT_CONFIG
    assert (c.w_contra, c.w_state, c.w_new, c.w_ind) == (1.0, 0.6, 0.5, 0.3)
    assert (c.h_short_days, c.h_med_days, c.h_long_days) == (7, 21, 120)
    assert c.material_threshold == 0.3
    assert c.stale_threshold == 0.1
    assert (c.tier_primary, c.tier_secondary) == (1.0, 0.6)
    assert (c.recency_full, c.recency_decayed) == (1.0, 0.7)
    assert c.salience_floor == 0.5
    assert c.horizon_boost_leading == 0.5


def test_crossrefgap_fields():
    g = CrossRefGap(source="entity:nvda", target="entity:amd", reason="asymmetric")
    assert (g.source, g.target, g.reason) == ("entity:nvda", "entity:amd", "asymmetric")


def test_lintreport_roundtrip():
    mv = MaterialMove(
        pageId="entity:nvda", title="NVDA", type="entity", status="provisional",
        score=1.05, factors=MoveFactors(newThread=True,
                                        indicatorMoves=[IndicatorMove(indicatorId="rpoBacklog",
                                                                      magnitude=3, scoring=True)]),
        contributingFindingIds=["f-1"], tierMult=1.0, recencyMult=1.0, effectiveSalience=0.0)
    report = LintReport(
        asOf="2026-06", prevAsOf=None, material=[mv], dropped=[],
        health=HealthReport(orphans=["entity:intc"],
                            stale=[StaleEntry(pageId="entity:old", effectiveSalience=0.04)],
                            crossRefGaps=[CrossRefGap(source="entity:nvda", target="entity:amd",
                                                      reason="mention-without-link")],
                            contradictions=[ContradictionEntry(pageId="entity:nvda",
                                                               note="guidance cut", asOf="2026-06")]))
    blob = json.loads(report.model_dump_json())
    assert blob["material"][0]["factors"]["indicatorMoves"][0]["scoring"] is True
    assert blob["health"]["crossRefGaps"][0]["source"] == "entity:nvda"
    assert blob["health"]["orphans"] == ["entity:intc"]
