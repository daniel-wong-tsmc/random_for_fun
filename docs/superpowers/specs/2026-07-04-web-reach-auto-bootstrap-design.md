# Web-Reach Auto-Bootstrap — Reproducible Per-Machine Install: Design

**Date:** 2026-07-04
**Status:** approved (user, 2026-07-04)
**Author model:** Claude Opus 4.8

## Context

The web-reach layer (charter **Part 37**; `docs/web-reach.md`) gives every gather cycle a
registry of external CLIs (`registry/web-reach-tools.json`) that run *complementarily* to the
built-in WebSearch/web_fetch: `agent-reach` (fetch role) and `last30days` (discovery role).

On the live `2026-07` merchant-gpu run both tools were logged **missing**. Root cause (verified,
not guessed):

- **Never bootstrapped on this machine.** Both are external tools installed by a *one-time
  per-machine* step (`docs/web-reach.md` §"One-time bootstrap"). `git pull` does not bring them
  down. Evidence: `agent-reach` absent from PATH and disk, its prerequisites `gh`/`mcporter` also
  absent (installer never ran); `last30days` absent from PATH, no `~/.claude/skills/last30days`,
  no installed plugin, marketplace never added, no `skills` npm global.
- **Windows `python3` trap (latent, tool-specific).** `last30days`' `healthCmd` is
  `python3 skills/last30days/scripts/last30days.py --preflight`. On Windows `python3` resolves to
  the Microsoft Store alias stub (`AppInstallerPythonRedirector.exe`), not real Python — so its
  health check would fail even after install. The repo elsewhere uses `.venv/Scripts/python` /
  `C:\Python313\python` (real Python 3.13). `agent-reach`'s own install doc flags this exact trap
  and prescribes `py -3`.

The health check behaved correctly (Part 37: "logged, never silent") and the run continued on the
built-ins — but the *extra reach* was lost, and nothing in the repo makes the tools appear on a
fresh clone.

**Reproducibility gap, stated plainly.** The current install is a manual per-machine ritual that
lives only in prose. A second machine that clones the repo and runs the agent gets the fallback,
not parity. Additionally, the project skills hardcode the Windows interpreter path
(`.venv/Scripts/python`, ~10 call sites in `run-cycle`/`gather-category`), so even the run flow is
not OS-portable today.

## Goal

Any machine that clones the repo and runs the GPU agent through Claude Code gets **both** web-reach
tools installed and health-passing in **free-core mode**, **automatically, every run**, with **zero
machine-unique artifacts committed**. The *recipe* is committed and runs on Windows, macOS, and
Linux; the *installed artifacts* stay machine-local. Secrets (cookies / paid API keys) remain an
**optional, documented** per-machine step (they cannot be committed).

**Decisions locked with the user (2026-07-04):**
- Platform scope: **Windows + macOS + Linux**.
- Credentials bar: **free-core auto; logged-in extras documented + optional**.
- Trigger: **both** the run-flow preamble (primary) **and** a committed SessionStart hook (backstop).

## Non-goals (YAGNI)

- No secret distribution / management (documented manual step only).
- No auto-upgrade of an already-healthy tool (install-if-missing only).
- No new web-reach tools; no change to gather doctrine beyond the install-timing flip below.
- **Nothing installed is ever committed** — installs go to standard external locations (pipx / a
  dedicated venv / the global skills dir / Node/gh/mcporter); the repo tree gains no binaries,
  venvs, `node_modules`, or cookies.

## Architecture

Five committed pieces. The registry is the source of truth; a stdlib-only engine reads it; a thin
launcher gives one OS-agnostic entry point; two triggers call the launcher; docs + tests lock it.

### 1. Registry as install source-of-truth — `registry/web-reach-tools.json`

Each tool object gains two OS-keyed fields (data, not code — matching the repo's existing
"tool list is data" design):

- `install`: `{ "windows": [cmd, …], "macos": [cmd, …], "linux": [cmd, …] }` — ordered shell
  commands that install that tool on that OS.
- `healthCmd`: promoted from a single string to `{ "windows", "macos", "linux" }`, each the
  OS-correct health command (fixing the `python3` → `py -3` trap on Windows).

Indicative recipes (exact command sequences finalized + Windows-verified during implementation):

- **agent-reach** (Python/pipx, per its install doc):
  - install: ensure `pipx` (`<py> -m pip install --user pipx` / `pipx ensurepath`; `brew install
    pipx` fallback on macOS) → `pipx install https://github.com/Panniantong/agent-reach/archive/main.zip`
    → `agent-reach install --env=auto` (auto-pulls gh / Node / mcporter / yt-dlp).
  - healthCmd: `agent-reach doctor` (all OSes).
  - `<py>` is `py -3` on Windows, `python3` on macOS/Linux.
- **last30days** (skills installer, non-interactive):
  - install (all OSes): `npx -y skills add mvanhorn/last30days-skill -g`.
  - healthCmd: resolve the globally-installed skill dir and run its preflight with the OS-correct
    interpreter (`py -3` on Windows). Health = "skill present + preflight exits 0"; if the
    install-relative path can't be resolved, report unhealthy (Part 37 unchanged).

A registry schema/validation update accompanies these fields.

### 2. Ensure engine — `gpu_agent.cli web-reach-ensure`

New subcommand backed by `gpu_agent/web_reach_ensure.py`. **Stdlib-only** (`platform`,
`subprocess`, `json`, `shutil`) so it runs on a bare clone *before* `.venv` / `pip install -e .`
exist. Algorithm, per `enabled` tool:

