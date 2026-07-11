# tests/test_corpus_coverage.py
from gpu_agent.corpus import CorpusReport, assemble, coverage, render_coverage_text
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import PageNotFound, WikiStore

REGISTRY = IndicatorRegistry.load("registry/indicators.json")
HZ = IndicatorHorizons({"designWins": {"cadence": "weekly", "horizon": "coincident"},
                        "rpoBacklog": {"cadence": "quarterly", "horizon": "lagging"}})


# local factories — repo convention, same block as tests/test_corpus_enumerate.py
def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _seed(store, f, as_of, category="chips.merchant-gpu", pid=None):
    pid = pid or f"entity:{f.entity.lower()}"
    try:
        store.get_page(pid)
    except PageNotFound:
        store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
    store.findings.append(f)
    store.append_observation(pid, f.id, as_of=as_of)


def test_coverage_entries_latest_and_count():
    fs = [
        _f("a-1", entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
           observedAt="2026-07-01"),
        _f("a-2", entity="NVDA", indicatorId="designWins", as_of="2026-07-03",
           observedAt="2026-07-03"),
        _f("b-1", entity="AMD", indicatorId="designWins", as_of="2026-07-02",
           observedAt="2026-07-01"),
    ]
    entries, not_covered = coverage(fs, REGISTRY)
    assert [(e.entity, e.indicatorId, e.count, e.latestAsOf) for e in entries] == [
        ("AMD", "designWins", 1, "2026-07-02"),
        ("NVDA", "designWins", 2, "2026-07-03"),
    ]
    assert "designWins" not in not_covered
    assert "rpoBacklog" in not_covered          # registered, zero windowed findings
    assert not_covered == sorted(not_covered)


def test_coverage_empty_store():
    entries, not_covered = coverage([], REGISTRY)
    assert entries == []
    assert set(not_covered) == set(REGISTRY.indicators)


def test_assemble_fills_coverage(tmp_path):
    store = _store(tmp_path)
    _seed(store, _f("store-1", as_of="2026-07-02", observedAt="2026-07-30"), "2026-07-02")
    res = assemble(tmp_path, "chips.merchant-gpu", "2026-07", [], REGISTRY, HZ)
    assert [e.indicatorId for e in res.report.coverage] == ["designWins"]
    assert "designWins" not in res.report.notCovered


def test_render_coverage_text_covered_and_gaps():
    report = CorpusReport(
        asOf="2026-07", category="chips.merchant-gpu", salienceFloor=0.1,
        storeIncluded=["a-1"],
        coverage=[{"entity": "NVDA", "indicatorId": "designWins", "count": 2,
                   "latestAsOf": "2026-07-03", "latestObservedAt": "2026-07-03"}],
        notCovered=["leadTimes", "rpoBacklog"])
    text = render_coverage_text(report)
    lines = text.splitlines()
    assert lines[0] == "STORE COVERAGE (aged, salience floor 0.1, 1 finding(s)):"
    assert "  NVDA designWins: 2 finding(s), latest asOf 2026-07-03 (observed 2026-07-03)" in lines
    assert "  not covered: leadTimes, rpoBacklog" in lines


def test_render_coverage_text_empty_store_names_full_gather():
    report = CorpusReport(asOf="2026-07", category="c", salienceFloor=0.1)
    assert "(no store coverage — full gather)" in render_coverage_text(report)


def test_render_deterministic():
    report = CorpusReport(asOf="2026-07", category="c", salienceFloor=0.1)
    assert render_coverage_text(report) == render_coverage_text(report)
