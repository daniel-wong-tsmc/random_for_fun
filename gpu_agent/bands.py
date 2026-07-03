"""gpu_agent/bands.py — the five-word band map (piece 5-2, output surgery).

Pure, deterministic, stdlib-only: maps a raw DMI/SMI-style value in roughly
[-1, 1] to one of five words (accelerating/firm/flat/softening/contracting),
and, given the prior cycle's value, renders the earned "WORD ARROW (was WORD)"
line the report leads with — words first, no invented magnitudes (charter Part
17). Raw indices move to the trust footer (docs/superpowers/specs/
2026-07-02-thesis-book-design.md §4); this module is the only place the
threshold numbers live, so retuning them retunes every caller at once.
"""
from __future__ import annotations

# v1 thresholds — documented, retunable data (spec §4). Ordered descending by
# threshold. The two positive floors are inclusive (>=); the two negative
# floors are exclusive (>) — so -0.05 itself is "softening" (not "flat") and
# -0.30 itself is "contracting" (not "softening"). Anything not caught by these
# four floors is "contracting" — the implicit fifth band, with no floor of its
# own.
BANDS: list[tuple[float, str]] = [
    (0.30, "accelerating"),
    (0.05, "firm"),
    (-0.05, "flat"),
    (-0.30, "softening"),
]

# Ascending rank, worst -> best, derived from BANDS so a retune of the
# thresholds/words above keeps band_with_prior's arrow logic consistent
# automatically.
_WORD_RANK: list[str] = ["contracting"] + [word for _, word in reversed(BANDS)]

_ARROW_ROSE = "▲"
_ARROW_FELL = "▼"
_ARROW_SAME = "="
_ARROW_NO_PRIOR = "·"


def band_word(value: float) -> str:
    """One of accelerating/firm/flat/softening/contracting, lowercase.

    Positive floors are inclusive (>=); negative floors are exclusive (>);
    see BANDS for the exact pinned thresholds.
    """
    for threshold, word in BANDS:
        if threshold >= 0:
            if value >= threshold:
                return word
        elif value > threshold:
            return word
    return "contracting"


def band_with_prior(value: float, prior: float | None) -> str:
    """'ACCELERATING ▲ (was FIRM)' style: the current band uppercased, an arrow
    for the move versus the prior cycle's band, and the prior band uppercased.

    Arrow: ▲ if the band rank rose vs prior, ▼ if it fell, = if unchanged, ·
    when there is no prior cycle to compare against (first cycle) — in which
    case the trailing clause reads '(no prior)' instead of '(was WORD)'.
    """
    word = band_word(value)
    if prior is None:
        return f"{word.upper()} {_ARROW_NO_PRIOR} (no prior)"
    prior_word = band_word(prior)
    rank = _WORD_RANK.index(word)
    prior_rank = _WORD_RANK.index(prior_word)
    if rank > prior_rank:
        arrow = _ARROW_ROSE
    elif rank < prior_rank:
        arrow = _ARROW_FELL
    else:
        arrow = _ARROW_SAME
    return f"{word.upper()} {arrow} (was {prior_word.upper()})"
