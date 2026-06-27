# Output & Coverage Overhaul — decomposition + shared-seam contract

- **Date:** 2026-06-27
- **Status:** Draft for review (umbrella design; binds three sub-project specs)
- **Author:** brainstorming session (superpowers workflow)
- **Motivation:** A live `category:chips.merchant-gpu` run (`store/chips.merchant-gpu/2026-06-v3.json`) rated **only 4 of
  6 dimensions** — `bottleneck` and `strategicRisk` were silently absent — reported "cycle complete," and produced
  DMI/SMI that swing run-to-run on the *same* period (v1→v3: 1, 5, 4 dimensions; DMI 0.067 → 0.140 → 0.100). An analyst
  can neither trust nor trend that. This overhaul makes the agent's output complete, honest, and comparable.
- **References:** [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) Part 17 (rating without inventing
  numbers; the overall rating, DMI/SMI/**SDGI**, "every rating stated against last time"), Part 18 (assignments /
  registries; principle **#8 "bend, don't break" — missing ability → flagged *under-supported* + confidence-capped,
  never dropped**), Part 22 (data-source reality: per-metric **source inventory**, tiered acquisition, honest
  "estimate/unavailable"), Part 35 (the **product surface** — graceful states "inputs degraded" / "provisional"),
  Part 37 (the gathering swarm) · Part 33 (schema evolution — the frozen contract thaws *additively*) · the **truly
  frozen** contract: the **`Finding` schema**, the **6 dimension names**, the **rating scale**, `gate.py`,
  `scoring.py:zscore`, the `pipeline.py` Part-7 gate, and `registry/validate.py`. **Evolvable additively (Part 33):**
  the **`Scorecard` model** (new *optional* fields only — existing fields/semantics untouched), the **judgment
  prompt/briefing/result** (B's mandate — request all 6 + the overall status), and the **indicator *data*** in
  `registry/indicators.json`. The sp2-era freeze on `judgment/*.py` was sp2-scoped and does **not** bind this overhaul.

---

## 1. Why this is three sub-projects (not one)

The recommendations cluster into three subsystems that map onto distinct charter seams and own distinct files. They
share a small core (the scorecard contract, `registry/indicators.json`, `cli.py`, the judge briefing) — which is exactly
why the seams below are fixed **once, here**, before any fan-out, and why the build is **sequenced** (Part 18: keep the
"small sacred contract" coherent; parallel writers corrupt it).

| | Sub-project | Charter seam | Owns (writes) | Depends on |
|---|---|---|---|---|
| **A** | **Scorecard → executive report** (a deterministic renderer + `report` CLI mode; the `run-cycle` skill calls it) | Part 35 + 17 | new `gpu_agent/report.py`; `report` subcommand in `cli.py`; the report step of `.claude/skills/run-cycle/SKILL.md` | reads **B**'s scorecard shape |
| **B** | **Six-dimension integrity** (every scorecard carries all 6 dimensions; ungrounded → `under-supported`, never dropped; add the missing `strategicRisk` indicator; compute `sdgi`) | Part 18 #8 + 17 | `registry/indicators.json` (indicator **definitions + dimension mapping**); the judge briefing / scorecard assembly that guarantees 6 + writes `sdgi` | none — ships first |
| **C** | **Coverage manifest + source inventory** (per-category "expected coverage" manifest; per-metric source inventory; the gather targets it; a missing source → a logged coverage gap) | Part 22 + 37 | a new manifest + source-inventory artifact; the assignment extension; `gather-category` skill; per-metric **source hints** in `registry/indicators.json` | feeds **B**'s coverage signal |

**Build order (sequenced, each merged before the next):** **B → A → C.** B fixes the data contract so the report never
renders a transiently-wrong shape; A renders it; C deepens sourcing and stabilizes coverage so the indices become
trendable. Spec + plan for all three are authored **in parallel** (distinct doc files — no conflict); only the build is
sequenced.

---

## 2. The shared-seam contract (binding on all three sub-projects)

These are fixed here so the three specs cannot diverge on the core. Each sub-spec **must** restate the seams it touches.

### 2.1 The scorecard contract grows additively (frozen fields untouched)
The scorecard keeps every field it has today (`dimensionRatings`, `demandSupply{dmiContribution, smiContribution,
anchors}`, `findings`, `sources`, `narrative`, `confidence`, `provenance`, `asOf`, `categoryId`). It **gains**:
- **All six dimensions, always present** in `dimensionRatings`. A dimension with no grounding is **not omitted**; it
  carries an explicit status — `evidenceStatus: "grounded" | "under-supported"` — and when `under-supported` its
  confidence is capped (Part 18 #8; Part 35 "inputs degraded"). (Owner: **B** writes it; **A** renders it.)
- **An overall category status** — one judged headline (Part 17: "an analyst's read of its six judgments, **not** an
  average"). Because it is *judgment*, it is produced by the **judge brain** and stored in the scorecard (a new field,
  e.g. `categoryStatus{rating, direction, bottleneck, reason}`), **not** computed or invented by the report. (Owner:
  **B** captures it in the judgment contract + scorecard; **A** renders it. Code never derives this rollup — that would
  be the "average" Part 17 forbids.)
- **`demandSupply.sdgi`** = `dmiContribution − smiContribution`, plus a per-track direction label (Part 17's
  Supply-Demand Gap). This is a **measured rollup computed in code**, never the agent. (Owner: **B** computes it; **A**
  renders it.)
- Trend is **derived, not stored**: the report reads the prior `store/<cat>/<asOf>-v<n-1>.json` (or prior `asOf`) to show
  "Δ vs last cycle" (Part 17 "every rating stated against last time"). (Owner: **A**; no scorecard field needed.)

Division of labor for the headline numbers/words: **code computes** DMI/SMI/SDGI, coverage %, and trend deltas; the
**judge brain produces** the dimension ratings and the one overall category status (both judgment); the **report (A)
only renders** — it invents nothing.

The 6 dimension **names**, the `Finding` schema, the rating scale, `gate.py`, `scoring.py:zscore`, and the `pipeline.py`
Part-7 gate are **frozen** — all additions sit around them.

### 2.2 `registry/indicators.json` ownership split (prevents the B/C collision)
Both B and C touch this file, so ownership is partitioned and the build is sequenced (B before C):
- **B owns:** indicator **definitions and dimension mapping** — specifically, adding the indicator(s) that ground
  `strategicRisk` (today no indicator maps to it, so the 6th dimension can never be grounded). B's spec settles the
  definition; **suggested default:** export-control / China-revenue exposure + customer-and-supplier concentration.
- **C owns:** per-metric **source hints / source inventory** fields (`defaultSourceHint` grown into
  `{accessMethod, tier, costUsd, license, refresh}`, Part 22) on existing and new indicators.
- Neither edits the other's fields. Because B lands first, C rebases onto B's indicator set.

### 2.3 The coverage manifest is the "expected coverage" set (C owns; B and A consume)
C defines, per category, the indicators/sources a cycle is **expected** to cover. B's `under-supported` logic reads
"expected vs actually-grounded" from it; A renders a coverage line (e.g. "5/6 dimensions grounded; 1 under-supported").
**Until C lands, B uses the simpler rule:** a dimension with zero supporting findings is `under-supported`. This keeps B
shippable before C and lets C tighten the definition later without reworking B.

### 2.4 Doctrine that binds every sub-project (charter)
- **Code computes + gates + stores; the agent reasons.** `sdgi`, coverage %, trend deltas, and any rollup are computed
  in code — the agent never sets a number that reaches the scorecard/report uncomputed (Part 17/38).
- **Bend, don't break (Part 18 #8):** missing data degrades to `under-supported`/`estimate`/`unavailable`,
  confidence-capped and labeled — never silently dropped, never faked.
- **Honest sourcing (Part 22):** paywalled trackers (Gartner/TrendForce/JPR/IDC/Mercury) are **not** scraped; they are
  inventoried with access/cost and the metric runs `estimate`-grade until licensed, and the surface says so.
- **Plain language (Part 17):** the report is readable by a board member without a glossary.
- **Reproducible (Part 20):** the report is a pure projection of a saved scorecard; same scorecard → same report.

---

## 3. Per-sub-project scope (the detail lives in each sub-spec)

Each sub-project gets its **own** spec (`docs/superpowers/specs/2026-06-27-<slug>-design.md`) and plan
(`docs/superpowers/plans/2026-06-27-<slug>.md`), authored against this umbrella.

- **A — Scorecard → executive report.** A deterministic `gpu_agent/report.py` + `report` CLI mode that reads a saved
  scorecard and **renders** (never invents) a board-ready report: the **overall category status** (read from the
  judge-produced `categoryStatus` field B adds — §2.1), all six dimensions with ratings/direction/confidence and the
  `under-supported` state shown, **DMI/SMI/SDGI** with a one-line interpretation and **Δ vs last cycle** (computed from
  the current + prior saved scorecards), a **per-entity panel** (NVDA/AMD/INTC from the entity-tagged findings),
  **evidence quality** per dimension (primary/secondary mix, finding count), the **sources** list with tiers/dates, and
  the **skip/coverage-gap** list. Replaces the free-text report that currently garbles. Validated by unit tests over
  committed scorecard fixtures (deterministic, no LLM).
- **B — Six-dimension integrity.** Guarantee all six dimensions in every scorecard with `evidenceStatus`; add the
  `strategicRisk` indicator(s) + mapping to the registry; capture the judge-produced **overall `categoryStatus`** in the
  judgment contract + scorecard; compute `demandSupply.sdgi` in code; ensure the judge briefing requests all six and the
  scorecard assembly enforces presence with capped confidence for under-supported ones. Additive; the frozen
  gate/scoring/schema stay untouched. TDD.
- **C — Coverage manifest + source inventory.** A per-category coverage manifest (expected indicators/sources) + a
  per-metric source inventory (Part 22 fields); the `gather-category` skill targets the manifest and logs each
  not-covered item as a surfaced gap (feeding B's `under-supported`); tiered acquisition with honest degradation. The
  assignment gains a manifest reference (Part 18 pluggable scope). Skill validated by a documented dry-run; any code TDD.

---

## 4. Out of scope / non-goals
- The multi-tier Opus fan-out (the previously-named next sub-project) — deferred; this overhaul is orthogonal and lands
  first.
- Scraping or redistributing paywalled data — Part 22 forbids it; we inventory + label, not circumvent.
- Changing the 6 dimension names, the Finding schema, the rating scale, `gate.py`, `scoring.py:zscore`, or the
  `pipeline.py` Part-7 gate (frozen).
- A taxonomy-default assignment generator / broad multi-category coverage (its own effort).

---

## 5. Execution
1. **Parallel:** three subagents, each authors its sub-project **spec** (via the brainstorming design captured here) then
   its **implementation plan** (superpowers `writing-plans`), referencing this umbrella for the shared seams. Distinct
   files → no conflict.
2. **Review:** the orchestrating session reviews the three specs+plans for seam consistency (especially §2.1–2.3).
3. **Sequenced build (B → A → C):** each via `superpowers:subagent-driven-development`, on its own branch off `main`,
   green + reviewed + merged before the next starts (so the shared core stays coherent).

## 6. Acceptance (umbrella)
- Every produced scorecard carries all 6 dimensions; an ungrounded one is `under-supported` + confidence-capped, never
  dropped; `strategicRisk` is groundable via a registry indicator; `demandSupply.sdgi` is computed in code.
- `report` renders a board-ready, plain-language report: overall status, 6 dimensions (with degraded states), DMI/SMI/
  SDGI + interpretation + Δ-vs-last-cycle, per-entity panel, evidence/source quality, coverage/skip list — deterministic
  from a saved scorecard.
- A coverage manifest + per-metric source inventory exist; the gather targets the manifest; not-covered items are logged
  gaps, never silent; paywalled sources are labeled `estimate`/`unavailable`, not faked.
- The frozen contract is untouched; each sub-project's full suite stays green; the three integrate via §2's seams.
