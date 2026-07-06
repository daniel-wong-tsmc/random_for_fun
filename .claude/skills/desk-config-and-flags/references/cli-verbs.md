# CLI verb-by-verb flag reference

Source of truth: the `main()` argparse block in `gpu_agent/cli.py` (lines ~933–1099). Every table below was transcribed from that block and cross-checked against `.venv/Scripts/python -m gpu_agent.cli <verb> --help` on 2026-07-05 at main @ `639c00d`. When this file and the live `--help` disagree, the live `--help` wins — update this file.

Conventions:
- **req** = argparse `required=True`. Some verbs enforce extra requirements in their handler (noted).
- **vintage-checked** = `type=_as_of`, i.e. `^\d{4}-\d{2}(-\d{2})?$` (`cli.py:56–60`). `--as-of` rows WITHOUT this note accept any string (open gap).
- All commands run from repo root as `.venv/Scripts/python -m gpu_agent.cli <verb> ...` (PowerShell and Git Bash identical).

---

## run / score (legacy fixture-driven MVP verbs)

Not the live path. They compute + gate a scorecard from a fixtures dir; `score` prints DMI/SMI and never persists; `run` appends to the store.

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--assignment` | req | — | Assignment JSON path |
| `--fixtures` | req | — | Dir with `findings.json`, `ratings.json`, `anchors.json` |
| `--out` | | `store` | `run` only; JsonStore root |

## extract

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--docs` | req | — | Dir of RawDocument JSON files (`gather-log.json` skipped) |
| `--as-of` | req | — | vintage-checked |
| `--out` | | None | Gated findings JSON path |
| `--model` | | `claude-opus-4-8` | Provenance stamp (`Finding.extractionModel`), not a live model call |
| `--captured-at` | | now (UTC) | Pin ONE value shared with `pipeline` (F62) |
| `--backend` | | `claude_code` | Default raises by design; `anthropic_api` = dormant, forbidden live |
| `--recorded` | | None | JSON **array of serialized-object strings**, one per doc in sorted doc order; count must equal doc count or exit 2 |
| `--persona` | | None | F26; None = byte-identical legacy "GPU market" prompt |
| `--emit-prompt` | | off | Print `{system, schema, docs:[{id,user}]}`, no LLM, exit |

## ingest

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--blobs` | req | — | Bare blob array or `{rounds, skipped, blobs}` envelope |
| `--out` | req | — | Dir for RawDocument snapshots + `gather-log.json` |
| `--primary-sources` | | `sec.gov` | Comma-separated primary domains. Fallback only — the gather flow supplies the manifest's raw-JSON `primaryDomains` |
| `--as-of` | req | — | vintage-checked; scopes doc/finding ids (F52), keys the L1 seen-index |
| `--dedup-store` | | None | Store root for L1 seen-doc dedup (`seen_docs.jsonl`). None = no L1 filtering (standard mode) |

## wiki-ingest

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--findings` | req | — | JSON array of gated Findings |
| `--store` | | `store` | Holds `wiki/` and `findings/` |
| `--as-of` | req | — | vintage-checked |
| `--category` | | None | Category id for auto-created entity pages |
| `--recorded` | | None | Recorded IngestResult JSON (enrichment brain; F14-gated) |
| `--emit-prompt` | | off | Print the enrichment bundle, no LLM, exit |

## wiki-dedup

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--findings` | req | — | This cycle's gated Findings |
| `--store` | | `store` | |
| `--as-of` | req | — | vintage-checked |
| `--out-findings` | | None | Deduped NEW+UPDATE stream (feeds wiki-ingest) |
| `--report` | | None | DedupReport JSON path (else stdout). Daily runs write `store/<id>/dedup-<asOf>.json` (tracked) |

## wiki-lint

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--store` | | `store` | |
| `--as-of` | req | — | vintage-checked |
| `--prev-as-of` | | auto | Prior cycle asOf for the diff window (default: derived from the log) |
| `--out` | | None | LintReport JSON path |

