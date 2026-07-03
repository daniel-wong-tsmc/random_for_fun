"""Tests for gpu_agent/brief.py — render_the_calls (THE CALLS section, sub-project
5-2 Task 2). THE CALLS leads the page with the standing thesis book: earned deltas
only, never invented citations, honest empty/never-judged states."""
from __future__ import annotations

from gpu_agent import reader
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact, Kind
from gpu_agent.schema.scorecard import DemandSupply, Scorecard
from gpu_agent.thesis import PendingChallenge, ThesisBook, ThesisEntry

from gpu_agent.brief import render_the_calls

AS_OF = "2026-07-03"
AS_OF_PRIOR = "2026-06-26"
CATEGORY_ID = "chips.merchant-gpu"
REG = IndicatorRegistry.load("registry/indicators.json")


# ── fixture helpers (mirrors tests/test_thesis_apply.py's builders) ──────────

def _entry(entry_id, *, title=None, status="registered", conviction="medium",
           lastVerdict=None, streak=0, pendingChallenge=None,
           lastChangedAsOf=AS_OF_PRIOR, trigger="Reassessed next quarter.",
           statement=None):
    return ThesisEntry(
        id=entry_id, title=title or entry_id.replace("-", " ").title(),
        statement=statement or "Original statement.", lens="demand", status=status,
        conviction=conviction, lastVerdict=lastVerdict, streak=streak,
        pendingChallenge=pendingChallenge, mechanism="mechanism",
        falsifiableTrigger=trigger, sensitivity="sensitivity",
        createdAsOf=AS_OF_PRIOR, lastChangedAsOf=lastChangedAsOf,
    )


def _book(*entries):
    return ThesisBook(categoryId=CATEGORY_ID, entries=list(entries))


def _evidence(tier, url="https://example.com/a"):
    return Evidence(source="Example", url=url, date=AS_OF, excerpt="e", tier=tier)


