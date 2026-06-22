# GPU Category Agent — Phase-1 MVP Design

- **Date:** 2026-06-19
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **References:** [`docs/agent-swarm-charter.md`](../../agent-swarm-charter.md) ·
  [`docs/category-agent-guide.md`](../../category-agent-guide.md) ·
  [`docs/taxonomy.json`](../../taxonomy.json)

---

## 1. Context & goal

Build the first **Tier-1 Category Agent** (charter Part 3) for the `chips.merchant-gpu` category,
covering **NVIDIA, AMD, and Intel**. It ingests sources, emits **demand/supply-tagged Findings**
(charter Part 2 + the guide's extensions), and produces a **6-dimension scorecard** plus the
category's **Demand-Momentum (DMI) and Supply-Momentum (SMI) contribution** to the Chips layer.

This is the **Phase-1 MVP** of the build roadmap in `category-agent-guide.md` §7. It is also the
**reference agent** the charter's pilot-first rule (Part 27) calls for: prove one category
end-to-end before fanning out to the other ~33.

### Why GPUs first
Merchant GPUs is the densest, most measurable, most decision-relevant category, and it exercises
**both** the demand track (D2, D6) and the supply track (S9, S10) — so it validates the dual-polarity
machinery that is the whole point of the demand/supply guide.

---

## 2. Scope

### In scope (MVP)
- Three constituents: **NVIDIA, AMD, Intel** (`merchant-gpu` seed constituents).
- Four indicators: **D2** (NVIDIA DC revenue structure, demand), **D6** (GPU rental price, demand),
  **S9** (alternative supply, supply), **S10** (whole-chain inventory, supply).
- Four measured metrics: `market-share-pct`, `perfPerWatt`, `flopsPerDollar`, `grossMargin`.
- Two qualitative metrics: `cudaLockIn`, `designWinDurability`.
- All six fixed scorecard dimensions: momentum, unitEconomics, competitiveStructure, moat,
  bottleneck, strategicRisk (charter Part 17 — fixed contract, not configurable).
- All three integration levels, built as one system (see §7):
  - **(A) deterministic core** on fixtures,
  - **(C) extraction slice** (fixtures → LLM extraction → core),
  - **(B) end-to-end slice** (live connector → extraction → core).

### Out of scope (later phases)
- The Layer agent and Main orchestrator (this feeds them; it is not them).
- Live production scheduling/cron, TimescaleDB/Neo4j, dashboard.
- The other 33 categories (the template is built here; fan-out is later).
- Recommendation Skill (Layer/Main only, charter Part 11).
- Price-confirmation family (P1–P6) and structural overlays (X1–X5) beyond what D6 implies.

---

## 3. Success criteria (acceptance)

Given fixture inputs for all three constituents, the agent produces a scorecard that:
1. **Passes the Part-7 gate** (no naked/invented numbers; every Finding has why+impact+source;
   demand/supply polarity present; no rating contradicts its cited evidence).
2. Carries **Findings across D2, D6, S9, S10** + the four measured + two qualitative metrics.
3. Emits a **deterministic DMI/SMI contribution** for the Chips layer.
4. **Matches a hand-authored golden scorecard** (the Part-24 golden set, one archetype) — exactly for
   the deterministic parts; within a rubric tolerance for the judged ratings.
5. The end-to-end and extraction slices reproduce the core's contract using **recorded** LLM
   responses (deterministic tests), with one optional **live smoke test** gated behind an API key.

---

## 4. Architecture

### 4.1 Modules (the core + three parallel adapters)

```
gpu_agent/
  schema/       Pydantic models: RawDocument, Finding (+ polarityDemand/Supply, side, magnitude,
                indicatorId, observedAt/capturedAt), DimensionRating, Scorecard
  gate/         Part-7 pre-commit validation gate (pure, deterministic)
  scoring/      deterministic "briefing book": z-score, DMI/SMI contribution, Δ-vs-prior anchors
  store/        append-only, versioned JSON canonical-store stub
  assignment/   loads asg.chips.merchant-gpu (entities, metrics, budget)
  judgment/     [LLM] forms the 6 ratings + narrative from briefing book + Findings   ← parallel
  extraction/   [LLM] RawDocument → Finding[]                                          ← parallel
  connectors/   ingest → RawDocument (EDGAR, GPU-rental)                               ← parallel
  cli/          `gpu-agent run --assignment <id> [--fixtures <dir>]`
  tests/  fixtures/
```

**Design principle (charter Part 18):** the schema + gate + scoring + store form a **small, frozen
contract**; the LLM adapters (judgment, extraction) and the connectors plug into it. A bug fixed in
the core is fixed for every future category that reuses the template.

### 4.2 Data flow

```
connectors → RawDocument → extraction → Finding[] → [gate] → store
                                                  ↓
                            scoring → briefing book (z-score, DMI/SMI contribution, Δ vs prior)
                                                  ↓
                            judgment → 6 ratings + narrative (each cites Finding IDs)
                                                  ↓
                            Scorecard → [gate] → store → hand-up to Chips Layer agent
```

The **core** runs the deterministic middle (gate → scoring → assemble-and-validate scorecard). The
LLM adapters bolt onto the ends; the connectors feed the front.

---

## 5. Ratings: grounded judgment + deterministic guardrails

Ratings are an analyst **judgment**, not an arithmetic of the metrics (charter Part 17: "not an
average"). A pure formula is rejected because (a) half the dimensions — moat, design-win durability,
strategic risk — have **no measurable input** (computing them would mean inventing numbers, doctrine
Rule 2), and (b) Part 17 forbids hidden scoring formulas. But unconstrained LLM judgment carries
bias (recency, anchoring, name-recognition, prompt sensitivity). So judgment is **grounded and
bounded**:

- **Deterministic anchors (code):** the scoring module computes z-score / percentile / Δ-vs-prior for
  every *measured* dimension. The judgment step must reference these — it cannot freelance against the
  data.
- **Anchor-consistency gate (code):** the Part-7 gate **rejects** a rating that contradicts its own
  cited measured evidence (e.g. "Momentum: Very strong" while the cited metric's z-score is deeply
  negative). Code does not *set* the rating; it *bounds* it.
- **Written rubric definitions** for each rating word (Very strong … Very weak), so two runs pick the
  same word for the same evidence — reduces variance.
- **Self-consistency sampling:** rate N times on identical input, take the majority, and **report the
  spread** (charter Part 24, applied at the Category tier) — residual bias becomes measured and
  visible, not hidden.
- **Mandatory citations + confidence:** every rating names the Finding IDs that drove it and a
  confidence with a basis — auditable and falsifiable.

Net: measured dimensions are *judgment grounded by computed anchors*; qualitative dimensions are
*judgment with cited evidence*; the gate enforces consistency; sampling measures the residual.

---

## 6. Schemas (MVP shape)

### Finding (charter Part 2 + guide extensions)
Fields: `id, statement, kind (measured|observed|hypothesis), value (null unless measured), trend,
why, impact{targets,direction,mechanism}, evidence[], reasoning (hypothesis only), confidence{level,
basis}, dispersion, asOf` **plus** `indicatorId, side (demand|supply|price|structural),
polarityDemand (-1|0|1), polaritySupply (-1|0|1), magnitude (1|2|3), entity, observedAt, capturedAt,
extractionModel, schemaVersion`.

### Scorecard
`{ categoryId, asOf, findings[], dimensionRatings{ <6 dimensions>: {rating, direction, confidence,
findingIds[], rationale} }, demandSupply: { dmiContribution, smiContribution, anchors{} }, narrative,
confidence, sources[], provenance }`.

### Validation gate (Part 7 + new MVP rules)
Rejects, with a re-run (never commit a partial):
- a `measured` Finding without a `value` and ≥1 dated source;
- a `value` on an `observed`/`hypothesis` Finding (invented number);
- any Finding missing `why`, `impact`, or **demand/supply polarity**;
- a hypothesis without `reasoning` or above `confidence = medium`;
- a dimension rating that cites no Finding IDs;
- **a rating that contradicts its cited measured anchor** (new — the bias guardrail);
- conflicting sources not surfaced as `dispersion`;
- any Finding citing the dashboard's own prior output (self-reference).

---

## 7. Build order & parallelization

1. **Core first (lead agent):** schema → gate → scoring → store → assignment → cli, fully TDD'd on
   fixtures (this is integration level **A**). Freeze the Finding/Scorecard interface.
2. **Then parallel** (superpowers `subagent-driven-development`, once the interface is frozen):
   - **judgment** module (ratings + narrative),
   - **extraction** module (RawDocument → Findings),
   - **connectors** (EDGAR + GPU-rental).
3. **Compose:** fixtures→extraction→core = level **C**; connectors→extraction→core→judgment =
   level **B**.

Parallelism is safe only *after* step 1 freezes the shared contract — otherwise the adapters would
re-invent the schema/scoring and conflict on merge.

---

## 8. Error handling (charter-aligned)

- **Gate failure → re-run, never commit a partial** (Part 7).
- **Bend, don't break** (Part 18 #8): a missing metric/source does not crash — the scorecard still
  emits, that dimension is **confidence-capped and flagged under-supported**.
- **Dispersion** (Part 1): conflicting sources surface as a range, never silently resolved.
- **LLM adapters**: schema-constrained (Pydantic-validated) output with retry-on-invalid; fetched
  content is **data, not instructions** (Parts 8/26).

---

## 9. Testing strategy (TDD-first, superpowers)

- **Golden set:** hand-authored RawDocuments → expected Findings → one golden Scorecard.
- **Unit:** schema round-trip; gate rejects each violation type (one test per rule, incl. the
  anchor-consistency rule); scoring math (z-score, DMI/SMI contribution); store append-only/versioning.
- **Integration:** fixtures → core → exact-match golden scorecard (deterministic parts).
- **LLM modules:** the validate-and-retry harness tested deterministically against **recorded**
  responses; self-consistency spread asserted within bound; one live smoke test gated behind an
  API-key flag.

---

## 10. Tech stack

- **Python 3.11+**, **Pydantic** (schema + validation), **pytest** (TDD).
- **Append-only JSON files** as the canonical-store stub (git-friendly, diffable; SQLite deferred).
- **LLM access goes through an `LLMClient` port** — the extraction + judgment modules depend on the
  port, never on an SDK directly (charter Part 18 #7: model swappable behind an interface). Two
  interchangeable backends:
  - **`ClaudeCodeClient` (default — runs via Claude Code):** drives Claude through the Claude Agent
    SDK (`claude-agent-sdk`) / headless `claude`, authenticated with a **subscription token**
    (`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`) so calls bill against the **Claude Code
    subscription credit pool**, not a metered key.
  - **`AnthropicAPIClient` (alternate):** the `anthropic` SDK + `ANTHROPIC_API_KEY`, for
    high-volume/production where the subscription credit pool is too small.
  Both wrap the **same validate-and-retry loop** (§9): the Claude Code path lacks the raw API's
  strict `output_config.format` enforcement, so instruct-JSON + Pydantic-validate + retry is
  load-bearing there. Model tiering (Haiku filter / Sonnet or Opus extraction / Opus judgment) is set
  when those modules are built.
- **The deterministic core (this plan) needs no LLM and no credential of any kind.** The Claude Code /
  subscription-token wiring lives entirely in the follow-on adapter plan.
- **Prerequisite for the adapter phase (not the core):** `pip install claude-agent-sdk` and a Claude
  Code CLI authenticated on the host (interactive login, or `CLAUDE_CODE_OAUTH_TOKEN` for
  unattended/scheduled runs). Ensure `ANTHROPIC_API_KEY` is **unset** when using the subscription
  backend — it overrides the subscription token.

---

## 11. Charter changes required (tracked follow-up — must land before code merges)

The design uses concepts that **extend** the charter; these additive edits (charter Part 33: additive,
version-bumped, old data still readable) are tracked as **Task #9** and must land before the GPU code
merges, so the charter stays the single source of truth:

1. **Part 2 (Finding):** add `polarityDemand`, `polaritySupply`, `side`, `magnitude`, and the
   `observedAt`/`capturedAt` split. Bump the Finding `schemaVersion`.
2. **Part 7 (gate):** add two checklist items — *demand/supply polarity present* and
   *no rating contradicts its cited measured anchor* (the bias guardrail).
3. **Part 17 + Part 6:** add the **demand/supply roll-up decomposition** (DMI / SMI / SDGI) as the
   dual-track companion to the existing single-track weakest-link roll-up.

Already covered by the charter (no change): computed rollups + agent interprets (Part 5);
ratings-are-judgments (Part 17); self-consistency sampling (Part 24); vintage/look-ahead honesty
(Part 8); demand-down / constraints-up topology (Part 9).

---

## 12. Open questions

None blocking. Model-tier selection for the LLM modules is intentionally deferred to build time
(§10). The charter reconciliation (§11) is sequenced as a tracked follow-up per the chosen plan.
