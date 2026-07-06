# Merchant-GPU Showcase Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reusable, deterministic Python generator that turns the daily `report.txt` + dated scorecards into a single self-contained plain-English HTML dashboard, plus a separate callable agent that rewrites the agent's jargon-y prose into the user's own voice.

**Architecture:** Two decoupled components joined by one file. (A) `gpu_agent.dashboard` — standard-library, LLM-free Python that loads scorecards (trends + ranking signals) and the latest report (claims), ranks every list most-important-first, and renders inline-SVG HTML; it consumes an optional plain-English overrides file and falls back to deterministic term-swap when a rewrite is missing/stale. (B) `.claude/agents/plain-language-writer.md` — a Claude Code subagent that rewrites prose into plain English in the user's voice (learned from dropped writing samples) and writes the overrides file, never touching source artifacts.

**Tech Stack:** Python 3 standard library only (no third-party deps, no network, no LLM in the tool). Inline HTML/CSS/SVG. pytest for tests. A Claude Code subagent definition (Markdown + frontmatter) for the writer.

## Global Constraints

*(Every task's requirements implicitly include this section. Values copied from the spec.)*

- **Generator is standard-library only, LLM-free, deterministic.** No third-party imports, no network, no `Date.now`-style nondeterminism beyond a single build timestamp.
- **Run Python from the worktree** via `../../.venv/Scripts/python` (one shared root venv; never create a per-worktree venv). Tests: `../../.venv/Scripts/python -m pytest -q`.
- **Single self-contained HTML:** all CSS/JS inline, charts hand-rendered inline SVG, no CDN/external assets/fonts. Theme-aware via `prefers-color-scheme`.
- **Ranking = weighted sum**, weights in one constant block: `W_NEW=0.40`, `W_OFFICIAL=0.35`, `W_IMPACT=0.25`. Ties break by New, then Official. Recency decays linearly to 0 at 42 days (full credit ≤ 7 days). Impact from the finding's `magnitude` (scale 1–3), with a bump when a large figure (≥ $1B or a ≥6-digit unit count) appears in the text.
- **Plain-language rule:** no AI-writing-tell words in authored copy; no raw acronym as a *primary label*; the shared glossary (`glossary.json`) powers labels, tooltips, and the term-swap fallback.
- **Plain-language overrides file:** `store/chips.merchant-gpu/plain-language/<YYYY-MM-DD>.json`, keyed by stable ids, storing `original` alongside `plain` for drift detection. Missing/stale → term-swap fallback + visible "pending human rewrite" flag; never blocks the render.
- **Voice files:** `.claude/agents/plain-language-writer/voice-samples/` and `voice-profile.md` are **gitignored** by default.
- **File reads** are UTF-8 with `errors="replace"` (console is cp1252).
- **`work/` is gitignored** → `report.txt` is NOT a committed fixture; tests use hermetic copies under `tests/dashboard/fixtures/`. `store/` IS committed.
- **Do not touch the frozen core or brain-prompt files** (extraction/judgment/thesis prompts, their CLI vocab glue, registry vocab) — this work adds only new files, so it must not trip `tests/test_evals_baseline_pin.py` (the F6 gate). Suite must be green at merge (expect 3–4 skips).
- **Coordination:** all work on the `dashboard-showcase` lane in `.worktrees/dashboard`. Before every commit: `git log --oneline -1` (HEAD-guard). Stage files explicitly — never `git add -A` (a concurrent instance has unrelated dirty files on root). Commit messages via bash heredoc.
- **Category** is `chips.merchant-gpu`, passed as a parameter (`category_id`) so a second category is a later one-line change.

## File Structure

**Component A — generator (new files):**
- `gpu_agent/dashboard/__init__.py` — package marker.
- `gpu_agent/dashboard/glossary.json` — shared translation dictionary (labels + prose terms). Single source of truth for generator and agent.
- `gpu_agent/dashboard/glossary.py` — load glossary; `plain_label`; `term_swap`; `has_big_figure`.
- `gpu_agent/dashboard/scorecards.py` — load dated scorecards → normalized per-cycle records + trend series.
- `gpu_agent/dashboard/report_calls.py` — find latest `report.txt`; parse the `THE CALLS` block.
- `gpu_agent/dashboard/ranking.py` — importance score, signals, badges; rank findings and claims.
- `gpu_agent/dashboard/plain_language.py` — stable-id keys; load overrides; drift check; resolve text with fallback.
- `gpu_agent/dashboard/render.py` — inline-SVG helpers + section renderers + full-document assembly.
- `gpu_agent/dashboard/build.py` — orchestrator + `main(argv)`.
- `scripts/build_dashboard.py` — thin CLI wrapper.
- `docs/dashboard.html` — build output (generated; gitignored or committed per taste — default committed so it can be shared).

**Component B — writer agent (new files):**
- `.claude/agents/plain-language-writer.md` — subagent definition.
- `.claude/agents/plain-language-writer/voice-samples/README.md` — "drop samples here".
- `voice-profile.md` — generated by calibrate (gitignored).
- `store/chips.merchant-gpu/plain-language/2026-07-06.json` — this run's overrides (produced in Task 9).

**Tests + fixtures (new files):**
- `tests/dashboard/test_glossary.py`, `test_scorecards.py`, `test_report_calls.py`, `test_ranking.py`, `test_plain_language.py`, `test_render.py`, `test_build_e2e.py`, `test_voice_privacy.py`
- `tests/dashboard/fixtures/` — committed copies: `2026-07-02-v1.json` … `2026-07-06-v1.json` (4 scorecards), `report-2026-07-06.txt`, `plain-2026-07-06.json` (small sample overrides).

**Modified files:**
- `.gitignore` — add the voice paths.

---

### Task 1: Shared glossary (labels, term-swap, big-figure detection)

**Files:**
- Create: `gpu_agent/dashboard/__init__.py`
- Create: `gpu_agent/dashboard/glossary.json`
- Create: `gpu_agent/dashboard/glossary.py`
- Test: `tests/dashboard/test_glossary.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `load_glossary(path: str | None = None) -> dict` → `{"labels": dict[str,str], "prose_terms": dict[str,str]}`
  - `plain_label(term: str, glossary: dict) -> str`
  - `term_swap(text: str, glossary: dict) -> str`
  - `has_big_figure(text: str) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/test_glossary.py
from gpu_agent.dashboard.glossary import (
    load_glossary, plain_label, term_swap, has_big_figure,
)

def test_glossary_loads_labels_and_prose_terms():
    g = load_glossary()
    assert g["labels"]["DMI"] == "Demand momentum"
    assert "HBM" in g["prose_terms"]

def test_plain_label_falls_back_to_term_when_unknown():
    g = load_glossary()
    assert plain_label("DMI", g) == "Demand momentum"
    assert plain_label("Totally Unknown", g) == "Totally Unknown"

def test_term_swap_expands_jargon_case_insensitively_and_longest_first():
    g = {"labels": {}, "prose_terms": {"HBM": "high-bandwidth memory",
                                       "merchant-GPU": "open-market GPUs"}}
    out = term_swap("hbm demand for merchant-GPU rose", g)
    assert "high-bandwidth memory" in out
    assert "open-market GPUs" in out
    assert "HBM" not in out and "merchant-GPU" not in out

def test_has_big_figure_detects_dollars_billions_and_large_counts():
    assert has_big_figure("books over $2B China revenue")
    assert has_big_figure("underwriting well over 200,000 GPUs")
    assert has_big_figure("$1.5 billion committed")
    assert not has_big_figure("a small qualitative shift")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_glossary.py -q`
Expected: FAIL (ModuleNotFoundError: `gpu_agent.dashboard`).

- [ ] **Step 3: Create the package marker and glossary data**

```python
# gpu_agent/dashboard/__init__.py
"""Deterministic, LLM-free dashboard generator for the GPU Category Agent."""
```

```json
// gpu_agent/dashboard/glossary.json
{
  "labels": {
    "DMI": "Demand momentum",
    "SMI": "Supply momentum",
    "SDGI": "Demand-vs-supply gap",
    "PMI": "Price direction",
    "momentum": "Right now",
    "outlook": "Looking ahead",
    "demand-led": "Driven by demand",
    "supply-led": "Driven by supply",
    "balanced": "Balanced",
    "bottleneck": "Supply bottleneck",
    "unitEconomics": "Profit economics",
    "competitiveStructure": "Competition",
    "moat": "Durability of the lead",
    "strategicRisk": "Big-picture risks",
    "grounded": "Backed by evidence this run",
    "under-supported": "Little evidence this run",
    "primary": "Official source",
    "secondary": "News & analysis",
    "INTACT": "Still holds",
    "CHALLENGED": "Being questioned",
    "reaffirmed": "Reconfirmed",
    "strengthened": "Getting stronger",
    "weakened": "Getting weaker"
  },
  "prose_terms": {
    "merchant-GPU": "open-market GPUs",
    "merchant GPU": "open-market GPUs",
    "HBM": "high-bandwidth memory",
    "DRAM": "standard memory chips",
    "NVMe": "fast storage drives",
    "CoWoS": "advanced chip packaging",
    "neocloud": "GPU rental cloud",
    "take-or-pay": "pay-whether-or-not-you-use-it",
    "hyperscaler": "largest cloud companies",
    "export control": "US limits on chip sales to China",
    "export-control": "US limits on chip sales to China",
    "custom ASIC": "custom in-house AI chip",
    "ASIC": "custom AI chip",
    "CUDA": "the leader's chip software",
    "bill of materials": "parts cost",
    "BOM": "parts cost",
    "wafer": "silicon production",
    "lead times": "wait time from order to delivery",
    "backlog": "orders placed but not yet filled"
  }
}
```

- [ ] **Step 4: Implement `glossary.py`**

```python
# gpu_agent/dashboard/glossary.py
import json
import re
from pathlib import Path

_DEFAULT = Path(__file__).with_name("glossary.json")


def load_glossary(path=None):
    p = Path(path) if path else _DEFAULT
    with open(p, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    data.setdefault("labels", {})
    data.setdefault("prose_terms", {})
    return data


def plain_label(term, glossary):
    return glossary.get("labels", {}).get(term, term)


def term_swap(text, glossary):
    if not text:
        return text
    terms = sorted(glossary.get("prose_terms", {}), key=len, reverse=True)
    out = text
    for term in terms:
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        out = pattern.sub(glossary["prose_terms"][term], out)
    return out


_MONEY = re.compile(r"\$\s?\d", re.IGNORECASE)
_BILLIONS = re.compile(r"\b\d[\d,.]*\s?(?:billion|bn)\b", re.IGNORECASE)
_BIG_COUNT = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{6,}\b")


def has_big_figure(text):
    if not text:
        return False
    return bool(_MONEY.search(text) or _BILLIONS.search(text) or _BIG_COUNT.search(text))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_glossary.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git log --oneline -1   # HEAD-guard: confirm it is your last commit (or the lane base)
git add gpu_agent/dashboard/__init__.py gpu_agent/dashboard/glossary.json gpu_agent/dashboard/glossary.py tests/dashboard/test_glossary.py
git commit -F- <<'EOF'
feat(dashboard): shared glossary — labels, term-swap, big-figure detection

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 2: Scorecard loader + trend series

**Files:**
- Create: `gpu_agent/dashboard/scorecards.py`
- Test: `tests/dashboard/test_scorecards.py`
- Create (fixtures): `tests/dashboard/fixtures/2026-07-02-v1.json`, `2026-07-03-v1.json`, `2026-07-05-v1.json`, `2026-07-06-v1.json` (copies of the real `store/chips.merchant-gpu/` files)

**Interfaces:**
- Consumes: nothing (reads JSON).
- Produces:
  - `load_scorecards(category_id: str, store_dir: str) -> list[dict]` — one normalized record per cycle, sorted by `asOf` ascending. Record keys: `as_of` (str), `rating`, `direction`, `bottleneck`, `reason`, `dmi` (float), `smi` (float), `sdgi` (float), `sdgi_direction`, `dimensions` (dict name→{`rating`,`direction`,`confidence`,`evidence_status`,`finding_count`}), `findings` (list of normalized finding dicts), `sources` (list), `findings_count`, `primary_count`, `secondary_count`, `sources_count`, `confidence`.
  - Normalized finding dict keys: `id`, `statement`, `observed_at` (str|None), `magnitude` (int), `impact_direction` (str), `mechanism`, `source_name`, `tier` (`"primary"|"secondary"`), `evidence_date`.
  - `trend_series(records: list[dict]) -> dict` → `{"dates":[...], "dmi":[...], "smi":[...], "sdgi":[...]}`.

- [ ] **Step 1: Create fixtures (copy the real scorecards)**

Run (from the worktree root):
```bash
mkdir -p tests/dashboard/fixtures
for d in 2026-07-02-v1 2026-07-03-v1 2026-07-05-v1 2026-07-06-v1; do
  cp "store/chips.merchant-gpu/$d.json" "tests/dashboard/fixtures/$d.json"
done
ls tests/dashboard/fixtures
```
Expected: the four json files listed.

- [ ] **Step 2: Write the failing test**

```python
# tests/dashboard/test_scorecards.py
from gpu_agent.dashboard.scorecards import load_scorecards, trend_series

FIX = "tests/dashboard/fixtures"

def test_loads_all_cycles_sorted_ascending():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    assert [r["as_of"] for r in recs] == ["2026-07-02", "2026-07-03", "2026-07-05", "2026-07-06"]

def test_latest_record_headline_fields():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    latest = recs[-1]
    assert latest["rating"] == "Strong"
    assert latest["direction"] == "worsening"
    assert round(latest["dmi"], 3) == 0.04
    assert round(latest["smi"], 3) == -0.027
    assert round(latest["sdgi"], 3) == 0.067
    assert latest["findings_count"] == 15

def test_findings_are_normalized():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    f = recs[-1]["findings"][0]
    assert set(["id", "statement", "observed_at", "magnitude",
                "impact_direction", "tier", "source_name"]).issubset(f)
    assert f["tier"] in ("primary", "secondary")

def test_trend_series_shape():
    recs = load_scorecards("chips.merchant-gpu", FIX)
    ts = trend_series(recs)
    assert len(ts["dates"]) == 4
    assert len(ts["dmi"]) == 4 and len(ts["smi"]) == 4 and len(ts["sdgi"]) == 4
```

- [ ] **Step 3: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_scorecards.py -q`
Expected: FAIL (ImportError: cannot import name `load_scorecards`).

- [ ] **Step 4: Implement `scorecards.py`**

```python
# gpu_agent/dashboard/scorecards.py
import json
import re
from pathlib import Path

# Day-level cycles only (YYYY-MM-DD). Month-granularity rollups like
# 2026-06-vN.json are intentionally excluded — the dashboard trends over daily cycles.
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})-v(\d+)\.json$")


