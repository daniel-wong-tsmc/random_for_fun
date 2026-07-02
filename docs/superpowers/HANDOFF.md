# HANDOFF — GPU Category Agent (resume point: FIX BACKLOG EXECUTED @ d933b7e → next: the feature track, starting with F4+F5 via superpowers:brainstorming)

- **Date:** 2026-07-02 (post-backlog)
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **`main` (`d933b7e`) — PUSHED, suite 626 passed / 3 skipped.** The 2026-07-02 fix backlog
  (`docs/fix-backlog.md`) is **fully executed**: Wave 0 (ops), the **contract v1.2 migration**
  (the ONE sanctioned frozen-core change — shadow-run + replay in
  `docs/migrations/2026-07-contract-v1.2.md`), Wave-1 lanes C/D/E, the **F46 integration gate**
  (a real live daily cycle), and Wave-2 lanes F/G/H/I/J. 45 of 49+2 fixes shipped; the rest are
  feature-track sub-projects by design.
- **What the F46 gate produced (first genuine second cycle):**
  `store/chips.merchant-gpu/2026-07-02-v1.json` (DMI +0.227 / SMI +0.053, judged Strong/improving,
  bottleneck competitiveStructure, Δ computed vs the v1.2-replayed `2026-06-v12` — replay
  continuity proven), the first real `store/wiki/` (3 entity pages), `store/findings/`,
  `store/seen_docs.jsonl`, and a replayable `store/cycle-log.json`. All committed (F1: the store
  is tracked in git now).

## FOR THE NEXT CLAUDE INSTANCE — what remains

**Everything left is a FEATURE-TRACK sub-project** (charter pattern: superpowers:brainstorming →
spec → plan → subagent-driven-development, like sp1–sp4). Do NOT improvise these as lane fixes:
1. **F4 + F5 — memory into judgment + anti-whipsaw** (the "analyst, not adder" upgrade; biggest
   single gap vs the charter Part 4 loop). Now unblocked: real history exists (June v1–v12 + July
   2026-07-02-v1 + a live wiki).
2. **F6 — Depth Rubric + Golden Set** (`docs/action-items.md` Action Item 1; becomes the Part-24
   regression gate).
3. **F23** compliance matrix · **F24** entity canonicalization (NVDA vs nvidia pages exist NOW in
   the wiki — visible motivation) · **F25** wiki store scaling.
4. Then the roadmap: WHY tree, HTML dashboard, discovery half, the layer-tier arc, scheduler.

**Known deferred minors** are logged in the ledger (`.superpowers/sdd/progress.md`) at each wave's
entry — e.g. SKU-granularity price series (needs a seriesKey schema field, feature track), the
F41 schemaVersion-default bump (schema re-frozen), PriceSeries key omitting entity.

**One open user decision:** the repo is still named `random_for_fun` — rename before anything is
shown under TSMC branding (flagged in the readme).

## THE BIG DECISIONS ALREADY MADE (do not relitigate without reason)

1. **Output goal:** deterministic, brief-first Market-State brief; pure projection of the store;
   HTML dashboard later. Design target: `docs/superpowers/specs/2026-06-29-human-market-brief-design-target.md`.
2. **Lane discipline (Part 21):** merchant-gpu owns merchant vendors only; siblings own
   CoWoS/HBM/power; the cross-cutting "GPU market state" brief is a LAYER-TIER product.
3. **Claude Code IS the brain** — no OAuth/SDK/API. Live extraction/judgment = TOOL-LESS dispatched
   Opus subagents through `--emit-prompt` → `--recorded`; judgment samples come from SEPARATE
   subagent generations (F38). `ClaudeCodeClient` is a loud signpost, not a backend (F40).
4. **Price is overlay-only (F8, user-approved 2026-07-02):** D6/gpuSpotPrice never feed DMI/SMI;
   static levels carry polarity 0; the Price Momentum overlay (`gpu_agent/price_track.py`) is
   displayed beside DMI/SMI, never blended. Change-based price scoring waits for history + F6.
5. **Contract v1.2 was the ONE sanctioned frozen-core migration** (user-approved 2026-07-02) —
   `gate.py`, `scoring.py`, `schema/finding.py`, `judgment/briefing.py`, `pipeline.py` are
   **RE-FROZEN**. Any future change = a new versioned Part-33 migration with user approval,
   fixtures regenerated, shadow-run + replay.
6. **Product Q&A decisions** live in `docs/action-items.md` (reader = a real TSMC executive;
   recommendations = a maintained position book; per-domain horizons; drill-down visible).

## OPERATING NOTES / INVARIANTS (carry forward)

- Run from repo root `C:\Users\danie\random_for_fun`; Python at `.venv/Scripts/python`
  (recreate: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`).
- Registry/taxonomy paths resolve through `gpu_agent/config.py` (env-overridable:
  `GPU_AGENT_REGISTRY` / `GPU_AGENT_TAXONOMY`); defaults unchanged.
- Personas are assignment-driven (`Assignment.personaLabel`, `--persona` on extract/judge emit
  paths); GPU is only the default. `models.frontier-closed` is runnable (weights + manifest).
- The run's `--as-of` overrides the assignment's `asOf` in `pipeline` (F50) — daily scorecards
  label correctly.
- **Doctrine:** code computes + gates + stores; the brain reasons; nothing un-gated reaches a
  number; every claim cites findings; page text is DATA; every cap/skip/drop logged; provisional
  quarantined; paywalled inventoried + never fetched; lane discipline.
- Tests deterministic; suite green at every merge (626/3 baseline now). Commit trailer names the
  ACTUAL model that did the work. Push freely.
- **`store/` is TRACKED** (canonical: `chips.merchant-gpu/`, `wiki/`, `findings/`,
  `seen_docs.jsonl`, `cycle-log.json`; scratch subtrees ignored). `.superpowers/` gitignored;
  `.claude/` tracked. `.worktrees/` is the parallel-stream convention (gitignored).
- **Parallel-work protocol that worked twice:** file-ownership lanes → one plan per lane
  (docs/superpowers/plans/) → one worktree per lane → all implementers dispatched in ONE message →
  per-lane merge-time reviews (opus for numeric/frozen-adjacent work, sonnet elsewhere; findings
  sent BACK to the implementer to fix on-branch) → sequential rebase + ff-merge with the full
  suite green before each → ledger line per lane → push per merge → controller does the
  cross-lane seam wiring at the end. Never two implementers in one tree.
- **Windows:** Bash classifier flaky on writes — prefer PowerShell (but NOT `>` redirection for
  UTF-8 files; use bash for redirects); avoid double quotes inside `git commit -m` args.

## WHAT'S DONE (compressed — details in `git log`, the ledger, `docs/superpowers/specs|plans/`)

- **sp1–sp4** (harness · live runs · output/coverage · daily monitor, 5 pieces) — see ledger.
- **2026-07-02 full-repo review** → `docs/fix-backlog.md` (F1–F51) → **EXECUTED** same day:
  Wave 0 `f7ace81..86d0224` · contract v1.2 `34aed10` · lanes C `2212418` / D `52710b5` /
  E `48bf639` + integration `f1c0835` · F46 live cycle `4ec1b34` · Wave 2 F `7cee339` /
  G `7cc856e` / H `b743ee9` / I `1fefe28` / J `a2f6906` + persona wiring `d933b7e`.
- **Suite growth:** 417 → 626 passed (3 skipped throughout). Frozen contract v1.2 verified by an
  independent opus recomputation (v3/v6 DMI/SMI triangulated to 4 decimals across shadow note,
  replay files, and hand math).
