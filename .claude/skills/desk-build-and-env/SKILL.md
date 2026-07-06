---
name: desk-build-and-env
description: Use when setting up this repo (random_for_fun / GPU Category Agent) on a new machine or fresh clone, recreating the .venv, running the pytest baseline for the first time, diagnosing "python3 not found"/Windows-Store-stub errors, bootstrapping web-reach tools (agent-reach, last30days), figuring out what survives a fresh clone vs what is per-machine state (work/, .superpowers/, worktrees, user-level skills, ~/.claude/CLAUDE.md), or hitting PowerShell/Git-Bash quoting, cp1252, or CRLF issues.
---

# Desk Build and Env

## Overview

This repo (`gpu_agent`, a.k.a. "the desk") is a deterministic Python 3.13 / pydantic-v2 pipeline with **zero
external runtime services** — no database, no API keys, no Docker. Standing it up from nothing is: create a
venv, `pip install -e ".[dev]"`, run pytest, bootstrap two stdlib-installable CLI tools. The hard part isn't
the install — it's knowing which of the things you observe on a working machine are **cloned repo state**
(same on every checkout) versus **per-machine invisible state** (exists only here, vanishes on a fresh clone
or a careless `git clean`) versus **per-user config outside the repo entirely** (`~/.claude/`).

## When to use

- Standing up the repo on a machine that has never run it (or after a fresh clone).
- "Why does `python3` fail / do nothing / open the Store?" or any Windows-Store-stub symptom.
- The pytest baseline count looks wrong, or you need to know what "green" means right now.
- `agent-reach` / `last30days` are missing, unhealthy, or you're adding a new web-reach tool.
- Orienting a new operator on what a fresh clone will and won't hand them (worktrees, ledgers, user skills).
- PowerShell 5.1 native-command / encoding / CRLF friction while running repo commands.

## When NOT to use

- Actually running a category/layer/market cycle → **run-cycle** (repo skill) via **run-gpu-market** (user
  skill).
- CLI flag/env-var *semantics* (what `--no-sufficiency` does, registry knobs) → **desk-config-and-flags**.
- Symptom → root-cause triage for a failing run → **desk-debugging-playbook**.
- Change-control doctrine (who may merge, what needs a Part-33 migration, F-item lifecycle) →
  **desk-change-control**.
- The eval harness mechanics (replicates, ε, rebaseline) → **desk-validation-and-qa** / **run-eval**.

---

## 1. Fresh-clone bootstrap

