# GPU Category Agent — Judgment Adapter (Stage 2) Design

- **Date:** 2026-06-24
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **Builds on:** the frozen deterministic core (`specs/2026-06-19-gpu-category-agent-design.md`,
  `plans/2026-06-19-gpu-category-agent-core.md`) and the extraction adapter + shared `LLMClient` port
  (`specs/2026-06-22-gpu-agent-extraction-adapter-design.md`,
  `plans/2026-06-22-gpu-agent-extraction-adapter.md`) — all merged to `main`.
- **References:** `docs/agent-swarm-charter.md` Part 17 (ratings are judgment, not an average) + Parts
  1/2/7/8/26; core spec §5 (grounded judgment + deterministic guardrails), §7 (build order/integration
  levels), §9 (testing), §10 (LLMClient port), §13 (modularity).

---

## 1. Context & goal

The core scores *pre-rated* fixtures: today `ratings.json` (the six `DimensionRating`s) and `anchors.json`
(the per-dimension signed anchors the gate checks ratings against) are **hand-authored**. This adapter is
**stage 2 — the Judgment Adapter**: it produces those ratings, anchors, and the scorecard narrative from
gated `Finding[]` using **grounded LLM judgment plus deterministic guardrails**, so the pipeline can run
`extract → judge → score` end-to-end without hand-authored judgment.

It reuses the **shared `LLMClient` port** built for extraction and stays **offline and deterministic in
tests** by replaying recorded model responses (core spec §9). The governing doctrine: **ratings are
judgment bounded by anchors, never set by code** (charter Part 17); code computes the anchors and runs the
gate, the LLM sets the rating within those bounds.

---

## 2. Scope

### In scope
- **Deterministic briefing book** — `gpu_agent/judgment/briefing.py`: from gated `Finding[]` compute the
  per-dimension signed **anchors** (reusing the scoring `polarity·magnitude/3` primitive) and assemble the
  evidence the LLM judges against. The anchors here are the same `dict[str, float]` the existing gate and
  `score`/`run` path already consume.
- **Judgment LLM contract** — `gpu_agent/judgment/judge.py`: a `JudgmentResult` schema the LLM fills per
  call (the six dimension ratings + narrative), driven through the port's validate-and-retry loop.
- **Self-consistency sampling** — sample the LLM `N` times (default 3), take the majority rating per
  dimension, surface the spread in `confidence.basis`, and **cap confidence when samples disagree**.
- **Anchor-conflict handling** — when a candidate rating contradicts its computed anchor sign, **re-sample
  up to K times, then raise `JudgmentError`** (never commit a partial; charter Part 7).
- **Gate backstop** — assemble candidate `ratings` + `anchors` + `narrative` and run the existing
  `check_scorecard` as a final guardrail before writing.
- **CLI** — a `judge` subcommand (gated findings → `ratings.json` / `anchors.json` / `narrative.json`) and a
  one-shot `pipeline` command chaining `extract → judge → score`. `score`/`run` extended to read
  `narrative.json` (and the judged confidence) when present, falling back to the current placeholder
  otherwise (back-compatible).
- **Tests** — recorded-response unit/integration tests (N recorded judgment responses for majority/spread);
  one **optional live smoke** gated behind `GPU_AGENT_LIVE_LLM=1`.

### Out of scope (later / not now)
- **Assignment-driven dimension mapping.** The `indicatorId → dimension` map ships as a **code default**
  (decision below; YAGNI) — no assignment-schema change in this plan.
- **Metric history / time-series anchors.** Anchors are computed from the *current* findings only; no
  historical z-score store (the `zscore` helper stays available but unused here).
- **Live connectors / extraction changes** — extraction and the frozen core are untouched.
- **Model-tier auto-selection / judge-vs-extract model tuning** — the model is a parameter, defaulting as
  the CLI does today; tuning is deferred.
- Any change to the **frozen contract**: the Finding/Scorecard schema, the six dimensions, the gate rules
  (`gate.py`), the rollup (core spec §13.1).

---

## 3. Success criteria (acceptance)

1. Given gated `Finding[]` + **recorded** LLM responses, `judge` emits `ratings.json` / `anchors.json` /
   `narrative.json` that flow unchanged into the existing `build_scorecard`/`score`/`run` path and produce a
   **`check_scorecard`-valid scorecard** (Stage 2 composes end-to-end with Stage 1).
