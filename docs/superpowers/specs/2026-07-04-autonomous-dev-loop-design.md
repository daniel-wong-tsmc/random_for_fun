# Autonomous Dev Loop — fresh instances drain the queue: Design

**Date:** 2026-07-04
**Status:** DRAFT — awaiting user review. **Every fork below was taken under the AFK
precedent** (user asked for the capability, was away at every question gate; each pick is
the recommended option and is individually overridable before implementation).
**Author model:** Claude Fable 5

## Purpose

One command starts a loop: a fresh Claude Code instance reads a queue file, claims the next
task, executes it with the superpowers workflow, records the outcome, commits the ledger,
and exits; the driver launches the next fresh instance. Development continues without the
user re-briefing every session. The user's live role narrows to two things: **merging
ready branches** and **overriding recorded picks**. This is autonomy of the *development
process* (Claude Code building the product) — distinct from the roadmap's autonomy track
(the product running unattended), but its learnings (headless trigger, held states,
notification) feed that track's Phase-2 pilot design.

## Decisions (all AFK-taken — override any of these before implementation)

1. **Gate policy: auto-implement, human merge.** Instances run brainstorm → spec → plan →
   implement → review autonomously on branches, taking the recommended option at every
   internal fork (the backlog's recorded lean where one exists) and recording the caveat in
   each spec's decision-provenance note (the F52–F54 precedent, codified). **Merging a
   feature/lane branch to main stays a user action.** Ready-to-merge branches accumulate;
   the loop continues past them until a dependency needs one merged. Rejected alternatives:
   full auto-merge (a bad merge lands on main before anyone looks; revisit after the loop
   earns trust), pre-approved-tasks-only (queue drains after two lanes and blocks on you
   for every spec).
2. **Mechanism: an external driver script launching headless instances.** A PowerShell
   while-loop runs `claude -p <kickoff>` once per task; each instance is genuinely fresh
   (clean context), and the loop survives any single instance dying. Rejected alternatives:
   a long-lived orchestrator session (dies with the window; context accretes), scheduled
   cloud routines (venv + suite setup per run; better suited to the product's own autonomy
   pilot later).
3. **Queue + ledger: one markdown file, `docs/superpowers/DEV-QUEUE.md`.** Human-first like
   everything in this repo, machine-parseable by construction (strict `STATE:` lines the
   driver greps). The queue is the machine state; HANDOFF stays the narrative companion.
4. **Permissions: a committed project allowlist, never `--dangerously-skip-permissions`.**
   `.claude/settings.json` allowlists the tools the workflow needs (git, gh, `.venv`
   python/pytest, repo-scoped file edits) plus `--permission-mode acceptEdits` on the
   headless invocation. An instance that hits a non-allowlisted prompt records
   `BLOCKED(permission: <tool>)` and exits — the allowlist grows by recorded evidence, not
   by disabling the guardrail.
5. **v1 driver is sequential — one instance at a time.** Parallelism stays *inside* an
   instance (the existing lane protocol: dispatch parallel lane agents in disjoint
   worktrees, per fix-backlog's execution model). A parallel driver is YAGNI until the
   sequential loop has run clean for a while.
6. **Notification, v1: queue states + console output.** The driver ends with a one-screen
   report (items advanced, branches awaiting merge, questions recorded). A push channel
   (PushNotification / scheduled check-in) is deferred — noted, not built.

## Components

### 1. `docs/superpowers/DEV-QUEUE.md` — the queue/ledger

Ordered task entries, each:

```
## Q2 — F63 corroboration doctrine + evidence-sufficiency gate
STATE: pending                    | one of: pending, in_progress, ready-to-merge,
                                  |         merged, blocked, needs-user
TYPE: feature                     | feature (brainstorm→spec→plan→implement)
                                  | or plan (approved plan exists — execute it)
DEPENDS-ON: (none)                | queue ids that must be `merged` first
BRANCH/WORKTREE: (minted at claim)
POINTERS: fix-backlog F63; charter Part 37; F69 handoff note (structured field)
LOG:
- (instances append one dated line per state change, with instance id)
```

**Seed content** (the approved Phase 1 sequence, post-F62):
- **Q1** `plan` — execute lanes β+γ in parallel per
  `specs/2026-07-04-parallel-execution-setup-design.md` (plans exist, user-approved;
  worktrees exist). One queue item: a single instance dispatches both lane agents.
- **Q2** `feature` — F63 corroboration doctrine + evidence-sufficiency counterweight
  (same spec, ships together — roadmap Phase 1 main risk).
- **Q3** `feature` — F60 fresh/leading indicators score. DEPENDS-ON: Q2 merged (eval
  baseline + scoring semantics serialize the prompt spine).
- **Q4** `feature` — F64 trigger-first daily brief + Brier. DEPENDS-ON: Q3 merged.
- **Q5** `feature` — F65 "So what for TSMC". DEPENDS-ON: Q4 merged.
- **Q6** `feature` — F66 post-hoc citation audit (low priority). DEPENDS-ON: Q5 merged.
- The user appends further items (desk-maturity picks, standing track) by editing the file.

### 2. `scripts/dev-loop.ps1` — the driver (deliberately dumb; all judgment lives in instances)

```
loop (max N iterations, default 5):
  git pull --ff-only on main
  next = first entry with STATE: pending whose DEPENDS-ON are all merged
         (also: flip ready-to-merge → merged when git says the branch is merged)
  if none:
    report (ready-to-merge list, needs-user list, or "queue drained"); exit
  launch: claude -p (kickoff file) --permission-mode acceptEdits --model opus
          with a generous wall-clock timeout (default 4h)
  after exit: git pull; if the claimed entry's STATE did not change on two
              consecutive iterations → stop ("loop stall — needs a human")
```

Plus `-DryRun` (parse queue, print what would run, launch nothing).

### 3. `scripts/dev-loop-kickoff.md` — the per-instance contract

The fixed prompt every fresh instance receives. In order:
1. **Orient:** read `DEV-QUEUE.md` + `HANDOFF.md`; `git branch -vv` + `git status`; never
   touch another entry's branch/worktree (the F69 mixup precedent).
2. **Claim = lock:** flip the chosen entry to `in_progress` with instance id + timestamp,
   commit + push to main (docs-only commit) *before* any work. A stale `in_progress`
   (crashed predecessor) may be resumed only if branch + plan-checklist state is coherent;
   otherwise mark `blocked` with what was found.
3. **Execute by TYPE**, with the superpowers skills the repo already uses:
   `plan` → executing-plans / subagent-driven-development in the named worktree;
   `feature` → brainstorming (AFK rules: recorded lean or recommended option at every
   fork, caveat in the spec's provenance note) → writing-plans → subagent-driven
   development → requesting-code-review → verification-before-completion.
4. **Hard rules (restated, binding):** frozen contract v1.2; the armed F6 eval gate
   (`run-eval` + `eval rebaseline` committed WITH any prompt change); never hand-edit
   brain output — re-dispatch; suite green before ready-to-merge; stop-slop on prose;
   commit trailer names the ACTUAL model; **never merge to main** (only docs/queue/handoff
   commits land on main); push the branch.
5. **Terminal states:** `ready-to-merge` (final review clean + suite + eval green) |
   `blocked(<reason>)` | `needs-user(<the question, verbatim>)`. Update queue LOG +
   HANDOFF, commit, push, print a one-line status, exit.
6. **Runaway bounds:** systematic-debugging on any failure; if the suite cannot get green
   after 3 distinct attempts, or the same error repeats 3×, mark `blocked` and exit.

### 4. `.claude/settings.json` — the allowlist

Generated from what the workflow actually uses (git/gh, `.venv` pytest/python, repo file
edits, worktree commands), committed to the repo so every fresh instance inherits it.
Grows only by evidence: a `BLOCKED(permission: …)` entry is the request ticket.

## Coordination with manual sessions

The queue becomes **the one lock surface for every instance, manual included**: a rule
added to HANDOFF says any session doing feature work claims the queue entry first
(`in_progress`, committed). The loop must not start while a manual instance is mid-task
outside the queue; as of this design the field is clear — F62 is merged, and lanes β/γ are
handed to the loop as Q1.

## Error handling

- **Suite red / gate rejection loops:** bounded (contract step 6) → `blocked`, never an
  infinite grind.
- **Instance crash:** stale `in_progress` → resume-or-block judgment by the next instance
  (contract step 2), always recorded in LOG.
- **Ledger races:** instances `git pull --rebase` immediately before every queue/handoff
  commit; the queue commit is small and last.
- **Driver stall detection:** an entry that survives two instances unchanged stops the
  loop — a loop defect is a human's problem, not something to retry silently.
- **Merge-wait:** when every pending item depends on an unmerged branch, the driver exits
  with the ready-to-merge list — that is the expected rhythm: the loop runs to the merge
  frontier, you clear merges in a batch, the loop resumes.

## Testing

- `-DryRun` exercises queue parsing + picker logic with no launch.
- **Iteration 1 is supervised:** run the driver for exactly one iteration on Q1 (lanes
  β+γ — approved plans, no eval-gate contact) and audit the ledger transitions, the
  permission log, and the final state before granting longer runs.
- The driver stays out of the pytest suite (scripts/, not gpu_agent/) — it is deliberately
  trivial; the queue file's format is validated by the dry-run, and every instance
  re-validates state on claim.

## Out of scope (recorded, not lost)

Auto-merge; a parallel driver; push notifications; scheduled/cloud execution of the loop;
any change to the product pipeline itself. The loop is pure development harness — if it
ever needs a `gpu_agent` change, that change is a queue item like any other.

## Expected throughput, stated honestly

With human-merge gating, the loop typically advances 2–3 items per merge batch (Q1 in
parallel worktrees, Q2 on its branch, then merge-wait — Q3 needs Q2's baseline on main).
The bottleneck is by design: it is the same eval-gate serialization the parallel-execution
setup identified, now made visible in DEPENDS-ON lines instead of discovered in flight.
