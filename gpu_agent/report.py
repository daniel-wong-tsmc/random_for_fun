"""gpu_agent/report.py — deterministic scorecard-to-report renderer.

Pure functions, no LLM, no network, no store writes.
Same scorecard + prior → byte-identical report. The only injected time input is
``render_ts`` (a caller-supplied string); render functions never read the clock.
"""
from __future__ import annotations
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.price_track import PriceTrack, compute_price_track
from gpu_agent import bands
from gpu_agent import reader
from gpu_agent import brief   # module ref; brief also does `from gpu_agent import report` — both resolve at call-time

# ── Constants ────────────────────────────────────────────────────────────────

RATING_SCALE: dict[str, int] = {
    "Very strong": 5,
    "Strong": 4,
    "Mixed": 3,
    "Weak": 2,
    "Very weak": 1,
}
DIRECTION_ARROW: dict[str, str] = {
    "improving": "↑",
    "steady": "→",
    "worsening": "↓",
}
SDGI_INTERP_RULES = [
    (0.05, "Demand outrunning supply — shortage pressure forming"),
    (-0.05, "Demand and supply roughly balanced"),
    (float("-inf"), "Supply outrunning demand — glut pressure forming"),
]
_VERSION_RE = re.compile(r"^(\d{4}-\d{2}(?:-\d{2})?)-v(\d+)\.json$")


# ── I/O helpers ──────────────────────────────────────────────────────────────

def load_scorecard(path: Path) -> Scorecard:
    """Parse a scorecard JSON file into a typed Scorecard. Raises ValueError on failure."""
    try:
        raw = json.loads(Path(path).read_text("utf-8"))
        return Scorecard.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — normalize any parse/validation error
        raise ValueError(f"Failed to load scorecard from {path}: {exc}") from exc


def find_prior(
    store_dir: Path,
    sc: Scorecard,
    current_path: Optional[Path] = None,
    unmatched: Optional[list[str]] = None,
) -> Optional[Path]:
    """Return the most-recent previous scorecard for sc.categoryId in store_dir, or None.

    Scans store_dir/<categoryId>/*.json, parses <asOf>-v<N>.json filenames — asOf may be
    month grain (YYYY-MM) or day grain (YYYY-MM-DD) — sorts by (asOf, N) descending.
    Mixed grain sorts lexically (e.g. "2026-06" < "2026-06-15"); grain consistency per
    category is enforced wiki-side by another stream, not here.

    When *current_path* is provided the function identifies the current
    scorecard's (asOf, version) from its filename, excludes it from the
    candidate list, and returns the candidate with the highest (asOf, version)
    that is strictly less than the current.  This correctly handles rendering
    an older version (e.g. v2 → prior=v1, not v3) and is the mode used by the
    CLI ``report`` subcommand.

    When *current_path* is None (legacy/backward-compatible mode) the function
    assumes the newest file in the directory is the current scorecard and
    returns the second-newest entry (index 1).  Existing callers and tests
    that rely on this behaviour remain green.

    F13d: when *unmatched* is passed a list, the name of every ``.json`` file in the
    category dir that does NOT match the <asOf>-v<N>.json pattern is appended to it —
    such files are never silently skipped.
    """
    cat_dir = store_dir / sc.categoryId
    if not cat_dir.is_dir():
        return None
    candidates: list[tuple[str, int, Path]] = []
    for p in cat_dir.glob("*.json"):
        m = _VERSION_RE.match(p.name)
        if m:
            candidates.append((m.group(1), int(m.group(2)), p))
        elif unmatched is not None:
            unmatched.append(p.name)
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)

    if current_path is not None:
        # Identify the current scorecard by (asOf, version) from its filename.
        cur_name = Path(current_path).name
        cur_m = _VERSION_RE.match(cur_name)
        if not cur_m:
            # Current filename doesn't match <asOf>-v<N>.json — we cannot
            # establish a strict ordering, so return no prior (safe fallback)
            # rather than guessing the globally-newest file.
            return None
        cur_key = (cur_m.group(1), int(cur_m.group(2)))
        below = [
            (asof, v, p) for asof, v, p in candidates if (asof, v) < cur_key
        ]
        return below[0][2] if below else None

    # Legacy mode: second-newest entry is assumed to be the prior.
    if len(candidates) < 2:
        return None
    return candidates[1][2]


