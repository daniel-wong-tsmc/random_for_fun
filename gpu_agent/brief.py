"""The human-facing Market-State brief (sub-project 4-5). Pure, deterministic
projection of a Scorecard — no LLM, no wiki store, no new number. Reuses report.py's
wording helpers so the brief and the detailed report speak the same vocabulary."""
from __future__ import annotations
import re
from typing import Optional
from urllib.parse import urlparse
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent import report   # module ref, resolved at call-time — avoids the report<->brief cycle

_ARROW = {"positive": "▲", "negative": "▼", "flat": "="}   # ▲ ▼ =


def _dir_arrow(value: float) -> str:
    return _ARROW[report._momentum_word(value)]


def render_state_of_market(sc: Scorecard, prior: Optional[Scorecard], track=None) -> str:
    """STATE OF THE MARKET (BLUF): demand/supply momentum as direction + Δ (never an
    invented magnitude word on the unscaled index — Part 17), the SDGI gap wording, the
    brain's earned categoryStatus headline + binding constraint, and NOW/NEXT + divergence
    from the two indices. Optional fields degrade cleanly. ``track`` (F49, optional) adds
    one Price Momentum overlay line after the Gap line, only when it carries series."""
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

    if cs is not None:
        lines.append(f"  BINDING CONSTRAINT: {cs.bottleneck}")
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
