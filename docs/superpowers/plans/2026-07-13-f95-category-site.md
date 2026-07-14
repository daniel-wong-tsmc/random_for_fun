# F95 Category Page (static site) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the F95 category page as a committed multi-page static site (`site/`) served by
Cloudflare Pages with no build step — E2 word tiles + a dynamic featured metric at the top, a
"why it reads this way" block at the bottom, and a full drill-down trail from every KPI to the
evidence.

**Architecture:** Pure-renderer extension of `gpu_agent/dashboard/` (spec S6). Four new modules:
`featured.py` (metric library + deterministic selector), `contributions.py` (per-indicator
score breakdown mirroring `scoring.py`), `site_model.py` (assembles one page model from stored
artifacts), `site_render.py` (HTML for the category page + drill-down pages), orchestrated by
`site_build.py` and a new append-only `site` CLI verb. No LLM calls, no new stored data except
the `registry/featured-metrics.json` library and the emitted `site/` folder.

**Tech Stack:** Python 3 (repo venv), stdlib only (json, pathlib, dataclasses, html), pydantic
models already in `gpu_agent/`, pytest. No JS framework — only `<details>` tags for
expand/collapse.

**Spec:** `docs/superpowers/specs/2026-07-13-f95-market-site-design.md` (decisions S1–S8).
Layer/market tiers (spec §6) are CONTRACT-ONLY — nothing in this plan builds them.

## Global Constraints

- **Lane mechanics:** work in worktree `.worktrees/f95-site`, branch `f95-market-site`, created
  via the superpowers:using-git-worktrees skill. Python is `../../.venv/Scripts/python` from the
  worktree root (one shared root venv — NEVER create a per-worktree venv). Suite must be green
  at every commit (`../../.venv/Scripts/python -m pytest -q`, expect 5–6 skips).
- **Frozen core untouched:** do not edit `scoring.py`, `gate.py`, `sufficiency.py`,
  `registry/indicators.json`, `registry/acronyms.json`, any prompt file, or anything under
  `store/`. `tests/test_evals_baseline_pin.py` (F6 pin) must stay GREEN — this is renderer-only
  work; `registry/featured-metrics.json` is a NEW file never embedded in any emitted prompt.
- **`cli.py` is append-only** (same pattern as F65/F79): add the `site` parser + dispatch
  lines; touch nothing else in the file.
- **No wall-clock in site output:** every date shown comes from `asOf`. `datetime.now` is
  FORBIDDEN in the four new modules; built pages must be byte-identical across two builds
  (pinned by test in Task 7).
- **Exec-plain rule (spec §3):** all category-page text above the appendix-links block passes
  `gpu_agent.reader.lint_acronyms` (returns `[]`); prose strings from findings pass through the
  dashboard glossary `term_swap` first.
- **Degrade honestly, never error (spec §8):** no prior run → no "(was …)"; price data absent →
  selector falls down the library; empty library → featured tile omitted (3 tiles);
  implication artifact absent → FOR TSMC section omitted; older scorecards missing fields →
  existing `.get(...)` guards.
- **`site/` is NOT gitignored** (root `.gitignore` only ignores `store/*` with whitelists,
  `work/`, `.worktrees/` — verified 2026-07-13). SPEC CORRECTION: spec §7.2's "gitignore
  whitelist" step is unnecessary; skip it. Task 7 verifies with `git check-ignore`.
- **Commit messages** end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and are
  written via bash heredoc (never double quotes inside PowerShell `git commit -m`).
- **Console prints:** ASCII-safe (cp1252 console) — no arrows/dots in `print()` strings.
  Unicode in FILE content (HTML/JSON) is fine (written as UTF-8).

## File Structure

```
registry/featured-metrics.json          NEW  metric library (data)
gpu_agent/dashboard/featured.py         NEW  library loader, MetricReading, selector, adapters
gpu_agent/dashboard/contributions.py    NEW  per-indicator contribution rows (+ parity w/ scoring)
gpu_agent/dashboard/site_model.py       NEW  build_site_model() — the one page model
gpu_agent/dashboard/site_render.py      NEW  render_category_page/render_how_*/render_appendix
gpu_agent/dashboard/site_build.py       NEW  build_site() — writes the site/ folder
gpu_agent/dashboard/build.py            MODIFY (additive: alert raw+triggers in model)
gpu_agent/cli.py                        MODIFY (append `site` verb)
.claude/skills/run-cycle/SKILL.md       MODIFY (step-7 site rebuild prose)
docs/cloudflare-pages.md                NEW  operator doc + launch gates
site/                                   NEW  committed build output
tests/dashboard/test_featured.py        NEW
tests/dashboard/test_contributions.py   NEW
tests/dashboard/test_site_model.py      NEW
tests/dashboard/test_site_render.py     NEW
tests/dashboard/test_site_build.py      NEW
```

Existing fixtures reused throughout: `tests/dashboard/fixtures/` (4 daily scorecards
2026-07-02..06, `report-2026-07-06.txt`, `plain-2026-07-06.json`). `FIX =
"tests/dashboard/fixtures"` is passed as `store_dir` exactly as `test_build_e2e.py` does.

---

### Task 1: Featured-metric library + pure selector

**Files:**
- Create: `registry/featured-metrics.json`
- Create: `gpu_agent/dashboard/featured.py`
- Test: `tests/dashboard/test_featured.py`

**Interfaces:**
- Consumes: nothing (pure).
- Produces: `MetricReading` dataclass (fields below), `Selection` dataclass
  (`reading: MetricReading, reason_code: str, reason_text: str`),
  `load_library(path="registry/featured-metrics.json") -> list[dict]`,
  `select_featured(readings: list[MetricReading], triggers: list[str]) -> Selection | None`,
  `normalized_change(reading) -> float | None`. Task 2 adds adapters to this same module;
  Tasks 4–6 consume `Selection`.

- [ ] **Step 1: Write the library JSON**

`registry/featured-metrics.json` (spec §4 v1 entries — data, retunable without code change):

```json
{
  "version": 1,
  "metrics": [
    {
      "id": "gpu-rent-h100",
      "label": "H100 rental price",
      "plainLabel": "GPU rent (H100)",
      "unit": "$/GPU-hr",
      "source": {"kind": "pricefeed", "model": "H100"},
      "howToRead": "The going hourly rate to rent one H100 GPU from a big cloud. Falling rent means supply is catching up with demand.",
      "staticPriority": 1,
      "scale": 0.5,
      "alertRuleTags": [],
      "honestyNote": null
    },
    {
      "id": "gap-score",
      "label": "Demand-vs-supply gap score",
      "plainLabel": "Demand-vs-supply gap",
      "unit": "score",
      "source": {"kind": "index", "field": "sdgi"},
      "howToRead": "Above zero: demand is outrunning supply. Below zero: supply is catching up.",
      "staticPriority": 2,
      "scale": 0.5,
      "alertRuleTags": ["gap-band-changed"],
      "honestyNote": "Early signal - about five weeks of history so far."
    },
    {
      "id": "demand-momentum",
      "label": "Demand momentum score",
      "plainLabel": "Demand momentum",
      "unit": "score",
      "source": {"kind": "index", "field": "dmi"},
      "howToRead": "Is buyer demand speeding up or slowing down, from this cycle's evidence.",
      "staticPriority": 3,
      "scale": 0.5,
      "alertRuleTags": ["demand-reversal"],
      "honestyNote": "Early signal - about five weeks of history so far."
    },
    {
      "id": "supply-momentum",
      "label": "Supply momentum score",
      "plainLabel": "Supply momentum",
      "unit": "score",
      "source": {"kind": "index", "field": "smi"},
      "howToRead": "Is available supply expanding or tightening, from this cycle's evidence.",
      "staticPriority": 4,
      "scale": 0.5,
      "alertRuleTags": [],
      "honestyNote": "Early signal - about five weeks of history so far."
    }
  ]
}
```

- [ ] **Step 2: Write the failing tests**

`tests/dashboard/test_featured.py`:

