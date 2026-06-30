import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.wiki.lint import health_report, DEFAULT_LINT_CONFIG
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, indicatorId="gpuSpotPrice"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


_HZ = IndicatorHorizons.load("registry/indicators.json")


def test_health_orphans(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06", body="")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    ws.update_header("entity:nvda", as_of="2026-06", crossRefs=["entity:amd"])
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    # amd is referenced by nvda -> not orphan ; nvda has no inbound ref -> orphan
    assert "entity:nvda" in h.orphans and "entity:amd" not in h.orphans


def test_health_asymmetric_crossref(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06", body="")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    ws.update_header("entity:nvda", as_of="2026-06", crossRefs=["entity:amd"])
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    gaps = [(g.source, g.target, g.reason) for g in h.crossRefGaps]
    assert ("entity:nvda", "entity:amd", "asymmetric") in gaps


def test_health_mention_without_link(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06",
                   body="## NVDA\nCompetes with AMD on data-center GPUs.\n")
    ws.create_page("entity:amd", "entity", "AMD", as_of="2026-06", body="")
    h = health_report(ws, as_of="2026-06", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    gaps = [(g.source, g.target, g.reason) for g in h.crossRefGaps]
    assert ("entity:nvda", "entity:amd", "mention-without-link") in gaps


def test_health_stale_excludes_fresh(tmp_path):
    ws = _store(tmp_path)
    # OLD page: daily-tagged finding (half-life 1), salience 0.5, quiet for 4 cycles -> eff 0.03125 < 0.1
    ws.create_page("entity:old", "entity", "OLD", as_of="2026-04")
    ws.findings.append(_f("f1", "OLD", "gpuSpotPrice"))   # daily -> H_short
    ws.append_observation("entity:old", "f1", as_of="2026-04")
    ws.record_state("entity:old", as_of="2026-04", state="x", trajectory="y", salience=0.5)
    for cyc in ("2026-05", "2026-06", "2026-07", "2026-08"):
        ws.create_page(f"entity:c{cyc}", "entity", cyc, as_of=cyc)  # later cycles, OLD stays quiet
    # FRESH page created this cycle, salience 0 (un-enriched), quiet_age 0 -> NOT stale
    h = health_report(ws, as_of="2026-08", contradictions={}, horizons=_HZ,
                      config=DEFAULT_LINT_CONFIG)
    stale_ids = [s.pageId for s in h.stale]
    assert "entity:old" in stale_ids
    assert "entity:c2026-08" not in stale_ids   # fresh this cycle -> excluded


def test_health_contradiction_rollup(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06")
    h = health_report(ws, as_of="2026-06", contradictions={"entity:nvda": "guidance cut"},
                      horizons=_HZ, config=DEFAULT_LINT_CONFIG)
    assert [(c.pageId, c.note, c.asOf) for c in h.contradictions] == \
        [("entity:nvda", "guidance cut", "2026-06")]