2. **Anchors are computed by code, ratings by the LLM** (charter Part 17): the briefing builder is a pure
   function of the findings (no LLM, no wall clock); the LLM never sets an anchor and code never sets a
   rating.
3. **Self-consistency works:** with N recorded responses that disagree on a dimension, `judge` returns the
   **majority** rating, records the spread in that dimension's `confidence.basis`, and **caps `confidence`**
   (no `high` when samples split).
4. **Anchor conflict is never silently committed:** a candidate rating that violates its anchor sign
   triggers re-sampling up to K; if it still conflicts, `judge` raises **`JudgmentError`** and writes
   nothing (charter Part 7). It does **not** auto-downgrade the rating.
5. **No invented numbers / no forged provenance:** the LLM authors only ratings/narrative text; anchors and
   provenance are code-stamped; the final bundle passes `check_scorecard`.
6. **Document/finding text is data, not instructions** (charter Parts 8/26) — the judgment prompt isolates
   the briefing content from the instruction frame.
7. All tests deterministic via `RecordedClient`; the single live test is **skipped by default** unless its
   env flag is set.

---

## 4. Architecture

### 4.1 New modules (adapters bolt onto the frozen core)

```
gpu_agent/
  judgment/
    __init__.py
    briefing.py     build_briefing(findings) -> Briefing            # deterministic: anchors + evidence digest
    map.py          DIMENSION_MAP, DIMENSION_POLARITY (code defaults)# indicatorId→dim, dim→demand|supply
    prompt.py       SYSTEM + build_user_prompt(briefing)            # rubric + doctrine + injection boundary
    judge.py        judge_findings(findings, client, ...) -> JudgmentBundle  # sample N, aggregate, backstop
  cli.py            + `judge` and `pipeline` subcommands; `score`/`run` read narrative.json (MODIFY)
fixtures/
  recorded/         + recorded judgment responses (N per scenario, keyed/ordered for majority+spread)
tests/              judgment unit tests + recorded extract→judge→score integration + gated live smoke
```

The **frozen core is untouched.** `judgment/` depends on `schema.finding`, `schema.scorecard`,
`scoring.dmi_smi_contribution` (the primitive it reuses), `gate.check_scorecard`, and the `LLMClient` port —
never the reverse (core spec §13.1).

### 4.2 Data flow

```
gated Finding[]  ─►  briefing.build_briefing  ─►  Briefing{ anchors: dict[str,float], evidence digest }
                          │ (pure, deterministic — anchors from polarity·magnitude/3)
                          ▼
        judgment.prompt.build_user_prompt(briefing) ─► LLMClient.complete_json(schema=JudgmentResult) × N
                          │  (instruct-JSON → Pydantic validate → retry, per sample)
                          ▼
        aggregate: majority rating per dim + spread → candidate DimensionRating[] (+ narrative)
                          │  anchor-conflict? → re-sample up to K → else JudgmentError
                          ▼
        JudgmentBundle{ ratings, anchors, narrative, confidence } ─► check_scorecard backstop
                          ▼
        ratings.json / anchors.json / narrative.json  ─►  (existing) build_scorecard → score/run
```

`complete_json` is the only place that talks to a model; everything before and after it is deterministic and
either reuses or is covered alongside the core's tests.

---

## 5. Key design decisions

### 5.1 Deterministic briefing book — anchors from the scoring primitive
`build_briefing(findings)` computes, per dimension `d`:

```
anchor[d] = mean over findings f mapped to d of ( polarity(f, d) · f.magnitude / 3 )
```

reusing the exact `polarity·magnitude/3` shape of `scoring.dmi_smi_contribution`. `polarity(f, d)` reads
`f.polarityDemand` when `d` is a **demand-track** dimension and `f.polaritySupply` when `d` is a
**supply/structure-track** dimension (`DIMENSION_POLARITY`). Each term lies in `[-1, 1]`, so the mean lies in
`[-1, 1]` — the range the gate's `_rating_consistent_with_anchor` already assumes (positive rating needs
`anchor > -0.5`, negative needs `anchor < 0.5`). A dimension with **no mapped findings gets no anchor**
(omitted from the dict) — the gate skips `None` anchors, so purely-qualitative dimensions are judged without
a numeric bound. The briefing also carries an evidence digest (per dimension: the mapped findings' ids,
statements, polarity, magnitude, confidence) so the LLM judges grounded in the same findings the anchor was
built from. `build_briefing` takes **only** `findings` — no clock, no LLM — so it is fully deterministic and
unit-testable in isolation.

