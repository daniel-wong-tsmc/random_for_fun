"""gpu_agent/pricefeed.py — the local-CSV price-feed reader (F78 Stage 5, D9).

Read-only. Loads the gitignored gpu_agent/scrape_data/{aws,coreweave,gcp,oracle}_gpu_price.csv
files and produces representative GPU rental prices normalized to $/GPU-hour, on-demand term,
USA region, mapped instance-family -> GPU model, keyed by an `asOf` date label.

DISPLAY-ONLY (F8): this module NEVER feeds scoring.py / DMI / SMI. It is a
confirmation/overlay surface, a sibling to price_track.py's PMI (which reads Scorecard
findings; this reads the raw CSVs). It touches no scorecard and no index.

DETERMINISM: every price is selected by the `asOf` label via period_end(label) -> a YYMMDD
date, then the nearest scrape date AT/BEFORE it. No wall-clock is ever read.
"""
from __future__ import annotations

import csv
import datetime
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from gpu_agent.asof import days_between, period_end

DEFAULT_DATA_DIR = Path(__file__).parent / "scrape_data"
HEADLINE_MODELS = ("H100", "H200", "B200", "B300")
PROVIDERS = ("aws", "coreweave", "gcp", "oracle")


@dataclass(frozen=True)
class PricePoint:
    """One normalized $/GPU-hour observation, on-demand, USA, at the nearest scrape date
    at/before `as_of`. `gpu_class` is 'gpu' or 'custom_silicon' (AWS Trainium)."""
    provider: str          # "aws" | "coreweave" | "gcp" | "oracle"
    vendor: str            # "nvidia" | "aws" | "amd"
    model: str             # "H100","H200","B200","B300","GB200","Trainium1", ...
    gpu_class: str         # "gpu" | "custom_silicon"
    region: str            # the region label actually selected (provenance)
    term: str              # "on_demand"
    usd_per_gpu_hour: float
    price_date: str        # YYMMDD row/column actually used (nearest at/before)
    as_of: str             # the requested label
    instance: str          # source instance / shape / sku name (provenance)


# --- label / date helpers -------------------------------------------------------------

def _label_to_yymmdd(label: str) -> str:
    """Day-grain asOf label -> the CSV's YYMMDD column/row key (deterministic via
    period_end; never wall-clock)."""
    return period_end(label).strftime("%y%m%d")


def _nearest_at_or_before(target_yymmdd: str, available) -> str | None:
    """The greatest available YYMMDD key <= target, or None. Zero-padded fixed-width
    YYMMDD strings sort chronologically, so string comparison is safe."""
    candidates = [d for d in available if d <= target_yymmdd]
    return max(candidates) if candidates else None


def lookback_label(as_of: str, days: int) -> str:
    """The day-grain label `days` calendar days before `as_of` (for since-yesterday/-week/
    -month deltas). Derived from period_end(as_of), never wall-clock."""
    return (period_end(as_of) - datetime.timedelta(days=days)).isoformat()


# --- cell parse helpers ---------------------------------------------------------------

def _money(s) -> float | None:
    """'$68.80' / '$1,234.50' -> float; blank/None/garbage -> None."""
    s = (s or "").strip().replace("$", "").replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _lead_int(s) -> int | None:
    """Leading integer of a possibly footnote-polluted count cell ('4^1' -> 4)."""
    m = re.match(r"\s*(\d+)", s or "")
    return int(m.group(1)) if m else None


# GB/GH prefixes listed before the bare B/H so 'GB200' is not read as 'B200'. (\bB200\b
# does not match inside 'GB200' anyway — no word boundary between G and B — but explicit
# order keeps intent obvious.)
_MODEL_PATTERNS = [
    (re.compile(r"\bGB300\b", re.I), "GB300"),
    (re.compile(r"\bGB200\b", re.I), "GB200"),
    (re.compile(r"\bGH200\b", re.I), "GH200"),
    (re.compile(r"\bB300\b", re.I), "B300"),
    (re.compile(r"\bB200\b", re.I), "B200"),
    (re.compile(r"\bH200\b", re.I), "H200"),
    (re.compile(r"\bH100\b", re.I), "H100"),
    (re.compile(r"\bA100\b", re.I), "A100"),
    (re.compile(r"\bMI355X\b", re.I), "MI355X"),
    (re.compile(r"\bMI300X\b", re.I), "MI300X"),
    (re.compile(r"\bL40S\b", re.I), "L40S"),
    (re.compile(r"\bL40\b", re.I), "L40"),
    (re.compile(r"\bA10\b", re.I), "A10"),
    (re.compile(r"\bV100\b", re.I), "V100"),
    (re.compile(r"\bP100\b", re.I), "P100"),
]


def _match_model(text: str) -> str | None:
    for pat, name in _MODEL_PATTERNS:
        if pat.search(text or ""):
            return name
    return None


def _vendor(text: str) -> str:
    low = (text or "").lower()
    if "amd" in low or "mi300" in low or "mi355" in low:
        return "amd"
    return "nvidia"
