"""tests/test_brief_report.py — Task 4 of sub-project 4-5.

Verifies that render_report composes the Market-State brief *first* (before the
detailed sections), and that the honesty / byte-stability invariants hold.
"""
from __future__ import annotations
import pathlib
from gpu_agent.report import render_report
from gpu_agent.cli import main
from gpu_agent.schema.scorecard import (
    Scorecard, DemandSupply, MarketIndices, Divergence, CategoryStatus,
)
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings
from gpu_agent.schema.finding import Kind, Impact, Evidence
from gpu_agent.wiki.movement import MarketMovement, StorylineRow


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ds(dmi: float = 0.05, smi: float = 0.02) -> DemandSupply:
    return DemandSupply(dmiContribution=dmi, smiContribution=smi)


def _f(fid: str = "f-001", *, side: str = "demand", indicatorId: str = "rpoBacklog",
       trend: str = "flat") -> Finding:
    return Finding(
        id=fid, statement="s", kind="observed", trend=trend, why="w",
        impact={"targets": ["t"], "direction": "positive", "mechanism": "m"},
        confidence={"level": "medium", "basis": "b"},
        asOf="2026-06", indicatorId=indicatorId, side=side,
        polarityDemand=1, polaritySupply=0,
        magnitude=2, entity="E", observedAt="2026-06",
        capturedAt="2026-06-12T00:00:00Z",
    )


def _sc(dmi: float = 0.05, smi: float = 0.02,
        indices: MarketIndices | None = None,
        category_status: CategoryStatus | None = None,
        findings: list | None = None) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf="2026-06",
        findings=findings or [],
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
        indices=indices,
        categoryStatus=category_status,
    )


def _reg():
    # the brief needs a registry only for the (unchanged) evidence-quality section.
    # IndicatorRegistry lives in gpu_agent.registry.indicators (confirmed against report.py:15).
    from gpu_agent.registry.indicators import IndicatorRegistry
    return IndicatorRegistry.load("registry/indicators.json")


def _rich_sc():
    ix = MarketIndices(momentum=_ds(dmi=0.07, smi=0.05), outlook=_ds(dmi=0.0, smi=0.0),
                       divergence=Divergence(state="insufficient-coverage", sdgiGap=0.0,
                                             outlookFindingCount=0, momentumFindingCount=3,
                                             note="no leading findings yet"))
    cs = CategoryStatus(rating="Strong", direction="improving",
                        bottleneck="advanced packaging (CoWoS)", reason="demand outruns ramp")
    return _sc(dmi=0.07, smi=0.05, indices=ix, category_status=cs,
               findings=[_f("d1", side="demand", indicatorId="rpoBacklog", trend="rising")])


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_render_report_is_brief_first():
    # Task 4 (5-2 output surgery) page order: THE CALLS leads, then STATE OF THE
    # MARKET, then WHY, then the WHAT MOVED -> DEMAND|SUPPLY board drill-down
    # (note: WHAT MOVED now comes BEFORE the board — swapped from the old order),
    # then the detail sections, with the trust footer caveat last.
    out = render_report(_rich_sc(), None, _reg(), render_ts="2026-07-01T00:00:00+00:00")
    i_calls = out.index("THE CALLS")
    i_state = out.index("STATE OF THE MARKET")
    i_why = out.index("WHY")
    i_moved = out.index("WHAT MOVED SINCE LAST RUN")
    i_board = out.index("DEMAND | SUPPLY")
    i_detail = out.index("ENTITY PANEL")         # an existing detailed section
    i_caveat = out.index("read DIRECTION, not level")
    assert i_calls < i_state < i_why < i_moved < i_board < i_detail < i_caveat


def test_render_report_honesty_invariant():
    # magnitude words appear only on the categoryStatus headline, never on the DMI/SMI lines
    out = render_report(_rich_sc(), None, _reg(), render_ts="t")
    for ln in out.splitlines():
        if "Demand momentum:" in ln or "Supply momentum:" in ln:
            for banned in ("strong", "accelerating", "weak", "slight", "moderate"):
                assert banned not in ln.lower()


