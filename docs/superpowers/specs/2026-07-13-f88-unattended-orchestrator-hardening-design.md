# F88 — Unattended-orchestrator hardening: threat model, injection wall, supply-chain pin (design)

**Date:** 2026-07-13 · **Status:** user-approved design (interactive), build authorized same day
· **Backlog:** F88 (2026-07-13 documentation gap review, `docs/fix-backlog.md`)

## 1. Problem

Since 2026-07-13 the scheduled daily runs headless with `--dangerously-skip-permissions`
(F83 flip): a full-tool orchestrating session — file writes, arbitrary commands, git push to a
public repo — reads open-web content daily with nobody watching. The F16/Part-8 injection
boundary protects the *brains* (tool-less, content fenced as data). It does not protect the
*orchestrator* or the *gatherers*. Findings from the 2026-07-13 review of the live pipeline:

1. **Fetched page text flows through the coordinator's context.** Gatherer subagents return
   blob `content` in their replies; the coordinator collects, dedupes, and assembles
   `blobs.json` — reading attacker-controlled text in the session that holds the permissions.
2. **Gatherers read hostile pages while holding Bash.** They need a shell today to run the
   web-reach CLIs. In the scheduled session every permission prompt is off, so an
   instruction-shaped page is talking to an agent that can execute commands, unattended.
3. **The web-reach supply chain is unpinned and auto-installing.** `agent-reach` installs
   from its repo's `main` branch by construction; the gather preflight auto-installs a
   missing tool mid-run — unattended code execution from upstream HEAD.
4. **The scheduled session pushes to the public repo**, so a hijacked run can publish, not
   just corrupt locally.

## 2. Decision provenance

User picks, interactive 2026-07-13 (none are AFK-defaults):

- **D1 — Staged privileges:** keep the F83 bypass working now; close content-flow and
  supply-chain holes first; the allowlist narrowing flips only when F83's replay-based
  conformance test can enumerate the daily's real toolset (guessing bricked 07-09/07-11/07-12).
- **D2 — Files, not messages:** fetched content never rides subagent replies; receipts only.
- **D3 — Disarm the readers:** no agent that reads web content holds Bash; CLI fetches move
  behind a deterministic runner.
- **D4 — Design approved as presented** (7 sections), build authorized, SDD execution.
- **D5 — Sequencing vs the F83 conformance pin (user-decided 2026-07-13, interactive,
  against the assistant's recommendation):** the F83 pin lane (concurrent orchestrator
  session) lands FIRST. F88's build starts only after that merge, builds over the pinned
  prose, and **re-records the pin** as part of T6. Consequence accepted: the injection
  holes stay open until then; the F88 spec + plan are parked ready.

Assistant leans (marked, to challenge in review): receipt schema fields; runner/assembler as
`gpu-agent` CLI subcommands; assembler skip-and-log on malformed blob files; rounds cap = 3;
no charter amendment in v1.

## 3. Threat model (summary — full doc is deliverable T1)

**Assets:** store integrity (poisoned analysis), push rights to the public repo, the operator
machine (arbitrary execution), anything readable on it. **Entry points:** page text, search
snippets, web-reach CLI stdout, the web-reach tools' own code (install/upgrade path).
**Role table (the wall):**

| Role | Reads hostile text? | Tools held | Blast radius if steered |
|---|---|---|---|
| Coordinator (session) | **NO** (after D2) | all (scheduled: bypass, stage 0) | full — hence it never reads content |
| Reader-gatherer (subagent) | YES | Read, Write, WebSearch, WebFetch — **no Bash** | scratch files + more fetching; no execution |
| Web-reach runner | n/a (code) | argv exec of registry-pinned CLIs | bounded by validation; no shell interpolation |
| Brains (extract/judge/thesis) | YES (fenced) | none (tool-less) | unchanged (F16/Part 8) |

**Narrowing ladder:** stage 0 = today, bypass, documented as deliberate + temporary; stage 1 =
scheduled job flips to an explicit allowlist generated from F83's conformance-test evidence
(ships with F83, not F88); stage 2+ (later, with Part 26/31): push scoping, sandboxing.

## 4. Deliverables

- **T1 — `docs/threat-model-unattended.md`:** assets, entry points, role table, ladder,
  review cadence note. Committed doc; no charter edit in v1 (folds into Part 26 at Phase 7).
- **T2 — Receipts hand-off (gather-category step-3 contract):** each gatherer writes every
  blob to `work/<run-dir>/blobs/<seq>-<slug>.json` (blob object schema unchanged) and returns
  only receipts: `{url, source, date, entity, path, sha256, coversMetrics[], chase?}`.
  Coordinator handles receipts and paths, never content. Dedupe stays URL-normalized
  (metadata-only today already). Coverage matching consumes `coversMetrics` self-reports +
  existing `urlPatterns` code path.
- **T3 — Envelope assembler:** `gpu-agent gather-assemble --blob-dir <dir> --out blobs.json`
  — deterministic, schema-validating; malformed blob file → rejected, named, logged in the
  envelope's skip log, assembly continues (cap/skip doctrine). The coordinator stops
  assembling `blobs.json` by hand.
