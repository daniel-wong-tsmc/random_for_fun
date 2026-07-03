"""Tests for gpu_agent/brief.py — render_why (WHY section, sub-project 5-2 Task 3).
WHY is a pure projection of the standing thesis book by lens: drivers (Pulling demand /
Capping supply) vs constraints held up for scrutiny (Contested). No new number, no LLM
call — every line is owned by exactly one thesis, and the three groups partition the
standing book without overlap."""
from __future__ import annotations

from gpu_agent.thesis import PendingChallenge, ThesisBook, ThesisEntry

from gpu_agent.brief import render_why

AS_OF_PRIOR = "2026-06-26"
CATEGORY_ID = "chips.merchant-gpu"


# ── fixture helpers (mirrors tests/test_brief_calls.py's builders) ──────────

def _entry(entry_id, *, title=None, lens="demand", status="registered",
           conviction="medium", pendingChallenge=None, mechanism=None):
    return ThesisEntry(
        id=entry_id, title=title or entry_id.replace("-", " ").title(),
        statement="Original statement.", lens=lens, status=status,
        conviction=conviction, pendingChallenge=pendingChallenge,
        mechanism=mechanism or f"{entry_id} mechanism",
        falsifiableTrigger="Reassessed next quarter.", sensitivity="sensitivity",
        createdAsOf=AS_OF_PRIOR, lastChangedAsOf=AS_OF_PRIOR,
    )


def _book(*entries):
    return ThesisBook(categoryId=CATEGORY_ID, entries=list(entries))


def _challenge(verdict="weakened"):
    return PendingChallenge(verdict=verdict, asOf=AS_OF_PRIOR, rationale="r", findingIds=["f-1"])


def _group(out, header):
    """Lines belonging to one group header, up to the next 2-space-indented header or EOF."""
    lines = out.splitlines()
    start = lines.index(header) + 1
    end = start
    while end < len(lines) and lines[end].startswith("    "):
        end += 1
    return lines[start:end]


# ── None / empty book ────────────────────────────────────────────────────────

def test_none_book_renders_honest_placeholder():
    assert render_why(None) == "WHY\n  (no thesis book yet)"


def test_empty_book_renders_honest_placeholder():
    assert render_why(_book()) == "WHY\n  (no thesis book yet)"


def test_header_line_for_populated_book():
    book = _book(_entry("thesis-a"))
    out = render_why(book)
    assert out.splitlines()[0] == "WHY (drivers -> constraints)"


# ── Pulling demand / Capping supply grouping ─────────────────────────────────