# ── Scalar helpers ────────────────────────────────────────────────────────────

def compute_sdgi(sc: Scorecard) -> float:
    """Return SDGI = DMI − SMI. Uses stored sdgi if present (written by sub-project B)."""
    stored = getattr(sc.demandSupply, "sdgi", None)
    if stored is not None:
        return stored
    return sc.demandSupply.dmiContribution - sc.demandSupply.smiContribution


# ── Section renderers ────────────────────────────────────────────────────────

def _as_of_date(as_of: str) -> str:
    """Normalize a possibly-partial date string (YYYY, YYYY-MM, or YYYY-MM-DD)
    to a full YYYY-MM-DD so it can be parsed by date.fromisoformat. Partial
    dates round to the coarsest boundary (Jan 1 / the 1st) so they never read
    as artificially fresher than they are."""
    if len(as_of) == 4:
        return f"{as_of}-01-01"
    if len(as_of) == 7:
        return f"{as_of}-01"
    return as_of


def evidence_vintage(sc: Scorecard) -> tuple[Optional[str], Optional[str], float]:
    """(median_date, oldest_date, share_older_than_42d) over all evidence dates.

    Pure string/date math; no clock — staleness is measured against sc.asOf,
    never against wall-clock "now". Evidence dates may be year, month, or day
    grain; each is normalized to a full date only for the ordinal comparison —
    the returned median/oldest strings are the original (possibly partial)
    values. Empty findings -> (None, None, 0.0)."""
    dates = sorted(ev.date for f in sc.findings for ev in f.evidence if ev.date)
    if not dates:
        return None, None, 0.0
    median = dates[len(dates) // 2]
    cutoff = date.fromisoformat(_as_of_date(sc.asOf)).toordinal() - 42
    stale = sum(1 for d in dates if date.fromisoformat(_as_of_date(d)).toordinal() < cutoff)
    return median, dates[0], stale / len(dates)


def render_header(sc: Scorecard, render_ts: str) -> str:
    """Render the report banner with category id, cycle, render timestamp,
    evidence vintage, and an honestly-labeled confidence line.

    ``render_ts`` is the only time input — supplied by the caller, never read
    from the clock here — so the header is byte-identical for equal inputs.
    """
    title = f"CATEGORY REPORT: {sc.categoryId}  |  Cycle: {sc.asOf}  |  {render_ts}"
    bar = "=" * max(len(title) + 4, 65)
    lines = [bar, title, bar]

    median, oldest, stale_share = evidence_vintage(sc)
    if median is not None:
        lines.append(f" Evidence: median {median} · oldest {oldest} · "
                     f"{round(stale_share * 100)}% older than 6 weeks")

    basis = sc.confidence.basis or ""
    m = re.search(r"(\d+)", basis)
    votes = f" ({m.group(1)} votes)" if m else ""
    lines.append(f" Confidence: vote agreement {sc.confidence.level}{votes} — "
                 f"agreement between raters, not evidence freshness")
    return "\n".join(lines)


def render_overall_status(sc: Scorecard) -> str:
    """Render the OVERALL CATEGORY STATUS section.

    Reads sc.categoryStatus (added by sub-project B). Degrades gracefully to
    'not yet available' if absent (legacy scorecards predating B).
    """
    lines = ["OVERALL CATEGORY STATUS"]
    cs = getattr(sc, "categoryStatus", None)
    if cs is None:
        lines += [
            "  Status:     not yet available  "
            "(field populated by sub-project B; scorecard predates it)",
            "  Direction:  —",
            "  Bottleneck: —",
            "  Reason:     —",
        ]
    else:
        # cs may be a typed CategoryStatus model or a plain dict.
        # F67: reason is no longer read here — it renders exactly once, in the
        # STATE OF THE MARKET headline (brief.render_state_of_market).
        if isinstance(cs, dict):
            rating = cs.get("rating", "—")
            direction = cs.get("direction", "—")
            bottleneck = cs.get("bottleneck", "—")
        else:
            rating = getattr(cs, "rating", "—")
            direction = getattr(cs, "direction", "—")
            bottleneck = getattr(cs, "bottleneck", "—")
        arrow = DIRECTION_ARROW.get(str(direction), "")
        lines += [
            f"  Status:     {rating}  {arrow} {direction}".rstrip(),
            f"  Bottleneck: {bottleneck}",
            "  Reason:     see State of the Market above",
        ]
    return "\n".join(lines)


def _dim_evidence_status(sc: Scorecard, dim: str):
    """Return (evidenceStatus, findingCount, confidenceCap, note) for a dimension.

    Prefers sc.dimensionStatus[dim] (B's authoritative six-row view). Legacy
    fallback (no dimensionStatus): grounded iff dim is in dimensionRatings;
    a legacy findingCount is not derivable here, so it is reported as None.
    """
    ds = getattr(sc, "dimensionStatus", None) or {}
    entry = ds.get(dim) if isinstance(ds, dict) else None
    if entry is not None:
        # entry is a DimensionStatus model (post-B) or a plain dict.
        if isinstance(entry, dict):
            return (entry.get("evidenceStatus", "under-supported"),
                    entry.get("findingCount", 0),
                    entry.get("confidenceCap"),
                    entry.get("note") or None)
        return (getattr(entry, "evidenceStatus", "under-supported"),
                getattr(entry, "findingCount", 0),
                getattr(entry, "confidenceCap", None),
                getattr(entry, "note", None) or None)
    # Legacy fallback: presence in the grounded-only dimensionRatings.
    if dim in sc.dimensionRatings:
        return ("grounded", None, None, None)
    return ("under-supported", 0, None, None)


def render_dimensions(sc: Scorecard, prior: Optional[Scorecard]) -> str:
    """Render DIMENSION RATINGS — all 6 dimensions, driven by dimensionStatus.

    For each canonical dimension: read evidenceStatus from sc.dimensionStatus
    (B's authoritative view; legacy fallback infers it from dimensionRatings
    presence). If grounded, JOIN sc.dimensionRatings[dim] for the rating detail.
    If under-supported, render the under-supported row from dimensionStatus.
    Δ vs prior column appears only when prior is not None.
    """
    show_delta = prior is not None
    header = "DIMENSION RATINGS"
    if show_delta:
        header += f"  (Δ vs prior cycle: {prior.asOf} (prior))"
    lines = [header]

    grounded_count = 0
    for dim in DIMENSIONS:
        ev_status, finding_count, conf_cap, note = _dim_evidence_status(sc, dim)
        dr = sc.dimensionRatings.get(dim)
        # Grounded requires both the evidence flag AND a rating row to join.
        is_grounded = (ev_status == "grounded") and (dr is not None)

        if not is_grounded:
            fc = "?" if finding_count is None else finding_count
            cap = f"; confidence capped at {conf_cap}" if conf_cap else ""
            note_str = f"; {note}" if note else ""
            delta_note = ""
            if show_delta and dim in prior.dimensionRatings:
                delta_note = "  Δ: was present in prior cycle"
            elif show_delta:
                delta_note = "  Δ: absent in prior too"
            lines.append(
                f"  {dim:<22}  —/under-supported  "
                f"(findings: {fc}{cap}{note_str}){delta_note}"
            )
        else:
            grounded_count += 1
            rating = dr.rating
            direction = dr.direction
            conf = dr.confidence.level
            arrow = DIRECTION_ARROW.get(direction, "?")
            delta_str = ""
            if show_delta:
                prior_dr = prior.dimensionRatings.get(dim)
                if prior_dr is None:
                    delta_str = "  Δ: new this cycle"
                else:
                    curr_score = RATING_SCALE.get(rating, 0)
                    prev_score = RATING_SCALE.get(prior_dr.rating, 0)
                    if curr_score > prev_score:
                        delta_str = "  Δ: ↑ improved"
                    elif curr_score < prev_score:
                        delta_str = "  Δ: ↓ worsened"
                    else:
                        delta_str = "  Δ: = same"
            lines.append(
                f"  {dim:<22}  {rating:<12}  {arrow} {direction:<12}  "
                f"{conf:<8}  grounded{delta_str}"
            )

    under_count = len(DIMENSIONS) - grounded_count
    lines.append("")
    lines.append(
        f"  Coverage: {grounded_count}/6 dimensions grounded; "
        f"{under_count} under-supported"
    )
    return "\n".join(lines)


def _sdgi_interpretation(sdgi: float) -> str:
    for threshold, label in SDGI_INTERP_RULES:
        if sdgi > threshold:
            return label
    return SDGI_INTERP_RULES[-1][1]


def _fmt_delta(current: float, prior_val: Optional[float]) -> str:
    """Format arithmetic delta; em-dash when prior is absent."""
    if prior_val is None:
        return "—"
    diff = current - prior_val
    sign = "+" if diff >= 0 else "−"
    return f"{sign}{abs(diff):.3f}"


def _momentum_word(value: float) -> str:
    # Honest direction only — no invented magnitude qualifier (the contribution
    # has no fixed 0..1 scale, so "slight"/"strong" would be unearned). Part 17.
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def render_dmi_smi_sdgi(sc: Scorecard, prior: Optional[Scorecard]) -> str:
    """Render DEMAND / SUPPLY MOMENTUM section with DMI, SMI, SDGI + Δ vs prior."""
    dmi = sc.demandSupply.dmiContribution
    smi = sc.demandSupply.smiContribution
    sdgi = compute_sdgi(sc)

    prior_dmi: Optional[float] = None
    prior_smi: Optional[float] = None
    prior_sdgi: Optional[float] = None
    if prior is not None:
        prior_dmi = prior.demandSupply.dmiContribution
        prior_smi = prior.demandSupply.smiContribution
        prior_sdgi = compute_sdgi(prior)

    delta_label = f"(Δ vs prior cycle: {prior.asOf})" if prior else ""
    lines = [f"DEMAND / SUPPLY MOMENTUM  {delta_label}".rstrip()]
    lines.append(
        f"  DMI   {dmi:.3f}   Δ {_fmt_delta(dmi, prior_dmi)}"
        f"   Demand momentum: {_momentum_word(dmi)}"
    )
    lines.append(
        f"  SMI   {smi:.3f}   Δ {_fmt_delta(smi, prior_smi)}"
        f"   Supply momentum: {_momentum_word(smi)}"
    )
    lines.append(
        f"  SDGI  {sdgi:.3f}   Δ {_fmt_delta(sdgi, prior_sdgi)}"
        f"   {_sdgi_interpretation(sdgi)}"
    )
    return "\n".join(lines)


def _pmi_word(pmi: float) -> str:
    """PMI has a fixed -1..1 scale (unlike the unbounded DMI/SMI contributions Part 17
    forbids a magnitude word on), so a magnitude threshold is earned here: |PMI| >= 0.5
    is a real majority of tracked series moving the same way."""
    if pmi >= 0.5:
        return "up"
    if pmi <= -0.5:
        return "down"
    return "flat"


_PMI_ARROW = {"up": "▲", "down": "▼", "flat": "="}


def render_price_track(track: PriceTrack) -> str:
    """Render PRICE TRACK — the Price Momentum overlay (F49): per-series levels + Δ vs
    prior, and a PMI computed over matched series only. Displayed beside DMI/SMI, never
    blended into them. Omit the whole section when the scorecard has no price series —
    honest absence, not a placeholder (render_report drops the resulting empty string).

    F67 Task 8 (dead-metric fold): when every series lacks a matched-prior delta AND
    there is no PMI (i.e. nothing has two matched cycles yet), the per-series dash rows
    ("Δ vs prior: —" on every line) are dead weight — fold them into one honest line
    instead. The moment at least one series has a matched delta (track.pmi is no longer
    None), the detailed per-series rows return."""
    if not track.series:
        return ""
    if track.pmi is None and all(s.delta is None for s in track.series):
        return (f"PRICE TRACK\n  {len(track.series)} price series captured; "
                f"day-over-day change needs two matched cycles")
    lines = ["PRICE TRACK  (overlay — displayed, never blended into DMI/SMI)"]
    for s in track.series:
        if s.delta is None:
            delta_str = "—"
        else:
            sign = "+" if s.delta >= 0 else "−"
            delta_str = f"{sign}{abs(s.delta):.2f}"
        lines.append(f"  {s.indicatorId} [{s.publisher}] {s.value:g} {s.unit}   "
                     f"Δ vs prior: {delta_str}")
    if track.pmi is None:
        lines.append(f"  PMI: — ({track.matchedSeries} matched series — "
                     f"needs two cycles of the same series)")
    else:
        word = _pmi_word(track.pmi)
        sign = "+" if track.pmi >= 0 else "−"
        lines.append(f"  PMI: {sign}{abs(track.pmi):.2f} {_PMI_ARROW[word]}   "
                     f"({track.matchedSeries} matched series)")
    return "\n".join(lines)


def _signal_label(score: float) -> str:
    """Convert a normalized polarity×magnitude score to a plain label."""
    if score > 1.5:
        return "+strong"
    if score > 0.5:
        return "+moderate"
    if score > 0.1:
        return "+slight"
    if score >= -0.1:
        return "neutral"
    if score >= -0.5:
        return "−slight"
    if score >= -1.5:
        return "−moderate"
    return "−strong"


def render_entity_panel(sc: Scorecard) -> str:
    """Render ENTITY PANEL — one sub-panel per entity found in findings.

    Entities are sorted by finding count (descending) then alphabetically.
    Each sub-panel shows: count, demand/supply signal level, up to 3 key signals.
    Findings with an empty entity string are excluded.
    """
    from collections import defaultdict
    entity_findings: dict[str, list] = defaultdict(list)
    for f in sc.findings:
        if f.entity:  # skip empty entity
            entity_findings[f.entity].append(f)

    # Sort: most findings first, then alphabetically
    sorted_entities = sorted(
        entity_findings.keys(),
        key=lambda e: (-len(entity_findings[e]), e),
    )

    lines = ["ENTITY PANEL"]
    SIDE_ORDER = {"demand": 0, "supply": 1, "structural": 2, "price": 3}
    for entity in sorted_entities:
        findings = entity_findings[entity]
        n = len(findings)
        # Demand signal: sum(polarityDemand * magnitude) / n
        demand_score = sum(f.polarityDemand * f.magnitude for f in findings) / n
        supply_score = sum(f.polaritySupply * f.magnitude for f in findings) / n
        lines.append(f"  {entity}  ({n} finding{'s' if n != 1 else ''})")
        lines.append(f"    Demand signal: {_signal_label(demand_score)}"
                     f"   Supply signal: {_signal_label(supply_score)}")
        # Top 3 findings by magnitude (desc), then side priority, then id for stable order
        top = sorted(
            findings,
            key=lambda f: (-f.magnitude, SIDE_ORDER.get(f.side, 9), f.id),
        )[:3]
        lines.append("    Key signals:")
        for f in top:
            stmt = f.statement[:100] + "..." if len(f.statement) > 100 else f.statement
            lines.append(f"      [{f.side}/{f.kind.value}]  {stmt}")
    return "\n".join(lines)


def render_evidence_quality(sc: Scorecard, registry: IndicatorRegistry) -> str:
    """Render EVIDENCE QUALITY — per-dimension distinct-finding counts + tiers.

    Uses registry.indicators to map indicatorId → dimension. Findings whose
    indicatorId is unregistered or dimension-less go to (unattributed). Each
    line reports the DISTINCT finding count for the dimension plus the
    primary/secondary EVIDENCE-item split (two different quantities, each
    labelled as exactly what it counts).
    """
    from collections import defaultdict

    # Build indicatorId → dimension map from raw registry dict (graceful on unknown ids)
    ind_to_dim: dict[str, Optional[str]] = {
        ind_id: spec.get("dimension")
        for ind_id, spec in registry.indicators.items()
    }

    # Per bucket: distinct FINDING count + primary/secondary EVIDENCE-item counts.
    # These are different quantities and are each labelled as exactly what they
    # count (A renders, never invents: never report more findings than exist).
    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"findings": 0, "primary": 0, "secondary": 0}
    )
    total_findings = 0
    total_primary = 0
    total_secondary = 0

    for f in sc.findings:
        dim = ind_to_dim.get(f.indicatorId)  # None if unregistered OR dimension-less
        bucket = dim if dim else "(unattributed)"
        counts[bucket]["findings"] += 1
        total_findings += 1
        for ev in f.evidence:
            counts[bucket][ev.tier] = counts[bucket].get(ev.tier, 0) + 1
            if ev.tier == "primary":
                total_primary += 1
            else:
                total_secondary += 1

    empty = {"findings": 0, "primary": 0, "secondary": 0}

    def _fmt_bucket(label: str, c: dict[str, int], status: bool = True) -> str:
        n = c.get("findings", 0)
        p, s = c.get("primary", 0), c.get("secondary", 0)
        if n == 0:
            return f"  {label:<22}   0 findings  ——  [under-supported]"
        plural = "s" if n != 1 else " "
        body = (f"  {label:<22}  {n:>3} finding{plural}  "
                f"(primary/secondary evidence: {p}/{s})")
        return body + "  [grounded]" if status else body

    lines = ["EVIDENCE QUALITY  (per dimension)"]
    for dim in DIMENSIONS:
        lines.append(_fmt_bucket(dim, counts.get(dim, empty)))
    # Unattributed bucket (non-scoring / unregistered indicators)
    uc = counts.get("(unattributed)", empty)
    if uc.get("findings", 0) > 0:
        lines.append(_fmt_bucket("(unattributed)", uc, status=False))
    lines.append("")
    lines.append(
        f"  Total: {total_findings} findings  "
        f"(primary/secondary evidence: {total_primary}/{total_secondary})"
    )
    return "\n".join(lines)


