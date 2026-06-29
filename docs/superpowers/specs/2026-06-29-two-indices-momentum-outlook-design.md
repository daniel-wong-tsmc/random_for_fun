# Two indices — Momentum vs Outlook (sub-project 4-3) — design

- **Date:** 2026-06-29
- **Status:** Draft for review (the third piece of sub-project 4)
- **Author:** brainstorming session (superpowers workflow)
- **Parent:** sub-project-4 umbrella
  [`2026-06-27-daily-monitor-decomposition-design.md`](2026-06-27-daily-monitor-decomposition-design.md) §4.4;
  the human-output target [`2026-06-29-human-market-brief-design-target.md`](2026-06-29-human-market-brief-design-target.md)
  (the NOW-vs-NEXT divergence is the 4-3 deliverable); charter Part 17 (rating; DMI/SMI/**SDGI**; numbers only
  from gated findings), Part 33 (additive evolution), Part 29 (no silent drops). Builds additively on **B**
  (`dimensionStatus`/`sdgi` machinery + additive-field discipline) and **4-2** (the `cadenceHorizon` tags +
  `IndicatorHorizons`).
- **Depends on:** 4-1 (merged), 4-2 (merged — the horizon tags + accessor). **Feeds:** 4-5 (the brief renders
  the two indices + the divergence); 4-4 (once it produces leading findings, Outlook becomes live).

---

## 0. What 4-3 is — and what it is not

4-3 adds **two horizon-split indices** to the scorecard, computed **in code** from the cycle's gated findings:

- **Momentum** (trailing) = the weighted demand/supply push of `lagging` + `coincident` findings.
- **Outlook** (forward) = the weighted demand/supply push of `leading` findings.

Each carries a demand track, a supply track, and an **SDGI = demand − supply** with a direction
(`demand-led | supply-led | balanced`). On top sits a **divergence verdict** that names the case the system
exists to catch: **trailing demand strong while the forward outlook softens**.

**Scope decision (locked in brainstorming): the divergence is CROSS-SECTIONAL (single cycle).** It compares
this cycle's Momentum vs Outlook — a pure function of one scorecard's tagged findings, no prior-cycle state.
The **temporal** layer ("Outlook *turned* vs last cycle") is **deferred to 4-5** (which reads the persistent
store); 4-3 ships the cross-sectional verdict with a clean seam for that later layer (the **hybrid** plan).

**4-3 is NOT:** the daily gather / scrape cron that *produces* leading findings (4-4); the discovery engine
(4-4); the brief renderer (4-5); the temporal "what moved / turned vs last cycle" comparison (4-5). 4-3 ships
**additive Scorecard fields + a small computation in `build_scorecard` + tests** only.

**The reality 4-3 is designed around:** the 4-2 leading indicators have **no findings** until 4-4 feeds them.
So on every run available today (and on the committed fixtures), **Outlook is empty** and the divergence reads
`insufficient-coverage`. This is handled **honestly** (Part 29 — a logged note, never a fabricated forward
signal), and all divergence paths are exercised in tests via **synthetic** leading findings.

---

## 1. The core approach — partition by horizon, reuse the frozen scoring

`gpu_agent/scoring.py::dmi_smi_contribution` is **frozen byte-unchanged**. 4-3 reuses it by feeding it
**pre-filtered finding subsets**, never by editing it:

- Partition the cycle's findings into two buckets using the 4-2 accessor
  `gpu_agent/registry/horizon.py::IndicatorHorizons.horizon(indicatorId)`:
  - **Momentum bucket** = findings whose indicator horizon ∈ {`lagging`, `coincident`}
  - **Outlook bucket** = findings whose indicator horizon ∈ {`leading`}
- Call the frozen `dmi_smi_contribution` on each bucket → `(dmi, smi)` per index, **passing the same
  `assignment.weights` overrides the blended `demandSupply` uses** (required for the invariant below to hold
  exactly). Inside it, price / structural / non-scoring indicators remain auto-excluded (registry is
  side-authority), so overlays never enter either index.

**Each indicator has exactly one horizon tag**, so the buckets are disjoint *by indicator*. Because
`dmi_smi_contribution` is an additive sum over indicators, this yields a free invariant (asserted as a test):

```
demandSupply.dmiContribution == momentum.dmiContribution + outlook.dmiContribution   (same for smi)
```

**On the committed fixtures** (no leading findings): Momentum exactly equals today's `demandSupply`, Outlook is
all-zero, the invariant holds → existing fixture numbers are provably unchanged, divergence = `insufficient-coverage`.

**Findings with an untagged indicator** must not be silently dropped: every *scoring* indicator is guaranteed
tagged by 4-2's `validate_coverage` (run as a guard), so any untagged indicator reaching the partition is a
data error and fails loud rather than vanishing from both indices.

---

## 2. The data model (additive Scorecard fields)

All new fields are **optional** → the frozen gate and every committed fixture are unaffected. Reuse B's
existing `DemandSupply` model for each index (DRY — same `{dmiContribution, smiContribution, anchors, sdgi,
sdgiDirection}` shape); per-index `anchors` stays empty (already defaulted).

```python
# new in gpu_agent/schema/scorecard.py
class Divergence(BaseModel):
    state: Literal["aligned", "diverging-weakening",
                   "diverging-strengthening", "insufficient-coverage"]
    sdgiGap: float                 # outlook.sdgi - momentum.sdgi (informational; 4-5 renders it)
    outlookFindingCount: int       # CONTRIBUTING (scoring) leading findings backing Outlook
    momentumFindingCount: int      # CONTRIBUTING (scoring) lagging+coincident findings backing Momentum
    note: str = ""                 # e.g. "no leading findings; Outlook deferred to 4-4"

class MarketIndices(BaseModel):
    momentum: DemandSupply         # lagging + coincident
    outlook: DemandSupply          # leading
    divergence: Divergence

class Scorecard(BaseModel):
    ...                            # everything existing stays byte-for-byte
    indices: Optional[MarketIndices] = None   # NEW
```

- **`demandSupply` (the blended all-findings index) stays exactly as-is** — it is what the frozen gate and the
  committed fixtures read. The two new indices are *additional*, tied to it by the §1 invariant.
- The blended `_sdgi_direction` helper (B) is reused for each index's `sdgiDirection`.

---

## 3. The divergence verdict (deterministic; agent sets nothing)

A pure helper in `pipeline.py` (alongside `_sdgi_direction`):

```python
# direction rank from a demand perspective: demand-led is the "strongest forward" lean
_DIR_RANK = {"demand-led": 1, "balanced": 0, "supply-led": -1}

def _divergence(momentum, outlook, mom_count, out_count, *, floor=1) -> Divergence:
    gap = (outlook.sdgi or 0.0) - (momentum.sdgi or 0.0)
    if out_count < floor:
        state, note = "insufficient-coverage", "no leading findings; Outlook deferred to 4-4"
    elif outlook.sdgiDirection == momentum.sdgiDirection:
        state, note = "aligned", ""
    elif _DIR_RANK[outlook.sdgiDirection] < _DIR_RANK[momentum.sdgiDirection]:
        state, note = "diverging-weakening", ""        # forward leans more supply-led / less demand-led
    else:
        state, note = "diverging-strengthening", ""    # forward leans more demand-led
    return Divergence(state=state, sdgiGap=gap, outlookFindingCount=out_count,
                      momentumFindingCount=mom_count, note=note)
```

Properties:
- **The aligned/diverging boundary uses the categorical `sdgiDirection`**, which already bakes in B's `eps=0.02`
  deadband — so there is **no new threshold to tune**. `sdgiGap` is carried as informational only (for 4-5).
- **Weakening vs strengthening** is the direction-rank comparison; the warning case the system exists to catch
  (`diverging-weakening`) is named explicitly. Example: Momentum `demand-led` while Outlook `supply-led` →
  `diverging-weakening`.
- **`insufficient-coverage` is checked first** (floor = 1 **contributing** leading finding) → on every current
  run and the committed fixtures it reports honestly with a logged note, never a fabricated forward signal
  (Part 29). The counts are of **scoring** findings only (those `dmi_smi_contribution` actually uses) — a lone
  leading *overlay* (e.g. `designWins`, structural) contributes 0 and does **not** by itself make Outlook
  "covered". The finding counts are carried so 4-5 can flag a thin / single-source Outlook.

---

## 4. Wiring (additive)

`build_scorecard` already receives `registry`. It will also obtain the horizon tags via `IndicatorHorizons`
(loaded from the same `registry/indicators.json` path, or accepted as an optional parameter that defaults to
that load — exact signature pinned in the plan, kept additive so existing call sites keep working). After the
existing blended `demandSupply` is computed and the gate runs unchanged, it:

1. runs `IndicatorHorizons.validate_coverage(registry)` as a fail-loud guard (every scoring indicator tagged);
2. partitions findings into the Momentum and Outlook buckets (§1);
3. computes each index via the frozen `dmi_smi_contribution` + `_sdgi_direction`;
4. computes the `Divergence` (§3);
5. attaches `indices = MarketIndices(momentum, outlook, divergence)` to the scorecard.

The existing output (`demandSupply`, `dimensionRatings`, `dimensionStatus`, the frozen gate call) is unchanged.

---

## 5. Frozen vs additive (Part 33)

- **Byte-unchanged:** `gpu_agent/scoring.py` (incl. `dmi_smi_contribution`, `zscore`), `gate.py`,
  `registry/indicators.py` + `validate.py`, the `Finding` schema, the 6 dimension names, the rating scale,
  `pipeline.py`'s Part-7 gate behavior.
- **Additive:** new optional `Scorecard.indices` field + `MarketIndices`/`Divergence` models; new private helpers
  in `pipeline.py` (`_partition_by_horizon`, `_divergence`) + the index computation inside `build_scorecard`.
- **Reuse, do not rebuild:** the frozen `dmi_smi_contribution`; B's `DemandSupply` model + `_sdgi_direction`;
  4-2's `IndicatorHorizons`.

---

## 6. Doctrine

Numbers come only from gated findings — the indices are sums over gated findings via the frozen function; the
agent sets none of them (Part 17). Price/structural/non-scoring indicators are auto-excluded from both indices.
`insufficient-coverage` and the finding counts are recorded in the scorecard, **logged, never silent** (Part 29).
Deterministic, no wall-clock; the same findings always yield the same indices.

---

## 7. Test strategy (deterministic; committed-fixture pattern)

- `_partition_by_horizon` buckets findings correctly (leading → Outlook; coincident/lagging → Momentum;
  price/structural carried but inert inside `dmi_smi_contribution`).
- **Additive invariant:** `demandSupply.dmiContribution == momentum + outlook` (and smi) on the committed
  fixtures.
- **Fixture inertness:** Momentum equals today's `demandSupply` and Outlook is all-zero on the committed
  fixtures (no regression); divergence reads `insufficient-coverage` with its note.
- **Divergence rule** exercised with *synthetic* leading findings: `aligned`, `diverging-weakening`
  (Momentum demand-led, Outlook supply-led), `diverging-strengthening`, and `insufficient-coverage` (below
  floor) all fire — non-tautological (constructed Findings drive real direction outcomes).
- **Coverage guard:** an untagged scoring indicator makes `validate_coverage` (run in `build_scorecard`) fail
  loud rather than silently dropping the finding.
- Frozen-contract git-diff guard (byte-unchanged) + full suite green (baseline after 4-2: **268 passed,
  3 skipped**, plus the new tests).

---

## 8. Out of scope (later pieces / arcs)

- The daily gather + scrape cron that *populates* leading findings, and the discovery engine (4-4).
- The **temporal** divergence ("Outlook turned vs last cycle") and the per-track thin-coverage rendering (4-5,
  reading the store).
- The brief render of the two indices + the divergence call (4-5).
- Numeric-magnitude divergence thresholds (deliberately deferred — cannot tune an epsilon until 4-4 produces
  forward findings; the categorical direction rule needs none).

---

## 9. Acceptance (4-3)

1. `Scorecard.indices` is populated with `momentum`, `outlook`, and `divergence`, each computed **in code** from
   the horizon-tagged findings via the frozen `dmi_smi_contribution`; the agent sets none of them.
2. The additive invariant `demandSupply == momentum + outlook` holds; the existing `demandSupply` and **all
   committed fixtures are byte-unchanged**; the frozen files are byte-unchanged.
3. The divergence verdict is correct across all four states (`aligned`, `diverging-weakening`,
   `diverging-strengthening`, `insufficient-coverage`), tested with synthetic leading findings; it reads
   `insufficient-coverage` with a logged note until 4-4 feeds leading findings.
4. Full suite green; doctrine honored (numbers only from gated findings; nothing silent; deterministic).
