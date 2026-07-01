"""Tests for gpu_agent/brief.py — render_state_of_market (the BLUF).

Task 1 of sub-project 4-5: per-category Market-State brief render.
"""
from __future__ import annotations
from gpu_agent.schema.scorecard import (
    Scorecard, DemandSupply, MarketIndices, Divergence, CategoryStatus,
)
from gpu_agent.schema.finding import Confidence

from gpu_agent.brief import render_state_of_market


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ds(dmi: float = 0.05, smi: float = 0.02) -> DemandSupply:
    return DemandSupply(dmiContribution=dmi, smiContribution=smi)


def _f(fid: str = "f-001", indicator: str = "D2") -> dict:
    return {
        "id": fid, "statement": "s", "kind": "observed", "trend": "flat", "why": "w",
        "impact": {"targets": ["t"], "direction": "positive", "mechanism": "m"},
        "confidence": {"level": "medium", "basis": "b"}, "asOf": "2026-06",
        "indicatorId": indicator, "side": "demand", "polarityDemand": 1, "polaritySupply": 0,
        "magnitude": 2, "entity": "E", "observedAt": "2026-06",
        "capturedAt": "2026-06-12T00:00:00Z",
    }


def _sc(dmi: float = 0.05, smi: float = 0.02,
        indices: MarketIndices | None = None,
        category_status: CategoryStatus | None = None) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf="2026-06",
        findings=[],
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
        indices=indices,
        categoryStatus=category_status,
    )


def _indices(*, mom=(0.07, 0.05), out=(0.0, 0.0), div_state="insufficient-coverage",
             note="outlook has no leading findings yet"):
    return MarketIndices(
        momentum=_ds(dmi=mom[0], smi=mom[1]),
        outlook=_ds(dmi=out[0], smi=out[1]),
        divergence=Divergence(state=div_state, sdgiGap=0.0, outlookFindingCount=0,
                              momentumFindingCount=3, note=note))


def _catstat():
    return CategoryStatus(rating="Strong", direction="improving",
                          bottleneck="advanced packaging (CoWoS)",
                          reason="demand outruns the packaging ramp")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_state_header_full():
    prior = _sc(dmi=0.04, smi=0.05)
    sc = _sc(dmi=0.07, smi=0.05, indices=_indices(), category_status=_catstat())
    out = render_state_of_market(sc, prior)
    assert "STATE OF THE MARKET" in out
    assert "Strong, improving" in out                 # categoryStatus headline
    assert "demand outruns the packaging ramp" in out
    assert "Demand momentum: positive" in out         # _momentum_word(0.07) == positive
    assert "Supply momentum: positive" in out         # _momentum_word(0.05) == positive (smi 0.05 > 0)
    assert "DMI 0.070" in out and "Δ +0.030" in out   # Δ vs prior 0.04
    assert "BINDING CONSTRAINT: advanced packaging (CoWoS)" in out


def test_now_next_and_divergence():
    sc = _sc(indices=_indices(div_state="insufficient-coverage"), category_status=_catstat())
    out = render_state_of_market(sc, None)
    assert "NOW (Momentum):" in out
    assert "NEXT (Outlook): insufficient coverage" in out   # honest until 4-4 feeds leading findings


def test_divergence_flagged_when_diverging():
    sc = _sc(indices=_indices(div_state="diverging-weakening",
                              note="trailing strong; one forward signal softened"),
             category_status=_catstat())
    out = render_state_of_market(sc, None)
    assert "DIVERGENCE" in out and "softened" in out


def test_degrades_without_categorystatus_or_indices():
    sc = _sc()  # no indices, no categoryStatus
    out = render_state_of_market(sc, None)
    assert "STATE OF THE MARKET" in out
    assert "Demand momentum:" in out         # scorecard demandSupply still renders
    assert "NOW (Momentum)" not in out       # no indices -> no NOW/NEXT
    assert "BINDING CONSTRAINT" not in out   # no categoryStatus -> no binding line


def test_no_magnitude_word_on_indices():
    # Honesty: the DMI/SMI momentum lines carry NO magnitude adjective.
    sc = _sc(dmi=0.9, smi=0.9, category_status=_catstat())  # large values, still only direction
    out = render_state_of_market(sc, None)
    demand_line = [ln for ln in out.splitlines() if "Demand momentum:" in ln][0]
    for banned in ("strong", "accelerating", "weak", "slight", "moderate"):
        assert banned not in demand_line.lower()