def _read_json(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return json.load(fh)


def _best_tier(evidence):
    for ev in evidence or []:
        if ev.get("tier") == "primary":
            return "primary"
    return "secondary"


def _source_name(evidence):
    for ev in evidence or []:
        if ev.get("source"):
            return ev["source"]
    return ""


def _norm_finding(f):
    ev = f.get("evidence") or []
    impact = f.get("impact") or {}
    return {
        "id": f.get("id", ""),
        "statement": f.get("statement", ""),
        "observed_at": f.get("observedAt") or f.get("asOf"),
        "magnitude": int(f.get("magnitude") or 0),
        "impact_direction": impact.get("direction", ""),
        "mechanism": impact.get("mechanism", ""),
        "source_name": _source_name(ev),
        "tier": _best_tier(ev),
        "evidence_date": (ev[0].get("date") if ev else None),
    }


def _norm_dimensions(ratings, status):
    dims = {}
    names = set(ratings) | set(status)
    for name in names:
        r = ratings.get(name, {}) or {}
        s = status.get(name, {}) or {}
        dims[name] = {
            "rating": r.get("rating"),
            "direction": r.get("direction"),
            "confidence": (r.get("confidence") or {}).get("level"),
            "rationale": r.get("rationale", ""),
            "evidence_status": s.get("evidenceStatus", "under-supported"),
            "finding_count": int(s.get("findingCount") or 0),
        }
    return dims


def load_scorecards(category_id, store_dir):
    base = Path(store_dir)
    latest = {}  # date -> (version, path); keep highest version per date
    for p in base.glob("*.json"):
        m = _DATE_RE.search(p.name)
        if not m:
            continue
        d_str, ver = m.group(1), int(m.group(2))
        if d_str not in latest or ver > latest[d_str][0]:
            latest[d_str] = (ver, p)
    files = sorted((d_str, vp[1]) for d_str, vp in latest.items())
    records = []
    for as_of, path in files:
        d = _read_json(path)
        ds = d.get("demandSupply", {}) or {}
        cat = d.get("categoryStatus", {}) or {}
        findings = [_norm_finding(f) for f in (d.get("findings") or [])]
        prim = sum(1 for f in findings if f["tier"] == "primary")
        records.append({
            "as_of": d.get("asOf", as_of),
            "rating": cat.get("rating"),
            "direction": cat.get("direction"),
            "bottleneck": cat.get("bottleneck"),
            "reason": cat.get("reason", ""),
            "dmi": float(ds.get("dmiContribution") or 0.0),
            "smi": float(ds.get("smiContribution") or 0.0),
            "sdgi": float(ds.get("sdgi") or 0.0),
            "sdgi_direction": ds.get("sdgiDirection", ""),
            "dimensions": _norm_dimensions(d.get("dimensionRatings", {}) or {},
                                           d.get("dimensionStatus", {}) or {}),
            "findings": findings,
            "sources": d.get("sources", []) or [],
            "findings_count": len(findings),
            "primary_count": prim,
            "secondary_count": len(findings) - prim,
            "sources_count": len(d.get("sources", []) or []),
            "confidence": (d.get("confidence", {}) or {}).get("level"),
        })
    return records


def trend_series(records):
    return {
        "dates": [r["as_of"] for r in records],
        "dmi": [r["dmi"] for r in records],
        "smi": [r["smi"] for r in records],
        "sdgi": [r["sdgi"] for r in records],
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_scorecards.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/scorecards.py tests/dashboard/test_scorecards.py tests/dashboard/fixtures/
git commit -F- <<'EOF'
feat(dashboard): scorecard loader + trend series (normalized per-cycle records)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 3: Parse `THE CALLS` block from `report.txt`

**Files:**
- Create: `gpu_agent/dashboard/report_calls.py`
- Test: `tests/dashboard/test_report_calls.py`
- Create (fixture): `tests/dashboard/fixtures/report-2026-07-06.txt` (copy of the real latest report; `work/` is gitignored so this copy must be committed)

**Interfaces:**
- Consumes: nothing (reads text).
- Produces:
  - `find_latest_report(work_dir: str) -> Path | None` — newest `daily-*/report.txt` by directory name.
  - `parse_calls(report_text: str) -> list[dict]` — each: `name`, `slug`, `status` (`"intact"|"challenged"|"not_judged"`), `direction` (`"reaffirmed"|"strengthened"|"weakened"|"none"`), `conviction` (`"high"|"medium"|"low"`), `cycles` (int), `statement`, `source_count` (int), `has_official` (bool), `early` (bool), `breaks_if` (str).

- [ ] **Step 1: Create the fixture**

Run (from the worktree root):
```bash
cp "$(ls -d work/daily-*/ | sort | tail -1)report.txt" tests/dashboard/fixtures/report-2026-07-06.txt
grep -c '●' tests/dashboard/fixtures/report-2026-07-06.txt
```
Expected: prints `14` (14 tracked calls; note the report separately reports 15 *findings* — different count).

- [ ] **Step 2: Write the failing test**

```python
# tests/dashboard/test_report_calls.py
from gpu_agent.dashboard.report_calls import parse_calls

def _load():
    with open("tests/dashboard/fixtures/report-2026-07-06.txt", encoding="utf-8", errors="replace") as fh:
        return fh.read()

def test_parses_all_fourteen_calls():
    calls = parse_calls(_load())
    assert len(calls) == 14

def test_first_call_fields():
    calls = parse_calls(_load())
    c = next(c for c in calls if c["name"].startswith("Export control"))
    assert c["status"] == "intact"
    assert c["direction"] == "reaffirmed"
    assert c["conviction"] == "high"
    assert c["cycles"] == 2
    assert c["slug"] == "export-control-exposure"
    assert "Export-control policy" in c["statement"]
    assert c["source_count"] == 1

def test_detects_challenged_and_official_and_early():
    calls = parse_calls(_load())
    challenged = [c for c in calls if c["status"] == "challenged"]
    assert any("Custom ASIC" in c["name"] for c in challenged)
    assert any(c["has_official"] for c in calls)   # "incl. company filing / official post"
    assert any(c["early"] for c in calls)          # "early — not yet corroborated"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_report_calls.py -q`
Expected: FAIL (ImportError: `parse_calls`).

- [ ] **Step 4: Implement `report_calls.py`**

```python
# gpu_agent/dashboard/report_calls.py
import re
from pathlib import Path

_HEAD = re.compile(
    r"^\s*●\s+(?P<name>.+?)\s{2,}(?P<statusdir>.+?)\s+\((?P<conv>high|medium|low),\s*(?P<cycles>\d+)\s*cycles?\)(?P<tail>.*)$"
)
_SRC = re.compile(r"\((?P<n>\d+)\s+sources?", re.IGNORECASE)


def _slug(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def find_latest_report(work_dir):
    base = Path(work_dir)
    dailies = sorted([p for p in base.glob("daily-*") if (p / "report.txt").exists()],
                     key=lambda p: p.name)
    if not dailies:
        return None
    return dailies[-1] / "report.txt"


def _status(statusdir):
    s = statusdir.upper()
    if "CHALLENGED" in s:
        return "challenged"
    if "NOT YET JUDGED" in s:
        return "not_judged"
    return "intact"


def _direction(statusdir):
    s = statusdir.lower()
    if "strengthened" in s:
        return "strengthened"
    if "weakened" in s:
        return "weakened"
    if "reaffirmed" in s:
        return "reaffirmed"
    return "none"


def parse_calls(report_text):
    lines = report_text.splitlines()
    calls = []
    i = 0
    while i < len(lines):
        m = _HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group("name").strip()
        tail = m.group("tail") or ""
        # Following indented lines until the next call or blank-section break.
        body = []
        j = i + 1
        while j < len(lines) and lines[j].startswith("      ") and "●" not in lines[j]:
            body.append(lines[j].strip())
            j += 1
        statement = body[0] if body else ""
        breaks_if = ""
        for b in body:
            if b.lower().startswith("breaks if:"):
                breaks_if = b.split(":", 1)[1].strip()
        src = _SRC.search(statement)
        calls.append({
            "name": name,
            "slug": _slug(name),
            "status": _status(m.group("statusdir")),
            "direction": _direction(m.group("statusdir")),
            "conviction": m.group("conv"),
            "cycles": int(m.group("cycles")),
            "statement": re.sub(r"\s*\(\d+ sources?.*?\)\s*$", "", statement).strip(),
            "source_count": int(src.group("n")) if src else 0,
            "has_official": "official post" in (statement + tail).lower()
                            or "company filing" in (statement + tail).lower(),
            "early": "early" in tail.lower() and "corroborated" in tail.lower(),
            "breaks_if": breaks_if,
        })
        i = j
    return calls
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_report_calls.py -q`
Expected: PASS (3 passed). If the statement/source assertions are off by whitespace, adjust the fixture-derived expectations — not the parser's contract.

- [ ] **Step 6: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/report_calls.py tests/dashboard/test_report_calls.py tests/dashboard/fixtures/report-2026-07-06.txt
git commit -F- <<'EOF'
feat(dashboard): parse THE CALLS block from report.txt

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 4: Importance ranking (signals, score, badges)

**Files:**
- Create: `gpu_agent/dashboard/ranking.py`
- Test: `tests/dashboard/test_ranking.py`

**Interfaces:**
- Consumes: normalized finding dicts (Task 2), call dicts (Task 3), `has_big_figure` (Task 1).
- Produces:
  - Constants `W_NEW, W_OFFICIAL, W_IMPACT, RECENCY_FULL_DAYS, RECENCY_ZERO_DAYS, MAGNITUDE_MAX`.
  - `finding_signals(finding: dict, as_of: str, glossary: dict) -> dict` → `{"new":float,"official":float,"impact":float}`
  - `call_signals(call: dict) -> dict`
  - `importance(signals: dict) -> float`
  - `badges(signals: dict) -> list[str]` (subset of `["new","official","impact"]`)
  - `rank_findings(findings, as_of, glossary) -> list[dict]` (each finding + `_signals`, `_score`, `_badges`; sorted)
  - `rank_calls(calls) -> list[dict]` (each call + `_signals`, `_score`, `_badges`; sorted)

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/test_ranking.py
from gpu_agent.dashboard.glossary import load_glossary
from gpu_agent.dashboard.ranking import (
    finding_signals, importance, badges, rank_findings,
)

G = load_glossary()

def _finding(**kw):
    base = dict(id="x", statement="a shift", observed_at="2026-07-06",
                magnitude=1, impact_direction="negative", tier="secondary",
                source_name="News")
    base.update(kw)
    return base

def test_recent_primary_highmag_outranks_stale_secondary_lowmag():
    strong = _finding(id="s", tier="primary", magnitude=3,
                      observed_at="2026-07-06",
                      statement="books over $2B China revenue")
    weak = _finding(id="w", tier="secondary", magnitude=1,
                    observed_at="2026-05-01", statement="a small shift")
    ranked = rank_findings([weak, strong], as_of="2026-07-06", glossary=G)
    assert ranked[0]["id"] == "s"

def test_official_badge_when_primary():
    sig = finding_signals(_finding(tier="primary"), "2026-07-06", G)
    assert "official" in badges(sig)

def test_recency_decays_to_zero_by_six_weeks():
    fresh = finding_signals(_finding(observed_at="2026-07-06"), "2026-07-06", G)
    stale = finding_signals(_finding(observed_at="2026-05-20"), "2026-07-06", G)
    assert fresh["new"] > 0.9
    assert stale["new"] == 0.0

def test_importance_is_weighted_sum_in_unit_range():
    sig = {"new": 1.0, "official": 1.0, "impact": 1.0}
    assert abs(importance(sig) - 1.0) < 1e-9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_ranking.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `ranking.py`**

```python
# gpu_agent/dashboard/ranking.py
from datetime import date
from .glossary import has_big_figure

W_NEW = 0.40
W_OFFICIAL = 0.35
W_IMPACT = 0.25
RECENCY_FULL_DAYS = 7
RECENCY_ZERO_DAYS = 42
MAGNITUDE_MAX = 3

_NEW_BADGE_AT = 0.66
_IMPACT_BADGE_AT = 0.66


def _parse_date(s):
    try:
        return date.fromisoformat(s[:10])
    except (TypeError, ValueError):
        return None


def _recency(observed_at, as_of):
    d0, d1 = _parse_date(observed_at), _parse_date(as_of)
    if not d0 or not d1:
        return 0.0
    age = (d1 - d0).days
    if age <= RECENCY_FULL_DAYS:
        return 1.0
    if age >= RECENCY_ZERO_DAYS:
        return 0.0
    span = RECENCY_ZERO_DAYS - RECENCY_FULL_DAYS
    return max(0.0, 1.0 - (age - RECENCY_FULL_DAYS) / span)


def finding_signals(finding, as_of, glossary):
    new = _recency(finding.get("observed_at"), as_of)
    official = 1.0 if finding.get("tier") == "primary" else 0.4
    impact = min(1.0, (finding.get("magnitude", 0) or 0) / MAGNITUDE_MAX)
    if has_big_figure(finding.get("statement", "")):
        impact = min(1.0, impact + 0.2)
    return {"new": new, "official": official, "impact": impact}


_CONV = {"high": 1.0, "medium": 0.66, "low": 0.33}
_MOVED = {"strengthened", "weakened"}


def call_signals(call):
    status = call.get("status")
    direction = call.get("direction")
    moved = direction in _MOVED or status in ("challenged", "not_judged") or call.get("cycles", 0) == 0
    new = 1.0 if moved else 0.3
    official = 1.0 if call.get("has_official") else 0.4
    impact = _CONV.get(call.get("conviction"), 0.33)
    return {"new": new, "official": official, "impact": impact}


def importance(signals):
    return (W_NEW * signals.get("new", 0.0)
            + W_OFFICIAL * signals.get("official", 0.0)
            + W_IMPACT * signals.get("impact", 0.0))


def badges(signals):
    out = []
    if signals.get("new", 0.0) >= _NEW_BADGE_AT:
        out.append("new")
    if signals.get("official", 0.0) >= 1.0:
        out.append("official")
    if signals.get("impact", 0.0) >= _IMPACT_BADGE_AT:
        out.append("impact")
    return out


def _sort_key(item):
    s = item["_signals"]
    return (-item["_score"], -s["new"], -s["official"])


def rank_findings(findings, as_of, glossary):
    out = []
    for f in findings:
        sig = finding_signals(f, as_of, glossary)
        out.append({**f, "_signals": sig, "_score": importance(sig), "_badges": badges(sig)})
    out.sort(key=_sort_key)
    return out


def rank_calls(calls):
    out = []
    for c in calls:
        sig = call_signals(c)
        out.append({**c, "_signals": sig, "_score": importance(sig), "_badges": badges(sig)})
    out.sort(key=_sort_key)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_ranking.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/ranking.py tests/dashboard/test_ranking.py
git commit -F- <<'EOF'
feat(dashboard): importance ranking — new/official/impact signals, score, badges

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 5: Plain-language overrides — stable keys, drift check, fallback

**Files:**
- Create: `gpu_agent/dashboard/plain_language.py`
- Test: `tests/dashboard/test_plain_language.py`
- Create (fixture): `tests/dashboard/fixtures/plain-2026-07-06.json`

**Interfaces:**
- Consumes: `term_swap` (Task 1).
- Produces:
  - Key helpers: `STATE_OF_MARKET_KEY = "stateOfMarket"`, `dimension_key(name) -> str`, `claim_key(slug) -> str`, `finding_key(fid) -> str`.
  - `load_plain_language(path: str | None) -> dict` → `{key: {"original":..,"plain":..,"note":..}}` (empty dict if missing).
  - `resolve_text(key, original, plain_map, glossary) -> tuple[str, bool]` → `(text, pending)`; `pending=True` means the shown text is the auto term-swap fallback (no fresh rewrite).

- [ ] **Step 1: Create the fixture**

```json
// tests/dashboard/fixtures/plain-2026-07-06.json
{
  "categoryId": "chips.merchant-gpu",
  "asOf": "2026-07-06",
  "generatedBy": "plain-language-writer",
  "rewrites": {
    "stateOfMarket": {
      "original": "Binding constraint is HBM.",
      "plain": "The main thing holding growth back is a shortage of the specialized memory AI chips need."
    }
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/dashboard/test_plain_language.py
from gpu_agent.dashboard.glossary import load_glossary
from gpu_agent.dashboard.plain_language import (
    load_plain_language, resolve_text, dimension_key, claim_key, finding_key,
    STATE_OF_MARKET_KEY,
)

G = load_glossary()
PMAP = load_plain_language("tests/dashboard/fixtures/plain-2026-07-06.json")

def test_key_helpers():
    assert STATE_OF_MARKET_KEY == "stateOfMarket"
    assert dimension_key("bottleneck") == "dimension.bottleneck.rationale"
    assert claim_key("export-control-exposure") == "claim.export-control-exposure.statement"
    assert finding_key("abc-1") == "finding.abc-1.statement"

def test_fresh_rewrite_is_used_when_original_matches():
    text, pending = resolve_text(STATE_OF_MARKET_KEY, "Binding constraint is HBM.", PMAP, G)
    assert pending is False
    assert "specialized memory" in text

def test_drift_falls_back_and_flags_pending():
    text, pending = resolve_text(STATE_OF_MARKET_KEY, "A different sentence about HBM now.", PMAP, G)
    assert pending is True
    assert "high-bandwidth memory" in text   # term-swap applied

def test_missing_key_falls_back():
    text, pending = resolve_text("finding.zzz.statement", "raw HBM text", {}, G)
    assert pending is True
    assert "high-bandwidth memory" in text
```

- [ ] **Step 3: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_plain_language.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 4: Implement `plain_language.py`**

```python
# gpu_agent/dashboard/plain_language.py
import json
from pathlib import Path
from .glossary import term_swap

STATE_OF_MARKET_KEY = "stateOfMarket"


def dimension_key(name):
    return f"dimension.{name}.rationale"


def claim_key(slug):
    return f"claim.{slug}.statement"


def finding_key(fid):
    return f"finding.{fid}.statement"


def load_plain_language(path):
    if not path or not Path(path).exists():
        return {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = json.load(fh)
    return data.get("rewrites", {}) or {}


def _norm(s):
    return " ".join((s or "").split())


def resolve_text(key, original, plain_map, glossary):
    entry = plain_map.get(key)
    if entry and _norm(entry.get("original")) == _norm(original) and entry.get("plain"):
        return entry["plain"], False
    return term_swap(original, glossary), True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_plain_language.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/plain_language.py tests/dashboard/test_plain_language.py tests/dashboard/fixtures/plain-2026-07-06.json
git commit -F- <<'EOF'
feat(dashboard): plain-language overrides — stable keys, drift check, term-swap fallback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 6: HTML render (inline SVG helpers + section renderers + document)

**Files:**
- Create: `gpu_agent/dashboard/render.py`
- Test: `tests/dashboard/test_render.py`

**Interfaces:**
- Consumes: everything above, via a `model` dict assembled by Task 7. `model` keys: `category_label` (str), `latest_date` (str), `run_count` (int), `generated_at` (str), `headline` (`{rating,direction,limiting_factor,state_of_market,state_pending}`), `tiles` (list of `{label,value,delta,spark}`), `trend` (from `trend_series`), `top_signals` (ranked findings, each with resolved `plain`/`pending`), `calls` (ranked calls, each with resolved `plain`/`pending`), `demand_supply` (`{dmi,smi,sdgi,sdgi_direction}`), `dimensions` (list of `{label,rating,direction,evidence_status}`), `runs` (list of `{date,findings,sources}`), `glossary_rows` (list of `{term,plain}`), `slop_denylist` (list[str]).
- Produces:
  - `svg_sparkline(values: list[float], width=80, height=20) -> str`
  - `svg_line_chart(series: dict, labels: list[str], width=640, height=220) -> str`
  - `render_html(model: dict) -> str`
  - Module constant `SECTION_IDS = ["headline","trend","top-signals","calls","demand-supply","dimensions","runs","guide"]`

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/test_render.py
import re
from gpu_agent.dashboard.render import render_html, svg_sparkline, svg_line_chart, SECTION_IDS

def _model():
    return {
        "category_label": "Merchant-GPU Market",
        "latest_date": "2026-07-06", "run_count": 4,
        "generated_at": "2026-07-06 09:20",
        "headline": {"rating": "Strong", "direction": "worsening",
                     "limiting_factor": "shortage of specialized AI memory",
                     "state_of_market": "Demand keeps outrunning supply.",
                     "state_pending": False},
        "tiles": [{"label": "Demand momentum", "value": "0.04", "delta": "+0.00",
                   "spark": [0.0, 0.02, 0.03, 0.04]}],
        "trend": {"dates": ["07-02", "07-03", "07-05", "07-06"],
                  "dmi": [0.0, 0.02, 0.03, 0.04], "smi": [0.0, 0.0, -0.01, -0.03],
                  "sdgi": [0.0, 0.02, 0.05, 0.07]},
        "top_signals": [{"plain": "Memory is getting scarcer.", "pending": False,
                         "_badges": ["new", "official", "impact"], "observed_at": "2026-07-06",
                         "source_name": "SEC", "impact_direction": "negative"}],
        "calls": [{"name": "Export control exposure", "plain": "US rules cap how many chips can be sold.",
                   "pending": True, "status": "intact", "direction": "reaffirmed",
                   "conviction": "high", "cycles": 2, "source_count": 1,
                   "_badges": ["official"], "breaks_if": "rules are lifted"}],
        "demand_supply": {"dmi": 0.04, "smi": -0.03, "sdgi": 0.07, "sdgi_direction": "demand-led"},
        "dimensions": [{"label": "Supply bottleneck", "rating": "Weak",
                        "direction": "worsening", "evidence_status": "grounded"}],
        "runs": [{"date": "2026-07-06", "findings": 15, "sources": 10}],
        "glossary_rows": [{"term": "HBM", "plain": "high-bandwidth memory"}],
        "slop_denylist": ["delve", "leverage", "seamless", "boasts", "robust"],
    }

def test_renders_all_sections_and_is_self_contained():
    html = render_html(_model())
    for sid in SECTION_IDS:
        assert f'id="{sid}"' in html
    assert "<!doctype html>" in html.lower()
    assert "http://" not in html and "https://" not in html   # no external assets
    assert "prefers-color-scheme" in html

def test_no_slop_words_in_output():
    html = render_html(_model()).lower()
    for w in _model()["slop_denylist"]:
        assert w not in html

def test_pending_items_are_flagged():
    html = render_html(_model())
    assert "pending human rewrite" in html.lower()

def test_svg_helpers_return_svg():
    assert svg_sparkline([0, 1, 2, 3]).startswith("<svg")
    assert svg_line_chart({"dmi": [0, 1]}, ["a", "b"]).startswith("<svg")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_render.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `render.py` — helpers + escaping + CSS**

```python
# gpu_agent/dashboard/render.py
import html as _html

SECTION_IDS = ["headline", "trend", "top-signals", "calls",
               "demand-supply", "dimensions", "runs", "guide"]

_BADGE = {"new": "🆕 New", "official": "🏛 Official source", "impact": "💲 High impact"}
_PENDING = '<span class="pending" title="Auto-simplified from the source; a human rewrite has not been applied yet.">pending human rewrite</span>'


def esc(s):
    return _html.escape("" if s is None else str(s))


def _badges_html(badges):
    return "".join(f'<span class="badge b-{b}">{_BADGE[b]}</span>' for b in badges if b in _BADGE)


def _pending_html(pending):
    return f" {_PENDING}" if pending else ""


def _minmax(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0, 1.0
    lo, hi = min(vals), max(vals)
    if lo == hi:
        lo, hi = lo - 1.0, hi + 1.0
    return lo, hi


def svg_sparkline(values, width=80, height=20):
    lo, hi = _minmax(values)
    n = max(1, len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        if v is None:
            continue
        x = (i / n) * (width - 2) + 1
        y = height - 1 - ((v - lo) / (hi - lo)) * (height - 2)
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline fill="none" stroke="currentColor" stroke-width="1.5" points="{" ".join(pts)}"/></svg>')


_CHART_COLORS = {"dmi": "#2563eb", "smi": "#d97706", "sdgi": "#059669"}
_SERIES_LABEL = {"dmi": "Demand", "smi": "Supply", "sdgi": "Gap"}


def svg_line_chart(series, labels, width=640, height=220):
    pad = 28
    all_vals = [v for s in series.values() for v in s]
    lo, hi = _minmax(all_vals)
    n = max(1, max((len(s) for s in series.values()), default=1) - 1)

    def x(i):
        return pad + (i / n) * (width - 2 * pad)

    def y(v):
        return height - pad - ((v - lo) / (hi - lo)) * (height - 2 * pad)

    parts = [f'<svg class="chart" width="100%" viewBox="0 0 {width} {height}" role="img">']
    zero_y = y(0.0) if lo <= 0 <= hi else None
    if zero_y is not None:
        parts.append(f'<line x1="{pad}" y1="{zero_y:.1f}" x2="{width - pad}" y2="{zero_y:.1f}" class="axis"/>')
    for key, s in series.items():
        color = _CHART_COLORS.get(key, "#64748b")
        pts_pairs = [(x(i), y(v)) for i, v in enumerate(s) if v is not None]
        if not pts_pairs:
            continue
        pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts_pairs)
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}"/>')
        lx, ly = pts_pairs[-1]
        parts.append(f'<text x="{lx + 4:.1f}" y="{ly:.1f}" class="lbl" fill="{color}">{esc(_SERIES_LABEL.get(key, key.upper()))}</text>')
    for i, lab in enumerate(labels):
        parts.append(f'<text x="{x(i):.1f}" y="{height - 8}" class="tick" text-anchor="middle">{esc(lab)}</text>')
    parts.append("</svg>")
    return "".join(parts)


CSS = """
:root{--bg:#ffffff;--fg:#0f172a;--muted:#64748b;--card:#f8fafc;--line:#e2e8f0;--accent:#2563eb;--warn:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#0b1220;--fg:#e5e9f0;--muted:#94a3b8;--card:#111a2e;--line:#1e293b;--accent:#60a5fa;--warn:#f59e0b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:24px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--muted);font-size:14px}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:170px;flex:1}
.tile .v{font-size:24px;font-weight:650}.tile .d{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.badge{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;margin-right:6px;border:1px solid var(--line)}
.b-new{color:#166534}.b-official{color:#1e40af}.b-impact{color:#9a3412}
@media (prefers-color-scheme:dark){.b-new{color:#86efac}.b-official{color:#93c5fd}.b-impact{color:#fdba74}}
.pending{color:var(--warn);font-size:12px;font-style:italic}
.meta{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:8px;text-align:left;font-size:14px}
.chart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px}
.axis{stroke:var(--line)}.tick{fill:var(--muted);font-size:11px}.lbl{font-size:11px;font-weight:600}
.spark{color:var(--accent);vertical-align:middle}
.caption{color:var(--muted);font-size:13px;margin-top:6px}
details{margin-top:6px}summary{cursor:pointer;color:var(--muted);font-size:13px}
.helps{color:#166534}.hurts{color:#9a3412}
@media (prefers-color-scheme:dark){.helps{color:#86efac}.hurts{color:#fca5a5}}
"""
```

- [ ] **Step 4: Implement `render.py` — section renderers + `render_html`**

```python
# ...append to gpu_agent/dashboard/render.py

def _dir_word(direction):
    return {"worsening": "Worsening", "improving": "Improving"}.get(direction, "Steady")


def _sec_headline(m):
    h = m["headline"]
    tiles = "".join(
        f'<div class="tile"><div class="meta">{esc(t["label"])}</div>'
        f'<div class="v">{esc(t["value"])} {svg_sparkline(t["spark"])}</div>'
        f'<div class="d">{esc(t["delta"])} vs previous run</div></div>'
        for t in m["tiles"])
    return (f'<section id="headline"><h2>Where the market stands</h2>'
            f'<div class="card"><strong>{esc(h["rating"])} · {esc(_dir_word(h["direction"]))}</strong>'
            f'<div class="meta">Main limiting factor: {esc(h["limiting_factor"])}</div>'
            f'<p>{esc(h["state_of_market"])}{_pending_html(h["state_pending"])}</p></div>'
            f'<div class="tiles">{tiles}</div></section>')


def _sec_trend(m):
    return (f'<section id="trend"><h2>How the numbers moved</h2>'
            f'{svg_line_chart({"dmi": m["trend"]["dmi"], "smi": m["trend"]["smi"], "sdgi": m["trend"]["sdgi"]}, m["trend"]["dates"])}'
            f'<div class="caption">Up = stronger demand (DMI), tighter supply (SMI), or a wider demand-vs-supply gap (SDGI). '
            f'Read the direction, not the exact level.</div></section>')


def _impact_span(direction):
    if direction == "negative":
        return '<span class="hurts">▼ hurts the market</span>'
    if direction == "positive":
        return '<span class="helps">▲ helps the market</span>'
    return '<span class="meta">mixed</span>'


def _sec_top_signals(m):
    rows = []
    for s in m["top_signals"]:
        rows.append(
            f'<div class="card">{_badges_html(s["_badges"])}'
            f'<div>{esc(s["plain"])}{_pending_html(s["pending"])}</div>'
            f'<div class="meta">{esc(s.get("observed_at"))} · {esc(s.get("source_name"))} · {_impact_span(s.get("impact_direction"))}</div></div>')
    return (f'<section id="top-signals"><h2>Top signals — most important first</h2>'
            f'<div class="caption">Sorted most important first — newest, official-source, and highest-impact items rise to the top.</div>'
            f'{"".join(rows)}</section>')


_STATUS_LABEL = {"intact": "Still holds", "challenged": "Being questioned", "not_judged": "Too new to rate"}
_DIR_LABEL = {"strengthened": "Getting stronger", "weakened": "Getting weaker",
              "reaffirmed": "Reconfirmed", "none": ""}


def _sec_calls(m):
    cards = []
    for c in m["calls"]:
        breaks = (f'<details><summary>We\'d change our mind if …</summary>'
                  f'<div class="meta">{esc(c["breaks_if"])}</div></details>') if c.get("breaks_if") else ""
        cards.append(
            f'<div class="card"><strong>{esc(c["name"])}</strong> {_badges_html(c["_badges"])}'
            f'<div class="meta">{esc(_STATUS_LABEL.get(c["status"], c["status"]))} · '
            f'{esc(_DIR_LABEL.get(c["direction"], ""))} · Confidence: {esc(c["conviction"])} · '
            f'Tracked for {esc(c["cycles"])} runs · {esc(c["source_count"])} sources</div>'
            f'<div>{esc(c["plain"])}{_pending_html(c["pending"])}</div>{breaks}</div>')
    return (f'<section id="calls"><h2>Key claims we\'re tracking</h2>'
            f'<div class="caption">Ordered most important first.</div>{"".join(cards)}</section>')


def _sec_demand_supply(m):
    d = m["demand_supply"]
    gapword = {"demand-led": "Demand is pulling ahead", "supply-led": "Supply is pulling ahead",
               "balanced": "Roughly balanced"}.get(d.get("sdgi_direction"), "")
    return (f'<section id="demand-supply"><h2>Demand vs supply</h2>'
            f'<div class="card"><strong>{esc(gapword)}</strong>'
            f'<div class="meta">Demand momentum {d["dmi"]:+.2f} · Supply momentum {d["smi"]:+.2f} · '
            f'Gap {d["sdgi"]:+.2f}</div></div></section>')


def _sec_dimensions(m):
    rows = "".join(
        f'<tr><td>{esc(x["label"])}</td><td>{esc(x["rating"])}</td>'
        f'<td>{esc(_dir_word(x["direction"]))}</td>'
        f'<td>{esc("Backed by evidence this run" if x["evidence_status"] == "grounded" else "Little evidence this run")}</td></tr>'
        for x in m["dimensions"])
    return (f'<section id="dimensions"><h2>Where the evidence is strong (and thin)</h2>'
            f'<table><tr><th>Area</th><th>Rating</th><th>Trend</th><th>Evidence</th></tr>{rows}</table></section>')


def _sec_runs(m):
    rows = "".join(
        f'<tr><td>{esc(r["date"])}</td><td>{esc(r["findings"])} evidence points</td>'
        f'<td>{esc(r["sources"])} sources</td></tr>' for r in m["runs"])
    return (f'<section id="runs"><h2>What we\'ve done so far</h2>'
            f'<div class="caption">Each run gathers fresh evidence and re-scores the market.</div>'
            f'<table><tr><th>Run</th><th>Evidence</th><th>Sources</th></tr>{rows}</table></section>')


def _sec_guide(m):
    rows = "".join(f'<tr><td>{esc(g["term"])}</td><td>{esc(g["plain"])}</td></tr>' for g in m["glossary_rows"])
    return (f'<section id="guide"><h2>Plain-language guide</h2>'
            f'<table><tr><th>Term</th><th>Plain meaning</th></tr>{rows}</table>'
            f'<div class="caption">The index levels wobble run to run until more history builds up — read direction, not level.</div></section>')


def render_html(model):
    body = "".join(f(model) for f in (
        _sec_headline, _sec_trend, _sec_top_signals, _sec_calls,
        _sec_demand_supply, _sec_dimensions, _sec_runs, _sec_guide))
    head = (f'<h1>{esc(model["category_label"])} — Agent Dashboard</h1>'
            f'<div class="sub">Latest run {esc(model["latest_date"])} · {esc(model["run_count"])} runs · '
            f'generated {esc(model["generated_at"])}</div>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(model["category_label"])} — Agent Dashboard</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{head}{body}</div></body></html>')
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_render.py -q`
Expected: PASS (4 passed). Note the test model uses no slop words and no `http(s)://`; keep it that way.

- [ ] **Step 6: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/render.py tests/dashboard/test_render.py
git commit -F- <<'EOF'
feat(dashboard): inline-SVG render — 8 sections, ranked cards, plain-language flags

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 7: Orchestrator + CLI + end-to-end render

**Files:**
- Create: `gpu_agent/dashboard/build.py`
- Create: `scripts/build_dashboard.py`
- Test: `tests/dashboard/test_build_e2e.py`

**Interfaces:**
- Consumes: all modules above.
- Produces:
  - `build_model(category_id, store_dir, work_dir, plain_path, generated_at) -> dict` (the render model).
  - `build_dashboard(category_id, store_dir, work_dir, plain_path, out_path, generated_at) -> dict` (summary: `{runs, claims, rewrites_applied, auto_simplified, out}`); writes the HTML.
  - `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/dashboard/test_build_e2e.py
import json, os
from gpu_agent.dashboard.build import build_dashboard

FIX = "tests/dashboard/fixtures"

def test_end_to_end_writes_html_and_summary(tmp_path):
    # Arrange a mini work dir containing the fixture report.
    work = tmp_path / "work" / "daily-2026-07-06"
    work.mkdir(parents=True)
    with open(f"{FIX}/report-2026-07-06.txt", encoding="utf-8", errors="replace") as fh:
        (work / "report.txt").write_text(fh.read(), encoding="utf-8")
    out = tmp_path / "dashboard.html"
    summary = build_dashboard(
        category_id="chips.merchant-gpu", store_dir=FIX,
        work_dir=str(tmp_path / "work"), plain_path=f"{FIX}/plain-2026-07-06.json",
        out_path=str(out), generated_at="2026-07-06 09:20")
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert 'id="calls"' in html and 'id="top-signals"' in html
    assert summary["runs"] == 4
    assert summary["claims"] == 14
    assert summary["auto_simplified"] >= 1   # most sentences have no fixture rewrite
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_build_e2e.py -q`
Expected: FAIL (ImportError).

- [ ] **Step 3: Implement `build.py`**

```python
# gpu_agent/dashboard/build.py
import argparse
import sys
from pathlib import Path

from .glossary import load_glossary, plain_label
from .scorecards import load_scorecards, trend_series
from .report_calls import find_latest_report, parse_calls
from .ranking import rank_findings, rank_calls
from .plain_language import (
    load_plain_language, resolve_text,
    STATE_OF_MARKET_KEY, dimension_key, claim_key, finding_key,
)

SLOP = ["delve", "leverage", "seamless", "boasts", "robust", "in today's fast-paced",
        "tapestry", "underscore", "testament to"]
_DIM_ORDER = ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]


def _delta(cur, prev):
    if prev is None:
        return "first run"
    return f"{cur - prev:+.2f}"


def build_model(category_id, store_dir, work_dir, plain_path, generated_at):
    g = load_glossary()
    pmap = load_plain_language(plain_path)
    recs = load_scorecards(category_id, store_dir)
    latest = recs[-1]
    prev = recs[-2] if len(recs) > 1 else None
    ts = trend_series(recs)

    counters = {"rewrites_applied": 0, "auto_simplified": 0}

    def resolve(key, original):
        text, pending = resolve_text(key, original, pmap, g)
        counters["auto_simplified" if pending else "rewrites_applied"] += 1
        return text, pending

    state_text, state_pending = resolve(STATE_OF_MARKET_KEY, latest["reason"])

    tiles = []
    for label, key in (("Demand momentum", "dmi"), ("Supply momentum", "smi"),
                       ("Demand-vs-supply gap", "sdgi")):
        tiles.append({"label": label, "value": f'{latest[key]:.2f}',
                      "delta": _delta(latest[key], prev[key] if prev else None),
                      "spark": ts[key]})

    ranked_findings = rank_findings(latest["findings"], latest["as_of"], g)
    top_signals = []
    for f in ranked_findings:
        plain, pending = resolve(finding_key(f["id"]), f["statement"])
        top_signals.append({**f, "plain": plain, "pending": pending})

    report = find_latest_report(work_dir)
    calls_raw = parse_calls(Path(report).read_text(encoding="utf-8", errors="replace")) if report else []
    ranked_calls = rank_calls(calls_raw)
    calls = []
    for c in ranked_calls:
        plain, pending = resolve(claim_key(c["slug"]), c["statement"])
        calls.append({**c, "plain": plain, "pending": pending})

    dims = []
    for name in _DIM_ORDER:
        d = latest["dimensions"].get(name)
        if not d:
            dims.append({"label": plain_label(name, g), "rating": "—",
                         "direction": "steady", "evidence_status": "under-supported"})
            continue
        dims.append({"label": plain_label(name, g), "rating": d["rating"] or "—",
                     "direction": d["direction"] or "steady",
                     "evidence_status": d["evidence_status"]})

    runs = [{"date": r["as_of"], "findings": r["findings_count"], "sources": r["sources_count"]} for r in recs]
    glossary_rows = [{"term": t, "plain": p} for t, p in g["prose_terms"].items()]

    model = {
        "category_label": "Merchant-GPU Market",
        "latest_date": latest["as_of"], "run_count": len(recs),
        "generated_at": generated_at,
        "headline": {"rating": latest["rating"], "direction": latest["direction"],
                     "limiting_factor": plain_label(latest["bottleneck"] or "", g) or "—",
                     "state_of_market": state_text, "state_pending": state_pending},
        "tiles": tiles, "trend": ts, "top_signals": top_signals, "calls": calls,
        "demand_supply": {"dmi": latest["dmi"], "smi": latest["smi"],
                          "sdgi": latest["sdgi"], "sdgi_direction": latest["sdgi_direction"]},
        "dimensions": dims, "runs": runs, "glossary_rows": glossary_rows,
        "slop_denylist": SLOP,
    }
    return model, {"runs": len(recs), "claims": len(calls_raw), **counters}


def build_dashboard(category_id, store_dir, work_dir, plain_path, out_path, generated_at):
    from .render import render_html
    model, summary = build_model(category_id, store_dir, work_dir, plain_path, generated_at)
    html = render_html(model)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html, encoding="utf-8")
    summary["out"] = out_path
    return summary


def _now_stamp():
    # Single build timestamp; the only nondeterministic value, isolated here.
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the merchant-GPU showcase dashboard.")
    ap.add_argument("--category", default="chips.merchant-gpu")
    ap.add_argument("--store", default="store/chips.merchant-gpu")
    ap.add_argument("--work", default="work")
    ap.add_argument("--plain", default=None,
                    help="plain-language overrides json (default: store/<cat>/plain-language/<latest>.json)")
    ap.add_argument("--out", default="docs/dashboard.html")
    args = ap.parse_args(argv)

    plain = args.plain
    if plain is None:
        recs = load_scorecards(args.category, args.store)
        if recs:
            cand = Path(args.store) / "plain-language" / f'{recs[-1]["as_of"]}.json'
            plain = str(cand) if cand.exists() else None

    summary = build_dashboard(args.category, args.store, args.work, plain, args.out, _now_stamp())
    print(f'[dashboard] runs={summary["runs"]} claims={summary["claims"]} '
          f'rewrites={summary["rewrites_applied"]} auto_simplified={summary["auto_simplified"]} '
          f'-> {summary["out"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Implement the thin CLI wrapper**

```python
# scripts/build_dashboard.py
"""CLI: build the merchant-GPU showcase dashboard (deterministic, LLM-free)."""
import os
import sys

# Ensure the local package (this checkout / worktree) is imported, not an
# editable-installed copy at another path. scripts/ is one level below the root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gpu_agent.dashboard.build import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the e2e test, then the full dashboard test module**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_build_e2e.py -q`
Expected: PASS (1 passed).

Run: `../../.venv/Scripts/python -m pytest tests/dashboard -q`
Expected: PASS (all dashboard tests green).

- [ ] **Step 6: Smoke-run the real generator**

Run (from the worktree root):
```bash
# NOTE: worktrees do not carry the gitignored work/ dir, so point --work at the root checkout's work/ (two levels up).
../../.venv/Scripts/python scripts/build_dashboard.py --store store/chips.merchant-gpu --work ../../work --out docs/dashboard.html
```
Expected: prints a `[dashboard] runs=4 claims=14 …-> docs/dashboard.html` line and writes the file. Open `docs/dashboard.html` in a browser and confirm it renders (prose will be auto-simplified until Task 9 supplies rewrites).

- [ ] **Step 7: Commit**

```bash
git log --oneline -1
git add gpu_agent/dashboard/build.py scripts/build_dashboard.py tests/dashboard/test_build_e2e.py docs/dashboard.html
git commit -F- <<'EOF'
feat(dashboard): orchestrator + CLI + end-to-end build

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 8: Plain-language writer agent + voice calibration + privacy

**Files:**
- Create: `.claude/agents/plain-language-writer.md`
- Create: `.claude/agents/plain-language-writer/voice-samples/README.md`
- Modify: `.gitignore`
- Test: `tests/dashboard/test_voice_privacy.py`

**Interfaces:**
- Consumes: `glossary.json` (baseline vocabulary), the stable-id key scheme (Task 5), the overrides file schema (spec §4c).
- Produces: the callable subagent; the gitignore guarantees; the voice-samples drop folder.

- [ ] **Step 1: Write the failing privacy test**

```python
# tests/dashboard/test_voice_privacy.py
from pathlib import Path

def _gitignore():
    return Path(".gitignore").read_text(encoding="utf-8", errors="replace")

def test_voice_samples_and_profile_are_gitignored():
    gi = _gitignore()
    assert ".claude/agents/plain-language-writer/voice-samples/" in gi
    assert ".claude/agents/plain-language-writer/voice-profile.md" in gi

def test_agent_definition_exists_and_declares_separate_output_file():
    txt = Path(".claude/agents/plain-language-writer.md").read_text(encoding="utf-8", errors="replace")
    assert "store/chips.merchant-gpu/plain-language/" in txt
    assert "voice-profile.md" in txt
    assert "style, never content" in txt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_voice_privacy.py -q`
Expected: FAIL (FileNotFoundError / assertion).

- [ ] **Step 3: Append the voice paths to `.gitignore`**

Append these lines to `.gitignore` (verify they are not already present first):
```
# plain-language-writer: private writing samples & derived voice profile (never commit)
.claude/agents/plain-language-writer/voice-samples/
.claude/agents/plain-language-writer/voice-profile.md
```

- [ ] **Step 4: Create the voice-samples drop folder README**

```markdown
<!-- .claude/agents/plain-language-writer/voice-samples/README.md -->
# Drop your writing here

Paste past conversations or things you've written into this folder as `.md` or `.txt`
files (one file per sample, or everything in a single `samples.md`). The
plain-language-writer learns **how you write** from them — sentence length, word
choices, punctuation habits — and matches your voice when it rewrites the agent's prose.

Nothing here is committed to git. It stays on your machine.

After adding samples, run the writer in **calibrate** mode to (re)build
`../voice-profile.md`.
```

- [ ] **Step 5: Create the agent definition**

```markdown
<!-- .claude/agents/plain-language-writer.md -->
---
name: plain-language-writer
description: >
  Rewrites the GPU Category Agent's jargon-heavy analytical prose into plain,
  human English in the user's own voice. Call it to (1) calibrate voice from
  writing samples, or (2) rewrite a run's prose into a plain-language overrides
  file for the dashboard. Reusable for any project text.
tools: Read, Grep, Write
---

You turn dense, jargon-y analytical sentences into plain English that reads like the
user wrote it. You are the "brain"; you never run code to do the writing.

## Two modes

### calibrate
Input: the files in `.claude/agents/plain-language-writer/voice-samples/`.
Read them all and write `.claude/agents/plain-language-writer/voice-profile.md`:
1. **Traits** — typical sentence length and rhythm, use of contractions, punctuation
   habits (em-dashes, lists, parentheticals), favored and avoided words, formality,
   how they open and close, recurring quirks.
2. **Pinned examples** — 2–3 short verbatim snippets that best capture the voice.
Keep it editable and concise. If there are no samples, say so and stop.

### rewrite  (default)
Inputs you read (never modify):
- the cycle scorecard `store/<category>/<date>-v*.json`
- the run report `work/daily-<date>/report.txt`
- `gpu_agent/dashboard/glossary.json` (baseline plain vocabulary)
- `voice-profile.md` if present
Output you write: `store/<category>/plain-language/<date>.json` with:
```
{ "categoryId": "...", "asOf": "...", "generatedBy": "plain-language-writer",
  "rewrites": { "<key>": { "original": "<verbatim source>", "plain": "<your rewrite>", "note": "" } } }
```
Keys (stable ids the dashboard expects):
- `stateOfMarket` — from `categoryStatus.reason`
- `dimension.<name>.rationale` — from each `dimensionRatings.<name>.rationale`
- `claim.<slug>.statement` — from each call in THE CALLS (slug = kebab-case of the name)
- `finding.<id>.statement` — from each finding's `statement`

## Rules (in priority order)
1. **Accuracy first.** Keep every number, date, company name, and direction (up/down,
   helps/hurts) exactly. Keep hedging ("alleged", "not yet confirmed") — never launder
   uncertainty into confidence.
2. **Plain English.** A sharp reader with no domain background must understand it with
   no lookups. Expand or replace every acronym/jargon term using glossary.json as the
   baseline. Rewrite sentence shape — do not just swap words.
3. **No AI writing tells.** Follow the stop-slop skill: no "delve/leverage/seamless/
   robust/boasts", no rule-of-three padding, no throat-clearing, restrained em-dashes.
4. **In the user's voice.** Match `voice-profile.md` when present — subordinate to rules 1–3.
5. **Style, never content.** Learn *how* the user writes from the samples; never copy
   *what* the samples say into a rewrite. Rewrite content comes only from the source text.
6. **Honesty.** If a source sentence is too vague to rewrite faithfully, leave `plain`
   close to the original and explain in `note` — do not invent detail.

Always store the exact `original` next to each `plain` so the dashboard can detect drift.
```

- [ ] **Step 6: Run the privacy test to verify it passes**

Run: `../../.venv/Scripts/python -m pytest tests/dashboard/test_voice_privacy.py -q`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git log --oneline -1
git add .gitignore .claude/agents/plain-language-writer.md .claude/agents/plain-language-writer/voice-samples/README.md tests/dashboard/test_voice_privacy.py
git commit -F- <<'EOF'
feat(dashboard): plain-language-writer agent + voice calibration + gitignore privacy

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

### Task 9: Produce this run's plain-English file and verify end-to-end

**Files:**
- Create: `store/chips.merchant-gpu/plain-language/2026-07-06.json` (produced by the agent, Claude-in-the-loop)
- Verify: `docs/dashboard.html`

**Interfaces:**
- Consumes: the agent (Task 8), the generator (Task 7).
- Produces: a real, plain-English dashboard.

- [ ] **Step 1: (Optional) calibrate voice**
If the user has dropped samples into `.claude/agents/plain-language-writer/voice-samples/`, invoke the `plain-language-writer` agent in **calibrate** mode to write `voice-profile.md`. If no samples yet, skip — rewrites will use neutral plain English.

- [ ] **Step 2: Rewrite this run's prose**
Invoke the `plain-language-writer` agent in **rewrite** mode for `chips.merchant-gpu`, `2026-07-06`. It reads the latest scorecard + report + glossary (+ profile) and writes `store/chips.merchant-gpu/plain-language/2026-07-06.json` covering: `stateOfMarket`, all `dimension.<name>.rationale`, all `claim.<slug>.statement`, all `finding.<id>.statement`.

- [ ] **Step 3: Rebuild the dashboard with the rewrites**

Run (point `--work` at the root checkout's `work/`; the worktree has none):
```bash
../../.venv/Scripts/python scripts/build_dashboard.py --store store/chips.merchant-gpu --work ../../work --out docs/dashboard.html
```
Expected: `auto_simplified` drops toward 0 and `rewrites` rises (most sentences now have fresh rewrites).

- [ ] **Step 4: Verify (use the `verify` skill)**
Open `docs/dashboard.html`. Confirm: all 9 sections render; the prose reads as plain English (no raw acronyms as primary text); "Top signals" and "Key claims" are ordered most-important-first with correct 🆕/🏛/💲 badges; light and dark themes both look right; no "pending human rewrite" flags remain on covered sentences.

- [ ] **Step 5: Full suite + commit**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: green (expect 3–4 pre-existing skips; the F6 baseline-pin test must NOT go red — this work touches no brain prompts).

```bash
git log --oneline -1
git add store/chips.merchant-gpu/plain-language/2026-07-06.json docs/dashboard.html
git commit -F- <<'EOF'
feat(dashboard): plain-English overrides for 2026-07-06 + rebuilt dashboard

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
```

---

## Self-Review

**Spec coverage:**
- §1/§5 both-with-trends showcase → Tasks 2 (trends), 6 (all 9 sections), 7 (assembly). ✓
- §3a scorecards / §3b report calls → Tasks 2, 3. ✓
- §4 plain-language principle + §4a dictionary → Task 1 (glossary), Task 6 (labels), Task 5 (fallback). ✓
- §4b importance ranking (signals, weighted sum, badges, what-gets-ranked) → Task 4; wired in Task 7. ✓
- §4c writer agent + overrides schema + stable keys → Tasks 8 (agent), 5 (keys), 9 (produce). ✓
- §4d voice calibration + guardrails + gitignore → Task 8. ✓
- §6 self-contained inline-SVG, theme-aware → Task 6 (asserted in tests). ✓
- §7 build flow (calibrate → rewrite → render, one-command render, fallback) → Tasks 7, 9. ✓
- §8 robustness (missing field, unparseable calls, one run, stale plain file) → guarded in Tasks 2/3/5/7; drift + fallback tested in Task 5. ✓
- §9 tests (unit, ranking, slop, plain-language wiring, voice privacy, e2e) → Tasks 1–8 tests; §9 end-to-end → Task 9. ✓
- §10 decisions (output location, weights, plain-file location, agent-vs-skill, privacy, not-committed-by-agent) → reflected in constraints + Task 7 defaults + Task 8. ✓

**Placeholder scan:** No "TBD/TODO/handle edge cases" — every code step carries full code; the only human-in-loop steps (Task 9 agent invocations) are inherently model work and are described concretely. ✓

**Type consistency:** finding dict keys (`observed_at`, `magnitude`, `tier`, `statement`, `id`) are identical across Tasks 2/4/7; call dict keys (`slug`, `status`, `direction`, `conviction`, `cycles`, `statement`, `has_official`, `breaks_if`) identical across Tasks 3/4/6/7; `resolve_text` returns `(text, pending)` and is consumed that way in Task 7; key helpers (`STATE_OF_MARKET_KEY`, `dimension_key`, `claim_key`, `finding_key`) defined in Task 5 and used in Tasks 7/8. ✓

**One coverage note (not a gap):** the `unitEconomics`/`moat` "under-supported" dimensions render as `—` rows (Task 7), matching the report's own handling.
