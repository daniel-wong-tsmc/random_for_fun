---
name: desk-failure-archaeology
description: Use when a failure in the GPU Category Agent repo (random_for_fun) looks familiar or tempting to re-fight — eval seam FAIL, red prompt hash pin, anchor-vs-sufficiency gate conflict, --no-sufficiency or --no-voice-lint, a skeleton or clobbered store/cycle-log.json, finding-id collisions in route_findings, a scorecard labeled the wrong month (2026-06-v13), scraped JSONs in docs/, a backlog checkbox or diagnosis contradicting git, cross-instance commit collisions, OAuth/SDK/anthropic_api questions — or before retrying/reverting anything that may already be settled.
---

# Desk Failure Archaeology

## Overview

Every major fight in this project's history was won (or parked) exactly once, in writing. This is the chronicle: one entry per fight, SYMPTOM → ROOT CAUSE → EVIDENCE → STATUS, plus what a newcomer would naively retry and why that retry is already settled. Check here before re-diagnosing, re-designing, or "fixing" anything that looks broken.

## When to use / When NOT to use

Use when:
- A symptom matches the index table below.
- You are about to retry, revert, redesign, or "clean up" something and want to know if that battle already happened.
- A doc, checkbox, or diagnosis contradicts what git shows.

Do NOT use for:
- Classifying or gating a NEW change (frozen surface, Part-33 migrations, eval-gate governance, F-item lifecycle) → **desk-change-control** owns that doctrine.
- Triaging a NEW symptom with no history match → **desk-debugging-playbook**.
- Executing the gate-integrity fixes (F74 closed 2026-07-05; F71 → F75 → F72 still open) → **gate-integrity-campaign** is the runbook.
- Eval mechanics, fixture families, hash-pin discipline → **desk-validation-and-qa**.
- Replicate/noise math behind the eval verdicts → **desk-proof-and-analysis-toolkit**.

## Jargon (defined once)

| Term | Meaning here |
|---|---|
| F-item | Numbered entry in `docs/fix-backlog.md` (F1–F76 as of 2026-07-05). IDs are backlog inventory, NOT chronology. |
| brain | A dispatched tool-less Claude Code (Opus) subagent answering an `--emit-prompt` bundle, replayed via `--recorded`. |
| eval seam | One of extract / judge / thesis — the three LLM-touching stages the F6 eval harness grades. |
| hash pin | `tests/test_evals_baseline_pin.py` — SHA-256 of emitted prompt bytes vs `fixtures/evals/baseline.json`; red on any prompt-byte change. |
| incumbent | The committed eval baseline a candidate prompt is gated against. |
| anchor bound | Part-7 bias guardrail: code-computed per-dimension anchor forbids a rating word contradicting measured evidence direction. |
| sufficiency gate | `gpu_agent/sufficiency.py` (F63): forbids changing a binding constraint / dimension rating without enough fresh, corroborated evidence. |
| Part-33 migration | The only sanctioned way to change the frozen core; see **desk-change-control**. |
| vintage | The asOf label scoping a run's artifacts (docIds, finding ids, scorecard versions). |
| worktree lane | A fix branch in `.worktrees/<name>` with exclusive file ownership; see **desk-change-control**. |

## Two laws this chronicle proves (maintainer-confirmed 2026-07-05)

1. **Fix forward, never revert.** Zero revert/backout commits exist in the entire history (verified: `git log --all -i --grep=revert` is empty at main @ 11ffd61). A mistake gets an F-item, a fix, and a closure note — never a `git revert`.
2. **Never hand-edit brain outputs, recorded answers, or `fixtures/evals/baseline.json`.** A rejected answer is re-dispatched with the verbatim violation text appended (the F38 protocol). Every fight below that involved a bad LLM answer was resolved by re-dispatch, never by editing.

Observed discipline (strong git/doc evidence, NOT confirmed as law): merges to main are performed only after explicit user go ("merge awaits user go" in `4f6c9d1`, "user-approved" in `87f281a`); decisions taken while the user was AFK are labeled AFK-default precedent, not "user-approved" (F76b flags the ambiguity).

## Status lookup order (checkboxes lie)

