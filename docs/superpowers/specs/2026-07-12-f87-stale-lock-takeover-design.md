# F87 — Stale-lock takeover for the wiki log lock (stacked on F25)

**Status:** approved design, ready for a lane plan.
**Decision provenance: user-approved 2026-07-12 (interactive AskUserQuestion, orchestrator
session — NOT AFK): dispatch now, stacked on F25's unmerged branch (merges immediately after
F25), rather than waiting for the F25 merge.** Design substance comes from the F25 final
review's recommendation (2026-07-12, recorded in `.superpowers/handoffs/f25-wiki-scale-DONE.md`
and backlog item F87). Any question/fork is a QUESTION-STOP per repo CLAUDE.md "Orchestrated
lane agents" — write `.superpowers/handoffs/f87-stale-lock-QUESTIONS.md` + recommendation, end
the turn, wait.

## Problem

F25's lockfile-guarded seq mint fails loud on a leftover `store/wiki/log.jsonl.lock`: after a
hard crash (SIGKILL/power loss) every later run raises `TimeoutError` until a human deletes
the lock. Correct for attended runs; incompatible with the unattended scheduled dailies that
went live 2026-07-12 (F83) — a crashed 3am run would block every following morning.

## The change (branch base: `f25-wiki-store-scale`)

- **Lock body gains an identity record:** the lock file is written with JSON
  `{pid, hostname, timestamp}` at acquire time (today it is empty/opaque).
- **Takeover rule — take over ONLY when the holder is provably dead:** on acquire timeout,
  read the lock body and take over (unlink + one immediate retry, with a LOUD log line naming
  the dead pid and lock age) only if ALL of:
  1. the body parses and carries pid + hostname + timestamp (unparseable/legacy body → never
     take over, fail loud);
  2. `hostname` matches this machine (a foreign-host lock is never taken over — fail loud);
  3. lock age exceeds a stale threshold (lean: 60s — the critical section is milliseconds;
     the plan may tighten with justification, QUESTION-STOP if it wants to loosen);
  4. the pid is **provably not running** on this machine.
- **Pid liveness on Windows via stdlib/ctypes only** (e.g. kernel32 OpenProcess +
  GetExitCodeProcess, handling pid-reuse conservatively — "can't prove dead" means "treat as
  alive"). **No new dependency.** If a dependency-free check cannot be made trustworthy,
  QUESTION-STOP — do not pull in psutil on your own authority.
- **Everything else stays fail-loud:** live holder, foreign host, young lock, unparseable
  body → the existing TimeoutError path, now with the review's minor applied: the message
  names the lock path AND the remedy ("delete this file if no writer is running").
- **Torn-write edge documented:** add the F25 review's noted pre-existing torn-write edge to
  the spec/risk notes in this lane's plan or the F25 spec's risk section (doc-only).

## Hard constraints

- Change surface: `gpu_agent/wiki/log.py` (the lock functions) + tests + docs. Nothing else.
- No emitted-prompt changes; no store/ edits; frozen core untouched.
- Suite baseline on this branch is F25's: **1215 passed / 5 skipped** — green at every commit.
- Merge order: this branch merges only AFTER F25; record that in the sentinel.

## Acceptance (each pinned by a test)

1. Dead-pid takeover: a stale lock naming a dead pid on this host, older than threshold →
   acquired after takeover, loud log line emitted, seq continuity preserved.
2. Live-pid refusal: a lock naming a LIVE pid (use the test's own pid) → no takeover,
   fail-loud path, regardless of age.
3. Young-lock refusal: dead pid but age below threshold → no takeover.
4. Foreign-host refusal: valid body, different hostname → no takeover.
5. Legacy/unparseable body → no takeover, remedy message present.
6. The F25 concurrency tests still pass unchanged on this branch (locking semantics for the
   normal path are byte-for-byte the same).

## Non-goals

Auto-expiry by age alone (age without proof-of-death never takes over); cross-host lock
coordination; changing lock hold times or the append critical section; touching F25's cache.
