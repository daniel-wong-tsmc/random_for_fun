# Threat model: the unattended scheduled session

**Status:** live doc, first version 2026-07-13 (F88, deliverable T1).
**Covers:** the daily scheduled cycle that has run headless since 2026-07-13 (F83).

## 1. Purpose & scope

This document is the threat model for the **unattended, headless, full-permission scheduled
session**: since 2026-07-13 (F83) the Task Scheduler job launches Claude with
`--dangerously-skip-permissions` and reads open-web content every day with nobody watching. It
complements — it does not replace — the F16/charter-Part-8 injection boundary, which protects
the tool-less **brains** (extract, gate, judge, thesis) by fencing fetched text as data those
prompts must never obey. This document is about the two roles that boundary does not cover: the
**orchestrator** (the session itself, holding every permission) and the **gatherers** (the
subagents that actually touch hostile pages). Full adversarial-boundary work — charter Parts 26
(manipulation resistance) and 31 (security/data protection) — stays deferred to Phase 7. What
follows is the thin now-slice that closes the worst holes without waiting for that larger build.

## 2. Assets

What an attacker who successfully steered the scheduled session could reach:

- **Store integrity.** Poisoned analysis — a fabricated or manipulated finding — feeding into
  the store and, downstream, the daily brief.
- **Push rights to the public repo.** The scheduled session commits and pushes; a hijacked run
  could publish attacker-chosen content, not just corrupt a local file.
- **The operator machine.** The session holds arbitrary command execution (the bypass grants
  every tool, including Bash) and can read anything on the machine it runs on.

## 3. Entry points

Where attacker-controlled text can enter the session:

- **Fetched page text** — the body of any page a gatherer retrieves.
- **Search-result snippets** — titles/summaries returned by search tools, before a page is even
  opened.
- **Web-reach CLI stdout** — output from third-party fetch tools (e.g. `agent-reach`,
  `crawl4ai`) invoked to retrieve a page.
- **The web-reach tools' own code** — their install/upgrade path. A tool installed or upgraded
  mid-run pulls and executes code from upstream at that moment.

## 4. The wall (what F88 built)

F88's core move is a role split: only one role is allowed to hold both "reads hostile text" and
"can execute commands," and that role is native code with a narrow, validated surface — no agent
gets both.

| Role | Reads hostile text? | Tools held | Blast radius if steered |
|---|---|---|---|
| Coordinator (session) | **NO** (after F88) | all (scheduled: bypass, stage 0) | full — hence it never reads content |
| Reader-gatherer (subagent) | YES | Read, Write, WebSearch, WebFetch — **no Bash** | scratch files + more fetching; no execution |
| Web-reach runner | n/a (code) | argv exec of registry-pinned CLIs | bounded by validation; no shell interpolation |
| Brains (extract/judge/thesis) | YES (fenced) | none (tool-less) | unchanged (F16/Part 8) |

What each row means in practice:

- **Coordinator never reads fetched content.** Before F88, gatherer subagents returned page
  content in their replies, and the coordinator — the one process holding every permission —
  read and assembled it. After F88, gatherers write every blob to a file and return only a
  **receipt** (url, source, date, entity, file path, self-reported `sha256` and
  `coversMetrics`). The coordinator handles receipts and paths only; it never opens a blob file
  or hand-assembles the envelope. Content travels from gatherer to assembler to `ingest` as
  files, never through the coordinator's own context.
- **Reader-gatherers hold no Bash.** They still need to run web-reach CLIs, but they no longer
  hold a shell to do it — CLI fetches move behind a deterministic runner (below). A gatherer
  that reads a hostile, instruction-shaped page can, at worst, write more scratch files or
  request more fetches; it cannot execute a command.
- **The web-reach runner executes, but only registry-templated argv.** It reads fetch requests
  (`{toolId, verb/args, url}`) written by gatherers, looks up the matching tool in
  `registry/web-reach-tools.json`, and builds the command as an **argv array** from that
  registry's template — the page-supplied target is substituted into a `{target}` slot, never
  concatenated into a shell string. It runs with `shell=False`, so page text can never become
  command syntax. Results are written to files under a sanitized in-`out_dir` path — filenames
  are derived from a sanitized slug, never from the raw attacker-controlled target, so a hostile
  target cannot escape the output directory via path separators or `..`.
- **Brains stay tool-less, unchanged.** Extract, gate, judge, and thesis prompts still fence
  fetched content as data (F16/Part 8) and hold no tools at all — F88 does not touch this layer.

**Supply chain.** Registry tools carry a pinned version (`pin`, a tag/commit recorded per tool).
Unattended runs **never install or upgrade** a web-reach tool: if a tool is missing or unhealthy,
the gap is logged and the run continues on built-in fetch paths (existing degradation doctrine)
rather than pulling new code. Install or upgrade is interactive-only, and a pin change is itself
a reviewed registry commit. The installed version is recorded per run (from each tool's health
check output) so drift is visible even though it isn't blocking.