def test_render_report_byte_stable():
    a = render_report(_rich_sc(), None, _reg(), render_ts="fixed")
    b = render_report(_rich_sc(), None, _reg(), render_ts="fixed")
    assert a == b


def test_cli_report_brief_first(tmp_path, capsys):
    p = tmp_path / "scorecard.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    # --scorecard is a REQUIRED flag (not positional); --registry defaults to registry/indicators.json
    rc = main(["report", "--scorecard", str(p), "--no-prior",
               "--render-ts", "2026-07-01T00:00:00+00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.index("STATE OF THE MARKET") < out.index("ENTITY PANEL")


def _story_movement():
    return MarketMovement(prevAsOf=None, moved=[], foldedCount=0, storylines=[
        StorylineRow(title="AMD", state="on-track", trajectory="accelerating",
                     lastUpdatedAsOf="2026-07", salience=0.8, provisional=False)])


def test_render_report_composes_store_sections_brief_first():
    out = render_report(_rich_sc(), None, _reg(), render_ts="t", movement=_story_movement())
    i_calls = out.index("THE CALLS")
    i_state = out.index("STATE OF THE MARKET")
    i_why = out.index("WHY")
    i_moved = out.index("WHAT MOVED SINCE LAST RUN")
    i_board = out.index("DEMAND | SUPPLY")
    i_story = out.index("STORYLINES (tracked over time)")
    i_detail = out.index("ENTITY PANEL")
    i_caveat = out.index("read DIRECTION, not level")
    assert i_calls < i_state < i_why < i_moved < i_board < i_story < i_detail < i_caveat
    assert "• AMD  on-track → accelerating" in out   # real storyline, not the stub


def test_render_report_movement_none_is_empty_state():
    out = render_report(_rich_sc(), None, _reg(), render_ts="t", movement=None)
    assert "WHAT MOVED SINCE LAST RUN" in out and "STORYLINES (tracked over time)" in out
    assert "no wiki store yet" in out
    assert "rendered in 4-5b" not in out             # the promissory stub is retired


def test_render_report_byte_stable_with_movement():
    a = render_report(_rich_sc(), None, _reg(), render_ts="fixed", movement=_story_movement())
    b = render_report(_rich_sc(), None, _reg(), render_ts="fixed", movement=_story_movement())
    assert a == b


def _seed_store(root: pathlib.Path):
    ws = WikiStore(root / "wiki", FindingStore(root / "findings"))
    f = Finding(id="f-nv", statement="s", kind=Kind.observed, trend="flat", why="w",
                impact=Impact(targets=["x"], direction="negative", mechanism="m"),
                evidence=[Evidence(source="src", url="u", date="2026-07", excerpt="e", tier="primary")],
                confidence=Confidence(level="medium", basis="b"), asOf="2026-07",
                indicatorId="rpoBacklog", side="demand", polarityDemand=1, polaritySupply=0,
                magnitude=3, entity="NVDA", observedAt="2026-07", capturedAt="2026-07-12")
    route_findings(ws, [f], as_of="2026-07")
    ws.update_header("entity:nvda", as_of="2026-07", status="registered")
    ws.record_state("entity:nvda", as_of="2026-07", state="hot", trajectory="rising", salience=0.9)


def test_cli_report_renders_storylines_from_store(tmp_path, capsys):
    _seed_store(tmp_path)
    p = tmp_path / "sc.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    rc = main(["report", "--scorecard", str(p), "--store", str(tmp_path), "--no-prior",
               "--render-ts", "2026-07-02T00:00:00+00:00"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STORYLINES (tracked over time)" in out
    assert "• NVDA  hot → rising" in out                       # real storyline from the store
    assert "no prior cycle to compare" in out                 # --no-prior → WHAT MOVED note


def test_cli_report_no_wiki_store_is_empty_state(tmp_path, capsys):
    p = tmp_path / "sc.json"
    p.write_text(_rich_sc().model_dump_json(), encoding="utf-8")
    rc = main(["report", "--scorecard", str(p), "--store", str(tmp_path), "--no-prior",
               "--render-ts", "t"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "no wiki store yet" in out                          # <store>/wiki absent → empty-state
