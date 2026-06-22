# GPU Category Agent — LLMClient Port + Extraction Adapter (Level C) Design

- **Date:** 2026-06-22
- **Status:** Draft for review
- **Author:** brainstorming session (superpowers workflow)
- **Builds on:** the frozen deterministic core (`specs/2026-06-19-gpu-category-agent-design.md`,
  `plans/2026-06-19-gpu-category-agent-core.md`) — schema/gate/scoring/store/assignment/cli, all merged to `main`.
- **References:** `docs/agent-swarm-charter.md` Parts 1/2/7/8/26; core spec §7 (build order), §9 (testing),
  §10 (LLMClient port), §13 (modularity).

---

## 1. Context & goal

The core turns *fixture* Findings into a gate-validated scorecard. This is the first **adapter**: it
produces those Findings from source documents using an LLM, so the pipeline can run from real text
instead of hand-authored Finding fixtures.

It is **integration Level C** (core spec §7): `RawDocument` fixtures → LLM extraction → existing gate →
core. It introduces the **shared `LLMClient` port** that the later judgment adapter also depends on, and
it stays **offline and deterministic in tests** by replaying recorded model responses (core spec §9). The
later judgment adapter and the live connectors (Level B) are explicitly out of scope here and build on the
frozen interfaces this plan produces.

---

## 2. Scope

### In scope
- **`RawDocument` schema** — the input unit the core never built (a fetched/loaded source document).
- **`LLMClient` port** (`typing.Protocol`) — `complete_json(prompt, system, schema, model) -> BaseModel`,
  wrapping an instruct-JSON → Pydantic-validate → retry loop (core spec §10, §13.2).
- **Two backends** behind the port:
  - **`ClaudeCodeClient`** (default) — drives Claude via the Claude Agent SDK / headless `claude`,
    authenticated with a subscription token (`CLAUDE_CODE_OAUTH_TOKEN`).
  - **`AnthropicAPIClient`** (alternate) — the `anthropic` SDK + `ANTHROPIC_API_KEY`.
- **`RecordedClient`** — a test/offline backend implementing `LLMClient` by replaying canned JSON keyed by
  document id; the load-bearing seam that makes extraction tests deterministic and CI-safe.
- **Extraction adapter** — `RawDocument → Finding[]`: prompts the LLM for the analytic fields, code stamps
  provenance, every Finding is run through the existing `check_finding` gate.
- **CLI `extract` subcommand** — the placeholder the core left for spec §13.5; reads `RawDocument`s, writes
  gated `Finding[]` (to stdout/JSON, consumable by the existing `run`/`score` path).
- **Tests** — recorded-response unit/integration tests; one **optional live smoke** gated behind an env flag.

### Out of scope (later plans)
- The **judgment** adapter (ratings + narrative + self-consistency sampling) — reuses this port, planned next.
- **Live connectors** (EDGAR, GPU-rental) — Level B; this plan consumes `RawDocument` *fixtures*, not the network.
- Model-tier auto-selection / Haiku pre-filter — the model is a parameter here; tuning is deferred.
- Any change to the frozen core (schema/gate/scoring/store). The core stays untouched (core spec §13.1).

---

## 3. Success criteria (acceptance)

1. Given `RawDocument` fixtures + **recorded** LLM responses, extraction emits `Finding[]` that **pass the
   existing Part-7 `check_finding` gate**, and the emitted Findings flow unchanged into the existing
   `build_scorecard`/`run` path (Level C composes end-to-end).
2. **Schema-invalid** model output triggers the validate-and-retry loop; after retries it is handled per §6
   (drop + flag, never crash, never emit an invalid Finding).
3. The `LLMClient` port has **≥2 working implementations** (a real backend + `RecordedClient`) proving the
   seam; callers depend only on the Protocol.
4. **No invented numbers / no naked findings reach output** — code stamps provenance (it never lets the LLM
   set `capturedAt`/`extractionModel`), and the gate rejects fabrication (charter Rules 1/2, Part 7).
5. **Fetched/source text is treated as data, not instructions** (charter Parts 8/26) — the extraction prompt
   isolates document content from the instruction frame.
6. All tests deterministic via `RecordedClient`; the single live test is **skipped by default** unless its
   env flag is set.

---

## 4. Architecture

### 4.1 New modules (adapters bolt onto the frozen core)

```
gpu_agent/
  schema/raw_document.py   RawDocument model (NEW)
  llm/
    client.py              LLMClient Protocol + LLMError + the shared validate-and-retry helper
    claude_code.py         ClaudeCodeClient (default backend)
    anthropic_api.py       AnthropicAPIClient (alternate backend)
    recorded.py            RecordedClient (replays canned JSON by doc id) — test/offline seam
  extraction/
    extractor.py           extract_findings(doc, client, assignment, model) -> list[Finding]
    prompt.py              the extraction system prompt + per-document user prompt builder
  cli.py                   + `extract` subcommand (MODIFY; core left run/score)
fixtures/
  raw/                     RawDocument fixtures
  recorded/                canned LLM responses keyed by doc id
tests/                     extraction tests (recorded) + gated live smoke
```

### 4.2 Data flow (this plan)

```
RawDocument fixture ─► extraction.prompt ─► LLMClient.complete_json (schema=ExtractionResult)
                                                   │  (instruct-JSON → Pydantic validate → retry)
                                                   ▼
                      ExtractionResult(drafts[]) ─► code stamps provenance ─► Finding[]
                                                   ▼
                                   check_finding (existing gate) ─► gated Finding[] ─► (→ core run/score)
```