def render_sources(sc: Scorecard) -> str:
    """Render SOURCES — deduplicated evidence list, primary first then date descending.

    Derives source metadata from sc.findings[].evidence[], deduplicating by URL.
    For a repeated URL the highest tier (primary wins) and the latest date are kept.
    """
    # Collect unique sources keyed by URL; keep latest date and highest tier.
    seen: dict[str, dict] = {}
    for f in sc.findings:
        for ev in f.evidence:
            url = ev.url
            if url not in seen:
                seen[url] = {"source": ev.source, "url": url,
                             "date": ev.date, "tier": ev.tier}
            else:
                if ev.tier == "primary":
                    seen[url]["tier"] = "primary"
                if ev.date > seen[url]["date"]:
                    seen[url]["date"] = ev.date

    # Sort: primary group first then secondary; within each group by date desc,
    # then by URL for a fully deterministic ordering.
    final = sorted(
        seen.values(),
        key=lambda s: (0 if s["tier"] == "primary" else 1,
                       _neg_date_key(s["date"]), s["url"]),
    )

    n = len(final)
    lines = [f"SOURCES  ({n} unique; primary first, then by date descending)"]
    for s in final:
        domain = s["url"].split("/")[2] if s["url"].startswith("http") else s["url"][:30]
        tag = f"[{s['tier']}]"  # e.g. "[primary]" / "[secondary]" — no inner padding
        lines.append(
            f"  {tag:<12}  {domain:<30}  {s['date']}   {s['source'][:60]}"
        )
    return "\n".join(lines)


