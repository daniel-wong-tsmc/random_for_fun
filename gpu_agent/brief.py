"""The human-facing Market-State brief (sub-project 4-5). Pure, deterministic
projection of a Scorecard — no LLM, no wiki store, no new number. Reuses report.py's
wording helpers so the brief and the detailed report speak the same vocabulary."""
from __future__ import annotations
import re
from typing import Optional
from urllib.parse import urlparse
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.thesis import CONVICTION_RANK, ThesisBook
from gpu_agent import bands
from gpu_agent import reader
from gpu_agent import report   # module ref, resolved at call-time — avoids the report<->brief cycle

_ARROW = {"positive": "▲", "negative": "▼", "flat": "="}   # ▲ ▼ =


def _dir_arrow(value: float) -> str:
    return _ARROW[report._momentum_word(value)]


def render_state_of_market(sc: Scorecard, prior: Optional[Scorecard], track=None) -> str:
    """STATE OF THE MARKET (BLUF): demand/supply momentum as a words-first band
    (gpu_agent.bands — earned via fixed, retunable thresholds, never an invented
    magnitude — Part 17), the SDGI gap wording, the brain's earned categoryStatus
    headline + binding constraint, and NOW/NEXT + divergence from the two indices.
    Optional fields degrade cleanly. ``track`` (F49, optional) adds one Price Momentum
    overlay line after the Gap line, only when it carries series.

    Task 4 (5-2 output surgery): the raw DMI/SMI/SDGI values + Δ that used to sit in
    parentheses on these lines have moved to the TRUST & COVERAGE footer's raw-index
    table (report.render_trust_footer) — this section speaks bands and words only."""
    ds = sc.demandSupply
    sdgi = report.compute_sdgi(sc)
    p_dmi = prior.demandSupply.dmiContribution if prior else None
    p_smi = prior.demandSupply.smiContribution if prior else None

    lines = ["STATE OF THE MARKET"]
    cs = sc.categoryStatus
    if cs is not None:
        lines.append(f"  {cs.rating}, {cs.direction} — {cs.reason}")
    lines.append(f"  Demand: {bands.band_with_prior(ds.dmiContribution, p_dmi)}")
    lines.append(f"  Supply: {bands.band_with_prior(ds.smiContribution, p_smi)}")
    lines.append(f"  Gap: {report._sdgi_interpretation(sdgi)}")

    if (cs is not None and cs.rating in ("Strong", "Very strong")
            and ds.smiContribution < 0):
        lines.append("  Note: the supply reading is negative because supply is the "
                     "constraint — a demand-led shortage, not a demand problem.")

    if track is not None and track.series:
        if track.pmi is None:
            pmi_str = "PMI —"
        else:
            word = report._pmi_word(track.pmi)
            sign = "+" if track.pmi >= 0 else "−"
            pmi_str = f"PMI {sign}{abs(track.pmi):.2f} {report._PMI_ARROW[word]}"
        lines.append(f"  Price overlay: {len(track.series)} series tracked, {pmi_str}")

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

    if cs is not None and getattr(cs, "constraintLabel", None):
        lines.append(f"  BINDING CONSTRAINT: {cs.constraintLabel}")
    return "\n".join(lines)


_TREND_ARROW = {"rising": "▲", "falling": "▼", "flat": "=", "unknown": "·"}


def _collapse_latest(findings):
    """One finding per indicatorId — the latest vintage (max by capturedAt, observedAt,
    magnitude), the same collapse the frozen dmi_smi_contribution uses. Deterministic."""
    latest: dict[str, object] = {}
    for f in findings:
        cur = latest.get(f.indicatorId)
        key = (f.capturedAt, f.observedAt, f.magnitude)
        if cur is None or key > (cur.capturedAt, cur.observedAt, cur.magnitude):
            latest[f.indicatorId] = f
    return latest


