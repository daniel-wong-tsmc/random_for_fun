# Sub-project A — Scorecard → Executive Report: Design Spec

- **Date:** 2026-06-27
- **Status:** Binding spec for implementation
- **Sub-project:** A (of three — see umbrella design)
- **Umbrella:** `docs/superpowers/specs/2026-06-27-output-coverage-decomposition-design.md`
- **Charter refs:** Part 35 (product surface); Part 17 (ratings, DMI/SMI/SDGI, plain-language rule); Parts 10–11 (recommendation → status → drill to findings → sources); Part 20 (reproducibility); Part 18 #8 (bend, don't break)

---

## 1. Context and Goal

The live `chips.merchant-gpu` run (v1 → v3) currently prints a garbled free-text summary produced by the LLM judge. The same scorecard produces a different-looking report each run, and two critical dimensions (`bottleneck`, `strategicRisk`) were silently absent without any signal that coverage was incomplete. A TSMC executive reading the output cannot tell what was and wasn't covered, cannot compare to last cycle, and cannot trace a number to its source. That is the gap sub-project A closes.

**A's mandate:** a deterministic `gpu_agent/report.py` + a `report` CLI subcommand that **reads a saved scorecard** (and optionally the prior-cycle scorecard for trend) and **renders** — never invents — a board-ready, plain-language report. Same scorecard input → byte-identical report output (Part 20). No LLM call, no network, no side effects.

A is a **pure projection consumer** (Part 35): it reads from the published snapshot (`store/`) and prints. It never writes canonical state.

---

## 2. Shared Seams Honoured (from Umbrella §2)

A touches these seams and must not diverge from the umbrella's definitions:

| Seam | A's behaviour |
|---|---|
| `Scorecard.dimensionStatus: dict[str, DimensionStatus]` — produced by B; the AUTHORITATIVE six-row view, always all 6 dimension names | A renders the six dimension rows from this; `evidenceStatus` per dimension comes from here, **not** from `dimensionRatings` |
| `Scorecard.dimensionRatings` — stays GROUNDED-ONLY (only dims the judge grounded, each citing ≥1 finding) | A JOINs it onto `dimensionStatus` for rating/direction/confidence/rationale detail of grounded dims only |
| `Scorecard.categoryStatus{rating, direction, bottleneck, reason}` — produced by B | A renders it when present; falls back to "not yet available" on older scorecards |
| `DemandSupply.sdgi: Optional[float]` + `DemandSupply.sdgiDirection: Optional[Literal["demand-led","supply-led","balanced"]]` — computed in code by B | A prefers the stored `sdgi` if present, else derives `sdgi = dmiContribution − smiContribution` at render time; never asks the agent to compute it |
| Trend Δ — derived by A, not stored | A reads the prior scorecard from `store/<categoryId>/` or a caller-supplied path; no new scorecard field needed |
| `Scorecard.sources: list[str]` | A derives richer source metadata (tier, date) by scanning `findings[].evidence[]`; the `sources` field provides the base URL list |