def _neg_date_key(date_str: str) -> tuple:
    """Sort key that orders ISO-8601 date strings descending (latest first).

    Inverts each character's ordinal so a plain ascending sort yields a
    descending-by-date result, without parsing partial/malformed dates.
    """
    return tuple(-ord(c) for c in date_str)


def render_coverage_gaps(sc: Scorecard) -> str:
    """Render COVERAGE / SKIP GAPS — under-supported dims + orphan source refs.

    Until sub-project C ships a coverage manifest, reports only:
    - Dimensions that are under-supported this cycle (evidenceStatus from
      dimensionStatus when present, else absence from dimensionRatings).
    - Entries in sc.sources not referenced by any finding's evidence. (sc.sources
      holds source *names*, so orphan detection matches against evidence source
      names, not URLs — adapted from the brief, which assumed URL-valued sources.)
    """
    evidence_source_names: set[str] = set()
    for f in sc.findings:
        for ev in f.evidence:
            evidence_source_names.add(ev.source)

    lines = ["COVERAGE / SKIP GAPS"]
    gap_found = False
    for dim in DIMENSIONS:
        ev_status, _fc, _cap, _note = _dim_evidence_status(sc, dim)
        is_grounded = (ev_status == "grounded") and (dim in sc.dimensionRatings)
        if not is_grounded:
            lines.append(
                f"  {dim:<22}  — 0 findings this cycle; dimension under-supported"
            )
            gap_found = True

    # Orphan source refs: sc.sources entries not referenced by any evidence.
    orphan_sources = [s for s in sc.sources if s not in evidence_source_names]
    if orphan_sources:
        for s in orphan_sources:
            lines.append(f"  (orphan source ref)  {s}")
    else:
        lines.append("  (No orphan source references detected)")

    if not gap_found and not orphan_sources:
        lines.append("  All 6 dimensions grounded; no coverage gaps this cycle.")
    return "\n".join(lines)


