"""gpu_agent/report.py — deterministic scorecard-to-report renderer.

Pure functions, no LLM, no network, no store writes.
Same scorecard + prior → byte-identical report. The only injected time input is
``render_ts`` (a caller-supplied string); render functions never read the clock.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Optional

from gpu_agent.schema.scorecard import Scorecard, DIMENSIONS

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