The backlog's checkbox state was stale for 7 merged items at the 2026-07-05 snapshot (F56/F57/F58/F59/F61/F63/F68 merged but unticked). Resolve any F-item's real status in this order:

1. `git log --oneline --all --grep="F<nn>"` — merge/fix commits are the truth.
2. `docs/superpowers/HANDOFF.md` — TOP section only; lower sections are historical layers.
3. `docs/fix-backlog.md` entry text — rich and accurate on content, unreliable on checkbox state.

## Symptom index

| You are seeing… | Fight | Status (2026-07-05) |
|---|---|---|
| Question about SDK/API/OAuth path; `anthropic_api.py` "dead code" | 1. No-OAuth pivot | settled |
| Scraped gather JSONs sitting in `docs/` | 2. F43 gather pollution | settled |
| A stale doc tree outside the repo | 3. F47 doc-tree retirement | settled |
| A backlog diagnosis that turns out factually wrong | 4. F27 wrong-diagnosis precedent | settled (meta-lesson) |
| Scorecard filed under the wrong month (e.g. `2026-06-v13`) | 5. F46/F50 mislabel | settled |
| `route_findings` loud collision on a reused finding id | 6. F52 id collisions | settled |
| Fresh brains 100% gate-dropped; voice-lint false positives | 7. F6 day-one catches | settled |
| Judge seam FAILs eval twice with one repeated deficit | 8. F62 eval fight | settled* |
| Eval FAIL that traces to baseline noise, not your change | 9. F63 fight → eval-v2 | settled mechanism; F73 open |
| Another instance's commits/files tangled with yours | 10. F69/F70 collisions | settled per-incident; F76 open |
| Anchor bound and sufficiency gate demand opposite outcomes | 11. F71 deadlock | OPEN |
| `store/cycle-log.json` reduced to a bare skeleton | 12. F74 clobber | CLOSED — merged 257cf1b |

---

## The chronicle

### 1. The no-OAuth pivot — the session became the brain (2026-06-27)

- **SYMPTOM:** Original design (spec §10, commits `4c8e015`, `341c72d`) ran LLM calls through an OAuth-token/SDK backend.
- **ROOT CAUSE (of the pivot):** External token/SDK dependency was unnecessary — the open Claude Code session can dispatch subagents to answer canonical prompts directly.
- **EVIDENCE:** Commit `98d09e3` (2026-06-27): "Drop the claude_code OAuth/SDK backend, the [llm] extra, and the token… Add a small --emit-prompt mode… reuse the existing --recorded ingest. Live and recorded unify (fixture = cached answer)." F40 later made the dead client a fail-loud signpost (`1fefe28`; `gpu_agent/llm/claude_code.py` raises "There is no SDK/API path").
- **STATUS:** settled. This is charter Part 38 doctrine.
- **DO NOT RETRY:** Do not "fix" `ClaudeCodeClient` so it stops raising, and do not wire `gpu_agent/llm/anthropic_api.py` into a live path. The SDK file exists in code as a dormant, doctrine-forbidden alternate seam (used only by env-gated live smoke tests). "No API/SDK path" is true of the LIVE path, not of the codebase — a grep hit on `anthropic` is not a contradiction to report.

### 2. F43 — gather pollution: 20 scraped JSONs in docs/ (fixed 2026-07-02)

- **SYMPTOM:** 20 scraped gather-output JSONs sitting beside the charter in `docs/`.
- **ROOT CAUSE:** The gather skill's own example command said `--out docs` — operators copy-pasted it faithfully.
- **EVIDENCE:** `docs/fix-backlog.md:166-169`; fix commit `839113b` (skill writes to `work/`; artifacts archived under `work/gather-2026-07-02/`).
- **STATUS:** settled (Wave 0).
- **DO NOT RETRY:** Don't delete stray artifacts you find without checking whether they were deliberately archived. And the transferable lesson: skill example commands are executed verbatim by model operators — an example IS an instruction. Audit examples when writing skills.

### 3. F47 — stale external doc tree retired (fixed 2026-07-02)

