"""Tests for gpu_agent/brief.py — render_market_caveat.

Task 3 of sub-project 4-5: per-category Market-State brief render.
"""
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence

from gpu_agent.brief import render_market_caveat


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ds(dmi: float = 0.05, smi: float = 0.02) -> DemandSupply:
    return DemandSupply(dmiContribution=dmi, smiContribution=smi)


def _sc(dmi: float = 0.05, smi: float = 0.02) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf="2026-06",
        findings=[],
        demandSupply=DemandSupply(dmiContribution=dmi, smiContribution=smi),
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
        indices=None,
        categoryStatus=None,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_market_caveat_reads_direction_not_level():
    out = render_market_caveat(_sc())
    assert "read DIRECTION, not level" in out
