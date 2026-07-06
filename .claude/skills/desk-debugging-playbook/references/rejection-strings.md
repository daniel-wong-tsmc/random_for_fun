# Rejection-string catalog (verified against source, 2026-07-05)

Every deterministic gate's exact output, enumerated from the code that emits it.
`<id>` is a finding id (`<docId>-<n>`), `<dim>` one of the six dimensions, `<fid>` a cited
finding id. Grep for the SUFFIX text: finding-level messages prefix `<id>: `, scorecard- and
judgment-level messages prefix `<dim>: `.

All strings below were read from source at main @ 11ffd61 (2026-07-05). Re-verify with the
commands in SKILL.md "Provenance and maintenance" before trusting them after a Part-33
migration touches `gate.py`.

## 1. Extraction seam checks — `gpu_agent/extraction/extractor.py:97-127`

Printed one line per dropped draft: `DROPPED <docId>-<n>: <violations joined by '; '>` on
stderr (`cli.py:333` for `extract`, `cli.py:734` for `pipeline`; pipeline adds a summary line
`gate dropped <n> finding(s)`).

| String | Meaning / F-item |
|---|---|
| `unregistered indicator: <indicatorId>` | Brain invented an indicator id not in registry/indicators.json. Pre-F55 this was the #1 drop cause; vocab is now baked into the emitted prompt — if you see it live, the brain ignored the vocab list. |
| `<id>: price unit '<unit>' != registered unit '<unit>' for <indicatorId>` | F53. Price draft's `value.unit` differs from the registry canonical unit. Also fires when the brain mislabeled the indicator (wrong indicator implies wrong canonical unit). |
| `<id>: non-finite value` | NaN/Inf in `value.number`. |
| `<id>: excerpt not found in source document` | F2b. Whitespace-folded but CASE-SENSITIVE substring check. Paraphrased "excerpts" always drop. |
| `<id>: evidence url does not match source document` | F2c. Every evidence.url must equal the document's own url — cross-document citation is forbidden at this seam (corroborators are merged later by L2 dedup, F10). |

## 2. Finding gate — `gpu_agent/gate.py:16-62` (`check_finding`)

Runs inside extraction (with taxonomy targets) and again inside `check_scorecard` (without).

| String | Meaning / F-item |
|---|---|
| `<id>: measured finding missing value` | Cardinal-sin guard: measured ⇒ number. |
| `<id>: non-measured finding has invented value` | Cardinal-sin guard: number without measured kind. |
| `<id>: measured finding missing evidence` / `<id>: observed finding missing evidence` | F2a. |
| `<id>: missing why` | Explainability doctrine (charter Part 7). |
| `<id>: hypothesis missing reasoning` | |
| `<id>: hypothesis confidence capped at medium` | Hypotheses can never be high confidence. |
| `<id>: secondary-only evidence cannot support high confidence (<k> distinct publishers < <n>)` | F2e, contract v1.3: ≥N distinct publishers (registry/corroboration.json, N=3) unlock high confidence on secondary-only evidence. Publisher = URL netloc, www-stripped (`gpu_agent/publisher.py`). Open F72: wire syndication defeats this count — see gate-integrity-campaign. |
| `<id>: static price level (trend unknown) must carry polarity 0` | F8: price is an overlay, a level without a baseline is not momentum. |
| `<id>: finding affects neither demand nor supply track` | Non-price finding with both polarities 0. Note structural-side findings are NOT exempt — only `side == "price"` is. |
| `<id>: observedAt not ISO (YYYY-MM-DD...)` | F17. Prefix check only — `2026-07` fails, `2026-07-05garbage` passes the shape check. |
| `<id>: evidence date not ISO (YYYY-MM-DD): '<date>'` | F17. |
| `<id>: future-dated evidence <date> vs asOf <asOf>` | Grain-aware lexical compare: with month-grain asOf `2026-07`, evidence dated `2026-07-31` passes even on July 1. |
| `<id>: impact.targets empty` / `<id>: impact.mechanism empty` | F21. |
| `<id>: impact target '<t>' not in taxonomy` | Only when `valid_targets` is passed — i.e. EXTRACTION TIME ONLY. `check_scorecard` re-runs `check_finding` without it. |

## 3. Scorecard gate — `gpu_agent/gate.py:76-94` (`check_scorecard`)

Dimension-prefixed (not finding-prefixed). Raised as `GateError` in `build_scorecard`
(pipeline never persists a violating scorecard) and as `JudgmentError` via the judge's
`_gate_backstop`.

