from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Evidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _reg_hz():
    return (IndicatorRegistry.load("registry/indicators.json"),
            IndicatorHorizons.load("registry/indicators.json"))


def _f(fid, entity, indicatorId, *, as_of, magnitude=2, tier="secondary"):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        evidence=[Evidence(source="src", url="u", date=as_of, excerpt="e", tier=tier)],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt=as_of, capturedAt=as_of + "-12")


from gpu_agent.wiki.movement import collect_movement


def test_collect_ranks_moves_splits_storylines_and_never_writes(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    # cycle 1 (2026-05): NVDA — a scoring, leading, magnitude-3, primary finding; promote it to REGISTERED.
    route_findings(ws, [_f("f-nv1", "NVDA", "rpoBacklog", as_of="2026-05", magnitude=3, tier="primary")],
                   as_of="2026-05")
    ws.update_header("entity:nvda", as_of="2026-05", status="registered")
    ws.record_state("entity:nvda", as_of="2026-05", state="on-track", trajectory="accelerating", salience=0.9)
    # cycle 2 (2026-06): NVDA gets a new material finding; AMD is a NEW provisional overlay (low materiality).
    # F34: AMD's magnitude-1 D6 (price) finding still folds — (0.5 + 0.3*1) * 0.6 * 1.0 * 1.0 * 0.5
    # = 0.24 < 0.3 — a low-magnitude price-only thread stays quiet even though non-scoring
    # activity now counts (a magnitude-2+ overlay would clear the threshold; see test_w2_lane_f.py).
    route_findings(ws, [_f("f-nv2", "NVDA", "rpoBacklog", as_of="2026-06", magnitude=3, tier="primary"),
                        _f("f-amd", "AMD", "D6", as_of="2026-06", magnitude=1)], as_of="2026-06")
    ws.record_state("entity:amd", as_of="2026-06", state="watch", trajectory="softening", salience=0.4)

    before = len(ws.log.read())
    mv = collect_movement(ws, as_of="2026-06", prev_as_of="2026-05", registry=reg, horizons=hz)
    assert len(ws.log.read()) == before                      # READ-ONLY: no lint/log write

    assert mv.prevAsOf == "2026-05"                           # carries the diff's prev cycle
    # NVDA is material (scoring/leading/primary); AMD (overlay) falls below threshold -> folded.
    assert mv.moved, "expected at least one material move"
    top = mv.moved[0]
    assert top.findingIds == ["f-nv2"]           # NVDA's this-cycle finding is the citation
    assert top.tier == "primary"                 # derived from tierMult
    assert top.provisional is False               # entity:nvda was promoted to registered
    assert mv.foldedCount >= 1                    # AMD overlay dropped below threshold

    # STORYLINES: entity:nvda registered (canonical), entity:amd provisional (confidence-capped).
    reg_titles = [s.title for s in mv.storylines if not s.provisional]
    prov_titles = [s.title for s in mv.storylines if s.provisional]
    assert "NVDA" in reg_titles and "AMD" in prov_titles


def test_collect_no_prior_still_lists_storylines(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-nv", "NVDA", "rpoBacklog", as_of="2026-06", magnitude=3, tier="primary")],
                   as_of="2026-06")
    ws.record_state("entity:nvda", as_of="2026-06", state="hot", trajectory="rising", salience=0.8)
    mv = collect_movement(ws, as_of="2026-06", prev_as_of=None, registry=reg, horizons=hz)
    assert mv.prevAsOf is None
    assert mv.moved == [] and mv.foldedCount == 0     # no diff without a prior cycle
    assert any(s.title == "NVDA" for s in mv.storylines)   # storylines still render


def test_collect_empty_store_is_empty(tmp_path):
    reg, hz = _reg_hz()
    ws = _store(tmp_path)
    mv = collect_movement(ws, as_of="2026-06", prev_as_of="2026-05", registry=reg, horizons=hz)
    assert mv.moved == [] and mv.storylines == [] and mv.foldedCount == 0