- **SYMPTOM:** A parallel doc tree at `Documents\TSMC\ai4bi\ai_state_of_the_market` (outside the repo) drifting from repo truth; `action-items.md` living outside git.
- **ROOT CAUSE:** Pre-repo working files never migrated.
- **EVIDENCE:** `docs/fix-backlog.md:181-183`; fix commit `c83ae83` — action-items.md pulled in-repo; the external tree got a `RETIRED.md` pointer, **nothing deleted**.
- **STATUS:** settled.
- **DO NOT RETRY:** Do not resurrect or sync the external tree; it is a tombstone. If you find it on this machine, its `RETIRED.md` points here. Retirement-by-pointer (not deletion) is the house pattern for stale artifacts.

### 4. F27 — the wrong-diagnosis precedent: the backlog itself can lie (2026-07-02)

- **SYMPTOM:** Backlog entry F27 claimed `models.frontier-closed` was unrunnable because "empty weights (zero indices)".
- **ROOT CAUSE:** The diagnosis was factually wrong when executed: a registry-weight fallback meant indices were never zero. The real deliverables became explicit weights + coverage manifest + persona + runnability pins (`b743ee9`).
- **EVIDENCE:** Wave-2 note, `docs/fix-backlog.md:17-19` (verbatim: "the old empty-weights-zero-indices claim was stale"); F27 entry line 127 still carries the wrong wording.
- **STATUS:** settled — with the meta-lesson standing: an F-item's stated diagnosis is a claim made at filing time, not verified truth. Re-verify the failure before building the fix.
- **DO NOT RETRY:** Don't re-diagnose frontier-closed as broken from the F27 entry text. Its honest current status (verify before repeating): **runnable-per-pins, never yet run live** — no `store/models.frontier-closed/` exists, and `.gitignore`'s store whitelist (lines 7–15) has NO carve-out for it, so a first live run would write scorecards into an ignored directory unless `.gitignore` is amended first (route that through **desk-change-control**).

### 5. F46 → F50 — the first real cycle mislabels its scorecard `2026-06-v13` (2026-07-02)

- **SYMPTOM:** The first genuine live daily cycle (validation gate F46, run 2026-07-02) wrote its scorecard as `store/chips.merchant-gpu/2026-06-v13.json` — a July run filed under June, as version 13 of a month with 12 versions.
- **ROOT CAUSE:** `Scorecard.asOf` came from `assignment.asOf` — a committed fixture pinning `2026-06` — not from the run's `--as-of`.
- **EVIDENCE:** `docs/fix-backlog.md:175-191`. The v13 file was removed and the cycle re-run with a run-scoped assignment copy; F50 (run asOf overrides assignment asOf, `6756a99`) shipped in Wave 2. The same F46 gate also surfaced F51 (per-series price dedup, `79aa548`), which itself needed a same-day fix-the-fix (`7cee339` — the first fix didn't hold cross-cycle).
- **STATUS:** settled. NOTE: removing the just-written v13 file is the closest thing to a revert in the whole history — it was an unpublished store artifact minutes old, not committed history. It does not license reverting anything committed.
- **DO NOT RETRY:** If a scorecard lands under the wrong asOf today, that is a NEW bug (F50 regressed), not this old one — F50 is test-pinned. Don't "fix" it by editing the store file; store artifacts are immutable once written.

### 6. F52 — finding-id collisions across cycles (2026-07-03)

- **SYMPTOM:** Append-only FindingStore fails loud in `route_findings`: a re-gathered URL produced finding ids identical to a prior cycle's (observed: `www-digitimes-com-f88ca4e6-1`, `lambda-ai-845323fc-1`).
- **ROOT CAUSE:** Finding ids were `docId-<n>` and docIds derived from the URL only — a URL re-gathered on a later day with different excerpt content reused prior-cycle ids. L1 dedup (url+hash) can't catch it because gatherer excerpts vary run-to-run.
- **EVIDENCE:** `docs/fix-backlog.md:200-212`. Interim workaround: a LOGGED wiki-ingest exclusion (`work/daily-2026-07-03/ingest-exclusions.json`) — scorecard path unaffected. Fix same day: vintage-scoped docIds `{slug}-{digest}-{asOf}` at the gather seam; `ingest --as-of` now required; L1 unchanged so unchanged content still skips cross-day.
- **STATUS:** settled.
- **DO NOT RETRY:** A collision today means something is stripping the vintage from docIds — check the gather seam, don't weaken the FindingStore collision check (failing loud there is the designed behavior, F11 family). And never resolve a collision by editing/deleting the stored finding.

### 7. First F6 eval run catches 3 shipped defects on day one (2026-07-04)

- **SYMPTOM:** The initial eval baseline run (F6 Task 10) found: (a) eval-context brains produced findings that were 100% gate-dropped; (b) the F67 voice lint rejected legitimate text ("U.S. GDP" split a 2-sentence rationale into 3, tripping the max-2 cap; GB300/GAAP/GDP flagged as un-allowlisted acronyms).
- **ROOT CAUSE:** (a) The emitted extraction system prompt did not carry the demand/supply indicator vocabulary the gates enforce — F55 had claimed to fix this but only partially; prompts and gates were being generated from different sources. (b) The sentence splitter was abbreviation-blind; the acronym allowlist had gaps.
- **EVIDENCE:** `docs/superpowers/HANDOFF.md:151-154`; fixes `6d9fa67` (bake vocabulary into emitted prompt, "completes F55"), `f1dc904` (extend to structural/unsided ids), `ac1e209` (abbreviation-aware splitter + allowlist GB300/GAAP/GDP). Baseline armed at `0344949`.
- **STATUS:** settled. Standing lesson: **prompts and gates must be generated from the same registry** — this is why "safe data-only" registry edits can trip the hash pin.
- **DO NOT RETRY:** Don't hand brains id vocabularies out-of-band (the pre-F55 habit — it caused one full re-dispatch wave per cycle on BOTH early live cycles). Voice-lint false positives are fixed by allowlist/splitter changes (data + code), never by bypassing the lint or editing the answer. New acronym echo → add to `registry/acronyms.json` (precedents: CEO, MI, CFO/CUDA/ZLUDA/SDNY handled by re-dispatch on 2026-07-05's daily).

