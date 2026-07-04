"""Lane-polish (fix/lane-polish) render-fidelity tests.

Task 1 (F68b): CITATION MAP must render every evidence item for a finding,
not just the first — a finding corroborated by multiple publishers should
show all of its sources in the appendix, since that's the one place a
finding id traces back to its sources.

Task 2 (F68c): the BLUF "supply is the constraint" reconciliation note must
key off the scorecard's computed `demandSupply.sdgiDirection` (the actual
demand/supply-gap semantics), not the raw sign of `smiContribution`.
"""
from __future__ import annotations
import json
import copy
from pathlib import Path

from gpu_agent.report import render_citation_map
from gpu_agent.brief import render_state_of_market
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, CategoryStatus
from gpu_agent.schema.finding import Confidence

FIX = Path("fixtures/report")
POSTB = FIX / "postb-scorecard.json"


def test_citation_map_renders_all_evidence_items_for_a_finding():
    """A finding with two distinct evidence items must show BOTH sources in
    the citation map — today only f.evidence[0] renders, so the second
    publisher's corroboration is silently dropped from the one place ids
    trace back to sources."""
    raw = json.loads(POSTB.read_text("utf-8"))
    target = raw["findings"][0]
    second = copy.deepcopy(target["evidence"][0])
    second["source"] = "A Totally Different Publisher"
    second["date"] = "2026-05-01"
    second["tier"] = "secondary" if target["evidence"][0]["tier"] == "primary" else "primary"
    target["evidence"].append(second)

    sc = Scorecard.model_validate(raw)
    out = render_citation_map(sc)

    fid = target["id"]
    finding_lines = [l for l in out.splitlines() if l.strip().startswith(fid)]
    assert len(finding_lines) == 2, f"expected 2 lines for {fid!r}, got: {finding_lines!r}"
    assert any(target["evidence"][0]["source"][:60] in l for l in finding_lines)
    assert any("A Totally Different Publisher" in l for l in finding_lines)


def test_citation_map_single_evidence_finding_still_one_line():
    """A finding with exactly one evidence item still emits exactly one line
    (single-evidence findings must render byte-identically to before)."""
    sc = Scorecard.model_validate(json.loads(POSTB.read_text("utf-8")))
    single_ev_finding = next(f for f in sc.findings if len(f.evidence) == 1)
    out = render_citation_map(sc)
    finding_lines = [l for l in out.splitlines() if l.strip().startswith(single_ev_finding.id)]
    assert len(finding_lines) == 1


# ── Task 2 (F68c): BLUF reconciliation note keys off sdgiDirection ──────────

def _sc_with_ds(ds: DemandSupply, cs: CategoryStatus) -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu",
        asOf="2026-06",
        findings=[],
        demandSupply=ds,
        narrative="n",
        confidence=Confidence(level="medium", basis="b"),
        categoryStatus=cs,
    )


def _strong_catstat() -> CategoryStatus:
    return CategoryStatus(rating="Strong", direction="improving", bottleneck="bottleneck",
                          reason="r")


def test_reconciliation_note_renders_when_sdgi_direction_supply_led():
    # Supply is the binding gap per the scorecard's own sdgiDirection — the note
    # should render regardless of the raw smiContribution sign.
    ds = DemandSupply(dmiContribution=0.05, smiContribution=-0.02, sdgiDirection="supply-led")
    sc = _sc_with_ds(ds, _strong_catstat())
    out = render_state_of_market(sc, None)
    assert "supply is the constraint" in out


def test_reconciliation_note_omitted_when_balanced_despite_negative_smi():
    # A raw-sign proxy (smiContribution < 0) would wrongly fire here; the gap is
    # actually "balanced" per sdgiDirection, so the note must NOT render.
    ds = DemandSupply(dmiContribution=0.01, smiContribution=-0.01, sdgiDirection="balanced")
    sc = _sc_with_ds(ds, _strong_catstat())
    out = render_state_of_market(sc, None)
    assert "supply is the constraint" not in out