def _publisher(ev) -> str:
    """Domain-level publisher for one Evidence item: netloc minus a leading 'www.',
    falling back to the evidence's source name when the URL has no netloc (F29)."""
    netloc = urlparse(ev.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[len("www."):]
    return netloc or ev.source.lower()


def _board_rows(findings, side, sc_as_of, horizons):
    rows = []
    on_side = [f for f in findings if f.side == side]
    latest = _collapse_latest(on_side)
    for indicator_id in sorted(latest):
        f = latest[indicator_id]
        pol = f.polarityDemand if side == "demand" else f.polaritySupply
        word = report._signal_label(pol * f.magnitude)
        arrow = _TREND_ARROW.get(f.trend, "·")
        tags = []
        if horizons is not None:
            tag = horizons.get(indicator_id)
            if tag is not None and tag.get("horizon") == "leading":
                tags.append("leading")
        if f.asOf < sc_as_of:
            tags.append("⚠carried")
        # F29: a row backed by exactly one distinct publisher domain (whether that's one
        # evidence item or several from the same outlet) carries a visible warning —
        # honest about corroboration, not just presence of evidence.
        publishers = {_publisher(ev) for ev in f.evidence}
        if len(publishers) == 1:
            tags.append("⚠single-source")
        suffix = ("  [" + ", ".join(tags) + "]") if tags else ""
        rows.append(f"    {indicator_id}  {word} {arrow}{suffix}")
    if not rows:
        rows.append(f"    (no {side} findings)")
    return rows


def render_demand_supply_board(sc: Scorecard, horizons) -> str:
    """DEMAND | SUPPLY board: findings grouped by side, collapsed to the latest vintage per
    indicator, each row a _signal_label word (from polarity*magnitude — the same score the
    entity panel uses) + a trend arrow, with a `leading` tag (when horizons supplied) and a
    `carried` flag for a stale carry-over. Read-only; deterministic (rows ordered by id)."""
    lines = ["DEMAND | SUPPLY"]
    lines.append("  DEMAND")
    lines.extend(_board_rows(sc.findings, "demand", sc.asOf, horizons))
    lines.append("  SUPPLY")
    lines.extend(_board_rows(sc.findings, "supply", sc.asOf, horizons))
    return "\n".join(lines)


def render_market_caveat(sc: Scorecard) -> str:
    """The one honest trust-footer caveat: the index LEVEL is run-to-run noisy until the
    4-4 memory stabilizes it, so the brief is a read of DIRECTION and change, not level."""
    return ("TRUST & COVERAGE (caveat)\n"
            "  index level varies run-to-run until the 4-4 memory stabilizes it — "
            "read DIRECTION, not level")


# ── store-fed sections (4-5b) ────────────────────────────────────────────────
_TRAJ_UP = {"accelerating", "improving", "rising", "up", "expanding", "strengthening", "hot"}
_TRAJ_DOWN = {"eroding", "worsening", "decelerating", "falling", "down", "slipping",
              "softening", "weakening", "contracting"}
_TRAJ_FLAT = {"steady", "flat", "stable", "unchanged", "tight", "intact", "firm", "on-track"}


_TRAJ_TOKEN_RE = re.compile(r"[a-z]+(?:-[a-z]+)?")


def _traj_arrow(text) -> str:
    """Best-effort ▲/▼/=/· from brain-authored free-text state/trajectory (shared by the
    WHAT MOVED UP/DOWN tag and the STORYLINES arrow). Falls back to · on no keyword match.

    F18: matches whole TOKENS, not substrings — a naive `"up" in text` check would fire
    on "supply" or "shutdown" (both contain "up"/"down" as substrings, not words), giving
    a fabricated direction. Tokenizing on [a-z]+ (with an optional single internal hyphen,
    so "on-track" stays one token) and intersecting with the keyword sets closes that gap."""
    tokens = set(_TRAJ_TOKEN_RE.findall((text or "").lower()))
    if tokens & _TRAJ_UP:
        return "▲"
    if tokens & _TRAJ_DOWN:
        return "▼"
    if tokens & _TRAJ_FLAT:
        return "="
    return "·"


def _moved_tag(row):
    if row.newThread:
        return "NEW", "▲"
    if row.contradiction:
        return "WATCH", "▼"
    if row.stateTo:
        arrow = _traj_arrow(row.stateTo)
        if arrow == "▲":
            return "UP", "▲"
        if arrow == "▼":
            return "DOWN", "▼"
        return "CHANGED", "="
    return "MOVED", "="


def render_what_moved(movement) -> str:
    """WHAT MOVED SINCE LAST RUN: the materiality-ranked daily diff (4-4b score_moves),
    each row tagged NEW/WATCH/UP/DOWN/CHANGED/MOVED, cited + tiered, provisional marked;
    the folded below-threshold count shown. Pure; movement=None → honest empty-state."""
    lines = ["WHAT MOVED SINCE LAST RUN"]
    if movement is None:
        lines.append("  (no wiki store yet — needs a multi-cycle store from daily cycles)")
        return "\n".join(lines)
    if movement.prevAsOf is None:
        lines.append("  (no prior cycle to compare — first tracked cycle)")
        return "\n".join(lines)
    lines[0] += f"  (vs {movement.prevAsOf})"
    for row in movement.moved:
        tag, arrow = _moved_tag(row)
        cite = f"[{', '.join(row.findingIds)}]" if row.findingIds else "[—]"
        prov = "  (provisional)" if row.provisional else ""
        contra = f"  ({row.contradictionNote})" if row.contradiction and row.contradictionNote else ""
        trans = f"  {row.stateFrom} → {row.stateTo}" if (row.stateFrom and row.stateTo) else ""
        lines.append(f"  {arrow} {tag:<6} {row.title}  {cite} {row.tier}{prov}{contra}{trans}")
    if not movement.moved:
        lines.append("  (no material moves this cycle)")
    if movement.foldedCount:
        lines.append(f"  ({movement.foldedCount} lower-materiality items folded — see wiki-lint)")
    return "\n".join(lines)


def _storyline_line(s) -> str:
    return (f"    • {s.title}  {s.state} → {s.trajectory}  "
            f"(last updated {s.lastUpdatedAsOf})  {_traj_arrow(s.trajectory)}")


_STORYLINE_CAP = 8   # F33: bound per-group render growth; the fold is always disclosed


def _storyline_group_lines(entries) -> list[str]:
    """Render one STORYLINES group, capped at _STORYLINE_CAP entries (already sorted by
    the caller's (-salience, title) order). When the group is capped, an explicit
    fold-count line is appended — nothing silent. Empty group -> "(none)"."""
    if not entries:
        return ["    (none)"]
    shown = entries[:_STORYLINE_CAP]
    lines = [_storyline_line(s) for s in shown]
    folded = len(entries) - len(shown)
    if folded > 0:
        lines.append(f"    (+{folded} more tracked — see wiki-lint)")
    return lines


def render_storylines(movement) -> str:
    """STORYLINES: the tracked threads' state → trajectory + last-change, split by
    partition_canonical into REGISTERED (canonical) and PROVISIONAL (confidence-capped),
    each ordered by salience desc and capped at the top _STORYLINE_CAP (F33) with an
    explicit fold count when a group overflows. Pure; movement=None → honest empty-state."""
    lines = ["STORYLINES (tracked over time)"]
    if movement is None:
        lines.append("  (no wiki store yet — needs a multi-cycle store from daily cycles)")
        return "\n".join(lines)
    if not movement.storylines:
        lines.append("  (no tracked storylines yet)")
        return "\n".join(lines)
    _key = lambda s: (-s.salience, s.title)   # deterministic display order: salience desc, then title
    registered = sorted((s for s in movement.storylines if not s.provisional), key=_key)
    provisional = sorted((s for s in movement.storylines if s.provisional), key=_key)
    lines.append("  REGISTERED (canonical)")
    lines.extend(_storyline_group_lines(registered))
    lines.append("  PROVISIONAL (confidence-capped)")
    lines.extend(_storyline_group_lines(provisional))
    return "\n".join(lines)


# ── THE CALLS (sub-project 5-2 Task 2) ──────────────────────────────────────
# The thesis book leads the page: earned deltas only, never an invented citation.

_CALLS_ARROW = {
    "strengthened": "▲", "weakened": "▼", "reaffirmed": "=", "adjusted": "~", "broken": "✕",
}


def _calls_entry_key(entry):
    """registered before provisional, then (-CONVICTION_RANK[conviction], id) — the
    spec §4 ordering rule. status != "registered" sorts False(0) before True(1)."""
    return (entry.status != "registered", -CONVICTION_RANK[entry.conviction], entry.id)


def _calls_headline_line(entry) -> str:
    """The three-line block's first line:
      `  ● <title>   <STATE>, <lastVerdict> <arrow>  (<conviction>, <streak> cycles)`
    STATE is CHALLENGED when a pendingChallenge is outstanding, else INTACT. A never-
    judged entry (lastVerdict is None — a freshly seeded book rendered before its first
    cycle; not itself pinned by the spec) gets a neutral "not yet judged" in place of a
    verdict word/arrow rather than fabricating one. Provisional entries append the
    reader-facing label (reader.STATUS_LABEL['provisional'] — an exec-facing phrase, not
    the internal word "provisional") at the end of the line."""
    state = "CHALLENGED — pending confirmation ⚠" if entry.pendingChallenge is not None else "INTACT"
    if entry.lastVerdict is None:
        verdict_part = "not yet judged"
    else:
        verdict_part = f"{entry.lastVerdict} {_CALLS_ARROW[entry.lastVerdict]}"
    prov = f"  ({reader.STATUS_LABEL['provisional']})" if entry.status == "provisional" else ""
    return (f"  ● {entry.title}   {state}, {verdict_part}  "
            f"({entry.conviction}, {entry.streak} cycles){prov}")


def _calls_evidence_line(entry, finding_ids, findings_by_id) -> str:
    """Second line: the thesis's own statement + a source-count tag (reader contract —
    ids live in the appendix citation map, never here)."""
    if not finding_ids:
        return f"      {entry.statement}  (sources in history)"
    resolved = [findings_by_id[fid] for fid in finding_ids if fid in findings_by_id]
    n = len(finding_ids)
    if resolved and any(ev.tier == "primary" for f in resolved for ev in f.evidence):
        tier = f", incl. {reader.TIER_LABEL['primary']}"
    else:
        tier = ""
    return f"      {entry.statement}  ({n} source{'s' if n != 1 else ''}{tier})"


def render_the_calls(book: Optional[ThesisBook], sc: Scorecard,
                      last_findings: Optional[dict[str, list[str]]] = None) -> str:
    """THE CALLS: the standing thesis book, leading the page with earned deltas only.
    book=None (no thesis cycle has ever run) -> the honest placeholder below. Otherwise:
    standing (registered/provisional) entries ordered per _calls_entry_key, each a
    three-line block (headline / thesis statement + source count / falsifiable trigger);
    a thesis retired THIS cycle (lastChangedAsOf == sc.asOf) renders once as a single
    BROKEN line, and is omitted in every later cycle — no permanent tombstone.
    `last_findings` supplies each thesis's latest-judgment findingIds (the book itself
    does not store them — Task 4 reads them from history.jsonl), used only to derive the
    evidence line's source count and primary-tier tag; the ids themselves never render
    here (reader contract — they live in the appendix citation map). absent -> the
    evidence line's honest "(sources in history)" fallback.

    Nothing-changed headline: apply_record (thesis.py) bumps lastChangedAsOf on every
    APPLIED judgment regardless of verdict word — including a reaffirmed one, since a
    reaffirmed verdict is never a reversal and so is always applied. That means
    "lastChangedAsOf == sc.asOf" is true for every standing entry precisely in the
    all-reaffirmed cycle this headline exists to name, so it cannot be the signal that
    something material happened. What actually changed the entry's substance is the verdict
    word: read "no entry changed this cycle" as "no standing entry's lastVerdict differs
    from reaffirmed and none has an outstanding pendingChallenge" (a deferred reversal
    always leaves a pendingChallenge, so that case is already caught), plus "no thesis was
    retired this cycle" (retirement is a book-shape change the standing-only reaffirmed
    check can't see, since a retired entry drops out of standing()). Under that reading the
    headline is followed by the compact one-line-per-thesis book (the same headline line
    each entry would otherwise open its three-line block with)."""
    if book is None:
        return "THE CALLS\n  (no thesis book yet - runs after the first thesis cycle)"

    findings_by_id = {f.id: f for f in sc.findings}
    standing = sorted(book.standing(), key=_calls_entry_key)
    retired_now = sorted(
        (e for e in book.entries if e.status == "retired" and e.lastChangedAsOf == sc.asOf),
        key=lambda e: e.id,
    )

    lines = ["THE CALLS"]

    nothing_changed = (
        bool(standing)
        and not retired_now
        and all(e.pendingChallenge is None for e in standing)
        and all(e.lastVerdict == "reaffirmed" for e in standing)
    )
    if nothing_changed:
        lines.append(f"  Nothing changed this cycle. ({len(standing)} theses reaffirmed)")
        lines.extend(_calls_headline_line(entry) for entry in standing)
        return "\n".join(lines)

    for entry in standing:
        finding_ids = (last_findings or {}).get(entry.id)
        lines.append(_calls_headline_line(entry))
        lines.append(_calls_evidence_line(entry, finding_ids, findings_by_id))
        lines.append(f"      breaks if: {entry.falsifiableTrigger}")

    for entry in retired_now:
        lines.append(f"  ✕ {entry.title}   BROKEN — retired")

    if not standing and not retired_now:
        lines.append("  (no standing theses)")

    return "\n".join(lines)


# ── WHY (sub-project 5-2 Task 3) ─────────────────────────────────────────────
# The standing thesis book projected by lens: drivers (Pulling demand / Capping supply)
# vs constraints held up for scrutiny (Contested). A pure projection — no new number, no
# LLM call — and the three groups partition the standing book with no overlap: a
# thesis's line, if it has one, appears in exactly one group.
#
# SPEC-WINS RESOLUTION (final whole-branch review): an earlier revision of this file
# followed the sub-project plan's Interfaces block, which had pinned a narrower
# `render_why(book)` (no findings parameter) and a Contested rule limited to
# low-conviction competitive/risk lenses — both of which contradicted spec §4
# ("Contested: = challenged/provisional/competitive-lens mechanisms with their state
# labeled" and "every [WHY] line carries the thesis's latest findingIds"). The project's
# standing rule is THE SPEC WINS where the plan and spec disagree, so both points are now
# aligned to spec: Contested includes every competitive-lens thesis at ANY conviction
# (not only low) that isn't already a driver, and every driver/Contested line carries a
# `last_findings` companion-dict lookup (the same pattern render_the_calls uses),
# falling back to the honest "sources in history" when the thesis has no entry in the
# dict — never inventing a citation, and never dumping ids (reader contract: a count,
# not an id list). The risk-lens low-conviction arm of Contested is the plan's own
# addition and is not itself contradicted by the spec text, so it is kept.

def _why_entry_key(entry):
    """(-CONVICTION_RANK, id) — deterministic display order within a WHY group."""
    return (-CONVICTION_RANK[entry.conviction], entry.id)


def _why_finding_suffix(entry_id, last_findings) -> str:
    """Spec §4: 'Every line carries the thesis's latest findingIds' — the same
    companion-dict pattern render_the_calls uses (the book itself does not store
    findingIds; the caller reads them from history.jsonl and supplies the dict). Reader
    contract: a source COUNT, never an id dump — ids live in the appendix citation map.
    Present + non-empty -> '  (<N> sources)'; absent, or present but empty, -> the honest
    '  (sources in history)' fallback — mirroring THE CALLS' convention of never
    fabricating a citation."""
    ids = (last_findings or {}).get(entry_id)
    if ids:
        return f"  ({len(ids)} source{'s' if len(ids) != 1 else ''})"
    return "  (sources in history)"


def _why_driver_line(entry, last_findings) -> str:
    return f"    • {entry.mechanism}  ({entry.title}){_why_finding_suffix(entry.id, last_findings)}"


def _why_contested_label(entry) -> Optional[str]:
    """The strongest true reason a standing thesis is Contested, or None when it is not
    contested at all — this function doubles as the Contested predicate itself (a thesis
    is contested iff it returns non-None). Precedence when more than one reason applies:
    CHALLENGED ⚠ > provisional > low conviction > "<conviction> conviction" (the spec-§4
    fallback for a competitive-lens thesis that is medium/high conviction and not
    otherwise challenged/provisional) — pick the single strongest, never stack labels.

    Spec §4: "Contested: = challenged/provisional/competitive-lens mechanisms with their
    state labeled" — a competitive-lens thesis is contested at ANY conviction, not only
    low. The risk-lens low-conviction arm is the plan's addition (not contradicted by the
    spec text, so kept); risk lens at medium/high conviction is NOT itself a Contested
    reason — see render_why's docstring for the resulting residual gap."""
    if entry.pendingChallenge is not None:
        return "CHALLENGED ⚠"
    if entry.status == "provisional":
        return "provisional"
    if entry.conviction == "low" and entry.lens in ("competitive", "risk"):
        return "low conviction"
    if entry.lens == "competitive":
        return f"{entry.conviction} conviction"
    return None


def _why_group_lines(entries, line_fn) -> list[str]:
    if not entries:
        return ["    (none)"]
    return [line_fn(entry) for entry in sorted(entries, key=_why_entry_key)]


def render_why(book: Optional[ThesisBook],
               last_findings: Optional[dict[str, list[str]]] = None) -> str:
    """WHY (drivers -> constraints): a pure projection of the standing thesis book by
    lens. None/empty book (no thesis cycle has ever run, or a freshly seeded book with
    no entries at all) -> the honest placeholder 'WHY\\n  (no thesis book yet)' — a bare
    header, not the full '(drivers -> constraints)' one, since there is nothing to
    project yet. Otherwise every retired entry is dropped first (retired entries appear
    nowhere), then the remaining standing entries are partitioned:

      - Pulling demand / Capping supply: lens=="demand"/"supply", conviction >= medium,
        status=="registered", no pendingChallenge. These criteria's own "no
        pendingChallenge" and "status registered" clauses already make membership here
        disjoint from Contested (which requires pendingChallenge, OR provisional, OR a
        competitive lens at any conviction, OR a risk lens at low conviction) — the
        partition is airtight by construction, not by a second de-dup pass: a driver is
        always demand/supply lens, and none of Contested's non-challenge/non-provisional
        paths ever select a demand/supply lens.
      - Contested (spec §4): pendingChallenge OR status=="provisional" OR
        lens=="competitive" (any conviction) OR (lens=="risk" AND conviction=="low");
        the label picks the strongest true reason per _why_contested_label.

    `last_findings` (optional dict[thesisId, list[findingId]], same companion-dict
    pattern as render_the_calls) feeds every driver AND Contested line's trailing
    source-count tag per spec §4 — present+non-empty -> '  (<N> sources)'; otherwise the
    honest '  (sources in history)' fallback (_why_finding_suffix). Reader contract: a
    count, never an id dump — ids live in the appendix citation map.

    Two literal-rule gaps this leaves on the table (by design — WHY shows drivers,
    constraints, and contested claims, not the whole book): a registered demand/supply
    thesis at low conviction with no outstanding challenge lands in no group (low
    conviction alone is not itself a Contested reason for a demand/supply lens); and,
    residually, a registered risk-lens thesis at medium/high conviction with no
    outstanding challenge also lands in no group — spec §4 names only the competitive
    lens for the any-conviction Contested widening, not risk. This is a real, literal gap
    on the committed seed book: export-control-exposure (risk, medium, intact) appears in
    no WHY group.

    Empty groups render '    (none)'. Order within a group: (-CONVICTION_RANK, id)."""
    if book is None or not book.entries:
        return "WHY\n  (no thesis book yet)"

    standing = book.standing()

    def _is_driver(entry, lens) -> bool:
        return (
            entry.lens == lens
            and CONVICTION_RANK[entry.conviction] >= CONVICTION_RANK["medium"]
            and entry.status == "registered"
            and entry.pendingChallenge is None
        )

    demand = [e for e in standing if _is_driver(e, "demand")]
    supply = [e for e in standing if _is_driver(e, "supply")]

    contested_labels = {e.id: _why_contested_label(e) for e in standing}
    contested = [e for e in standing if contested_labels[e.id] is not None]

    lines = ["WHY (drivers -> constraints)"]
    lines.append("  Pulling demand:")
    lines.extend(_why_group_lines(demand, lambda e: _why_driver_line(e, last_findings)))
    lines.append("  Capping supply:")
    lines.extend(_why_group_lines(supply, lambda e: _why_driver_line(e, last_findings)))
    lines.append("  Contested:")
    lines.extend(_why_group_lines(
        contested,
        lambda e: (f"    • {e.mechanism}  ({e.title} — {contested_labels[e.id]})"
                   f"{_why_finding_suffix(e.id, last_findings)}"),
    ))
    return "\n".join(lines)