**`DimensionStatus` shape (B's model):** `{evidenceStatus: "grounded" | "under-supported", findingCount: int, confidenceCap: Optional[str], note: Optional[str]}`.

**Why the six-row view is a separate field (binding rationale):** the FROZEN `gate.py:check_scorecard` rejects any `dimensionRatings` entry with empty `findingIds`, so an ungrounded (under-supported) dimension legally **cannot** sit in `dimensionRatings`. B therefore keeps `dimensionRatings` grounded-only and adds `dimensionStatus` as the always-all-6 authoritative view. A renders the six rows from `dimensionStatus` and joins `dimensionRatings` only for the grounded ones.

**Frozen (A must not touch):** `Finding` schema, 6 dimension names, rating scale, `gate.py`, `scoring.py`, `pipeline.py` gate, `registry/indicators.py`, `registry/validate.py`.

---

## 3. The Report: Section Layout

The report is **plain text** to stdout. Every section is deterministic from the scorecard. Sections appear in this fixed order:

```
=================================================================
CATEGORY REPORT: <categoryId>  |  Cycle: <asOf>  |  <timestamp>
=================================================================

OVERALL CATEGORY STATUS
DIMENSION RATINGS
DEMAND / SUPPLY MOMENTUM
ENTITY PANEL
EVIDENCE QUALITY
SOURCES
COVERAGE / SKIP GAPS
```

### 3.1 Header

One line: category id, cycle period (asOf), and the UTC timestamp of the render (from Python `datetime.now(UTC)`). This makes every report instance traceable without an LLM.

### 3.2 Overall Category Status

Renders the judge-produced `categoryStatus` object B adds. Fields:
- `rating` — one of the five plain words (Very strong / Strong / Mixed / Weak / Very weak)
- `direction` — improving / steady / worsening
- `bottleneck` — plain-language label of the binding constraint (e.g. "CUDA ecosystem lock-in")
- `reason` — one-sentence plain rationale

**Graceful degradation (pre-B scorecard):** if `categoryStatus` is absent from the scorecard, render:

```
  Status:    not yet available  (field populated by sub-project B; scorecard predates it)
  Direction: —
  Bottleneck: —
  Reason:    —
```

This is **never** fabricated.

### 3.3 Dimension Ratings

All **six dimensions** are always shown. The six rows are driven by **`sc.dimensionStatus`** (B's authoritative always-all-6 view), **not** by `dimensionRatings`. For each of the six canonical dimension names:
- Read its `DimensionStatus` from `sc.dimensionStatus[dim]`.
- If `evidenceStatus == "grounded"`, **JOIN** `sc.dimensionRatings[dim]` for the rating / direction / confidence / rationale detail and render the full row.
- If `evidenceStatus == "under-supported"`, render the under-supported row (rating shown as `—/under-supported`, plus `findingCount`, any `confidenceCap`, and any `note`).

For a grounded dimension the row carries:
- **Rating** (one of five words, from `dimensionRatings[dim].rating`)
- **Direction** (improving / steady / worsening) with a Unicode arrow (↑ / → / ↓) for scannability
- **Confidence** (low / medium / high)
- **Evidence status** — `grounded` (from `sc.dimensionStatus[dim].evidenceStatus`)
- **Δ vs prior** (if prior scorecard supplied): `↑` if rating improved on the five-point scale, `↓` if worsened, `=` if same, `–` if dimension was absent in prior

For an under-supported dimension the row carries: `—/under-supported`, `findingCount`, `confidenceCap` (if any), `note` (if any), and the Δ note (was it present in prior?).

The five-point scale for Δ comparison: Very strong=5, Strong=4, Mixed=3, Weak=2, Very weak=1.

Coverage summary line at the end: `Coverage: N/6 dimensions grounded; M under-supported`, where N and M are computed by counting `evidenceStatus` values across `sc.dimensionStatus`.

**Graceful degradation (pre-B / legacy scorecard with no `dimensionStatus`):** when `sc.dimensionStatus` is absent or empty (the committed v2/v3 fixtures), fall back to inference — a dimension present in `dimensionRatings` → `grounded` (joined for detail); a dimension absent from `dimensionRatings` → `under-supported` (with `findingCount` counted from `findings`). This is the path the fixture-based tests exercise before B lands.

**Example rendering (v3 scorecard, v2 as prior):**

```
DIMENSION RATINGS  (Δ vs prior cycle: 2026-06 v2)
  momentum              Very strong  ↑ improving    high      grounded      = (same)
  unitEconomics         Strong       → steady       high      grounded      = (same)
  competitiveStructure  Strong       → steady       medium    grounded      ↓ (was Strong, now Strong — 1-step drop context note)
  moat                  Very strong  → steady       high      grounded      = (same)
  bottleneck            —/under-supported  (findings: 0; confidence capped at medium)  Δ: was present in v2
  strategicRisk         —/under-supported  (findings: 0; no indicator mapped)  Δ: absent in prior too

  Coverage: 4/6 dimensions grounded; 2 under-supported
```

### 3.4 Demand / Supply Momentum

Three numbers, each with a one-line plain interpretation and Δ vs prior.

```
DEMAND / SUPPLY MOMENTUM  (Δ vs prior cycle: 2026-06 v2)
  DMI   0.100   Δ −0.040   Demand momentum: slight positive pull; lower than prior cycle
  SMI   0.027   Δ −0.240   Supply momentum: near-flat; sharply lower than prior cycle
  SDGI  0.073   Δ +0.200   Demand outrunning supply (positive gap); gap widened vs prior
                            Interpretation: shortage pressure building; demand side leading
```

**SDGI formula:** `sdgi = dmiContribution − smiContribution`. Computed at render time. Positive = demand outrunning supply (potential shortage). Negative = supply outrunning demand (potential glut). Near zero = balanced.

**Plain interpretation rules (computed, not judged):**

| Condition | Plain label |
|---|---|
| `sdgi > 0.05` | "Demand outrunning supply — shortage pressure forming" |
| `-0.05 <= sdgi <= 0.05` | "Demand and supply roughly balanced" |
| `sdgi < -0.05` | "Supply outrunning demand — glut pressure forming" |

Δ is rendered as the arithmetic difference (current − prior); if prior is absent, Δ column shows `—`.

**Graceful degradation:** if the prior scorecard lacks `demandSupply`, all Δ values are `—`.

### 3.5 Entity Panel

One sub-panel per entity appearing in `findings[].entity` (non-null). Entities are sorted by finding count (descending) then alphabetically. For each entity:

- Entity id (NVDA, AMD, INTC from registry; displayed as the entity value from findings)
- Finding count
- DMI contribution from this entity's findings (sum of `polarityDemand × magnitude` for demand-side findings tagged to this entity, normalised by the entity's finding count)
- SMI contribution similarly
- Up to 3 representative statements (the highest-magnitude findings for this entity), each prefixed with its side and kind

**Example:**

```
ENTITY PANEL
  NVIDIA  (23 findings)
    Demand signal:  +strong   Supply signal:  neutral
    Key signals:
      [demand/measured]  Data Center revenue Q1FY27: record $75.2B (+92% YoY) — NVIDIA 8-K
      [demand/measured]  Gross margin 74.9% — dominant pricing power maintained
      [supply/measured]  Market share declining from 87% (2024) toward 75% (2026E)
  AMD  (12 findings)
    Demand signal:  +moderate   Supply signal:  +slight
    Key signals:
      [demand/measured]  Data Center revenue Q1 2026: $5.775B (+57% YoY) — AMD IR (primary)
      [supply/observed]  MI350 positioned as matching GB200 at lower cost
  intel  (7 findings)
    Demand signal:  +slight   Supply signal:  +slight
    Key signals:
      [demand/measured]  DCAI revenue Q1 2026: $5.1B (+22% YoY)
      [supply/observed]  Crescent Island GPU sampling H2 2026 (air-cooled, 480GB)
```

### 3.6 Evidence Quality

One line per dimension showing finding counts broken down by tier and kind. A dimension marked `under-supported` in `sc.dimensionStatus` (or, on legacy fixtures, absent from `dimensionRatings`) shows `0 findings (under-supported)`.

```
EVIDENCE QUALITY  (per dimension)
  momentum              18 findings  (primary: 6, secondary: 12)  [grounded]
  unitEconomics         10 findings  (primary: 4, secondary: 6)   [grounded]
  competitiveStructure   7 findings  (primary: 2, secondary: 5)   [grounded]
  moat                   5 findings  (primary: 3, secondary: 2)   [grounded]
  bottleneck             0 findings  ——  [under-supported]
  strategicRisk          0 findings  ——  [under-supported]

  Total: 40 findings  (primary: 15, secondary: 25)
```

Finding-to-dimension mapping: A finding is attributed to a dimension if its `indicatorId` maps to that dimension in the indicator registry. Findings whose `indicatorId` does not map to any dimension are shown in a catch-all `(unattributed)` line. The per-dimension finding count may also be read directly from `sc.dimensionStatus[dim].findingCount` when `dimensionStatus` is present (post-B); on legacy scorecards A counts from `findings` via the registry mapping. The tier breakdown (primary/secondary) is always computed from `findings[].evidence[]` since `dimensionStatus` does not carry tier counts.

**Note on sourcing `indicatorId → dimension` mapping:** `report.py` will load the indicator registry (via `IndicatorRegistry.load("registry/indicators.json")`) to resolve mappings — this is a pure read at render time, no write.

### 3.7 Sources

Derived from `findings[].evidence[]`, deduplicated by URL. Each source is shown with its tier, the latest date cited for it, and its domain/name.

```
SOURCES  (19 unique; ranked primary-first then by date)
  [primary]    sec.gov                 2026-05-20   NVIDIA Form 8-K Q1FY27
  [primary]    ir.amd.com              2026-05-05   AMD Q1 2026 press release
  [primary]    newsroom.intel.com      2025-10-14   Intel Crescent Island announcement
  [secondary]  siliconanalysts.com     2026-04-13   AMD vs NVIDIA market share 2026
  [secondary]  finance.yahoo.com       2026-04-23   Intel Q1 2026 earnings coverage
  ...
```

The `Scorecard.sources: list[str]` field is used as a cross-reference to flag any source URL listed there but not appearing in findings evidence (which would be a coverage anomaly worth noting).

### 3.8 Coverage / Skip Gaps

Surfaces dimensions and indicators that expected coverage but received none this cycle. Until sub-project C ships a formal coverage manifest, this section reports:

- Dimensions with zero findings (under-supported)
- Any `Scorecard.sources` URLs not matched in findings evidence (orphan source references)

```
COVERAGE / SKIP GAPS
  bottleneck     — 0 findings this cycle; dimension under-supported
  strategicRisk  — 0 findings this cycle; dimension under-supported
  (No orphan source references detected)
```

When C ships a coverage manifest, A will additionally surface: expected indicators with zero findings. The section renders identically either way — the manifest just makes it more specific.

---

## 4. Architecture: `gpu_agent/report.py`

`report.py` is a **pure projection** module. No LLM call, no network, no store writes.

### 4.1 Unit decomposition

Each function is small, testable, and takes plain arguments (no global state).

```
gpu_agent/report.py
│
├── load_scorecard(path: Path) -> Scorecard
│     Parses JSON from path into the Pydantic Scorecard model. Raises ValueError with
│     a clear message on parse failure.
│
├── find_prior(store_dir: Path, sc: Scorecard) -> Path | None
│     Scans store_dir/<sc.categoryId>/ for files matching the pattern
│     <asOf>-v*.json, excludes the current file, returns the most-recent
│     previous version (by version suffix). Returns None if none found.
│     Pure filesystem read; no LLM.
│
├── compute_sdgi(sc: Scorecard) -> float
│     Returns sc.demandSupply.dmiContribution − sc.demandSupply.smiContribution.
│     Uses a stored sdgi field if present (B may write it); falls back to computing
│     it. This function is trivially tested.
│
├── render_header(sc: Scorecard, render_ts: str) -> str
│     One-line header block.
│
├── render_overall_status(sc: Scorecard) -> str
│     Reads sc.categoryStatus (if present); graceful degradation if absent.
│
├── render_dimensions(sc: Scorecard, prior: Scorecard | None) -> str
│     Iterates the 6 canonical DIMENSIONS list from scorecard.py.
│     For each: reads sc.dimensionStatus[dim] (B's authoritative six-row view).
│       grounded      → JOIN sc.dimensionRatings[dim] for rating/direction/confidence
│       under-supported → render —/under-supported + findingCount/confidenceCap/note
│     evidenceStatus comes from dimensionStatus, NOT dimensionRatings.
│     Legacy fallback (no dimensionStatus): present in dimensionRatings → grounded;
│       absent → under-supported (count from findings). Computes Δ from prior if supplied.
│
├── render_dmi_smi_sdgi(sc: Scorecard, prior: Scorecard | None) -> str
│     Reads sc.demandSupply. Calls compute_sdgi(). Computes Δ against prior.
│     Applies the plain-interpretation rules (static dict, no LLM).
│
├── render_entity_panel(sc: Scorecard) -> str
│     Groups sc.findings by entity (non-null). For each entity: count, demand/supply
│     signal level, up to 3 top findings by magnitude.
│
├── render_evidence_quality(sc: Scorecard, registry: IndicatorRegistry) -> str
│     Groups sc.findings by dimension via registry indicatorId→dimension mapping.
│     Counts by tier. Renders per-dimension and totals.
│
├── render_sources(sc: Scorecard) -> str
│     Builds a deduplicated list from sc.findings[].evidence[].
│     Sorts: primary first, then by date descending.
│     Cross-references sc.sources for orphans.
│
├── render_coverage_gaps(sc: Scorecard) -> str
│     Reports under-supported dimensions and orphan source refs.
│
└── render_report(sc: Scorecard, prior: Scorecard | None,
                  registry: IndicatorRegistry,
                  render_ts: str | None = None) -> str
      Calls every render_* function in section order, joins with blank lines.
      render_ts defaults to datetime.now(UTC).isoformat() if not supplied.
      This is the top-level entry point; all other functions are composable units.
```

### 4.2 Registry dependency

`render_evidence_quality` is the only function that needs the indicator registry (for the `indicatorId → dimension` mapping). The registry is loaded once in the CLI handler and passed in. Tests can supply a minimal stub registry.

### 4.3 No shared mutable state

All functions are pure or nearly pure (the only "impure" call is `datetime.now()`, which is injectable via the `render_ts` parameter). This makes every unit trivially testable over fixtures.

---

## 5. CLI Surface

New subcommand added to `gpu_agent/cli.py`, following the exact pattern of `extract`, `judge`, `cycle-plan`.

```
gpu-agent report \
    --scorecard <path>        # required: path to the scorecard JSON file
    [--prior <path>]          # optional: explicit path to prior-cycle scorecard
    [--store <dir>]           # optional: store root; used to auto-discover prior
                              #   if --prior is not given. Default: "store"
    [--out <file>]            # optional: write report to file instead of stdout
    [--registry <path>]       # optional: indicator registry. Default: "registry/indicators.json"
    [--no-prior]              # flag: suppress prior-cycle lookup entirely
```

**Prior-discovery logic (deterministic):**
1. If `--prior` is given, use it. No auto-discovery.
2. If `--no-prior` is given, run without prior. Δ columns show `—`.
3. Otherwise, call `find_prior(store_dir, sc)` to auto-discover. If nothing found, run without prior.

**Handler signature:**

```python
def _report(args) -> int:
    sc = load_scorecard(Path(args.scorecard))
    prior = None
    if not args.no_prior:
        if args.prior:
            prior = load_scorecard(Path(args.prior))
        else:
            prior_path = find_prior(Path(args.store), sc)
            if prior_path:
                prior = load_scorecard(prior_path)
    registry = IndicatorRegistry.load(args.registry)
    text = render_report(sc, prior, registry)
    if args.out:
        Path(args.out).write_text(text, "utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0
```

This follows the same shape as `_cycle_plan`, `_judge`, `_extract`.

---

## 6. Graceful-Degradation Behaviour (Pre-B Scorecards)

A must be testable and useful on the committed v2/v3 fixtures before B ships. The degradation rules are:

| Situation | Rendering |
|---|---|
| `categoryStatus` absent | Section shows "not yet available" label; no fabrication |
| `dimensionStatus` absent or empty (legacy v2/v3 fixtures) | Per dimension: present in `dimensionRatings` → infer `grounded` (joined for detail); absent from `dimensionRatings` → infer `under-supported`, with `findingCount` counted from `findings` |
| `dimensionStatus` present but a dimension's `evidenceStatus == "under-supported"` | Rendered as `—/under-supported` row with `findingCount` / `confidenceCap` / `note` from `dimensionStatus[dim]`; **never** joined to `dimensionRatings` (it isn't there) |
| `demandSupply.sdgi` absent | Computed at render time as `dmiContribution − smiContribution` |
| Prior scorecard not found / not supplied | All Δ columns render `—`; no error |
| `finding.entity` is null | Finding excluded from entity panel (not an error) |
| `finding.indicatorId` maps to no dimension in registry | Finding counted in `(unattributed)` bucket in evidence quality |