## wiki-lifecycle

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--store` | | `store` | |
| `--as-of` | req | — | vintage-checked |
| `--apply` | | off | Apply promotions/prunes (default: propose-only, read-only) |
| `--report` | | None | LifecycleReport JSON path |

## corpus

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--store` | | `store` | |
| `--category` | req | — | Scopes wiki pages |
| `--as-of` | req | — | **NOT vintage-checked** (`cli.py:995` lacks `type=_as_of`) — open defense-in-depth gap; do not rely on the CLI seam here |
| `--window-days` | | 45 | `WINDOW_DAYS_DEFAULT` from `gpu_agent/corpus.py` |
| `--fresh` | | None | This cycle's gated findings; enables assemble mode |
| `--out-merged` | | None | Required with `--fresh` |
| `--out-deduped-fresh` | | None | Write-back stream for wiki-ingest |
| `--report` | | None | CorpusReport JSON path |

## judge

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--findings` | req | — | JSON array of gated Findings |
| `--out` | | None | Handler exits 2 if omitted without `--emit-prompt` |
| `--samples` | | 3 | Recorded answer count must equal this or exit 2 |
| `--model` | | `claude-opus-4-8` | Provenance stamp |
| `--backend` | | `claude_code` | Same doctrine as extract |
| `--recorded` | | None | JSON array of `samples` serialized JudgmentResult strings |
| `--no-voice-lint` | | off | **BYPASS** — F67 lint skip; see SKILL.md Axis 2 before touching |
| `--no-sufficiency` | | off | **BYPASS** — F63 gate skip; see SKILL.md Axis 2 before touching |
| `--category` | req | — | e.g. `chips.merchant-gpu` |
| `--persona` | | None | F26 |
| `--emit-prompt` | | off | Print `{system, schema, user, samples}` with MEMORY + citation groups + dated rows |
| `--store` | | `store` | Memory source for `--emit-prompt` (F5) AND for the sufficiency gate in `--recorded` mode |

Note: `judge` has NO `--as-of` flag — the vintage comes from the findings themselves. Sufficiency memory here reads `--store`; at the pipeline seam it reads `--corpus-store` and is INERT without it.

## thesis

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--findings` | req | — | |
| `--store` | | `store` | Holds `theses/<category>/` |
| `--category` | req | — | |
| `--as-of` | req | — | vintage-checked |
| `--emit-prompt` | | off | |
| `--recorded` | | None | A SINGLE ThesisAnswer JSON object (not an array) |
| `--seed` | | None | First-run seed file; default `registry/theses.<category>.json` |
| `--persona` | | None | |

## eval

Positional `action` ∈ `emit-brain | record-brain | emit-grade | record-grade | verdict | rebaseline`.

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--cases` | | `fixtures/evals/cases` | |
| `--out` | | `""` | Run dir; required (handler-enforced) for emit-*/record-* |
| `--as-of` | | `""` | Required (handler-enforced) for `record-grade`; **NOT vintage-checked** |
| `--baseline` | | `fixtures/evals/baseline.json` | NEVER hand-edit |
| `--runs` | | None | `verdict`: 1–2 run dirs. `rebaseline`: **exactly 3** (enforced in `evals/harness.py:276–277`) |
| `--verdict` | | `""` | Path to `verdict.json` proving the gate PASS (rebaseline governance) |
| `--force` | | off | User-only; pairs with `--reason`, stored permanently in the baseline |
| `--reason` | | `""` | |
| `--human-review` | | `""` | Free-text provenance note |

The v1 `rebaseline --out` form is GONE (the error message says so verbatim). `verdict` writes `verdict.json` into the LAST `--runs` dir and requires a schema-v2 baseline.

## pipeline

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--docs` | req | — | |
| `--assignment` | req | — | Assignment `asOf` mismatching `--as-of` prints an F50 note and is overridden |
| `--out` | | `store` | JsonStore root; mints `store/<id>/<asOf>-v<N>.json` (append-only) |
| `--as-of` | req | — | vintage-checked |
| `--samples` | | 3 | |
| `--model` | | `claude-opus-4-8` | |
| `--captured-at` | | now (UTC) | MUST equal the value used at `extract --recorded` (F62) |
| `--backend` | | `claude_code` | |
| `--recorded-extract` | | None | Count must equal doc count or exit 2 |
| `--recorded-judge` | | None | The PRODUCTION judging path (the live cycle never calls `judge --recorded` directly) |
| `--no-voice-lint` | | off | **BYPASS** (see SKILL.md Axis 2) |
| `--no-sufficiency` | | off | **BYPASS**; note the sufficiency gate at this seam only runs at all when `--corpus-store` is given (memory source) — without it the gate is silently inert |
| `--corpus-store` | | None | Enables the F62 windowed store merge AND supplies sufficiency memory; live cycles always pass it |
| `--corpus-window-days` | | 45 | |
| `--corpus-report` | | None | CorpusReport JSON path |