| String | Meaning |
|---|---|
| `<dim>: rating cites no findings` | |
| `<dim>: cites unknown finding <fid>` | |
| `<dim>: rating <rating> contradicts anchor a=<x.xx>` | Anchor bound, tolerance ±0.15 (F36). Note the `a=` — the judgment-seam variant of this message (below) has no `a=`. |
| `<id>: evidence self-references the dashboard output` | Evidence source `AI Market State dashboard` or url containing `market-state.json`. |

## 4. Judgment conflicts — `gpu_agent/judgment/judge.py:109-152`

These are the strings carried by `JudgmentError`. **In recorded mode you usually never see
them**: the resample loop calls the LLM client again, the `RecordedClient` is empty, and the
run dies with `LLMError: no recorded response for this call` instead. Use
`scripts/judge_conflicts.py` (this skill) to surface them.

| String | Meaning |
|---|---|
| `<dim>: rating <rating> contradicts anchor <x.xx>` | Anchor bound at the judgment seam (no `a=` prefix). |
| `<dim>: cites <fid> which is not in its indicator group` | Sample cited a finding outside the dimension's code-computed citation group. |
| `categoryStatus.bottleneck '<x>' not a dimension` | Bottleneck must be one of the six dimensions. |
| `no recorded response for this call` | `LLMError` from `gpu_agent/llm/recorded.py:20` — the mask over all of the above in recorded mode, OR a genuine answer-count shortfall that got past the CLI count check (shouldn't happen; count is checked first, exit 2). |
| `no valid output after 3 attempts: <err>` | `LLMError` from `gpu_agent/llm/client.py:27`. Recorded answer failed `json.loads`/pydantic three times (RecordedClient re-serves the SAME answer on retry, F11). Classic cause: markdown code fences — there is NO fence-stripping anywhere in gpu_agent. |

Uncaught by the CLI: `JudgmentError` and `LLMError` surface as raw Python tracebacks (only
`RegistryError` is caught on the judge/pipeline paths, printing `REGISTRY GATE FAILED:`).

## 5. Voice lint (F67) — `gpu_agent/reader.py:109-129` via `cli.py:_voice_lint_samples`

Printed as `voice-lint: sample <n>: <field>: <violation>` on stderr, exit 1. Runs on
`judge --recorded` AND `pipeline --recorded-judge` (both, or it would be dead code in
production — the live cycle only uses the pipeline path). `sample <n>` is 1-based dispatch
order and tells you WHICH answer to re-dispatch.

| String | Meaning |
|---|---|
| `<field>: indicator id '<id>' in exec-facing prose` | Registry ids (D2, apiArr…) may not appear in narrative/rationale/reason. |
| `<field>: finding id '<slug>-<8hex>-<n>' in exec-facing prose` | |
| `<field>: banned word '<w>'` | 12 banned words: delve(s), crucial, pivotal, robust, landscape, leverage(s), holistic, seamless, utilize(s). |
| `<field>: <n> sentences (max <m>)` | narrative max 3, each `<dim>.rationale` max 2, `categoryStatus.reason` uncapped. Splitter is regex with FIXED abbreviation lookbehinds (U.S., U.K., e.g., i.e., vs. only) — any other abbreviation followed by space+capital miscounts. See SKILL.md triage row. |
| `<field>: acronym '<A>' not on registry/acronyms.json allowlist` | All-caps tokens only (`CoWoS` never trips it); allowlist has 100 entries as of 2026-07-05 — a DATA file, extend it there, never weaken `lint_prose`. |
| `categoryStatus.constraintLabel: must name the concrete constraint, not a dimension` | Label equals a dimension name or contains "bottleneck". |
| `categoryStatus.constraintLabel: over 6 words` | |

## 6. Sufficiency gate (F63) — `gpu_agent/sufficiency.py:31-65`

Printed as `sufficiency: sample <n>: <violation>` on stderr, exit 1. INERT when memory is
None — see SKILL.md for the two silent-skip conditions.

| String | Meaning |
|---|---|
| `<dim>: rating changed <old>-><new> with insufficient evidence (no primary; <k> distinct publishers < <n>)` | A rating change vs prior-cycle MEMORY needs primary evidence or ≥N distinct publishers among the cited findings' evidence. |
| `categoryStatus.bottleneck: changed <old>-><new> with insufficient evidence (no primary; <k> distinct publishers < <n>)` | Same bar for a binding-constraint change. |

Direction-only changes, constraintLabel changes, and dimensions with no prior rating never
trigger (deliberate scope, module docstring).

## 7. Thesis gate — `gpu_agent/thesis.py` (gate_answer and book application)

Non-zero exit with violations on stderr; the thesis book is NEVER written on rejection.

`<label>: cites no findings` / `<label>: cites unknown finding <fid>` /
`<label>: missing mechanism` / `<label>: missing sensitivity` /
`<label>: missing falsifiableTrigger` / `<label>: trigger names no observable` /
`judgment for unknown thesis <id>` / `duplicate judgment for <id>` /
`no judgment for thesis <id>` / `proposal has unroutable title: '<title>'` /
`proposal duplicates thesis id <label>` / `proposal duplicates statement of <owner>`

## 8. Wiki enrichment gate (F14) — `gpu_agent/wiki/ingest.py:146-150`

Raised as `EnrichmentGateError` with ALL violations collected; nothing is written when it
fires. Only relevant on the separate `wiki-ingest --emit-prompt`/`--recorded` enrichment flow
— the standard run-cycle write-back is deterministic routing only and never dispatches the
enrichment brain.

`<pageId>: cites unknown finding <token>` / `<pageId>: uncited number <token>`

## 9. Gathering / ingest — `gpu_agent/gathering/ingest.py`, `dedup.py`, `cli.py:113-116`

| String | Meaning |
|---|---|
| `DROPPED [<i>] <url>: missing/empty fields: <fields>` | Blob missing url/content/source/date/entity. |
| `DROPPED-KNOWN <url>: seen-url (first seen <asOf>)` | L1 dedup hit. BOTH reasons are content-hash hits (`dedup.py:77-85`, F12: hash-before-URL); `seen-url` only adds that the URL was also known. A known URL with NEW content is never dropped. L1 runs only with `--dedup-store` (daily mode). |
| `DROPPED-KNOWN <url>: seen-content-hash (first seen <asOf>)` | Same content seen at a different URL, or a batch-internal repeat. |

## 10. CLI operator errors (exit 2) — `gpu_agent/cli.py`

| String | Where |
|---|---|
| `gpu-agent extract: error: recorded answers (<N>) != documents (<M>)` | cli.py:313 — extract answer array length must equal doc count, one string per doc in the emitted order. |
| `gpu-agent judge: error: recorded answers (<N>) != samples (<M>)` | cli.py:438 — judge answer array length must equal `--samples` (default 3). |
| `gpu-agent judge: error: --out is required` | cli.py:430. |
| `argument --as-of: --as-of '<s>' must be YYYY-MM or YYYY-MM-DD` | `_as_of` validator (cli.py:56-60, F56). NOT enforced on the `corpus` verb (known gap) or `eval --as-of`. |

## 11. Top-level banners

| String | Where / meaning |
|---|---|
| `GATE FAILED:` + one violation per line | `run`/`score` fixture paths only (cli.py:1155-1157). |
| `REGISTRY GATE FAILED:` | RegistryError on corpus/judge/thesis/eval/pipeline — registry file missing/invalid or unresolvable indicator at load time. |
| `CYCLE SCOPE ERROR: <e>` | `cycle-plan` bad `--scope` (must be `all`/`market`, `category:<id>`, `layer:<id>`). |
| `SKIPPED <categoryId>: skipped-no-assignment` | cycle-plan stderr: taxonomy category with no `fixtures/asg.<id>.json`. Expected for 32 of 34 categories today — not an error. |
| `gpu-agent pipeline: corpus error: <e>` | F62 corpus assembly failed (exit 1). |
| `note: assignment asOf <a> overridden by run asOf <b> (F50)` | INFORMATIONAL, stderr — the run's `--as-of` owns the scorecard label. Not an error. |
| `gate dropped <n> finding(s)` | pipeline stderr summary after per-finding DROPPED lines. |

## 12. Eval brain/grade gates — `gpu_agent/evals/harness.py:26-66`

Recorded in `brain-gates.json` / printed by `eval record-brain` (exit 1 = gate failure = the
candidate prompt produces invalid output — SIGNAL, not an eval bug).

| String | Meaning |
|---|---|
| `extract parse/gate error: <e>` | Malformed extract answer (JSON/schema). |
| `DROPPED <id>: ...` | Real extraction gates over the eval case (same strings as §1-2). |
| `judge parse error: <e>` | Malformed judge answer. |
| any §4 or §5 string | Eval judges gate with samples=1, resample_budget=0 — conflicts DO surface cleanly here (unlike live recorded mode), plus the same voice lint. |
| `thesis parse error: <e>` | Malformed thesis answer. |

Grader-side: `GradeResult` forbids extra keys — graders emitting `score_note`/`verdict` keys
(3 occurrences on 2026-07-05, see docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md)
fail pydantic with `extra_forbidden`; fix is a shape-only re-dispatch of THAT grader ("keep
your scores/evidence; fix the structure"). Eval mechanics beyond this: desk-validation-and-qa.
