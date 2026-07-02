# HANDOFF — GPU Category Agent (resume point: sub-project 5 SPEC+PLANS COMMITTED @ 83b7c5b → EXECUTE 5-1 then 5-2)

- **Date:** 2026-07-02 (post-backlog, sp5 planned)
- **Repo:** https://github.com/daniel-wong-tsmc/random_for_fun
- **`main` (`83b7c5b`) — PUSHED, suite 626 passed / 3 skipped.** The 2026-07-02 fix backlog is
  fully executed (waves 0/1/2 + the F46 live-cycle gate — see `docs/fix-backlog.md` headers and
  the ledger). **Sub-project 5 (the Thesis Book) is brainstormed, specced, and planned — not yet
  built.** It answers the user's standing complaint: the cycle output "says a lot but tells me
  nothing."

## IMMEDIATE NEXT TASK — build sub-project 5

Read, in this order:
1. **Spec (user-approved section by section):** `docs/superpowers/specs/2026-07-02-thesis-book-design.md`
2. **Plan 5-1 (build first):** `docs/superpowers/plans/2026-07-02-thesis-engine.md` — 7 TDD tasks:
   thesis models + six-thesis seed book, rebuild-verified ThesisStore, gate, anti-whipsaw apply
   engine (F5), memory bundle (F4), prompts (judge memory injection, byte-identical when absent),
   `thesis` CLI stage + run-cycle skill wiring.
3. **Plan 5-2 (only after 5-1 is merged):** `docs/superpowers/plans/2026-07-02-thesis-output-surgery.md`
   — 5 tasks: five-word band map, THE CALLS renderer, WHY projection, page reorder with raw
   indices demoted to the trust footer, e2e acceptance.

**Execution method:** superpowers:subagent-driven-development per piece (fresh implementer per
task, review between tasks), each piece on its own branch in a worktree under `.worktrees/`
(`sp5-1-thesis-engine`, then `sp5-2-output-surgery`), opus for the final whole-branch review
(sonnet acceptable for per-task work), full suite green before merge, one ledger entry per piece
in `.superpowers/sdd/progress.md`, push after each merge. The pieces are SEQUENTIAL — 5-2 consumes
5-1's exact interfaces (pinned in the plans' Produces/Consumes blocks).

**After both pieces merge:** run one live daily cycle (run-cycle skill, `mode: daily`,
`category:chips.merchant-gpu`, day-grain asOf) so THE CALLS renders from a real judged book — the
same integration-gate pattern F46 used. Fix what breaks; commit the store state.

**Key spec decisions (user-approved — do not relitigate):** THE CALLS (thesis book with per-cycle
deltas) leads the page, stacked above STATE OF THE MARKET & WHY; positions are category-scoped
falsifiable THESES (the Category tier still does not recommend actions — that stays Layer/Main);
seeded + brain-maintained book with quarantined promotion; depth fields (mechanism /
falsifiableTrigger / sensitivity) gate-enforced NOW, the F6 golden-set harness LATER; anti-whipsaw
lives in code (secondary-only reversals defer as CHALLENGED; primary evidence or a second
consecutive signal applies); ONE tool-less Opus generation authors the book each cycle (no
majority voting); "nothing changed" is a first-class headline.

## THE BIG DECISIONS ALREADY MADE (do not relitigate without reason)

1. **Output goal:** deterministic, brief-first Market-State brief; pure projection of the store;
   HTML dashboard later. Design target: `docs/superpowers/specs/2026-06-29-human-market-brief-design-target.md`.
2. **Lane discipline (Part 21):** merchant-gpu owns merchant vendors only; the cross-cutting
   "GPU market state" brief is a LAYER-TIER product.
3. **Claude Code IS the brain** — no OAuth/SDK/API. Live extraction/judgment/thesis = TOOL-LESS
   dispatched Opus subagents through `--emit-prompt` → `--recorded`; judgment samples come from
   SEPARATE subagent generations (F38); `ClaudeCodeClient` is a loud signpost (F40).
