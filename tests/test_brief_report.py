"""tests/test_brief_report.py — Task 4 of sub-project 4-5.

Verifies that render_report composes the Market-State brief *first* (before the
detailed sections), and that the honesty / byte-stability invariants hold.
"""
from __future__ import annotations
from gpu_agent.report import render_report
from gpu_agent.cli import main
from gpu_agent.schema.scorecard import (
    Scorecard, DemandSupply, MarketIndices, Divergence, CategoryStatus,
)
from gpu_agent.schema.finding import Finding, Confidence


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
    out = render_report(_rich_sc(), None, _reg(), render_ts="2026-07-01T00:00:00+00:00")
    i_state = out.index("STATE OF THE MARKET")
    i_board = out.index("DEMAND | SUPPLY")
    i_moved = out.index("WHAT MOVED SINCE LAST RUN")
    i_detail = out.index("ENTITY PANEL")         # an existing detailed section
    i_caveat = out.index("read DIRECTION, not level")
    assert i_state < i_board < i_moved < i_detail < i_caveat  # brief-first, caveat last


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
