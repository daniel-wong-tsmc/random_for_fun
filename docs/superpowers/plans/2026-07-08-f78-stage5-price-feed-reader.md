# F78 Stage 5 — Price-feed reader (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `gpu_agent/pricefeed.py` that loads the four local `scrape_data/` CSVs and produces representative GPU rental prices — normalized to **$/GPU-hour** (instance price ÷ GPU count), **on-demand** term, **USA** region, mapped instance-family → GPU model — keyed by an `asOf` date label. It exposes the current price per headline GPU model (H100 / H200 / B200 / B300), the delta vs a lookback label (since-yesterday / last-week / last-month), and a separately labeled **custom-silicon** series (AWS Trainium). The reader is **display-only** — it never feeds `scoring.py` / DMI / SMI.

**Architecture:** One module, four small **per-provider adapters** behind a common `PricePoint` record, plus a thin aggregation layer (`load_points`, `headline_prices`, `price_delta`, `custom_silicon_series`). The four CSVs do **not** share a schema — only AWS is the wide `instance, term, region, <YYMMDD…>` layout the spec describes; CoreWeave / GCP / Oracle are long-format (one row per date). Each adapter absorbs its provider's quirks and emits the same normalized `PricePoint`. Selection is by `asOf` label → `YYMMDD` → **nearest date at/before** the label (robust to blank cells and skipped scrape days). Determinism comes from `gpu_agent/asof.py::period_end` (day-grain label → date); no wall-clock is read.

**Tech Stack:** Python 3.11, stdlib `csv` + `dataclasses`, pytest. Run Python as `.venv/Scripts/python` from repo root (from a worktree: `../../.venv/Scripts/python`).

**Spec:** `docs/superpowers/specs/2026-07-08-f78-daily-change-first-brief-design.md` §5.7 (D9 price feed), §5.6 Tier 2 / Optional (scarcity + custom-silicon substitution signal), the F8 "price is display-only, never feeds DMI/SMI" rule. This is **F78 Stage 5** of 6 (build order §9 step 4 — independent; feeds the renderer, Stage 6).

**Prerequisite:** `gpu_agent/asof.py` (F78 **Stage 1**) provides `period_end(label)` and `days_between(later, earlier)`. Stage 1 is foundational (build order §9 step 1) and lands before this stage. If working a worktree where Stage 1 is not yet merged, rebase onto it first — do **not** re-implement `period_end` here.

---

## Global Constraints

Copy these verbatim into the working notes; every task honors them.