## 5. Licensed sources (D6): fetch-and-flag, not hard-block

Inventoried subscription-only domains (TrendForce, SemiAnalysis, Dell'Oro, Omdia, IDC) are
**fetched like any other page** — they are not refused. Every fetch of one is **flagged**: the
web-reach runner's result manifest carries `licensedSource: <domain|null>`, and the
`gather-category` skill prose copies that flag into the cycle log wherever it appears (manifest
row or a gatherer's receipt) so the licensing risk is never silent. The operator is expected to
watch this flag rather than have the tool decide the question for them.

What's still deferred: a **per-finding trust-footer tag** — surfacing "this figure traces back to
a licensed source" on the specific finding it feeds, not just in the cycle log. That needs a new
field on the `RawDocument` schema (a frozen-core migration), which is out of F88's scope and is
logged as a follow-up. Non-http(s) schemes and unknown tool/verb requests are still refused
exactly as before — D6 only removed the *domain*-based refusal, nothing else.

## 6. The narrowing ladder

The scheduled session's permissions are meant to narrow over time, in stages:

- **Stage 0 — today.** Full `--dangerously-skip-permissions` bypass. This is documented here as
  **deliberate and temporary**, not an oversight: F88 closes the content-flow and supply-chain
  holes first, before touching the permission grant itself.
- **Stage 1 — explicit allowlist.** The scheduled job flips from the full bypass to an explicit
  approved-tool allowlist. That allowlist is **generated from F83's conformance-test evidence**
  (a replay-based test that enumerates the daily's real toolset), not guessed by hand — guessing
  the toolset by hand is what bricked the 2026-07-09, 07-11, and 07-12 scheduled runs. This stage
  ships with F83's follow-on work, **not** with F88.
- **Stage 2+ — push scoping and sandboxing.** Restricting the session's git push rights and
  running it inside a sandbox. This rides charter Parts 26/31 and lands in Phase 7, alongside the
  full adversarial-boundary build.

## 7. Accepted residuals

F88 closes the content-flow and supply-chain holes described above, but the following gaps are
**known and intentionally left open** — they are not closed by this work:

- **The web-reach runner's in-memory capture is bounded only by time, not by size.** A
  subprocess's stdout is fully captured in memory before anything is written to disk; that
  capture is bounded by the request `timeout`, not by a byte limit. Full incremental streaming
  with a hard memory cap is deferred. The **on-disk** result, by contrast, **is** capped
  (`MAX_RESULT_BYTES`): anything over the cap is truncated before it's written to the result
  file, and the manifest records the truncation.
- **The runner's per-request catch-all covers the subprocess call, not the disk write after
  it.** Any exception raised while running the fetch (including a timeout) is caught and recorded
  in that request's manifest row without aborting the rest of the batch. The write of the result
  file to disk that follows a successful fetch is not inside that same guard: an `OSError` at
  that point (for example, a full disk) could still abort the batch. This is a narrow,
  disk-full-territory gap, not a hostile-content vector.
- **`coversMetrics` and the receipt `sha256` are self-reported by a gatherer agent that just read
  hostile text**, and the `sha256` is not independently computed or verified by any code today.
  Their blast radius is limited to coverage bookkeeping and dedupe: sufficiency, the gate, and
  scoring all sit downstream and are unchanged by F88, so a lie in either field cannot move a
  rating — at worst it mis-tracks what's already been covered.
- **Query-kind fetch verbs are not URL-scheme-validated; only url-kind verbs are.** A verb like
  agent-reach's `search` takes a free-text query rather than a URL, and its target is passed
  through without a scheme check (unlike url-kind verbs, which must be `http`/`https` with a
  parseable host). Under D6 (licensed sources are fetched and flagged rather than blocked
  anyway), this is not a paywall-bypass channel, but it is worth naming: a query-kind target
  reaches its tool with no scheme validation at all.
- **Interactive installs of `agent-reach` still pull from its `main` branch, not a pinned
  ref.** The registry records a version (`1.5.0`) for drift detection, but the install command
  itself installs from upstream `main` — an exact-ref (tag/commit) pin is a follow-up.
  **Unattended** runs never install or upgrade at all (see §4); this residual applies only to a
  human running an interactive install.

## 8. What this document does not cover

- **Content-level manipulation** — fake news, coordinated disinformation, source-reputation
  defenses: tracked as **F85** (manipulation-resistance early slice).
- **Operator-machine rebuild and continuity** — what happens if the laptop running the scheduled
  job is lost or replaced: tracked as **F90**.
- **Public-repo visibility and quoted-content posture** — whether the repo (and the findings it
  publishes, quoting fetched articles) should be public, and what posture governs republishing
  quoted text: tracked as **F91**.
- **The full adversarial boundary** — charter Parts 26 (manipulation resistance) and 31
  (security/data protection) in their complete form: deferred to Phase 7.

## 9. Review cadence

Re-read and re-evaluate this document at every phase gate, and at any change to the scheduled
session's permissions (including the stage 1 allowlist flip described in §6).