### 8. The F62 eval fight — judge seam FAIL ×2, rubric-vs-prompt mismatch (2026-07-04)

- **SYMPTOM:** F62's `observed=` vintage tag drifted judge+thesis prompt hashes → pin red → full eval required. Attempt 1 FAIL (extract 6.25 < 6.62 incumbent, judge 6.50 < 6.75). Attempt 2 FAIL on judge only (6.25).
- **ROOT CAUSE:** A rubric-vs-prompt mismatch, isolated by a consistent deficit signature: ALL 8 fresh judge generations across both attempts scored sensitivity-differentiation = 1 because the rubric rewards a consensus-departure sentence the post-F67 3-sentence narrative budget never asked for. (Separately: extract, on an UNCHANGED prompt, swung 6.62→6.25→6.75 — calibrating a ~±0.4 generation noise floor, the seed of eval-v2.)
- **EVIDENCE:** `docs/superpowers/2026-07-04-f62-eval-run-notes.md` (all three attempts); FAIL record committed as docs commit `b9301e8` with the pre-committed STOP disposition ("no retry-until-green"); user chose option B — fix the prompt, keep the rubric — commit `b8f41f8` (judge crux sentence demands "where and why this read departs from the consensus view", now pinned by `tests/test_judgment_prompt.py`); attempt 3 PASS (extract 6.75 / judge 7.50 / thesis 6.00; the criterion moved 1→2 on all four judge cases — exactly the diagnosed signature); rebaselined on merit WITHOUT --force (`f605a77`); merged `eb925bc`.
- **STATUS:** settled* — the asterisk: attempt 3's PASS was itself later acknowledged a **high draw** (`345fc31`: "F62 attempt-3 was a high draw"; eval-v2 migration notes: "a3 remains a high draw for extract… reflected honestly, not corrected for"). That acknowledgment triggered fight 9.
- **DO NOT RETRY:** (a) Never retry-until-green — the disposition is pre-committed before grading and a FAIL is a STOP + docs(eval) run-notes commit + user decision (governance in **desk-change-control**). (b) Don't re-litigate the prompt-vs-rubric choice: "fix the prompt, keep the rubric" was the user's call. (c) The transferable diagnostic move: look for a CONSISTENT deficit signature across generations before blaming noise — two shortfalls with one signature is a mismatch, not luck.

