"""The human-facing Market-State brief (sub-project 4-5). Pure, deterministic
projection of a Scorecard — no LLM, no wiki store, no new number. Reuses report.py's
wording helpers so the brief and the detailed report speak the same vocabulary."""
from __future__ import annotations
from typing import Optional
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent import report   # module ref, resolved at call-time — avoids the report<->brief cycle

_ARROW = {"positive": "▲", "negative": "▼", "flat": "="}   # ▲ ▼ =


def _dir_arrow(value: float) -> str:
    return _ARROW[report._momentum_word(value)]


def render_state_of_market(sc: Scorecard, prior: Optional[Scorecard]) -> str:
    """STATE OF THE MARKET (BLUF): demand/supply momentum as direction + Δ (never an
    invented magnitude word on the unscaled index — Part 17), the SDGI gap wording, the
    brain's earned categoryStatus headline + binding constraint, and NOW/NEXT + divergence
    from the two indices. Optional fields degrade cleanly."""
    ds = sc.demandSupply
    sdgi = report.compute_sdgi(sc)
    p_dmi = prior.demandSupply.dmiContribution if prior else None
    p_smi = prior.demandSupply.smiContribution if prior else None
    p_sdgi = report.compute_sdgi(prior) if prior else None

    lines = ["STATE OF THE MARKET"]
    cs = sc.categoryStatus
    if cs is not None:
        lines.append(f"  {cs.rating}, {cs.direction} — {cs.reason}")
    lines.append(f"  Demand momentum: {report._momentum_word(ds.dmiContribution)} "
                 f"{_dir_arrow(ds.dmiContribution)}   "
                 f"(DMI {ds.dmiContribution:.3f}, Δ {report._fmt_delta(ds.dmiContribution, p_dmi)})")
    lines.append(f"  Supply momentum: {report._momentum_word(ds.smiContribution)} "
                 f"{_dir_arrow(ds.smiContribution)}   "
                 f"(SMI {ds.smiContribution:.3f}, Δ {report._fmt_delta(ds.smiContribution, p_smi)})")
    lines.append(f"  Gap: {report._sdgi_interpretation(sdgi)}   "
                 f"(SDGI {sdgi:.3f}, Δ {report._fmt_delta(sdgi, p_sdgi)})")

    ix = sc.indices
    if ix is not None:
        now = (f"demand {report._momentum_word(ix.momentum.dmiContribution)} "
               f"{_dir_arrow(ix.momentum.dmiContribution)} / "
               f"supply {report._momentum_word(ix.momentum.smiContribution)} "
               f"{_dir_arrow(ix.momentum.smiContribution)}")
        if ix.divergence.state == "insufficient-coverage":
            nxt = "insufficient coverage"
        else:
            nxt = (f"demand {report._momentum_word(ix.outlook.dmiContribution)} "
                   f"{_dir_arrow(ix.outlook.dmiContribution)} / "
                   f"supply {report._momentum_word(ix.outlook.smiContribution)} "
                   f"{_dir_arrow(ix.outlook.smiContribution)}")
        lines.append(f"  NOW (Momentum): {now}    NEXT (Outlook): {nxt}")
        if ix.divergence.state != "aligned":
            flag = "⚠ " if ix.divergence.state.startswith("diverging") else ""
            lines.append(f"  {flag}DIVERGENCE: {ix.divergence.note}")

    if cs is not None:
        lines.append(f"  BINDING CONSTRAINT: {cs.bottleneck}")
    return "\n".join(lines)