```python
from gpu_agent.dashboard.featured import (
    MetricReading, Selection, load_library, normalized_change, select_featured,
)


def _r(mid, value, prior, priority, tags=(), scale=0.5):
    return MetricReading(
        metric_id=mid, label=mid, plain_label=mid, unit="score",
        value=value, prior=prior, scale=scale, static_priority=priority,
        alert_rule_tags=tuple(tags), how_to_read="how", honesty_note=None,
        display=f"{value:+.2f}")


def test_library_loads_four_entries_with_required_keys():
    lib = load_library()
    assert len(lib) == 4
    for e in lib:
        for k in ("id", "label", "plainLabel", "unit", "source", "howToRead",
                  "staticPriority", "scale", "alertRuleTags"):
            assert k in e, f"{e.get('id')} missing {k}"


def test_rule_tag_hit_beats_bigger_move():
    quiet_tagged = _r("gap", 0.10, 0.09, priority=2, tags=["gap-band-changed"])
    big_mover = _r("price", 3.00, 1.00, priority=1)
    sel = select_featured([big_mover, quiet_tagged], triggers=["gap-band-changed"])
    assert sel.reading.metric_id == "gap" and sel.reason_code == "alert-rule"


def test_two_tagged_hits_tie_break_by_priority():
    a = _r("a", 1.0, 1.0, priority=3, tags=["gap-band-changed"])
    b = _r("b", 1.0, 1.0, priority=2, tags=["high-call-moved"])
    sel = select_featured([a, b], triggers=["gap-band-changed", "high-call-moved"])
    assert sel.reading.metric_id == "b"


def test_biggest_normalized_move_wins_scale_matters():
    # raw move 0.30/scale 0.5 = 0.6  beats  raw move 1.00/scale 2.0 = 0.5
    small_scale = _r("idx", 0.40, 0.10, priority=4, scale=0.5)
    big_scale = _r("price", 3.00, 2.00, priority=1, scale=2.0)
    sel = select_featured([big_scale, small_scale], triggers=[])
    assert sel.reading.metric_id == "idx" and sel.reason_code == "biggest-move"


def test_move_tie_breaks_by_priority():
    a = _r("a", 0.30, 0.10, priority=3)
    b = _r("b", 0.30, 0.10, priority=2)
    assert select_featured([a, b], triggers=[]).reading.metric_id == "b"


def test_no_priors_falls_back_to_priority():
    a = _r("a", 0.3, None, priority=2)
    b = _r("b", 0.4, None, priority=1)
    sel = select_featured([a, b], triggers=[])
    assert sel.reading.metric_id == "b" and sel.reason_code == "priority"


def test_zero_moves_fall_back_to_priority():
    a = _r("a", 0.3, 0.3, priority=1)
    sel = select_featured([a], triggers=[])
    assert sel.reason_code == "priority"


def test_unknown_triggers_are_ignored_and_empty_readings_give_none():
    a = _r("a", 0.3, None, priority=1, tags=["gap-band-changed"])
    assert select_featured([a], triggers=["no-such-rule"]).reason_code == "priority"
    assert select_featured([], triggers=["gap-band-changed"]) is None


def test_normalized_change():
    assert normalized_change(_r("a", 0.40, 0.10, 1, scale=0.5)) == 0.6
    assert normalized_change(_r("a", 0.40, None, 1)) is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_featured.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.dashboard.featured'`

- [ ] **Step 4: Write the implementation**

`gpu_agent/dashboard/featured.py`:

```python
"""F95 featured metric — library loader + deterministic selector (spec §4).

Pure projection: no LLM, no wall-clock, replayable. The library is DATA
(registry/featured-metrics.json); selection is first-match-wins:
(1) alert-rule tag hit -> (2) biggest normalized move -> (3) static priority.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

FEATURED_REGISTRY_PATH = "registry/featured-metrics.json"


@dataclass(frozen=True)
class MetricReading:
    metric_id: str
    label: str
    plain_label: str
    unit: str
    value: float
    prior: float | None          # None = no prior cycle value available
    scale: float                 # library denominator: a move this big is headline-worthy
    static_priority: int         # lower = shown first on fallback
    alert_rule_tags: tuple
    how_to_read: str
    honesty_note: str | None
    display: str                 # preformatted value, e.g. "$2.31/GPU-hr" or "+0.76"


@dataclass(frozen=True)
class Selection:
    reading: MetricReading
    reason_code: str             # "alert-rule" | "biggest-move" | "priority"
    reason_text: str             # plain sentence rendered on the page (spec §4)


def load_library(path: str = FEATURED_REGISTRY_PATH) -> list[dict]:
    with open(Path(path), encoding="utf-8") as fh:
        return json.load(fh)["metrics"]


def normalized_change(reading: MetricReading) -> float | None:
    if reading.prior is None:
        return None
    return abs(reading.value - reading.prior) / reading.scale


def select_featured(readings: list[MetricReading], triggers: list[str]) -> Selection | None:
    if not readings:
        return None
    trig = set(triggers or [])
    tagged = [r for r in readings if set(r.alert_rule_tags) & trig]
    if tagged:
        r = min(tagged, key=lambda r: r.static_priority)
        return Selection(r, "alert-rule",
                         "Shown because it tracks what set off today's alert.")
    moved = [(normalized_change(r), r) for r in readings]
    moved = [(c, r) for c, r in moved if c is not None and c > 0]
    if moved:
        _, r = max(moved, key=lambda cr: (cr[0], -cr[1].static_priority))
        return Selection(r, "biggest-move",
                         "Shown because it moved the most since the last run.")
    r = min(readings, key=lambda r: r.static_priority)
    return Selection(r, "priority",
                     "Shown as the standing headline metric; nothing moved more.")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_featured.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun/.worktrees/f95-site
git add registry/featured-metrics.json gpu_agent/dashboard/featured.py tests/dashboard/test_featured.py
git commit -m "$(cat <<'EOF'
feat(f95): featured-metric library + deterministic selector

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Metric reading adapters (price + index) with honest degradation

**Files:**
- Modify: `gpu_agent/dashboard/featured.py` (append)
- Test: `tests/dashboard/test_featured.py` (append)

**Interfaces:**
- Consumes: Task 1's `MetricReading`; dashboard scorecard records (dicts from
  `gpu_agent.dashboard.scorecards.load_scorecards` with keys `dmi`,`smi`,`sdgi`);
  `gpu_agent.pricefeed.headline_prices(as_of) -> dict[str, float]` and
  `gpu_agent.pricefeed.lookback_label(as_of, days) -> str`.
- Produces: `assemble_readings(library: list[dict], latest: dict, prev: dict | None,
  as_of: str, price_fn=None) -> list[MetricReading]` (Task 4 consumes). `price_fn` is
  injectable for tests; `None` means the real price feed with failure → `{}`.

- [ ] **Step 1: Write the failing tests** (append to `tests/dashboard/test_featured.py`)

```python
from gpu_agent.dashboard.featured import assemble_readings, load_library

_LATEST = {"dmi": 0.39, "smi": 0.42, "sdgi": 0.76}
_PREV = {"dmi": 0.30, "smi": 0.40, "sdgi": 0.10}


def test_assemble_full_house_with_stub_price():
    lib = load_library()
    prices = {"2026-07-13": {"H100": 2.31}, "2026-06-13": {"H100": 2.51}}
    rs = assemble_readings(lib, _LATEST, _PREV, "2026-07-13",
                           price_fn=lambda d: prices.get(d, {}))
    by_id = {r.metric_id: r for r in rs}
    assert set(by_id) == {"gpu-rent-h100", "gap-score", "demand-momentum", "supply-momentum"}
    p = by_id["gpu-rent-h100"]
    assert p.value == 2.31 and p.prior == 2.51 and p.display == "$2.31/GPU-hr"
    g = by_id["gap-score"]
    assert g.value == 0.76 and g.prior == 0.10 and g.display == "+0.76"


def test_assemble_price_absent_skips_entry():
    rs = assemble_readings(load_library(), _LATEST, _PREV, "2026-07-13",
                           price_fn=lambda d: {})
    assert "gpu-rent-h100" not in {r.metric_id for r in rs}
    assert len(rs) == 3


def test_assemble_no_prev_record_gives_none_priors():
    rs = assemble_readings(load_library(), _LATEST, None, "2026-07-13",
                           price_fn=lambda d: {})
    assert all(r.prior is None for r in rs)