### 9. The F63 eval fight → eval-v2 built in one day (2026-07-04 → 05)

- **SYMPTOM:** F63 (corroboration doctrine — all three seam prompts amended) FAILED two full eval runs against the F62 incumbents: attempt 1 extract 6.38 / judge 7.00 / thesis 6.00-tie; full replication 6.38 / 6.75 / 5.50.
- **ROOT CAUSE:** The bar, not the candidate. The v1 baseline was a single lucky run (F62's high-draw attempt 3); identical-prompt runs swing 6.25–7.50, exceeding the pass margin. No graded deduction traced to the F63 changes, and F63's mechanisms graded WELL (the F2e gate caught within-document corroboration in both runs — the gate doing its job on a real brain failure mode).
- **EVIDENCE:** FAIL record `345fc31` + `docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`; BLOCKED-on-user `6b75d33`; resolution = rebuild the bar, not force past it: eval-v2 replicate baseline designed (`a0dfe41`) and built as its own branch, merged `c0d5dd2`, all on 2026-07-05 (baseline = mean of 3 unfiltered replicates − ε, per-case crater prong, marginal band, verdict.json governance — mechanics owned by **desk-validation-and-qa**); F63 folded in eval-run fixes (`5923619`: "across separately fetched documents" corroboration scope, impact.direction enum stated, CEO allowlisted), re-gated PASS r1 extract 6.625 vs bar 6.5833 — **margin 0.042** (`ef52790`), merged `017b592`.
- **STATUS:** settled mechanism / OPEN question. The 0.042 margin is "deep inside noise" (F73's words, `docs/fix-backlog.md:592-605`), and **the eval-v2 gate has never demonstrably caught a real regression** — that is F73, an open problem, not a solved gate. Related doc-reconciliation note: charter Part 37's closing "Not yet" line contradicted the F63 amendment ~60 lines above for weeks; reconciled 2026-07-06 to say the *staged* corroboration step shipped (F63/F2e) and only the *full* Part 26 requirement is still deferred. Quote the current "Still deferred (by decision)" wording.
- **DO NOT RETRY:** (a) Don't treat a marginal eval verdict (either direction) as meaningful signal until F73 lands — a 0.04 pass decides alone today. (b) Don't propose "just --force past a noisy FAIL": the one time the bar was wrong, the project rebuilt the bar in a day instead. (c) Don't re-derive the replicate math from scratch — **desk-proof-and-analysis-toolkit** has the worked example. (d) The v1 single-run baseline lived <24h; any doc calling a single run "the incumbent" predates `c0d5dd2` and is stale.

### 10. F69/F70 — concurrent-instance collisions (2026-07-04)

- **SYMPTOM:** Two wounds in one day of parallel work: (a) an instance made a stray commit onto the concurrent instance's F69 branch; (b) `git add -A` swept an untracked copy of the other instance's `roadmap.md` into an F70-era charter commit (`c4913a6` context).
- **ROOT CAUSE:** No coordination substrate — nothing prevented an instance from touching a branch or file another instance owned; `git add -A` is indiscriminate in a shared tree.
- **EVIDENCE:** `docs/superpowers/HANDOFF.md:105-125` (both incidents and their un-bundling before merge). Codified rules: never touch another instance's branch/worktree; `git log --oneline -1` immediately before every commit; sentinel files + HANDOFF board (see **desk-run-and-operate** for the operating conventions).
- **STATUS:** settled per-incident; the umbrella (F76: handoff atomicity, provenance labels, retained-worktree registry) is OPEN. Related standing confusion F76 exists to fix: merged branches keep their worktrees (`.worktrees/f62-flagship-store` has a DELETED remote yet is fully merged — tip `4f6c9d1` is parent 2 of `eb925bc`) because gitignored `work/` inside them holds the raw eval replicate data behind the committed baseline. **Never `git clean`, never delete a retained worktree.**
- **DO NOT RETRY:** Don't "clean up" worktrees or branches that look stale — check `git branch --merged main` and merge parents first. Don't use `git add -A` in this repo. Don't assume a deleted remote means stranded work.

### 11. F71 — the gate deadlock on the sufficiency gate's FIRST live contest (2026-07-05) — OPEN

- **SYMPTOM:** First live flagship on the post-F62/F63 stack (monthly v3): judge rated moat Weak; the +0.50 measured anchor made Weak illegal (Part-7 bias guardrail), forcing Weak→Mixed; the F63 sufficiency gate then correctly objected — the forced move rested on 2 secondary publishers (<3, no primary). Two frozen-adjacent code guards demanded contradictory outcomes with no defined precedence.
- **ROOT CAUSE:** Missing precedence rule between the anchor bound (code-computed measured evidence forces a rating) and the sufficiency gate (forbids the change without corroboration). Nobody had specified which wins.
- **EVIDENCE:** After one rewrite attempt, the run completed under whole-run `--no-sufficiency` — **the exact configuration the F63 spec forbade (loosening live, counterweight off), on the gate's first contest** (`docs/fix-backlog.md:620-632`, F75's wording). The bypass was logged in `store/cycle-log.json` `gates.sufficiency` — a record that today survives ONLY at commit `99ca522` (see fight 12). Backlog entry: `docs/fix-backlog.md:463-484` (`d0b39ea`). The shipped moat record was judged defensible (capped medium, honest rationale). Addendum, verified 2026-07-05 evening: daily cycle #1 (`d9cfb3f`) passed the sufficiency gate with NO bypass on a 3-publisher + primary-SEC-filing constraint shift — the deadlock did not recur; it is a corner case, not a constant.
- **STATUS:** OPEN. Lean fix recorded (anchor-forced move = measured evidence, exempt from sufficiency, stamped "anchor-bounded on thin evidence"; bypass per-dimension + reason or removed); rejected-lean alternative recorded (sufficiency wins → publishes a rating the anchor declares illegal). Declared blocker for any unattended loop. Fix ships as a Part-33 migration → **desk-change-control**; execution sequence → **gate-integrity-campaign**.
- **DO NOT RETRY:** (a) Don't re-derive the precedence argument from scratch — both options and the lean are already written in the F71 entry; the remaining call is the user's. (b) Don't treat run-cycle SKILL.md's "neither check ever blocks a scorecard" bypass instruction (line ~155 on main) as durable doctrine — it is F75's named removal target. (c) If you hit the deadlock live: one rewrite re-dispatch attempt, then bypass + LOG it in the cycle journal + surface it — that is the (unsatisfying, recorded) interim protocol, not a precedent that bypassing is fine.

### 12. F74 — the cycle-log clobber that erased the F71 bypass record (2026-07-05)

- **SYMPTOM:** Sometime after `99ca522`, working-tree `store/cycle-log.json` was found rewritten to a bare machine skeleton (bare `status: ready`; no asOf/gather/gates/thesis/report), deleting the finalized 2026-07-v3 run journal INCLUDING the F71 `gates.sufficiency: "bypassed…"` record — the doctrine's own audit trail, erased by the project's own automation. One routine `git add store/` away from permanent loss.
- **ROOT CAUSE (now identified):** `cli._cycle_plan`'s unconditional `write_text` (`gpu_agent/cli.py:811-812` on main), pointed at the canonical `store/cycle-log.json` by run-cycle SKILL step 1 (`--out store/cycle-log.json`, SKILL.md line ~49) — so EVERY run start began by erasing the previous run's session-authored journal in the working tree. Named in the fix commit per F74's acceptance criteria.
- **EVIDENCE:** Backlog `docs/fix-backlog.md:606-619` (URGENT). The v3 journal + bypass record survive at `git show 99ca522:store/cycle-log.json` (verified 2026-07-05). Fix BUILT on worktree branch `f74-cycle-log` @ `3613ede` ("cycle-plan must never destroy the finalized cycle journal": cycle-plan --out refuses to overwrite anything richer than a bare plan, fails loud naming F74; run-cycle step 1 redirected to `work/<run-dir>/cycle-plan.json`; tripwire test `tests/test_store_cycle_log_integrity.py`; suite 1063/4 on the branch).
- **STATUS: CLOSED — merged `257cf1b` on 2026-07-05** (backlog ticked same day at `1a9eb33`; `docs/fix-backlog.md:606-607`). One-line history: root-caused and fix-built on worktree branch `f74-cycle-log` (this entry originally described that branch as unmerged, verified 2026-07-05 @ `11ffd61` — a snapshot taken hours before the merge landed); the branch was then hardened by an 8-angle adversarial review (`9a5f9b2`) and merged same day. **The `f74-cycle-log` branch/worktree no longer exist at all** — deleted after merge, not merely retained (`git branch -a` / `git worktree list` show no trace) — don't go looking for them. `gpu_agent/cli.py`'s `_cycle_plan` (`_is_bare_plan`, currently ~lines 813-848) now refuses to overwrite anything richer than a bare plan skeleton, naming F74 in its own error message. `store/cycle-log.json` holds the latest committed daily journal; the monthly v3 journal (with the F71 bypass record) lives only in history at `99ca522` (acceptable: cycle-log is a single-run slot, not an archive; git history is the archive). Standing monitor: **desk-diagnostics-and-tooling**'s `f74_guard.py` / `status_reconcile.py` scripts confirm RESOLVED live — re-run them rather than trusting this date-stamp.
- **DO NOT RETRY:** (a) Don't assume the guard means `git add store/` is safe to blanket-run — the guard is pytest/write-time only (see its own documented residual: a store commit made without a suite run, or a stale staged blob, still slips through); diffing `store/cycle-log.json` before adding is still good hygiene, just no longer THE trap. (b) Don't hand-reconstruct a lost journal from memory; restore from git history. (c) Don't merge branches yourself in general — observed practice is user-merge-only (this specific branch is already merged and gone). (d) Execution order for the remaining open cluster (F71 → F75 → F72) is owned by **gate-integrity-campaign**.

---

## Adjacent open wounds (not yet fights — don't be the one who makes them one)

Dated 2026-07-05; re-verify each before acting.

- **F72** (`docs/fix-backlog.md:567-591`): `publisher_key` is netloc-only, so one wire press release on 3 syndicator domains (the live store already holds `stocktitan.net`, `markets.financialcontent.com`, `finance.yahoo.com`) silently satisfies `minDistinctPublishers: 3` — unlocking F2e high confidence, thesis rule-6 reversals, and wiki promotion at once. Note the recorded asymmetry with F71: the gate blocked HONEST thin evidence and was bypassed, while DISGUISED thin evidence would pass unremarked.
- **F73** (`592-605`): the eval gate every prompt change must pass is possibly underpowered (fight 9's status).
- **F75** (`620-632`): whole-run bypass flags still on live paths and still taught by run-cycle SKILL.md.
- **F76** (`633-645`): coordination substrate (fight 10's umbrella).

## Common mistakes

| Mistake | Why it's wrong | Instead |
|---|---|---|
| Trusting a backlog checkbox or diagnosis | 7 checkboxes were stale at snapshot; F27's diagnosis was factually wrong | Status lookup order above; re-verify the failure itself |
| `git revert` / proposing a rollback | Zero reverts in 475+ commits; fix-forward is law | F-item + fix + closure via **desk-change-control** |
| Hand-editing a rejected brain answer, recorded fixture, or baseline.json | Maintainer-confirmed law; 5+ documented precedents of doing it right under pressure | Re-dispatch with verbatim violations (F38); rebaseline via governance |
| Retrying an eval until green | Explicitly forbidden (`b9301e8`); dispositions are pre-committed | STOP, docs(eval) run-notes commit, user decides |
| Reading a marginal eval PASS/FAIL as signal | F73: margins (0.042) sit deep inside documented 6.25–7.50 same-prompt swings | Treat as noise event; note it; don't redesign prompts off it |
| `git add store/` or `git add -A` without a diff | The F74 trap (closed 2026-07-05, but its write-time-only guard doesn't cover a stale staged blob) and the F70 sweep both came from exactly this | Diff `store/cycle-log.json`; add paths explicitly |
| Deleting "stale" worktrees/branches; `git clean` | Retained worktrees hold the gitignored raw eval evidence behind the committed baseline | Check `git branch --merged main` + merge parents; never clean |
| Grepping `anthropic` and reporting a live SDK path | The file is a dormant, doctrine-forbidden seam | Fight 1 |
| Reading F-numbers as chronology | F6 executed after F55; F62/F63 after F67–F70 | Date-stamps and git log are the timeline |
| Quoting charter Part 37's old flat "Not yet: hard corroboration" line | That contradiction was reconciled 2026-07-06: the deferred list now says the *staged* 3-publisher step shipped (F63/F2e) and only *full* Part 26 hard corroboration remains deferred | Quote the current "Still deferred (by decision)" wording, not the pre-fix line |

## Provenance and maintenance

Authored 2026-07-05 against **main @ 11ffd61** (the skill-library discovery snapshot was main @ `a8ec757` earlier the same day; five commits landed in between — notably the F74 lane claim `d84f3b9`, the committed daily cycle `d9cfb3f`, and the session-hygiene config `29584d9` which tracked the formerly-untracked CLAUDE.md/session-orient). All commit hashes, backlog line numbers, run-note quotes, and file/line references above were re-verified against the working repo on 2026-07-05. **Fight 12 (F74) re-verified and corrected 2026-07-06**, after F74 merged (`257cf1b`) and its worktree/branch were deleted — the entry originally described the fix as unmerged, which was accurate at authoring time but stale within the same day.

Volatile facts and their one-line re-verification commands (run from repo root):

| Volatile fact | Re-verify with |
|---|---|
| HEAD / how far this chronicle has drifted | `git log --oneline -10` |
| F74 fix merged yet? | CLOSED 2026-07-05 (`257cf1b`); the `f74-cycle-log` branch/worktree are deleted, so `git log --oneline main..f74-cycle-log` now errors "unknown revision" rather than returning empty — that error itself confirms closure. Re-verify with `git log --oneline --grep=F74` |
| Guard still on main? | `grep -n "_is_bare_plan\|_cycle_plan" gpu_agent/cli.py` (line numbers drift; re-anchor by name, not by number) and `grep -n "cycle-plan" .claude/skills/run-cycle/SKILL.md` |
| v3 journal + bypass record still recoverable | `git show 99ca522:store/cycle-log.json \| grep -o "bypassed[^\"]*"` |
| Any F-item's real status | `git log --oneline --all --grep="F<nn>"` then HANDOFF top section |
| F71/F72/F73/F75/F76 still open | `sed -n '463,484p;556,645p' docs/fix-backlog.md` (line numbers drift — re-anchor with `grep -n "F71 —" docs/fix-backlog.md`) |
| Still zero reverts | `git log --all -i --grep=revert --oneline` |
| Eval baseline bars / margin claims | `python -c "import json;b=json.load(open('fixtures/evals/baseline.json'));print(b['seamMeans'],b.get('epsilon'))"` |
| Bypass flags still taught by run-cycle | `grep -n "no-sufficiency\|neither check" .claude/skills/run-cycle/SKILL.md` |
| frontier-closed still never run / not whitelisted | `ls store/ \| grep frontier` (expect nothing) and `sed -n '7,15p' .gitignore` |
| Charter Part 37 corroboration reconciled (2026-07-06) | `grep -n "Still deferred (by decision)" docs/agent-swarm-charter.md` (expect the staged-shipped/full-deferred pair) |
| Retained worktrees | `git worktree list` |

Bash-syntax note: the commands above use POSIX tools (`sed`, `grep`, `|`); on this Windows 11 machine run them in Git Bash, or via the Claude Code Bash tool — not PowerShell 5.1 (whose `sed`/`grep` don't exist and whose pipes pass objects).

When a fight in this file changes status (F74 merges, F71 lands its migration, F73 gets a canary), update the entry's STATUS line and the symptom index in the same commit as the change's documentation — a chronicle with stale statuses is this repo's F27 mistake repeated in its own archaeology.
