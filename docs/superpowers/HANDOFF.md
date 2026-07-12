# HANDOFF — GPU Category Agent (resume point: F78 STAGES 1–5 ALL MERGED 2026-07-12, `main == origin/main == fd0b08c`, suite **1200/5**, eval pin green. Next task: **F78 stage 6** — the change-first renderer + the 2026-07-11 exec top band amendment — its plan is fully written and its dependencies are now all on main. Then F79 (SDEWS index rebuild) after F78 closes.)

- **Date: 2026-07-12 (LATEST) — the F78 pipeline landed.** All merges user-directed interactively
  (ZERO AFK-defaults this session or the 2026-07-11 session). Authoritative state:
  - **Stage 4** (7-day gather sweep + logged `pursuedDespiteAge[]`, reworks F58) merged `b9a3251`.
  - **Stage 5** (price-feed reader, 4 provider adapters → $/GPU-hr display-only) merged `fdbc7fb`
    (its flagged Oracle GB200/GB300 `_match_model` deviation accepted with the merge).
  - **Stage 3** (corpus ages via the wiki — flat 45-day window GONE; aged salience over real
    `observedAt` age + lifecycle gate + **any-page-keeps** dedup, user-adjudicated) merged
    `6e24259`. Built this session subagent-driven (6 tasks, per-task reviews, final opus review:
    Ready to merge). Sentinel `.superpowers/handoffs/f78-stage3-DONE.md`.
  - **Stage 2** (calendar-day thesis pacing, 21-day dials, `lastPaceAsOf`) merged `fd0b08c`.
    ADOPTED from a dormant 07-09 instance (user-directed), reconciled with main by re-running the
    deterministic book rebuild over v5's history (streaks re-paced: nvda 8→2 — designed effect),
    given its FIRST whole-branch review (opus: Ready to merge). Sentinel
    `.superpowers/handoffs/f78-stage2-DONE.md` — **read its venv/editable-install import gotcha.**
  - **2026-07-11 session:** exec-format spec committed (`3959643`,
    `docs/superpowers/specs/2026-07-11-executive-brief-format-design.md` — top band tiles + alert
    ladder, decisions E1–E7) + stage-6 plan amended in place (`bfbaa51`, Tasks 5b/5c/8-amend/11);
    SDEWS docx committed (`c29fc82`) + metric extraction doc; **F79** (full SDEWS-style scoring
    v2.0 migration — USER CHOSE against assistant recommendation, starts only after F78 closes)
    and **F80** (live-store `category: null` on entity:nvidia/entity:multi wiki pages → NVIDIA
    contributes ZERO store findings to its own corpus, pre-existing since F62) logged in
    `docs/fix-backlog.md`. A concurrent instance landed the live 2026-07 **v5** top-up (`60879fb`).
- **OPEN GATES (user decisions still pending):** (1) blocked scheduled dailies — RESOLVED
  2026-07-12 (user-approved, interactive): grant the scheduled session ALL tools, recorded as
  **F83**, and the config flip is DONE the same day — the machine-local Task Scheduler job
  script (`~/.claude/jobs/gpu-daily-cycle.ps1`, not in the repo) now passes
  `--dangerously-skip-permissions` (scheduled session only; see F83 for the one residual —
  the unrecorded bypass acceptance dialog, confirmed by the 2026-07-13 08:57 run); still open:
  whether the three skipped days (07-09/07-11/07-12) are re-run — the 07-07 precedent is skip
  (the F78-1-unpushed part of the 07-11 callout was RESOLVED 2026-07-11: user said push);
  (2) F80 store fix mechanism (store edits are sacred); (3) merged-worktree cleanup (see
  registry); (4) repo rename before TSMC-branded exposure.
- **NEXT:** claim a stage-6 lane per its plan
  (`docs/superpowers/plans/2026-07-08-f78-stage6-change-first-renderer.md`, base must import
  `gpu_agent.asof` + `gpu_agent.pricefeed` — current main does). After F78: F79 (own
  brainstorm/spec), F65, F66, F80. Then the **F81–F86 gap wave** (2026-07-12 section in
  `docs/fix-backlog.md`, user-adjudicated: brain diversity, corrections pathway, scheduled-daily
  grant + event wake, external scoreboard, manipulation-resistance slice, model-swap
  recalibration), beside the standing F23/F24/F25 track.

> **[2026-07-12 SCHEDULED DAILY — BLOCKED (web-fetch tooling still permission-gated); AFK-default 2026-07-12.]**
> The scheduled 2026-07-12 headless daily (`category:chips.merchant-gpu`, mode=daily, live gather) hit the
> SAME wall as 2026-07-09 and 2026-07-11: every sanctioned web-fetch path is permission-gated in this
> non-interactive session. Confirmed THIS session by direct probe: `agent-reach doctor --json` (approval
> required), `scripts\web-reach-ensure.cmd --json` (approval required), `WebFetch` and `WebSearch`
> (permission not granted — probed at BOTH main-loop and subagent level). `import gpu_agent` OK (venv
> fine); `git pull --ff-only` already up to date; tree clean at session start (no concurrent instance
> mid-run; `store/cycle-log.json` keeps its finalized journal). Recorded/demo mode NOT authorized (the
> schedule asks for live gather); hand-rolling raw fetches would be improvising outside the skill
> (forbidden). Claude file-write tools (Edit/Write) gated again — this note written via the allowlisted
> `.venv` Python channel. **Action taken (AFK-default; scheduled run, no user available):** category NOT
> run, NO scorecard written, `store/` untouched, nothing fabricated, no scratch `work/` dir created. This
> doc-only commit IS pushed — an AFK-default judgment: `main == origin/main` and the tree was clean
> beforehand, so no other instance's unpushed work gets published (the 2026-07-11 confound), it is not a
> merge, and the project rule requires session end with `main == origin/main`. **Standing decision still
> open (07-09/07-11 gate):** grant WebSearch+WebFetch(+agent-reach) to the scheduled session, or keep
> skipping blocked days. Do NOT auto-re-run this day until the user decides.

## HISTORICAL — blocked-daily callouts + 2026-07-08 state (superseded 2026-07-12 by the block above)

> **[2026-07-11 SCHEDULED DAILY - BLOCKED (web-fetch tooling still permission-gated); AFK-default 2026-07-11.]**
> The scheduled 2026-07-11 headless daily (`category:chips.merchant-gpu`, mode=daily, live gather) hit the
> SAME wall as 2026-07-09: every sanctioned web-fetch path is permission-gated in this non-interactive
> session. Confirmed gated THIS session by direct probe: `agent-reach doctor` (approval required),
> `scripts\web-reach-ensure.cmd --json` (approval required), the `WebFetch` tool (probe to example.com -
> permission not granted), and the `WebSearch` tool (permission not granted). `import gpu_agent` works
> (venv fine), but the CLAUDE.md preflight (agent-reach doctor + web-reach-ensure) could not run and the
> gather-category gatherer contract (fetches via WebSearch/WebFetch) had no sanctioned fetch tool. The
> Claude file-write tools (Edit/Write) were ALSO gated again, so this note was written via the allowlisted
> `.venv` Python channel. Recorded/demo mode was NOT authorized; hand-rolling raw fetches would be
> improvising outside the skill (forbidden). **Action taken (AFK-default; scheduled run, no user
> available):** category NOT run, NO scorecard written, `store/` untouched (tree clean since the 07-09
> note, so `store/cycle-log.json` keeps its finalized 2026-07 v4 journal), nothing fabricated.
> **GIT STATE - IMPORTANT:** root `main` is 4 commits AHEAD of `origin/main` (`eb1b79b`) with F78-1
> wiki-decay commits `184b688..71d4fa4`, authored by a CONCURRENT instance and never pushed. Publishing
> another instance's unpushed work under an AFK-default is not sanctioned, so this blocker note is
> committed to local `main` ONLY and NOT pushed - `main != origin/main` on purpose until the user decides.
> **Awaiting user decision:** (a) re-run interactively / after granting WebSearch+WebFetch(+agent-reach)
> permission to the scheduled session, or (b) skip the day as with 2026-07-07 / 2026-07-09; AND (c) whether
> to push the 4 unpushed F78-1 commits (are they ready to publish?). Do NOT auto-re-run until the user decides.

