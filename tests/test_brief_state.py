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
                          reason="demand outruns the packaging ramp",
                          constraintLabel="advanced packaging (CoWoS)")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_state_header_full():
    # Task 4 (5-2 output surgery): Demand/Supply lines are now words-first bands
    # (gpu_agent.bands.band_with_prior) — the raw "DMI 0.070, Δ +0.030" parenthetical
    # this test used to pin here has moved to the TRUST & COVERAGE footer table
    # (see tests/test_report_surgery.py's DMI-only-in-footer scenario).
    prior = _sc(dmi=0.04, smi=0.05)
    sc = _sc(dmi=0.07, smi=0.05, indices=_indices(), category_status=_catstat())
    out = render_state_of_market(sc, prior)
    assert "STATE OF THE MARKET" in out
    assert "Strong, improving" in out                 # categoryStatus headline
    assert "demand outruns the packaging ramp" in out
    assert "Demand: FIRM ▲ (was FLAT)" in out          # band_word(0.07)=firm, band_word(0.04)=flat, rose
    assert "Supply: FIRM = (was FIRM)" in out          # band_word(0.05)=firm both cycles, unchanged
    assert "Gap: Demand and supply roughly balanced" in out
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
    assert "Demand: " in out                 # scorecard demandSupply still renders (band word)
    assert "NOW (Momentum)" not in out       # no indices -> no NOW/NEXT
    assert "BINDING CONSTRAINT" not in out   # no categoryStatus -> no binding line


def test_no_unearned_magnitude_word_on_demand_supply_lines():
    # Honesty (Part 17, band-map release): the Demand/Supply band word is now earned
    # via gpu_agent.bands' fixed, retunable thresholds — "accelerating" is a legitimate
    # band word (dmi/smi=0.9 lands at/above the 0.30 floor), never an ad-hoc adjective
    # like "strong"/"weak"/"slight"/"moderate", which bands.py never produces.
    sc = _sc(dmi=0.9, smi=0.9, category_status=_catstat())  # large values -> ACCELERATING band
    out = render_state_of_market(sc, None)
    demand_line = [ln for ln in out.splitlines() if "Demand: " in ln][0]
    for banned in ("strong", "weak", "slight", "moderate"):
        assert banned not in demand_line.lower()
    assert "ACCELERATING" in demand_line     # earned via the >= 0.30 threshold, not invented


# ── F67 Task 5: BLUF constraint noun + reconciliation note ──────────────────

def test_constraint_line_uses_label_never_dimension():
    # constraintLabel is the plain-language physical/market constraint name; the
    # binding-constraint line must render it, never the dimension-name bottleneck.
    cs = CategoryStatus(rating="Strong", direction="improving", bottleneck="bottleneck",
                        reason="r", constraintLabel="CoWoS/HBM3E advanced packaging")
    sc = _sc(category_status=cs)
    out = render_state_of_market(sc, None)
    assert "BINDING CONSTRAINT: CoWoS/HBM3E advanced packaging" in out


def test_constraint_line_omitted_without_label():
    cs = CategoryStatus(rating="Strong", direction="improving", bottleneck="bottleneck",
                        reason="r")   # no constraintLabel
    sc = _sc(category_status=cs)
    out = render_state_of_market(sc, None)
    assert "BINDING CONSTRAINT" not in out          # honest omission, no jargon leak


def test_reconciliation_note_when_strong_but_supply_negative():
    cs = CategoryStatus(rating="Strong", direction="improving", bottleneck="bottleneck",
                        reason="r")
    sc = _sc(smi=-0.45, category_status=cs)
    out = render_state_of_market(sc, None)
    assert "supply is the constraint" in out