def test_demand_entry_meeting_criteria_lands_in_pulling_demand():
    entry = _entry("thesis-a", lens="demand", conviction="high", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    • thesis-a mechanism  (Thesis A)"]


def test_supply_entry_meeting_criteria_lands_in_capping_supply():
    entry = _entry("thesis-b", lens="supply", conviction="medium", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Capping supply:") == ["    • thesis-b mechanism  (Thesis B)"]


def test_demand_entry_excluded_when_conviction_low():
    entry = _entry("thesis-a", lens="demand", conviction="low", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    (none)"]
    # literal-rule gap, by design: a low-conviction, unchallenged, registered demand
    # thesis is not a Contested reason either (no pendingChallenge, not provisional,
    # not competitive/risk) — it lands in no group at all.
    assert _group(out, "  Contested:") == ["    (none)"]


def test_demand_entry_excluded_when_provisional():
    entry = _entry("thesis-a", lens="demand", conviction="high", status="provisional")
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    (none)"]


def test_supply_entry_excluded_when_wrong_lens():
    entry = _entry("thesis-a", lens="demand", conviction="high", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Capping supply:") == ["    (none)"]


def test_competitive_or_risk_lens_never_in_demand_or_supply_groups():
    entry = _entry("thesis-a", lens="competitive", conviction="high", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    (none)"]
    assert _group(out, "  Capping supply:") == ["    (none)"]


# ── Contested grouping + precedence ──────────────────────────────────────────

def test_challenged_entry_lands_in_contested_with_challenged_label():
    entry = _entry("thesis-a", lens="demand", conviction="high", status="registered",
                    pendingChallenge=_challenge())
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — CHALLENGED ⚠)"]


def test_provisional_entry_lands_in_contested_with_provisional_label():
    entry = _entry("thesis-a", lens="supply", conviction="high", status="provisional")
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — provisional)"]


def test_competitive_low_conviction_lands_in_contested_with_low_conviction_label():
    entry = _entry("thesis-a", lens="competitive", conviction="low", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — low conviction)"]


def test_risk_low_conviction_lands_in_contested_with_low_conviction_label():
    entry = _entry("thesis-a", lens="risk", conviction="low", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — low conviction)"]


def test_competitive_medium_conviction_no_challenge_lands_in_no_group():
    """Documented literal-rule gap: a competitive/risk thesis at medium+ conviction with
    no outstanding challenge is neither a driver nor Contested — WHY shows drivers,
    constraints, and contested claims, not the whole book."""
    entry = _entry("thesis-a", lens="competitive", conviction="medium", status="registered")
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    (none)"]
    assert _group(out, "  Capping supply:") == ["    (none)"]
    assert _group(out, "  Contested:") == ["    (none)"]


def test_precedence_challenged_beats_provisional():
    entry = _entry("thesis-a", lens="demand", conviction="high", status="provisional",
                    pendingChallenge=_challenge())
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — CHALLENGED ⚠)"]


def test_precedence_provisional_beats_low_conviction():
    entry = _entry("thesis-a", lens="risk", conviction="low", status="provisional")
    out = render_why(_book(entry))
    assert _group(out, "  Contested:") == ["    • thesis-a mechanism  (Thesis A — provisional)"]


# ── partition airtightness ────────────────────────────────────────────────────

def test_challenged_demand_thesis_appears_under_contested_not_pulling_demand():
    """The demand/supply criteria's own 'no pendingChallenge' clause already excludes a
    challenged thesis, but this pins the resulting partition explicitly: a challenged
    demand thesis is never silently dropped — it must surface, and only under Contested."""
    entry = _entry("thesis-a", lens="demand", conviction="high", status="registered",
                    pendingChallenge=_challenge())
    out = render_why(_book(entry))
    assert _group(out, "  Pulling demand:") == ["    (none)"]
    assert len(_group(out, "  Contested:")) == 1
    assert "thesis-a" in _group(out, "  Contested:")[0]


def test_no_thesis_appears_in_two_groups():
    entries = [
        _entry("d-high", lens="demand", conviction="high", status="registered"),
        _entry("d-challenged", lens="demand", conviction="high", status="registered",
                pendingChallenge=_challenge()),
        _entry("s-med", lens="supply", conviction="medium", status="registered"),
        _entry("prov", lens="demand", conviction="high", status="provisional"),
        _entry("comp-low", lens="competitive", conviction="low", status="registered"),
        _entry("comp-med", lens="risk", conviction="medium", status="registered"),
        _entry("d-low", lens="demand", conviction="low", status="registered"),
    ]
    out = render_why(_book(*entries))

    demand_ids = [ln.split("•")[1].split("mechanism")[0].strip() for ln in _group(out, "  Pulling demand:")
                  if ln != "    (none)"]
    supply_ids = [ln.split("•")[1].split("mechanism")[0].strip() for ln in _group(out, "  Capping supply:")
                  if ln != "    (none)"]
    contested_ids = [ln.split("•")[1].split("mechanism")[0].strip() for ln in _group(out, "  Contested:")
                     if ln != "    (none)"]

    assert demand_ids == ["d-high"]
    assert supply_ids == ["s-med"]
    # comp-low (competitive, low conviction) is also a Contested reason
    assert sorted(contested_ids) == ["comp-low", "d-challenged", "prov"]
    # every id appears in at most one group
    all_seen = demand_ids + supply_ids + contested_ids
    assert len(all_seen) == len(set(all_seen))
    # d-low and comp-med land in no group at all (documented literal-rule gaps)
    assert "d-low" not in all_seen
    assert "comp-med" not in all_seen


def test_retired_entries_appear_nowhere_even_if_they_would_otherwise_match():
    """Retired entries are excluded up front — even a retired entry carrying a leftover
    pendingChallenge or a competitive/low-conviction shape must not surface anywhere."""
    retired_challenged = _entry("r-challenged", lens="demand", conviction="high",
                                 status="retired", pendingChallenge=_challenge())
    retired_low_comp = _entry("r-lowcomp", lens="competitive", conviction="low", status="retired")
    out = render_why(_book(retired_challenged, retired_low_comp))
    assert "r-challenged" not in out
    assert "r-lowcomp" not in out
    assert _group(out, "  Pulling demand:") == ["    (none)"]
    assert _group(out, "  Capping supply:") == ["    (none)"]
    assert _group(out, "  Contested:") == ["    (none)"]


# ── empty groups ──────────────────────────────────────────────────────────────

def test_all_groups_none_when_book_has_only_non_matching_entries():
    entry = _entry("thesis-a", lens="competitive", conviction="medium", status="registered")
    out = render_why(_book(entry))
    assert out == (
        "WHY (drivers -> constraints)\n"
        "  Pulling demand:\n"
        "    (none)\n"
        "  Capping supply:\n"
        "    (none)\n"
        "  Contested:\n"
        "    (none)"
    )


# ── ordering: (-CONVICTION_RANK, id) within a group ──────────────────────────

def test_ordering_within_group_by_conviction_desc_then_id():
    e_z_high = _entry("z-thesis", lens="demand", conviction="high", status="registered")
    e_a_medium = _entry("a-thesis", lens="demand", conviction="medium", status="registered")
    e_m_high = _entry("m-thesis", lens="demand", conviction="high", status="registered")
    out = render_why(_book(e_z_high, e_a_medium, e_m_high))

    lines = _group(out, "  Pulling demand:")
    ids_in_order = [ln.split("•")[1].split("mechanism")[0].strip() for ln in lines]
    assert ids_in_order == ["m-thesis", "z-thesis", "a-thesis"]


def test_ordering_within_contested_by_conviction_desc_then_id():
    e_z = _entry("z-thesis", lens="demand", conviction="low", status="provisional")
    e_a = _entry("a-thesis", lens="demand", conviction="high", status="provisional")
    out = render_why(_book(e_z, e_a))

    lines = _group(out, "  Contested:")
    ids_in_order = [ln.split("•")[1].split("mechanism")[0].strip() for ln in lines]
    assert ids_in_order == ["a-thesis", "z-thesis"]


# ── byte-stability ────────────────────────────────────────────────────────────

def test_byte_stability_two_calls_produce_identical_output():
    entries = [
        _entry("thesis-a", lens="demand", conviction="high", status="registered"),
        _entry("thesis-b", lens="supply", conviction="medium", status="registered",
                pendingChallenge=_challenge()),
        _entry("thesis-c", lens="risk", conviction="low", status="registered"),
    ]
    book = _book(*entries)

    out1 = render_why(book)
    out2 = render_why(book)

    assert out1 == out2


def test_byte_stability_empty_and_none_book():
    assert render_why(None) == render_why(_book())