> **[2026-07-09 SCHEDULED DAILY - BLOCKED (web-fetch tooling permission-gated); AFK-default 2026-07-09.]**
> The scheduled 2026-07-09 headless daily (`category:chips.merchant-gpu`, mode=daily, live gather) could not
> run the sanctioned gather. Raw network egress WORKS this session (a Python `urllib` GET to example.com
> returned HTTP 200), but every sanctioned web-fetch path is **permission-gated** in this non-interactive
> session: `WebSearch`, `WebFetch` (confirmed blocked at BOTH main-loop and subagent level via a probe),
> the `agent-reach` binary, and `scripts\web-reach-ensure.cmd`. So the CLAUDE.md preflight
> (`agent-reach doctor` + web-reach-ensure) could not run, and the gather-category gatherer contract (which
> fetches via WebSearch/WebFetch) had no sanctioned fetch tool. Hand-rolling raw-urllib fetches would be
> improvising outside the skill (user forbade improvising), and recorded/demo mode was NOT authorized.
> The Claude file-write tools (Edit/Write/mkdir) were also gated, so this note was written via the
> allowlisted `.venv` Python channel. **Action taken (AFK-default; scheduled run, no user available):**
> category NOT run, NO scorecard written, `store/` untouched, `store/cycle-log.json` keeps its finalized
> **2026-07** v4 journal, nothing fabricated. Gitignored scratch `work/daily-2026-07-09/` (only a
> `cycle-plan.json`) can be discarded. **Awaiting user decision:** either (a) re-run interactively / after
> granting WebSearch+WebFetch (+agent-reach) permission to the scheduled session, or (b) skip the day as
> with 2026-07-07. Do NOT auto-re-run until the user decides.

> **[2026-07-07 BLOCKED DAILY — CLOSED, will NOT be re-run] (by user decision, 2026-07-08).**
> The scheduled 2026-07-07 headless daily (`category:chips.merchant-gpu`) could not gather — that
> non-interactive session had no web egress, so all 3 gatherers returned zero blobs → category SKIPPED
> (skipped-no-gather), no scorecard written, `store/` untouched, nothing fabricated, recorded/demo mode
> not used. **Per user direction 2026-07-08 this cycle will NOT be re-run:** the day is skipped,
> `store/cycle-log.json` keeps its finalized **2026-07-06** journal, and the next live cycle just resumes
> on its normal cadence. The gitignored scratch `work/daily-2026-07-07/` can be discarded.