def _finding(fid, statement="A finding statement.", *, evidence=None, indicator="D2"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["t"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"),
        asOf=AS_OF, indicatorId=indicator, side="demand",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="E",
        observedAt=AS_OF, capturedAt=AS_OF,
        evidence=evidence if evidence is not None else [_evidence("secondary")],
    )


def _sc(findings=()):
    return Scorecard(
        categoryId=CATEGORY_ID, asOf=AS_OF, findings=list(findings),
        demandSupply=DemandSupply(dmiContribution=0.0, smiContribution=0.0),
        narrative="n", confidence=Confidence(level="medium", basis="b"),
    )


def _calls_lines(out):
    return [ln for ln in out.splitlines() if ln.startswith("  ● ")]


# ── None book ─────────────────────────────────────────────────────────────

def test_none_book_renders_honest_placeholder():
    out = render_the_calls(None, _sc())
    assert out == "THE CALLS\n  (no thesis book yet - runs after the first thesis cycle)"


# ── ordering: registered before provisional, then (-CONVICTION_RANK, id) ────

def test_ordering_registered_before_provisional_then_conviction_desc_then_id():
    e_prov_high = _entry("z-prov", status="provisional", conviction="high", lastVerdict="strengthened")
    e_reg_low = _entry("b-reg", status="registered", conviction="low", lastVerdict="weakened")
    e_reg_high_a = _entry("a-reg", status="registered", conviction="high", lastVerdict="strengthened")
    e_reg_high_c = _entry("c-reg", status="registered", conviction="high", lastVerdict="strengthened")
    book = _book(e_prov_high, e_reg_low, e_reg_high_a, e_reg_high_c)

    out = render_the_calls(book, _sc())

    ids_in_order = [ln.split("●")[1].strip().split("   ")[0] for ln in _calls_lines(out)]
    assert ids_in_order == ["A Reg", "C Reg", "B Reg", "Z Prov"]


# ── CHALLENGED render ────────────────────────────────────────────────────────

def test_challenged_state_when_pending_challenge():
    challenge = PendingChallenge(verdict="weakened", asOf=AS_OF, rationale="new signal", findingIds=["f-9"])
    entry = _entry("thesis-a", lastVerdict="reaffirmed", pendingChallenge=challenge)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "CHALLENGED — pending confirmation ⚠" in out


def test_intact_state_when_no_pending_challenge():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "INTACT, strengthened ▲" in out
    assert "CHALLENGED" not in out


# ── BROKEN-once render (retired-this-cycle only) ────────────────────────────

def test_retired_entry_renders_once_when_changed_this_cycle():
    entry = _entry("thesis-b", status="retired", conviction="low", lastVerdict="broken",
                    lastChangedAsOf=AS_OF)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "  ✕ Thesis B   BROKEN — retired" in out


def test_retired_entry_omitted_when_not_changed_this_cycle():
    entry = _entry("thesis-b", status="retired", conviction="low", lastVerdict="broken",
                    lastChangedAsOf=AS_OF_PRIOR)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "retired" not in out.lower()


# ── nothing-changed headline ─────────────────────────────────────────────────

def test_nothing_changed_headline_when_all_standing_reaffirmed_no_pending():
    e1 = _entry("thesis-a", lastVerdict="reaffirmed", lastChangedAsOf=AS_OF)
    e2 = _entry("thesis-b", lastVerdict="reaffirmed", lastChangedAsOf=AS_OF)
    book = _book(e1, e2)

    out = render_the_calls(book, _sc())

    lines = out.splitlines()
    assert lines[0] == "THE CALLS"
    assert lines[1] == "  Nothing changed this cycle. (2 theses reaffirmed)"
    # still followed by the compact one-line-per-thesis book
    assert len(_calls_lines(out)) == 2


def test_not_nothing_changed_when_pending_challenge_present():
    challenge = PendingChallenge(verdict="weakened", asOf=AS_OF, rationale="r", findingIds=["f-1"])
    entry = _entry("thesis-a", lastVerdict="reaffirmed", pendingChallenge=challenge)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "Nothing changed" not in out


def test_not_nothing_changed_when_a_thesis_was_retired_this_cycle():
    e1 = _entry("thesis-a", lastVerdict="reaffirmed", lastChangedAsOf=AS_OF)
    e2 = _entry("thesis-b", status="retired", lastVerdict="broken", lastChangedAsOf=AS_OF)
    book = _book(e1, e2)

    out = render_the_calls(book, _sc())

    assert "Nothing changed" not in out
    assert "BROKEN — retired" in out


def test_not_nothing_changed_when_a_verdict_differs():
    e1 = _entry("thesis-a", lastVerdict="reaffirmed")
    e2 = _entry("thesis-b", lastVerdict="strengthened")
    book = _book(e1, e2)

    out = render_the_calls(book, _sc())

    assert "Nothing changed" not in out


# ── provisional tag (reader-facing label, not the internal word) ───────────

def test_calls_provisional_renders_reader_label():
    entry = _entry("thesis-c", status="provisional", conviction="low", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc())

    line = _calls_lines(out)[0]
    assert line.rstrip().endswith(f"  ({reader.STATUS_LABEL['provisional']})")
    assert "(provisional)" not in out


def test_registered_entries_not_tagged_provisional():
    entry = _entry("thesis-c", status="registered", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "(provisional)" not in out
    assert reader.STATUS_LABEL["provisional"] not in out


def test_nothing_changed_path_uses_reader_provisional_label():
    """The compact 'nothing changed' path renders only headline lines — verify the
    reader-facing provisional label flows there too, not just the full three-line block."""
    entry = _entry("thesis-a", status="provisional", lastVerdict="reaffirmed", lastChangedAsOf=AS_OF)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    assert "Nothing changed" in out
    assert f"  ({reader.STATUS_LABEL['provisional']})" in out
    assert "(provisional)" not in out


# ── missing-citations fallback ───────────────────────────────────────────────

def test_missing_citations_fallback_when_last_findings_is_none():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc(), last_findings=None)

    assert "      Original statement.  (sources in history)" in out


def test_missing_citations_fallback_when_entry_absent_from_last_findings():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc(), last_findings={})

    assert "      Original statement.  (sources in history)" in out


def test_calls_evidence_counts_unresolvable_finding_without_leaking_its_id():
    """A citation id that doesn't resolve against this cycle's sc.findings still
    contributes to the honest source count (the line carries the entry's own statement,
    not the finding's) — but the id itself must never leak into the rendered line."""
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)

    out = render_the_calls(book, _sc(findings=[]), last_findings={"thesis-a": ["f-ghost"]})

    assert "      Original statement.  (1 source)" in out
    assert "f-ghost" not in out   # never invented — no fabricated citation reference either