def test_assemble_unknown_source_kind_is_skipped():
    lib = [{"id": "x", "label": "x", "plainLabel": "x", "unit": "u",
            "source": {"kind": "someday"}, "howToRead": "h", "staticPriority": 9,
            "scale": 1.0, "alertRuleTags": [], "honestyNote": None}]
    assert assemble_readings(lib, _LATEST, _PREV, "2026-07-13", price_fn=lambda d: {}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_featured.py -v -k assemble`
Expected: FAIL — `ImportError: cannot import name 'assemble_readings'`

- [ ] **Step 3: Write the implementation** (append to `gpu_agent/dashboard/featured.py`)

```python
def _default_price_fn(as_of: str) -> dict:
    """Real price feed; scrape_data is gitignored so absence is normal — degrade to {}."""
    from gpu_agent import pricefeed
    try:
        return pricefeed.headline_prices(as_of)
    except (FileNotFoundError, OSError, ValueError):
        return {}


def _reading(entry: dict, value: float, prior: float | None, display: str) -> MetricReading:
    return MetricReading(
        metric_id=entry["id"], label=entry["label"], plain_label=entry["plainLabel"],
        unit=entry["unit"], value=value, prior=prior, scale=float(entry["scale"]),
        static_priority=int(entry["staticPriority"]),
        alert_rule_tags=tuple(entry.get("alertRuleTags") or []),
        how_to_read=entry["howToRead"], honesty_note=entry.get("honestyNote"),
        display=display)


def assemble_readings(library, latest, prev, as_of, price_fn=None):
    """One MetricReading per library entry whose source has data; honest skips otherwise."""
    from gpu_agent.pricefeed import lookback_label
    price_fn = price_fn or _default_price_fn
    cur_prices = None   # fetched lazily, once
    out = []
    for entry in library:
        src = entry.get("source") or {}
        kind = src.get("kind")
        if kind == "index":
            field = src.get("field")
            if field not in ("dmi", "smi", "sdgi"):
                continue
            value = float(latest[field])
            prior = float(prev[field]) if prev else None
            out.append(_reading(entry, value, prior, f"{value:+.2f}"))
        elif kind == "pricefeed":
            if cur_prices is None:
                cur_prices = price_fn(as_of)
            model = src.get("model")
            if not cur_prices or model not in cur_prices:
                continue
            value = float(cur_prices[model])
            prior_prices = price_fn(lookback_label(as_of, 30))
            prior = float(prior_prices[model]) if model in (prior_prices or {}) else None
            out.append(_reading(entry, value, prior, f"${value:.2f}/GPU-hr"))
        # unknown kinds: forward-compatible skip (spec §8)
    return out
```

- [ ] **Step 4: Run the full featured test file + whole suite**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_featured.py -v`
Expected: all PASS
Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green (5–6 skips), F6 pin green.

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/dashboard/featured.py tests/dashboard/test_featured.py
git commit -m "$(cat <<'EOF'
feat(f95): price + index reading adapters with honest degradation

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Contribution rows (drill-down arithmetic, parity-pinned to scoring.py)

**Files:**
- Create: `gpu_agent/dashboard/contributions.py`
- Test: `tests/dashboard/test_contributions.py`

**Interfaces:**
- Consumes: `gpu_agent.report.load_scorecard(path) -> Scorecard` (pydantic; `sc.findings` are
  `Finding` objects with `.entity/.indicatorId/.capturedAt/.observedAt/.magnitude/
  .polarityDemand/.polaritySupply/.statement/.id/.evidence[]` where each Evidence has
  `.source/.url/.date/.tier`); `IndicatorRegistry.load(REGISTRY_PATH)` with
  `.resolve(indicator_id, category_id) -> spec` (`.scoring`, `.side`, `.weight`, `.label`).
- Produces: `contribution_rows(findings, registry, category_id) -> list[dict]`, rows sorted by
  total absolute contribution desc then (indicator_id, entity). Row keys: `entity`,
  `indicator_id`, `label`, `weight`, `magnitude`, `polarity_demand`, `polarity_supply`,
  `demand_contribution`, `supply_contribution`, `finding_id`, `statement`, `observed_at`,
  `evidence` (list of `{source, url, date, tier}`). Tasks 4/6 consume.

**CRITICAL:** `scoring.py` is frozen core — read it, never edit it. This module MIRRORS its
loop (group by `(entity, indicatorId)`, skip non-scoring and price/structural sides, pick the
latest finding by `(capturedAt, observedAt, magnitude)`, contribution = weight × polarity ×
magnitude / 3). The parity test below is the guard that the mirror never drifts.

- [ ] **Step 1: Write the failing tests**

`tests/dashboard/test_contributions.py`:

```python
from pathlib import Path

from gpu_agent.config import REGISTRY_PATH
from gpu_agent.dashboard.contributions import contribution_rows
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.report import load_scorecard
from gpu_agent.scoring import dmi_smi_contribution

FIX = Path("tests/dashboard/fixtures")
CAT = "chips.merchant-gpu"


def _sc():
    return load_scorecard(FIX / "2026-07-06-v1.json")


def _reg():
    return IndicatorRegistry.load(REGISTRY_PATH)


def test_row_sums_match_frozen_scoring_exactly():
    sc, reg = _sc(), _reg()
    rows = contribution_rows(sc.findings, reg, CAT)
    dmi, smi = dmi_smi_contribution(sc.findings, reg, CAT)
    assert abs(sum(r["demand_contribution"] for r in rows) - dmi) < 1e-12
    assert abs(sum(r["supply_contribution"] for r in rows) - smi) < 1e-12


def test_rows_have_the_drilldown_fields_and_are_sorted():
    rows = contribution_rows(_sc().findings, _reg(), CAT)
    assert rows, "fixture scorecard must produce scoring rows"
    for r in rows:
        for k in ("entity", "indicator_id", "label", "weight", "magnitude",
                  "polarity_demand", "polarity_supply", "demand_contribution",
                  "supply_contribution", "finding_id", "statement", "observed_at",
                  "evidence"):
            assert k in r
        for ev in r["evidence"]:
            assert set(ev) == {"source", "url", "date", "tier"}
    totals = [abs(r["demand_contribution"]) + abs(r["supply_contribution"]) for r in rows]
    assert totals == sorted(totals, reverse=True)


def test_deterministic_across_two_calls():
    sc, reg = _sc(), _reg()
    assert contribution_rows(sc.findings, reg, CAT) == contribution_rows(sc.findings, reg, CAT)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_contributions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.dashboard.contributions'`

- [ ] **Step 3: Write the implementation**

`gpu_agent/dashboard/contributions.py`:

```python
"""F95 drill-down arithmetic — mirrors gpu_agent/scoring.py (FROZEN CORE, never edited here).

Same grouping, same latest-finding rule, same weight x polarity x magnitude / 3. The parity
test (tests/dashboard/test_contributions.py) pins the sums to dmi_smi_contribution so this
mirror can never silently drift from the real scoring."""
from __future__ import annotations


def _latest(findings):
    return max(findings, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))


def contribution_rows(findings, registry, category_id) -> list[dict]:
    by_key: dict[tuple, list] = {}
    for f in findings:
        spec = registry.resolve(f.indicatorId, category_id)
        if not spec.scoring or spec.side in ("price", "structural"):
            continue
        by_key.setdefault((f.entity, f.indicatorId), []).append(f)
    rows = []
    for (entity, ind_id), fs in by_key.items():
        spec = registry.resolve(ind_id, category_id)
        chosen = _latest(fs)
        dc = spec.weight * chosen.polarityDemand * chosen.magnitude / 3
        sc_ = spec.weight * chosen.polaritySupply * chosen.magnitude / 3
        rows.append({
            "entity": entity,
            "indicator_id": ind_id,
            "label": getattr(spec, "label", ind_id) or ind_id,
            "weight": spec.weight,
            "magnitude": chosen.magnitude,
            "polarity_demand": chosen.polarityDemand,
            "polarity_supply": chosen.polaritySupply,
            "demand_contribution": dc,
            "supply_contribution": sc_,
            "finding_id": chosen.id,
            "statement": chosen.statement,
            "observed_at": chosen.observedAt,
            "evidence": [{"source": e.source, "url": e.url, "date": e.date, "tier": e.tier}
                         for e in chosen.evidence],
        })
    rows.sort(key=lambda r: (-(abs(r["demand_contribution"]) + abs(r["supply_contribution"])),
                             r["indicator_id"], r["entity"]))
    return rows
```

NOTE for the implementer: if `spec.label` does not exist on the registry spec object, run
`../../.venv/Scripts/python -c "from gpu_agent.registry.indicators import IndicatorRegistry; from gpu_agent.config import REGISTRY_PATH; s=IndicatorRegistry.load(REGISTRY_PATH).resolve('market-share-pct','chips.merchant-gpu'); print(type(s), dir(s))"`
and use the real attribute name; the `getattr` fallback keeps the row honest either way.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_contributions.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/dashboard/contributions.py tests/dashboard/test_contributions.py
git commit -m "$(cat <<'EOF'
feat(f95): contribution rows for the KPI drill-down, parity-pinned to scoring

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Site page model (assembly + WHY block + implication + degradations)

**Files:**
- Modify: `gpu_agent/dashboard/build.py:145` (one additive line in the `model` dict)
- Create: `gpu_agent/dashboard/site_model.py`
- Test: `tests/dashboard/test_site_model.py`

**Interfaces:**
- Consumes: `build.build_model(category_id, store_dir, work_dir, plain_path, generated_at)
  -> (model, summary)` — model keys used: `tiles` (list of 3 dicts `label/band/value/delta/
  spark`), `alert` (`color/prior` + the new `raw/triggers`), `what_changed`, `calls`,
  `headline` (`rating/direction/limiting_factor/state_of_market`), `demand_supply`
  (`dmi/smi/sdgi/sdgi_direction`), `trend`, `runs`, `latest_date`, `top_signals`.
  Also: Task 2 `assemble_readings`/`load_library`, Task 1 `select_featured`, Task 3
  `contribution_rows`, `gpu_agent.report.load_scorecard` + `_VERSION_RE` +
  `evidence_vintage(sc) -> (oldest, newest, share)`, `gpu_agent.dashboard.glossary.
  load_glossary/term_swap`.
- Produces: `build_site_model(category_id, store_dir, work_dir, plain_path, price_fn=None)
  -> dict` — everything in `model` PLUS:
  `as_of: str`; `featured: dict | None`
  (`{metric_id, plain_label, display, unit, delta_phrase, reason_code, reason_text,
  how_to_read, honesty_note, value, prior}`); `contributions: list[dict]` (Task 3 rows,
  statements already glossary-swapped); `implication: dict | None` (`{"lines": [str, ...]}`);
  `why: list[dict]` (`{"topic": str, "text": str}` for topics
  `alert, demand, supply, gap, featured, trust` — featured omitted when featured is None).
  Tasks 5–7 consume this dict.

- [ ] **Step 1: additive alert detail in `build.py`**

In `gpu_agent/dashboard/build.py`, change the one line

```python
        "alert": {"color": alert.color, "prior": alert.priorColor},
```

to

```python
        "alert": {"color": alert.color, "prior": alert.priorColor,
                  "raw": alert.rawColor, "triggers": list(alert.triggers)},
```

(Additive keys only — `render.py` ignores unknown keys; existing dashboard tests must stay
green, verified in Step 5.)

- [ ] **Step 2: Write the failing tests**

`tests/dashboard/test_site_model.py`:

```python
import json
import shutil
from pathlib import Path

from gpu_agent.dashboard.site_model import build_site_model, read_implication

FIX = "tests/dashboard/fixtures"
CAT = "chips.merchant-gpu"


def _model(price_fn=lambda d: {}):
    return build_site_model(CAT, FIX, work_dir="work-nonexistent",
                            plain_path=f"{FIX}/plain-2026-07-06.json", price_fn=price_fn)


def test_model_has_the_f95_extras():
    m = _model()
    assert m["as_of"] == m["latest_date"]
    assert m["alert"].keys() >= {"color", "prior", "raw", "triggers"}
    assert m["contributions"], "fixture must yield contribution rows"
    topics = [w["topic"] for w in m["why"]]
    assert topics[:1] == ["alert"] and {"demand", "supply", "gap", "trust"} <= set(topics)
    for w in m["why"]:
        assert w["text"].strip()


def test_featured_with_stub_price_and_reason_present():
    prices = {"H100": 2.31}
    m = _model(price_fn=lambda d: prices)
    f = m["featured"]
    assert f is not None and f["metric_id"] in {"gpu-rent-h100", "gap-score",
                                                "demand-momentum", "supply-momentum"}
    assert f["reason_text"] and f["reason_code"] in {"alert-rule", "biggest-move", "priority"}
    assert any(w["topic"] == "featured" for w in m["why"])


def test_no_price_data_still_selects_an_index_metric():
    f = _model()["featured"]
    assert f is not None and f["metric_id"] != "gpu-rent-h100"


def test_gap_why_shows_the_equation():
    m = _model()
    gap = next(w for w in m["why"] if w["topic"] == "gap")
    ds = m["demand_supply"]
    assert f'{ds["dmi"]:+.2f}' in gap["text"] and f'{ds["sdgi"]:+.2f}' in gap["text"]


def test_implication_read_defensively(tmp_path):
    root = tmp_path / "store"
    (root / "implications" / CAT).mkdir(parents=True)
    art = {"asOf": "2026-07-06", "lines": [
        {"text": "Watch CoWoS allocation notes in earnings calls.",
         "watchItem": "cowosSoicAllocation", "dimensions": ["bottleneck"]},
        {"watchItem": "waferStartsByNode"},
        "A bare string line survives too."]}
    (root / "implications" / CAT / "2026-07-06.json").write_text(
        json.dumps(art), encoding="utf-8")
    got = read_implication(root, CAT, "2026-07-06")
    assert got == {"lines": ["Watch CoWoS allocation notes in earnings calls.",
                             "waferStartsByNode",
                             "A bare string line survives too."]}
    assert read_implication(root, CAT, "2026-07-05") is None
    assert read_implication(tmp_path / "nowhere", CAT, "2026-07-06") is None


def test_single_run_store_degrades_no_prior(tmp_path):
    cat_dir = tmp_path / "store" / CAT
    cat_dir.mkdir(parents=True)
    shutil.copy(Path(FIX) / "2026-07-06-v1.json", cat_dir / "2026-07-06-v1.json")
    m = build_site_model(CAT, str(cat_dir), work_dir="work-nonexistent",
                         plain_path=None, price_fn=lambda d: {})
    assert m["featured"]["reason_code"] == "priority"
    assert m["alert"]["prior"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_site_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.dashboard.site_model'`

- [ ] **Step 4: Write the implementation**

`gpu_agent/dashboard/site_model.py`:

```python
"""F95 site page model — one dict per category page, assembled from stored artifacts only.

Pure projection: reuses build_model (same change engine as the text brief — parity by
construction), then adds the F95 extras: featured metric, contribution rows, the FOR TSMC
implication artifact (read defensively; F65 may not be merged), and the WHY block."""
from __future__ import annotations

import json
from pathlib import Path

from gpu_agent.config import REGISTRY_PATH
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.report import _VERSION_RE, evidence_vintage, load_scorecard

from .build import build_model
from .contributions import contribution_rows
from .featured import assemble_readings, load_library, select_featured
from .glossary import load_glossary, term_swap
from .scorecards import load_scorecards

# Alert-ladder rule ids -> plain English (unknown ids fall back to id with spaces).
_RULE_PLAIN = {
    "gap-band-changed": "the demand-vs-supply gap band changed within the last week",
    "high-call-moved": "a high-confidence call moved within the last week",
    "constraint-rotated": "the main limiting factor changed within the last week",
    "calls-co-move": "two or more calls moved in the same direction within the last week",
    "high-call-broke": "a high-confidence call broke or was retired within the last week",
    "demand-reversal": "demand worsened while the gap moved toward glut within the last week",
}


def rule_plain(rule_id: str) -> str:
    return _RULE_PLAIN.get(rule_id, rule_id.replace("-", " "))


def read_implication(store_root, category_id: str, as_of: str):
    """F65 artifact, read defensively: {'lines': [str,...]} or None. Never raises."""
    p = Path(store_root) / "implications" / category_id / f"{as_of}.json"
    try:
        art = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    out = []
    for ln in (art.get("lines") or []) if isinstance(art, dict) else []:
        if isinstance(ln, str):
            out.append(ln)
        elif isinstance(ln, dict):
            out.append(ln.get("text") or ln.get("watchItem") or "")
    lines = [l for l in out if l]
    return {"lines": lines} if lines else None


def _band_word(tile_band: str) -> str:
    return tile_band.split()[0].capitalize()


def _delta_phrase(value, prior, unit):
    if prior is None:
        return "no prior run to compare"
    d = value - prior
    word = "up" if d > 0 else ("down" if d < 0 else "flat")
    if unit == "$/GPU-hr":
        return f"{word} ${abs(d):.2f} vs about a month ago"
    return f"{word} {abs(d):.2f} vs the prior run"


def _top_row(rows, side_key):
    live = [r for r in rows if r[side_key] != 0]
    if not live:
        return None
    return max(live, key=lambda r: (abs(r[side_key]), r["indicator_id"]))


def _why(model, featured, rows, sc, g):
    why = []
    a = model["alert"]
    fired = "; ".join(rule_plain(t) for t in a["triggers"]) if a["triggers"] else \
        "no alert rule fired"
    text = f"The light is {a['color'].upper()} because {fired}."
    if a["raw"] != a["color"]:
        text += (f" Today's raw read was {a['raw'].upper()}; the shown color only steps"
                 " down after two calm runs in a row.")
    why.append({"topic": "alert", "text": text})

    for topic, side_key, tile in (("demand", "demand_contribution", model["tiles"][0]),
                                  ("supply", "supply_contribution", model["tiles"][1])):
        top = _top_row(rows, side_key)
        if top is None:
            t = (f"{topic.capitalize()} reads {_band_word(tile['band'])}; no scoring"
                 " findings pulled it this cycle.")
        else:
            pull = "up" if top[side_key] > 0 else "down"
            t = (f"{topic.capitalize()} reads {_band_word(tile['band'])}. Biggest pull"
                 f" {pull}: {top['label']} - {term_swap(top['statement'], g)}")
        why.append({"topic": topic, "text": t})

    ds = model["demand_supply"]
    why.append({"topic": "gap", "text":
                (f"The gap score is demand minus supply: {ds['dmi']:+.2f} minus"
                 f" {ds['smi']:+.2f} = {ds['sdgi']:+.2f}, currently"
                 f" {ds['sdgi_direction'] or 'balanced'}.")})

    if featured is not None:
        t = f"{featured['reason_text']} {featured['how_to_read']}"
        if featured["honesty_note"]:
            t += f" ({featured['honesty_note']})"
        why.append({"topic": "featured", "text": t})

    oldest, newest, _ = evidence_vintage(sc)
    span = f"Evidence spans {oldest} to {newest}." if oldest and newest else \
        "Evidence dates were not recorded this cycle."
    prim = sum(1 for f in model["top_signals"] if f.get("tier") == "primary")
    why.append({"topic": "trust", "text":
                f"{span} {prim} of the {len(model['top_signals'])} ranked signals trace"
                " to a primary source."})
    return why


def build_site_model(category_id, store_dir, work_dir, plain_path, price_fn=None):
    model, _summary = build_model(category_id, store_dir, work_dir, plain_path,
                                  generated_at="")
    g = load_glossary()

    # Same layout detection as build_model (build.py:57-59): store_dir either IS the
    # category dir or is the store root holding <category_id>/.
    store_dir = Path(store_dir)
    if (store_dir / category_id).is_dir():
        store_root, cat_dir = store_dir, store_dir / category_id
    else:
        store_root, cat_dir = store_dir.parent, store_dir
    latest_path = max((p for p in cat_dir.iterdir() if _VERSION_RE.match(p.name)),
                      key=lambda p: (_VERSION_RE.match(p.name).group(1),
                                     int(_VERSION_RE.match(p.name).group(2))))
    sc = load_scorecard(latest_path)

    reg = IndicatorRegistry.load(REGISTRY_PATH)
    rows = contribution_rows(sc.findings, reg, category_id)
    for r in rows:
        r["statement"] = term_swap(r["statement"], g)

    recs = load_scorecards(category_id, str(cat_dir))
    latest, prev = recs[-1], (recs[-2] if len(recs) > 1 else None)
    readings = assemble_readings(load_library(), latest, prev, latest["as_of"],
                                 price_fn=price_fn)
    sel = select_featured(readings, model["alert"]["triggers"])
    featured = None
    if sel is not None:
        r = sel.reading
        featured = {"metric_id": r.metric_id, "plain_label": r.plain_label,
                    "display": r.display, "unit": r.unit,
                    "delta_phrase": _delta_phrase(r.value, r.prior, r.unit),
                    "reason_code": sel.reason_code, "reason_text": sel.reason_text,
                    "how_to_read": r.how_to_read, "honesty_note": r.honesty_note,
                    "value": r.value, "prior": r.prior}

    model.update({
        "as_of": model["latest_date"],
        "category_id": category_id,
        "featured": featured,
        "contributions": rows,
        "implication": read_implication(store_root, category_id, model["latest_date"]),
        "why": _why(model, featured, rows, sc, g),
    })
    return model
```

NOTE for the implementer: `build_model` must be absent-safe for the work dir —
`find_latest_report` is expected to return None for a missing dir (verify; if it raises,
pass an empty `tmp_path` dir as `work_dir` in the tests instead of `"work-nonexistent"`).

- [ ] **Step 5: Run tests + whole suite**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/ -v`
Expected: all PASS (including the pre-existing dashboard tests — the build.py edit is additive)
Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green, F6 pin green.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/dashboard/build.py gpu_agent/dashboard/site_model.py tests/dashboard/test_site_model.py
git commit -m "$(cat <<'EOF'
feat(f95): site page model — featured metric, WHY block, implication read, degradations

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Category page renderer

**Files:**
- Create: `gpu_agent/dashboard/site_render.py`
- Test: `tests/dashboard/test_site_render.py`

**Interfaces:**
- Consumes: Task 4's model dict; `gpu_agent.dashboard.render.esc`;
  `gpu_agent.reader.lint_acronyms(text) -> list`.
- Produces: `SITE_CSS: str`, `page(title: str, body: str) -> str` (full HTML document
  string, linking `style.css` relative), `render_category_page(model) -> str`,
  `render_index_redirect(target_href: str, label: str) -> str`. `HOW_LINKS: dict`
  mapping tile side → href (`{"alert": "how/alert.html", "demand": "how/demand.html",
  "supply": "how/supply.html", "gap": "how/gap.html", "featured": "how/featured.html"}`).
  Task 6 appends the how-page renderers to this module; Task 7 writes the files.

**Page body order (spec §3):** breadcrumb → h1 + as-of → alert line (+how link) → tile row
(3 band tiles + featured tile, each with its how link) → constraint line → WHAT CHANGED →
FOR TSMC (conditional) → THE TOP CALLS (top 5 + one-liners) → WHY IT READS THIS WAY →
appendix links (marker id `appendix-links`). Lint applies to everything ABOVE the marker.

- [ ] **Step 1: Write the failing tests**

`tests/dashboard/test_site_render.py`:

```python
import re

from gpu_agent.dashboard.site_model import build_site_model
from gpu_agent.dashboard.site_render import (
    HOW_LINKS, page, render_category_page, render_index_redirect,
)
from gpu_agent.reader import lint_acronyms

FIX = "tests/dashboard/fixtures"
CAT = "chips.merchant-gpu"


def _model():
    return build_site_model(CAT, FIX, work_dir="work-nonexistent",
                            plain_path=f"{FIX}/plain-2026-07-06.json",
                            price_fn=lambda d: {"H100": 2.31})


def _text_above_appendix(html):
    cut = html.split('id="appendix-links"')[0]
    return re.sub(r"<[^>]+>", " ", cut)


def test_category_page_structure_and_links():
    html = render_category_page(_model())
    assert html.startswith("<!doctype html>")
    for href in HOW_LINKS.values():
        assert f'href="{href}"' in html
    assert 'id="appendix-links"' in html
    assert "Why it reads this way" in html
    assert "MERCHANT GPU" in html
    assert "2026-07-06" in html


def test_featured_tile_renders_value_and_reason_link():
    html = render_category_page(_model())
    assert "$2.31/GPU-hr" in html
    assert 'href="how/featured.html"' in html


def test_no_featured_drops_tile_and_link():
    m = _model()
    m["featured"] = None
    m["why"] = [w for w in m["why"] if w["topic"] != "featured"]
    html = render_category_page(m)
    assert 'href="how/featured.html"' not in html


def test_implication_section_conditional():
    m = _model()
    assert "For TSMC" not in render_category_page(m)
    m["implication"] = {"lines": ["Watch CoWoS allocation notes."]}
    html = render_category_page(m)
    assert "For TSMC" in html and "Watch CoWoS allocation notes." in html


def test_above_fold_text_passes_acronym_lint_and_no_slop():
    html = render_category_page(_model())
    text = _text_above_appendix(html)
    assert lint_acronyms(text) == []
    for slop in ("delve", "leverage", "seamless", "tapestry"):
        assert slop not in text.lower()


def test_render_is_deterministic_and_clockless():
    m = _model()
    assert render_category_page(m) == render_category_page(m)
    import gpu_agent.dashboard.site_render as sr
    import inspect
    src = inspect.getsource(sr)
    assert "datetime.now" not in src and "date.today" not in src


def test_index_redirect_points_at_category():
    html = render_index_redirect("chips.merchant-gpu/index.html", "Merchant GPU")
    assert 'http-equiv="refresh"' in html and "chips.merchant-gpu/index.html" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_site_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.dashboard.site_render'`

- [ ] **Step 3: Write the implementation**

`gpu_agent/dashboard/site_render.py` — complete module (Task 6 appends the how pages):

```python
"""F95 site renderer — static, deterministic, self-contained pages (spec §3/§5).

No wall-clock, no LLM, no external assets beyond the sibling style.css. Only
<details> tags for expand/collapse — no scripting."""
from __future__ import annotations

from .render import esc

HOW_LINKS = {"alert": "how/alert.html", "demand": "how/demand.html",
             "supply": "how/supply.html", "gap": "how/gap.html",
             "featured": "how/featured.html"}

_TILE_SIDES = ("demand", "supply", "gap")

SITE_CSS = """
:root { --ink:#1a1a1a; --muted:#666; --line:#ddd; --green:#2e7d32; --yellow:#f9a825;
        --orange:#ef6c00; --red:#c62828; }
* { box-sizing: border-box; }
body { font: 16px/1.5 system-ui, sans-serif; color: var(--ink); margin: 0 auto;
       max-width: 60rem; padding: 1.5rem; }
a { color: #0b57d0; }
h1 { font-size: 1.4rem; margin: .2rem 0; }
h2 { font-size: 1.1rem; margin-top: 2rem; border-top: 1px solid var(--line);
     padding-top: 1rem; }
.crumb, .asof, .muted { color: var(--muted); font-size: .9rem; }
.alertline { font-size: 1.15rem; margin: 1rem 0 .5rem; }
.dot { display: inline-block; width: .8em; height: .8em; border-radius: 50%;
       vertical-align: baseline; }
.dot.green{background:var(--green)} .dot.yellow{background:var(--yellow)}
.dot.orange{background:var(--orange)} .dot.red{background:var(--red)}
.tiles { display: flex; flex-wrap: wrap; gap: .8rem; margin: 1rem 0; }
.tile { flex: 1 1 12rem; border: 1px solid var(--line); border-radius: .5rem;
        padding: .8rem; }
.tile .k { font-size: .8rem; letter-spacing: .05em; color: var(--muted);
           text-transform: uppercase; }
.tile .v { font-size: 1.25rem; margin: .2rem 0; }
.tile .how { font-size: .85rem; }
table { border-collapse: collapse; width: 100%; }
.scroll { overflow-x: auto; }
th, td { text-align: left; padding: .35rem .5rem; border-bottom: 1px solid var(--line); }
ul { padding-left: 1.2rem; }
details { margin: .3rem 0; }
.callmore { color: var(--muted); }
"""


def page(title: str, body: str) -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"<title>{esc(title)}</title>\n"
            "<link rel=\"stylesheet\" href=\"style.css\">\n"
            f"</head>\n<body>\n{body}\n</body>\n</html>\n")


def render_index_redirect(target_href: str, label: str) -> str:
    body = (f'<meta http-equiv="refresh" content="0; url={esc(target_href)}">\n'
            f'<p>AI market site - continue to <a href="{esc(target_href)}">'
            f"{esc(label)}</a>.</p>")
    return page("AI market", body)


def _dot(color: str) -> str:
    return f'<span class="dot {esc(color)}"></span>'


def _alert_line(alert) -> str:
    was = (f' (was {esc(alert["prior"].upper())})' if alert["prior"]
           else " (first tracked run)")
    return (f'<p class="alertline">{_dot(alert["color"])} '
            f'<strong>{esc(alert["color"].upper())}</strong>{was} '
            f'<a class="how" href="{HOW_LINKS["alert"]}">How was this decided?</a></p>')


def _tiles(model) -> str:
    out = ['<div class="tiles">']
    for side, tile in zip(_TILE_SIDES, model["tiles"]):
        out.append(
            f'<div class="tile"><div class="k">{esc(tile["label"])}</div>'
            f'<div class="v">{esc(tile["band"])}</div>'
            f'<a class="how" href="{HOW_LINKS[side]}">how?</a></div>')
    f = model.get("featured")
    if f is not None:
        out.append(
            f'<div class="tile"><div class="k">Worth watching: {esc(f["plain_label"])}'
            f'</div><div class="v">{esc(f["display"])}</div>'
            f'<div class="muted">{esc(f["delta_phrase"])}</div>'
            f'<a class="how" href="{HOW_LINKS["featured"]}">why this number?</a></div>')
    out.append("</div>")
    return "\n".join(out)


def _what_changed(model) -> str:
    items = "".join(f'<li><strong>{esc(w["phrase"])}:</strong> {esc(w["text"])}</li>'
                    for w in model["what_changed"])
    return f"<h2>What changed</h2>\n<ul>{items or '<li>No change lines this run.</li>'}</ul>"


def _implication(model) -> str:
    imp = model.get("implication")
    if not imp:
        return ""
    items = "".join(f"<li>{esc(l)}</li>" for l in imp["lines"])
    return f"<h2>For TSMC</h2>\n<ul>{items}</ul>"


def _calls(model) -> str:
    calls = model["calls"]
    if not calls:
        return "<h2>The top calls</h2>\n<p class=\"muted\">No tracked calls this run.</p>"
    top, rest = calls[:5], calls[5:]
    blocks = []
    for c in top:
        breaks = (f'<div class="muted">breaks if: {esc(c["breaks_if"])}</div>'
                  if c.get("breaks_if") else "")
        blocks.append(f'<p><strong>{esc(c["title"])}</strong> - {esc(c["plain"])}'
                      f"{breaks}</p>")
    more = ""
    if rest:
        lines = "".join(f'<li class="callmore">{esc(c["title"])} - {esc(c["plain"])}</li>'
                        for c in rest)
        more = f"<ul>{lines}</ul>"
    return f'<h2>The top calls ({len(top)} of {len(calls)})</h2>\n' + "\n".join(blocks) + more


def _why(model) -> str:
    paras = "".join(f'<p><strong>{esc(w["topic"].capitalize())}:</strong> '
                    f'{esc(w["text"])}</p>' for w in model["why"])
    return f"<h2>Why it reads this way</h2>\n{paras}"


def render_category_page(model) -> str:
    title = model["category_label"]
    body = [
        f'<p class="crumb">{esc(title)} &middot; Chips layer &middot; AI market</p>',
        f"<h1>{esc(model['category_id'].rsplit('.', 1)[-1].replace('-', ' ').upper())}</h1>",
        f'<p class="asof">as of {esc(model["as_of"])}</p>',
        _alert_line(model["alert"]),
        _tiles(model),
        f'<p>Main limiting factor: <strong>{esc(model["headline"]["limiting_factor"])}'
        "</strong></p>",
        _what_changed(model),
        _implication(model),
        _calls(model),
        _why(model),
        '<h2 id="appendix-links">Appendix</h2>',
        '<p><a href="appendix.html">Raw scores, every finding with its evidence, and the '
        "run history</a></p>",
    ]
    return page(f"{title} - {model['as_of']}", "\n".join(b for b in body if b))
```

NOTE for the implementer: the call dict keys (`title`, `plain`, `breaks_if`) come from
`build_model`'s calls list — check
`gpu_agent/dashboard/ranking.py::rank_calls` / `report_calls.parse_calls` for the exact key
names (`test_build_e2e.py` shows `plain` and `breaks_if`; the display-name key may be `slug`
or `statement`-derived — adjust `c["title"]` to the real key and keep the tests passing).
Calls may be EMPTY here because `work_dir` has no report in fixtures-only tests — the
"No tracked calls" branch covers it; that is honest degradation, not a bug.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_site_render.py -v`
Expected: all PASS. If `lint_acronyms` flags a term coming from fixture prose, route that
string through `term_swap` in `site_model._why` (the lint is the spec's exec-plain gate —
fix the pipeline, never relax the test).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/dashboard/site_render.py tests/dashboard/test_site_render.py
git commit -m "$(cat <<'EOF'
feat(f95): category page renderer — tiles, WHY block, conditional sections

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Drill-down pages + appendix renderer

**Files:**
- Modify: `gpu_agent/dashboard/site_render.py` (append)
- Test: `tests/dashboard/test_site_render.py` (append)

**Interfaces:**
- Consumes: Task 4's model (`alert.triggers/raw`, `contributions`, `featured`,
  `demand_supply`, `trend`, `runs`, `top_signals`); `site_model.rule_plain`;
  `gpu_agent.bands.BANDS` + `band_word`.
- Produces: `render_how_alert(model) -> str`, `render_how_tile(model, side) -> str` for
  `side in {"demand","supply","gap"}`, `render_how_featured(model) -> str` (call ONLY when
  `model["featured"]` is not None), `render_appendix(model) -> str`. Task 7 writes them to
  `how/*.html` / `appendix.html`. All how-pages live one directory down, so their stylesheet
  link must be `../style.css` — add a `depth` parameter: `page(title, body, depth=0)` and
  emit `("../" * depth) + "style.css"`; update `render_category_page`/`render_index_redirect`
  to keep depth 0 (default keeps Task 5 tests green).

- [ ] **Step 1: Write the failing tests** (append to `tests/dashboard/test_site_render.py`)

```python
from gpu_agent.dashboard.site_render import (
    render_appendix, render_how_alert, render_how_featured, render_how_tile,
)


def test_how_alert_names_the_ladder_and_todays_state():
    m = _model()
    html = render_how_alert(m)
    for word in ("GREEN", "YELLOW", "ORANGE", "RED"):
        assert word in html
    assert m["alert"]["color"].upper() in html
    assert 'href="../style.css"' in html


def test_how_demand_shows_weights_findings_and_evidence_links():
    m = _model()
    html = render_how_tile(m, "demand")
    rows = [r for r in m["contributions"] if r["demand_contribution"] != 0]
    assert rows, "fixture must have demand-side rows"
    top = rows[0]
    assert top["label"] in html
    assert f'{top["weight"]:g}' in html
    assert "<details>" in html
    ev_urls = [e["url"] for r in rows for e in r["evidence"] if e["url"]]
    if ev_urls:
        assert f'href="{ev_urls[0]}"' in html


def test_how_gap_shows_the_equation_and_cross_links():
    m = _model()
    html = render_how_tile(m, "gap")
    ds = m["demand_supply"]
    assert f'{ds["sdgi"]:+.2f}' in html
    assert 'href="demand.html"' in html and 'href="supply.html"' in html


def test_how_featured_shows_selection_trace():
    m = _model()
    html = render_how_featured(m)
    assert m["featured"]["reason_text"] in html
    assert m["featured"]["display"] in html


def test_appendix_has_raw_scores_findings_and_runs():
    m = _model()
    html = render_appendix(m)
    assert "Raw scores" in html
    for d in m["trend"]["dates"]:
        assert d in html
    assert str(len(m["runs"])) in html or m["runs"][0]["date"] in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_site_render.py -v -k "how_ or appendix"`
Expected: FAIL — `ImportError: cannot import name 'render_how_alert'`

- [ ] **Step 3: Write the implementation** (append to `site_render.py`; also modify `page()`
  to take `depth=0` as described in Interfaces)

```python
from gpu_agent import bands as _bands

from .site_model import rule_plain

_LADDER = [
    ("GREEN", "nothing on the watchlist moved this week"),
    ("YELLOW", "one thing moved: the gap band changed, a high-confidence call moved, the "
               "main limiting factor changed, or two calls moved together"),
    ("ORANGE", "two yellow-level things happened at once, a high-confidence call broke, or "
               "demand worsened while the gap moved toward glut"),
    ("RED", "a confirmed structural break: a high-confidence call broke AND the gap band "
            "flipped in the same week"),
]


def render_how_alert(model) -> str:
    a = model["alert"]
    ladder = "".join(f"<li><strong>{c}</strong>: {esc(d)}</li>" for c, d in _LADDER)
    fired = ("".join(f"<li>{esc(rule_plain(t))}</li>" for t in a["triggers"])
             or "<li>none - no rule fired</li>")
    flap = ""
    if a["raw"] != a["color"]:
        flap = (f'<p>Today\'s raw read was <strong>{esc(a["raw"].upper())}</strong>. The '
                "shown color steps down only after two calm runs in a row, so the page "
                f'still shows {esc(a["color"].upper())}.</p>')
    was = esc(a["prior"].upper()) if a["prior"] else "no prior run"
    body = (
        "<h1>How the alert color was decided</h1>"
        f'<p>Today: {_dot(a["color"])} <strong>{esc(a["color"].upper())}</strong> '
        f"(before: {was})</p>"
        "<h2>The ladder (first match from the top wins)</h2>"
        f"<ul>{ladder}</ul>"
        "<h2>What fired this run</h2>"
        f"<ul>{fired}</ul>" + flap +
        '<p><a href="../index.html">Back to the page</a></p>')
    return page("How the alert was decided", body, depth=1)


def _band_scale(value: float) -> str:
    words = ["contracting"] + [w for _, w in reversed(_bands.BANDS)]
    cur = _bands.band_word(value)
    cells = "".join(
        f"<td>{'&#9679; ' if w == cur else ''}{esc(w)}</td>" for w in words)
    return f'<div class="scroll"><table><tr>{cells}</tr></table></div>'


def _contrib_table(rows, side_key) -> str:
    live = [r for r in rows if r[side_key] != 0]
    if not live:
        return "<p>No scoring findings pulled this side this cycle.</p>"
    out = ['<div class="scroll"><table><tr><th>What</th><th>Weight</th>'
           "<th>Strength (1-3)</th><th>Pull</th></tr>"]
    for r in live:
        pull = f'{r[side_key]:+.3f}'
        ev = "".join(
            f'<li>{esc(e["source"])} ({esc(e["date"])}, {esc(e["tier"])} source)'
            + (f' - <a href="{esc(e["url"])}">link</a>' if e["url"] else "")
            + "</li>" for e in r["evidence"])
        out.append(
            f'<tr><td><details><summary>{esc(r["label"])} ({esc(r["entity"])})</summary>'
            f'<p>{esc(r["statement"])}</p><ul>{ev or "<li>no evidence rows</li>"}</ul>'
            f'</details></td><td>{r["weight"]:g}</td><td>{r["magnitude"]}</td>'
            f"<td>{pull}</td></tr>")
    out.append("</table></div>")
    return "".join(out)


def render_how_tile(model, side) -> str:
    ds = model["demand_supply"]
    if side == "gap":
        body = (
            "<h1>How the gap tile was computed</h1>"
            "<p>The gap score is simply demand minus supply:</p>"
            f'<p><strong>{ds["dmi"]:+.2f} (demand) minus {ds["smi"]:+.2f} (supply) '
            f'= {ds["sdgi"]:+.2f}</strong>, currently '
            f'{esc(ds["sdgi_direction"] or "balanced")}.</p>'
            "<p>To see what moved each side: "
            '<a href="demand.html">demand</a> &middot; '
            '<a href="supply.html">supply</a></p>'
            f"{_band_scale(ds['sdgi'])}"
            '<p><a href="../index.html">Back to the page</a></p>')
        return page("How the gap was computed", body, depth=1)
    key = "dmi" if side == "demand" else "smi"
    side_key = f"{side}_contribution"
    body = (
        f"<h1>How the {side} tile was computed</h1>"
        f"<p>The {side} score this run is <strong>{ds[key]:+.2f}</strong>. It lands on "
        "this five-word scale:</p>"
        f"{_band_scale(ds[key])}"
        "<h2>What pulled it (weight &times; direction &times; strength / 3, from this "
        "cycle's findings)</h2>"
        f"{_contrib_table(model['contributions'], side_key)}"
        "<p>Every row expands to the finding behind it and each piece of evidence: "
        "who published it, when, and whether it is a primary source.</p>"
        '<p><a href="../index.html">Back to the page</a></p>')
    return page(f"How the {side} tile was computed", body, depth=1)


def render_how_featured(model) -> str:
    f = model["featured"]
    note = f'<p class="muted">{esc(f["honesty_note"])}</p>' if f["honesty_note"] else ""
    src = ("Median of each cloud provider's median price, nearest stored day."
           if f["metric_id"].startswith("gpu-rent")
           else "From the desk's own scoring pipeline for this cycle.")
    body = (
        f'<h1>Why this number: {esc(f["plain_label"])}</h1>'
        f'<p><strong>{esc(f["display"])}</strong> - {esc(f["delta_phrase"])}</p>'
        f'<p>{esc(f["reason_text"])}</p>'
        "<p>The page shows one featured number per run, picked by a fixed rule: first, a "
        "metric tied to whatever set off today's alert; otherwise the metric that moved "
        "the most since the last run; otherwise a standing order with price first.</p>"
        f'<p>How to read it: {esc(f["how_to_read"])}</p>'
        f"<p>Source: {esc(src)}</p>" + note +
        '<p><a href="../index.html">Back to the page</a></p>')
    return page("Why this number", body, depth=1)


def render_appendix(model) -> str:
    t = model["trend"]
    head = "".join(f"<th>{esc(d)}</th>" for d in t["dates"])
    def row(label, xs):
        cells = "".join(f"<td>{x:+.2f}</td>" for x in xs)
        return f"<tr><td>{esc(label)}</td>{cells}</tr>"
    findings = "".join(
        f'<li><details><summary>{esc(f["plain"])}</summary>'
        f'<p class="muted">observed {esc(f.get("observed_at") or "n/a")} - '
        f'{esc(f.get("source_name") or "unnamed source")} ({esc(f.get("tier") or "?")})'
        "</p></details></li>"
        for f in model["top_signals"])
    runs = "".join(f'<li>{esc(r["date"])}: {r["findings"]} findings, {r["sources"]} '
                   "sources</li>" for r in model["runs"])
    body = (
        "<h1>Appendix</h1>"
        "<h2>Raw scores by run</h2>"
        f'<div class="scroll"><table><tr><th></th>{head}</tr>'
        f'{row("Demand", t["dmi"])}{row("Supply", t["smi"])}{row("Gap", t["sdgi"])}'
        "</table></div>"
        "<p>These raw scores read as direction, not level - the words on the main page "
        "are the honest summary.</p>"
        "<h2>Every ranked signal this run</h2>"
        f"<ul>{findings}</ul>"
        "<h2>Run history</h2>"
        f"<ul>{runs}</ul>"
        '<p><a href="index.html">Back to the page</a></p>')
    return page("Appendix", body, depth=0)
```

NOTE for the implementer: `model["top_signals"]` items come from `rank_findings` +
`resolve` in `build_model` — verify the exact keys (`plain`, `observed_at`, `source_name`,
`tier`) against `gpu_agent/dashboard/ranking.py::rank_findings` and adjust; the tests you
write pin whatever the real keys are. The appendix lives at the category-page level
(`site/<cat>/appendix.html`) hence `depth=0` and the `index.html` back link.

- [ ] **Step 4: Run tests + whole suite**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/ -v`
Expected: all PASS (Task 5's tests still green after the `page(depth=)` change)

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/dashboard/site_render.py tests/dashboard/test_site_render.py
git commit -m "$(cat <<'EOF'
feat(f95): drill-down pages — alert ladder, tile arithmetic to evidence, featured trace, appendix

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Site builder + `site` CLI verb (e2e: files, links, determinism)

**Files:**
- Create: `gpu_agent/dashboard/site_build.py`
- Modify: `gpu_agent/cli.py` (append-only: parser after the `report` block, dispatch line
  with the other `if args.cmd == ...` lines)
- Test: `tests/dashboard/test_site_build.py`

**Interfaces:**
- Consumes: Tasks 4–6 (`build_site_model`, all renderers, `SITE_CSS`, `HOW_LINKS`).
- Produces: `build_site(category_id, store_dir, work_dir, plain_path, out_dir,
  price_fn=None) -> dict` (summary `{"pages": int, "out": str, "featured": str | None}`),
  writing:
  `out/index.html` (redirect), `out/style.css`, `out/<category_id>/index.html`,
  `out/<category_id>/style.css`, `out/<category_id>/appendix.html`,
  `out/<category_id>/how/style.css` is NOT emitted — how pages link `../style.css`;
  `out/<category_id>/how/{alert,demand,supply,gap}.html` and `how/featured.html` only when
  a featured metric exists. CLI verb: `site`.

- [ ] **Step 1: Write the failing tests**

`tests/dashboard/test_site_build.py`:

```python
import re
from pathlib import Path

from gpu_agent.dashboard.site_build import build_site

FIX = "tests/dashboard/fixtures"
CAT = "chips.merchant-gpu"


def _build(tmp_path, price_fn=lambda d: {"H100": 2.31}):
    return build_site(CAT, FIX, work_dir="work-nonexistent",
                      plain_path=f"{FIX}/plain-2026-07-06.json",
                      out_dir=str(tmp_path / "site"), price_fn=price_fn)


def test_emits_the_full_page_set(tmp_path):
    summary = _build(tmp_path)
    root = tmp_path / "site"
    for rel in ("index.html", "style.css", f"{CAT}/index.html", f"{CAT}/style.css",
                f"{CAT}/appendix.html", f"{CAT}/how/alert.html", f"{CAT}/how/demand.html",
                f"{CAT}/how/supply.html", f"{CAT}/how/gap.html", f"{CAT}/how/featured.html"):
        assert (root / rel).exists(), rel
    assert summary["pages"] >= 8 and summary["featured"] is not None


def test_no_price_data_drops_only_the_featured_page(tmp_path):
    _build(tmp_path, price_fn=lambda d: {})
    root = tmp_path / "site"
    assert (root / CAT / "how" / "gap.html").exists()
    # featured falls back to an index metric, so the page still exists:
    assert (root / CAT / "how" / "featured.html").exists()


def test_every_local_href_resolves(tmp_path):
    _build(tmp_path)
    root = tmp_path / "site"
    for html_path in root.rglob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (html_path.parent / href).resolve()
            assert target.exists(), f"{html_path.name} -> {href}"


def test_two_builds_are_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    build_site(CAT, FIX, "work-nonexistent", f"{FIX}/plain-2026-07-06.json",
               str(a), price_fn=lambda d: {"H100": 2.31})
    build_site(CAT, FIX, "work-nonexistent", f"{FIX}/plain-2026-07-06.json",
               str(b), price_fn=lambda d: {"H100": 2.31})
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_site_build.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'gpu_agent.dashboard.site_build'`

- [ ] **Step 3: Write the builder**

`gpu_agent/dashboard/site_build.py`:

```python
"""F95 site builder — emits the committed site/ folder Cloudflare Pages serves as-is."""
from __future__ import annotations

from pathlib import Path

from .site_model import build_site_model
from .site_render import (
    SITE_CSS, render_appendix, render_category_page, render_how_alert,
    render_how_featured, render_how_tile, render_index_redirect,
)


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_site(category_id, store_dir, work_dir, plain_path, out_dir, price_fn=None):
    model = build_site_model(category_id, store_dir, work_dir, plain_path,
                             price_fn=price_fn)
    out = Path(out_dir)
    cat = out / category_id
    pages = 0

    label = category_id.rsplit(".", 1)[-1].replace("-", " ").title()
    _write(out / "index.html",
           render_index_redirect(f"{category_id}/index.html", label))
    _write(out / "style.css", SITE_CSS)
    _write(cat / "style.css", SITE_CSS)
    _write(cat / "index.html", render_category_page(model)); pages += 1
    _write(cat / "appendix.html", render_appendix(model)); pages += 1
    _write(cat / "how" / "alert.html", render_how_alert(model)); pages += 1
    for side in ("demand", "supply", "gap"):
        _write(cat / "how" / f"{side}.html", render_how_tile(model, side)); pages += 1
    featured = model.get("featured")
    if featured is not None:
        _write(cat / "how" / "featured.html", render_how_featured(model)); pages += 1

    return {"pages": pages + 1,   # +1 for the root redirect
            "out": str(out),
            "featured": featured["metric_id"] if featured else None}
```

- [ ] **Step 4: Append the CLI verb** (`gpu_agent/cli.py`, append-only)

After the `report` parser block (`gpu_agent/cli.py:1204-1227`), add:

```python
    st = sub.add_parser("site", help="F95: build the static category site into site/")
    st.add_argument("--category", default="chips.merchant-gpu")
    st.add_argument("--store", default="store/chips.merchant-gpu")
    st.add_argument("--work", default="work")
    st.add_argument("--plain", default=None,
                    help="plain-language overrides json (default: "
                         "store/<cat>/plain-language/<latest>.json when present)")
    st.add_argument("--out", default="site")
```

With the other dispatch lines (`if args.cmd == ...`), add:

```python
    if args.cmd == "site":
        return _site(args)
```

And a `_site` function next to the other `_verb` helpers (match the file's local style):

```python
def _site(args):
    from pathlib import Path
    from gpu_agent.dashboard.scorecards import load_scorecards
    from gpu_agent.dashboard.site_build import build_site
    plain = args.plain
    if plain is None:
        recs = load_scorecards(args.category, args.store)
        if recs:
            cand = Path(args.store) / "plain-language" / f'{recs[-1]["as_of"]}.json'
            plain = str(cand) if cand.exists() else None
    summary = build_site(args.category, args.store, args.work, plain, args.out)
    print(f'[site] pages={summary["pages"]} featured={summary["featured"]} '
          f'-> {summary["out"]}')
    return 0
```

- [ ] **Step 5: Run everything**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/ -v`
Expected: all PASS
Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green suite, F6 pin green.
Run: `git check-ignore -q site; echo "ignored=$?"`
Expected: `ignored=1` (site/ is NOT gitignored — spec §7.2 correction confirmed).

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/dashboard/site_build.py gpu_agent/cli.py tests/dashboard/test_site_build.py
git commit -m "$(cat <<'EOF'
feat(f95): site builder + append-only `site` CLI verb; e2e link/determinism pins

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Live build, run-cycle prose step, operator doc, lane wrap-up

**Files:**
- Create: `site/` (real build output, committed)
- Modify: `.claude/skills/run-cycle/SKILL.md` (end of section `### 7. Report`)
- Create: `docs/cloudflare-pages.md`
- Modify: `docs/superpowers/HANDOFF.md` (lane record), `.superpowers/handoffs/f95-site-DONE.md`

- [ ] **Step 1: Build the real site from the live store**

Run from the worktree root:
`../../.venv/Scripts/python -m gpu_agent.cli site`
Expected: `[site] pages=8 featured=<id> -> site` (or pages=9 with featured). Open
`site/chips.merchant-gpu/index.html` locally and eyeball: 3–4 tiles, alert line, WHY block,
working how-links. **Known and accepted (verified 2026-07-13):** the live store's
day-granularity scorecards run through `2026-07-06-v1.json`; the newer `2026-07-vN.json`
files are MONTHLY flagship cycles that `load_scorecards` deliberately excludes (same
convention as the dashboard — it trends daily cycles). So the first committed site will
honestly read "as of 2026-07-06" until the next daily runs; that is correct behavior, not
a bug. Record this in the DONE sentinel so nobody "fixes" it.

- [ ] **Step 2: Add the run-cycle step** (append at the end of `### 7. Report` in
  `.claude/skills/run-cycle/SKILL.md`)

```markdown
After the report, rebuild the public site so the committed `site/` matches the run (F95):

    .venv/Scripts/python -m gpu_agent.cli site

Commit `site/` together with the run's other artifacts. The site is a pure projection of
the store — never hand-edit its HTML.
```

- [ ] **Step 3: Write the operator doc**

`docs/cloudflare-pages.md`:

```markdown
# Cloudflare Pages hosting (F95)

The site is pre-rendered into `site/` and committed; Pages serves the folder as-is.

## One-time setup (operator)

1. Cloudflare dashboard -> Workers & Pages -> Create -> Pages -> Connect to Git.
2. Pick this GitHub repo (private is fine; the SITE becomes public, the repo does not).
3. Production branch: `main`. Build command: (leave empty). Build output directory: `site`.
4. Deploy. Every push to main auto-deploys in under a minute.

## Launch gates (user decisions — settle BEFORE the first deploy; spec §7.5)

- [ ] The standing "repo rename before TSMC-branded exposure" decision (the page carries a
      FOR TSMC section once F65 lands, and the exec framing is TSMC-specific).
- [ ] The `<project>.pages.dev` subdomain name (part of the same exposure decision).

Until both boxes are ticked, building and committing `site/` is fine — just do not connect
the Pages project.
```

- [ ] **Step 4: Suite + pin + lint gates**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green (5–6 skips), `tests/test_evals_baseline_pin.py` green.

- [ ] **Step 5: Commit the artifacts + prose**

```bash
git add site/ .claude/skills/run-cycle/SKILL.md docs/cloudflare-pages.md
git commit -m "$(cat <<'EOF'
feat(f95): first committed site build + run-cycle rebuild step + Pages operator doc

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: Lane wrap-up (STOP before merge — only the user merges)**

Write `.superpowers/handoffs/f95-site-DONE.md`: delivered list, suite count, the spec §7.2
gitignore correction, the run-cycle prose-collision note (F95's edit is in; F88 rebases over
it per its own "last of the prose-touchers" rule; F65's step 3e2 edit is on the F65 branch —
whichever merges second reconciles two ADJACENT additions, trivial), any deviations, and the
two launch gates still open. Update `docs/superpowers/HANDOFF.md` per its F76 discipline
(atomic top-block replace). Push the branch. Do NOT merge; do NOT touch `main`.

---

## Self-Review (done at plan-writing time)

- **Spec coverage:** S2 top band → Tasks 4/5; S3 featured library+selector → Tasks 1/2 and
  §4 selection trace → Task 6; S4 full trail → Tasks 3/6; S6 commit-then-serve → Tasks 7/8;
  §3a WHY block → Task 4; §7 deploy + gates → Task 8; §8 degradations → tests in Tasks 2/4/5/7;
  §9 testing list → mapped 1:1 (golden/byte determinism Task 7, selector truth table Task 1,
  link integrity Task 7, lint Task 5, no wall-clock Tasks 5/7). Rollup truth table (§9) is
  deliberately NOT here — spec §6 is contract-only and its tests land with Part B's build.
- **Known unknowns called out inline** (implementer notes): registry spec `.label` attribute,
  calls/top_signals exact key names, `find_latest_report` behavior on a missing dir, live
  store day-vs-month scorecard granularity (question-stop if monthly-only).
- **Type consistency:** `MetricReading`/`Selection` fields match across Tasks 1→2→4→6;
  `HOW_LINKS` hrefs match the files Task 7 writes; `page(depth=)` change is applied in Task 6
  with Task 5 tests kept green via the default.