## cycle-plan

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--scope` | req | — | `category:<id>` \| `layer:<id>` \| `all` (`market` is an accepted alias for `all`, `gpu_agent/cycle.py:26`) |
| `--assignments` | | `fixtures` | Dir of `asg.<category>.json` files |
| `--taxonomy` | | `docs/taxonomy.json` | Via `TAXONOMY_PATH` (env-overridable) |
| `--out` | | None | **HAZARD (F74, open):** plain `write_text` overwrite (`cli.py:811–812`). Diff `store/cycle-log.json` before pointing `--out` at it |

Missing assignments print `SKIPPED <id>: skipped-no-assignment` to stderr, never silent. Stages are hardcoded: category=active, layer/main=deferred.

## report

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--scorecard` | req | — | Path to the scorecard JSON |
| `--store` | | `store` | Prior auto-discovery root |
| `--out` | | None | Write to file instead of stdout |
| `--registry` | | `registry/indicators.json` | Via `REGISTRY_PATH` (env-overridable) |
| `--render-ts` | | now (UTC) | Pin for byte-reproducible output |
| `--daily` | | off | Lead with WHAT MOVED instead of STATE OF THE MARKET (F67 §4); same renderer otherwise |
| `--prior` / `--no-prior` | | auto | Mutually exclusive group: explicit prior path vs suppress lookup (Δ columns show —) |

The handler reconfigures stdout to UTF-8 (report emits ↑↓→ — Δ glyphs); subprocess callers should set `PYTHONIOENCODING=utf-8`.

## web-reach-ensure

| Flag | Req | Default | Notes |
|---|---|---|---|
| `--check-only` | | off | Health checks only, never installs |
| `--json` | | off | Machine-readable `{webReach: {...}}` block, suppresses log lines |
| `--timeout` | | 600 | Seconds per install command; health checks are hard-capped at 60s (`_HEALTH_TIMEOUT`) |

Exit 0 only if every enabled tool is `ok`/`installed-ok`. Registry path is resolved relative to CWD — invoke via `scripts\web-reach-ensure.cmd --json` (Windows) or `sh scripts/web-reach-ensure --json`, which cd to repo root first.

---

## Cross-verb invariants worth memorizing

- Recorded answer shapes: extract = array of strings (one per doc, sorted order); judge = array of `samples` strings; thesis = ONE object. String-vs-object and count mismatches are the #1 replay failure mode (exit 2 or raw TypeError, not a friendly gate message).
- `--emit-prompt` verbs are read-only prompt printers — always safe to run.
- Every mutating store write is append-only (`JsonStore.append` mints the next `-v<N>`; `FindingStore` raises on id collision with differing content). The ONE known overwrite exception is `cycle-plan --out` (F74).
- Gate rejection stderr prefixes the operator greps for: `DROPPED` (extract), `voice-lint: `, `sufficiency: ` (judge/pipeline), `GATE FAILED` / `REGISTRY GATE FAILED` (build paths), `BRAIN GATE FAILED` / `GRADE GATE FAILED` (eval), `SKIPPED` (cycle-plan), `DROPPED-KNOWN` (ingest L1).
