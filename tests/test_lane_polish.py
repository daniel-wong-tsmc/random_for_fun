"""Lane-polish (fix/lane-polish) render-fidelity tests.

Task 1 (F68b): CITATION MAP must render every evidence item for a finding,
not just the first — a finding corroborated by multiple publishers should
show all of its sources in the appendix, since that's the one place a
finding id traces back to its sources.
"""
from __future__ import annotations
import json
import copy
from pathlib import Path

from gpu_agent.report import render_citation_map
from gpu_agent.schema.scorecard import Scorecard

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