def render_trust_footer(sc: Scorecard, *, gate_waivers=None) -> str:
    """TRUST & COVERAGE: the one honest caveat (brief.render_market_caveat) — read
    direction, not level. Renders above reader.APPENDIX_DIVIDER, so it carries no raw
    index numbers or off-allowlist acronyms.

    F67 Task 8 (controller item 1): the raw-index table this footer used to carry below
    the caveat has moved to its own appendix section (render_raw_indices, below the
    divider) — DMI/SMI/SDGI are off the exec acronym allowlist and never belonged above
    the fold in the first place.

    Final-review addition (spec §1 row 8): two evidence-trust lines below the caveat,
    both reader.TIER_LABEL-worded (never the bare "primary"/"secondary" words, which the
    above-the-fold jargon lint bans) — an Evidence line (finding count + evidence-item
    tier split) always renders; a Thin evidence line (counts only, no dimension names,
    no jargon words) renders only when at least one of the six dimensions is not grounded,
    reusing the exact is_grounded rule render_dimensions/render_coverage_gaps use.
    """
    lines = [brief.render_market_caveat(sc, gate_waivers=gate_waivers)]
    n = len(sc.findings)
    primary_n = sum(1 for f in sc.findings for ev in f.evidence if ev.tier == "primary")
    secondary_n = sum(1 for f in sc.findings for ev in f.evidence if ev.tier == "secondary")
    lines.append(
        f"  Evidence: {n} finding{'s' if n != 1 else ''} — {primary_n} evidence items "
        f"from {reader.TIER_LABEL['primary']}, {secondary_n} from {reader.TIER_LABEL['secondary']}"
    )
    under_count = sum(
        1 for dim in DIMENSIONS
        if not (_dim_evidence_status(sc, dim)[0] == "grounded" and sc.dimensionRatings.get(dim) is not None)
    )
    if under_count:
        lines.append(f"  Thin evidence: {under_count} of 6 dimensions (detail in appendix)")
    return "\n".join(lines)