1. Detect OS via `platform.system()` → `windows|macos|linux`.
2. Run the tool's OS `healthCmd`. Healthy → record `ok` (sub-second fast path); skip install.
3. Missing/unhealthy → run its OS `install` commands in order, streaming output; then re-run
   `healthCmd`. Record `installed-ok` or `failed:<detail>`.

Contract:
- **Idempotent + safe every run.** Never upgrades a healthy tool; never touches secrets; honors the
  paywalled boundary (never fetches/installs licensed sources).
- **Logged, never silent** (Part 37): every check/install/skip is a log line; a machine-readable
  summary is emitted under `--json`.
- Flags: `--check-only` (health only, no install — used by the fast hook path and CI), `--json`
  (status block the gather preamble folds into `gather-log.json::webReach`), `--timeout <s>` per
  install command (a hung install can't block forever), `--tool <id>` (optional targeting).
- Exit code: `0` if all enabled tools end healthy; non-zero if any `failed`. **Callers treat
  non-zero as "log + continue on the built-ins"** — parity with today's doctrine; a failed install
  never blocks a run.

### 3. One cross-platform launcher

Committed thin launchers `scripts/web-reach-ensure` (POSIX sh) + `scripts/web-reach-ensure.cmd`
(Windows) that (a) resolve a usable Python — prefer `.venv` (`.venv/Scripts/python` on Windows,
`.venv/bin/python` on POSIX), else system `python` / `py -3` / `python3` — and (b) run
`<py> -m gpu_agent.cli web-reach-ensure "$@"` with the repo root importable. Because the engine is
stdlib-only, it works on a bare clone with only a system Python present (which the agent requires
anyway). This is the **single entry point**: both triggers call the launcher, so no caller makes an
interpreter assumption. It also resolves the existing Windows-only-`.venv/Scripts/python`
portability gap for this one path.

### 4. Two triggers (both, per the locked decision)

- **Run-flow (primary)** — `.claude/skills/gather-category/SKILL.md` web-reach preamble gains a
  step 0: run the launcher with `--json`, then health-check reads its output. Replaces "health-check
  each tool" with "ensure each tool, then report health." Guarantees the tools are ready *before*
  gather needs them, on every agent run.
- **SessionStart hook (backstop)** — committed `.claude/settings.json` SessionStart hook runs the
  launcher `--check-only` when a session opens in the repo; if anything is missing it kicks the full
  ensure. **Known tradeoff:** the one-time first-run install (a few minutes) blocks that first
  session start; every session afterward is an instant no-op. (Chosen over "warn-only" for true
  zero-touch.)

### 5. Doctrine + docs + tests

- **Doctrine flip.** `docs/web-reach.md` and charter **Part 37**: *"never install mid-cycle"* →
  *"ensure-installed idempotently at run start; install once per machine, no-op thereafter; never
  re-install or upgrade a healthy tool mid-run."* Rewrite web-reach.md §"One-time bootstrap" →
  §"Automatic bootstrap (idempotent, every run)"; document `web-reach-ensure` and the optional
  secrets step; add a line to `readme.md`.
- **Tests.** Extend `tests/test_web_reach_registry.py`: every `enabled` tool has `install` +
  `healthCmd` for all three OSes; schema holds. New `tests/test_web_reach_ensure.py` with a fake
  registry + mocked `subprocess`: healthy → no install; missing → runs install cmds *in order* →
  re-checks → `installed-ok`; `--check-only` never installs; `--json` shape; OS selection. **No real
  network in tests.**

## Data flow

```
Fresh clone → session opens → SessionStart hook → launcher --check-only
    → missing?  yes → full ensure (one-time, ~minutes) → tools installed to standard locations
             → no  → instant ok
Agent run → gather-category preamble → launcher --json → ensure (fast no-op when healthy)
    → webReach block {tool: ok|installed-ok|failed} → gather-log.json → gather proceeds with full reach
```

## What's committed vs machine-local

| Committed (the reproducible recipe) | Machine-local (never committed) |
|---|---|
| `registry/web-reach-tools.json` install/health recipes | installed `agent-reach` (pipx / venv) |
| `gpu_agent/web_reach_ensure.py` + CLI subcommand | global `last30days` skill install |
| `scripts/web-reach-ensure` + `.cmd` launcher | Node / gh / mcporter / yt-dlp |
| `.claude/settings.json` SessionStart hook | cookies / API keys (optional secrets) |
| `docs/web-reach.md`, charter Part 37, `readme.md` | any local caches / `.venv` (already gitignored) |
| `tests/test_web_reach_*.py` | |

## Verification & known limits

- **Windows path** is built and end-to-end verified on this machine (install actually runs, both
  tools reach `ok`).
- **macOS/Linux recipes** are authored from the tools' own install docs and validated by the mocked
  unit tests (logic, OS selection, ordering) — **verified-by-reading + unit-tested, not
  verified-by-running**, since neither OS is available on this box. This limit is documented in
  `docs/web-reach.md` so the first mac/Linux operator knows to confirm.
- Secrets remain out of scope for reproduction: free-core capability is the guaranteed bar; the
  documented optional step unlocks logged-in X/Reddit/LinkedIn and paid search keys per machine.

## Open questions

None blocking. Exact per-OS command strings and the `last30days` global-skill-dir resolution are
implementation details finalized (and Windows-verified) during the plan.