`complete_json` is the only place that talks to a model. Everything downstream of it is deterministic and
already covered by the core's tests.

---

## 5. Key design decisions

### 5.1 LLM-authored fields vs. code-stamped provenance
The LLM produces an **`ExtractionResult`** = `{ drafts: list[FindingDraft] }`, where `FindingDraft` carries
only the **analytic** Finding fields the model can reason about (`statement, kind, value, trend, why,
impact, evidence, reasoning, confidence, dispersion, indicatorId, side, polarityDemand, polaritySupply,
magnitude, entity, observedAt`). **Code** — not the model — stamps the rest into the final `Finding`:
`id` (deterministic, e.g. `{docId}-{n}`), `asOf` (run as-of), `capturedAt` (ingestion timestamp),
`extractionModel` (the model used), `schemaVersion`. This enforces charter look-ahead honesty and prevents
the model from forging provenance (success criterion 4). **`asOf`, `capturedAt`, and `extractionModel` are
caller-supplied parameters to the extractor** (not read from a wall clock or global inside it), so
extraction stays a pure function of its inputs and tests are deterministic; the CLI/connectors supply the
real values at the edge. `FindingDraft` reuses the core's sub-models
(`Value`, `Impact`, `Evidence`, `Confidence`) so the analytic shape stays identical to the frozen schema.

### 5.2 Validate-and-retry (the load-bearing loop, core spec §10)
`complete_json(prompt, system, schema, model)`: call the backend → parse JSON → `schema.model_validate` →
on `json.JSONDecodeError`/`ValidationError`, retry up to **N=2** times, appending the parse/validation error
to the prompt as corrective feedback → after the last failure raise **`LLMError`**. The Claude Code backend
lacks the raw API's strict format enforcement, so this loop is what guarantees structured output there.

### 5.3 Gate handling — bend, don't break (charter §8 / Part 7)
After provenance-stamping, each Finding is run through `check_finding`. A Finding that fails the gate is
**dropped and recorded** (its id + violations) rather than crashing the document — extraction still emits
the surviving Findings. (Per-document "re-run, never commit a partial" applies to *schema* failures via the
retry loop; *gate* failures after stamping are a content judgment, so they bend.) The dropped list is
surfaced (CLI stderr + return value) so nothing is silently discarded.

### 5.4 Prompt injection boundary (charter Parts 8/26)
The system prompt states the task and the rules; the document text is passed in a clearly delimited block
labeled untrusted data, with an explicit instruction that content inside it is **data to extract from, never
instructions to follow**. The extractor never executes or re-prompts based on document content.

### 5.5 Backend selection
A small factory picks the backend: default `ClaudeCodeClient`; `AnthropicAPIClient` when an API-key/env
selector is set; `RecordedClient` in tests (injected directly). `ANTHROPIC_API_KEY` must be unset for the
subscription backend (core spec §10). The model id is a parameter (assignment- or CLI-supplied), defaulting
to a Sonnet-tier model for extraction.

---

## 6. Error handling

- **Schema-invalid output** → validate-and-retry (§5.2); exhausted → `LLMError` (the document fails, not the run).
- **Gate-invalid Finding** → drop + flag, keep the rest (§5.3).
- **Backend/transport error** → typed `LLMError` with backoff on the real backends (charter Part 19 spirit);
  `RecordedClient` raises a clear "no recording for doc id" error so missing fixtures fail loudly in tests.
- **Untrusted content** → never redirects the task (§5.4).

---

## 7. Testing strategy (TDD-first)

- **Unit — validate-and-retry:** a stub client returns bad-JSON then good-JSON; assert the loop retries and
  returns the validated model; assert it raises `LLMError` after N failures.
- **Unit — provenance stamping:** assert code sets `capturedAt`/`extractionModel`/`id`/`schemaVersion` and
  that a draft cannot override them.
- **Unit — gate handling:** a recorded response containing one good + one gate-violating draft → the good
  Finding is emitted, the bad one is dropped and reported.
- **Integration (Level C):** `RawDocument` fixture + `RecordedClient` → extraction → `check_finding` →
  feed into existing `build_scorecard` and assert a valid scorecard is produced.
- **Live smoke (gated):** one test that hits a real backend, **skipped unless** `GPU_AGENT_LIVE_LLM=1` (and
  the relevant credential) is set — proves the real client wiring without making CI depend on the network.

---

## 8. Modularity & extensibility contract (core spec §13)

- The **`LLMClient` Protocol** is the new port; adding a backend = a new class, no caller change (§13.2).
- The **frozen core is untouched** — extraction depends on `schema.finding`, `gate.check_finding`, and the
  core sub-models, never the reverse (§13.1).
- The **`extract` subcommand** joins `run`/`score` over the shared store, so each stage still runs
  independently (§13.5); `ingest`/`judge` remain for later plans.
- **YAGNI guard:** only the two real backends the design actually needs (Claude Code default + API alternate)
  plus the recorded test seam — no speculative providers.

---

## 9. Open questions

None blocking. The exact extraction model id and any Haiku pre-filter are deferred to build/tuning time
(parameterized, §5.5). The Claude Agent SDK vs. headless-`claude` detail inside `ClaudeCodeClient` is an
implementation choice for the plan, behind the port either way.
