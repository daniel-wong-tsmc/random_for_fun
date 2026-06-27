"""gpu_agent/report.py — deterministic scorecard-to-report renderer.

Pure functions, no LLM, no network, no store writes.
Same scorecard + prior → byte-identical report. The only injected time input is
``render_ts`` (a caller-supplied string); render functions never read the clock.
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS
from gpu_agent.registry.indicators import IndicatorRegistry

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
_VERSION_RE = re.compile(r"^(\d{4}-\d{2})-v(\d+)\.json$")


# ── I/O helpers ──────────────────────────────────────────────────────────────

def load_scorecard(path: Path) -> Scorecard:
    """Parse a scorecard JSON file into a typed Scorecard. Raises ValueError on failure."""
    try:
        raw = json.loads(Path(path).read_text("utf-8"))
        return Scorecard.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — normalize any parse/validation error
        raise ValueError(f"Failed to load scorecard from {path}: {exc}") from exc


def find_prior(store_dir: Path, sc: Scorecard) -> Optional[Path]:
    """Return the most-recent previous scorecard for sc.categoryId in store_dir, or None.

    Scans store_dir/<categoryId>/*.json, parses <asOf>-v<N>.json filenames,
    sorts by (asOf, N) descending, and returns the second entry (index 1).
    The most-recent entry (index 0) is assumed to be the current scorecard.
    """
    cat_dir = store_dir / sc.categoryId
    if not cat_dir.is_dir():
        return None
    candidates: list[tuple[str, int, Path]] = []
    for p in cat_dir.glob("*.json"):
        m = _VERSION_RE.match(p.name)
        if m:
            candidates.append((m.group(1), int(m.group(2)), p))
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
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

def render_header(sc: Scorecard, render_ts: str) -> str:
    """Render the report banner with category id, cycle, and render timestamp.

    ``render_ts`` is the only time input — supplied by the caller, never read
    from the clock here — so the header is byte-identical for equal inputs.
    """
    title = f"CATEGORY REPORT: {sc.categoryId}  |  Cycle: {sc.asOf}  |  {render_ts}"
    bar = "=" * max(len(title) + 4, 65)
    return f"{bar}\n{title}\n{bar}"


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
        if isinstance(cs, dict):
            rating = cs.get("rating", "—")
            direction = cs.get("direction", "—")
            bottleneck = cs.get("bottleneck", "—")
            reason = cs.get("reason", "—")
        else:
            rating = getattr(cs, "rating", "—")
            direction = getattr(cs, "direction", "—")
            bottleneck = getattr(cs, "bottleneck", "—")
            reason = getattr(cs, "reason", "—")
        arrow = DIRECTION_ARROW.get(str(direction), "")
        lines += [
            f"  Status:     {rating}  {arrow} {direction}".rstrip(),
            f"  Bottleneck: {bottleneck}",
            f"  Reason:     {reason}",
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
    if value > 0:
        return "slight positive"
    if value < 0:
        return "slight negative"
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
    """Render EVIDENCE QUALITY — per-dimension evidence counts by source tier.

    Uses registry.indicators to map indicatorId → dimension. Findings whose
    indicatorId is unregistered or dimension-less go to (unattributed). Each
    finding's evidence items are tallied by tier (primary/secondary).
    """
    from collections import defaultdict

    # Build indicatorId → dimension map from raw registry dict (graceful on unknown ids)
    ind_to_dim: dict[str, Optional[str]] = {
        ind_id: spec.get("dimension")
        for ind_id, spec in registry.indicators.items()
    }

    # Bucket evidence items: dimension → {primary: int, secondary: int}
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"primary": 0, "secondary": 0})
    total_primary = 0
    total_secondary = 0

    for f in sc.findings:
        dim = ind_to_dim.get(f.indicatorId)  # None if unregistered OR dimension-less
        bucket = dim if dim else "(unattributed)"
        for ev in f.evidence:
            counts[bucket][ev.tier] = counts[bucket].get(ev.tier, 0) + 1
            if ev.tier == "primary":
                total_primary += 1
            else:
                total_secondary += 1

    lines = ["EVIDENCE QUALITY  (per dimension)"]
    for dim in DIMENSIONS:
        c = counts.get(dim, {"primary": 0, "secondary": 0})
        total = c.get("primary", 0) + c.get("secondary", 0)
        ev_status = "grounded" if total > 0 else "under-supported"
        if total == 0:
            lines.append(f"  {dim:<22}   0 findings  ——  [{ev_status}]")
        else:
            lines.append(
                f"  {dim:<22}  {total:>3} findings  "
                f"(primary: {c.get('primary', 0)}, secondary: {c.get('secondary', 0)})  "
                f"[{ev_status}]"
            )
    # Unattributed bucket (non-scoring / unregistered indicators)
    uc = counts.get("(unattributed)", {"primary": 0, "secondary": 0})
    utotal = uc.get("primary", 0) + uc.get("secondary", 0)
    if utotal > 0:
        lines.append(
            f"  {'(unattributed)':<22}  {utotal:>3} findings  "
            f"(primary: {uc.get('primary', 0)}, secondary: {uc.get('secondary', 0)})"
        )
    total_all = total_primary + total_secondary
    lines.append("")
    lines.append(
        f"  Total: {total_all} findings  "
        f"(primary: {total_primary}, secondary: {total_secondary})"
    )
    return "\n".join(lines)