These rules make A robustly testable on every committed fixture (v1, v2, v3) today.

---

## 7. Testing Strategy

### 7.1 Principles

- **Deterministic:** all tests run against committed scorecard fixtures (`store/chips.merchant-gpu/2026-06-v2.json`, `2026-06-v3.json`). No LLM call, no network.
- **TDD:** every test is written and verified to fail before the implementation is written.
- **Full suite stays green:** baseline is **117 passed, 3 skipped**. No regressions.
- **Unit first, then integration:** render functions are tested independently, then `render_report` as integration, then the CLI handler.

### 7.2 Test file: `tests/test_report.py`

**Unit tests (render functions):**

- `test_compute_sdgi` — DMI 0.100, SMI 0.027 → SDGI 0.073 (numeric precision to 6 dp)
- `test_compute_sdgi_stored_field` — if `sdgi` field is present, use it directly (B's value)
- `test_render_overall_status_absent` — scorecard without `categoryStatus` → contains "not yet available"
- `test_render_overall_status_present` — scorecard with `categoryStatus` → rating appears in output
- `test_render_dimensions_all_six_always` — v3 scorecard (4 of 6 grounded) → all 6 appear; `bottleneck` and `strategicRisk` contain "under-supported"
- `test_render_dimensions_reads_dimensionstatus_when_present` — post-B: evidenceStatus read from `dimensionStatus`, not `dimensionRatings` (xfail until B ships)
- `test_render_dimensions_grounded_label` — legacy fixture: a dimension present in `dimensionRatings` infers `grounded`
- `test_render_dimensions_delta` — v3 vs v2 prior: `bottleneck` was present in v2, absent in v3 → Δ note appears
- `test_render_dmi_smi_sdgi_no_prior` — Δ column is `—` when no prior supplied
- `test_render_dmi_smi_sdgi_with_prior` — v3 vs v2: arithmetic Δ correct
- `test_render_dmi_smi_sdgi_interpretation` — SDGI 0.073 → "Demand outrunning supply" in output
- `test_render_entity_panel_entities_present` — v3 scorecard → nvidia, amd, intel panels all appear
- `test_render_entity_panel_null_entity_excluded` — findings with null entity don't appear in panel
- `test_render_evidence_quality_per_dimension` — finding counts match expected totals per dimension
- `test_render_evidence_quality_unattributed` — findings with unmapped indicatorId appear in `(unattributed)`
- `test_render_sources_primary_first` — primary sources sort before secondary
- `test_render_coverage_gaps_undersupported` — v3 → bottleneck and strategicRisk appear in gap list
- `test_find_prior_discovers_previous_version` — given v3 path, finds v2
- `test_find_prior_returns_none_if_only_version` — single file → returns None
- `test_render_report_deterministic` — same scorecard + prior → byte-identical output on two calls

**CLI integration tests (in `tests/test_cli_report.py`):**

- `test_cli_report_stdout` — `gpu-agent report --scorecard store/chips.merchant-gpu/2026-06-v3.json` → exit 0, output contains all section headers
- `test_cli_report_with_prior` — `--prior store/chips.merchant-gpu/2026-06-v2.json` → Δ column shows values
- `test_cli_report_no_prior_flag` — `--no-prior` → Δ column shows `—` throughout
- `test_cli_report_auto_discover_prior` — `--store store` → v2 auto-discovered as prior for v3
- `test_cli_report_out_file` — `--out <tmp>` → file written, stdout shows "wrote <path>"
- `test_cli_report_bad_scorecard` — nonexistent path → exit non-zero with clear error message

### 7.3 Fixture strategy

Tests import `Scorecard.model_validate(json.loads(Path("store/chips.merchant-gpu/2026-06-v3.json").read_text()))` directly. No new fixture files needed — the committed scorecards are the test fixtures. A minimal `Scorecard` fixture with `categoryStatus` and `evidenceStatus` fields is constructed inline in the relevant test (simulating B's output).

---

## 8. Run-Cycle Skill Update

After A is built and merged, `.claude/skills/run-cycle/SKILL.md` gains a **report step** at the end of the cycle:

```
After the scorecard is written to the store, run:
  gpu-agent report --scorecard <path> --store store [--out <report_path>]
and display or save the report.
```

This step is additive (no existing step changes). The skill continues to work without it if A is not yet built (it simply omits the report step).

---

## 9. Acceptance Criteria

A is done when every item below is checked:

- [ ] `gpu_agent/report.py` exists; all render functions are pure/deterministic; no LLM call, no network
- [ ] `gpu-agent report --scorecard store/chips.merchant-gpu/2026-06-v3.json` prints a complete report with all 8 sections
- [ ] All 6 dimensions appear in every report (driven by `dimensionStatus`); `bottleneck` and `strategicRisk` show `—/under-supported` on v3
- [ ] `categoryStatus` section shows "not yet available" on v2/v3 (pre-B) scorecards
- [ ] SDGI is computed correctly as `dmiContribution − smiContribution` when not stored
- [ ] Δ-vs-prior values are arithmetically correct when v2 is the prior
- [ ] Per-entity panel shows nvidia / amd / intel from v3 findings
- [ ] Same scorecard + prior → identical report on repeated runs (deterministic)
- [ ] All tests in `tests/test_report.py` and `tests/test_cli_report.py` pass
- [ ] Full suite remains **117+ passed, 3 skipped** (no regressions)
- [ ] No new fields written to the scorecard; no modifications to frozen files
- [ ] `.claude/skills/run-cycle/SKILL.md` has a report step at the end of the cycle

---

## 10. Cross-Seam Concerns for Sub-projects B and C

### What A needs from B (binding on B's spec)

B adds the following fields to the `Scorecard` model as **optional** (so pre-B scorecards remain valid). This is B's actual, agreed contract (umbrella §2.1):

| Field | Type | Needed by A |
|---|---|---|
| `dimensionStatus` | `dict[str, DimensionStatus]` optional; `DimensionStatus = {evidenceStatus: "grounded" \| "under-supported", findingCount: int, confidenceCap: Optional[str], note: Optional[str]}` — always populated with **all 6** dimension names by `build_scorecard` | Section 3.3 — the authoritative six-row dimension view + evidence status; Section 3.6 — per-dim finding count |
| `categoryStatus` | `Optional[{rating: str, direction: str, bottleneck: str, reason: str}]` | Section 3.2 — overall status rendering |
| `demandSupply.sdgi` | `Optional[float]` on `DemandSupply` | Section 3.4 — A prefers stored value if present, else computes |
| `demandSupply.sdgiDirection` | `Optional[Literal["demand-led","supply-led","balanced"]]` on `DemandSupply` | Section 3.4 — A may render B's direction label when present |

**B guarantees all 6 dimensions in `dimensionStatus`; `dimensionRatings` is grounded-only** (only dims the judge grounded, each citing ≥1 finding). The FROZEN `gate.py` forbids an empty-`findingIds` entry in `dimensionRatings`, so an under-supported dimension cannot live there — it lives in `dimensionStatus`. A's render-all-six logic reads `dimensionStatus` post-B, and falls back to `dimensionRatings`-presence inference only for legacy fixtures.

**There is NO `DimensionRating.evidenceStatus` field** — evidence status is read exclusively from `dimensionStatus[dim].evidenceStatus`.

### What A provides to C

A's `render_coverage_gaps` section is the user-facing surface where C's manifest will show its effect. When C lands, the gap list becomes: "expected N indicators; M have zero findings." A's coverage section is designed to accept an optional manifest parameter in a future revision without changing the overall structure.

### Notes for the orchestrator (seam review)

- A is built **after B** (umbrella §1 build order: B → A → C). B's optional fields must exist in the `Scorecard` schema before A's implementation begins.
- A must not introduce any import from B's new files that could break if B is not yet merged. The optional-field degradation spec above ensures A builds cleanly even without B.
- A does not touch `registry/indicators.json` — it only reads it. Any new indicator B adds (for `strategicRisk`) will automatically appear in A's evidence-quality mapping once B is merged.
