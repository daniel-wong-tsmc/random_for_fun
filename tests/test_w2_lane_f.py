"""Wave-2 Lane F — brief/report + price track (F18, F29, F33, F34, F49, F51).

Tests are grouped by task, in plan order. Strict TDD: each task's tests are added and
proven failing before the corresponding implementation change lands.
"""
from __future__ import annotations

from gpu_agent.brief import _traj_arrow


# ── Task 1 (F18): trajectory arrows match TOKENS, not substrings ──────────────

def test_traj_arrow_supply_glut_worsening_is_down_not_up():
    # The review's bug: "up" is a substring of "supply", so naive substring matching
    # rendered UP (▲) for a sentence that is actually about a glut worsening (▼).
    assert _traj_arrow("supply glut worsening") == "▼"


def test_traj_arrow_shutdown_risk_is_unknown_not_down():
    # "down" is a substring of "shutdown" but not a standalone token.
    assert _traj_arrow("shutdown risk") == "·"


def test_traj_arrow_on_track_is_flat():
    assert _traj_arrow("on-track") == "="


def test_traj_arrow_tight_but_improving_is_up_precedence():
    # "tight" (FLAT) and "improving" (UP) both present — UP wins precedence.
    assert _traj_arrow("tight but improving") == "▲"