def render_raw_indices(sc: Scorecard, prior: Optional[Scorecard]) -> str:
    """Appendix-only: the raw DMI/SMI/SDGI numbers — value, Δ vs prior, and the prior
    cycle's band word (gpu_agent.bands) — one row per index. Renders below
    reader.APPENDIX_DIVIDER (F67 Task 8 split out of render_trust_footer): DMI/SMI/SDGI
    are off the exec acronym allowlist, so a reader who wants the underlying number
    instead of the band word finds it here, demoted below the fold; content is
    unchanged from the table this replaces in the old trust footer."""
    dmi = sc.demandSupply.dmiContribution
    smi = sc.demandSupply.smiContribution
    sdgi = compute_sdgi(sc)
    p_dmi = prior.demandSupply.dmiContribution if prior is not None else None
    p_smi = prior.demandSupply.smiContribution if prior is not None else None
    p_sdgi = compute_sdgi(prior) if prior is not None else None

    lines = ["Raw indices (DMI/SMI/SDGI):"]
    for label, value, prior_value in (
        ("DMI", dmi, p_dmi), ("SMI", smi, p_smi), ("SDGI", sdgi, p_sdgi),
    ):
        was = f"(was {bands.band_word(prior_value).upper()})" if prior_value is not None else "(no prior)"
        lines.append(f"    {label} {value:.3f}  Δ {_fmt_delta(value, prior_value)}  {was}")
    return "\n".join(lines)


