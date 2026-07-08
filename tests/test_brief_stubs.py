"""Tests for gpu_agent/brief.py — render_market_caveat.

Task 3 of sub-project 4-5: per-category Market-State brief render.
"""
from __future__ import annotations
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Confidence

from gpu_agent import reader
from gpu_agent.brief import render_market_caveat, gate_waivers_from_cycle_log


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
    # F67 Task 8: reworded to drop internal jargon ("the 4-4 memory") and the
    # off-allowlist all-caps word ("DIRECTION" -> "direction") — this caveat renders
    # above reader.APPENDIX_DIVIDER and must pass the acronym lint.
    out = render_market_caveat(_sc())
    assert "read direction, not level" in out
    assert "4-4 memory" not in out


# --- F75 (contract v1.4 companion): trust-footer gate-waiver disclosure ---

def test_clean_cycle_renders_no_waiver_line():
    out = render_market_caveat(_sc())
    assert "waiver" not in out.lower()


def test_bypass_waiver_renders_a_footer_line():
    line = ("a recorded waiver applied to the evidence-sufficiency check this cycle — "
            "read the affected calls with added caution")
    out = render_market_caveat(_sc(), gate_waivers=[line])
    assert line in out
    assert "read direction, not level" in out          # base caveat still present


def test_gate_waivers_from_cycle_log_extracts_only_bypasses():
    gates = {
        "sufficiency": "bypassed - moat Weak->Mixed forced by +0.50 anchor; --no-sufficiency; logged",
        "voiceLint": "all 3 judge samples re-dispatched once; all passed; NO bypass",
        "extract": "15 findings gated, 0 dropped, no re-dispatch",
    }
    waivers = gate_waivers_from_cycle_log(gates)
    assert len(waivers) == 1
    assert "evidence-sufficiency" in waivers[0]
    assert reader.lint_acronyms(waivers[0]) == []       # exec-readable, no off-allowlist acronyms


def test_gate_waivers_clean_cycle_is_empty():
    gates = {"sufficiency": "PASSED with no bypass - cited 3 distinct publishers",
             "voiceLint": "all passed on the re-dispatch; NO bypass"}
    assert gate_waivers_from_cycle_log(gates) == []


def test_gate_waivers_handles_missing_or_empty_gates():
    assert gate_waivers_from_cycle_log(None) == []
    assert gate_waivers_from_cycle_log({}) == []
