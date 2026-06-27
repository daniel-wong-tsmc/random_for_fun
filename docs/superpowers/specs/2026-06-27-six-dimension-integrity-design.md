# Sub-project B — Six-dimension integrity (SPEC)

- **Date:** 2026-06-27
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **Owner:** Sub-project **B** of the Output & Coverage Overhaul (umbrella:
  [`2026-06-27-output-coverage-decomposition-design.md`](2026-06-27-output-coverage-decomposition-design.md)).
  The umbrella §2 (shared seams) and §3 (B's scope) **bind** this spec; it restates the seams it touches.
- **References:** [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) Part 17 (rate without inventing
  numbers; category status is "an analyst's read of its six judgments, **not** an average"; DMI/SMI/**SDGI**),
  Part 18 #8 ("**bend, don't break** — missing → flagged *under-supported* + confidence-capped, never dropped"; the
  small sacred contract), Part 33 (schema evolution — additive thaw), Part 35 ("inputs degraded" surface state).

---

## 1. Context & problem

A live `category:chips.merchant-gpu` run (`store/chips.merchant-gpu/2026-06-v3.json`) rated **only 4 of 6
dimensions** — `bottleneck` and `strategicRisk` were silently **absent** from `dimensionRatings`, yet the cycle
reported "complete." Two distinct failures produced this:

1. **`bottleneck` was groundable but ungrounded this cycle** — its indicator (`S10`, whole-chain inventory) exists
   and maps to `bottleneck`, but the gather surfaced **zero** `S10` findings, so the judge had nothing to rate and
   silently omitted the dimension.
2. **`strategicRisk` is structurally ungroundable** — **no indicator in `registry/indicators.json` maps to it**, so
   the 6th dimension can *never* be grounded. It is invisible by construction.

Separately, the scorecard carries no judge-produced **overall category status** (Part 17's headline) and no
**Supply-Demand Gap** (`sdgi = dmi − smi`), both of which the executive surface (A) needs.

The bug is silent omission. Part 18 #8 is explicit: a missing ability **degrades to `under-supported` +
confidence-capped, it is never dropped.** B makes every scorecard carry all six dimensions honestly.

## 2. Goal / non-goals

**Goal.** Every scorecard B helps assemble:
- carries an explicit status for **all six** dimensions; an ungrounded one is `under-supported` + confidence-capped,
  **never omitted**;
- can in principle **ground `strategicRisk`** (a registry indicator now maps to it);
- carries a judge-produced **overall `categoryStatus`** (judgment, not a code rollup);
- carries **`demandSupply.sdgi`** = `dmi − smi` with a direction label (a code-computed rollup).

All changes are **additive and optional** (Part 33): existing fields/semantics are untouched, so committed scorecards
and fixtures still validate, and the full suite stays green (baseline **117 passed, 3 skipped**).

**Non-goals.** No change to: the 6 dimension **names**, the `Finding` schema, the rating scale, `gate.py`,
`scoring.py:zscore`, the `pipeline.py` Part-7 gate **behavior**, or `registry/validate.py` (all **frozen**, §2.4).
No per-metric **source-hint** fields (that is C, umbrella §2.2). No coverage manifest (C). No report renderer (A).

## 3. Architecture & the seams B touches (restating the umbrella)

```
findings ──> build_briefing ──> judge (BRAIN: 6 dim ratings + categoryStatus) ──> JudgmentBundle
                                                                                       │
                                              build_scorecard (CODE):                  │
                                              • dmi,smi = dmi_smi_contribution(...)     │
                                              • sdgi = dmi − smi  (+ direction)         ▼
                                              • dimensionStatus: enforce ALL 6 ──> Scorecard ──> gate (FROZEN, grounded only)
                                              • categoryStatus passthrough              │
                                                                                       ▼
                                                                                  JsonStore
```

- **Frozen, untouched:** `Finding`, the 6 dimension names, the rating scale, `gate.py:check_scorecard`,
  `scoring.py` (`zscore`, `dmi_smi_contribution`), `registry/validate.py`. All additions sit *around* them.
- **Evolved additively (B's mandate):** the `Scorecard` model (new **optional** fields only), the judgment
  prompt/briefing/result (request all 6 + the overall status), and the indicator **data** in
  `registry/indicators.json`. The sp2-era freeze on `judgment/*.py` was sp2-scoped and does not bind B.
- **Registry ownership (umbrella §2.2):** B owns indicator **definitions + dimension mapping** only. B does **not**
  add `defaultSourceHint`/`accessMethod`/`tier`/`cost` fields — that is C. B lands first; C rebases onto B's set.

### The binding frozen-gate constraint (the crux — flagged)
`gate.py:check_scorecard` iterates `sc.dimensionRatings` and **errors on any rating with empty `findingIds`** (`"…:
rating cites no findings"`) and on any cited id not present in `findings`. An `under-supported` dimension has **zero**
supporting findings, so **it cannot live in `dimensionRatings`** without failing the frozen gate. Therefore the
umbrella's "all six present in `dimensionRatings`" is reconciled as: **all six present in the scorecard's
dimension *view***, where grounded dimensions stay in the gate-validated `dimensionRatings` and the full six-row
status (including the ungrounded ones) lives in a **new additive field** the frozen gate ignores. This keeps
`gate.py` untouched and every committed fixture valid. (See §4.1 / §4.6.)

## 4. Resolved decisions

### 4.1 Scorecard additive fields (exact fields + defaults)

All new fields are **optional with defaults**, so old fixtures/scorecards that lack them validate unchanged. The
`Scorecard` and `DemandSupply` models use pydantic's default config (extra ignored), so additions are safe.

**(a) Per-dimension evidence status — the all-six honesty record.** New model + field:

```python
class DimensionStatus(BaseModel):
    evidenceStatus: Literal["grounded", "under-supported"]
    findingCount: int = 0
    confidenceCap: Optional[Literal["low", "medium"]] = None  # set when under-supported
    note: str = ""                                            # one-line, plain-language reason

class Scorecard(BaseModel):
    ...                                          # all existing fields unchanged
    dimensionStatus: dict[str, DimensionStatus] = Field(default_factory=dict)
    categoryStatus: Optional["CategoryStatus"] = None
```

`dimensionStatus` is **authoritative for the six-row view** and is **always populated with all six dimension
names** by `build_scorecard` (code backstop, §4.2). For a grounded dim: `evidenceStatus="grounded"`,
`findingCount=len(rating.findingIds)`, `confidenceCap=None`. For an ungrounded dim: `evidenceStatus="under-supported"`,
`findingCount=0`, `confidenceCap="low"`, `note` e.g. `"no findings mapped to strategicRisk this cycle"`. A (the
report) renders six rows from `dimensionStatus`, joining `dimensionRatings[dim]` for rating detail on grounded rows.

Default `{}` ⇒ pre-B fixtures (which lack the field) still validate; A treats an empty `dimensionStatus` as "legacy
scorecard, render what's in `dimensionRatings`."

**(b) Overall category status — judge-produced headline.** New model + the `categoryStatus` field above:

```python
class CategoryStatus(BaseModel):
    rating: Literal["Very strong", "Strong", "Mixed", "Weak", "Very weak"]  # the frozen 5-word scale
    direction: Literal["improving", "steady", "worsening"]
    bottleneck: str   # the dimension name that is the binding constraint right now (one of the 6)
    reason: str       # one plain-language line (Part 17)
```

Default `None` ⇒ legacy scorecards validate; A shows "overall status: not assessed" if absent. This is **judgment**
produced by the judge brain (§4.2) — code never derives it (that would be the "average" Part 17 forbids).

**(c) `demandSupply.sdgi` + direction.** Two optional fields on `DemandSupply`:

```python
class DemandSupply(BaseModel):
    dmiContribution: float
    smiContribution: float
    anchors: dict[str, float] = Field(default_factory=dict)
    sdgi: Optional[float] = None
    sdgiDirection: Optional[Literal["demand-led", "supply-led", "balanced"]] = None
```

`build_scorecard` computes `sdgi = dmiContribution − smiContribution`; direction by a small dead-band:
`sdgi > +ε → "demand-led"` (shortage forming), `sdgi < −ε → "supply-led"` (glut forming), else `"balanced"`
(ε e.g. `0.02`). A **code-computed rollup** (Part 17 "measured rollups computed in code"), never the agent.

**Tolerance check.** `build_scorecard`, `gate.py`, and `JsonStore` all tolerate the additions: the gate reads only
`findings`, `dimensionRatings`, and `demandSupply.anchors` (it ignores `dimensionStatus`, `categoryStatus`, `sdgi`);
`JsonStore.append` does `model_dump_json` (serializes whatever is present). The one test that compares `demandSupply`
by **exact equality** (`test_golden_integration`) must have its golden fixture's `demandSupply` updated to include the
computed `sdgi`/`sdgiDirection` — an expected-output fixture refresh, called out in the plan.

### 4.2 Who sets what (doctrine — Part 17/18)

| Artifact | Producer | Mechanism |
|---|---|---|
| The six dimension **ratings** (grounded) | **judge BRAIN** | judge cites ≥1 finding per rated dim; gate-validated |
| The overall **`categoryStatus`** | **judge BRAIN** | new field in `JudgmentResult`; judgment, not a rollup |
| **`sdgi`** + direction | **CODE** | `build_scorecard` computes `dmi − smi` |
| **All-six presence** (`dimensionStatus`) | **CODE backstop** | `build_scorecard` fills every dim; ungrounded → `under-supported` + cap |
| Per-dimension / overall **confidence cap** | **CODE backstop** | under-supported dim → `confidenceCap="low"`; if any under-supported, overall scorecard `confidence` is capped at `medium` (high → medium, basis annotated) |

The agent never sets a computed number; code never invents a rating or the headline. The judge **attempts** all six
and **omits** any it cannot ground (cite a finding for); code then fills the omissions as `under-supported`. This
keeps the frozen gate green (every dim in `dimensionRatings` cites a real finding) while guaranteeing six-dim
coverage in `dimensionStatus`.

### 4.3 `strategicRisk` indicator — definition and SCORING vs JUDGMENT-ONLY

**Definition (suggested default per umbrella §2.2).** Add to `registry/indicators.json` indicator(s) mapping to
`strategicRisk`:
- `exportControlExposure` — "Export-control / China-revenue exposure" (share of revenue exposed to export-control or
  China end-markets).
- `customerConcentration` — "Customer & supplier concentration" (revenue share from top customers / single-source
  suppliers).

**Decision: JUDGMENT-ONLY (`scoring: false`), excluded from DMI/SMI. Recommended and adopted.** Justification:
1. **Part 17 says so.** Strategic risk — geopolitical/regulatory exposure, concentration — is the archetypal
   "judgment call you can't measure" ("How risky is it? You can't put a tape measure on these"). Forcing it into the
   weighted DMI/SMI momentum sum would "dress a judgment up as a measurement."
2. **It would corrupt comparability — the very thing this overhaul fixes.** DMI/SMI are weighted sums over scoring
   indicators; adding a new weighted indicator perturbs every category's index and breaks run-to-run trendability
   (the umbrella's motivating defect: DMI swinging 0.067 → 0.140 → 0.100). A judgment-only indicator leaves DMI/SMI
   untouched.
3. **It is a structural/overlay signal, not a demand/supply momentum push** — Part 17 keeps price/structural-family
   findings out of DMI/SMI as a confirmation overlay; risk belongs there.

**How `scoring: false` threads the existing frozen code (verified):**
- `scoring.py:dmi_smi_contribution` skips `not spec.scoring` ⇒ the indicator never enters DMI/SMI. ✔ (frozen, untouched)
- `registry/validate.py` and `IndicatorRegistry.validate_against` **skip** non-scoring indicators (`if not
  spec.scoring: continue`) ⇒ a `weight: 0.0`, `scoring: false` indicator with `dimension: "strategicRisk"` passes
  validate; the zero-weight and taxonomy-dimension checks apply only to scoring indicators. ✔ (frozen, still passing)
- `briefing.py:build_briefing` groups findings by `spec.dimension` **regardless of `scoring`** ⇒ once `strategicRisk`
  findings exist, they form a `strategicRisk` anchor and the **judge can rate the dimension** (grounded). ✔
- `strategicRisk` is already a taxonomy dimension (`docs/taxonomy.json`), so the mapping is valid.

Registry rows use **only existing `IndicatorSpec` fields** (the model is `extra="forbid"`): `label`, `dimension`,
`polarityTrack`, `side` (set `"structural"`), `weight: 0.0`, `kind: "qualitative"`, `scoring: false`,
`comparability`. **No source-hint fields** (C's territory).

Wiring these indicators into the merchant-gpu assignment's `metrics` (so the gather targets them) is **optional and
deferred to C's coverage manifest**; B only makes `strategicRisk` *groundable*. Until findings arrive it remains
`under-supported` — which is exactly the honest behavior B guarantees.

### 4.4 The "until C lands" rule (umbrella §2.3)

B uses the **simple rule**: a dimension with **zero supporting findings** (equivalently, absent from the judge's
grounded ratings) ⇒ `under-supported`. No coverage manifest is read. When C lands, "expected vs actually-grounded"
can tighten the rule without reworking B (the `dimensionStatus` shape already carries `note`/`confidenceCap`). This
keeps B shippable **before** C (umbrella build order B → A → C).

### 4.5 Registry ownership (umbrella §2.2)

B edits `registry/indicators.json` for **indicator definitions + dimension mapping only** (the `strategicRisk` rows
above). B does **not** touch override semantics beyond what already exists and adds **no** per-metric source-hint
fields. `registry/validate.py` stays frozen and passing.

### 4.6 The frozen-gate reconciliation (flagged risk)

Resolved in §3/§4.1: under-supported dimensions live in the **new `dimensionStatus`** field, not in the gated
`dimensionRatings`. This honors the umbrella intent ("all six always present, never dropped") **and** leaves
`gate.py` byte-for-byte frozen. The alternative — putting all six in `dimensionRatings` — is **rejected** because it
forces either a fake `findingIds` (inventing evidence, violating Part 18) or a gate edit (violating the freeze).

## 5. Data flow (end to end)

1. **Briefing/judge prompt** (`briefing.py` unchanged in logic; `prompt.py` evolved): the system prompt instructs the
   judge to (a) rate **every** dimension for which it can cite ≥1 finding, (b) **omit** any dimension it cannot
   ground, and (c) emit one overall `categoryStatus {rating, direction, bottleneck, reason}`.
2. **`JudgmentResult`** gains `categoryStatus: CategoryStatus` (the model is `extra="forbid"`, so the field is added
   explicitly). `aggregate()` selects the `categoryStatus` from the **representative sample** (the same sample whose
   ratings best agree with the majority winners — reusing `_representative_index`) and carries it on `JudgmentBundle`.
   A light judge-layer check (not `gate.py`) asserts `categoryStatus.bottleneck ∈ DIMENSIONS`.
3. **`build_scorecard`** (`pipeline.py`): computes `dmi, smi` (unchanged frozen call), then `sdgi`/`sdgiDirection`;
   builds `dimensionStatus` for **all six** `DIMENSIONS` (grounded if in `ratings`, else `under-supported` + cap);
   caps overall `confidence` to `medium` if any dim under-supported; passes `categoryStatus` through. Then runs the
   **frozen** `check_scorecard(sc)` — which sees only the grounded `dimensionRatings` and passes as before.
4. **CLI** (`cli.py`): `_judge` writes a new `status.json` (the `categoryStatus`); `_pipeline` passes
   `bundle.categoryStatus` into `build_scorecard`; `_build_from_fixtures` (the `run` path) loads an **optional**
   `status.json` like it already loads `narrative.json`.
5. **`JsonStore.append`** serializes the enriched scorecard unchanged.

## 6. Error handling / graceful degradation (Part 18 #8, Part 35)

- **Ungrounded dimension** → `dimensionStatus[dim] = under-supported, confidenceCap="low", note=…`; never dropped,
  never faked. Surfaces as "inputs degraded" for A.
- **Any under-supported dimension** → overall scorecard `confidence` level capped at `medium`.
- **Judge omits a groundable dim** (e.g. `bottleneck` with zero findings this cycle) → handled identically; honest.
- **Malformed `categoryStatus`** (bad `bottleneck`, missing fields) → judge-layer `JudgmentError`, resample budget
  applies (reusing the existing resample loop); never written half-formed.
- **`strategicRisk` with no findings** → `under-supported` (the expected steady state until the gather targets it).
- The frozen gate continues to reject invented values, dashboard self-reference, and anchor-contradicting ratings —
  unchanged.

## 7. Testing strategy (TDD, additive, suite stays green)

New/updated tests (red → green, each commit keeps the **full** suite green):
- **Schema (`test_scorecard_schema.py`):** `DimensionStatus`, `CategoryStatus`, and `DemandSupply.sdgi/sdgiDirection`
  round-trip; a **pre-B** scorecard JSON (no new fields) still validates (defaults apply).
- **`build_scorecard` (`test_pipeline.py`):** with one grounded dim, output has **all six** in `dimensionStatus`
  (1 grounded, 5 `under-supported` + `confidenceCap="low"`); `sdgi == dmi − smi` with correct direction; overall
  confidence capped to `medium`; the frozen gate still passes (grounded `dimensionRatings` only). A contradiction
  case still raises `GateError`.
- **Judge (`test_judge_findings.py` / `test_judgment_*`):** `JudgmentResult`/`JudgmentBundle` carry `categoryStatus`;
  `aggregate` selects it from the representative sample; a bad `categoryStatus.bottleneck` raises `JudgmentError`.
- **Prompt (`test_judgment_prompt.py`):** the system prompt requests all six + the overall status and says "omit a
  dimension you cannot ground."
- **Registry (`test_registry_*`):** the new `strategicRisk` indicators load; `validate_against`/`validate_assignment`
  still pass (non-scoring skipped); `dmi_smi_contribution` over `strategicRisk` findings is **unchanged** (excluded);
  `build_briefing` over a `strategicRisk` finding produces a `strategicRisk` anchor (now groundable).
- **Golden (`test_golden_integration.py`):** update `fixtures/golden/scorecard.json` `demandSupply` to include
  `sdgi`/`sdgiDirection`; add optional `fixtures/golden/status.json`; the run produces a six-row `dimensionStatus`.
- **CLI (`test_cli_judge.py`):** `judge` writes `status.json`; `run`/`pipeline` thread it through.

## 8. Acceptance criteria

1. Every scorecard B assembles has **all six** dimension names in `dimensionStatus`; any ungrounded one is
   `under-supported` + `confidenceCap` set, **never omitted**.
2. `registry/indicators.json` contains at least one `strategicRisk`-mapped indicator; it is `scoring: false`
   (judgment-only) and **does not change** any DMI/SMI value; `registry/validate.py` passes unchanged.
3. The scorecard carries a judge-produced `categoryStatus {rating, direction, bottleneck, reason}`; code does not
   derive it.
4. `demandSupply.sdgi == dmiContribution − smiContribution` with a correct direction label, computed in code.
5. `gate.py`, `scoring.py`, `registry/validate.py`, the 6 names, the `Finding` schema, and the rating scale are
   **untouched**; committed fixtures still validate.
6. The full suite is green (baseline **117 passed, 3 skipped**, plus the new tests).

## 9. Out of scope

The report renderer (A), the coverage manifest + per-metric source inventory (C), wiring `strategicRisk` indicators
into assignment `metrics`/gather targeting (C), and any change to the frozen contract.
