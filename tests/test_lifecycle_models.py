import json
from gpu_agent.wiki.lifecycle import (
    PromotionCandidate, PruneCandidate, QuarantineEntry, LifecycleReport,
    AppliedSummary, LifecycleConfig, DEFAULT_LIFECYCLE_CONFIG)


def test_lifecycle_config_defaults():
    c = DEFAULT_LIFECYCLE_CONFIG
    assert c.min_persist_cycles == 2
    assert c.min_sources == 2
    assert c.stale_threshold == 0.1
    assert c.prune_salience_floor == 0.0


def test_models_construct():
    pc = PromotionCandidate(pageId="entity:nvda", type="entity", title="NVIDIA",
                            persistCycles=3, distinctSources=2,
                            verdict="persisted 3 cycles, 2 sources -> promote")
    pr = PruneCandidate(pageId="theme:cowos", type="theme", reason="stale: eff_salience 0.04")
    q = QuarantineEntry(pageId="entity:amd", status="provisional")
    a = AppliedSummary(promoted=1, pruned=1)
    assert pc.persistCycles == 3 and pc.distinctSources == 2
    assert pr.type == "theme"
    assert q.confidenceCapped is True and q.note == "not yet in coverage"
    assert a.promoted == 1 and a.pruned == 1


def test_lifecycle_report_roundtrip():
    report = LifecycleReport(
        asOf="2026-07",
        promotions=[PromotionCandidate(pageId="entity:nvda", type="entity", title="NVIDIA",
                                       persistCycles=2, distinctSources=2, verdict="promote")],
        prunes=[PruneCandidate(pageId="entity:x", type="entity", reason="stale")],
        quarantined=[QuarantineEntry(pageId="entity:nvda", status="provisional")],
        provisionalConsidered=1)
    blob = json.loads(report.model_dump_json())
    assert blob["asOf"] == "2026-07"
    assert blob["promotions"][0]["pageId"] == "entity:nvda"
    assert blob["quarantined"][0]["confidenceCapped"] is True
    assert blob["provisionalConsidered"] == 1