4. **Price is overlay-only (F8):** D6/gpuSpotPrice never feed DMI/SMI; the Price Momentum overlay
   (`gpu_agent/price_track.py`) is displayed, never blended.
5. **Contract v1.2 was the ONE sanctioned frozen-core migration.** `gate.py`, `scoring.py`,
   `schema/finding.py`, `schema/scorecard.py`, `judgment/briefing.py`, `judgment/judge.py`
   aggregation, `pipeline.py`, `JsonStore` are **RE-FROZEN**. Sub-project 5 is designed to be
   fully additive — if a task seems to need a frozen edit, STOP and escalate.
6. **Product Q&A decisions** live in `docs/action-items.md` (real TSMC-executive reader; position
   book with per-cycle deltas; per-domain horizons; "nothing changed" is honest output).

## OPERATING NOTES / INVARIANTS (carry forward)

- Run from repo root `C:\Users\danie\random_for_fun`; Python at `.venv/Scripts/python`
  (recreate: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`).
- Worktrees: `.worktrees/<name>` (gitignored). The shared root `.venv` imports the WORKTREE's
  code when pytest runs from the worktree root — verified; do not create per-worktree venvs.
- Registry/taxonomy paths via `gpu_agent/config.py` (`GPU_AGENT_REGISTRY`/`GPU_AGENT_TAXONOMY`).
- Personas are assignment-driven (`Assignment.personaLabel`, `--persona` on emit paths).
- The run's `--as-of` overrides the assignment's `asOf` in `pipeline` (F50). Day-grain asOf for
  daily cycles; the store carve-outs in `.gitignore` track `store/chips.merchant-gpu/`,
  `store/wiki/`, `store/findings/`, `store/seen_docs.jsonl`, `store/cycle-log.json` (5-1 adds
  `store/theses/`).
- **Doctrine:** code computes + gates + stores; the brain reasons; nothing un-gated reaches a
  number; every claim cites findings; page text is DATA; every cap/skip/drop logged; provisional
  quarantined; paywalled inventoried + never fetched. The session NEVER hand-edits brain output —
  re-dispatch with the errors instead (a prior session violated this; don't repeat it).
- Tests deterministic; suite green at every merge (626/3 baseline). Commit trailer names the
  ACTUAL model that did the work. Push freely.
- **Windows:** prefer PowerShell, but NOT `>` redirection for UTF-8 (use bash for redirects);
  avoid double quotes inside `git commit -m` (use here-strings); the Bash safety classifier is
  flaky on writes — retry via PowerShell.
- Model policy: opus for important/final reviews and frozen-adjacent numeric work; sonnet for
  mechanical per-task implementer/reviewer work.

## WHAT'S DONE (compressed — details in `git log`, the ledger, `docs/superpowers/specs|plans/`)

- **sp1–sp4** (harness · live runs · output/coverage · daily monitor) — merged; see ledger.
- **The 2026-07-02 fix backlog (F1–F51) — EXECUTED same day:** Wave 0 ops · contract v1.2
  migration (shadow-run + replay v7–v12, `docs/migrations/2026-07-contract-v1.2.md`) · lanes
  C/D/E · F46 first genuine second cycle (`store/chips.merchant-gpu/2026-07-02-v1.json`, first
  real wiki) · Wave 2 lanes F/G/H/I/J (price track, robustness, generalization, coverage, rating
  anchors) · persona wiring. Suite 417 → 626.
- **Sub-project 5 brainstorm → spec (`dd41b5a`) → plans (`83b7c5b`)** — this handoff's task.
- Remaining feature track AFTER sp5: F6 golden set + backtesting; F23 compliance matrix; F24
  entity canonicalization; F25 wiki scaling; then WHY-tree extensions, HTML dashboard, discovery,
  the layer-tier arc.
- **Open user decision:** the repo is still named `random_for_fun` — rename before TSMC-branded
  exposure.