- **Determinism, never wall-clock:** prices are selected by `asOf` date label / CSV column, not `datetime.now()`. Same `asOf` in → byte-identical `PricePoint`s out. (`datetime` is imported only for `timedelta` arithmetic on a label-derived date and for `strptime` parsing a `YYMMDD` cell — never `.now()`/`.today()`.)
- **Display-only (F8):** the price feed NEVER feeds `scoring.py` / DMI / SMI; it is a confirmation/overlay surface only. It is a sibling to the existing `gpu_agent/price_track.py` PMI overlay (which reads *Scorecard findings*, not these CSVs) — this reader reads the raw local CSVs and touches no scorecard, no index.
- **Frozen core untouched:** do NOT modify `gate.py`, `scoring.py`, `pipeline.py`, `schema/*`, `judgment/*`.
- **Eval pin stays green:** no emitted brain-prompt bytes change; `tests/test_evals_baseline_pin.py` stays green. This stage adds a new module + tests only.
- **Test fixtures:** the real CSVs are ~20 MB total (GCP alone is 19 MB) and gitignored — every pytest here MUST use small inline/temp CSV fixtures (a handful of instances, a few date columns), NOT the real files, so tests are fast and committable. A separate one-off sanity task (Task 7) runs the reader against the real `gpu_agent/scrape_data/` files and prints representative $/GPU-hour to confirm the mapping.
- **Execution happens in a git worktree** per repo discipline (`.worktrees/<name>` on a claimed branch; never the root checkout's main; one shared root venv — no per-worktree venv).
- **Windows:** use the Bash tool for `>` redirects / heredocs; no double quotes inside `git commit -m` under PowerShell (use a bash heredoc). Commit trailer names the ACTUAL implementer model.
- **Suite green at every commit.** Baseline before starting: run `.venv/Scripts/python -m pytest -q` and record the pass count.

---

## Data facts derived from the real CSVs (2026-07-08 inspection)

These are the ground truth this plan is built on — read them before coding; they explain every quirk the adapters handle.

**Schemas differ per provider (only AWS matches the spec's `instance, term, region, <YYMMDD>`):**

| File | Layout | Key columns |
|---|---|---|
| `aws_price.csv` | **wide** (511 cols) | `instance, term, region, 250206 … 260708` (daily) |
| `coreweave_gpu_price.csv` | long | `'', GPU Model, GPU Count, …, Instance Price (Per Hour), date, On-Demand Price (Per Hour), Spot Price (Per Hour), …, Region` |
| `gcp_gpu_price.csv` | long (175 896 rows) | `'', name, sku_id, currency, price, rate_unit, date` |
| `oracle_gpu_price.csv` | long | `'', Shape, GPUs, Architecture, Network, GPU Price Per Hour **, date` |

**AWS** — `term` values: `on_demand`, `reserved`, `1 year`, `3 year` (want `on_demand`). Regions are human labels; the USA pick is **`US East (N. Virginia)`** with documented fallback order `US East (N. Virginia)` → `US East (Ohio)` → `US West (Oregon)`. The wide row has one price per `YYMMDD` column; **cells can be blank** (e.g. `trn2.48xlarge` on_demand stops at `250619`), so per-cell nearest-at/before is required. `u-p6e-gb200x36/x72` have **no on_demand US row** (only `reserved` in a Local Zone) → not representable under the filter; documented gap.

**CoreWeave** — `GPU Model` and `GPU Count` are explicit columns; `Instance Price (Per Hour)` is a `"$68.80"` string. **Caveats:** the priced rows carry a **blank `Region`** (the `NORTH AMERICA` value appears on *other*, price-blank rows), and the `Instance Price` feed **goes stale after ~`260310`** (blank thereafter). So CoreWeave is best-effort: region relaxed to its US-neocloud default, nearest **priced** date used.

**GCP** — the `name` is free text encoding model + pricing-mode + region, e.g. `"Nvidia H100 80GB GPU running in Americas"`, `"Commitment v1: … for 1 Year"`, `"… Spot …"`, `"… DWS Defined Duration …"`. `price` is **already per-GPU** (rate_unit `1h`). USA region token = **`Americas`**. The **on-demand + Americas** SKUs are exactly four names (below). **NO TPU / custom silicon exists anywhere in this file** — every one of the 657 SKU names is H100 / H200 / B200 Nvidia. (Confirmed by exhaustive scan.)

**Oracle** — `GPU Price Per Hour **` is a `"$10.00"` string and is **already per-GPU** (no division needed). There is **no region and no term column** (single region, on-demand implied). Includes Nvidia (H100/H200/B200/B300/GB200/GB300) **and AMD** (MI300X/MI355X — competitor GPUs, not custom silicon). `Shape` carries `\n(new)` artifacts to strip.

### Derived instance/shape → GPU-model map (the pinned, tested table)

**AWS** (no GPU-count column in the CSV — this table is the authority for counts; `$/GPU-hr = instance_price ÷ gpu_count`):

| instance | vendor | model | class | gpu_count | on_demand US price (260708) | $/GPU-hr |
|---|---|---|---|---|---|---|
| `p5.48xlarge` | nvidia | H100 | gpu | 8 | 55.04 (N. Virginia) | 6.88 |
| `p5en.48xlarge` | nvidia | H200 | gpu | 8 | 63.296 (N. Virginia) | 7.912 |
| `p6-b200.48xlarge` | nvidia | B200 | gpu | 8 | 113.9328 (N. Virginia) | 14.2416 |
| `p6-b300.48xlarge` | nvidia | B300 | gpu | 8 | 142.416 (N. Virginia) | 17.802 |
| `trn1.2xlarge` | aws | Trainium1 | **custom_silicon** | 1 | 1.34375 | 1.34375 |
| `trn1.32xlarge` | aws | Trainium1 | **custom_silicon** | 16 | 21.5 | 1.34375 |
| `trn1n.32xlarge` | aws | Trainium1 | **custom_silicon** | 16 | 24.78 | 1.54875 |
| `trn2.48xlarge` | aws | Trainium2 | **custom_silicon** | 16 | on_demand Ohio-only, stale after 250619 | ~5.37 (stale) |
| `u-p6e-gb200x36` | nvidia | GB200 | gpu | 36 | *(no on_demand US row — excluded)* | — |
| `u-p6e-gb200x72` | nvidia | GB200 | gpu | 72 | *(no on_demand US row — excluded)* | — |

**GCP** on-demand Americas SKUs (price already per-GPU; latest 260707):

| name | model | $/GPU-hr |
|---|---|---|
| `Nvidia H100 80GB GPU running in Americas` | H100 | 9.7966 |
| `Nvidia H100 80GB Plus GPU running in Americas` | H100 | 10.3443 |
| `H200 141GB GPU running in Americas` | H200 | 9.3117 |
| `A4 Nvidia B200 (1 gpu slice) running in Americas` | B200 | 16.11 |

**Oracle** (price already per-GPU; latest 260707): `BM.GPU.H100.8`→H100 $10.00, `BM.GPU.H200.8`→H200 $10.00, `BM.GPU.B200.8`→B200 $14.00, `BM.GPU.B300.8`→B300 $15.00, `BM.GPU.GB200.4`→GB200 $16.00, `BM.GPU.GB300.4`→GB300 $18.00, `BM.GPU.MI300X.8`→MI300X (AMD) $6.00, `BM.GPU.MI355X.8`→MI355X (AMD) $8.60. **CoreWeave** (per-GPU = instance ÷ count; priced only through ~260310): `NVIDIA HGX H100`→H100 $49.24/8=6.155, `NVIDIA HGX H200`→H200 $50.44/8=6.305, `NVIDIA B200`→B200 $68.80/8=8.60.

---

### Task 1: `PricePoint` record + label→column + nearest-at/before + parse helpers

**Files:**
- Create: `gpu_agent/pricefeed.py`
- Create: `tests/test_pricefeed_helpers.py`

**Interfaces:**
- Consumes: `gpu_agent.asof.period_end` (Stage 1).
- Produces: `@dataclass(frozen=True) PricePoint`; `_label_to_yymmdd(label) -> str`; `_nearest_at_or_before(target_yymmdd, available) -> str|None`; `_money(s) -> float|None`; `_lead_int(s) -> int|None`; `_match_model(text) -> str|None`; `_vendor(text) -> str`; `lookback_label(as_of, days) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pricefeed_helpers.py
import pytest
from gpu_agent.pricefeed import (
    PricePoint, _label_to_yymmdd, _nearest_at_or_before, _money, _lead_int,
    _match_model, _vendor, lookback_label,
)


def test_label_to_yymmdd():
    assert _label_to_yymmdd("2026-07-08") == "260708"
    assert _label_to_yymmdd("2025-02-06") == "250206"


def test_nearest_at_or_before_exact():
    cols = ["260601", "260607", "260608", "260707", "260708"]
    assert _nearest_at_or_before("260708", cols) == "260708"


def test_nearest_at_or_before_gap_picks_prior():
    # target 260610 has no column -> nearest at/before is 260608
    cols = ["260601", "260607", "260608", "260707", "260708"]
    assert _nearest_at_or_before("260610", cols) == "260608"


def test_nearest_at_or_before_none_when_all_after():
    assert _nearest_at_or_before("250101", ["260601", "260708"]) is None


def test_money_strips_dollar_and_commas():
    assert _money("$68.80") == 68.8
    assert _money("$1,234.50") == 1234.5
    assert _money("") is None
    assert _money("  ") is None
    assert _money(None) is None


def test_lead_int_handles_footnote_pollution():
    assert _lead_int("16") == 16
    assert _lead_int("4^1") == 4      # CoreWeave footnote artifact
    assert _lead_int("") is None


def test_match_model_gb_prefix_not_confused_with_b():
    assert _match_model("NVIDIA GB200 NVL72") == "GB200"
    assert _match_model("8x Nvidia B200 180GB") == "B200"
    assert _match_model("NVIDIA HGX H100") == "H100"
    assert _match_model("8x NVIDIA H200 141GB Tensor Core") == "H200"
    assert _match_model("8x AMD MI300X 192GB Matrix Core") == "MI300X"
    assert _match_model("something unmapped") is None


def test_vendor_detects_amd():
    assert _vendor("8x AMD MI300X 192GB Matrix Core") == "amd"
    assert _vendor("8x NVIDIA H100 80GB Tensor Core") == "nvidia"


def test_lookback_label_is_calendar_days_before():
    assert lookback_label("2026-07-08", 1) == "2026-07-07"
    assert lookback_label("2026-07-08", 7) == "2026-07-01"
    assert lookback_label("2026-07-08", 30) == "2026-06-08"


def test_pricepoint_is_frozen():
    p = PricePoint(provider="aws", vendor="nvidia", model="H100", gpu_class="gpu",
                   region="US East (N. Virginia)", term="on_demand",
                   usd_per_gpu_hour=6.88, price_date="260708", as_of="2026-07-08",
                   instance="p5.48xlarge")
    with pytest.raises(Exception):
        p.usd_per_gpu_hour = 0.0
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_helpers.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.pricefeed'`.

- [ ] **Step 3: Write the implementation**

```python
# gpu_agent/pricefeed.py
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_helpers.py -q`
Expected: PASS (all helper tests green).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_helpers.py
git commit -m "$(cat <<'EOF'
feat(F78-5): pricefeed PricePoint + label->column, nearest-at/before, parse helpers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: AWS adapter + the pinned `AWS_INSTANCE_MAP` table

**Files:**
- Modify: `gpu_agent/pricefeed.py` (add `AWS_INSTANCE_MAP`, `AWS_REGION_FALLBACKS`, `_read_csv`, `_first_available`, `_aws_points`)
- Create: `tests/test_pricefeed_aws.py`

**Interfaces:**
- Produces: `_aws_points(as_of, data_dir) -> list[PricePoint]` — on_demand only, per-instance region chosen by fallback order, $/GPU-hr = price ÷ mapped gpu_count, nearest **non-blank** cell at/before `as_of`. Instances not in the map, non-on_demand rows, and instances with no on_demand US row (the GB200 ultraservers) are skipped.

- [ ] **Step 1: Write the failing test** (inline AWS fixture — mirrors the real wide schema)

```python
# tests/test_pricefeed_aws.py
from gpu_agent.pricefeed import _aws_points

AWS_HEADER = "instance,term,region,250718,260601,260607,260608,260707,260708\n"
AWS_ROWS = [
    # p5 -> H100, 8 GPUs, N. Virginia present (and a pricier N. California to prove region pick)
    "p5.48xlarge,on_demand,US East (N. Virginia),55.04,55.04,55.04,55.04,55.04,55.04",
    "p5.48xlarge,on_demand,US West (N. California),68.8,68.8,68.8,68.8,68.8,68.8",
    "p5.48xlarge,reserved,US East (N. Virginia),40,40,40,40,40,40",          # non-on_demand -> skip
    # p5en -> H200, 8 GPUs
    "p5en.48xlarge,on_demand,US East (N. Virginia),63.296,63.296,63.296,63.296,63.296,63.296",
    # p6-b200 -> B200, 8 GPUs
    "p6-b200.48xlarge,on_demand,US East (N. Virginia),113.9328,113.9328,113.9328,113.9328,113.9328,113.9328",
    # trn1.32xlarge -> Trainium1 custom silicon, 16
    "trn1.32xlarge,on_demand,US East (N. Virginia),21.5,21.5,21.5,21.5,21.5,21.5",
    # trn2 -> only Ohio, blank in recent columns -> nearest non-blank at/before 260708 is 260607
    "trn2.48xlarge,on_demand,US East (Ohio),85.964,85.964,85.964,,,",
    # GB200 ultraserver -> only reserved local zone -> no on_demand US -> excluded
    "u-p6e-gb200x72,reserved,US East (Dallas) Local Zone,761.904,761.904,761.904,761.904,761.904,761.904",
    # foreign region only for an otherwise-mapped instance is still fine to skip via fallback
    "p6-b300.48xlarge,on_demand,Asia Pacific (Tokyo),160,160,160,160,160,160",  # no US -> skip
]


def _write_aws(tmp_path):
    (tmp_path / "aws_price.csv").write_text(AWS_HEADER + "\n".join(AWS_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_aws_normalizes_to_per_gpu_hour_and_picks_us_east(tmp_path):
    _write_aws(tmp_path)
    pts = {p.model: p for p in _aws_points("2026-07-08", tmp_path)}
    assert round(pts["H100"].usd_per_gpu_hour, 4) == 6.88          # 55.04 / 8, N. Virginia (not 68.8)
    assert pts["H100"].region == "US East (N. Virginia)"
    assert round(pts["H200"].usd_per_gpu_hour, 4) == 7.912         # 63.296 / 8
    assert round(pts["B200"].usd_per_gpu_hour, 4) == 14.2416       # 113.9328 / 8
    assert pts["H100"].price_date == "260708"
    assert pts["H100"].term == "on_demand"


def test_aws_trainium_is_custom_silicon(tmp_path):
    _write_aws(tmp_path)
    trn = [p for p in _aws_points("2026-07-08", tmp_path) if p.model == "Trainium1"]
    assert len(trn) == 1
    assert trn[0].gpu_class == "custom_silicon"
    assert trn[0].vendor == "aws"
    assert round(trn[0].usd_per_gpu_hour, 5) == 1.34375            # 21.5 / 16


def test_aws_blank_recent_cell_falls_back_to_nearest_prior(tmp_path):
    _write_aws(tmp_path)
    trn2 = [p for p in _aws_points("2026-07-08", tmp_path) if p.model == "Trainium2"]
    assert len(trn2) == 1
    assert trn2[0].price_date == "260607"                         # last non-blank <= 260708
    assert trn2[0].region == "US East (Ohio)"                     # fallback: no N. Virginia row


def test_aws_gb200_ultraserver_without_ondemand_us_is_excluded(tmp_path):
    _write_aws(tmp_path)
    models = {p.model for p in _aws_points("2026-07-08", tmp_path)}
    assert "GB200" not in models                                  # only reserved/local-zone existed
    assert "B300" not in models                                   # only APAC on_demand existed
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_aws.py -q`
Expected: FAIL with `ImportError: cannot import name '_aws_points'`.

- [ ] **Step 3: Add the table + adapter to `gpu_agent/pricefeed.py`**

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_aws.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_aws.py
git commit -m "$(cat <<'EOF'
feat(F78-5): AWS price adapter + pinned instance->GPU map ($/GPU-hr, on_demand, US East)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Oracle adapter (already per-GPU; no region/term columns)

**Files:**
- Modify: `gpu_agent/pricefeed.py` (add `_oracle_points`)
- Create: `tests/test_pricefeed_oracle.py`

**Interfaces:**
- Produces: `_oracle_points(as_of, data_dir) -> list[PricePoint]` — price taken as-is (already $/GPU-hr), model from the `GPUs`/`Shape` text, vendor nvidia/amd, region `"(global)"`, nearest priced date at/before `as_of`. All Oracle points are `gpu_class="gpu"` (no Trainium/TPU in Oracle).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pricefeed_oracle.py
from gpu_agent.pricefeed import _oracle_points

ORACLE_HEADER = ",Shape,GPUs,Architecture,Network,GPU Price Per Hour **,date\n"
ORACLE_ROWS = [
    "0,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,net,$10.00,260707",
    "1,BM.GPU.H200.8,8x Nvidia H200 141GB Tensor Core,Hopper,net,$10.00,260707",
    "2,BM.GPU.B200.8,8x Nvidia B200 180GB,Blackwell,net,$14.00,260707",
    "3,BM.GPU.MI300X.8,8x AMD MI300X 192GB Matrix Core,CDNA 3,net,$6.00,260707",
    # an older date to prove nearest-at/before + that stale rows aren't chosen when a newer exists
    "4,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,net,$9.50,260601",
]


def _write(tmp_path):
    (tmp_path / "oracle_gpu_price.csv").write_text(
        ORACLE_HEADER + "\n".join(ORACLE_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_oracle_price_is_already_per_gpu(tmp_path):
    _write(tmp_path)
    pts = {p.model: p for p in _oracle_points("2026-07-08", tmp_path)}
    assert pts["H100"].usd_per_gpu_hour == 10.0        # taken as-is, NOT divided by 8
    assert pts["H100"].price_date == "260707"          # newest at/before, not the 260601 row
    assert pts["B200"].usd_per_gpu_hour == 14.0
    assert pts["H100"].gpu_class == "gpu"


def test_oracle_classifies_amd_vendor(tmp_path):
    _write(tmp_path)
    mi = [p for p in _oracle_points("2026-07-08", tmp_path) if p.model == "MI300X"]
    assert mi and mi[0].vendor == "amd" and mi[0].gpu_class == "gpu"


def test_oracle_no_data_before_first_scrape(tmp_path):
    _write(tmp_path)
    assert _oracle_points("2025-01-01", tmp_path) == []   # all rows are after -> nothing at/before
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_oracle.py -q`
Expected: FAIL with `ImportError: cannot import name '_oracle_points'`.

- [ ] **Step 3: Add the adapter**

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_oracle.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_oracle.py
git commit -m "$(cat <<'EOF'
feat(F78-5): Oracle price adapter (per-GPU as-is; nvidia/amd; nearest-at/before)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: GCP adapter (name-parsed on-demand Americas; per-GPU; streamed)

**Files:**
- Modify: `gpu_agent/pricefeed.py` (add `GCP_ONDEMAND_AMERICAS`, `_gcp_points`)
- Create: `tests/test_pricefeed_gcp.py`

**Interfaces:**
- Produces: `_gcp_points(as_of, data_dir) -> list[PricePoint]` — filters the 19 MB file by streaming, keeping only the four known on-demand-Americas SKU names; `price` is used as-is (already per-GPU); vendor nvidia, region `"Americas"`. Commitment / Spot / DWS SKUs and non-Americas regions are excluded by the name allow-list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pricefeed_gcp.py
from gpu_agent.pricefeed import _gcp_points

GCP_HEADER = ",name,sku_id,currency,price,rate_unit,date\n"
GCP_ROWS = [
    "0,Nvidia H100 80GB GPU running in Americas,AAA,USD,9.796550569,1h,260707",
    "1,H200 141GB GPU running in Americas,BBB,USD,9.31174,1h,260707",
    "2,A4 Nvidia B200 (1 gpu slice) running in Americas,CCC,USD,16.11,1h,260707",
    "3,Nvidia H100 80GB Plus GPU running in Americas,DDD,USD,10.344275712,1h,260707",
    # noise that MUST be excluded by the allow-list:
    "4,Commitment v1: Nvidia H100 80GB GPU running in Americas for 1 Year,EEE,USD,4.0,1h,260707",
    "5,Spot Nvidia H100 80GB GPU running in Americas,FFF,USD,3.0,1h,260707",
    "6,Nvidia H100 80GB GPU running in Frankfurt,GGG,USD,11.0,1h,260707",
    # older date for nearest-at/before
    "7,Nvidia H100 80GB GPU running in Americas,AAA,USD,9.0,1h,260601",
]


def _write(tmp_path):
    (tmp_path / "gcp_gpu_price.csv").write_text(
        GCP_HEADER + "\n".join(GCP_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_gcp_ondemand_americas_only_price_is_per_gpu(tmp_path):
    _write(tmp_path)
    pts = _gcp_points("2026-07-08", tmp_path)
    by_model = {}
    for p in pts:
        by_model.setdefault(p.model, []).append(p)
    # H100 base + "Plus" both kept (two SKUs), region Americas, per-GPU as-is
    h100 = sorted(p.usd_per_gpu_hour for p in by_model["H100"])
    assert h100 == [9.796551, 10.344276]               # rounded to 6dp; the 9.0/260601 row NOT chosen
    assert all(p.region == "Americas" and p.term == "on_demand" for p in pts)
    assert by_model["H200"][0].usd_per_gpu_hour == 9.31174
    assert by_model["B200"][0].usd_per_gpu_hour == 16.11


def test_gcp_excludes_commitment_spot_and_foreign_region(tmp_path):
    _write(tmp_path)
    prices = {p.usd_per_gpu_hour for p in _gcp_points("2026-07-08", tmp_path)}
    assert 4.0 not in prices and 3.0 not in prices and 11.0 not in prices


def test_gcp_has_no_custom_silicon(tmp_path):
    # documents the data fact: the GCP file contains NO TPU / custom silicon.
    _write(tmp_path)
    assert all(p.gpu_class == "gpu" for p in _gcp_points("2026-07-08", tmp_path))
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_gcp.py -q`
Expected: FAIL with `ImportError: cannot import name '_gcp_points'`.

- [ ] **Step 3: Add the adapter** (streamed — never materializes the 175k rows)

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_gcp.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_gcp.py
git commit -m "$(cat <<'EOF'
feat(F78-5): GCP price adapter (on-demand Americas SKU allow-list, per-GPU, streamed)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: CoreWeave adapter (best-effort; region relaxed; feed stale after ~260310)

**Files:**
- Modify: `gpu_agent/pricefeed.py` (add `_coreweave_points`)
- Create: `tests/test_pricefeed_coreweave.py`

**Interfaces:**
- Produces: `_coreweave_points(as_of, data_dir) -> list[PricePoint]` — $/GPU-hr = `Instance Price` ÷ `GPU Count`, model from the `GPU Model` text, nearest **priced** date at/before `as_of`. Region is relaxed (priced rows carry a blank `Region`; CoreWeave is a single US-centric neocloud) and labeled `"NORTH AMERICA (CoreWeave default)"`. **Known caveat:** the instance-price feed goes blank after ~`260310`, so recent `as_of` labels select a lagging `price_date` — surfaced honestly via `price_date`; Task 6's staleness filter keeps a lagging CoreWeave point out of the headline median while still listing it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pricefeed_coreweave.py
from gpu_agent.pricefeed import _coreweave_points

CW_HEADER = (",GPU Model,GPU Count,VRAM (GB),vCPUs,System RAM (GB),Local Storage (TB),"
             "Instance Price (Per Hour),date,On-Demand Price (Per Hour),Spot Price (Per Hour),"
             "Inference Single GPU Price(Per Hour),Region\n")
CW_ROWS = [
    # priced rows carry a BLANK region (real-data quirk); price ÷ count
    "0,NVIDIA HGX H100,8,80,128,2048,61,$49.24,260305,,,,",
    "1,NVIDIA HGX H200,8,141,128,2048,61,$50.44,260305,,,,",
    "2,NVIDIA B200,8,180,128,2048,61,$68.80,260305,,,,",
    # a later date where price went BLANK and Region got filled -> must be ignored (no price)
    "3,NVIDIA HGX H100,8,80,128,2048,61,,260707,,,,NORTH AMERICA",
]


def _write(tmp_path):
    (tmp_path / "coreweave_gpu_price.csv").write_text(
        CW_HEADER + "\n".join(CW_ROWS) + "\n", encoding="utf-8")
    return tmp_path


def test_coreweave_per_gpu_and_nearest_priced_date(tmp_path):
    _write(tmp_path)
    pts = {p.model: p for p in _coreweave_points("2026-07-08", tmp_path)}
    assert round(pts["H100"].usd_per_gpu_hour, 4) == 6.155        # 49.24 / 8
    assert round(pts["B200"].usd_per_gpu_hour, 3) == 8.6          # 68.80 / 8
    # newest date is 260707 but its price is blank -> selects the last PRICED date 260305
    assert pts["H100"].price_date == "260305"
    assert pts["H100"].gpu_class == "gpu"
    assert "CoreWeave" in pts["H100"].region


def test_coreweave_before_first_priced_date_is_empty(tmp_path):
    _write(tmp_path)
    assert _coreweave_points("2026-01-01", tmp_path) == []
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_coreweave.py -q`
Expected: FAIL with `ImportError: cannot import name '_coreweave_points'`.

- [ ] **Step 3: Add the adapter**

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_coreweave.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_coreweave.py
git commit -m "$(cat <<'EOF'
feat(F78-5): CoreWeave price adapter (best-effort, region relaxed, nearest priced date)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Public API — `load_points`, `headline_prices`, `price_delta`, `custom_silicon_series` + determinism

**Files:**
- Modify: `gpu_agent/pricefeed.py` (add the four public functions + `_median` / `_fresh` helpers)
- Create: `tests/test_pricefeed_api.py`

**Interfaces:**
- Produces:
  - `load_points(as_of, data_dir=DEFAULT_DATA_DIR) -> list[PricePoint]` (union of all four adapters).
  - `headline_prices(as_of, data_dir=…, max_staleness_days=45) -> dict[str, float]` — representative $/GPU-hr per headline model = median of per-provider medians, over `gpu_class=="gpu"` points whose `price_date` is within `max_staleness_days` of `as_of`.
  - `price_delta(as_of, lookback, data_dir=…, max_staleness_days=45) -> dict[str, dict]` — per headline model `{current, prior, abs_delta, pct_delta}`.
  - `custom_silicon_series(as_of, data_dir=…) -> list[PricePoint]` — the `custom_silicon` points (AWS Trainium; TPU absent from the data).

- [ ] **Step 1: Write the failing test** (writes all four fixtures into one temp dir)

```python
# tests/test_pricefeed_api.py
from gpu_agent.pricefeed import (
    load_points, headline_prices, price_delta, custom_silicon_series, lookback_label,
)

# reuse the per-adapter fixtures inline (small)
AWS = ("instance,term,region,260601,260707,260708\n"
       "p5.48xlarge,on_demand,US East (N. Virginia),50.0,55.04,55.04\n"       # H100 6.88
       "trn1.32xlarge,on_demand,US East (N. Virginia),21.5,21.5,21.5\n")      # Trainium1
ORACLE = (",Shape,GPUs,Architecture,Network,GPU Price Per Hour **,date\n"
          "0,BM.GPU.H100.8,8x NVIDIA H100 80GB Tensor Core,Hopper,n,$10.00,260707\n")
GCP = (",name,sku_id,currency,price,rate_unit,date\n"
       "0,Nvidia H100 80GB GPU running in Americas,A,USD,9.796550569,1h,260707\n")
CW = (",GPU Model,GPU Count,VRAM (GB),vCPUs,System RAM (GB),Local Storage (TB),"
      "Instance Price (Per Hour),date,On-Demand Price (Per Hour),Spot Price (Per Hour),"
      "Inference Single GPU Price(Per Hour),Region\n"
      "0,NVIDIA HGX H100,8,80,128,2048,61,$49.24,260305,,,,\n")   # stale (260305)


def _write_all(tmp_path):
    (tmp_path / "aws_price.csv").write_text(AWS, encoding="utf-8")
    (tmp_path / "oracle_gpu_price.csv").write_text(ORACLE, encoding="utf-8")
    (tmp_path / "gcp_gpu_price.csv").write_text(GCP, encoding="utf-8")
    (tmp_path / "coreweave_gpu_price.csv").write_text(CW, encoding="utf-8")
    return tmp_path


def test_load_points_unions_all_providers(tmp_path):
    _write_all(tmp_path)
    provs = {p.provider for p in load_points("2026-07-08", tmp_path)}
    assert provs == {"aws", "oracle", "gcp", "coreweave"}


def test_headline_price_is_median_of_provider_medians(tmp_path):
    _write_all(tmp_path)
    # fresh H100 provider medians: aws 6.88, oracle 10.0, gcp 9.796551; coreweave (260305) is stale (>45d) -> excluded
    # median of [6.88, 9.796551, 10.0] = 9.796551
    hp = headline_prices("2026-07-08", tmp_path, max_staleness_days=45)
    assert round(hp["H100"], 4) == 9.7966
    assert "B200" not in hp                      # no B200 in these fixtures


def test_stale_provider_included_when_window_widened(tmp_path):
    _write_all(tmp_path)
    # widen staleness so CoreWeave's 260305 point (124d before 260708) is admitted:
    # provider medians [aws 6.88, coreweave 6.155, gcp 9.796551, oracle 10.0] -> median = (6.88+9.796551)/2 = 8.338276
    hp = headline_prices("2026-07-08", tmp_path, max_staleness_days=400)
    assert round(hp["H100"], 4) == 8.3383


def test_custom_silicon_is_trainium_only(tmp_path):
    _write_all(tmp_path)
    cs = custom_silicon_series("2026-07-08", tmp_path)
    assert {p.model for p in cs} == {"Trainium1"}
    assert all(p.gpu_class == "custom_silicon" and p.provider == "aws" for p in cs)


def test_price_delta_since_last_week(tmp_path):
    _write_all(tmp_path)
    # AWS H100: 260708 uses 55.04 (6.88/gpu); a week back 2026-07-01 -> nearest col <=260701 is 260601 = 50.0 (6.25/gpu)
    # but oracle/gcp have no 260601 rows, so at lookback only AWS+CoreWeave(stale,excluded) -> H100 median = 6.25
    d = price_delta("2026-07-08", lookback_label("2026-07-08", 7), tmp_path, max_staleness_days=45)
    assert d["H100"]["current"] == round(headline_prices("2026-07-08", tmp_path)["H100"], 4)
    assert d["H100"]["prior"] == 6.25
    assert d["H100"]["abs_delta"] is not None


def test_determinism_same_asof_same_bytes(tmp_path):
    _write_all(tmp_path)
    a = load_points("2026-07-08", tmp_path)
    b = load_points("2026-07-08", tmp_path)
    assert a == b                                # frozen dataclasses compare by value
```

- [ ] **Step 2: Run it — verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_api.py -q`
Expected: FAIL with `ImportError` on `load_points` / `headline_prices` / …

- [ ] **Step 3: Add the public API to `gpu_agent/pricefeed.py`**

```python
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
```

- [ ] **Step 4: Run it — verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_api.py -q`
Expected: PASS (7 passed). If a median literal is off, recompute it exactly from the fixture (do not weaken the assertion to a range).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/pricefeed.py tests/test_pricefeed_api.py
git commit -m "$(cat <<'EOF'
feat(F78-5): pricefeed public API (load_points, headline_prices, price_delta, custom_silicon)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Real-data sanity check + full-suite / eval-pin / display-only reconciliation

This is the spec's mapping-confirmation slice (§7): run the reader against the **real** `gpu_agent/scrape_data/` files and eyeball the representative $/GPU-hr for H100 / H200 / B200 / B300, then confirm the suite, the eval pin, and the display-only invariant.

- [ ] **Step 1: Run the whole new test group + full suite**

Run: `.venv/Scripts/python -m pytest tests/test_pricefeed_*.py -q` → all green.
Run: `.venv/Scripts/python -m pytest -q` → same pass count as the recorded baseline **+ the new pricefeed tests**, no regressions (expect the usual 3–4 skips). This module is additive, so nothing downstream should move.

- [ ] **Step 2: Confirm the eval pin is green**

Run: `.venv/Scripts/python -m pytest tests/test_evals_baseline_pin.py -q`
Expected: PASS (this stage emits no brain-prompt bytes — it added a data-reader module only).

- [ ] **Step 3: Confirm display-only (F8) — no scoring/DMI/SMI coupling**

Run (grep): `grep -rn "scoring\|demandSupply\|\bDMI\b\|\bSMI\b\|Scorecard\|indices" gpu_agent/pricefeed.py` — expect **ZERO** hits. `pricefeed.py` imports only `csv`, `datetime`, `re`, `collections`, `dataclasses`, `pathlib`, and `gpu_agent.asof`. If any scoring symbol appears, the display-only boundary was crossed — stop and re-scope.

- [ ] **Step 4: Real-data sanity print (evidence, not just green tests)**

Reconfigure stdout to UTF-8 first (Windows note), then run against the real files:

```bash
.venv/Scripts/python - <<'PY'
import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from gpu_agent import pricefeed as pf
as_of = "2026-07-08"
print("== representative headline $/GPU-hr (median of provider medians) ==")
for model, price in pf.headline_prices(as_of).items():
    print(f"  {model:<6} ${price}")
print("\n== per-provider points (headline models) ==")
for p in pf.load_points(as_of):
    if p.gpu_class == "gpu" and p.model in pf.HEADLINE_MODELS:
        print(f"  {p.provider:<9} {p.model:<6} ${p.usd_per_gpu_hour:<9} region={p.region:<28} date={p.price_date} src={p.instance}")
print("\n== custom silicon (Trainium; TPU absent from data) ==")
for p in pf.custom_silicon_series(as_of):
    print(f"  {p.provider:<9} {p.model:<10} ${p.usd_per_gpu_hour:<9} date={p.price_date} src={p.instance}")
print("\n== deltas vs 1d / 7d / 30d ==")
for d in (1, 7, 30):
    lb = pf.lookback_label(as_of, d)
    print(f"  since {lb} (-{d}d):", pf.price_delta(as_of, lb))
PY
```

**Expected shape (from the 2026-07-08 inspection — confirms the mapping):**
- AWS: H100 ≈ $6.88, H200 ≈ $7.91, B200 ≈ $14.24, B300 ≈ $17.80 (US East N. Virginia, ÷8).
- GCP (Americas): H100 ≈ $9.80–10.34, H200 ≈ $9.31, B200 ≈ $16.11.
- Oracle: H100 $10.00, H200 $10.00, B200 $14.00, B300 $15.00.
- CoreWeave: H100 ≈ $6.16, H200 ≈ $6.31, B200 ≈ $8.60 — but with `price_date` ≈ `260310` (stale), so it drops from the default-window headline median while still listing.
- Custom silicon: Trainium1 ≈ $1.34/chip-hr (trn1.32xlarge), Trainium1 ≈ $1.55 (trn1n), Trainium2 present only if the Ohio on_demand cell resolves (else absent — stale after 250619). No TPU.

If any model maps to an implausible value (e.g. an H100 at sub-$2 would mean a per-instance price wasn't divided, or a Trainium mislabeled as a GPU), fix the `AWS_INSTANCE_MAP`/`_match_model` entry and re-run — do not paper over it in the aggregate.

- [ ] **Step 5: Commit (if Step 4 surfaced any table fix; otherwise nothing to commit)**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test(F78-5): real-data sanity for pricefeed mapping; suite + eval pin green; display-only verified

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-review

- **Spec coverage (§5.7 / D9):** $/GPU-hr normalization (Task 2 AWS ÷count; CoreWeave ÷count; GCP/Oracle already per-GPU) ✅; on-demand term ✅; USA region (AWS `US East (N. Virginia)` + fallbacks; GCP `Americas`; Oracle single region; CoreWeave relaxed US default) ✅; instance-family → GPU-model map **derived from the data and pinned in a tested table** (`AWS_INSTANCE_MAP`, `GCP_ONDEMAND_AMERICAS`, `_match_model`) ✅; `asOf`-driven column/date selection with nearest-at/before (Task 1, exercised in every adapter) ✅; current headline price + 1/7/30-day deltas (`headline_prices`, `price_delta`, `lookback_label`, Task 6) ✅; custom-silicon as a separate labeled series (`custom_silicon_series`, Task 6) ✅.
- **Display-only (F8):** verified by grep in Task 7 Step 3; `pricefeed.py` imports nothing from scoring/schema/judgment; a sibling to `price_track.py`, never blended into DMI/SMI ✅.
- **Determinism, never wall-clock:** all date selection flows through `asof.period_end`/`days_between`; `datetime` used only for `timedelta`/`strptime`, never `.now()`; determinism pinned by `test_determinism_same_asof_same_bytes` ✅.
- **Frozen core / eval pin:** untouched / pinned green (Task 7 Steps 1–2) ✅.
- **Fixtures:** every unit test uses small inline temp CSVs mirroring the real headers; the 20 MB real files are touched only by the one-off sanity print (Task 7 Step 4), never by pytest ✅.
- **Placeholders:** none — every step ships real code and real fixture rows; median literals are exact and must be recomputed (not range-weakened) if a fixture changes.
- **Known data gaps / open questions (documented, not silently dropped):**
  1. **No TPU / custom silicon in the GCP file** — the entire GCP file is H100/H200/B200 Nvidia. The custom-silicon series is **Trainium-only** (AWS). The spec assumed "Trainium / TPU"; TPU simply isn't in the scrape data. Confirm whether a TPU feed is expected to be added later; today it cannot be surfaced.
  2. **AWS GB200 ultraservers** (`u-p6e-gb200x36/x72`) have **no on_demand US row** (only `reserved` in a Dallas Local Zone) → excluded from the headline set. GB200 headline price therefore comes only from Oracle (`BM.GPU.GB200.4`) / CoreWeave (if/when priced), which are outside the four HEADLINE_MODELS today. Decide whether to add `GB200` to `HEADLINE_MODELS` (Oracle-sourced) in Stage 6.
  3. **CoreWeave feed staleness** — its `Instance Price` goes blank after ~`260310` and its `Region` column doesn't align with priced rows. Handled best-effort (region relaxed, nearest priced date, staleness filter in the headline median), but CoreWeave will read as a lagging cross-check, not a live quote, until the upstream scrape is fixed.
  4. **AWS GPU counts are a pinned table, not in the CSV** — the p-family `.48xlarge` = 8 and Trainium counts (16 / 1) are asserted from instance specs and sanity-checked in Task 7. If AWS ships a new family, the map must be extended (an unmapped instance is silently skipped by design).
  5. **AMD GPUs** (Oracle MI300X/MI355X) are captured as `vendor="amd", gpu_class="gpu"` but are **not** in `HEADLINE_MODELS`; they are available via `load_points` for a competitive cross-read (§5.6 Optional) if Stage 6 wants them.
</content>
</invoke>