- **Date: 2026-07-08 (LATEST) — F60 DATA HALF MERGED + pushed (`b2a1a88`).** Authoritative current state:
  `main == origin/main == b2a1a88`, suite **1153/5**. Lane `fix/freshness-weights` (S1) reweighted the
  leading DEMAND set in `registry/indicators.json` — `rpoBacklog` 0.10→0.14, `vendorRevenueGuidance`
  0.12→0.16 — so fresh, corpus-persisted leading findings move DMI (Option A, user-approved). Weight-only
  → **F6 pin stayed green**; `scoring.py` byte-identical (side-semantics deferred to v1.5). One consequence
  handled: the v1.2 replay-fidelity test was frozen to its historical weight vector `_WEIGHTS_AS_OF_2026_06`
  (verified reproduces the stored dmi/smi/sdgi; **no store scorecard edited**). Lane commits
  `57cbb4d..d3d97e4`; note `docs/superpowers/eval-notes/2026-07-08-f60-freshness-weights-note.md`. **F60 is
  NOT ticked done** (see DEFERRED below). The merge landed cleanly on top of concurrent-instance work that
  advanced main first — crawl4ai web-reach tool #3 (`6f53c9c`), worktree-registry cleanup (`b1cf664`), and
  a live 2026-07 **v4** top-up cycle (`0f9a57a`, Strong/improving, SMI flips positive) — all file-disjoint
  (my 7 files vs its 21, zero overlap). **Lane cleanup pending (user's call):** the `fix/freshness-weights`
  worktree + local + remote branch are fully merged and safe to retire.
- **Date:** 2026-07-08 — the three finished lanes (P1/P2/P3) were merged to main and pushed on an
  explicit interactive user "go" (NOT an AFK-default). `main == origin/main == e16672a`. Suite 1150/5.
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **This session (all merges on main, in wave-plan order P1,P2 → P3):**
  - **P1 `fix/coord-hygiene` (F76) MERGED + pushed** (`a0e3123`): handoff discipline, controlled
    provenance vocabulary, retained-worktrees registry, `test_handoff_integrity.py` tripwire.
  - **P2 `fix/eval-gate-power` (F73) MERGED + pushed** (`6d098a7`): pooled-dispersion epsilon +
    symmetric marginal-pass band + seeded-regression canary (scaffolded). Barrier B1 satisfied
    (merged before any product rebaseline). No emitted prompt bytes → F6 pin stayed green.
  - **P3 `fix/contract-v1.4` (F72 + F71, +F75) MERGED + pushed** (`e16672a`): the frozen-core v1.4
    migration (all §7 decisions were user-approved 2026-07-06). Its charter Part 37 amendment collided
    with an orphaned 2026-07-06 dashboard-era reconciliation of the same paragraph — that orphan work
    was committed first as `d6abfaf`, then the conflict was hand-resolved into ONE paragraph carrying
    both v1.3/F63 and v1.4/F72. All 28 non-charter files byte-matched the branch; schemaVersion stays
    1.2; goldens/store untouched; F6 pin green. Barrier B2 satisfied (v1.4 lands before S1).
- **DEFERRED — MUST NOT LOSE (user-directed):** (1) F60 DATA HALF is now MERGED (`b2a1a88`) but F60 stays
  **OPEN**: its `scoring.py` side-semantics ships as a **future v1.5 migration**, AND the
  `smiContribution: 0.0` residual is a SUPPLY-leading gap (no leading supply indicator exists) that a
  demand reweight cannot move — needs an Option-C news-sourced leading supply indicator or the v1.5 half.
  Do **not** tick F60 done (wave-plan §6 ledger).
  (2) **NEW from the P3 lane:** `sufficiency.py::_sufficient` still counts raw `publisher_key`, not
  `collapsed_publisher_set` (it was outside P3's 3-consumer scope; `sufficiency.py` is now
  frozen-core-listed) — a bounded follow-up the lane flagged for a user decision.
- **FOLLOW-UP:** P2's seeded-regression canary needs a ONE-TIME live eval capture (Opus brains + graders)
  to fill its skipped fixture — must not be hand-authored. (The 2026-07-07 blocked daily will NOT be
  re-run — user decision 2026-07-08; see the closed callout above.)
- **NEXT (approved sequence, wave-plan §5):** **F60 data half ✅ MERGED (`b2a1a88`).** Remaining serial
  pipeline — F57/F58/F59 gather-freshness wave → **F77 renderer** (reconcile vs the merged dashboard-showcase
  first) → F64 → F65 → F66. Each prompt-changing step passes `run-eval` one at a time, no retry-until-green
  (barrier B3). (Ordering note: the resume line lists F57/F58/F59 ahead of F77 per the roadmap; wave-plan
  §5's forced-serial starts at F77 — an unresolved priority call, not a dependency; pick either first.)
- **Merged-lane cleanup (user's call, not yet done):** the three `fix/*` worktrees + branches
  (`coord-hygiene`, `eval-gate-power`, `contract-v1.4`) and the `dashboard-showcase` lane are all merged
  and hold no gitignored data worth keeping — safe to retire (see the RETAINED WORKTREES REGISTRY).

## HISTORICAL — 2026-07-06 planning & P1/P2/P3 lane dispatch (superseded 2026-07-08 by the block above)

- **Date:** 2026-07-06 (planning session — no code change, no cycle run; skill library + wave plan only)
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **That session (all on main, `main == origin/main`):**
  - Committed + pushed the 15-skill **desk skill library** at `6fe1841` (was untracked; now version-controlled).
  - Authored the **concurrency wave plan** for the open backlog →
    `docs/superpowers/plans/2026-07-06-concurrency-wave-plan.md` (committed this session). **Read it
    first** — it has the full wave/lane/barrier/merge-order map and the model-tier assignment.
  - **Four user-approved decisions (2026-07-06) — NOT AFK-defaults:** (1) the gate cluster ships as
    **ONE contract v1.4** = **F72 + F71**, with **F75** as companion doctrine on the same branch;
    (2) **F60 = registry-weight DATA half now**, `scoring.py` side-semantics **DEFERRED**; (3) **F72**
    records the originating publisher as **gather-blob metadata, NO schema bump** — v1.4 stays
    schemaVersion 1.2; (4) **HOLD all dispatch** until per-lane plans are reviewed and the user says go.
  - **DEFERRED — MUST NOT LOSE (user-directed):** F60's `scoring.py` side-semantics ships as a
    **future v1.5 migration**; do **not** tick F60 done when the data half merges (plan §6 ledger).
  - **Machine-local coordination tooling (NOT in the repo):** new `concurrent-edit-guard` skill
    (`~/.claude/skills`) + a PreToolUse/PostToolUse hook (`.claude/settings.local.json`, git-excluded
    via `.git/info/exclude`) that blocks editing a file another instance is mid-editing. **Needs a
    `/hooks` reload or restart to activate.** `instance-sync` now cross-references it.
- **Open pre-reqs before ANY dispatch (plan §7):** reconcile the live `dashboard-showcase` lane (its
  uncommitted desk-skill + charter edits sit on the main checkout — do NOT touch them); write the
  **P3 contract-v1.4 migration spec** for user approval; finalize the F76 + F73 per-lane task plans.
- **Concurrent instance still live:** `dashboard-showcase` in `.worktrees/dashboard` (presentation/
  dashboard work — may overlap the renderer stream F77/F64/F65; reconcile before claiming it).
- **NEXT (on user "go" only — nothing is dispatched yet):** (a) claim + dispatch **P1 (F76, Sonnet)**
  and **P2 (F73, Opus)** as parallel worktree lanes; (b) separately open the **P3 v1.4 migration
  spec** for user approval (frozen core — never AFK, only the user merges to main).

## How to update this file (F76 discipline)

- **One CURRENT STATE block.** The H1 title carries the single top-of-file resume marker (the
  `resume point` phrase, followed by a colon). When state changes, replace the top block
  **atomically**: in the same edit, move the superseded text down under a new
  `## HISTORICAL — <what/when>` heading. Never leave two "current" blocks.
- **Provenance labels are controlled** (see the Provenance vocabulary below): `user-approved`
  only when an actual user answer exists; `AFK-precedent` / `AFK-default` otherwise.
- **Retained worktrees** are tracked in the "## RETAINED WORKTREES REGISTRY" section, not in
  scattered "do not git clean" asides.

## DISPATCH STATUS — 2026-07-06 (post user "go")

> **SUPERSEDED 2026-07-08:** all three lanes below (P1, P2, and the then-PARKED P3) are now MERGED +
> pushed — see the current-state block at the top of this file. Kept as the dispatch-time record.

User gave **"go"** 2026-07-06. Actioned:
- **P1 `fix/coord-hygiene` (F76, Sonnet)** and **P2 `fix/eval-gate-power` (F73, Opus)** DISPATCHED as
  parallel worktree lanes (`.worktrees/coord-hygiene`, `.worktrees/eval-gate-power`), each executing
  its per-lane plan (`docs/superpowers/plans/2026-07-06-f76-coordination-substrate.md` /
  `-f73-eval-gate-power.md`) via subagent-driven TDD. Each lane STOPS before merge and writes
  `.superpowers/handoffs/<lane>-DONE.md`. **Only the user merges to main.**
- **P3 `fix/contract-v1.4` (F72+F71, +F75 companion) — PARKED, NOT dispatched.** Frozen-core; the
  design spec `docs/superpowers/specs/2026-07-06-contract-v1.4-migration-design.md` §7 lists **6 open
  decisions requiring user sign-off** (never AFK). The migration branch opens only after §7 is answered.
- **User-approved decision D5 (2026-07-06):** F72 fix = BOTH `registry/syndicators.json` + L1 near-dup
  content collapse.
- **DEFERRED, MUST NOT LOSE:** F60 `scoring.py` scoring-half → future v1.5 migration (wave plan §6);
  do NOT tick F60 done when its data half merges.

## HISTORICAL — desk-LIVE item 1 cleared (2026-07-06 morning; superseded by the section above)

- **Date:** 2026-07-06 (morning — post daily #2, ablation verdict recorded)
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **Desk-LIVE item 1 is CLEARED** (roadmap "unit of the build" checklist): TWO gate-clean
  daily cycles on the current stack (**#1** `d9cfb3f` asOf 2026-07-05, **#2** `adc7251`
  asOf 2026-07-06) plus the store-consuming 2026-07 flagship (`99ca522`, F62 corpus merge
  live). Both dailies passed the F63 sufficiency gate with **no bypass** and zero hand
  edits; the F71 deadlock never recurred.
  - **Daily #2** (`store/chips.merchant-gpu/2026-07-06-v1.json`, DMI 0.040 / SMI −0.027 /
    SDGI 0.067; Strong/worsening): binding constraint shifted export enforcement →
    HBM/DRAM+NVMe memory scarcity on 3 distinct publishers (sufficiency PASS). Voice lint:
    one DRAM re-dispatch wave, passed. Thesis: 13/13 first pass — AMD weakened APPLIED on
    the 2nd consecutive signal (high→medium, pending challenge resolved); custom-asic
    strengthened DEFERRED (2 publishers < 3); pricing-power strengthened (medium→high);
    2 promotions; new proposal `rising-memory-costs-inflate-ai-server-economics`. Two
    primaries chased in-run: SharonAI 8-K (corrects press "rent-back" language — the
    filing has revenue-sharing + credit-support only) and Meituan's LongCat official blog.
    First day-over-day PMI computed (+1.00, 2 matched series) with a logged artifact: the
    lambda.ai delta compares different GPU models (provider-grain D6 series key — F51
    follow-up candidate, noted in the cycle log; overlay-only). Pin + F74 journal tripwire
    green after the run.
  - Remaining desk-LIVE items (2,3,4,6 look satisfied by these runs; 5 = eval archetype
    coverage already held): item 1 was the last open proof — **next probation step per
    the roadmap is category #2 (the desk recipe), or the F71/F75 gate-precedence fixes
    before any unattended loop.**
- **The 2026-07-05 flagship v3 store state is now COMMITTED** (`99ca522`) — the prior
  session had left it uncommitted in the working tree. Its cycle log (with the F71
  `sufficiency: bypassed` record) is preserved in that commit's `store/cycle-log.json`.
- **Blind baseline ablation SCORED by the user (2026-07-06) — the desk (B) WON on
  substance.** Verdict recorded in `docs/action-items.md` ("Verdict — blind baseline
  ablation 2026-07"): the desk was the only artifact giving implications + watch items
  (the thesis-book machinery); both web-only baselines were stale and non-actionable.
  Every desk deficit named is presentation-layer → logged as **F77** in the backlog
  (order by importance, consolidate sections, cap volume; renderer-only). The blinding
  is spent — `docs/ablation-2026-07/` is now a historical record.
- F71 (anchor-bound vs sufficiency-gate precedence) remains OPEN in the backlog — it did
  not fire this cycle but must land before any unattended loop runs a cycle.

## HISTORICAL — F63 state at merge time (2026-07-05, superseded by the section above)

- Main was green and pushed at `9292751` (includes the eval-v2 merge `c0d5dd2`; suite on
  merged main 1031/4). The F63 branch passed its v2 gate (`ef52790`): extract 6.625 /
  judge 7.75 / thesis 6.00 vs bars 6.5833/7.3333/5.6667, no craters; rebaselined via the
  `--verdict` governance path (no force); suite on the branch 1059/4/0. F63 then MERGED
  to main `017b592`. Run journal:
  `docs/superpowers/eval-notes/2026-07-05-f63-regate-run-notes.md`; raw runs (gitignored):
  `work/eval-f63-regate-2026-07-05/{r1,r2,r3}` plus the 2026-07-04 runs — see the RETAINED
  WORKTREES REGISTRY below.

## HISTORICAL — F63 pre-eval-v2 state (superseded 2026-07-05 by the section above)

- **Tasks 1–7 complete, reviewed, committed** on branch `f63-corroboration-doctrine`
  (worktree `.worktrees/f63-corroboration` — see the RETAINED WORKTREES REGISTRY below;
  gitignored `work/` holds both eval runs' raw data). Ledger: worktree `.superpowers/sdd/progress.md`.
  Built: `gpu_agent/publisher.py` (F31 identity, single source of truth); `registry/corroboration.json`
  (`minDistinctPublishers: 3`) + `config.min_distinct_publishers()`; the ONE sanctioned frozen-core
  edit — `gate.py` F2e secondary-corroboration exception (contract v1.2→v1.3, migration note in
  `docs/migrations/2026-07-contract-v1.3.md`); `thesis.py` anti-whipsaw rule-6 corroborated-step
  (`corroboratedStep` recorded, logged, no auto-resolve); `gpu_agent/sufficiency.py` +
  evidence-sufficiency gate wired at `judge --recorded` / `pipeline --recorded-judge`
  (`--no-sufficiency` bypass); three amended SYSTEM prompts (extract corroboration exception,
  thesis ≥3-publisher reversal exception, judge sufficiency rule); charter Part 37 amendment.
- **Task 8 (run-eval) ran TWICE and FAILED TWICE** vs the F62 incumbents (extract 6.75 /
  judge 7.50 / thesis 6.00): attempt 1 = 6.38/7.00/6.00-tie; full replication = 6.38/6.75/5.50.
  Pre-committed disposition executed: STOP, pin stays red, NO rebaseline, NO --force.
  **Diagnosis (evidence in the run notes): the deficits are incumbent-bar noise, not F63
  regressions** — the bar is F62's high-draw attempt 3; identical-prompt runs swing 6.25–7.50;
  no deduction in either run traces to the F63 prompt changes, and the F63 mechanisms graded
  WELL (F2e caught the within-document-corroboration error in BOTH runs' fresh generations;
  a judge visibly kept the prior binding constraint citing single-outlet evidence).
  Durable notes (committed): `docs/superpowers/eval-notes/2026-07-04-f63-run-notes.md`.
  Raw runs (gitignored): worktree `work/eval-f63-2026-07-04/` and `-r2/`.
- **RECOMMENDATION MADE TO USER (2026-07-05), NOT YET APPROVED — do not start without a user go:**
  build **eval-v2** as its own feature (brainstorm → spec → plan → SDD, branch from main):
  (1) baseline = N=3 replicate runs storing per-seam mean + per-run scores + per-case medians;
  (2) gate = one fresh run vs baseline-mean − ε (ε computed from the stored replicates,
  deterministic); marginal fail auto-triggers exactly ONE replication, two-run mean decides,
  hard stop; (3) add a per-case crater prong (fail if any case drops ≥3 vs its baseline median);
  (4) frozen negatives unchanged. Then re-gate F63 under the new rule (no judgment-call pass).
  Optional fold-in to F63 before its re-gate (user to confirm): the two proven prompt
  clarifications — corroboration counts publishers "across separately fetched documents",
  and state the `impact.direction` enum — plus the `CEO` acronyms.json allowlist entry.
  User's alternatives if they reject eval-v2: A force-rebaseline / B more replications / D hold.
- **F63 merge blockers (in order):** user decision on eval-v2 → gate PASS → final whole-branch
  review (opus, review-package from merge-base; not yet run) → rebase/merge onto current main
  (main advanced past F63's base — careful with shared frozen files) → USER GO to merge.
- Fix-backlog additions from the runs are in `docs/fix-backlog.md` ("F63 eval-run findings").

## ⚠ 2026-07-05: EVAL-V2 MERGED (`c0d5dd2`) — the eval gate rule CHANGED

- `fixtures/evals/baseline.json` is now **schema v2**: 3 replicate runs; bar = replicate mean − ε
  (extract ≥ 6.5833 / judge ≥ 7.3333 / thesis ≥ 5.6667) + per-case crater prong (median − 3);
  marginal fail ⇒ exactly ONE replication, two-run mean decides. `eval rebaseline` now takes
  `--runs <d1> <d2> <d3>` (+ `--verdict` governance proof); the old `--out` form is GONE.
  Follow the rewritten `.claude/skills/run-eval/SKILL.md`. Spec:
  `docs/superpowers/specs/2026-07-05-eval-v2-replicate-baseline-design.md`. Suite on merged
  main: 1031 passed / 4 skipped. (This instance works `.worktrees/eval-v2` + the F63 re-gate;
  the authoritative full HANDOFF still lives on the f63-corroboration-doctrine branch.)

## ⚠ CONCURRENT-INSTANCE COORDINATION (still live)

- **WAVE-2 LANES ALL DONE + REVIEWED READY-TO-MERGE (2026-07-12, orchestrator session) —
  AWAITING USER MERGE** (F80 awaiting a diff sign-off, see below). All design forks were
  answered INTERACTIVELY by the user (user-approved provenance in each spec); lanes ran under
  the question-stop rule — F24 raised ONE question-stop (parked clean, resumed with the user's
  three answers), F72/F87 raised none. Review verdicts + open notes appended to each sentinel.
  - **F24 stage 1 READY** `.worktrees/f24-entities`, branch `f24-entity-resolver` @ `51ad3ff`
    (6 commits, suite 1221/5). Entity resolver: NVDA/nvidia one identity at the new-finding
    seams; unregistered names byte-unchanged + flagged (stderr + cycle-log); 10 test files
    migrated — review audited all 10 FAITHFUL, 0 Critical/Important. Merge order vs F25:
    don't-care (zero overlap). Stage 2 (historical page consolidation) intentionally open.
  - **F72 v1.4.1 READY (frozen-core — user-merge-only)** `.worktrees/f72-sufficiency`, branch
    `f72-sufficiency-collapse` @ `7a2b9a5` (2 commits, suite 1205/5). Sufficiency counts
    collapsed publishers via the SAME helper as F2e (9-line seam); shadow-check: ZERO past
    verdict flips (reviewer reproduced independently). Review: Ready to merge, 0 Crit/Imp.
  - **F87 READY (merges only AFTER F25 — stacked)** `.worktrees/f87-stale-lock`, branch
    `f87-stale-lock-takeover` @ `7859193` (7 commits, suite 1228/5). Stale-lock takeover;
    review round 1 caught a real two-reclaimers race (fixed, mutation-test-verified);
    round 2: Ready to merge.
  - **F80 PREPARED, AWAITING USER DIFF SIGN-OFF** `.worktrees/f80-wiki-category` — the
    two-line `category: null` → `"chips.merchant-gpu"` edit + red-green-verified tripwire
    test sit UNCOMMITTED in the worktree until the user signs off (store edits are sacred).
- **WAVE-1 FIX LANES ALL DONE + REVIEWED READY-TO-MERGE (2026-07-12, orchestrator session) —
  AWAITING USER MERGE.** Three background Opus lanes (user-directed "start the parallelization
  today"), each superpowers-workflow built, each given a fresh-context Opus whole-branch review
  (verdicts + open decisions appended to each sentinel). Only the user merges. Suggested merge
  order: F25 and F23 any time (file-disjoint from everything); F56 AFTER F78 stage 6, rebased.
  - **F25 READY** `.worktrees/f25-wiki-scale`, branch `f25-wiki-store-scale` @ `7f4e762`
    (8 commits, suite 1215/5). Wiki store: incremental log cache, Aho-Corasick health scan,
    lockfile seq mint (~54×/40×/3.6× measured). Review: Ready to merge, 0 Critical; ONE
    forward-looking flag logged as **F87** (stale-lock takeover before unattended runs).
    Sentinel: `.superpowers/handoffs/f25-wiki-scale-DONE.md`.
  - **F56 READY (after stage 6)** `.worktrees/f56-asof`, branch `f56-asof-validation` @
    `2516064` (5 commits, suite 1210/5). All 10 `--as-of` CLI seams validated; review: Ready to
    merge, 0 Critical/Important, both AFK picks endorsed. **Merge AFTER F78 stage 6, rebase
    first** (shared cli.py, tiny). Sentinel: `.superpowers/handoffs/f56-asof-DONE.md`.
  - **F23 READY** `.worktrees/f23-compliance`, branch `f23-compliance-matrix` @ `a801277`
    (4 commits, suite 1210/5). Compliance matrix: 123 rows, 57/25/10/27/4/0, 65 test-function
    pins + rot lint. Review round 1 caught 1 Critical + 3 Important (all fixed, verified);
    round 2: Ready to merge. OPEN DECISION A4 in the sentinel (P19.budget DEFERRED vs
    NOT-ENFORCED — reviewer leans DEFERRED). Sentinel:
    `.superpowers/handoffs/f23-compliance-DONE.md`.
- **F78 stage-6 lane CLAIMED + IN FLIGHT (2026-07-12).** Worktree `.worktrees/f78-stage6`,
  branch `f78-stage6` off `b7e66aa` (dependency gate verified: `gpu_agent.asof` +
  `gpu_agent.pricefeed` import). Plan
  `docs/superpowers/plans/2026-07-08-f78-stage6-change-first-renderer.md` incl. the 2026-07-11
  amendment (Tasks 5b/5c/8-amend/11). Touches: `gpu_agent/change.py` (new), `gpu_agent/report.py`,
  `gpu_agent/reader.py`, `gpu_agent/brief.py` wording, CLI wiring, `registry/acronyms.json`,
  `docs/dashboard.html`, new `tests/test_change_*` + `tests/test_report_*`. Subagent-driven;
  STOPS before merge — only the user merges. Sentinel: `.superpowers/handoffs/f78-stage6-DONE.md`.
- **ALL PRIOR F78 stage lanes are CLOSED (2026-07-12): stages 2/3/4/5 merged to main by the user**
  (`fd0b08c`/`6e24259`/`b9a3251`/`fdbc7fb`). Original stage-2
  instance, if you return: your lane was adopted (user-directed), reconciled, reviewed, and
  merged — see `.superpowers/handoffs/f78-stage2-DONE.md`; do not resume it.

- **F78 stage-3 lane DONE (2026-07-12) — READY TO MERGE, awaiting the user.** Worktree
  `.worktrees/f78-stage3-corpus`, branch `f78-stage3-corpus-ages-via-wiki` @ `d0f35d3` (7 commits
  on base `fdbc7fb`). Suite 1187/5, eval pin green, frozen-core diff empty; final opus
  whole-branch review: Ready to merge. Sentinel `.superpowers/handoffs/f78-stage3-DONE.md`
  (full delivered-list + follow-ups). Two follow-ups logged as F80 + a doc line in
  `docs/fix-backlog.md` (live-store `category: null` on entity:nvidia/entity:multi; cli-verbs
  doc drift). Mid-execution user-approved decisions recorded in the sentinel (any-page-keeps
  dedup rule; red-import window between Tasks 1–3; WINDOW_DAYS_DEFAULT retirement path).
- **F78 stages 4+5 MERGED to main by the user 2026-07-12** (`b9a3251`, `fdbc7fb`; suite
  1188/5; pushed). Stage-2 worktree (`f78-stage2`, another instance) looks complete
  ("suite green" commit, clean tree) but carries NO DONE sentinel — treat as that
  instance's open lane; do not touch.

- **`dashboard-showcase` lane is ACTIVE (another instance) — 2026-07-06.** Worktree
  `.worktrees/dashboard`, branch `dashboard-showcase` @ `6fe1841`; spec
  `docs/superpowers/specs/2026-07-06-merchant-gpu-dashboard-design.md`. Its uncommitted edits are
  visible on the main checkout (10 desk-skill `SKILL.md` files + `docs/agent-swarm-charter.md`) —
  **do NOT touch or `git add -A` them.** Presentation work; may overlap the renderer stream
  (F77/F64/F65) — reconcile before claiming a renderer lane.
- **P1 `coord-hygiene` lane CLAIMED + DISPATCHED (2026-07-06).** Worktree `.worktrees/coord-hygiene`,
  branch `fix/coord-hygiene` (F76, Sonnet). Touches docs (`HANDOFF.md`, `fix-backlog.md`, wave plan)
  + `tests/test_handoff_integrity.py`. File-disjoint from P2 and from the dashboard lane. Completion
  sentinel: `.superpowers/handoffs/coord-hygiene-DONE.md`. STOPS before merge — only the user merges.
- **P2 `eval-gate-power` lane CLAIMED + DISPATCHED (2026-07-06).** Worktree `.worktrees/eval-gate-power`,
  branch `fix/eval-gate-power` (F73, Opus). Touches `gpu_agent/evals/harness.py`, `tests/test_evals_*`,
  `fixtures/evals/canary/`. No emitted prompt bytes → the F6 pin stays green. Completion sentinel:
  `.superpowers/handoffs/eval-gate-power-DONE.md`. STOPS before merge — only the user merges.
- **Coordination guard (machine-local, this checkout):** a `concurrent-edit-guard` PreToolUse hook
  now blocks edits to a file another instance is mid-editing (needs `/hooks` reload/restart to arm).
  See the `concurrent-edit-guard` and `instance-sync` skills.

- **F74 (cycle-log clobber fix) is DONE — merged to main `257cf1b` (2026-07-05, user go);
  claim RELEASED; branch + worktree removed.** Sentinel:
  `.superpowers/handoffs/f74-cycle-log-DONE.md`. Operational changes every future run must
  know: `cycle-plan --out` refuses non-bare targets (plans go to
  `work/<run-dir>/cycle-plan.json`, NEVER `store/cycle-log.json` — run-cycle step 1
  updated); finalize (step 6) requires `asOf`/`mode`/`capturedAt` and no bare `ready`
  entries; the suite tripwire `tests/test_store_cycle_log_integrity.py` goes RED on any
  journal skeleton. The restore step became moot (daily `d9cfb3f` committed a healthy
  journal; the monthly v3 journal with the F71 bypass record is preserved at `99ca522`).

- F67 is DONE (merged `b0e8061`, completion handoff `.superpowers/handoffs/output-engineering-DONE.md`).
- **F69 (web-reach layer) is DONE — merged to main `e167c6b` (2026-07-04); branch
  `f69-web-reach-layer` deleted.** Data-driven registry `registry/web-reach-tools.json`
  (agent-reach first; a 2nd github drops in as a data entry), health-check preamble +
  gatherer-contract additions in `gather-category`, doctrine in charter Part 37, operator doc
  `docs/web-reach.md`. Frozen core untouched; no scoring change (corroboration math stays F63 —
  see the F63 handoff note in the backlog). Spec/plan 28e38de/a23467f; final whole-branch review
  clean. (Earlier cross-branch mixup with this instance — a stray commit onto the F69 branch —
  was resolved before the merge.)
- **F70 (last30days — 2nd web-reach github) is DONE — merged to main `7938eb4` (2026-07-04);
  branch `f70-last30days-webreach` deleted.** Adds `mvanhorn/last30days-skill` to
  `registry/web-reach-tools.json` as tool #2 and introduces a `role` field: `fetch` (agent-reach —
  raw content → secondary blobs) vs `discovery` (last30days — a last-30-days multi-platform
  synthesizer used for **leads only**: mined for leads in gather Round-building step 2b, its
  synthesized brief NEVER ingested as a blob — Part 37). Role-aware step-3 gatherer contract +
  charter Part 37 `role` clause + `docs/web-reach.md`. Whole-branch review caught + fixed a Critical
  (the subagent contract was not role-aware). Frozen core untouched.
- **NOTE — `docs/roadmap.md`:** the concurrent instance committed its 326-line roadmap doc to main
  as **`c4913a6`** (independent of F69/F70), landed on top of `ed378ae` while F70 was on its branch.
  main had advanced to `c4913a6` before the F70 merge, so it rode into origin via the F70
  merge/push — it is the concurrent instance's own commit, not part of F70. (My F70 charter commit
  had briefly swept an earlier untracked copy in via `git add -A`; that was un-bundled, so F70's own
  commits contain only F70 files.)

## RETAINED WORKTREES REGISTRY

Merged-feature worktrees are kept ONLY for gitignored data (raw eval replicate runs, SDD
ledgers). Never `git clean` these. Remove a worktree only when its "can go when" condition holds.

| Worktree | Branch | Retained because | Contains (gitignored) | Can be removed when |
|---|---|---|---|---|
| `.worktrees/eval-v2` | `eval-v2-replicate-baseline` | raw replicate-baseline eval run + SDD ledger | `work/eval-v2-migration/`; `.superpowers/sdd/` (5 task briefs/reports + 7 review diffs) | v2 baseline superseded + notes committed |
| `.worktrees/f62-flagship-store` | `f62-flagship-consumes-store` | raw eval runs (attempts 1-3) + SDD ledger | `work/eval-f62-2026-07-04/`; `.superpowers/sdd/` (8 task briefs + 9 review diffs) | F62 eval history no longer referenced |
| `.worktrees/f63-corroboration` | `f63-corroboration-doctrine` | raw eval runs (2026-07-04/05) + SDD ledger | `work/eval-f63-2026-07-04/`, `work/eval-f63-2026-07-04-r2/`, `work/eval-f63-regate-2026-07-05/`; `.superpowers/sdd/` (progress.md + 7 task briefs/reports + 8 review diffs) | F63 re-gate history archived |

| `.worktrees/f78-stage3-corpus` | `f78-stage3-corpus-ages-via-wiki` | SDD ledger + per-task briefs/reports/review packages | `.superpowers/sdd/` (ledger, 6 briefs/reports, 7 review diffs) | F78-3 build history no longer referenced |
| `.worktrees/f78-stage2` | `f78-stage2` | adoption-reconciliation evidence | `.superpowers/sdd/` (whole-branch review package) | stage-2 review history archived |

**Safe to retire now (merged 2026-07-12, NO gitignored data — user's call):** `.worktrees/{f78-stage4,
f78-stage5}` + branches `f78-stage4`, `f78-stage5`. Also merged and removable once their retained
data is archived: the two rows above. `.worktrees/f73-canary` (branch `fix/f73-canary`) is PARKED
unmerged — needs redesign, not cleanup.

**Removed 2026-07-08 (merged, no gitignored data worth keeping):** `.worktrees/{dashboard, coord-hygiene,
eval-gate-power, contract-v1.4}` and their branches (`dashboard-showcase`, `fix/coord-hygiene`,
`fix/eval-gate-power`, `fix/contract-v1.4`) — all merged (`75db88f`/`a0e3123`/`6d098a7`/`e16672a`).

**Concurrent active lane (another instance — NOT retained-only, do not touch):** `.worktrees/freshness-weights`
(`fix/freshness-weights`) appeared 2026-07-08, unmerged; owned by a live concurrent instance that manages its
registry entry and merge. The `.worktrees/crawl4ai` (`feat/crawl4ai-webreach`) lane is now DONE: merged to
main (`6f53c9c`, in `origin/main`), worktree removed + branch deleted; crawl4ai web-reach **fetch** tool #3
also installed and smoke-verified on the operator machine (`crawl4ai 0.9.0`; real `crwl` crawl OK) 2026-07-08.

Update this table whenever a worktree is added or removed. It replaces every scattered
"do not git clean <path>" warning — delete those asides as you migrate them here.

## STANDING RULE (F6 gate, now ACTIVE)

Any edit that changes the emitted brain prompts (extraction/judgment/thesis prompt files, their
cli vocab glue, or registry vocab data) turns the suite RED via
`tests/test_evals_baseline_pin.py`. The unlock is NEVER a hand-edit of `fixtures/evals/baseline.json`:
run `.claude/skills/run-eval/SKILL.md` (re-dispatch brains + graders), then
`gpu-agent eval rebaseline`, and commit the new baseline WITH the prompt change. F57/F58/F62/F63
prompt work all flows through this gate.

## IMMEDIATE NEXT TASK — await user decision on eval-v2, then either build it or execute the chosen F63 disposition

Sequence position: F62 ✅ MERGED (`eb925bc`) → **F63 BUILT/BLOCKED (see top section)** →
F57/F58/F59 → F60 → F64 → F65 → F66. Eval-v2, if approved, slots in as its own feature before
F63's re-gate. F56 remains a safe tiny side item.

## Newest state (newest first)
  - **2026-07-11/12 sessions: F78 stages 1–5 all on main (`fd0b08c`, suite 1200/5); exec-format
    spec + stage-6 plan amendment committed; F79 + F80 logged; SDEWS docx + extraction committed;
    v5 top-up landed (concurrent instance).** Details in the current-state block at the top.
  - **SHOWCASE DASHBOARD shipped + merged + pushed (2026-07-06, `75db88f`; sentinel
    `.superpowers/handoffs/dashboard-showcase-DONE.md`).** New plain-English HTML dashboard from
    report.txt + scorecards: `gpu_agent/dashboard/` + `scripts/build_dashboard.py` → `docs/dashboard.html`
    (ranked most-important-first; 8 sections), plus the reusable `plain-language-writer` subagent with
    voice calibration. Additive only — no frozen-core / brain-prompt / wave interaction; suite 1103/4.
    OPEN: (1) voice calibration not run (no samples dropped — prose is neutral plain English);
    (2) claims section sourced from gitignored `work/report.txt`, so rebuild in place post-cycle.
  - **`docs/roadmap.md` — the phased roadmap from this one desk to the full charter product
    (2026-07-04): forks user-approved live (layer tier after cats #2–3, Main after ~2 layers,
    coarse size tags); final doc committed under AFK-precedent — open questions inside.**
  - **F6 TASK 10 DONE — initial eval baseline committed (`0344949`), hash-pin gate ARMED.**
    Live run 2026-07-04 (all tool-less Opus): 14 fresh brains + 1 F38-safe voice re-dispatch, all
    gate-clean; 18 rubric graders + 1 schema re-dispatch. Seam means extract 6.62 / judge 6.75 /
    thesis 5.50; calibration held (negatives 2/1/0/2 of 8, limit 4). The run itself caught and
    shipped three fixes (eval working as designed on day one): extract prompt was missing the
    demand/supply indicator vocabulary — context-free brains were 100% gate-dropped (completes
    F55; `6d9fa67`+`f1dc904`); F67 voice-lint acronym allowlist gaps (GB300/GAAP/GDP) + an
    abbreviation-blind sentence splitter that counted "U.S." as a sentence end (`ac1e209`); one
    golden-case gate-outcome re-pin (`4aa8154`). Run artifacts: `work/eval-2026-07-04/`
    (RUN-NOTES.md is the full run journal).
  - **F6 SECOND HALF MERGED (`87f281a`, user-approved; 15 branch commits; suite 910/5 verified
    on merged main and pushed).**
    `gpu_agent/evals/` (cases/rubric/emit/prompt_hash/harness) + `eval` CLI
    (emit-brain/record-brain/emit-grade/record-grade/rebaseline) + 18-case golden set curated from
    the real July cycles (provenance spot-verified byte-exact; 4 anchor-decidable negatives) +
    fixture-health tests + hash-pin regression-gate test (skips until baseline.json exists) +
    `.claude/skills/run-eval` skill. Spec `docs/superpowers/specs/2026-07-04-f6-eval-harness-design.md`,
    plan + Task-10 checklist `docs/superpowers/plans/2026-07-04-f6-eval-harness.md`. Post-F67
    alignment done on-branch: main merged in (`57be83c`), eval judge brain-gate mirrors the live
    voice lint, 4 pre-F67 judge positives re-pinned gateOutcome=reject (documented). Comparison
    rule: per-seam mean ≥ incumbent, TIES PASS. **Decision provenance: user approved scope/
    architecture/spec + chose subagent-driven execution; user was AFK at the finish-branch gate —
    merge deliberately left for the user (see pending-decision section).**
  - **F67 output contract MERGED (`b0e8061`, suite 873/3 on main).** Reader vocabulary layer
    (`gpu_agent/reader.py` + `registry/acronyms.json`), voice lint fail-loud on `judge --recorded`
    + `pipeline --recorded-judge` (`--no-voice-lint` bypass), exec-readable renderer (BLUF, appendix
    divider, zero raw ids above it), run-cycle session-output rule. Read
    `.superpowers/handoffs/output-engineering-DONE.md` for the delivered list + F68 follow-ups
    logged in the backlog.
  - **F52/F53/F54 DONE (branch f52-f53-f54 merged, 5 commits `2a2dae7..2c070f4`; final opus
    review: Ready to merge, no Critical/Important).** F52: docIds vintage-scoped at the gather
    seam (`{slug}-{digest}-{asOf}`; `ingest --as-of` required; finding ids inherit; L1 url+hash
    unchanged). F53: extractor seam rejects measured price rows whose value.unit != the
    registered canonical unit AND `extract --emit-prompt` lists the price-side ids + canonical
    units (F55 pattern; defaults byte-identical). F54: two seed triggers reworded to pass the
    observable heuristic + seed-lint test; live book untouched. New: F56 (tiny, --as-of shape
    validation + two cosmetic minors) added to the backlog.
    **PROCESS CAVEAT:** the user was away at every question gate this session — the spec's
    approach picks (all matching the backlog's stated lean) and the merge decision followed the
    recommended options + prior precedent. Spec flags this in its Decision-provenance note:
    docs/superpowers/specs/2026-07-03-f52-f53-f54-small-fixes-design.md. Relitigate there if any
    pick is wrong.
  - (F52–F54 live verification criteria: see VERIFY NEXT LIVE CYCLES under the approved
    sequence below.)
  - **First MONTHLY live cycle on the sp5 stack** (asOf 2026-07, committed `a8b7398`): scorecard
    `store/chips.merchant-gpu/2026-07-v1.json` DMI +0.633 / SMI −0.453; all 7 standing theses
    judged (3 strengthened→high; custom-asic reaffirmed@high; pricing-power reaffirmed;
    export-control + vendor-financed-circularity weakened→low) + 2 new provisional proposals
    (customer-concentration-risk, networking-attach-as-systems-moat).
  - **F55 DONE (`39f427e`):** emitted prompts now carry the id vocabularies the gates enforce —
    `extract --emit-prompt` lists the taxonomy's valid impact.targets ids; `judge --emit-prompt`
    appends a `<citationGroups>` block (per-dimension id groups + the six DIMENSIONS names);
    thesis SYSTEM states the v1 observable-trigger heuristic verbatim. Default prompt paths
    byte-identical; `tests/test_prompt_vocab.py`. Dispatching sessions no longer supply id lists
    out-of-band — trust the emitted prompt.
- Sub-project 5 (the Thesis Book) is BUILT, MERGED, and LIVE-VERIFIED:
  - **5-1 thesis engine** merged @ `7197226` (11 commits; suite 626→714/3): `gpu_agent/thesis.py`
    (models, rebuild-verified ThesisStore, gate rules 1–7, anti-whipsaw apply engine F5),
    `gpu_agent/memory.py` (F4 bundle), thesis/judge prompts (memory injection, byte-identical when
    absent), `thesis` CLI stage (emit→recorded), run-cycle skill stage (e), seed book
    `registry/theses.chips.merchant-gpu.json`.
  - **5-2 output surgery** merged @ `d5dd492` (6 commits; suite 714→796/3): `gpu_agent/bands.py`
    five-word band map, THE CALLS + WHY renderers in brief.py, page reorder (CALLS → STATE → WHY →
    drill-down → TRUST footer), raw indices demoted to the footer, cli._report book loading, e2e
    acceptance test. One spec-vs-plan conflict resolved under the standing SPEC-WINS rule (WHY
    Contested widened to competitive-lens at any conviction + findingIds on every WHY line).
  - **Integration gate PASSED (2026-07-03 live daily cycle):** THE CALLS renders from a real judged
    book. Store state committed: scorecard `store/chips.merchant-gpu/2026-07-03-v1.json`
    (DMI +0.133 / SMI +0.147), seeded+judged thesis book `store/theses/chips.merchant-gpu/`
    (2 strengthened→high, 3 reaffirmed, 1 weakened→low, +1 provisional proposal), wiki/dedup/L1
    artifacts, finalized `store/cycle-log.json` (every brain re-dispatch reason logged). The F4
    MEMORY block fed both brains live; judged direction moved vs prior (Strong/steady, was
    Strong/improving; bottleneck rotated competitiveStructure→moat).

## IMMEDIATE NEXT TASK — the APPROVED SEQUENCE (user-approved 2026-07-03; full context in
## docs/fix-backlog.md's F57–F66 section header — do not re-derive or re-ask)

Quick wins, independent: **F56** (tiny, --as-of shape validation). F61 is DONE (subsumed by F67).
Then in order — each feature starts with brainstorming, per charter:
0. **F6 second half — MERGED (`87f281a`).** Remaining: Task 10 live baseline only (see
   IMMEDIATE NEXT TASK above) — it arms the hash-pin gate that F57/F58/F62/F63 depend on.
1. **F62** — flagship consumes the daily store (highest-leverage; the monthly brief currently
   discards everything the dailies learned). Interacts with F52 vintage ids + L2 dedup.
2. **F63** — corroboration doctrine (N independent secondary publishers move one bounded step)
   + evidence-sufficiency gate counterweight. Charter Part-37 amendment, migration discipline.
3. **F57/F58/F59** — gather freshness wave (headline/forward slices + per-class doc floors;
   live-mode recency window ~45d; primary allowlist = charter's "filings, official posts").
4. **F60** — let fresh/leading indicators score (registry weights are DATA = safe; any
   scoring.py change ships only as a versioned migration, Part 33).
5. **F64** — trigger-first daily brief + Brier scoring. 6. **F65** — "So what for TSMC"
   section. 7. **F66** — post-hoc citation audit (low priority).
Standing feature track (slot in as capacity allows): F23 compliance matrix, F24 entity
canonicalization, F25 wiki scaling (hard prereq for 34-category fan-out); then WHY-tree,
HTML dashboard, discovery, layer tier, Main roll-up.
REJECTED (user-approved, do not resurrect): SEC-EDGAR/sec-api pipeline; search-API/scraper
benchmarking. Do NOT relitigate sp5 design decisions
(spec `docs/superpowers/specs/2026-07-02-thesis-book-design.md`).
**VERIFY NEXT LIVE CYCLES (F52–F54 criterion #6):** re-gathered URLs mint vintage ids (no
FindingStore collision/exclusions); price rows carry D6/gpuSpotPrice with canonical units;
PMI matches ≥1 series once two post-fix cycles exist; brains echoing seed triggers pass.

## THE BIG DECISIONS ALREADY MADE (do not relitigate without reason)

1. **Output goal:** deterministic, brief-first Market-State brief; pure projection of the store;
   HTML dashboard later. THE CALLS (thesis book, per-cycle deltas) leads the page above STATE &
   WHY; raw indices live ONLY in the trust footer; five-word band map with earned "(was X)".
2. **Lane discipline (Part 21):** merchant-gpu owns merchant vendors only; the cross-cutting
   "GPU market state" brief is a LAYER-TIER product. Category tier does not recommend actions —
   theses are category-scoped falsifiable claims; recommendations stay Layer/Main.
3. **Claude Code IS the brain** — no OAuth/SDK/API. Live extraction/judgment/thesis = TOOL-LESS
   dispatched Opus subagents through `--emit-prompt` → `--recorded`; judgment samples are SEPARATE
   generations (F38); thesis book gets ONE coherent author (no voting); gate rejection →
   re-dispatch the brain with the errors — NEVER hand-edit brain output (held throughout the
   2026-07-03 gate: 5 re-dispatches, all logged in cycle-log.json, zero hand edits).
4. **Price is overlay-only (F8):** D6/gpuSpotPrice never feed DMI/SMI; price-level drafts carry
   polarity 0 (the gate enforces it; non-price findings must move a track).
5. **Contract v1.2 frozen core RE-FROZEN:** `gate.py`, `scoring.py`, `schema/*`,
   `judgment/briefing.py`, `judgment/judge.py` aggregation, `pipeline.py`, `JsonStore`. Sub-project
   5 shipped fully additive (final reviews verified empty frozen diffs on both branches).
6. **Anti-whipsaw lives in code:** secondary-only reversals defer as CHALLENGED; primary evidence
   or a second consecutive signal applies; conviction ±1/cycle; applied broken retires. Promotion:
   provisional → registered at ≥2 cycles + ≥2 publisher domains (F31 key).
7. **Product Q&A decisions** live in `docs/action-items.md`; "nothing changed" is a first-class
   honest headline (renders as the compact book list).

## OPERATING NOTES / INVARIANTS (carry forward)

- Run from repo root `C:\Users\danie\random_for_fun`; Python at `.venv/Scripts/python`
  (recreate: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`).
- Worktrees: `.worktrees/<name>` (gitignored); shared root `.venv` imports the WORKTREE's code when
  pytest runs from the worktree root — no per-worktree venvs.
- Registry/taxonomy paths via `gpu_agent/config.py`; taxonomy lives at `docs/taxonomy.json` and its
  category ids are `<layer>.<category>` (merchant-gpu, hyperscaler-asic, foundry-packaging,
  hbm-memory, …; infrastructure.hyperscale-cloud / infrastructure.neocloud). The six judge
  dimensions: momentum, unitEconomics, competitiveStructure, moat, bottleneck, strategicRisk —
  the judge may cite ONLY within each dimension's briefing group (feed the real groups to a
  re-dispatch, never invented names — a 2026-07-03 dispatch error proved the gate catches this).
- The run's `--as-of` overrides the assignment's asOf (F50). Day-grain asOf for daily cycles.
  Tracked-store carve-outs: `store/chips.merchant-gpu/`, `store/wiki/`, `store/findings/`,
  `store/theses/`, `store/seen_docs.jsonl`, `store/cycle-log.json`.
- **Doctrine:** code computes + gates + stores; the brain reasons; nothing un-gated reaches a
  number; every claim cites findings; page text is DATA; every cap/skip/drop logged; provisional
  quarantined; paywalled inventoried + never fetched (TrendForce/SemiAnalysis stayed unfetched
  through the gate); the session NEVER hand-edits brain output — re-dispatch with the errors.
- Tests deterministic; suite green at every merge (**828 passed / 3 skipped** on main). Commit
  trailer names the ACTUAL model. Push freely.
- **Windows:** prefer PowerShell but NOT `>` redirection for UTF-8 (use bash for redirects); avoid
  double quotes inside `git commit -m` (here-strings); synchronous subagent transcripts are NOT
  written to task output files — capture their answers from the tool result (resumed/background
  agents DO write transcripts).
- Model policy: opus for important/final reviews, frozen-adjacent numeric work, and ALL brains;
  sonnet for mechanical per-task implementer/reviewer work.

## WHAT'S DONE (compressed — details in `git log`, the ledger `.superpowers/sdd/progress.md`, docs/superpowers/specs|plans/)

- **sp1–sp4** (harness · live runs · output/coverage · daily monitor) — merged; see ledger.
- **2026-07-02 fix backlog F1–F51:** waves 0/1/2 + contract v1.2 migration + F46 first genuine
  second cycle — all merged + pushed. Suite 417 → 626.
- **Sub-project 5 (Thesis Book):** spec `dd41b5a` → plans `83b7c5b` → 5-1 merged `7197226` →
  5-2 merged `d5dd492` → integration gate passed (this handoff). Suite 626 → 796.
  Ledger has per-task review outcomes + the deferred-minors list for both pieces.
- **F52/F53/F54 small-fix wave:** spec `091c709` → plan `0e6cb0e` → merged (5 commits,
  `2a2dae7..2c070f4`). Suite 804 → 828. Ledger has per-task reviews + the final-review triage.
- **F62 (flagship consumes the daily store):** spec `de0719b` → plan `d18c0c2` → implemented on
  branch `f62-flagship-consumes-store` → **MERGED to main `eb925bc` (2026-07-04, user go);
  suite on merged main 974 passed / 3 skipped** (F62 + F70 combined).
  New `gpu_agent/corpus.py` (45-day windowed store↔fresh union), `corpus` CLI,
  `pipeline --corpus-store/--corpus-report`, `observed=` vintage tag (emit-only kwarg),
  judge crux sentence now demands a consensus-departure (`b8f41f8`), run-cycle wiring +
  write-back. Frozen core empty-diff vs main; final opus whole-branch review APPROVED
  (0 critical/important, all minors ride). **Eval RESOLVED on merit after three attempts:**
  attempts 1-2 failed the judge seam (6.50, 6.25 vs incumbent 6.75) with one signature — all 8
  generations missed the rubric's consensus-departure point the 3-sentence voice budget never
  asked for; user chose option B (fix the prompt, keep the rubric); attempt 3 PASSED
  (extract 6.75 / judge 7.50 / thesis 6.00 — sensitivity-differentiation went 1→2 on all four
  judges) and the baseline was rebaselined WITHOUT --force (`f605a77`). Suite on the branch:
  **970 passed / 3 skipped / 0 failed.** Full three-attempt history in
  `docs/superpowers/2026-07-04-f62-eval-run-notes.md`; raw runs in the worktree's gitignored
  `work/eval-f62-2026-07-04/` (attempts 1-3 preserved — see the RETAINED WORKTREES REGISTRY).
  Ledger: `.superpowers/sdd/f62/progress.md` (repo root).
- **Open user decision:** repo is still named `random_for_fun` — rename before TSMC-branded
  exposure.

## ⚠ 2026-07-06 ~08:57 +0800: SCHEDULED HEADLESS RUN STOOD DOWN (blocker record, AFK-default)

- A scheduled headless session was invoked to run daily `category:chips.merchant-gpu`
  (mode: daily, live) and found **another instance already mid-run on the same cycle**:
  `work/daily-2026-07-06/` created 08:46 (gather complete 08:45:49, `extract-dispatch.md`
  emitted 08:46:04) and 10 fresh uncommitted `store/seen_docs.jsonl` entries with
  `asOf: 2026-07-06`. No `2026-07-06` scorecard existed yet - the run was in flight
  (brain dispatch phase).
- Per the mid-run stop rule, this session STOPPED: no `git pull`, no cycle run, no
  commits. **AFK-default decision: stand down and cede daily #2 (2026-07-06) to the
  in-flight instance**, which owns the post-run store/ commit+push and the HANDOFF run
  summary. This note was appended (uncommitted) by the blocked session; fold or remove
  it once daily #2 lands.
- If the in-flight run stalled or died (no `store/chips.merchant-gpu/2026-07-06-*.json`
  and no new commit hours later), daily #2 still needs to be run - do NOT assume it
  happened.
