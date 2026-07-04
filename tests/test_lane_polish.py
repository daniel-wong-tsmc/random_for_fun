"""Lane-polish (fix/lane-polish) render-fidelity tests.

Task 1 (F68b): CITATION MAP must render every evidence item for a finding,
not just the first — a finding corroborated by multiple publishers should
show all of its sources in the appendix, since that's the one place a
finding id traces back to its sources.

Task 2 (F68c): the BLUF "supply is the constraint" reconciliation note must
key off the scorecard's computed `demandSupply.sdgiDirection` (the actual
demand/supply-gap semantics), not the raw sign of `smiContribution`.

Task 3 (F68d): WHAT MOVED's folded-count line must not state the folded
count twice in the no-material-moves empty state.

Task 4 (F68e): label_ids_in_text must substitute indicator ids -> human
labels in ONE pass, so a future registry label that happens to embed
another id's literal token can never be re-substituted (no chaining).

Task 5 (F68a): lint_thesis_prose is a NEW deterministic post-hoc lint,
symmetrical to the judgment path's reader.lint_prose voice enforcement —
the thesis spec's Sec 2b voice rules (one-sentence statement/mechanism,
finding ids only in falsifiableTrigger) previously existed as prompt text
only, with no code check.
"""
from __future__ import annotations
import json
import copy
from pathlib import Path

from gpu_agent import reader
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.report import render_citation_map
from gpu_agent.brief import render_state_of_market, render_what_moved
from gpu_agent.schema.scorecard import Scorecard, DemandSupply, CategoryStatus
from gpu_agent.schema.finding import Confidence
from gpu_agent.wiki.movement import MarketMovement, MovedRow

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


# ── Task 3 (F68d): WHAT MOVED folded-count line must not double-state ───────

def _moved_row(**kw):
    base = dict(title="NVDA — hot (rising)", findingIds=["f-1"], tier="primary",
                provisional=False, newThread=True, contradiction=False,
                contradictionNote="", stateFrom=None, stateTo=None, score=1.0)
    base.update(kw)
    return MovedRow(**base)


def _movement(**kw):
    base = dict(prevAsOf="2026-06", moved=[], foldedCount=0, storylines=[])
    base.update(kw)
    return MarketMovement(**base)


def test_no_moves_folded_count_stated_once_not_twice():
    # No material moves + foldedCount > 0: the empty-state branch already owns the
    # folded message ("N below-threshold items folded") — the always-on tail must
    # not repeat it as "N lower-materiality items folded — see wiki-lint".
    mv = _movement(prevAsOf="2026-06", moved=[], foldedCount=3)
    out = render_what_moved(mv)
    assert out.count("folded") == 1


def test_moves_present_folded_tail_still_renders_once():
    # When there WERE material moves, the tail line is the only folded-count
    # mention — it must still render exactly once.
    mv = _movement(prevAsOf="2026-06", moved=[_moved_row()], foldedCount=3)
    out = render_what_moved(mv)
    assert out.count("folded") == 1
    assert "(3 lower-materiality items folded — see wiki-lint)" in out


# ── Task 4 (F68e): label_ids_in_text substitutes ids -> labels in ONE pass ──

def test_label_ids_in_text_single_pass_no_chaining_when_label_embeds_another_id():
    """If a future registry label for id A embeds id B's literal token, iterative
    substitution (looping over ids one at a time, re.sub-ing the whole text on
    each pass) would re-scan A's freshly-inserted label and wrongly relabel the
    embedded B token too. label_ids_in_text must substitute in exactly ONE pass
    over the ORIGINAL text so an inserted label is never re-scanned."""
    stub = IndicatorRegistry({
        "ALPHA-ID": {"label": "compute change vs BETA index"},
        "BETA": {"label": "capacity utilization"},
    })
    out = reader.label_ids_in_text("Track ALPHA-ID and BETA this week.", stub)

    # A's label renders once, verbatim — including its embedded literal "BETA"
    # token, which must NOT be re-substituted just because it also matches id B.
    assert out.count("compute change vs BETA index") == 1
    # B's own standalone occurrence IS substituted — exactly once.
    assert out.count("capacity utilization") == 1
    assert out == "Track compute change vs BETA index and capacity utilization this week."


def test_label_ids_in_text_existing_no_collision_render_stays_byte_identical():
    """Pin: a real, no-collision 'breaks if' style trigger naming two distinct
    registry indicator ids renders exactly as it did before the single-pass
    change (existing behavior for the no-collision case must not move)."""
    reg = IndicatorRegistry.load("registry/indicators.json")
    text = "The D6 track shows a decline while S10 tightens across the chain."
    out = reader.label_ids_in_text(text, reg)
    assert out == (
        "The GPU rental price track shows a decline "
        "while Whole-chain inventory tightens across the chain."
    )


# ── Task 5 (F68a): lint_thesis_prose — deterministic thesis-prose lint ──────

from gpu_agent.thesis import lint_thesis_prose

_CLEAN_STATEMENT = "Merchant GPU demand stays firm through the cycle."
_CLEAN_MECHANISM = "Hyperscaler capex commitments convert to shipments with a lag."


def test_lint_thesis_prose_flags_multi_sentence_statement():
    """statement must fit in exactly one sentence, same cap the judge path enforces
    on narrative/rationale fields via reader.lint_prose(..., max_sentences=N)."""
    two_sentence_statement = (
        "Merchant GPU demand stays firm through the cycle. Backlog growth confirms it."
    )
    violations = lint_thesis_prose(two_sentence_statement, _CLEAN_MECHANISM)
    assert any(v.startswith("statement:") and "sentences" in v for v in violations)


def test_lint_thesis_prose_flags_multi_sentence_mechanism():
    two_sentence_mechanism = (
        "Hyperscaler capex commitments convert to shipments with a lag. "
        "The lag is roughly two quarters."
    )
    violations = lint_thesis_prose(_CLEAN_STATEMENT, two_sentence_mechanism)
    assert any(v.startswith("mechanism:") and "sentences" in v for v in violations)


def test_lint_thesis_prose_flags_finding_id_in_statement():
    """Finding ids belong ONLY in falsifiableTrigger (spec Sec 2b voice rule) — one
    leaking into statement is a violation naming the field, mirroring lint_prose's
    existing finding-id check reused (not reimplemented) here."""
    statement_with_finding_id = (
        "Backlog strength is corroborated by nvidia-earnings-a1b2c3d4-2."
    )
    violations = lint_thesis_prose(statement_with_finding_id, _CLEAN_MECHANISM)
    assert any(
        v.startswith("statement:") and "finding id" in v for v in violations
    )


def test_lint_thesis_prose_clean_prose_yields_no_violations():
    assert lint_thesis_prose(_CLEAN_STATEMENT, _CLEAN_MECHANISM) == []
