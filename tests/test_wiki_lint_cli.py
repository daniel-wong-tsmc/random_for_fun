import json
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings, apply_enrichment, IngestResult, PageEnrichment
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import lint, DEFAULT_LINT_CONFIG
from gpu_agent.cli import main
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(root):
    return WikiStore(root / "wiki", FindingStore(root / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId="rpoBacklog", magnitude=3):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date="2026-06", excerpt="e", tier="primary")],
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def _seed_with_contradiction(ws):
    route_findings(ws, [_f("f-nv", "NVDA")], as_of="2026-06")
    apply_enrichment(ws, IngestResult(pages=[PageEnrichment(
        pageId="entity:nvidia", bodyMarkdown="## NVDA\nDC up [f-nv].\n", state="accelerating",
        trajectory="steady -> accelerating", contradictsThesis=True,
        contradictionNote="guidance cut")]), as_of="2026-06")


def test_lint_end_to_end_reads_contradiction(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    _seed_with_contradiction(ws)
    report = lint(ws, as_of="2026-06", registry=reg, horizons=hz, config=DEFAULT_LINT_CONFIG)
    nvda = [m for m in report.material if m.pageId == "entity:nvidia"]
    assert nvda and nvda[0].factors.contradiction is True
    assert [c.pageId for c in report.health.contradictions] == ["entity:nvidia"]


def test_lint_emits_one_idempotent_event(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    _seed_with_contradiction(ws)
    lint(ws, as_of="2026-06", registry=reg, horizons=hz)
    n = len([e for e in ws.log.read() if e.kind == "lint"])
    lint(ws, as_of="2026-06", registry=reg, horizons=hz)  # re-run
    assert n == 1
    assert len([e for e in ws.log.read() if e.kind == "lint"]) == 1


def test_lint_is_page_type_agnostic(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06")
    ws.findings.append(_f("f-t", "CoWoS", "leadTimes"))
    ws.append_observation("theme:cowos", "f-t", as_of="2026-06")
    report = lint(ws, as_of="2026-06", registry=reg, horizons=hz)
    assert any(m.pageId == "theme:cowos" and m.type == "theme"
               for m in report.material + report.dropped)


def test_wiki_lint_cli_prints_report(tmp_path, capsys):
    # seed a store via the wiki-ingest CLI, then lint it
    main(["wiki-ingest", "--findings", "fixtures/golden/findings.json",
          "--store", str(tmp_path), "--as-of", "2026-06"])
    capsys.readouterr()
    rc = main(["wiki-lint", "--store", str(tmp_path), "--as-of", "2026-06"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["asOf"] == "2026-06"
    assert "material" in report and "health" in report