```
git clone https://github.com/daniel-wong-tsmc/random_for_fun.git
cd random_for_fun
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

- **Never `python3`.** On this Windows box it resolves to `AppInstallerPythonRedirector.exe` (the Windows
  Store stub) — it silently does nothing useful. Use `.venv/Scripts/python` once the venv exists, or `py -3`
  before it does.
- **Python version**: `pyproject.toml` declares `requires-python = ">=3.11"`. The venv on this machine
  actually runs **Python 3.13.7** (verified: `.venv/Scripts/python --version`, 2026-07-06). Don't assume 3.11
  — check what you actually got.
- **Runtime dependency is one package**: `pydantic>=2,<3` (installed: 2.13.4). `[dev]` adds `pytest>=8` — this
  is the extra you need for the operational path.
- **`[llm]` extra (`anthropic>=0.40`, `claude-agent-sdk>=0.1`) is NOT part of the bootstrap.** The live brain
  path is a dispatched Claude Code subagent, never a metered API call. `gpu_agent/llm/anthropic_api.py` is a
  real, coded alternate backend (`--backend anthropic_api`) but it is doctrine-forbidden on the live path —
  don't install `[llm]` "just in case" and don't "fix" a `claude_code` backend `LLMError` by switching
  backends. See **desk-config-and-flags** for the backend axis, **desk-change-control** for the doctrine.
- **Run everything from repo root.** `gpu_agent/config.py` resolves `registry/indicators.json`,
  `docs/taxonomy.json`, `registry/corroboration.json` relative to CWD (overridable via `GPU_AGENT_REGISTRY` /
  `GPU_AGENT_TAXONOMY` / `GPU_AGENT_CORROBORATION` env vars, but nothing sets those by default). Running the
  CLI or pytest from a subdirectory or from inside a worktree's own root silently reads the wrong (or no)
  registry. From a worktree, `cd` to the worktree root first — its checkout has its own `registry/`, `docs/`,
  etc. at the same relative paths.

### Preflight (every session, cheap)

```
.venv/Scripts/python -c "import gpu_agent"
```
No output = success. If it fails, the venv is missing or broken — recreate it per above.

### The pytest baseline — verify, don't trust a number

```
.venv/Scripts/python -m pytest --collect-only -q
.venv/Scripts/python -m pytest
```

| When | Collected | Passed | Skipped | HEAD |
|---|---|---|---|---|
| 2026-07-05 (discovery baseline) | 1063 | 1059 | 4 | `a8ec757` |
| 2026-07-06 (re-verified live, this authoring session) | 1070 | 1066 | 4 | `1a9eb33` |

Both numbers are real — the suite grew by 7 tests in one day of active development. **Neither number is "the"
baseline**; re-run `--collect-only` and the full suite yourself and compare against whatever HEAD you're on
(`git log --oneline -1`). Expect it to keep growing. The **shape** that doesn't change: a flat `tests/` dir
(no subdirectories except `tests/fixtures/`), no `conftest.py`, no custom pytest markers — only `skipif` and
env vars gate anything.

The 4 skips are **always** the same four gates, never rot:

| Test | Gate | Why it skips by default |
|---|---|---|
| `tests/test_extraction_integration.py` | `GPU_AGENT_LIVE_LLM=1` | live-LLM smoke, off by default (deterministic $0 suite) |
| `tests/test_pipeline_integration.py` | `GPU_AGENT_LIVE_LLM=1` | same |
| `tests/test_gather_integration.py` | `GPU_AGENT_LIVE_GATHER=1` | live-gather smoke, off by default |
| `tests/test_web_reach_launcher.py` (one of the two OS-keyed tests) | `os.name` | the POSIX-only or Windows-only half always skips on the other OS |

If your run shows a **different** skip count or a **failure**, don't assume the repo is broken before you've
ruled yourself out: confirm you're at repo root, confirm `.venv` is the one you just built (not a stray
system Python on `PATH`), and confirm nothing in your shell exports `GPU_AGENT_LIVE_LLM`/`GPU_AGENT_LIVE_GATHER`.

`tests/test_evals_baseline_pin.py` going **red** after any prompt-adjacent edit is a different animal — that's
the F6 regression gate working as designed, not an environment problem. Never "fix" it by hand-editing
`fixtures/evals/baseline.json`. See **run-eval** / **desk-validation-and-qa**.

Readme staleness note: `readme.md` still says "suite 417 passed / 3 skipped" (verified stale, 2026-07-06) —
it's a stale F48-era (2026-07-02) line, never refreshed. Don't cite it; run the suite yourself.

---

## 2. Web-reach bootstrap

Two external CLIs extend gathering beyond the built-in `WebSearch`/`web_fetch`: `agent-reach` (role `fetch`)
and `last30days` (role `discovery`, leads-only — never ingested as evidence; see **market-state-reference** /
**desk-config-and-flags** for the role doctrine itself). Both are declared in `registry/web-reach-tools.json`
and installed/health-checked automatically — there is no manual per-machine ritual to remember.

```
scripts\web-reach-ensure.cmd --json          REM Windows
sh scripts/web-reach-ensure --json           # POSIX (Git Bash, macOS, Linux)
.venv/Scripts/python -m gpu_agent.web_reach_ensure --check-only --json    # check only, never installs
```

- Both launcher scripts are thin: they locate a Python (prefer `.venv`, then `py -3`/`python3`, then
  `python`) and exec the **stdlib-only** `gpu_agent.web_reach_ensure` module from repo root — it imports
  no pydantic, so it works even before `pip install -e .` (bare-clone safe).
- It reads `registry/web-reach-tools.json`, health-checks each enabled tool (60s cap per check), and installs
  anything missing via the registry's per-OS `install` recipe (default 600s cap per install command). It's
  idempotent — a healthy run is sub-second and **never re-installs or upgrades a healthy tool**.
- Verified live on this machine (2026-07-06): `agent-reach --version` → `Agent Reach v1.5.0`; both tools
  report `"status": "ok"` from `--check-only --json`.
- Two triggers call it automatically, both committed to the repo: the `gather-category` skill's preamble
  (primary, runs at the start of every live gather) and a `.claude/settings.json` `SessionStart` hook
  (backstop, matcher `startup|clear|compact` — deliberately **not** `resume`). Re-verify current hook content
  with `git show HEAD:.claude/settings.json` — as of `1a9eb33` both the web-reach-ensure hook and a second
  `sh scripts/session-orient || true` hook are present and fully committed (no working-tree diff).
- **Preflight text inconsistency, still live**: this repo's `CLAUDE.md` says preflight with
  `agent-reach doctor --json`; the registry's own `healthCmd` is `agent-reach --version` (the automation's
  actual health signal). Historical reason for the split: an earlier `agent-reach` build exited 120 on
  `doctor`. Re-verified live today: `agent-reach doctor --json` exits **0** on this machine's v1.5.0 — so the
  two commands may have converged, but don't be surprised if a different `agent-reach` version disagrees.
  Trust `--version` (exit 0 + version string) as the minimum bar; treat `doctor` as informational.
- **macOS/Linux install recipes in `registry/web-reach-tools.json` are authored from each tool's install
  docs and unit-tested for logic/order — never exercised on real mac/Linux hardware.** `docs/web-reach.md`
  says so explicitly: the first mac/Linux operator should expect to confirm/adjust `install`/`healthCmd`.
  Only the Windows path is hardware-verified.
- Adding a same-role tool to the registry is a pure data change (no skill/charter edit). A **new** `role`
  value needs a one-time doctrine update (this happened once, for `discovery`, F70) — see
  **desk-config-and-flags**.
- Optional per-machine secrets (Twitter/Xiaohongshu cookies, Groq/Brave/Perplexity/ScrapeCreators keys) are
  never committed and never required — their absence just marks that capability unhealthy, logged, not fatal.

---

## 3. The per-machine invisible layer

This is the part a fresh clone (or a naive "just copy the repo" migration) silently loses. Two different
kinds of invisibility: **gitignored-but-inside-the-repo-folder** (survives a clone if you also copy the
untracked files, dies on `git clean`) and **outside-the-repo-entirely** (per-user Claude Code config; a new
person needs it created or handed to them separately — cloning the repo never gets it).

| What | Tracked in git? | Survives fresh clone? | Notes |
|---|---|---|---|
| `CLAUDE.md` (repo root) | **Yes**, as of `29584d9` (verified `git ls-files CLAUDE.md`, 2026-07-06) | Yes | Was untracked at the 2026-07-05 discovery snapshot — re-verify at read time, this is exactly the kind of fact that flips. |
| `scripts/session-orient` + its `.claude/settings.json` hook entry | **Yes**, fully committed (verified `git diff HEAD -- .claude/settings.json` is empty) | Yes | Same caveat — was an uncommitted local hook as of 2026-07-05. |
| `work/` | No (gitignored) | **No** | Per-run scratch: blobs, RawDocument snapshots, brain prompt/answer JSONs, corpus artifacts, **eval replicate runs**. Never `git clean` it — see below. |
| `.superpowers/` | No (gitignored) | **No** | SDD build ledgers (`sdd/`, `sdd-f67/`) + lane sentinels (`handoffs/*-DONE.md`). Currently holds `output-engineering-DONE.md` and `f74-cycle-log-DONE.md` (verified 2026-07-06). Per-machine only. |
| `.worktrees/<name>` (real worktrees) | No (gitignored) | **No** | Verified live 2026-07-06: `eval-v2` (branch `eval-v2-replicate-baseline` @ `7b79846`), `f62-flagship-store` (branch `f62-flagship-consumes-store` @ `4f6c9d1`, **local-only, not on origin**), `f63-corroboration` (branch `f63-corroboration-doctrine` @ `adf21e8`). The `f74-cycle-log` worktree referenced in recent handoff notes is **already merged and gone** — `git worktree list` no longer shows it; F74 landed on main at `257cf1b`. This list drifts fast — re-run `git worktree list` yourself. |
| `.venv/` (shared root venv) | No (gitignored) | **No** | Recreate per §1. One shared venv for root + all worktrees — never a per-worktree venv. |
| `~/.claude/CLAUDE.md` (user-level, **outside the repo**) | N/A — not part of this repo at all | **Never**, by construction | Verified present on this machine (2026-07-06): codifies the Windows/PowerShell tax (§4), the multi-instance pre-commit check (`git log --oneline -1` + `git status`), and the AFK-default provenance rule (AFK-timeout decisions are recorded as "AFK-default," never "user-approved"; never merge/push/delete branches under one). A fresh machine or a different user account needs this handed to them or rewritten — cloning the repo does not carry it. Whether AFK-default is binding law or observed practice is **desk-change-control**'s call, not this skill's; this skill only attests that the file exists, here, and won't travel with `git clone`. |
| User-level skills the repo flow references (`run-gpu-market`, `desk-handoff`, `resume-desk`, `eval-driver`, `instance-sync`, `stop-slop`, plus the web-reach tools' own skills `agent-reach`/`last30days`) | N/A — live at `C:\Users\<user>\.claude\skills\<name>\SKILL.md` | **Never** | Verified present on this machine (2026-07-06, `ls C:\Users\danie\.claude\skills`). A fresh Claude Code account elsewhere has none of these; the repo's own `.claude/skills/` (`run-cycle`, `gather-category`, `run-eval`, plus this skill library) is everything that *does* travel with the clone. |

**Never `git clean` in this repo or any of its worktrees.** `work/` holds the raw replicate runs that back
the committed `fixtures/evals/baseline.json` provenance, and some of those runs live **inside retained
worktrees** (e.g. `.worktrees/f63-corroboration/work/eval-f63-regate-2026-07-05/{r1,r2,r3}` — not in the root
checkout's `work/` at all). `.superpowers/sdd/` holds build-ledger history that exists nowhere else. The
baseline **file** survives in git regardless; the raw runs behind it do not. There is deliberately no registry
of which worktrees are retained for this reason — that gap is open backlog item **F76** (unfixed as of
`1a9eb33`, 2026-07-06) — so treat every worktree you find as possibly load-bearing until you've checked what's
in its `work/`.

`store/` deserves one call-out here even though its full mechanics belong to `desk-architecture-contract` /
`desk-config-and-flags`: `models.frontier-closed` has an assignment fixture and is config-runnable, but its
`store/models.frontier-closed/` directory **does not exist yet** and there is **no `.gitignore` carve-out**
for it (verified: `ls store/` shows no such directory, 2026-07-06). Honest status: **"runnable-per-pins,
never yet run live."** The first live run of that category will write scorecards that `git status` silently
never sees (the whitelist only covers `chips.merchant-gpu/`) — add the negation line to `.gitignore` *before*
that first run, not after.

---

## 4. Worktree conventions

- Real worktrees live in gitignored **`.worktrees/<name>`** (top-level, dot-prefixed). A separate, similarly
  named **`.claude/worktrees/`** (nested under `.claude/`) is a **stray empty directory** — not the
  convention, don't put anything there, don't be misled by its existence (verified still present and still
  empty, 2026-07-06). The two paths differ only in whether `.claude/` is a parent — easy to typo past.
- **One shared root `.venv`.** From inside a worktree, the interpreter is `../../.venv/Scripts/python` — verified
  that path resolves from `.worktrees/f63-corroboration`. Never create a per-worktree venv.
- Feature work happens **only** in a worktree on a claimed branch — never directly on the root checkout's
  `main`. Never touch another instance's branch or worktree — this is the standing rule after a real
  incident (a concurrent instance's stray commit landed on the wrong branch; see **desk-failure-archaeology**
  for the story).
- Retained-post-merge worktrees are not stray litter — they hold the gitignored `work/` raw data behind a
  committed eval baseline (see §3). Don't "clean up" a merged worktree without checking whether it's one of
  these.
- A branch existing only in `git branch -a` with no `remotes/origin/...` entry (e.g. `f62-flagship-consumes-store`
  as of 2026-07-06) is normal here — merged branches sometimes never had a remote push. Don't assume
  local-only means abandoned.

---

## 5. Windows 11 / PowerShell 5.1 tax

This machine is Windows 11 Home, PowerShell 5.1 as the primary shell, Git Bash available as a secondary tool.
These are per-machine environment traps, verified against the user-level `~/.claude/CLAUDE.md` and this
session's own tool behavior — they are not repo doctrine, just "how to not waste an hour here."

| Trap | Fix |
|---|---|
| `python3` resolves to the Windows Store stub (`AppInstallerPythonRedirector.exe`) and does nothing useful | Use `.venv/Scripts/python` (once the venv exists) or `py -3` |
| PowerShell 5.1 has no `&&` / `\|\|` chaining | `A; if ($?) { B }` for conditional, `A; B` for unconditional |
| No ternary / null-coalescing / null-conditional operators in PS 5.1 | Use explicit `if`/`else` |
| `2>&1` on a native exe in PS 5.1 wraps stderr lines as `NativeCommandError` and flips `$?` to false **even on exit 0** | Don't redirect native stderr in PowerShell; judge success by exit code, not by "did stderr print anything" |
| Native command progress/warnings on stderr (e.g. `git push`) are not failures | Check the actual exit code, not the presence of stderr text |
| Console codepage is cp1252 — printing non-ASCII from Python can raise `UnicodeEncodeError` | Reconfigure stdout to UTF-8 with `errors="replace"` before printing |
| Double quotes inside `git commit -m "..."` under PowerShell mangle the message | Use the Bash tool with a heredoc for commit messages, never inline PowerShell quoting |
| `>` redirects, heredocs, and multi-line quoting are fragile in PowerShell | Use the Bash tool (Git Bash / POSIX sh semantics) for these, not PowerShell |
| CRLF vs LF diffs on generated files | Treat LF as canonical; a CRLF-only diff is not a real change — don't chase it as a bug |
| Windows paths (`C:\Users\...`) vs POSIX (`/c/Users/...`) | In Python one-liners always use the Windows form; the two tools (Bash vs PowerShell) don't agree on which form resolves |
| PowerShell `Out-File`/`Set-Content` default to UTF-16 LE with BOM | Pass `-Encoding utf8` when another tool will read the file |
| `ConvertFrom-Json` returns a `PSCustomObject`, not a hashtable | No `-AsHashtable` in PS 5.1 — index with `.Property`, not `["key"]` |
| Shell working directory can silently reset between tool calls | Prefix repo commands with an explicit `cd` to repo root rather than assuming you're still there |

---

## 6. Fresh-machine smoke checklist

Ordered, copy-pasteable, with what to expect at each step. Run from a shell at repo root unless noted.

```
# 1. Clone (skip if already local)
git clone https://github.com/daniel-wong-tsmc/random_for_fun.git
cd random_for_fun

# 2. Venv + install
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"

# 3. Python version sanity
.venv/Scripts/python --version
#   expect: Python 3.1x.y  (>=3.11 per pyproject; this machine runs 3.13.7)

# 4. Import preflight
.venv/Scripts/python -c "import gpu_agent"
#   expect: no output = success

# 5. Test collection (shape check, not a full run)
.venv/Scripts/python -m pytest --collect-only -q
#   expect: "NNNN tests collected" with no errors; NNNN drifts (1070 as of 2026-07-06 @ 1a9eb33)

# 6. Full suite
.venv/Scripts/python -m pytest
#   expect: "M passed, 4 skipped" in roughly a minute, exit 0 (1066/4 as of 2026-07-06 @ 1a9eb33)

# 7. Web-reach bootstrap + health
scripts\web-reach-ensure.cmd --json         REM Windows
#   expect: {"webReach": {"agent-reach": {"status": "ok"|"installed-ok"}, "last30days": {...}}}
#   a fresh machine will show "installed-ok" the first time (install takes a few minutes), "ok" after

# 8. Confirm the health-check tool itself
agent-reach --version
#   expect: "Agent Reach vX.Y.Z", exit 0

# 9. Orient in the repo (git + doctrine state)
git log --oneline -1
git status --short
git worktree list
sh scripts/session-orient
#   read docs/superpowers/HANDOFF.md's top section (resume point) before touching anything

# 10. Confirm per-machine layer expectations (see §3 table)
#     — do NOT expect .worktrees/, .superpowers/, or user-level ~/.claude/skills/* on a truly
#       fresh machine; those are per-machine/per-user and must be rebuilt or handed over separately.
```

If step 5 or 6 errors instead of collecting/running cleanly, stop and diagnose before touching anything
live — see **desk-debugging-playbook**. If step 7 reports a tool `"failed"` or `"missing"` after an install
attempt, check the registry's per-OS `install` recipe for that tool (`registry/web-reach-tools.json`) —
on a mac/Linux box you may be the first to hit a recipe drift (§2).

---

## Common mistakes

- Calling `python3` and concluding "Python isn't installed" — it's the Windows Store stub, not an absence.
- Running pytest or the CLI from inside a worktree's parent directory, or from any directory that isn't the
  worktree/repo root — registry/taxonomy resolution is CWD-relative and fails or silently reads the wrong
  file.
- Citing `readme.md`'s test-count line as current — it's a stale 2026-07-02 snapshot; always run the suite.
- `git clean`-ing the repo or a worktree to "tidy up" — this destroys the raw eval replicate evidence behind
  the committed baseline and the SDD build ledgers, with no way to regenerate either.
- Assuming `.claude/worktrees/` is where worktrees live — it's a stray empty folder; real ones are
  `.worktrees/<name>`.
- Creating a per-worktree `.venv` "to be safe" — banned; one shared root venv, referenced as
  `../../.venv/Scripts/python` from inside a worktree.
- Installing the `[llm]` pyproject extra "just in case the brain needs it" — it doesn't; the live path never
  calls an API, and installing it doesn't unlock anything sanctioned.
- Assuming a fresh clone hands you `.superpowers/`, `.worktrees/`, or the user-level skills that repo skills
  reference (`run-gpu-market`, `eval-driver`, etc.) — none of these travel with `git clone`; they're
  per-machine or per-user and must be separately recreated or handed over.
- Treating the discovery-baseline pytest count (1059/4 @ `a8ec757`, 2026-07-05) as current — the suite grew
  to 1066/4 (@ `1a9eb33`, 2026-07-06) within a day of active development. Always re-collect.

---

## Provenance and maintenance

Facts in this skill were verified live against the repo on **2026-07-06 at `main` @ `1a9eb33`**. The
discovery sweep this skill was drafted from ran a day earlier, 2026-07-05, at `main` @ `a8ec757` — where the
two dates disagree (pytest counts, F74 merge state, CLAUDE.md tracked status, worktree list), the 2026-07-06
figures above are what was actually observed this session; the 2026-07-05 figures are cited only as historical
context. Re-verify every volatile fact class before trusting it further:

| Fact class | Re-verification command |
|---|---|
| Current HEAD / repo state | `git log --oneline -1` and `git status --short` |
| Pytest baseline (collected/passed/skipped) | `.venv/Scripts/python -m pytest --collect-only -q` then `.venv/Scripts/python -m pytest` |
| Python version actually in the venv | `.venv/Scripts/python --version` |
| Real worktrees currently checked out | `git worktree list` and `git branch -a` |
| Web-reach tool health | `scripts\web-reach-ensure.cmd --check-only --json` and `agent-reach --version` |
| CLAUDE.md / scripts/session-orient tracked status | `git ls-files CLAUDE.md scripts/session-orient` and `git diff HEAD -- .claude/settings.json` |
| F74/F76 backlog status | `grep -n "F74\|F76" docs/fix-backlog.md` and `git log --grep=F74 --oneline` |
| `store/models.frontier-closed` existence / gitignore carve-out | `ls store/` and `grep -n "frontier" .gitignore` |
| User-level per-machine files | `ls "$HOME/.claude/skills"` and check for `~/.claude/CLAUDE.md` |