# ── calls line: thesis statement + source counts, no id dumps ───────────────

def test_calls_line_uses_thesis_statement_and_source_counts():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)
    findings = [_finding("f-1"), _finding("f-2"), _finding("f-3")]
    sc = _sc(findings=findings)

    out = render_the_calls(book, sc, last_findings={"thesis-a": ["f-1", "f-2", "f-3"]})

    assert "3 sources" in out
    assert "[" not in out.split("breaks if")[0]     # no id dumps anywhere in the block
    assert entry.statement[:40] in out               # full statement, not an excerpt


# ── evidence line: tier tag (no truncation — one authored sentence) ─────────

def test_evidence_line_tier_primary_when_any_cited_finding_has_primary_evidence():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)
    finding = _finding("f-1", evidence=[_evidence("primary")])
    sc = _sc(findings=[finding])

    out = render_the_calls(book, sc, last_findings={"thesis-a": ["f-1"]})

    line = [ln for ln in out.splitlines() if ln.startswith("      Original statement.")][0]
    assert line == f"      Original statement.  (1 source, incl. {reader.TIER_LABEL['primary']})"


def test_evidence_line_tier_secondary_when_no_primary_evidence():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    book = _book(entry)
    finding = _finding("f-1", evidence=[_evidence("secondary")])
    sc = _sc(findings=[finding])

    out = render_the_calls(book, sc, last_findings={"thesis-a": ["f-1"]})

    line = [ln for ln in out.splitlines() if ln.startswith("      Original statement.")][0]
    assert line == "      Original statement.  (1 source)"


def test_evidence_line_not_truncated_full_statement_used():
    long_stmt = "x" * 150
    entry = _entry("thesis-a", lastVerdict="strengthened", statement=long_stmt)
    book = _book(entry)
    finding = _finding("f-1")
    sc = _sc(findings=[finding])

    out = render_the_calls(book, sc, last_findings={"thesis-a": ["f-1"]})

    assert f"      {long_stmt}  (1 source)" in out


# ── never-judged entry (lastVerdict None) ───────────────────────────────────

def test_never_judged_entry_renders_neutral_no_verdict_word():
    entry = _entry("thesis-a", lastVerdict=None)
    book = _book(entry)

    out = render_the_calls(book, _sc())

    line = _calls_lines(out)[0]
    assert "not yet judged" in line
    assert "reaffirmed" not in line
    assert "None" not in line


# ── "breaks if:" display-layer id labeling (registry param) ────────────────

def test_breaks_if_line_labels_indicator_id_when_registry_supplied():
    entry = _entry("thesis-a", lastVerdict="strengthened",
                    trigger="The D6 price track shows a 15% decline across providers.")
    book = _book(entry)

    out = render_the_calls(book, _sc(), registry=REG)

    assert "GPU rental price" in out
    assert "D6" not in out


def test_breaks_if_line_unchanged_without_registry():
    entry = _entry("thesis-a", lastVerdict="strengthened",
                    trigger="The D6 price track shows a 15% decline across providers.")
    book = _book(entry)

    out = render_the_calls(book, _sc())   # no registry -> default None

    assert "breaks if: The D6 price track shows a 15% decline across providers." in out
    assert "GPU rental price" not in out


# ── byte-stability ───────────────────────────────────────────────────────────

def test_byte_stability_two_calls_produce_identical_output():
    entry = _entry("thesis-a", lastVerdict="strengthened")
    finding = _finding("f-1")
    book = _book(entry)
    sc = _sc(findings=[finding])
    last_findings = {"thesis-a": ["f-1"]}

    out1 = render_the_calls(book, sc, last_findings)
    out2 = render_the_calls(book, sc, last_findings)

    assert out1 == out2


def test_byte_stability_nothing_changed_branch():
    e1 = _entry("thesis-a", lastVerdict="reaffirmed")
    book = _book(e1)
    sc = _sc()

    assert render_the_calls(book, sc) == render_the_calls(book, sc)