- **T4 — Web-reach runner:** `gpu-agent webreach-fetch --requests <file> --out-dir <dir>` —
  executes fetch requests `{toolId, verb/args, url}` written by reader-gatherers. Commands
  built as argv arrays from `registry/web-reach-tools.json` templates (page-supplied text
  never becomes command syntax; no shell string pass-through); http/https URLs only;
  paywalled/licensed domains refused from inventory data (**P22's first code seam**); results
  saved to files; per-request result manifest `{path, bytes, exitCode, error?}`. Flow:
  gatherer round 1 (built-in web tools + writes `fetch-requests.json`) → coordinator runs the
  runner → gatherer round 2 reads result files, writes blobs, returns receipts. Rounds ≤ 3.
- **T5 — Supply-chain pin:** registry gains `pin` per tool (tag or commit; agent-reach pinned
  to a commit, install templated on it). Unattended runs NEVER install or upgrade: missing or
  unhealthy tool → log the gap, continue on built-ins (existing degradation doctrine).
  Install/upgrade = interactive-only, pin change = a reviewed registry commit. Cycle log
  records per-run `installedVersion` (from `healthCmd` output).
- **T6 — Skill prose:** `gather-category` (dispatch toolset line — no Bash for readers;
  receipt contract; runner rounds; no-install-unattended preflight), `run-cycle` (coordinator
  handles receipts/paths only; runs the runner between gatherer rounds).
- **T7 — Compliance matrix:** upgrade `P8.injection` and `P22.allowlist` rows from
  prose-only/PARTIAL to their new code-backed status; rot-lint pins updated.

## 5. Seams & swap story (Part 18/38 — binding)

- Runner sits **behind the web-reach registry**: adding a tool or changing a CLI is a data
  entry, not runner code; removing the runner = registry `enabled: false` per tool.
- Assembler sits **behind the ingest/store seam**; blob object schema is byte-unchanged, so
  reverting to inline hand-off is a skill-prose change, not a schema migration.
- Reader toolset is **dispatch-time data** in skill prose now, pinned mechanically by F83's
  conformance test later.
- Frozen core untouched. No emitted brain-prompt bytes change → **F6 pin stays green**.

## 6. Data flow (after)

```
manifest/seeds ─► reader-gatherer (Read/Write/WebSearch/WebFetch)
                    │  writes blob files + fetch-requests.json
                    ▼
coordinator ──► gpu-agent webreach-fetch ──► result files + manifest
   │ (receipts/paths only)                      │
   ▼                                            ▼
gpu-agent gather-assemble ◄── blob files ◄── reader round 2
   │
   ▼
blobs.json ─► existing ingest → extract → gate → judge (unchanged)
```

## 7. Error handling

Runner: per-request failure recorded in the manifest, never aborts the batch; unknown toolId,
non-http(s) URL, or inventoried-paywalled domain → refused with reason. Assembler: malformed
blob file skipped + logged, never silently dropped. Missing tool unattended: gap logged,
built-ins continue. Nothing in this feature adds a new silent state.

## 8. Out of scope (v1)

Stage-1 allowlist flip (rides F83); charter Part 26 amendment (Phase 7); content-level
manipulation defenses (F85); sanitizer/lint on returned text (superseded by the wall); any
change to brain prompts, gate, scoring, or sufficiency; F90's machine runbook; F91 repo
visibility.

## 9. Acceptance

1. Suite green (expected skips only); F6 pin green; frozen-core diff empty.
2. Runner tests: argv construction from registry data, URL validation, paywall refusal,
   injection-shaped inputs (URL/verb carrying shell metacharacters, `file://`, UNC paths)
   never reach a shell; manifest correctness on partial failure.
3. Assembler tests: schema validation, deterministic output ordering, malformed-file skip log.
4. Registry schema test: every enabled tool carries `pin`; ensure-script respects it;
   preflight prose forbids unattended install.
5. `gather-category`/`run-cycle` prose states the new contract (receipts, no-Bash readers,
   rounds cap, no-install) — verified in whole-branch review; mechanical pin deferred to F83.
6. T1 doc committed; compliance rows updated.
7. Live shakedown: the next daily (attended or scheduled) completes a gather through
   runner + assembler with the cap/skip log showing any degradation loudly.
8. The F83 orchestration-conformance pin re-recorded over the changed prose (the pin exists
   by build time — sequencing D5) and green at merge.

## 10. Risks

- **Gather-quality regression** from round-tripping CLI fetches (lost mid-read chasing).
  Mitigation: rounds cap chosen to mirror today's chase depth; acceptance 7 shakedown; the
  built-in WebFetch path inside readers still allows immediate follow-up fetches.
- **Self-reported `coversMetrics`** comes from an agent that read hostile text. Accepted:
  blast radius is coverage bookkeeping; sufficiency, gate, and scoring are downstream and
  unchanged. Noted in T1.
- **Runner grows into a fetch framework.** Guard: registry-templated argv only; any new
  capability is a registry field, reviewed.
- **Pin staleness** (tools age). Accepted trade: staleness is visible (cycle-log versions) and
  an interactive upgrade away; silent drift was the hazard.
