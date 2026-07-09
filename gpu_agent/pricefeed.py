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


# --- shared CSV reader ----------------------------------------------------------------

def _read_csv(path: Path) -> list[list[str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def _first_available(order, mapping):
    """First key in `order` that is present in `mapping`, else None (region fallback)."""
    for key in order:
        if key in mapping:
            return key
    return None


# --- AWS ------------------------------------------------------------------------------
# The CSV has NO GPU-count column, so this table is the AUTHORITY for per-GPU
# normalization. Counts are pinned from AWS instance specs and sanity-checked in Task 7.
# (vendor, model, gpu_class, gpu_count)
AWS_INSTANCE_MAP = {
    "p5.48xlarge":      ("nvidia", "H100", "gpu", 8),
    "p5en.48xlarge":    ("nvidia", "H200", "gpu", 8),
    "p6-b200.48xlarge": ("nvidia", "B200", "gpu", 8),
    "p6-b300.48xlarge": ("nvidia", "B300", "gpu", 8),
    "trn1.2xlarge":     ("aws", "Trainium1", "custom_silicon", 1),
    "trn1.32xlarge":    ("aws", "Trainium1", "custom_silicon", 16),
    "trn1n.32xlarge":   ("aws", "Trainium1", "custom_silicon", 16),
    "trn2.48xlarge":    ("aws", "Trainium2", "custom_silicon", 16),
    "u-p6e-gb200x36":   ("nvidia", "GB200", "gpu", 36),
    "u-p6e-gb200x72":   ("nvidia", "GB200", "gpu", 72),
}
# Preferred USA region, then documented fallbacks (some instances live only in Ohio/Oregon).
AWS_REGION_FALLBACKS = ["US East (N. Virginia)", "US East (Ohio)", "US West (Oregon)"]


def _aws_points(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    path = Path(data_dir) / "aws_price.csv"
    if not path.exists():
        return []
    rows = _read_csv(path)
    date_cols = rows[0][3:]
    target = _label_to_yymmdd(as_of)
    # instance -> region -> {date: price} over non-blank on_demand cells only
    by_inst: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows[1:]:
        instance, term, region = row[0], row[1], row[2]
        if term != "on_demand" or instance not in AWS_INSTANCE_MAP:
            continue
        series = {date_cols[i]: v for i, v in enumerate(row[3:]) if v.strip()}
        if series:
            by_inst[instance][region] = series
    points: list[PricePoint] = []
    for instance, regions in by_inst.items():
        vendor, model, gpu_class, gpu_count = AWS_INSTANCE_MAP[instance]
        region = _first_available(AWS_REGION_FALLBACKS, regions)
        if region is None:
            continue                                   # no USA on_demand row for this instance
        series = regions[region]
        pdate = _nearest_at_or_before(target, sorted(series))
        if pdate is None:
            continue
        price = float(series[pdate]) / gpu_count
        points.append(PricePoint(
            provider="aws", vendor=vendor, model=model, gpu_class=gpu_class,
            region=region, term="on_demand", usd_per_gpu_hour=round(price, 6),
            price_date=pdate, as_of=as_of, instance=instance))
    return sorted(points, key=lambda p: (p.model, p.instance))


# --- Oracle ---------------------------------------------------------------------------
# Oracle's "GPU Price Per Hour **" is ALREADY per-GPU; no region/term columns (single
# region, on-demand implied). Shape carries a trailing "\n(new)" to strip.

def _oracle_points(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    path = Path(data_dir) / "oracle_gpu_price.csv"
    if not path.exists():
        return []
    rows = _read_csv(path)
    h = {name: i for i, name in enumerate(rows[0])}
    si, gi, pi, di = h["Shape"], h["GPUs"], h["GPU Price Per Hour **"], h["date"]
    target = _label_to_yymmdd(as_of)
    by_shape: dict[str, dict[str, tuple[float, str]]] = defaultdict(dict)
    for row in rows[1:]:
        price = _money(row[pi])
        if price is None:
            continue
        shape = row[si].split("\n")[0].strip()
        by_shape[shape][row[di]] = (price, row[gi])
    points: list[PricePoint] = []
    for shape, series in by_shape.items():
        pdate = _nearest_at_or_before(target, sorted(series))
        if pdate is None:
            continue
        price, gtext = series[pdate]
        model = _match_model(gtext) or _match_model(shape)
        if model is None:
            continue
        points.append(PricePoint(
            provider="oracle", vendor=_vendor(gtext), model=model, gpu_class="gpu",
            region="(global)", term="on_demand", usd_per_gpu_hour=round(price, 6),
            price_date=pdate, as_of=as_of, instance=shape))
    return sorted(points, key=lambda p: (p.model, p.instance))


# --- GCP ------------------------------------------------------------------------------
# The name encodes model + pricing-mode + region. The on-demand ("running in ...", no
# Commitment/Spot/DWS prefix) + Americas SKUs are exactly these four; price is per-GPU.
# NOTE (data fact): the GCP file contains NO TPU / custom silicon — every SKU is H100/
# H200/B200 Nvidia. So there is no GCP custom-silicon series (see Task 6).
GCP_ONDEMAND_AMERICAS = {
    "Nvidia H100 80GB GPU running in Americas": "H100",
    "Nvidia H100 80GB Plus GPU running in Americas": "H100",
    "H200 141GB GPU running in Americas": "H200",
    "A4 Nvidia B200 (1 gpu slice) running in Americas": "B200",
}


def _gcp_points(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    path = Path(data_dir) / "gcp_gpu_price.csv"
    if not path.exists():
        return []
    target = _label_to_yymmdd(as_of)
    by_name: dict[str, dict[str, str]] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        ni, pi, di = header.index("name"), header.index("price"), header.index("date")
        for row in r:
            name = row[ni]
            if name in GCP_ONDEMAND_AMERICAS:
                by_name[name][row[di]] = row[pi]
    points: list[PricePoint] = []
    for name, model in GCP_ONDEMAND_AMERICAS.items():
        series = by_name.get(name)
        if not series:
            continue
        pdate = _nearest_at_or_before(target, sorted(series))
        if pdate is None:
            continue
        price = _money(series[pdate])            # per-GPU already; _money also tolerates plain floats
        if price is None:
            continue
        points.append(PricePoint(
            provider="gcp", vendor="nvidia", model=model, gpu_class="gpu",
            region="Americas", term="on_demand", usd_per_gpu_hour=round(price, 6),
            price_date=pdate, as_of=as_of, instance=name))
    return sorted(points, key=lambda p: (p.model, p.instance))


# --- CoreWeave ------------------------------------------------------------------------
# Best-effort: the priced rows carry a BLANK Region (the NORTH AMERICA label lands on
# other, price-blank rows), and the Instance Price feed goes stale after ~260310. We
# relax the region (CoreWeave is a single US-centric neocloud) and take the nearest
# PRICED date at/before as_of. Staleness is surfaced via price_date (Task 6 filters it).

def _coreweave_points(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    path = Path(data_dir) / "coreweave_gpu_price.csv"
    if not path.exists():
        return []
    rows = _read_csv(path)
    h = {name: i for i, name in enumerate(rows[0])}
    gi, ci, ip, di = h["GPU Model"], h["GPU Count"], h["Instance Price (Per Hour)"], h["date"]
    target = _label_to_yymmdd(as_of)
    by_model: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows[1:]:
        price = _money(row[ip])
        count = _lead_int(row[ci])
        if price is None or not count:
            continue
        model = _match_model(row[gi])
        if model is None:
            continue
        by_model[model][row[di]] = price / count
    points: list[PricePoint] = []
    for model, series in by_model.items():
        pdate = _nearest_at_or_before(target, sorted(series))
        if pdate is None:
            continue
        points.append(PricePoint(
            provider="coreweave", vendor="nvidia", model=model, gpu_class="gpu",
            region="NORTH AMERICA (CoreWeave default)", term="on_demand",
            usd_per_gpu_hour=round(series[pdate], 6), price_date=pdate, as_of=as_of,
            instance=model))
    return sorted(points, key=lambda p: (p.model,))


# --- aggregation (public API) ---------------------------------------------------------

def load_points(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    """Every normalized PricePoint across all four providers for `as_of` (nearest scrape
    at/before the label). Deterministic; read-only."""
    return (_aws_points(as_of, data_dir) + _coreweave_points(as_of, data_dir)
            + _gcp_points(as_of, data_dir) + _oracle_points(as_of, data_dir))


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _fresh(points, as_of, max_staleness_days):
    """Keep points whose selected price_date is within max_staleness_days of as_of
    (measured in calendar days via the asOf convention — never wall-clock)."""
    out = []
    for p in points:
        pd_label = datetime.datetime.strptime(p.price_date, "%y%m%d").date().isoformat()
        if 0 <= days_between(as_of, pd_label) <= max_staleness_days:
            out.append(p)
    return out


def headline_prices(as_of: str, data_dir=DEFAULT_DATA_DIR,
                    max_staleness_days: int = 45) -> dict[str, float]:
    """Representative $/GPU-hr per headline model (H100/H200/B200/B300): the median of
    per-provider medians over fresh gpu-class points. A model absent from the data is
    omitted. Two-level median keeps a provider with several SKUs (e.g. GCP's H100 base +
    Plus) as a single vote."""
    pts = _fresh([p for p in load_points(as_of, data_dir)
                  if p.gpu_class == "gpu" and p.model in HEADLINE_MODELS],
                 as_of, max_staleness_days)
    out: dict[str, float] = {}
    for model in HEADLINE_MODELS:
        prov_medians = []
        for prov in PROVIDERS:
            vals = [p.usd_per_gpu_hour for p in pts if p.model == model and p.provider == prov]
            m = _median(vals)
            if m is not None:
                prov_medians.append(m)
        agg = _median(prov_medians)
        if agg is not None:
            out[model] = round(agg, 4)
    return out


def price_delta(as_of: str, lookback: str, data_dir=DEFAULT_DATA_DIR,
                max_staleness_days: int = 45) -> dict[str, dict]:
    """Per headline model: current headline price at `as_of`, prior at `lookback`, and the
    absolute + percent change. Missing either side -> deltas are None (honest 'no
    comparison', never a fabricated 0)."""
    cur = headline_prices(as_of, data_dir, max_staleness_days)
    prev = headline_prices(lookback, data_dir, max_staleness_days)
    out: dict[str, dict] = {}
    for model in HEADLINE_MODELS:
        c, p = cur.get(model), prev.get(model)
        if c is None or p is None:
            out[model] = {"current": c, "prior": p, "abs_delta": None, "pct_delta": None}
        else:
            out[model] = {"current": c, "prior": p, "abs_delta": round(c - p, 4),
                          "pct_delta": round((c - p) / p * 100, 2) if p else None}
    return out


def custom_silicon_series(as_of: str, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]:
    """The custom-silicon points (AWS Trainium) as a separate labeled series — the
    substitution signal (§5.6 Optional). NOTE: GCP TPU is NOT present in the scrape data,
    so this series is Trainium-only today."""
    return [p for p in load_points(as_of, data_dir) if p.gpu_class == "custom_silicon"]
