# Parallel-Execution Setup — Post-F62 Lanes β and γ: Design

**Date:** 2026-07-04
**Status:** approved (user, 2026-07-04) — set-up-only scope, concise lane plans
**Author model:** Claude Opus 4.8

## Context

Phase 1's approved sequence (do-not-reorder) is
**F62 → F63 → F57/F58/F59 → F60 → F64 → F65 → F66**. The prompt spine
(F63→F60→F64→F65) is serialized by the armed F6 eval gate: any edit to an emitted
brain prompt (extraction / judgment / thesis prompt text, cli vocab glue, or registry
vocab data) turns the suite red until `run-eval` + `eval rebaseline` commits a new
`fixtures/evals/baseline.json`. That single baseline file is the true bottleneck — two
prompt-changing branches in flight collide on it.

This design sets up the parallelism that is *available around* that spine: the two
work-streams that change no emitted brain prompt and therefore run concurrently with it,
each in its own git worktree, each internally sequential (superpowers'
subagent-driven-development forbids parallel implementers on one branch;
dispatching-parallel-agents requires disjoint file domains).

**Repo state at design time:**
- `main` @ `f086c29` — code unchanged since the F70 merge (`7938eb4`); suite **927 passed
  / 3 skipped**. Commits since are roadmap docs only.
- F62 is on `.worktrees/f62-flagship-store` (branch `f62-flagship-consumes-store`), all 9
  plan tasks implemented, pushed, review-approved — **blocked on the user** at Task 9: the
  `observed=` vintage tag regressed the judge eval seam over two attempts; merge +
  rebaseline decision is pending. Not part of this setup; noted for merge-order.

## Goal

Create two isolated worktrees and one concise implementation plan each, so the
**current-signal** lane (F57/F58/F59 + F56) and the **render/prompt-polish** lane (F68)
can be executed in parallel — with the prompt spine and with each other — the moment the
user chooses to run them. No implementation code is produced by this setup.

## The two lanes

| Lane | Items | Owns (no other lane touches) | Eval gate |
|---|---|---|---|
| **β — Current-signal** | F57, F58, F59, F56 | `.claude/skills/gather-category/SKILL.md`; `manifests/*.json`; `gpu_agent/cli.py` (ingest `--primary-sources` allowlist for F59; `--as-of` shape validation for F56); the β test files | **No** |
| **γ — Render/prompt-polish** | F68 (a–f) + F56 minor-1 | `gpu_agent/report.py`; `gpu_agent/brief.py`; `gpu_agent/thesis.py` (new prose lint + the F56 comment only — never `_finding_lines`/prompt text); `gpu_agent/reader.py`; `registry/acronyms.json`; the γ test files | **No** |

**Why F56 sits in β, not γ.** Lanes are *file-ownership* domains. F56's `--as-of`
validation lives in `cli.py`, which F59 also edits. Grouping all `cli.py` + gather work
in β keeps β and γ disjoint (`report.py`/`brief.py`/`thesis.py`/`reader.py` vs.
`cli.py`/gather-skill/manifests), which is the precondition for true parallel execution.

**F56 splits (surfaced during planning).** F56's core (`--as-of` shape validation,
`cli.py`) goes to β. Its two "cosmetic minors" do **not**: minor-1 (the "mirrors gate
rule 3" comment) lives in `thesis.py`, which γ owns — folded into γ (Task 5); minor-2
(the malformed `"shown: ."` when `price_indicators=[]`) lives in `extraction/prompt.py`,
a **brain-prompt file** — deliberately **excluded** from both eval-gate-free lanes (it
must ride a prompt-spine change or a deliberate eval-checked standalone commit).

**Why neither lane trips the eval gate.**
- β changes gather *orchestration* prose, the primary-source allowlist (ingest-time
  confidence stamping), and CLI argument validation — none of which is an emitted
  extraction/judgment/thesis prompt or registry vocab. The prompt hashes are untouched.
- γ adds post-hoc deterministic lints and render/reader fixes — it validates and formats
  *output*, it does not change any emitted prompt's text.

This is the property that makes them safe to run alongside the serial spine: they never
contend for `fixtures/evals/baseline.json`.

## Worktrees & branches

Mirroring the historical lane convention (`fix/lane-a` … `fix/lane-e`, `fix/lane-g`):

- β → worktree `.worktrees/lane-freshness`, branch `fix/lane-freshness`
- γ → worktree `.worktrees/lane-polish`, branch `fix/lane-polish`

Both branch from `main` @ `f086c29`. `.worktrees/` is gitignored; the shared root `.venv`
imports the worktree's code when pytest runs from the worktree root (no per-worktree
venv). Suite baseline at branch start: **927 / 3**. F62's worktree is untouched.

## Merge order & conflict management

Standard "merge gate, sequential; full suite green before each merge; rebase each onto the
accumulated result." Cross-branch file overlaps are only with F62, never between β and γ:

- β ↔ F62 on `gpu_agent/cli.py` (F62 added the `corpus` command + pipeline corpus flags).
- γ ↔ F62 on `gpu_agent/thesis.py` (F62 Task 7 edited `_finding_lines`).

**Recommended order:** F62 first *if* it unblocks soon, then β and γ rebase onto post-F62
`main` and merge in either order. If F62 stays blocked, β and γ may merge first onto
F62-less `main`; F62 then rebases onto them and reconciles the two overlap points above at
its merge. Either way the reconciliation is a rebase touch-up at exactly two files — β and
γ never block each other because they share no file.

The prompt spine (F63→F60→F64→F65) merges through the eval gate independently and is out of
scope here.

## Deliverables of this setup

1. This design doc, committed to `main` (local; no push without user go).
2. Two worktrees created: `.worktrees/lane-freshness`, `.worktrees/lane-polish`.
3. Two concise lane plans in `docs/superpowers/plans/` (the `w2-lane-g` format: goal,
   owned + never-edit file lists, ordered tasks each with a named pinning test and a commit
   message, self-review line).

## Out of scope (explicit)

- Any implementation code (user chose set-up-only).
- The prompt spine (F63/F60/F64/F65) and F62's merge/rebaseline decision.
- Dispatching execution agents (a later, separate user go).
- `git push` (shared checkout; local commits only until the user asks).

## Decision provenance

User-approved 2026-07-04 in the brainstorming dialogue: (1) scope = set-up-only
(worktrees + plans, no code); (2) plan depth = concise lane plans per the repo's
execution-model protocol, backlog entries serving as the spec; (3) the F56→β refinement
for disjoint-domain isolation. Relitigate here if any pick is wrong.