### 5.2 Dimension mapping — code default (YAGNI)
`map.py` ships two code-default dicts: `DIMENSION_MAP: dict[str, str]` (`indicatorId → dimension`, e.g.
`D2/D6 → momentum`, `grossMargin → unitEconomics`, `S9 → competitiveStructure`, `S10 → bottleneck`, plus the
structural indicators for `moat`/`strategicRisk`) and `DIMENSION_POLARITY: dict[str, str]` (each dimension →
`"demand"` or `"supply"`). Unmapped `indicatorId`s simply contribute to no anchor (and are logged, not
dropped — they still travel as findings). This stays a code default for now; promoting it to an
assignment-driven config is a later change behind the same call site (no schema churn until there's a
demonstrated per-category need).

### 5.3 Judgment LLM contract
Per call the LLM returns a `JudgmentResult` (validate-and-retry via the port):

```
JudgmentResult = {
  dimensions: { <dim>: { rating, direction, findingIds, rationale } },   # one entry per of the 6 dimensions
  narrative: str,
}
```

`rating`/`direction` reuse the frozen `DimensionRating` literals; `findingIds` must cite ids present in the
briefing (the gate enforces this downstream). The LLM authors **only** these analytic fields — it never
emits an anchor or a `confidence` object; code attaches the anchor (from the briefing) and the
sampling-derived confidence. `JudgmentResult` uses `extra="forbid"` so the model cannot smuggle extra keys
(mirrors `FindingDraft`).

### 5.4 Self-consistency sampling & confidence
`judge_findings(..., samples=N)` calls `complete_json` N times (default **3**). Per dimension it takes the
**majority `rating`** (ties broken toward the more conservative / lower rating); `direction`, `findingIds`,
and `rationale` are taken from the majority run, and the **narrative** is taken from that same majority run
(so the prose stays internally coherent rather than stitched). The **spread is recorded verbatim** in that
dimension's `confidence.basis` (e.g. `"2/3 Strong, 1/3 Mixed"`). **Confidence is capped on disagreement:**
unanimous → may be `high`; any split → capped at `medium`. This is a **schema-free** change — it rides in the
existing `Confidence.basis`/`level` fields. *Honest caveat:* recorded responses or low intra-model variance
may yield little spread; the design **measures** spread, it does not manufacture it (charter Part 1).

### 5.5 Anchor-conflict handling — re-sample then raise (charter Part 7)
After aggregation, each candidate rating is checked against its anchor with the gate's own
`_rating_consistent_with_anchor` rule. If a rating conflicts (e.g. `Strong` against an anchor `< -0.5`),
`judge` **re-samples up to K additional times** and re-aggregates. If the majority still conflicts, it raises
**`JudgmentError`** (carrying the offending dimension, rating, and anchor) and **writes nothing** — a gate
failure is re-run, never committed as a partial. It does **not** silently downgrade the rating to fit the
anchor (the rejected design): code overriding judgment would violate Part 17, and masking a genuine
model-vs-evidence conflict is exactly what the gate exists to surface.

### 5.6 Gate backstop
Even after §5.5, the assembled `JudgmentBundle` (ratings + code-attached anchors + narrative over the input
findings) is run through the existing `check_scorecard` before writing, catching anything the per-dimension
check misses (e.g. a `findingId` citing an unknown finding, an empty `findingIds`). A backstop failure raises
`JudgmentError`. This guarantees `judge`'s output is always gate-valid before `score`/`run` ever sees it.

### 5.7 Prompt injection boundary (charter Parts 8/26)
`SYSTEM` states the rubric (the rating scale, "ratings are judgment bounded by the anchor", cite findings by
id) and the doctrine; the briefing is passed in a clearly delimited block labeled untrusted data, with an
explicit instruction that its content is **evidence to weigh, never instructions to follow**. The prompt
**states each dimension's anchor sign up front** so the model judges with the bound visible. `judge` never
re-prompts or branches on briefing/finding text.

---

## 6. Error handling

- **Schema-invalid output** → the port's validate-and-retry (extraction §5.2); exhausted on a sample →
  `LLMError` (the run fails, not a silent skip).