def render_citation_map(sc: Scorecard) -> str:
    """Appendix-only CITATION MAP (spec §1 row 9): one line per finding id -> the tier,
    date, and (truncated) source of EACH of that finding's evidence items, sorted by
    finding id. This is where the full finding-id -> source/date/tier map lives — THE
    CALLS / WHY compress citations to counts above the fold (reader contract: never dump
    ids), so a reader who wants to trace a specific id back to its sources finds them
    all here (F68b: a finding corroborated by several publishers previously showed only
    its first source; now every evidence item gets its own line).
    "" when there are no findings (render_report drops the resulting empty string)."""
    if not sc.findings:
        return ""
    lines = ["CITATION MAP"]
    for f in sorted(sc.findings, key=lambda f: f.id):
        if not f.evidence:
            continue
        for ev in f.evidence:
            lines.append(f"  {f.id}  {ev.tier}  {ev.date}  {ev.source[:60]}")
    return "\n".join(lines)


def render_report(
    sc: Scorecard,
    prior: Optional[Scorecard],
    registry: IndicatorRegistry,
    *,
    render_ts: Optional[str] = None,
    horizons=None,
    movement=None,
    thesis_book=None,
    thesis_last_findings=None,
    daily: bool = False,
    gate_waivers=None,
) -> str:
    """Compose the full board-ready report from a scorecard + optional prior.

    Calls every render_* function in canonical section order and joins sections
    with a blank line. ``render_ts`` is injected (the clock is only read here when
    the caller passes None) so output is byte-identical for identical inputs.

    F67 Task 8 (output contract, inverted pyramid) page order — the brief is one fixed
    section order, everything either earns its place above the fold or folds to one
    honest line: HEADER -> STATE OF THE MARKET (words-first BLUF) -> WHAT MOVED (the
    diff vs prior) -> THE CALLS (the standing thesis book) -> WHY (drivers ->
    constraints, projected from the same book) -> DEMAND|SUPPLY board -> STORYLINES ->
    TRUST & COVERAGE (the one honest caveat) -> reader.APPENDIX_DIVIDER -> OVERALL
    CATEGORY STATUS -> DIMENSION RATINGS -> the raw DMI/SMI/SDGI index table -> PRICE
    TRACK -> ENTITY PANEL -> EVIDENCE QUALITY -> SOURCES -> COVERAGE GAPS -> the full
    CITATION MAP. Everything below the divider is internal/technical detail (raw index
    acronyms, ids); everything above it passes reader.lint_acronyms + the label-map
    jargon ban (spec §2a) — a TSMC executive with zero repo knowledge can read the top
    half start to finish.

    ``daily`` (F67 §4): the daily cadence shares this exact renderer/order — "one
    renderer, so monthly and daily cannot drift apart" — but swaps STATE OF THE MARKET
    and WHAT MOVED so the daily leads with the diff (its natural content); everything
    else, including the appendix, is untouched.

    Args:
        sc: the current scorecard to render.
        prior: the previous-cycle scorecard for Δ columns; None for no delta.
        registry: the indicator registry for evidence-quality dimension mapping.
        render_ts: ISO-8601 timestamp string for the header; defaults to now(UTC).
        horizons: optional IndicatorHorizons for the demand/supply board leading tags.
        movement: optional MarketMovement (from wiki.movement.collect_movement) feeding
            the WHAT MOVED / STORYLINES sections; None renders their honest empty-state.
        thesis_book: optional ThesisBook (gpu_agent.thesis) feeding THE CALLS / WHY;
            None renders their honest empty-state (no thesis cycle has ever run yet).
        thesis_last_findings: optional dict of thesisId -> latest-judgment findingIds
            (read from theses/<categoryId>/history.jsonl by the caller — the book itself
            does not store them); feeds THE CALLS' cited-evidence line and, per spec §4,
            every WHY driver/Contested line's trailing findingIds citation.
        daily: when True, lead with WHAT MOVED instead of STATE OF THE MARKET (F67 §4).
    """
    if render_ts is None:
        render_ts = datetime.now(timezone.utc).isoformat()

    track = compute_price_track(sc, prior)   # F49 — computed once, shared by brief + report

    top = [
        render_header(sc, render_ts),
        brief.render_state_of_market(sc, prior, track),       # words-first BLUF
        brief.render_what_moved(movement),
        brief.render_the_calls(thesis_book, sc, thesis_last_findings, registry=registry),
        brief.render_why(thesis_book, thesis_last_findings),  # drivers -> constraints
        brief.render_demand_supply_board(sc, horizons, registry=registry),
        brief.render_storylines(movement),
        render_trust_footer(sc, gate_waivers=gate_waivers),   # the one honest caveat (+F75 waivers)
    ]
    if daily:   # F67 §4: the daily's headline is the diff
        top[1], top[2] = top[2], top[1]

    appendix = [
        reader.APPENDIX_DIVIDER,
        render_overall_status(sc),
        render_dimensions(sc, prior),
        render_raw_indices(sc, prior),      # off-allowlist DMI/SMI/SDGI, demoted below the fold
        render_price_track(track),          # F49, omitted (returns "") with no price series
        render_entity_panel(sc),
        render_evidence_quality(sc, registry),
        render_sources(sc),
        render_coverage_gaps(sc),
        render_citation_map(sc),            # spec §1 row 9: full finding id -> source/date/tier map
    ]
    return "\n\n".join(s for s in top + appendix if s)
