import json
from gpu_agent.gathering.dedup import (
    DroppedDoc, FindingClass, DedupResult, DedupReport, DedupConfig, DEFAULT_DEDUP_CONFIG)


def test_dedup_config_defaults():
    c = DEFAULT_DEDUP_CONFIG
    assert c.rel_tol == 0.01
    assert c.eps == 1e-9


def test_finding_class_and_result():
    r = DedupResult(
        new=[FindingClass(findingId="f-1", entity="NVDA", indicatorId="rpoBacklog", verdict="new")],
        update=[FindingClass(findingId="f-2", entity="AMD", indicatorId="gpuSpotPrice",
                             verdict="update", priorFindingId="f-0", detail="value 2.10 -> 2.35 (>1%)")],
        duplicate=[FindingClass(findingId="f-3", entity="INTC", indicatorId="S10",
                                verdict="duplicate", priorFindingId="f-prev",
                                detail="unchanged within tolerance")])
    assert [fc.findingId for fc in r.new] == ["f-1"]
    assert r.update[0].priorFindingId == "f-0"
    assert r.duplicate[0].verdict == "duplicate"


def test_dedup_report_roundtrip():
    report = DedupReport(
        asOf="2026-07",
        docsDroppedKnown=[DroppedDoc(url="http://x/a", reason="seen-url", firstSeenAsOf="2026-06")],
        findingsNew=[FindingClass(findingId="f-1", entity="NVDA", indicatorId="rpoBacklog", verdict="new")],
        findingsUpdate=[], findingsDuplicate=[])
    blob = json.loads(report.model_dump_json())
    assert blob["asOf"] == "2026-07"
    assert blob["docsDroppedKnown"][0]["reason"] == "seen-url"
    assert blob["findingsNew"][0]["entity"] == "NVDA"