- **Anchor conflict after re-sampling** → `JudgmentError` (§5.5); nothing written.
- **Gate backstop failure** → `JudgmentError` with the violations (§5.6).
- **Unmapped `indicatorId`** → contributes to no anchor; logged (CLI stderr), not an error.
- **Backend/transport error** → typed `LLMError` from the real backends; `RecordedClient` raises a clear
  "no recorded response" error so missing/short fixtures (fewer than N+K recordings) fail loudly in tests.
- **Untrusted content** → never redirects the task (§5.7).

---

## 7. CLI & pipeline wiring

- **`judge --findings <file> --out <dir> [--assignment <file>] [--samples 3] [--backend …]
  [--recorded <file>] [--model …]`** — loads gated `Finding[]`, builds the briefing, samples the LLM, and
  writes `ratings.json` / `anchors.json` / `narrative.json` into `<dir>`. `--recorded` injects a
  `RecordedClient` (offline, $0); otherwise `make_client(backend)`.
- **`pipeline --docs <dir> --assignment <file> --out <dir> [--as-of …] [--samples 3]
  [--recorded-extract <file>] [--recorded-judge <file>] [--backend …]`** — chains
  `extract → judge → score` in one invocation; each stage keeps its own `--recorded` option so the whole
  chain can run deterministically.
- **`score`/`run` (MODIFY):** read `narrative.json` and the judged `confidence` from the fixtures dir **when
  present**, else fall back to the current hardcoded placeholder (`"MVP scorecard."`,
  `Confidence(level="medium", basis="fixture run")`). This keeps every existing fixture run working
  unchanged while letting judged bundles flow through (core spec §13.5: stages stay independently runnable).

---

## 8. Testing strategy (TDD-first)

- **Unit — anchor math:** known findings (using the golden `D2`/`S9`/etc. indicator/polarity/magnitude
  values) → assert exact `anchor[d]` per `mean(polarity·magnitude/3)`, demand vs supply track selection, and
  that an unmapped/empty dimension yields **no** anchor key.
- **Unit — aggregation:** N `JudgmentResult`s that split on a dimension → assert majority rating, the
  conservative tie-break, the `confidence.basis` spread string, and confidence capped at `medium`; a
  unanimous set → may stay `high`.
- **Unit — anchor-conflict:** recorded samples whose majority contradicts the anchor → assert re-sample up to
  K then `JudgmentError` (no auto-downgrade, nothing written).
- **Unit — gate backstop:** a candidate bundle that passes the per-dimension check but trips
  `check_scorecard` (e.g. unknown `findingId`) → `JudgmentError`.
- **Integration (Stage 1+2):** `RawDocument` fixture + recorded extract responses + recorded judge responses
  → `pipeline` (extract → judge → score) → assert a `check_scorecard`-valid scorecard, exercising the
  `narrative.json` read path in `score`.
- **Live smoke (gated):** one test hitting a real backend, **skipped unless** `GPU_AGENT_LIVE_LLM=1` (and the
  credential) is set — proves the real judge wiring without making CI depend on the network.

---

## 9. Modularity & extensibility contract (core spec §13)

- The **`LLMClient` Protocol** is reused unchanged — `judge` adds a backend-agnostic caller, no port change
  (§13.2). Adding a backend remains a new class with zero caller change.
- The **frozen core is untouched** — `judgment/` consumes `schema`, `scoring`, `gate`; the gate's
  anchor/findingId rules remain the single source of truth and `judge` defers to them rather than
  re-implementing (§13.1).
- The **briefing builder is a pure, isolated unit** (findings → anchors+digest), separately testable and free
  of any LLM or clock dependency.
- The **`judge`/`pipeline` subcommands** join `extract`/`run`/`score` over the shared store, each still
  runnable in isolation; the `narrative.json` read is additive and back-compatible (§13.5).
- **YAGNI guards:** code-default dimension map (no assignment schema change), no metric-history store, no new
  model providers — only the recorded test seam plus the existing backends.

---

## 10. Open questions

None blocking. Both prior open points are resolved: (a) anchor conflict → **re-sample then raise
`JudgmentError`** (§5.5); (b) `DIMENSION_MAP` → **code default for now** (§5.2). The exact `K`
(re-sample budget, default ~2), the precise default `DIMENSION_MAP` entries, and the judge model id are
parameterized and finalized at build time.
